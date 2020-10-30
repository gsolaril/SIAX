import datetime, pandas, time, ZMQL
from ZMQL import ZMQL

class MTrack(ZMQL):

#### Constantes de clase ###############################################################################################

    _TFLabels = {"T": "ticks", "Z": "milliseconds", "S": "seconds", "M": "minutes", "H": "hours", "D": "days"}
    _SymError = "\"symbol\" must be given as a string and must be enlisted in Broker's MetaTrader's symbol watch!"
    _TFError = "\"frame\" must carry one of the MetaTrader's standardized timeframes! (e.g.: \"M5\", \"H4\", etc.)"
    _DColumns = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum", "Spread": "max"}
    _DTError = "\"t1\" & \"t2\" must be datetime inputs."
    _TFError2 = "\"frame\" should be chosen from between MT4 standards."
    _TFMT4s = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN"]
    _SlotError = "\"slot\" must be an integer. Also check amount of slots in EA config."
    _MaxRows = 1000000 #| Máxima cantidad de filas en todos los DataFrames dentro de Base.

#### Constructor #######################################################################################################

    def __init__(self, context, verbose = 1):
        """
        Object initializer
        This is the Data exchange block that inquires MQL through ZMQ for market data, either synchronous or async.
        As a ZMQL child class, it does inherit every feature of itself: functions, attributes and constants. Besides,
        it avails the use of wrapper methods that predefine certain messages such as "OHLCV" for data history download,
        and "Ticks" for instantaneous data streaming. An important new addition is the designation of the data "Base" as
        a "dict" with distinct symbol datasets and variables whose update is automated by the custom "_process" method.
        Finally, it presents the new "Sim" method as a crossover between "OHLCV" and "Ticks": it emulates the stream of
        data by means of scanning an historical market data file and its content.
        Note: Port numbers for sockets are predefined as {"SUB": 65530, "PUSH": 65531, "PULL": 65532} by default. Try
        not to use such numbers for MTrade or any other ZMQL block so as to avoid interferences or spurious messages.
        Inputs:
            >> "context"... "ZMQ context" object. Will identify all ports in the protocol.
            >> "verbose"... Control variable. "= 0" disables console prints aside from prioritary Python errors
                            (e.g.: assertions). "1" enables MQL responses as of using "download" and "subscribe"
                            functions. "2" shows asynchronous market data stream incoming through SUB socket.
        """

        ports = {"SUB": 65530, "PUSH": 65531, "PULL": 65532}
        super().__init__(context, ID = "MTrack", ports = ports, verbose = verbose)
        #| Base de datos. Las "Keys" serán los instrumentos ("symbols").
        self.Base = {"_Config": pandas.DataFrame(columns = ["Frame", "Flag", "Slot"])}

#### Validación de especificaciones ####################################################################################

    @staticmethod
    def _check_symbol(symbol, action = None):

        if isinstance(symbol, str): return symbol.upper()
        print(f"(({action})) ERROR! {MTrack._SymError}")
        return None

    @staticmethod
    def _check_frame(frame, action = None):

        try: #| La separación solo funciona si "frame" es string.
            time_unit, N = frame[0], int(frame[1:]) #| Separar en letra y número, sabiendo...
            time_unit = MTrack._TFLabels[time_unit] #| ...que la letra siempre viene primero.
            return time_unit, N
        except: #| En caso de error, reportar y devolver 2 Nones.
            print(f"(({action})) ERROR! {MTrack._TFError}")
            return None, None #| Un None por letra, el otro por número.

#### Designación int ZMQL de marcos temporales #########################################################################

    @staticmethod
    def _frame_enum(frame):
        """
        MTrack timeframe label to enumeration integer.
        MetaTrader works with standard timeframes, identifying them with an "enum" integer. It is indeed equivalent to
        the amount of minutes between candle and candle (e.g.: "H2" would have an "enum = 120"). As we might need more
        precise and smaller timesteps, we will use a different enumeration mode, measuring seconds between two candles
        (e.g.: "H2" would have an "enum = 120 x 60 = 7200"). We will also enable negative enums for irregular (ticks')
        timeframes.
        Inputs:
            >> "frame"...   Timeframe label string, written as standardized by MetaTrader.
        """
        time_unit, N = MTrack._check_frame(frame)
        if (frame[0] == "T"): enum = -N
        if (frame[0] == "Z"): enum = N/1000
        if (frame[0] == "S"): enum = N
        if (frame[0] == "M"): enum = N*60
        if (frame[0] == "H"): enum = N*60*60
        if (frame[0] == "D"): enum = N*60*60*24
        return round(enum*10)/10

#### Compresión de velas hacia mayor temporalidad ######################################################################

    @staticmethod
    def _reframe(frame, data):
        """
        Restructure a market dataframe towards a different timeframe.
        Follows the same procedure as common trading platforms: Divides the index timeline in identical time intervals
        (equal to the given time-"frame"), Takes all candles belonging to each interval, and compresses them into a
        single candle, with the corresponding characteristic values according to what "_DColumns" dict instructs so.
        Timeframes can be irregular ("tick data") so in that case, index intervals are not time-specific but equal to
        the number of rows given in "T__".
        Inputs:
            >> "frame"...   Timeframe label to what should the "data" be adapted.
            >> "data"...    Dataframe with OHLCVS columns, and datetime objects as index.
        """
        assert isinstance(data, (pandas.Series, pandas.DataFrame)), \
               "ERROR! \"data\" must be a Pandas' series at least!"
        time_unit, N = MTrack._check_frame(frame) #| Unidad de tiempo, y cantidad de ellas.
        if (time_unit == None): return None #| "frame" inexistente dentro de "_check_frame".
        if (time_unit != "ticks"): #| Marco temporal regular...
            delta = datetime.timedelta(**{time_unit: N}) #| Crear objeto de salto de tiempo.
            data = data.resample(rule = delta)  #| Calcular velas nuevas.
        else: #| Si el marco temporal es irregular...
            rows = N*(numpy.arange(len(data))//N) #| Hallar número de filas final.
            data = data.groupby(data.index[rows]) #| Calcular velas nuevas.
        return(data.agg(MTrack._DColumns)) #| Reformular datos con nuevo "frame".

#### Declaración de nuevo instrumento ##################################################################################

    def _setup_symbol(self, symbol, frame, subject = ""):
        """
        Create new symbol in data "Base".
        Given a certain "symbol" and a certain time "frame", it creates its own new OHLCVS DataFrame inside "Base" and
        saves its configuration variables inside the "_Config" dataframe.
        Inputs:
            >> "symbol"...  Symbol (string) associated with a tradable instrument in MetaTrader.
            >> "frame"...   Timeframe label (string) following MetaTrader standards.
            >> "subject"... String including the name of the function in which this one is called.
        """
        #| Verificar que "symbol" y "frame" sean strings y correctos.
        symbol = MTrack._check_symbol(symbol, subject)
        time_unit, N = MTrack._check_frame(frame, subject)
        #| Interrumpir si "symbol" o "frame" incorrectos. Devolver "None" en tal caso.
        if (time_unit == None) or (symbol == None): return None, None
        if symbol in self.Base: #| Si "symbol" ya estaba registrado en "Base"...
            prev = self.Base["_Config"].loc[symbol, "Frame"] #| Adquirir "frame" actual.
            no_reframe_1 = (MTrack._frame_enum(frame) < MTrack._frame_enum(prev))
            no_reframe_2 = (MTrack._frame_enum(frame) == MTrack._frame_enum(prev)) 
            if not (no_reframe_1 or (no_reframe_2 and (subject == "Ticks"))):
                print(f"(({subject})) \"{frame}\" less accurate than former \"{prev}\".",
                "Restart object and database completion if wishing to decrease timestep.")
                return None, None  #| Nueva "frame" de menor precisión o igual: no hacer nada.
            print(f"[[{subject}]] Resampling \"{symbol}\" from \"{prev}\" to \"{frame}\"...")
            self.Base["_Config"].loc[symbol, "Frame"] = frame #| Reemplazar por "frame" nuevo.
            #| Ante un nuevo "frame", hacer el "reframe" de los datos almacenados hasta ahora.
            self.Base[symbol] = MTrack._reframe(frame, self.Base[symbol])
        else: #| Si "symbol" es nuevo, darle un espacio en "Base", y todos los elementos necesarios.
            self.Base[symbol] = pandas.DataFrame(columns = MTrack._DColumns.keys())
            self.Base["_Config"].loc[symbol, :] = frame, False, None #| Configuración base.
        return symbol, frame #| Devolver "symbol" y "frame" (no None) como prueba de que salió todo bien.

#### Procesamiento en recepción ########################################################################################

    def _process(self, message):
        """
        Received message parsing procedure.
        Same as in parent class (ZMQL), it receives the "message" as recovered from the receiving socket, and divides
        it in its "subject" and "content". These can be identified as "_responses", or as data candles themselves.
        Inputs:
            >> "message"... The message "evaluated" by the "_receive" method in ZMQL.
        """
        #| Divido el "dict" en el asunto y el contenido del mensaje.
        subject, content = list(message.items())[0]
        #| Derivo el contenido a cada función responsable, acorde al asunto.
        if (subject == "Ticks"): self._response_Ticks(content)
        if (subject == "OHLCV"): self._response_OHLCV(content)
        symbol = subject #| Suponer que el asunto del mensaje es un "symbol".
        if (subject in self.Base.keys()): #| Si cumple, el "content" es un dato de mercado.
            T = pandas.to_datetime(content[0], unit = "s") #| Traducir unix a fecha/hora.
            data = self.Base[symbol] #| Tomar base de datos del "symbol".
            if not data.empty and (T <= data.index[-1]): return #| Descartar datos viejos.
            data.loc[T, :] = content[1:]  #| Si son datos recientes, adjuntarlos a la Data.
            self.Base["_Config"].loc[symbol, "Flag"] = True #| Notificar a las estrategias en "MThink".
            #| Máxima cantidad de filas POR instrumento.
            max_rows = MTrack._MaxRows/len(self.Base)
            #| Borrar excedentes de Data mas antiguos, para no saturar la memoria.
            if (len(data) > max_rows): data = data.iloc[-max_rows:, :]

#### Ante respuestas de solicitudes OHLCV ##############################################################################

    def _response_OHLCV(self, content):
        """
        Received OHLCV response parsing procedure.
        When a message is identified as the notification of MQL4 having stored the requested OHLCVS data inside a CSV
        in "Common Data Folder" ("_CommonPath"), this function retrieves said file and turns it into DataFrame inside
        our data "Base". Notification contents are commonly formatted as: "[symbol, frame, start date, end date]". If
        any of these arrays is a "tuple" (with "()" brackets as delimiters), it implies there has been an error.
        Inputs:
            >> "content"... The array describing the downloaded OHLCVS CSV file.
        """
        symbol, frame, t1, t2 = content #| Usamos los datos del mensaje para identificar el archivo.
        if isinstance(content, tuple): #| Si llegó a haber un error, el mensaje contendría una "tuple".
            error = MTrack._MQErrors[content[-1]] #| Obtenemos la descripción del error desde el listado.
            error = f"(\"{symbol}, {frame}\") -> \"{error}\"." #| Armamos el aviso del error para mostrar.
            if (self.Enable["verbose"] >= 1): #| Si el grado de verbose es 1 o mayor...
                print("((OHLCV)) Warning! MQL error:", error) #| Reportamos el error en pantalla.
            return #| Terminamos la función acá, ya que no existe ningún CSV de tal "content".
        datapath = MTrack._CommonPath + f"OHLCV\\{symbol} {60*frame} {t1} {t2}.csv" #| Ubicación del CSV.
        new_data = pandas.read_csv(datapath, index_col = 0) #| CSV a DataFrame. "Datetime" pasa a ser index.
        new_data.index = pandas.to_datetime(new_data.index) #| Identificamos las marcas de tiempo como fecha/hora.
        #| Descartar última fila (incompleta). Al resto, llevarlo a nuestra Data.
        self.Base[symbol] = self.Base[symbol].copy().append(new_data)

#### Ante respuestas de solicitudes Ticks ##############################################################################

    def _response_Ticks(self, content):
        """
        Received OHLCV response parsing procedure.
        When a message is identified as the notification of data stream being available for a specified "symbol",
        this function acknowledges this and prepares the SUB port for subsequent tick reception. Notification
        contents are commonly formatted as: "[symbol, frame]". If any of these arrays is a "tuple" (with "()"
        brackets as delimiters), it implies there has been an error.
        Inputs:
            >> "content"... The array describing the downloaded OHLCVS CSV file.
        """
        symbol = content[0]
        if isinstance(content, tuple): #| Si hubo algún error por parte de MQL...
            #| Tomar al nº de error al final de "content", y buscar su descripción.
            error = MTrack._MQErrors[content[-1]]
            error = f"\"{symbol}\" -> \"{error}\"."
            #| Mostrar en pantalla, si el grado de "verbose" es 1 o mayor.
            if (self.Enable["verbose"] >= 1): print("((Ticks)) Warning! MQL error:", error)
        
#### Solicitud de datos históricos #####################################################################################

    def download(self, symbol, frame, rows = 10000):
        """
        Function for OHLCVS data download.
        It sends a message with the request for historical market data, and awaits for MQL4 to notify that the
        corresponding CSV file is ready to be imported to "Base". Request must be formulated in MQL4 standards
        ("enum" in minutes, not in seconds). The CSV reading process is done in the background by the parallel
        "_receive" Thread, and "_response_OHLCV" function.
        Inputs:
            >> "symbol"...  Symbol (string) associated with a tradable instrument in MetaTrader.
            >> "frame"...   Timeframe label (string). It must be available in MetaTrader.
            >> "rows"...    Theoretical amount of rows to be downloaded, since actual timestamp. Can result in
                            a lesser amount of them, depending on MetaTrader's storage availability.
        """
        if not (frame in MTrack._TFMT4s):
            print("((Download)) ERROR!", MTrack._TFError2, MTrack._TFMT4s); return
        if not isinstance(rows, int):
            print("((Download)) Number of \"rows\" must be an \"int\".") ; return
        symbol, frame = self._setup_symbol(symbol, frame, "OHLCV") #| Crear dict en "Base" si el "symbol" no existe.
        if (symbol == None) or (frame == None): return #| Ante algún error al ingresar "symbol" o "frame", abandonar.
        enum = MTrack._frame_enum(frame)/60 #| Enum en MTrack se mide en segundos. Enum en MQL se mide en minutos.
        self._send(label = "PUSH", message = f"OHLCV;{symbol};{enum};{rows};;;;;;") #| Armar y enviar mensaje.

#### Solicitud de (de)suscripción a datos ##############################################################################

    def subscribe(self, symbol, frame, slot = 0):
        """
        Function for tick data subscription.
        It sends a message with the request for streaming market data, and awaits for MQL4 to notify that the
        corresponding subscription is available for forward transmission. MQL4's EA features a certain limited
        number of stream lines which we will call "slots". When we subscribe to a new instrument, we occupy one
        new slot. We can subscribe for different symbols until such slots are all busy, or we can replace an
        already filled one with a new "symbol" and "frame" if we wish. The max amount of them is specified in
        the Expert Advisor's panel when initializing ZMQ from MetaTrader.
        Inputs:
            >> "symbol"...  Symbol (string) associated with a tradable instrument in MetaTrader.
            >> "frame"...   Timeframe label (string). It must be available in MetaTrader.
            >> "slot"...    Number of slot in MQL4 "Enable" array. Must be between 0 and the specified max.
        """
        if not isinstance(slot, int) or (slot < 0): #| Verificar que el "slot" sea un int positivo.
            print("((Subscribe)) ERROR!", MTrack._SlotError) ; return
        symbol, frame = self._setup_symbol(symbol, frame, "Ticks") #| Crear dict en "Base" si el "symbol" no existe.
        if (symbol == None) or (frame == None): return #| Ante algún error al ingresar "symbol" o "frame", abandonar.
        for symbol_in in self.Base["_Config"].index: #| Verificar que el "slot" no esté ya ocupado.
            if (self.Base["_Config"].loc[symbol_in, "Slot"] == slot): #| En caso que lo esté por otro "symbol"...
                self.Base["_Config"].loc[symbol_in, "Slot"] = None #| "Reseteo" su status, y prosigo a reemplazarlo.
        self.Base["_Config"].loc[symbol, "Slot"] = slot #| Guardar para seguimiento local, y para desuscribirse mas tarde.
        enum_Py = MTrack._frame_enum(frame) #| Convertir de "frame" en string a enum con las reglas ya planteadas.
        self._send(label = "PUSH", message = f"Ticks;{symbol};{enum_Py};{slot};;;;;;") #| Armar y enviar mensaje.

    def unsubscribe(self, symbol):
        """
        Function for tick data unsubscription.
        The opposite from the "subscribe" function. It will remove the "symbol" from the EA's slot that holds it.
        Inputs:
            >> "symbol"...  Symbol (string) associated with a tradable instrument in MetaTrader.
        """
        if (symbol not in self.Base): return #| No se puede desuscribir de un "symbol" al que nunca me suscribí.
        slot = self.Base["_Config"].loc[symbol, "Slot"] #| Recuperar slot para borrar "symbol" en "Enable" (MQL).
        if (slot >= 0): self._send(label = "PUSH", message = "Ticks;"";0;%d;;;;;;" % slot) #| Armar y enviar mensaje.
        self.Base["_Config"].loc[symbol, "Slot"] = None

#### Archivado de datos ################################################################################################

    def save(self, symbol, x1 = 0, x2 = 1):
        """
        Function for storage of Base data in CSV.
        What is stored inside the data "Base" in the class instance, can be converted to a CSV file. The destination
        folder is "Ticks", and it is located inside the "Common Data Folder" ("_CommonPath") next to "OHLCV" as well.
        Amount of rows to be stored can be specified as well.
        Inputs:
            >> "symbol"...      Symbol (string) associated with a tradable instrument in MetaTrader.
            >> "x1" & "x2"...   Floats between 0 and 1: beginning and end percentage of the DataFrame to be stored.
                                E.g.: to store the middle third, "x1 = 0.33" (33%) and "x2 = 0.67" (67%).
                                      to store the last quarter, "x1 = 0.75" (75%) and "x2 = 1.0" (100%).
        """
        if (symbol[0] == "_") or (symbol not in self.Base) or self.Base[symbol].empty:
            print(f"((Save)) ERROR! Symbol \"{symbol}\" not in store.")
        if not ((0 <= x1 < 1) and (0 < x2 <= 1)):
            print(f"((Save)) ERROR! \"{x1}\" & \"{x2}\" must be between 0 and 1.")
        try: os.makedirs(_CommonPath + "Ticks")
        except: pass
        enum = MTrack._frame_enum(self.Base["_Config"].loc[symbol, "Frame"])
        enum = enum if (0 < enum < 1) else int(enum)
        x1 = round(min(x1, x2)*len(self.Base[symbol]))
        x2 = round(max(x1, x2)*len(self.Base[symbol]))
        data = self.Base[symbol].iloc[x1 : x2, :]
        t1 = round(data.index[x1].timestamp())
        t2 = round(data.index[x2 - 1].timestamp())
        filename = f"Ticks\\{symbol} {enum} {t1} {t2}.csv"
        data.to_csv(MTrack._CommonPath + filename)

#### Unit test al ejecutar este código #################################################################################

if (__name__ == "__main__"):

    from IPython.display import display
    from zmq import Context
    INST = MTrack(Context(), verbose = 2)   #| Crear instancia de "MTrack". Mostrar datos SUB.
    symbol, frame = "BTCUSD", "T5"          #| Instrumento, y marco temporal. Pueden ser "T"icks.
    INST.download(symbol, frame, 100000)    #| Descargar últimas 100 mil velas, o las que haya.
    time.sleep(1)  ;  print("")             #| Darle tiempo a las velas, a que entren a la "Base".
    display(INST.Base)                      #| Mostrar el contenido de "Base", incluyendo "_Config".
    INST.subscribe(symbol, frame, 0)        #| Solicitar suscripción a "symbol"/"frame", en slot 0.
    time.sleep(60*5)                        #| Esperar 5 minutos. Ir viendo todas las velas que llegan.
    display(INST.Base[symbol][-15:])        #| Mostrar el DataFrame resultante, con las últimas 15 velas.
    INST.save(symbol)                       #| Guardar datos recibidos en CSV. Todos, por defecto.
    INST._shutdown()                        #| Eliminar instancia de "MTrack", incluida su Thread.