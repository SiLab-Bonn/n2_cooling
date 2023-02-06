  /*
------------------------------------------------------------
Copyright (c) All rights reserved
SiLab, Institute of Physics, University of Bonn (modified with other code)
-----------------------------------------------------------
Using the Arduino Nano as temperature sensor via voltage divider and NTC thermistor.
Every analog pin is connected to read the voltage over a thermistor, therefore up to 8
temperature values can be recorded.
*/
#include <Wire.h>
#include "arduino_sht-1.2.2/arduino-sht.h"


//SHTSensor sht;

// To use a specific sensor instead of probing the bus use this command:
 SHTSensor sht(SHTSensor::SHT3X);





// Define constants
const float KELVIN = 273.15; // Kelvin
const int SAMPLE_DELAY_US = 50; // Microseconds delay between two measurement samples
const int NTC_PINS [] = {A0, A1, A2, A3, A4, A5, A6, A7}; // Array of analog input pins on Arduino
int i;
// Default values
const int N_SAMPLES = 20; // Average each temperature value over N_SAMPLES analog reads
const uint16_t SERIAL_DELAY_MILLIS = 1; // Delay between Serial.available() checks
const float NTC_NOMINAL_RES = 10000.0; // Resistance of NTC at 25 degrees C
const float RESISTOR_RES = 12000.0; // Resistance of the resistors in series to the NTC, forming voltage divider
const float TEMP_NOMINAL_DEGREE_C = 25.0; // Nominal temperature for above resistance (almost always 25 C)
const float BETA_COEFFICIENT = 3435.0; // The beta coefficient of the NTC (usually 3000-4000); EPC B57891-M103 NTC Thermistor (geandert)

// Serial related
const char END = '\n';
const uint8_t END_PEEK = int(END); // Serial.peek returns byte as dtype int
const char DELIM = ':';
const char NULL_TERM = '\0';
size_t nProcessedBytes;
const size_t BUF_SIZE = 32;
char serialBuffer[BUF_SIZE]; // Max buffer 32 bytes in incoming serial data


//// Commands
//const char TEMP_CMD = 'T';
//const char RES_CMD = 'Q';
//const char DELAY_CMD = 'D';
//const char SAMPLE_CMD = 'S';
//const char BETA_CMD = 'B';
//const char NOMINAL_RES_CMD = 'O';
//const char NOMINAL_TEMP_CMD = 'C';
//const char RESISTANCE_CMD = 'R';
//const char RESET_CMD = 'X';


// Define variables to be used for calculation
float temperature;
float resistance;
int ntcPin;
bool oneLastProcess;
float temp;
float tempNTC;
float tempSHT;
float humiditySHT;


//Define arrays the average value is calculated with

//Sample Size
const int SIZE=5;
//outputnumber here 3 (tempNTC, tempSHT, humiditySHT)
const int output_number=3;
float tempNTC_mean_array[SIZE];
float tempSHT_mean_array[SIZE];
float humiditySHT_mean_array[SIZE];
String incomingChar;

// Define vars potentially coming in from serial
int nSamples;
uint16_t serialDelayMillis; 
float ntcNominalRes;
float resistorRes;
float tempNominalDegreeC;
float betaCoefficient;


void restoreDefaults(){
  /*
  Resores default values of all variables that potentially come in over serial
  */
  nSamples = N_SAMPLES;
  serialDelayMillis = SERIAL_DELAY_MILLIS;
  ntcNominalRes = NTC_NOMINAL_RES;
  resistorRes = RESISTOR_RES;
  tempNominalDegreeC = TEMP_NOMINAL_DEGREE_C;
  betaCoefficient = BETA_COEFFICIENT;
}


float steinhartHartNTC(float res){
  /*
  Steinhart-Hart equation for NTC: 1/T = 1/T_0 + 1/B * ln(R/R_0)  
  */

  // Do calculation
  temperature = 1.0 / (1.0 / (tempNominalDegreeC + KELVIN) + 1.0 / betaCoefficient * log(res / ntcNominalRes));

  // To Kelvin
  temperature -= KELVIN;
  
  return temperature;
}


float getRes(int ntc){
  /*
  Reads the voltage from analog pin *ntc_pin* in ADC units and converts them to resistance.
  */

  // Reset resitance
  resistance = 0;

  // take N samples in a row, with a slight delay
  for (int i=0; i< nSamples; i++){
    resistance += analogRead(ntc);
    delayMicroseconds(SAMPLE_DELAY_US);
  }

  // Do the average
  resistance /= nSamples;

  // Convert  ADC resistance value to resistance in Ohm
//  PCB multiplikation
  resistance = 1023 / resistance - 1 ;
  resistance = resistorRes / resistance;
  return resistance;
}





float getTemp(int ntc){
  /*
  Reads the voltage from analog pin *ntc_pin* in ADC units and converts them to resistance.
  Returns the temperature calculated from Steinhart-Hart-Equation
  */
  return steinhartHartNTC(getRes(ntc));
}






float printNTCMeasurements(int kind){
  /*
  Read the input buffer, read pins to read and print the respective temp or resistance to serial
  */

    // We only have 8 analog pins
    if (0 <= ntcPin && ntcPin < 8) {
      if (kind == 0) {
        // Send out tempertaure in C, two decimal places, wait
        temp=getTemp(NTC_PINS[ntcPin]);
        }     
}
        
//        else {
//        // Send out resitance in Ohm, two decimal places, wait
//        Serial.println(getRes(NTC_PINS[ntcPin]));
//      }

      
    else {
      // Pin out of range
      Serial.println(999);
    }
  return temp;
}





int read_command(float *Array){
  
  /*
   reads incoming command and chooses than to print a array
   */
  incomingChar = Serial.read();

  // "82" equals a "R"
  if (incomingChar=="82"){
    
    for (int i=0;i<output_number;i++){
    Serial.print(Array[i]);
    Serial.print(" ");
    
      }
      Serial.print("\n");
    }
    
 
  else{
    return 1;
    
    }
  }





float mean_value(float Array[SIZE]){
  /*
    Returns mean value of Array
   */
  
  float sum=0;
  for(int i = 0; i < SIZE; i++){

       sum=sum+Array[i];
    
    }
    return sum/SIZE;
 }


void setup(void){
  //NTC
 restoreDefaults(); // Restore default values
  Serial.begin(115200); // Initialize serial connection
  analogReference(EXTERNAL); // Set 3.3V as external reference voltage instead of internal 5V reference
  delay(500);




  // SHT                               
  Wire.begin();
  Serial.begin(115200);
  delay(10);                   
  sht.init();

  }







  
void loop(void){

//start measurement:
  for (int i=0; i<5; i++){
    
    //the following if statement is needed because sht func needs to call sht.Readsample to update 
    //the sample where it takes the new values from
    
    if (sht.readSample()) {
    tempNTC_mean_array[i]=printNTCMeasurements(0);
    tempSHT_mean_array[i]=sht.getTemperature();
    humiditySHT_mean_array[i]=sht.getHumidity();
    }
    delay(100);
  }
  
  tempNTC=mean_value(tempNTC_mean_array);
  tempSHT=mean_value(tempSHT_mean_array);
  humiditySHT=mean_value(humiditySHT_mean_array);
  float output_array[3]={tempNTC,tempSHT,humiditySHT};
//  Serial.print("TESTING");
  
  if (Serial.available()>0){
    
    read_command(output_array);
    }
}
