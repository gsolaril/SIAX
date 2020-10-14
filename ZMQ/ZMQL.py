import zmq, time, datetime, pandas, threading, IPython

class ZMQL(object):
    #| Nombres de puertos; deben llevar al principio y en mayusculas, el TIPO (ej.: "PUSH Data", "SUB Trading", etc.)
    _PortsDef = {"PUSH": 32768, "PULL": 32769, "SUB": 32770} #| IDs para "Dirección" de cada puerto. Deben ser ints.
    #| Lista de códigos de error de MT4 con sus descripciones, en formato "pandas.Series".
    _MQErrors = pandas.read_csv("..\MQL4ErrorCodes.csv").set_index("#")["Error"]

#### Constructor #######################################################################################################

    def __init__(self, ID, context, ports = _PortsDef, verbose = False): 
        """ Object initializer.
        This is the basic building block of the communication pipeline flowchart. Personal adaptations of this scheme
        (e.g.: each one of the blocks in the trading system) will be a subclass of this, and shall inherit the following
        functions: "init", "shutdown", "_send" and "_receive". One subclass should also have their own "_process" method
        as a customized parsing procedure of the received messages. Finally, each subclass should automate all of these
        "_" functions as lower level tools: by creating wrapping methods that include them inside. (e.g.: "open_trade").
        Inputs:
            >> "context"... "ZMQ context" object. Will identify all ports in the protocol.
            >> "ports"..... "dict" object with port IDs as values. Keys must be "XXXX _______", where "XXXX" is the
                            port type ("PUSH", "PULL", "PUB", "SUB", etc.), and after a space separator, "___" shall
                            hold some short custom label (e.g.: "Data", "SAIX", etc.).
            >> "verbose"... Control variable. "= None" disables console prints aside from prioritary Python errors
                            (e.g.: assertions). "False" enables reports related to message sending, PULL responses
                            and MQL4 errors. "True" prints SUB responses (e.g.: tick data, active trade data).
        """
        assert isinstance(verbose, bool), "((INIT)) ERROR! \"verbose\" may either be \"True\", \"False\" or \"None\"."
        assert isinstance(context, zmq.sugar.context.Context), "((INIT)) ERROR! Use a valid (zmq.) \"context\" input."
        warn = "((INIT)) ERROR! \"ports\" dict may be something like: {\"PUSH ...\": (int), \"PULL ...\": (int), ...}."
        assert isinstance(ports, dict) and all([isinstance(port, int) for port in ports.values()]), warn
        assert (list(ports.values()) == list(set(ports.values()))), warn + " Each key/value must be unique."

        #| Dataframe con objetos de comunicación: con todas las variables de acceso al protocolo.
        self.Comm = pandas.DataFrame(columns = ["Port"], index = ports.keys(), data = ports.values())
        self.Enable = {"comm": True, "verbose": verbose} #| Diccionario con parámetros de control.
        self.Poller = zmq.Poller() #| Inicializar "poll" para empezar a detectar llegada de mensajes.

        print("---------------------------------------"*2)
        for label in self.Comm.index: #| Ir creando cada uno de los puertos de comunicación con MetaTrader.
            assert isinstance(ports[label], int), "((INIT)) ERROR! Ports must be integers and respond to MT4."
            if (verbose != None): print(f">>{label}<< Connecting to port {ports[label]}. Await for response...")
            enum = eval("zmq." + label.split(' ')[0]) #| "Enum" de ZMQ que distingue que tipo de puerto es.
            self.Comm.loc[label, "Enum"] = enum #| Guardar este "Enum" en el DataFrame de objetos de comunicación.
            Socket = context.socket(enum) #| Crear socket: portal de envío, recepción e interpretación de mensajes.
            self.Comm.loc[label, "Socket"] = Socket #| Guardar socket en DataFrame de objetos de comunicación.
            Socket.connect(f"tcp://localhost:{ports[label]}") #| Conectar cada dirección al protocolo común (ethernet).
            if (enum == zmq.PUSH): Socket.setsockopt(zmq.SNDHWM, 1) #| Limitar memoria para cache de puertos PUSH.
            if (enum == zmq.PULL): Socket.setsockopt(zmq.RCVHWM, 1) #| Limitar memoria para cache de puertos PULL.
            if (enum == zmq.SUB): Socket.setsockopt(zmq.SUBSCRIBE, b"")  #| Limitar memoria para cache de puertos SUB.
            if enum in (zmq.PULL, zmq.SUB): self.Poller.register(Socket, zmq.POLLIN) #| Crear "listener" para recepción.
            self.Comm.loc[label, "Cache"] = "" #| Crear columna en DataFrame como "inbox de últimos mensajes".
            #| Initialize poll set for message parsing.
        print("---------------------------------------"*2)

        self.Comm[["Port", "Enum"]] = self.Comm[["Port", "Enum"]].astype(int) #| Guardar "Enums" de ZMQ como ints.
        self._send(socket = "PUSH", message = "Check; ; ; ; ; ; ; ; ; ") #| Enviar un primer mensaje, como prueba.
        self.Thread = threading.Thread(name = "ID", target = self._receive) #| Hilo de espera y detección de recibidos.
        self.Thread.daemon = True #| Que el hilo paralelo finalice su trabajo apenas se termine el sistema.
        self.Thread.start() #| Arrancar hilo de espera. A partir de ahora, MetaTrader puede comenzar a responder.
        self._DebugLog = pandas.Series({datetime.datetime.now(): "Start"}) #| Lista de mensajes para debug.

#### Terminación #######################################################################################################

    def shutdown(self): 
        """ ZMQ shutdown.
        Will eliminate ports and terminate communication protocol. No inputs."
        """
        #| El hilo paralelo de recepción no debe seguir funcionando al cerrar ZMQ.
        self.Thread.join() #| Unirlo con el hilo principal, y cerrar ambos ya juntos.
        print("---------------------------------------"*2)
        for label in self.Comm.index: #| Por cada puerto...
            #| Dar el "listener" de baja, si es un puerto de recepción.
            if ("PULL" in label) or ("SUB" in label):
                self.Poller.unregister(self.Comm["Socket"][label])
            port = self.Comm["Port"][label] #| Adquirir ID de cada puerto.
            address = f"tcp://localhost:{port}" #| Armar dirección en protocolo.
            self.Comm["Socket"][label].disconnect(address) #| Disasociar de dirección.
            print(f">>{label}<< Disconnected from port {port}.") #| Informar en consola.
        print("---------------------------------------"*2)

#### Transmisión de mensajes ###########################################################################################

    def _send(self, socket, message): 
        """ Message sender.
        Inputs:
            >> "socket".... "string" with socket label as seen in Comm DataFrame. Must be of PUSH type.
            >> "message"... "string" with message content. Must hold 10 words separated by ";".
        """
        if not isinstance(socket, str) or not isinstance(message, str):
            print(f">>{socket}<< ERROR! Message to be sent, must be string") ; return
        if "PUSH" not in socket: return #| Los puertos no PUSH no estan hechos para enviar mensajes.
        self.Comm.loc[socket, "Cache"] = message #| Antes que nada, conservar copia del mensaje.
        try: #| Poner mensaje en "fila de espera" del socket. Enviar de inmediato apenas disponible.
            self.Comm["Socket"][socket].send_string(message, zmq.DONTWAIT) 
            if (self.Enable["verbose"] != None): print(f"[{socket}] Command sent: [{message}]")
            time.sleep(0.02) #| Esperar un poco para darle tiempo a la llegada de la respuesta.
        except zmq.error.Again: #| Limitar la espera del mensaje. Informar cuando esperó demasiado.
            print(f">>{socket}<< Warning! Timeout with no response... try again.")

#### Recepción de mensajes #############################################################################################

    def _receive(self): 
        """ Message receiver.
        This should never be executed directly. Must ONLY be accessed and running in the parallel "(self.)Thread".
        """
        while self.Enable["comm"]: #| Dentro del hilo paralelo, siempre y cuando este parámetro de control sea "True"...
            sockets_polled = dict(self.Poller.poll()) #| Chequear cuales son los puertos que han recibido algo.
            for label in self.Comm.index: #| Tomar a cada uno de los puertos que tengo registrados.
                Socket = self.Comm["Socket"][label] #| De ellos, tomar a cada uno de los sockets.
                if (Socket not in sockets_polled.keys()): continue #| Saltear los que no hayan recibido nada.
                if (sockets_polled[Socket] != zmq.POLLIN): continue #| Saltear los que no son de recepción.
                try: message = self.Comm["Socket"][label].recv_string(zmq.DONTWAIT) #| Formular respuesta como string.
                except: message = None #| Si no se pudo formular el string de respuesta, es que no hubo respuesta.
                if message: #| Si se formuló una respuesta, parsearla literalmente como una "linea de Python".
                    try: self._process(eval(message)) #| Por ejemplo: "eval('x = 2')" hace que "x" sea "2".
                    #| "self._process" va a ser una función que va a procesar la variable implicada.
                    except Exception as ex: #| Cuando hubo un error al procesarla...
                        if (self.Enable["verbose"] != None): #| Si se activó el verbose de errores "no graves"...
                            warning = f"Type: {type(ex)}. Args: {ex.args}" #| Mostrar mensaje de error.
                            print(f">>{label}<< Warning! Reception error --> {warning}")
                        continue #| No bloquear el bucle paralelo de recepción luego de un error de recepción.
                    self.Comm.loc[label, "Cache"] = message #| Guardar string en Cache de puerto tal y como llegó.
                    #| Verbose de 2º grado (False/True): Mostrar mensajes PULL. En general, son respuestas de sends.
                    if (self.Enable["verbose"] != None) and (label == "PULL"):
                        print(f">>{label}<< Received --> {message}", flush = True)
                    #| Verbose de 3º grado (solo True): Mostrar mensajes SUB. En general, datos asincrónicos (ticks).
                    if (self.Enable["verbose"] == True) and (label == "SUB"):
                        print(f">>{label}<< Received --> {message}", flush = True)
                    time.sleep(0.001) #| Apenas pausar al sistema para impedir saturación de punto de recepción.

#### Procesamiento en recepción ########################################################################################

    def _process(self, message): 
        """ Received message processing.
        As an example for class debugging purposes, we might use a basic log to store test messages (no more than 1000).
        """
        self._DebugLog[datetime.datetime.now()] = str(message) #| Añadir al final del log.
        excess = max(0, len(self._DebugLog) - 100) #| Medir si hay un exceso de mensajes.
        self._DebugLog = self._DebugLog[excess :]  #| Conservar siempre los últimos 100.