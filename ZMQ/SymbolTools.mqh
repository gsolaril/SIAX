#property copyright "Copyright SAIX Sep. 2020"
#property link      "https://github.com/gsolaril"
#property version   "1.0"
#property strict

#include <TimeTools.mqh>

  //==========================================================================================//
 //  constants                                                                               //
//==========================================================================================//

ENUM_MARKETINFO Specs[] = { MODE_POINT, MODE_STOPLEVEL, MODE_TICKSIZE, MODE_LOTSIZE,
                            MODE_TICKVALUE, MODE_MINLOT, MODE_LOTSTEP, MODE_MAXLOT };
                            
  //==========================================================================================//
 //  functions                                                                               //
//==========================================================================================//

double roundTo(string number, string symbol) {
    uchar decimals = MarketInfo(symbol, MODE_DIGITS);
    return(NormalizeDouble(StringToDouble(number), decimals)); }

  //==========================================================================================//
 //  class SYMBOLIST                                                                         //
//==========================================================================================//

class symbolist {

//------------------------------------------------------------------------------- Atributos.

    public:
    
        string Enable[];
        double Counts[];
        double Frames[];
        double Memory[][8];
        
//----------------------------------------------------------------------------- Constructor.
        
    public: // Constructor.
    
        void symbolist(uchar slots) {
            
            ArrayResize(Enable, slots);  ArrayResize(Memory, slots);
            ArrayResize(Frames, slots);  ArrayInitialize(Frames, 0);
            ArrayResize(Counts, slots);  ArrayInitialize(Counts, 0);
            for (uchar slot = 0; slot < slots; slot++) { Enable[slot] = ""; } }
            
//-------------------------------------------------------------------- Cargador de simbolos.
                
        ushort enable(string symbol, double tf, char slot) {
        
            if ((slot < 0) || (ArraySize(Enable) <= slot)) { return(4002); }
            if (symbol == "") {
                Frames[slot] = 0;   Enable[slot] = "";
                Counts[slot] = 0;   return(1); }
            for (uchar s = 0; s < SymbolsTotal(true); s++) {
                if (SymbolName(s, true) != symbol) { continue; }
                Enable[slot] = symbol;  Frames[slot] = tf;  return(1); }
            return(4106); }
            
//-------------------------------------------------------------------- Buscador de simbolos.
            
        char lookup(string symbol) {
        
            for (uchar s = 0; s < ArraySize(Enable); s++) {
                if (symbol == Enable[s]) { return(s); } }
            return(-1); }
            
//------------------------------------------------------------------ Cambiar marco temporal.
            
        void reframe(string symbol, short frame) {
        
            char slot = lookup(symbol);
            if (slot < 0) { return; }
            Frames[slot] = frame; }
            
//-------------------------------------------------------------- Actualizar datos guardados.
                
        bool update(uchar slot) {
            double tf = Frames[slot];
            if (tf == 0) { return(false); }
            string symbol = Enable[slot];
            if (symbol == "") { return(false); }
            double A = SymbolInfoDouble(symbol, SYMBOL_ASK);
            double B = SymbolInfoDouble(symbol, SYMBOL_BID);
            long V = SymbolInfoInteger(symbol, SYMBOL_VOLUME);
            if (Counts[slot] == 0) {
                if (tf < 0) {
                    Counts[slot] = tf;
                    Memory[slot][0] = NOW(); }
                else {
                    long units = floor(NOW()/tf);
                    Counts[slot] = tf*(units + 1);
                    Memory[slot][0] = tf*units; }
                Memory[slot][1] = B;  Memory[slot][4] = B;
                Memory[slot][2] = B;  Memory[slot][5] = 1;
                Memory[slot][3] = B;  Memory[slot][6] = A - B; }
            else {
                Memory[slot][5] += 1;
                Memory[slot][2] = fmax(Memory[slot][2], B);
                Memory[slot][3] = fmin(Memory[slot][3], B);
                Memory[slot][6] = fmax(Memory[slot][6], A - B); }
            bool restart;
            if (tf < 0) {
                restart = (++Counts[slot] == 0); }
            else {
                restart = (NOW() >= Counts[slot]); }
            if (!restart) { return(false); }
            Memory[slot][4] = B;
            Counts[slot] = 0;
            return(true); }
            
//---------------------------------------------------------------- Convertir vela en string.

        string CandleToString(uchar slot) {
        
            uchar digits = MarketInfo(Enable[slot], MODE_DIGITS);
            return("[" + DoubleToString(Memory[slot][0], 6) + ","
                  + DoubleToString(Memory[slot][1], digits) + ","
                  + DoubleToString(Memory[slot][2], digits) + ","
                  + DoubleToString(Memory[slot][3], digits) + ","
                  + DoubleToString(Memory[slot][4], digits) + ","
                  + IntegerToString(floor(Memory[slot][5])) + ","
                  + DoubleToString(Memory[slot][6], digits) + "]"); }
        
//-------------------------------------------------------- Imprimir vela parcial en consola.

        void spy(uchar slot) {
        
            string symbol = Enable[slot];   if (symbol == "") return;
            int frame = Frames[slot];       if (frame == 0) return;
            string row = "Memory Report '%s': {'F': %d, 'T': %s, 'O': %s, "
                 + "'H': %s, 'L': %s, 'C': %s, 'V': %d, 'S': %s}. Next: %s";
            double c = Counts[slot];
            bool by_tick = (frame < 0);
            double time = Memory[slot][0];
            string T = TimeDoubleToString(time);
            string count = TimeDoubleToString(c);
            if (by_tick) { count = IntegerToString(c); }
            uchar digits = MarketInfo(symbol, MODE_DIGITS);
            string O = DoubleToString(Memory[slot][1], digits);
            string H = DoubleToString(Memory[slot][2], digits);
            string L = DoubleToString(Memory[slot][3], digits);
            string C = DoubleToString(Memory[slot][4], digits);
            string V = DoubleToString(Memory[slot][5], digits);
            string S = DoubleToString(Memory[slot][6], digits);
            PrintFormat(row, symbol, frame, T, O, H, L, C, V, S, count); } };