#property copyright "Copyright SAIX Sep. 2020"
#property link      "https://github.com/gsolaril"
#property version   "1.0"
#property strict

#import "kernel32.dll"
    void GetSystemTime(int& TimeArray[]);
#import

extern uchar Broker_TZ = +3;     // Zona horaria de broker (GMT __).

short GMT_LOCAL = TimeLocal() - TimeGMT();
short GMT_BROKER = Broker_TZ*60*60;
short DELTA = GMT_BROKER - GMT_LOCAL;

  //==========================================================================================//
 //  Functions                                                                               //
//==========================================================================================//

double NOW() {
    int Timer[4];   GetSystemTime(Timer);
    return(TimeGMT() + GMT_BROKER + ((Timer[3] >> 16) % 1000)*1e-3
                             + (GetMicrosecondCount() % 1000)*1e-6); }
                             
string TimeDoubleToString(double time) {
    datetime minutes = 60*floor(time/60);
    double seconds = time - minutes;
    return(TimeToString(minutes) + ":"
         + ((seconds < 10)? "0" : "")
         + DoubleToString(seconds, 6)); }