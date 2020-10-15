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

extern string ID = "SAIX";    // Nómbre del proyecto.
extern uchar Slots = 10;      // Máxima cantidad de instrumentos para datos de ticks.
extern ushort nPULL = 32768;  // Número de canal "Python a MetaTrader".
extern ushort nPUSH = 32769;  // Número de canal "MetaTrader a Python".
extern ushort nPUB  = 32770;  // Número de canal de datos asincrónicos.
extern uchar verbose = 2;     // Sin verbose (0), solo comandos (1), comandos & ticks (2).

//---------------------------------------------------------------------- Variables globales.

ulong uS;
string request[10];
Context context(ID);
symbolist Symbolist(Slots);
string address = "tcp://*:%d";
Socket PUSH(context, ZMQ_PUSH);
Socket PULL(context, ZMQ_PULL);
Socket PUB(context, ZMQ_PUB);

  //==========================================================================================//
 //  < 1 >  SETUP                                                                            //
//==========================================================================================//

//--------------------------------------------------------------------------- Al comenzar...

int OnInit() {

    EventSetMillisecondTimer(1);   context.setBlocky(false);
    
    if (!PULL.bind(StringFormat(address, nPULL))) {
        PrintFormat("(PULL) Binding ERROR.");   return(INIT_FAILED); }
    PrintFormat("[PULL] successfully bound to port %d.", nPULL);
    PULL.setSendHighWaterMark(1);   PULL.setLinger(0);
    
    if (!PUSH.bind(StringFormat(address, nPUSH))) {
        PrintFormat("(PUSH) Binding ERROR.");   return(INIT_FAILED); }
    PrintFormat("[PUSH] successfully bound to port %d.", nPUSH);
    PUSH.setSendHighWaterMark(1);   PUSH.setLinger(0);
    
    if (!PUB.bind(StringFormat(address, nPUB))) {
        PrintFormat("(PUB) Binding ERROR.");   return(INIT_FAILED); }
    PrintFormat("[PUB] successfully bound to port %d.", nPUB);
    PUB.setSendHighWaterMark(1);    PUB.setLinger(0);
            
    // Función OnTimer se encargará de leer el puerto PULL.
    return(INIT_SUCCEEDED); }
    
   
//--------------------------------------------------------------------------- Al terminar...

void OnDeinit(const int reason) {
    
    Send("PUSH", "{'Shutdown': 'Please wait...'}");
    PrintFormat("[PULL] successfully unbound from port %d.", nPULL);
    PULL.unbind(StringFormat(address, nPULL));
    PULL.disconnect(StringFormat(address, nPULL));
    PrintFormat("[PUSH] successfully unbound from port %d.", nPUSH);
    PUSH.unbind(StringFormat(address, nPUSH));
    PUSH.disconnect(StringFormat(address, nPUSH));
    PrintFormat("[PUB] successfully unbound from port %d.", nPUB);
    PUB.unbind(StringFormat(address, nPUB));
    PUB.disconnect(StringFormat(address, nPUB));
    context.shutdown();
    context.destroy(0);
    EventKillTimer(); }
   
  //==========================================================================================//
 //  < 2 >  MAIN                                                                             //
//==========================================================================================//

uint nnn = 0;

//-------------------------------------------------------------------------------- PUSH/PULL

void OnTimer() {

    if (_StopFlag) {
        ExpertRemove(); return; } // Detener si cerró EA.
    // Ejecutar OnTick de manera sincrónica también, para compensar los periodos sin ticks.
    if (GetMicrosecondCount() > uS) { OnTick(); } // (cuando el mercado está quieto)
    
    string message = Receive();
    if (message == "") { return; }
    uchar n_elements = StringSplit(message, StringGetCharacter(";", 0), request);
    if (!Send("PUSH", "{" + process(request) + "}")) {
        Print("(PUSH) Couldn't send answers to client."); } }

//---------------------------------------------------------------------------------- PUB/SUB

void OnTick() {

    if (_StopFlag) {
        ExpertRemove(); return; } // Detener si cerró EA.
    uS = GetMicrosecondCount(); // Llevar registro del tiempo desde que arrancó el EA.
    
    for (uchar slot = 0; slot < Slots; slot++) {
        string symbol = Symbolist.Enable[slot];
        if (symbol == "") { continue; }
        if (!Symbolist.update(slot)) { continue; }
        uchar digits = MarketInfo(symbol, MODE_DIGITS);
        string candle = Symbolist.CandleToString(slot);
        string row = StringFormat("{'%s': %s}", symbol, candle);
        if (Send("PUB", row)) {
            if (verbose >= 2) { Print("[PUB] Sent tick: " + row); } }
        else {
            Print("(PUB) ERROR sending ticks for " + symbol); } } }

  //==========================================================================================//
 //  < 3 >  PROCESS                                                                          //
//==========================================================================================//
    
bool Send(string port, string message) {
    ZmqMsg Message(message); // Traducir a ZMQ.
    if (port == "PUSH") { return(PUSH.send(Message, true)); }
    if (port == "PUB") { return(PUB.send(Message, true)); }
    return(false); }
    
string Receive() {
    ZmqMsg Message; // Interpretador de mensajes.
    if (!PULL.recv(Message, true) || (Message.size() <= 0)) { return(""); }
    uchar msg_chars[]; // Mensaje de Python, caracter por caracter.
    ArrayResize(msg_chars, Message.size()); // Darle el tamaño para...
    Message.getData(msg_chars); // ...copiar el contenido del mensaje.
    string message = CharArrayToString(msg_chars); // Reconstruir mensaje.
    if (verbose >= 1) { PrintFormat("[PULL] Received: {%s}", message); }
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
        answer += Send("PUB", "{'Check': 'SUB'}")? "[['SUB'], " : "[('SUB'), ";
        answer += Send("PUSH", "{'Check': 'PULL'}")? "['PULL']]" : "('PULL')]"; }
        
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
        MqlRates Data[];
        symbol = message[1];
        ushort frame = StringToInteger(message[2]);
        datetime t1 = StringToDouble(message[3]) + GMT_BROKER;
        datetime t2 = StringToDouble(message[4]) + GMT_BROKER;
        string frame_tag = EnumToString((ENUM_TIMEFRAMES) frame);
        frame_tag = StringSubstr(frame_tag, StringLen("PERIOD_"));
        int n_rows = CSVdata(symbol, frame, t1, t2, false);
        string X_ = (n_rows > 0)? "[" : "(";
        string _X = (n_rows > 0)? "]" : ")";
        answer += StringFormat("%s'%s', %d, %d, %d, %d%s", X_,
                     symbol, frame, t1, t2, fabs(n_rows), _X); }
                   
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
        int frame = StringToInteger(message[2]);
        uchar slot = StringToInteger(message[3]);
        short error = Symbolist.enable(symbol, frame, slot);
        answer += (error == 1)? "['%s', %d]" : "('%s', %d)";
        answer = StringFormat(answer, symbol, (error == 1)? frame : error); }
        string comment = "";
        for (uchar slot = 0; slot < ArraySize(Symbolist.Enable); slot++) {
            symbol = Symbolist.Enable[slot];
            int frame = Symbolist.Frames[slot];
            if (symbol == "") { continue; }
            comment += (slot == 0)? "" : ", ";
            comment += "(" + symbol + ", " + frame + ")" ; }
        Comment(StringFormat("\nSUB-scribed to: [%s]", comment));
        
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
   
    // --------------------------------------------------------------------------- Reportes.
    if ((verbose >= 1) || (action == "Check")) {Print("[PUSH] Answer sent... ", answer); }
    return(answer); }           