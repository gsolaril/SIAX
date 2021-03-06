#property copyright "Copyright SAIX Sep. 2020"
#property link      "https://github.com/gsolaril"
#property version   "1.0"
#property strict

#include <Zmq/Zmq.mqh>
#include <FileTools.mqh>
#include <SymbolTools.mqh>

  //==========================================================================================//
 //  < 0 >  GLOBAL                                                                           //
//==========================================================================================//

//------------------------------------------------------------- Parámetros de Configuración.

input uchar Slots = 10;     // Máxima cantidad de instrumentos para datos de ticks.
input ushort nPUB = 65530;  // Nº puerto socket: PUB/SUB, streaming de datos.
input ushort nPLD = 65531;  // Nº puerto socket: PULL desde Python, Datos
input ushort nPSD = 65532;  // Nº puerto socket: PUSH hacia Python, Datos
input ushort nPLT = 65533;  // Nº puerto socket: PULL desde Python, Trades
input ushort nPST = 65534;  // Nº puerto socket: PUSH desde Python, Trades
input uchar verbose = 2;    // Sin verbose (0), solo comandos (1), comandos & ticks (2).

//---------------------------------------------------------------------- Variables globales.

ulong uS;
string request[10];
Context context("SAIX");
symbolist Symbolist(Slots);
string address = "tcp://*:%d";
// Sockets
Socket PUB(context, ZMQ_PUB);
Socket PLD(context, ZMQ_PULL);
Socket PSD(context, ZMQ_PUSH);
Socket PLT(context, ZMQ_PUSH);
Socket PST(context, ZMQ_PULL);
string Pair[2][2] = {"PLD", "PSD", "PLT", "PST"};

  //==========================================================================================//
 //  < 1 >  SETUP                                                                            //
//==========================================================================================//

//--------------------------------------------------------------------------- Al comenzar...

int OnInit() {

    EventSetMillisecondTimer(1);   context.setBlocky(false);
    
    if (!PUB.bind(StringFormat(address, nPUB))) {
        Print("((INIT)) PUB binding ERROR.");  return(INIT_FAILED); }
    PrintFormat("((INIT)) PUB successfully bound to port %d.", nPUB);
    PUB.setSendHighWaterMark(1);  PUB.setLinger(0);
    
    if (!PLD.bind(StringFormat(address, nPLD))) {
        Print("((INIT)) PLD binding ERROR.");  return(INIT_FAILED); }
    PrintFormat("((INIT)) PLD successfully bound to port %d.", nPLD);
    PLD.setSendHighWaterMark(1);  PLD.setLinger(0);
    
    if (!PSD.bind(StringFormat(address, nPSD))) {
        Print("((INIT)) PSD binding ERROR.");  return(INIT_FAILED); }
    PrintFormat("((INIT)) PSD successfully bound to port %d.", nPSD);
    PSD.setSendHighWaterMark(1);  PSD.setLinger(0);
    
    if (!PLT.bind(StringFormat(address, nPLT))) {
        Print("((INIT)) PLT binding ERROR.");  return(INIT_FAILED); }
    PrintFormat("((INIT)) PLT successfully bound to port %d.", nPLT);
    PLT.setSendHighWaterMark(1);  PLT.setLinger(0);
    
    if (!PST.bind(StringFormat(address, nPST))) {
        Print("((INIT)) PST binding ERROR.");  return(INIT_FAILED); }
    PrintFormat("((INIT)) PST successfully bound to port %d.", nPST);
    PST.setSendHighWaterMark(1);  PST.setLinger(0);
    
    // "OnTimer" se encargará de leer sockets PULL y REP.
    Comment("\nPUB-lishing: []");   return(INIT_SUCCEEDED); }
    
   
//--------------------------------------------------------------------------- Al terminar...

void OnDeinit(const int reason) {
    
    Send("PUB", "{'Shutdown': 'Please wait...'}");
    Send("PSD", "{'Shutdown': 'Please wait...'}");
    Send("PST", "{'Shutdown': 'Please wait...'}");
    PrintFormat("((EXIT)) PUB successfully unbound from port %d.", nPUB);
    PUB.unbind(StringFormat(address, nPUB));
    PUB.disconnect(StringFormat(address, nPUB));
    PrintFormat("((EXIT)) PLD successfully unbound from port %d.", nPLD);
    PLD.unbind(StringFormat(address, nPLD));
    PLD.disconnect(StringFormat(address, nPLD));
    PrintFormat("((EXIT)) PSD successfully unbound from port %d.", nPSD);
    PSD.unbind(StringFormat(address, nPSD));
    PSD.disconnect(StringFormat(address, nPSD));
    PrintFormat("((EXIT)) PLT successfully unbound from port %d.", nPLT);
    PLT.unbind(StringFormat(address, nPLT));
    PLT.disconnect(StringFormat(address, nPLT));
    PrintFormat("((EXIT)) PST successfully unbound from port %d.", nPST);
    PST.unbind(StringFormat(address, nPST));
    PST.disconnect(StringFormat(address, nPST));
    
    context.shutdown();  context.destroy(0);  EventKillTimer(); }
   
  //==========================================================================================//
 //  < 2 >  MAIN                                                                             //
//==========================================================================================//

//------------------------------------------------------------------------------------- Sync

void OnTimer() {

    // Ejecutar OnTick de manera sincrónica también, para compensar los periodos sin ticks.
    if (GetMicrosecondCount() > uS) { OnTick(); } // (cuando el mercado está quieto)
    
    for (int n = 0; n < ArrayRange(Pair, 0); n++) {
        string message = Receive(Pair[n][0]);
        if (message == "") { return; }
        ushort sp = StringGetCharacter(";", 0);
        uchar dim = StringSplit(message, sp, request);
        string received = process(request);
        if (request[0] == "Check") { continue; }
        if (request[0] == "Shutdown") { continue; }
        Send(Pair[n][1], "{" + received + "}"); } }

//------------------------------------------------------------------------------------ Async

void OnTick() {

    uS = GetMicrosecondCount(); // Llevar registro del tiempo desde que arrancó el EA.
    
    for (uchar slot = 0; slot < Slots; slot++) {
        string symbol = Symbolist.Enable[slot];
        if (symbol == "") { continue; }
        Symbolist.update(slot);
        if (verbose > 2) { Symbolist.spy(slot); }
        if (Symbolist.Counts[slot]) { continue; }
        uchar digits = MarketInfo(symbol, MODE_DIGITS);
        string candle = Symbolist.CandleToString(slot);
        string row = StringFormat("{'%s': %s}", symbol, candle);
        Send("PUB", row); } }

  //==========================================================================================//
 //  < 3 >  PROCESS                                                                          //
//==========================================================================================//
    
void Send(string socket, string message) {
    ZmqMsg Message(message); // Traducir a ZMQ.
    bool OK, is_PUB = false;
    if (socket == "PUB") { OK = PUB.send(Message, true); is_PUB = true; }
    if (socket == "PSD") { OK = PSD.send(Message, true); }
    if (socket == "PST") { OK = PST.send(Message, true); }
    if ((verbose <= 0) || ((verbose <= 1) && is_PUB)) { return; }
    string format = (OK? "Sent" : "ERROR! on sending");
    string type = (is_PUB? "market data" : "response");
    PrintFormat("<<%s>> %s %s: %s", socket, format, type, message);
    return; }
    
string Receive(string port) {
    ZmqMsg Message; // Interpretador de mensajes.
    if ((port == "PLD") && (!PLD.recv(Message, true))) { return(""); }
    if ((port == "PLT") && (!PLT.recv(Message, true))) { return(""); }
    if (Message.size() == 0) { return(""); }
    uchar msg_chars[]; // Mensaje de Python, caracter por caracter.
    ArrayResize(msg_chars, Message.size()); // Darle el tamaño para...
    Message.getData(msg_chars); // ...copiar el contenido del mensaje.
    string message = CharArrayToString(msg_chars); // Reconstruir mensaje.
    if (verbose >= 1) { PrintFormat(">>%s<< Received: {%s}", port, message); }
    return(message); }
    
string process(string &message[]) {

    string action = message[0], symbol = message[1];
    double ask = MarketInfo(symbol, MODE_ASK);
    double bid = MarketInfo(symbol, MODE_BID);
    double point = MarketInfo(symbol, MODE_POINT);
    uchar decimals = MarketInfo(symbol, MODE_DIGITS);
    double s_min = MarketInfo(symbol, MODE_STOPLEVEL)*point;
    string answer = StringFormat("'%s': ", action);
    ResetLastError();
    
    // --------------------------------------------------- Probar funcionamiento de puertos.
    if (action == "Check") {
        Send("PUB", "{'Check': 'SUB'}");
        Send("PSD", "{'Check': 'PUSH'}");
        Send("PST", "{'Check': 'PUSH'}"); }
        
    // ------------------------------------------------------------ Abrir orden u operación.
    if (action == "Open") {
        symbol = message[1];
        string comm = message[9];
        uchar type = StringToInteger(message[2]);
        double lot = StringToDouble(message[3]);
        double OP = roundTo(message[4], symbol);
        double SL = roundTo(message[5], symbol);
        double TP = roundTo(message[6], symbol);
        uint magic = StringToInteger(message[8]);
        ushort slip = StringToInteger(message[7]);
        if (type < 2) { OP = type? bid : ask; }
        if (SL != 0) { SL = OP - MathMax(SL, s_min)*MathPow(-1, type); }
        if (TP != 0) { TP = OP + MathMax(TP, s_min)*MathPow(-1, type); }
        uint ticket = OrderSend(symbol, type, lot, OP, slip, SL, TP, comm, magic);
        if (!OrderSelect(ticket, SELECT_BY_TICKET)) {
            answer += StringFormat("('%s', %d, %d)", symbol, magic, _LastError); }
        else {
            string OPs = DoubleToString(OrderOpenPrice(),  decimals);
            string SLs = DoubleToString(OrderStopLoss(),   decimals);
            string TPs = DoubleToString(OrderTakeProfit(), decimals);
            answer += StringFormat("['%s', %d, %.6f, %d, %.2f, %s, %s, %s, %d]",
                      symbol, ticket, NOW(), type, lot, OPs, SLs, TPs, magic); } }
            
    // ----------------------------------------------------------- Cerrar orden u operación.
    if (action == "Close") {
        answer += "[";
        uchar n_order = 0;  bool failed, invalid;
        int number = StringToInteger(message[1]);
        while (n_order < OrdersTotal()) {
            invalid = !OrderSelect(n_order, SELECT_BY_POS);
            if (invalid) { answer += StringFormat("(%d, %d), ", number, _LastError);
                           n_order++; continue; }
            int ticket = OrderTicket(), magic = OrderMagicNumber();
            if ((number > 0) && (number != ticket)) { n_order++; continue; }
            if ((number < 0) && (number != -magic)) { n_order++; continue; }
            double p_value = MarketInfo(OrderSymbol(), MODE_TICKVALUE);
            short points = MathAbs(OrderProfit()/(OrderLots()*p_value));
            double CP = (OrderType() % 2 == 0)? ask : bid;
            if (OrderType() > 1) { failed = !OrderDelete(ticket); }
            else { failed = !OrderClose(ticket, OrderLots(), CP, 1 + points/10); }
            if (failed) { answer += StringFormat("(%d, %d), ", ticket, _LastError);
                          n_order++; continue; }
            answer += StringFormat("[%d, %d], ", ticket, points); }
        answer += "]"; }
                                                             
    // -------------------------------------------------------- Modificar orden u operación.
    if (action == "Modify") {
        uint ticket = StringToInteger(message[1]);
        if (!OrderSelect(ticket, SELECT_BY_TICKET)) {
            answer += StringFormat("(%d, %d)", ticket, _LastError); }
        else {
            symbol = OrderSymbol();
            point = MarketInfo(symbol, MODE_POINT);
            s_min = MarketInfo(symbol, MODE_STOPLEVEL)*point;
            double OP = roundTo(message[2], symbol)*(OrderType() > 1);
            OP = (OP != 0)? OP : OrderOpenPrice();
            double SL = roundTo(message[3], symbol),  SL_prev = OrderStopLoss();
            double TP = roundTo(message[4], symbol),  TP_prev = OrderTakeProfit();
            SL = (SL != 0)? OP - MathMax(SL, s_min)*MathPow(-1, OrderType()) : SL_prev;
            TP = (TP != 0)? OP + MathMax(TP, s_min)*MathPow(-1, OrderType()) : TP_prev;
            if (!OrderModify(ticket, OP, SL, TP, 0)) {
                answer += StringFormat("(%d, %d)", ticket, _LastError); }
            else {
                decimals = MarketInfo(symbol, MODE_DIGITS);
                string OPs = DoubleToString(OrderOpenPrice(),  decimals);
                string SLs = DoubleToString(OrderStopLoss(),   decimals);
                string TPs = DoubleToString(OrderTakeProfit(), decimals);
                answer += StringFormat("[%d, %s, %s, %s]", ticket, OPs, SLs, TPs); } } }
                
    // ------------------------------------------------------- Descarga de datos históricos.
    if (action == "OHLCV") {
        symbol = message[1];
        uint tf = StringToInteger(message[2]);
        uint rows = StringToInteger(message[3]);
        long t1 = CSVdata(symbol, (ENUM_TIMEFRAMES) tf, rows);
        long t2 = (long) iTime(symbol, tf, 1);
        string X_ = (t1 > 0)? "[" : "(";
        string _X = (t1 > 0)? "]" : ")";
        answer += StringFormat("%s'%s', %d, %d, %d%s", X_, symbol, tf, t1, t2, _X); }
                   
    // ------------------------------------------------------- Descarga de especificaciones.
    if (action == "Specs") {
        symbol = message[1];
        answer += StringFormat("['%s', ", symbol);
        decimals = MarketInfo(symbol, MODE_DIGITS);
        for (uchar n_spec = 0; n_spec < ArraySize(Specs); n_spec++) {
            double spec = MarketInfo(symbol, Specs[n_spec]);
            answer += DoubleToString(spec, decimals) + ", "; }
        answer += "]"; }
        
    // --------------------------------------------------------- Descarga de datos de ticks.
    if (action == "Ticks") {
        double tf = StringToDouble(message[2]);
        uchar slot = StringToInteger(message[3]);
        short error = Symbolist.enable(symbol, tf, slot);
        answer += (error == 1)? "['%s', %.1f]" : "('%s', %.1f)";
        answer = StringFormat(answer, symbol, (error == 1)? tf : error);
        string comment = "";
        for (slot = 0; slot < ArraySize(Symbolist.Enable); slot++) {
            symbol = Symbolist.Enable[slot];
            tf = Symbolist.Frames[slot];
            if (symbol == "") { continue; }
            if (tf == 0) { Symbolist.Enable[slot] = "" ; continue; }
            comment += (slot == 0)? "" : ", ";
            comment += StringFormat("(%s, %.1f)", symbol, tf); }
        Comment(StringFormat("\nPUB-lishing: [%s]", comment)); }
        
    // ----------------------------------------------------- Reporte de situación de cuenta.
    if (action == "Account") {
        answer += StringFormat("['%s', ", AccountCompany());
        answer += StringFormat("%d, ",   AccountNumber());
        answer += StringFormat("%d, ", AccountLeverage());
        answer += StringFormat("%.2f, ", AccountBalance());
        double equity = AccountEquity(), margin = AccountMargin();
        answer += StringFormat("%.2f, %.2f, ", equity, margin);
        answer += StringFormat("%.2f]", 100/AccountStopoutLevel()); }
    
    // -------------------------------------------------------- Reporte de órdenes cerradas.
    if (action == "Closed") {
        ulong r1 = StringToInteger(message[1]);
        ulong r2 = StringToInteger(message[2]);
        ulong n_rows = CSVtrades(r1, r2, false);
        answer += StringFormat("[%d, %d, %d]", r1, r2, n_rows); }
    
    // -------------------------------------------------------- Reporte de órdenes abiertas.
    if (action == "Opened") {
        symbol = "";   answer += "[";  
        string which = message[1], entry = message[2];
        long ticket = 0, magic = -1, n = 1;
        if (Symbolist.lookup(entry) >= 0) { symbol = entry; }
        else { n = StringToInteger(entry); }
        if (n > 0) { ticket = n; } else { magic = -n; }
        string row = "['%s', %d, %d, %d, %.2f, %s, %s, %s, %.2f, %d], ";
        for (ushort n_order = 0; n_order < OrdersTotal(); n_order++) {
            if (!OrderSelect(n_order, SELECT_BY_POS)) { continue; }
            if ((OrderType() < 2) != (which == "Active")) { continue; }
            bool filter_m = (magic != OrderMagicNumber());
            bool filter_s = (symbol != OrderSymbol());
            bool filter_t = (ticket != OrderTicket());
            if ((n != 0) && (filter_m && filter_s && filter_t)) { continue; }
            decimals = MarketInfo(symbol, MODE_DIGITS);
            answer += StringFormat(row, OrderSymbol(), OrderTicket(),
                      OrderOpenTime(), OrderType(), OrderLots(),
                      DoubleToString(OrderOpenPrice(),  decimals),
                      DoubleToString(OrderStopLoss(),   decimals), 
                      DoubleToString(OrderTakeProfit(), decimals),
                               OrderProfit(), OrderMagicNumber()); }
            answer += "]"; }
            
    // ----------------------------------------------------------------- Desactivado remoto.
    if (action == "Shutdown") { ExpertRemove(); }    
   
    // -------------------------------------------------------------------------------- Fin.
    return(answer); }