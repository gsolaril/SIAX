#property copyright "Copyright SAIX Sep. 2020"
#property link      "https://github.com/gsolaril"
#property version   "1.0"
#property strict

  //==========================================================================================//
 //  constants                                                                               //
//==========================================================================================//

ushort CONFIG = FILE_READ|FILE_WRITE|FILE_SHARE_WRITE|
       FILE_SHARE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON;
                            
  //==========================================================================================//
 //  Funciones                                                                               //
//==========================================================================================//

// ---------------------------------------------------------------------- Crear archivo CSV.

int CSVnew(string filename) {
        if (FileIsExist(filename, FILE_COMMON)) {
            FileDelete(filename, FILE_COMMON); }
        int fileWrite = FileOpen(filename, CONFIG, ",");
    return(fileWrite); }

// ----------------------------------------------------------- Descarga de especificaciones.

int CSVspecs(ENUM_MARKETINFO &specs[]) {

    string row = "SYMBOL,DIGITS";
    string broker = AccountCompany();
    StringReplace(broker, ".", "");
    string filename = "Specs, " + broker + ".csv";
    int fileWrite = CSVnew(filename);
    ushort symbols = SymbolsTotal(false);
    uchar var = 0, vars = ArraySize(specs);
    for (var = 0; var < vars; var++) {
        ENUM_MARKETINFO spec = specs[var];
        string mode = EnumToString(spec);
        row += "," + StringSubstr(mode, 5); }
    FileWrite(fileWrite, row);
    for (uchar sym = 0; sym < symbols; sym++) {
        string symbol = SymbolName(sym, false);
        uchar digits = MarketInfo(symbol, MODE_DIGITS);
        row = symbol + "," + IntegerToString(digits);
        for (var = 0; var < vars; var++) {
            ENUM_MARKETINFO spec = specs[var];
            double value = MarketInfo(symbol, spec);
            row += "," + DoubleToString(value, digits); }
        FileWrite(fileWrite, row); }
    FileClose(fileWrite);
    return(symbols); }
    
// ----------------------------------------------------------- Descarga de datos de mercado.

int CSVdata(string symbol, uchar frame, datetime t1, datetime t2, bool format = true) {
    
    int n_rows = -1;
    MqlRates OHLCV[];
    string frame_tag = EnumToString((ENUM_TIMEFRAMES) frame);
    frame_tag = StringSubstr(frame_tag, StringLen("PERIOD_"));
    for (int n_try = 0; n_try < 10; n_try++) {
            ResetLastError();
            n_rows = CopyRates(symbol, frame, t1, t2, OHLCV);
            bool OK = (_LastError != 4066) && (_LastError != 4073);
            if ((n_rows > 0) || OK) { break; } else { Sleep(100); } }
    if (n_rows <= 0) { return(-_LastError); }
    n_rows = ArraySize(OHLCV);
    double point = MarketInfo(symbol, MODE_POINT);
    uchar digits = MarketInfo(symbol, MODE_DIGITS);
    uchar spread = MarketInfo(symbol, MODE_SPREAD);
    int fileWrite = CSVnew("OHLCV\\" + symbol + ((format)?
                  StringFormat(" %s %s %s.csv", frame_tag,
                  TimeToString(t1), TimeToString(t2)) :
                  StringFormat(" %d %d %d.csv", frame, t1, t2)));
    for (ushort n_row = 0; n_row < n_rows; n_row++) {
        string timestamp = (format)? TimeToString(OHLCV[n_row].time)
                                : IntegerToString(OHLCV[n_row].time);
        int written = FileWrite(fileWrite, StringFormat(
                   "%s,%s,%s,%s,%s,%d,%d,%s", timestamp,
             DoubleToString(OHLCV[n_row].open,  digits),
             DoubleToString(OHLCV[n_row].high,  digits),
             DoubleToString(OHLCV[n_row].low,   digits),
             DoubleToString(OHLCV[n_row].close, digits),
             IntegerToString(OHLCV[n_row].real_volume),
             IntegerToString(OHLCV[n_row].tick_volume),
             DoubleToString(spread*point, digits))); }
        FileClose(fileWrite);
        return(n_rows); }

// --------------------------------------------------- Descarga de historial de operaciones.

int CSVtrades(datetime st, datetime nd, bool format = true) {
    
    ulong n1, n2, t1, t2, n_rows = 0;
    ushort n_orders = OrdersHistoryTotal();
    bool by_time = (st > 1e6) && (nd > 1e6);
    if (!by_time) {
        st = MathMin(st, n_orders - 2);    n2 = n_orders - (st + 1);
        nd = MathMin(nd, n_orders - 1);    n1 = n_orders - (nd + 0);
        OrderSelect(n1, SELECT_BY_POS, MODE_HISTORY);  t1 = OrderOpenTime();
        OrderSelect(n2, SELECT_BY_POS, MODE_HISTORY);  t2 = OrderCloseTime(); }
    else { t1 = st;   t2 = nd;   n1 = 0;   n2 = n_orders - 1; }
    string st1 = format? TimeToString(t1) : IntegerToString(t1);
    string st2 = format? TimeToString(t2) : IntegerToString(t2);
    int fileWrite = CSVnew("Closed\\" + st1 + " " + st2 + ".csv");
    for (ushort n_trade = n1; n_trade <= n2; n_trade++) {
        OrderSelect(n_trade, SELECT_BY_POS, MODE_HISTORY);
        uchar digits = MarketInfo(OrderSymbol(), MODE_DIGITS);
        double p_value = MarketInfo(OrderSymbol(), MODE_TICKVALUE);
        short points = floor(OrderProfit()/(OrderLots()*p_value));
        ulong OT = OrderOpenTime(), CT = OrderCloseTime();
        bool filter_1 = (OT < t1) && (CT < t1);
        bool filter_2 = (t2 < OT) && (t2 < CT);
        if (by_time && (filter_1 || filter_2)) { continue; }
        n_rows++;
        int written = FileWrite(fileWrite, StringFormat(
        "%d,%s,%d,%d,%d,%.2f,%s,%s,%s,%s,%d,%.2f,%d", OrderTicket(),
                 OrderSymbol(), OT, CT, OrderType(), OrderLots(), 
                       DoubleToString(OrderOpenPrice(),  digits),
                       DoubleToString(OrderClosePrice(), digits),
                       DoubleToString(OrderStopLoss(),   digits),
                       DoubleToString(OrderTakeProfit(), digits),
                       points, OrderProfit(), OrderMagicNumber())); }
    FileClose(fileWrite); return(n_rows); }

  //==========================================================================================//
 //  class                                                                                   //
//==========================================================================================//

