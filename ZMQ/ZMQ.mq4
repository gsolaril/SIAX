#property copyright "Copyright SAIX Sep. 2020"
#property link      "https://github.com/gsolaril"
#property version   "1.0"
#property strict

#include <Zmq/Zmq.mqh>
#import "stdlib.ex4"
    string Error(int a0); // DA69CBAFF4D38B87377667EEC549DE5A
#import

  //==========================================================================================//
 //  < 0 >  GLOBAL                                                                           //
//==========================================================================================//

//------------------------------------------------------------- Parámetros de configuración.

extern string ID = "SAIX";
extern int    nPUSH = 32768;
extern int    nPULL = 32769;
extern int    nPUB  = 32770;
extern bool   verbose = false;

//-------------------------------------------------------------------- Estructuras de datos.

enum ENUM_PORTS { PULL = 0, PUSH = 1, PUB = 2 };
string port_labels[3] = {"PULL", "PUSH", "PUB"};

Context context(ID);

class server {
    public: // Atributos.
        bool States[3]; // "true" para puertos activados y funcionando.
        ushort Ports[3]; // Nº de puerto. PULL y PUSH dispuestos al revés de Python.
        string Caches[3]; // Último mensaje contenido en cada socket.
        Socket* Sockets[3]; // Canales para transmisión y recepción de mensajes.
    public: // Constructor.
        server(ushort pull, ushort push, ushort pub) {
            Caches[PULL] = "";  States[PULL] = true;  Ports[PULL] = pull;
            Caches[PUSH] = "";  States[PUSH] = true;  Ports[PUSH] = push;
            Caches[PUB]  = "";  States[PUB]  = true;  Ports[PUB]  = pub;
            Sockets[PULL] = new Socket(context, ZMQ_PULL); // Recepción sincrónica.
            Sockets[PUSH] = new Socket(context, ZMQ_PUSH); // Transmisión sincrónica.
            Sockets[PUB]  = new Socket(context, ZMQ_PUB); } // Transmisión asincrónica.
        bool send(ENUM_PORTS port, string message) { // Enviar string ya armado.
            ZmqMsg Message(message); // Traducir a ZMQ.
            return(Server.Sockets[port].send(Message, true)); } };
            
class symbolist {
    public: // Atributos.
        string Labels[]; short Frames[]; datetime Recent[]; ushort Total;
    public: // Constructor.
        void symbolist() {
            Total = ArrayResize(Labels, SymbolsTotal(false));
            Total = ArrayResize(Frames, SymbolsTotal(false));
            Total = ArrayResize(Recent, SymbolsTotal(false));
            for (ushort symbol = 0; symbol < Total; symbol++) {
                Labels[symbol] = SymbolName(symbol, false);
                Frames[symbol] = 0; Recent[symbol] = 0; } return; }
        short lookup(string label) {
            for (short symbol = 0; symbol < Total; symbol++) {
                if (label == Labels[symbol]) { return(symbol); } }
            return(-1); }
        bool modify(string label, short frame) {
            char symbol = lookup(label);
            if (symbol < 0) { return(false); }
            Frames[symbol] = frame;  return(true); }
        bool update(string label, datetime recent) {
            char symbol = lookup(label);
            if (symbol < 0) { return(false); }
            if (recent <= Recent[symbol]) { return(false); }
            Recent[symbol] = recent;  return(true); } };
            
//---------------------------------------------------------------------- Variables globales.

server Server(nPULL, nPUSH, nPUB);
symbolist Symbolist();  ulong uS;
ushort config = FILE_READ|FILE_WRITE|FILE_SHARE_WRITE|
       FILE_SHARE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON;

  //==========================================================================================//
 //  < 1 >  SETUP                                                                            //
//==========================================================================================//

//--------------------------------------------------------------------------- Al comenzar...

int OnInit() {

    EventSetMillisecondTimer(1); // Función OnTimer se encargará de leer el puerto PULL.
    context.setBlocky(false);    // 
    // Verificar que todos los sockets son correctamente asociados con sus puertos.
    
    for (uchar n = 0; n < 3; n++) {
        string to_address = "tcp://*:" + Server.Ports[n];
        if (Server.Sockets[n].bind(to_address)) {
            Server.Sockets[n].setSendHighWaterMark(1);
            Server.Sockets[n].setLinger(0);
            PrintFormat("[%s] successfully bound to port %d.",
                          port_labels[n], Server.Ports[n]); }
        else {
            PrintFormat("[%s] ERROR on binding socket to port %d.",
                          port_labels[n], Server.Ports[n]);
            return(INIT_FAILED); } }
   
   return(INIT_SUCCEEDED); }
   
//--------------------------------------------------------------------------- Al terminar...

void OnDeinit(const int reason) {

    // Si el EA fue detenido, avisar de ello.
        PrintFormat("[PPP] Connector stopped.");
        Server.send(PUSH, "{'Warning': 'EA stopped'}");

    // Verificar que todos los sockets son correctamente disociados de sus puertos.
    for (uchar n = 0; n < 3; n++) {
        string to_address = "tcp://*:" + Server.Ports[n];
        if (Server.Sockets[n].unbind(to_address)) {
            if (Server.Sockets[n].disconnect(to_address)) {
                PrintFormat("[%s] successfully unbound to port %d.",
                               port_labels[n], Server.Ports[n]); } }
        else {
            PrintFormat("[%s] ERROR on unbinding socket to port %d.",
                               port_labels[n], Server.Ports[n]); } }
   
   // Desconectar ZMQ.
   context.shutdown();
   context.destroy(0);
   EventKillTimer();
   return; }

  //==========================================================================================//
 //  < 2 >  MAIN                                                                             //
//==========================================================================================//

//---------------------------------------------------------------------------------- PUB/SUB

void OnTick() {

    if (_StopFlag) { ExpertRemove(); return; } // Detener si cerró EA.
    uS = GetMicrosecondCount(); // Llevar registro del tiempo desde que arrancó el EA.
    string symbol = "", row = ""; uchar decimals;
    
    for (uchar n_symbol = 0; n_symbol < Symbolist.Total; n_symbol++) {
        if (!Symbolist.Frames[n_symbol]) { continue; }
        symbol = Symbolist.Labels[n_symbol]; MqlTick Tick; 
        if (SymbolInfoTick(symbol, Tick)) {
            if (!Symbolist.update(symbol, Tick.time_msc)) { continue; }
            decimals = MarketInfo(symbol, MODE_DIGITS);
            row = StringFormat("{'%s': [%s, %s, %s, %d]}", symbol,
                                 DoubleToString(Tick.time_msc, 6),
                                 DoubleToString(Tick.bid, decimals),
                                 DoubleToString(Tick.ask, decimals),
                                 IntegerToString(Tick.volume));
            if (Server.send(PUB, row)) {
                if (verbose) { Print("[PUB] Sent tick: " + row); }
            else { Print("[PUB] ERROR sending ticks for " + symbol); } } } } }

//-------------------------------------------------------------------------------- PUSH/PULL

void OnTimer() { 

    if (_StopFlag) { ExpertRemove(); return; } // Detener si cerró EA.
    
    ZmqMsg Request; // Interpretador de mensajes.
    if (!Server.Sockets[PULL].recv(Request, true)) { // Si no puede leerse el puerto PULL...
    if (!Server.Sockets[PULL].recv(Request, false)) { // Ni de inmediato ni con paciencia...
        Print("[PULL] Couldn't read requests from client."); } } // Avisar.

    if (Request.size() > 0) { // Si se leyó contenido en PULL, es porque Python envió algo.
        uchar request_chars[]; // Mensaje de Python, pero caracter por caracter.
        ArrayResize(request_chars, Request.size()); // Darle el tamaño suficiente...
        Request.getData(request_chars); // ...para copiarle el contenido de "Request".
        string request_str = CharArrayToString(request_chars); // Decodificar a string.
        string request[10]; // Array de datos para interpretar el mensaje decodificado.
        uchar n_elements = StringSplit(request_str, StringGetCharacter(";", 0), request);
        if (!Server.send(PUSH, "{" + process(request) + "}")) {
            Print("[PUSH] Couldn't send answers to client."); } }
    
    // Ejecutar OnTick de manera sincrónica también, para compensar los periodos sin ticks.
    if (GetMicrosecondCount() >= uS + 1) { OnTick(); } } // (cuando el mercado está quieto)

  //==========================================================================================//
 //  < 3 >  PROCESS                                                                          //
//==========================================================================================//

double roundTo(string number, string symbol) {
    uchar decimals = MarketInfo(symbol, MODE_DIGITS);
    return(NormalizeDouble(StringToDouble(number), decimals)); }

string process(string &request[]) {

    string action = request[0], symbol = request[1];
    double ask = MarketInfo(symbol, MODE_ASK);
    double bid = MarketInfo(symbol, MODE_BID);
    double point = MarketInfo(symbol, MODE_POINT);
    uchar decimals = MarketInfo(symbol, MODE_DIGITS);
    double s_min = MarketInfo(symbol, MODE_STOPLEVEL)*point;
    string answer = StringFormat("'%s': ", action);
    ResetLastError();

    // --------------------------------------------------- Probar funcionamiento de puertos.
    if (action == "Check") {
        bool ok_push = Server.send(PUSH, "{'Check': 'PUSH'}");
        bool ok_pub = Server.send(PUB, "{'Check': 'PUB'}");
        if (!ok_push) { answer += "['PUSH', 'Error']"; }
        if (!ok_pub)  { answer += "['PUB', 'Error']"; }
        if (ok_push && ok_pub) { answer += "OK!"; } }
        
    // ------------------------------------------------------------ Abrir orden u operación.
    if (action == "Open") {
        string symbol = request[1], comm = request[9];
        uchar type = StringToInteger(request[2]);
        double lot = StringToDouble(request[3]);
        double OP = roundTo(request[4], symbol);
        double SL = roundTo(request[5], symbol);
        double TP = roundTo(request[6], symbol);
        uint magic = StringToInteger(request[8]);
        ushort slip = StringToInteger(request[7]);
        if (type < 2) { OP = type? bid : ask; }
        if (SL != 0) { SL = OP - MathMax(SL, s_min)*MathPow(-1, type); }
        if (TP != 0) { TP = OP + MathMax(TP, s_min)*MathPow(-1, type); }
        uint ticket = OrderSend(symbol, type, lot, OP, slip, SL, TP, comm, magic);
        if (!OrderSelect(ticket, SELECT_BY_TICKET)) {
            answer += StringFormat("('%s', %d, %d)", symbol, magic, _LastError); }
        else {
            datetime OT = IntegerToString(OrderOpenTime());
            string OPs = DoubleToString(OrderOpenPrice(),  decimals);
            string SLs = DoubleToString(OrderStopLoss(),   decimals);
            string TPs = DoubleToString(OrderTakeProfit(), decimals);
            answer += StringFormat("['%s', %d, %d, %d, %.2f, %s, %s, %s, %d]",
                      symbol, ticket, OT, type, lot, OPs, SLs, TPs, magic); } }
            
    // ----------------------------------------------------------- Cerrar orden u operación.
    if (action == "Close") {
        answer += "[";
        uchar n_order = 0;  bool failed, invalid;
        int number = StringToInteger(request[1]);
        while (n_order < OrdersTotal()) {
            invalid = !OrderSelect(n_order, SELECT_BY_POS);
            if (invalid) { answer += StringFormat("(%d, %d), ", number, _LastError);
                           n_order++; continue; }
            int ticket = OrderTicket(), magic = OrderMagicNumber();
            if ((number > 0) && (number != ticket)) { n_order++; continue; }
            if ((number < 0) && (number != -magic)) { n_order++; continue; }
            double p_value = MarketInfo(OrderSymbol(), MODE_TICKVALUE);
            short points = MathAbs(OrderProfit()/(OrderLots()*p_value));
            double CP = (OrderType() % 2)? bid : ask;
            if (OrderType() > 1) { failed = !OrderDelete(ticket); }
            else { failed = !OrderClose(ticket, OrderLots(), CP, 1 + points/10); }
            if (failed) { answer += StringFormat("(%d, %d), ", ticket, _LastError);
                          n_order++; continue; }
            answer += StringFormat("[%d, %d], ", ticket, points); }
        answer += "]"; }
                                                             
    // -------------------------------------------------------- Modificar orden u operación.
    if (action == "Modify") {
        uint ticket = StringToInteger(request[1]);
        if (!OrderSelect(ticket, SELECT_BY_TICKET)) {
            answer += StringFormat("(%d, %d)", ticket, _LastError); }
        else {
            string symbol = OrderSymbol();
            double point = MarketInfo(symbol, MODE_POINT);
            double s_min = MarketInfo(symbol, MODE_STOPLEVEL)*point;
            double OP = roundTo(request[2], symbol)*(OrderType() > 1);
            OP = (OP != 0)? OP : OrderOpenPrice();
            double SL = roundTo(request[3], symbol),  SL_prev = OrderStopLoss();
            double TP = roundTo(request[4], symbol),  TP_prev = OrderTakeProfit();
            SL = (SL != 0)? OP - MathMax(SL, s_min)*MathPow(-1, OrderType()) : SL_prev;
            TP = (TP != 0)? OP + MathMax(TP, s_min)*MathPow(-1, OrderType()) : TP_prev;
            if (!OrderModify(ticket, OP, SL, TP, 0)) {
                answer += StringFormat("(%d, %d)", ticket, _LastError); }
            else {
                uchar decimals = MarketInfo(symbol, MODE_DIGITS);
                string OPs = DoubleToString(OrderOpenPrice(),  decimals);
                string SLs = DoubleToString(OrderStopLoss(),   decimals);
                string TPs = DoubleToString(OrderTakeProfit(), decimals);
                answer += StringFormat("[%d, %s, %s, %s]", ticket, OPs, SLs, TPs); } } }
                
    // ------------------------------------------------------- Descarga de datos históricos.
    if (action == "OHLCV") {
        MqlRates OHLCV[];
        string symbol = request[1];
        datetime t1 = StringToInteger(request[3]);
        datetime t2 = StringToInteger(request[4]);
        ushort frame = StringToInteger(request[2]),  n_rows = 0;
        string frame_tag = EnumToString((ENUM_TIMEFRAMES) frame);
        frame_tag = StringSubstr(frame_tag, StringLen("PERIOD_"));
        string row = "%s" + StringFormat("'%s', '%s', %d, %d",
                       symbol, frame_tag, t1, t2) + ", %d%s";
        for (int n_try = 0; n_try < 10; n_try++) {
            n_rows = CopyRates(symbol, frame, t1, t2, OHLCV);
            bool OK = (_LastError != 4066) && (_LastError != 4073);
            if ((n_rows > 0) || OK) { break; } else { Sleep(100); } }
        if (n_rows <= 0) {
            answer += StringFormat(row, "(", _LastError, ")"); }
        else {
            string file = StringFormat("OHLCV\\%s %d %d %d.csv",
                                        symbol, frame, t1, t2);
            if (FileIsExist(file, 1)) { FileDelete(file); }
            char fileWrite = FileOpen(file, config, ",");
            for (ushort n_row = 0; n_row < n_rows; n_row++) {
                double spread = OHLCV[n_row].spread;
                if (spread == 0) { spread = MarketInfo(symbol, MODE_SPREAD); }
                uint written = FileWrite(fileWrite, StringFormat(
                    "%d,%s,%s,%s,%s,%d,%d,%s", OHLCV[n_row].time,
                    DoubleToString(OHLCV[n_row].open,  decimals),
                    DoubleToString(OHLCV[n_row].high,  decimals),
                    DoubleToString(OHLCV[n_row].low,   decimals),
                    DoubleToString(OHLCV[n_row].close, decimals),
                    IntegerToString(OHLCV[n_row].real_volume),
                    IntegerToString(OHLCV[n_row].tick_volume),
                    DoubleToString(spread*point, decimals))); }
            FileClose(fileWrite);  answer += StringFormat(row, "[", n_rows, "]"); } }
    
    // ------------------------------------------------------- Descarga de especificaciones.
    if (action == "Specs") {
        string symbol = request[1];
        answer += StringFormat("['%s', ", symbol);
        double decimals = MarketInfo(symbol, MODE_DIGITS);
        uchar specs[8] = { MODE_POINT, MODE_DIGITS, MODE_STOPLEVEL, MODE_TICKSIZE,
                           MODE_TICKVALUE, MODE_MINLOT, MODE_LOTSTEP, MODE_MAXLOT };
        for (uchar n_spec = 0; n_spec < ArraySize(specs); n_spec++) {
            double spec = MarketInfo(symbol, specs[n_spec]);
            answer += DoubleToString(spec, decimals) + ", "; }
        answer += "]"; }
        
    // --------------------------------------------------------- Descarga de datos de ticks.
    if (action == "Ticks") {
        uchar n_symbol = 1;   answer += "["; 
        while (n_symbol < ArraySize(request)) {
            symbol = request[n_symbol++];
            PrintFormat("Symbol %d: %s", n_symbol, symbol);
            if (symbol == "(null)") { continue; }
            bool OK = Symbolist.modify(symbol, true);
            OK = OK & Symbolist.update(symbol, TimeCurrent());
            string L = OK? "[" : "(";
            string R = OK? "]" : ")";
            answer += StringFormat("%s'%s'%s, ",
                                  L, symbol, R); } }
        
    // ----------------------------------------------------- Reporte de situación de cuenta.
    if (action == "Funds") {
        answer += StringFormat("['%s', ", AccountCompany());
        answer += StringFormat("%d, ",   AccountNumber());
        answer += StringFormat("%d, ", AccountLeverage());
        answer += StringFormat("%.2f, ", AccountBalance());
        double equity = AccountEquity(), margin = AccountMargin();
        answer += StringFormat("%.2f, %.2f, ", equity, margin);
        answer += StringFormat("%.2f]", 100/AccountStopoutLevel()); }
    
    // -------------------------------------------------------- Reporte de órdenes cerradas.
    if (action == "Closed") {
        ulong n1, n2, t1, t2, output;
        ulong r1 = StringToInteger(request[1]);
        ulong r2 = StringToInteger(request[2]);
        ushort n_orders = OrdersHistoryTotal();
        bool by_time = (r1 > 1e6) && (r2 > 1e6);
        if (!by_time) {
            r1 = MathMin(r1, n_orders - 2);    n2 = n_orders - (r1 + 1);
            r2 = MathMin(r2, n_orders - 1);    n1 = n_orders - (r2 + 0);
            OrderSelect(n1, SELECT_BY_POS, MODE_HISTORY);  t1 = OrderOpenTime();
            OrderSelect(n2, SELECT_BY_POS, MODE_HISTORY);  t2 = OrderCloseTime(); }
        else { t1 = r1;   t2 = r2;   n1 = 0;   n2 = n_orders - 1; }
        string file = StringFormat("Closed\\%d %d.csv", t1, t2);
        if (FileIsExist(file, 1)) { FileDelete(file); }
        char fileWrite = FileOpen(file, config, ",");
        for (ushort n_trade = n1; n_trade <= n2; n_trade++) {
            OrderSelect(n_trade, SELECT_BY_POS, MODE_HISTORY);
            string symbol = OrderSymbol();
            uchar decimals = MarketInfo(symbol, MODE_DIGITS);
            ulong OT = OrderOpenTime(), CT = OrderCloseTime();
            bool filter_1 = (OT < t1) && (CT < t1);
            bool filter_2 = (t2 < OT) && (t2 < CT);
            if (by_time && (filter_1 || filter_2)) { continue; }
            output = FileWrite(fileWrite, StringFormat(
            "%d,%s,%d,%d,%d,%.2f,%s,%s,%s,%s,%.2f,%d", OrderTicket(), 
                        symbol, OT, CT, OrderType(), OrderLots(),
                        DoubleToString(OrderOpenPrice(),  decimals),
                        DoubleToString(OrderClosePrice(), decimals),
                        DoubleToString(OrderStopLoss(),   decimals), 
                        DoubleToString(OrderTakeProfit(), decimals), 
                        OrderProfit(), OrderMagicNumber())); }
        FileClose(fileWrite);
        answer += StringFormat("[%d, %d, %d]", t1, t2, output); }
    
    // -------------------------------------------------------- Reporte de órdenes abiertas.
    if (action == "Opened") {
        string symbol = "";   answer += "[";  
        string which = request[1], entry = request[2];
        long ticket = 0, magic = -1, n = 1;
        if (Symbolist.lookup(entry) >= 0) { symbol = entry; }
        else { n = IntegerToString(entry); }
        if (n > 0) { ticket = n; } else { magic = -n; }
        string row = "['%s', %d, %d, %d, %.2f, %s, %s, %s, %.2f, %d], ";
        for (ushort n_order = 0; n_order < OrdersTotal(); n_order++) {
            if (!OrderSelect(n_order, SELECT_BY_POS)) { continue; }
            if ((OrderType() < 2) != (which == "Active")) { continue; }
            bool filter_m = (magic != OrderMagicNumber());
            bool filter_s = (symbol != OrderSymbol());
            bool filter_t = (ticket != OrderTicket());
            if ((n != 0) && (filter_m && filter_s && filter_t)) { continue; }
            double decimals = MarketInfo(symbol, MODE_DIGITS);
            answer += StringFormat(row, OrderSymbol(), OrderTicket(),
                      OrderOpenTime(), OrderType(), OrderLots(),
                      DoubleToString(OrderOpenPrice(),  decimals),
                      DoubleToString(OrderStopLoss(),   decimals), 
                      DoubleToString(OrderTakeProfit(), decimals),
                               OrderProfit(), OrderMagicNumber()); }
            answer += "]"; }
   
    // --------------------------------------------------------------------------- Reportes.
    if (verbose) { Print("[PUSH] Answer sent... ", answer); }   return(answer); }