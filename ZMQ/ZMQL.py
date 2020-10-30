import os, sys, time, threading
import zmq, datetime, pandas
from random import random

class ZMQL(object):

#### Constantes de clase ###############################################################################################

    #| Ubicación de la "Common Data Folder". Todo archivo (CSVs) solicitado a MQL, irá a parar allí.
    _CommonPath = os.path.expanduser("~") + "\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files\\"
    #| Nombres de puertos; deben llevar al principio y en mayusculas, el TIPO (ej.: "PUSH Data", "REP Trading", etc.)
    _PortsDef = {"SUB": 65530, "PUSH": 65531, "PULL": 65532} #| Puertos de cada socket. Deben ser ints.
    #| Lista de códigos de error de MT4 con sus descripciones, en formato "pandas.Series". Descargar de Google Drive.
    _MQErrors = pandas.read_csv("https://drive.google.com/uc?id=1YFLpNNbJMd-NaZNjEklN4snBD-wcKc9r").set_index("#")
    
#### Constructor #######################################################################################################

    def __init__(self, context, ID, ports = _PortsDef, verbose = 1): 
        """ Object initializer.
        This is the basic building block of the communication pipeline flowchart. Personal adaptations of this scheme
        (e.g.: each one of the blocks in the trading system) will be a subclass of this, and shall inherit the following
        functions: "init", "shutdown", "_send" and "_receive". One subclass should also have their own "_process" method
        as a customized parsing procedure of the received messages. Finally, each subclass should automate all of these
        "_" functions as lower level tools: by creating wrapping methods that include them inside. (e.g.: "open_trade").
        Inputs:
            >> "context"... "ZMQ context" object. Will identify all ports in the protocol.
            >> "ports"..... "dict" object with port IDs as values. Keys must be "XXXX _______", where "XXXX" is one
                            socket type ("PUSH", "PULL", "PUB", "SUB", etc.), and after a space separator, "______"
                            may hold some short custom label (e.g.: "Data", "SAIX", etc.).
            >> "verbose"... Control variable. "= None" disables console prints aside from prioritary Python errors
                            (e.g.: assertions). "False" enables reports related to message sending, PULL responses
                            and MQL4 errors. "True" prints SUB responses (e.g.: tick data, active trade data).
        """
        assert verbose in (0, 1, 2), "((INIT)) ERROR! \"verbose\" may either be integer \"0\", \"1\" or \"2\"."
        assert isinstance(context, zmq.sugar.context.Context), "((INIT)) ERROR! Use a valid (zmq.) \"context\" input."
        warn = "((INIT)) ERROR! \"ports\" dict may be something like: {\"PUSH ...\": (int), \"PULL ...\": (int), ...}."
        assert isinstance(ports, dict) and all([isinstance(port, int) for port in ports.values()]), warn
        assert (len(ports.values()) == len(set(ports.values()))), warn + " Each key/value must be unique."
        assert isinstance(ID, str), "((INIT)) ERROR! \"ID\" string must differ from other block IDs."

        #| Dataframe con objetos de comunicación: con todas las variables de acceso al protocolo.
        self.Comm = pandas.DataFrame(columns = ["Port"], index = ports.keys(), data = ports.values())
        self.Enable = {"comm": True, "verbose": verbose} #| Diccionario con parámetros de control.
        self.Poller = zmq.Poller() #| Inicializar "poll" para empezar a detectar llegada de mensajes.
        self.Base = dict()

        print("---------------------------------------"*2)
        for label in self.Comm.index: #| Ir creando cada uno de los puertos de comunicación con MetaTrader.
            assert isinstance(ports[label], int), "((INIT)) ERROR! Ports must be integers and respond to MT4."
            if (verbose > 0): print(f"[[INIT]] {label} connecting to port {ports[label]}. Await for response...")
            enum = eval("zmq." + label.split(' ')[0]) #| "Enum" de ZMQ que distingue que tipo de puerto es.
            self.Comm.loc[label, "Enum"] = enum #| Guardar este "Enum" en el DataFrame de objetos de comunicación.
            Socket = context.socket(enum) #| Crear socket: portal de envío, recepción e interpretación de mensajes.
            self.Comm.loc[label, "Socket"] = Socket #| Guardar socket en DataFrame de objetos de comunicación.
            Socket.connect(f"tcp://localhost:{ports[label]}") #| Conectar cada dirección al protocolo común (ethernet).
            if (enum == zmq.SUB): Socket.setsockopt(zmq.SUBSCRIBE, b"{") #| Limitar memoria para cache de puertos SUB.
            if enum in (zmq.PUB, zmq.PUSH, zmq.ROUTER): self.Comm.loc[label, "Role"] = "S"
            if enum in (zmq.SUB, zmq.PULL, zmq.DEALER): self.Comm.loc[label, "Role"] = "R"
            if enum in (zmq.REQ, zmq.REP, zmq.PAIR): self.Comm.loc[label, "Role"] = "SR"
            if "S" in self.Comm.loc[label, "Role"]: Socket.setsockopt(zmq.SNDHWM, 1)
            if "R" in self.Comm.loc[label, "Role"]: Socket.setsockopt(zmq.RCVHWM, 1)
            if "R" in self.Comm.loc[label, "Role"]: self.Poller.register(Socket, zmq.POLLIN)
            self.Comm.loc[label, "Cache"] = "" #| Crear columna en DataFrame como "inbox de últimos mensajes".
            Socket.setsockopt(zmq.LINGER, 0) #| Al eliminar los sockets, se elimina cualquier fila de espera que tenga.
            #| Initialize poll set for message parsing.
        print("---------------------------------------"*2)

        self.Comm[["Port", "Enum"]] = self.Comm[["Port", "Enum"]].astype(int) #| Guardar "Enums" de ZMQ como ints.
        self.Thread = threading.Thread(name = ID, target = self._receive)
        self.Thread.daemon = True #| Detención inmediata ante cierre del programa.
        self.Thread.start()

        if self._check(): print("[[CHECK]] Successfully initialized and connected to MetaTrader! :)")
        else: print("((CHECK)) ERROR! Connection unsuccessful. Shutting down... :(", self._shutdown())

#### Terminación #######################################################################################################

    def _shutdown(self, EA = False, thread = True): 
        """ ZMQ shutdown.
        Will eliminate ports and terminate communication protocol. No inputs."
        Inputs:
            >> "EA".... If "True", force EA to close as well.
        """
        #| El hilo paralelo de recepción no debe seguir funcionando al cerrar ZMQ.
        print("---------------------------------------"*2)
        for label in self.Comm.index:
            if EA and ("S" in self.Comm.loc[label, "Role"]): self._send(label, "Shutdown")
        time.sleep(0.5) #| Esperar a que responda confirmando su propia terminación.
        self.Enable["comm"] = False #| Desactivar comunicación: sockets PUSH y SUB.
        for label in self.Comm.index: #| Por cada socket...
            #| Dar el "listener" de baja, si es un socket de recepción.
            if "R" in self.Comm.loc[label, "Role"]:
                self.Poller.unregister(self.Comm["Socket"][label])
            port = self.Comm["Port"][label] #| Adquirir ID de cada socket.
            address = f"tcp://localhost:{port}" #| Armar dirección en protocolo.
            self.Comm["Socket"][label].disconnect(address) #| Disasociar de dirección.
            print(f"[[EXIT]] {label} Disconnected from port {port}.") #| Informar en consola.
        print("---------------------------------------"*2) 
        if thread: self.Thread.join() #| Unirlo con el hilo principal, y cerrar ambos ya juntos.
        del self

#### Transmisión de mensajes ###########################################################################################

    def _send(self, label, message): 
        """ Message sender.
        Inputs:
            >> "socket".... "label" of socket row. Role in Comm (DF) must be "S" (sender).
            >> "message"... "string" with message content. Must hold 10 words separated by ";".
        """
        if not isinstance(label, str) or not isinstance(message, str):
            print(f"((SEND)) ERROR! Message must be a string. Got {type(message)}") ; return
        if "S" not in self.Comm.loc[label, "Role"]: return #| Solo permitir sockets de envío.
        message += ";"*(9 - message.count(";")) #| Completar con los separadores que falten.
        self.Comm.loc[label, "Cache"] = message #| Antes que nada, conservar copia del mensaje.
        try: #| Poner mensaje en "fila de espera" del socket. Enviar de inmediato apenas disponible.
            self.Comm["Socket"][label].send_string(message, zmq.DONTWAIT)
            if (self.Enable["verbose"] >= 1): print(f"<<{label}>> Command sent: [{message}]")
            time.sleep(0.02) #| Esperar un poco para darle tiempo a la llegada de la respuesta.
        except zmq.error.Again: #| Limitar la espera del mensaje. Informar cuando esperó demasiado.
            print(f"<<{label}>> Warning! Timeout with no response... try again.")

#### Comprobación de comunicación ######################################################################################

    def _check(self):
        """ Comm socket validation.
        Sends a "Check" message throughout its TX sockets, and awaits for a handshake-like response. If nothing
        is received, it is considered as a communication failure, and system closes down automatically for the
        sake of security.
        """
        for label in self.Comm.index: #| Enviar checks por todos los sockets de transmisión.
            if "S" in self.Comm.loc[label, "Role"]: self._send(label, "Check")
        for label in self.Comm.index: #| Revisar todos los sockets de recepción.
            time.sleep(0.25) #| Darle tiempo para recibir mensajes y llenar "Caches".
            if "R" in self.Comm.loc[label, "Role"]:
                if self.Comm["Cache"][label]: continue #| "Cache" lleno: hubo recepción
                #| Caso contrario, "Cache" vacío: no se recibió nada. Hubo alguna falla.
                print(f">>{label}<< ERROR! MQL4 \"check\" not answering!")  ;  return False
        return True #| Si está todo bien y no hubo un error en el camino, devolver "True".

#### Recepción de mensajes #############################################################################################

    def _receive(self): 
        """ Message receiver.
        This should never be executed directly. Must ONLY be accessed and running in the parallel "(self.)Thread".
        """
        while self.Enable["comm"]: #| Dentro del hilo paralelo, siempre y cuando este parámetro de control sea "True"...
            sockets_polled = dict(self.Poller.poll()) #| Chequear cuales son los puertos que han recibido algo.
            for label in self.Comm.index: #| Tomar a cada uno de los puertos que tengo registrados.
                Socket = self.Comm["Socket"][label] #| De ellos, tomar a cada uno de los sockets.
                if (Socket not in sockets_polled.keys()): continue #| Saltear los que no son de recepción. 
                if (sockets_polled[Socket] != zmq.POLLIN): continue #| Saltear los que no hayan recibido nada.
                try: message = self.Comm["Socket"][label].recv_string(zmq.DONTWAIT) #| Formular respuesta como string.
                except: message = None #| Si no se pudo formular el string de respuesta, es que no hubo respuesta.
                if message: #| Si se formuló una respuesta, parsearla literalmente como una "linea de Python".
                    try: self._process(eval(message)) #| Por ejemplo: "eval('x = 2')" hace que "x" sea "2".
                    #| "_process" va a ser una función que va a procesar la variable implicada.
                    except AssertionError: #| Dada una condición de cierre explicita dentro de "_process"...
                        print(f">>{label}<< ERROR! Forced shutdown condition --> {message}")
                        self.Enable["comm"] = False #| Detención del proceso...
                    except Exception as ex: #| Cuando hubo un error al procesarla...
                        if (self.Enable["verbose"] >= 1): #| Si se activó el verbose de errores "no graves"...
                            Type = str(type(ex))[8:-2] #| Conseguir el tipo de error en formato string.
                            Line = ex.__traceback__.tb_next.tb_next.tb_lineno #| Conseguir nº de linea del error.
                            warning = f"{Type}: {ex.args[0]}..." #| Armar mensaje de error y mostrar.
                            print(f">>{label}<< Warning! Process error at line {Line} ===>", warning)
                        continue #| No bloquear el bucle paralelo de recepción luego de un error de recepción.
                    self.Comm.loc[label, "Cache"] = message #| Guardar string en Cache de puerto tal y como llegó.
                    v = self.Enable["verbose"] #| 1º grado incluye todos los "R" menos "SUB". 2º grado incluye "SUB". 
                    if (v > 1) or (v and (label != "SUB")): print(f">>{label}<< Received -> {message}", flush = True)
                    sys.stdout.flush() #| Mostrar cualquier cosa que haya sido impresa por esta vía, en consola.
                    time.sleep(0.001) #| Apenas pausar al sistema para impedir saturación de punto de recepción.

#### Procesamiento en recepción ########################################################################################

    def _process(self, message):
        """ Received message processing - Default for debugging. Test this with "verbose = 2".
        To test AssertionErrors, we impose a condition which when (randomly) met, accounts as an error and blocks comm.
        """
        assert (random() > 1/20) #| Simulamos una condición crítica: por cada 10 ciclos, 1 me devolverá "AssertionError".

#### Unit test al ejecutar este código #################################################################################

if (__name__ == "__main__"):
    f = 0.05 #| "frame": marco temporal en segundos. Máxima precisión: 0.1 seg.
    through = list(ZMQL._PortsDef)[1]  #| Socket de envío de mensaje. NO COMENTAR!
    INST = ZMQL(context = zmq.Context(), ID = "DATA", verbose = 2)  #| Crear instancia ZMQL.
    INST._send(through, f"Ticks;BTCUSD;{f};0")     #| Enviar suscripción a BTCUSD S1 en slot 0.
    while INST.Enable["comm"]: time.sleep(0.01)    #| Mostrar lo recibido por SUB repetidamente.
    INST._send(through, f"Ticks;BTCUSD;{0};0")     #| Desuscripción BTCUSD. Notar cambios en MT4.
    INST._shutdown(False)                          #| Desconectar instancia de ZMQ y eliminarla.