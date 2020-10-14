#property copyright "Copyright SAIX Sep. 2020"
#property link      "https://github.com/gsolaril"
#property version   "1.0"
#property strict

#include <GSL/TimeTools.mqh>

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
        ulong Counts[];
        int Frames[];
        double Memory[][8];
        
//----------------------------------------------------------------------------- Constructor.
        
    public: // Constructor.
    
        void symbolist(uchar slots) {
            
            ArrayResize(Enable, slots);  ArrayResize(Memory, slots);
            ArrayResize(Frames, slots);  ArrayInitialize(Frames, 0);
            ArrayResize(Counts, slots);  ArrayInitialize(Counts, 0);
            for (uchar slot = 0; slot < slots; slot++) { Enable[slot] = ""; } }
            
//-------------------------------------------------------------------- Cargador de simbolos.
                
        ushort enable(string symbol, int frame, char slot) {
        
            if ((slot < 0) || (ArraySize(Enable) <= slot)) { return(4002); }
            if (symbol == "") {
                Frames[slot] = 0;   Enable[slot] = "";
                Counts[slot] = 0;   return(1); }
            for (uchar s = 0; s < SymbolsTotal(false); s++) {
                if (SymbolName(s, false) != symbol) { continue; } 
                Enable[slot] = symbol;  Frames[slot] = frame;  return(1); }
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
        
            int frame = Frames[slot];
            if (frame == 0) { return(false); }
            bool by_tick = (frame < 0);
            frame = fabs(frame);  MqlTick Tick;
            string symbol = Enable[slot];
            bool OK = SymbolInfoTick(symbol, Tick);
            if (!OK) { return(false); }
            double spread = Tick.ask - Tick.bid;
            double price = Tick.bid;
            if (Counts[slot] == 0) {
                if (by_tick) { Counts[slot] = frame; }
                else { Counts[slot] = NOW() + frame; }
                Memory[slot][0] = NOW();
                Memory[slot][1] = price;
                Memory[slot][2] = price;
                Memory[slot][3] = price;
                Memory[slot][4] = price;
                Memory[slot][5] = Tick.volume;
                Memory[slot][6] = spread; }
            else {
                Memory[slot][5] += Tick.volume;
                Memory[slot][2] = fmax(Memory[slot][2], price);
                Memory[slot][3] = fmin(Memory[slot][3], price);
                Memory[slot][6] = fmax(Memory[slot][6], spread); }
            bool restart;
            if (by_tick) {
                restart = (--Counts[slot] == 0); }
            else {
                restart = (NOW() >= Counts[slot]); }
            if (!restart) { return(false); }
            Memory[slot][4] = price;
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

        void report() {
        
            string row = "Memory Report '%s': {'F': %d, 'C': %s, 'T': %s,"
                 + "'O': %s, 'H': %s, 'L': %s, 'C': %s, 'V': %d, 'S': %s}";
            for (uchar slot = 0; slot < ArraySize(Enable); slot++) {
                string symbol = Enable[slot];
                if (symbol == "") { continue; }
                double c = Counts[slot];
                int frame = Frames[slot];
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
                PrintFormat(row, symbol, frame, count, T, O, H, L, C, V, S); } } };