/*
  Asignatura: Sistemas Informáticos en IoT
  Trabajo Final de Asignatura
  Laura Sanz Martín
  MARIA EUGENIA ARAÚJO MARTÍN
  ZHICHENG XUE

*/

#include <WiFi.h>
#include <Wire.h>
#include "SparkFunBME280.h"
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include "BluetoothSerial.h"

BME280 mySensor;
Servo myservo; 
BluetoothSerial SerialBT;

int servoPin = 4; 
int buzzerPin = 16;
int ledPin = 17;
int ldrPin = 34;

//const char* ssid = "ALICESCHARMING";
//const char* password =  "ZPFL2S429FPL";
//const char* ssid = "MIWIFI_2G_jcYD";
//const char* password =  "kkpbxknrcxng";
//const char* ssid = "MIWIFI_EZq9";
//const char* password =  "gmvKz6bX";
const char* ssid = "DIGIFIBRA-ENdt";
const char* password =  "56Pz6sKchxDQ";
//const char* ssid = "UC3M-LABS";
//const char* password =  "Uc3M.L4b.2020";
const String PASSWORD_BT = "1234"; // Definimos password bluetooth


float temperature, altitude, pressure, humidity, light;
uint8_t angle, newAngle;
bool BTClient;

WiFiClient wifi;

float HumidMax = 80.0;
float HumidMin = 20.0;
float TempMax = 30.0;
float TempMin = 20.0;
String server_thresholds="";

unsigned long inicioPuertaAbierta = 0;  
#define TIEMPO_ESPERA 30000 // 30 segundos
#define LightThreshold 1000 

float calculoLux(int luzADC){
  //calculo ftc aproximado según gráfica datasheet LDR
  float m=0.769;
  float b=2.076;
  float volts=(5.0/4095.0)*luzADC;
  float resistance=10000.0*volts/(5.0-volts);
  float lux=pow(pow(10,b) / (resistance/1000), 1/m);
  return lux;
}

void setup()
{
  //Setup sensores y actuadores
  Serial.begin(230400);
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  myservo.setPeriodHertz(50);    // 50 hz servo estándar
  myservo.attach(servoPin, 600, 2400);

  pinMode(buzzerPin, OUTPUT);
  pinMode(ledPin, OUTPUT);
  pinMode(ldrPin, INPUT);

  // Comprobación de que el sensor BME280 funciona correctamente
  Wire.begin();
  while (mySensor.beginI2C() == false) //Comienzo comunicacion I2C
  {
    Serial.println("No hubo respuesta del sensor. Revise el cableado.");
    while(1); //Freeze
  }
  angle = 0; //default puerta está cerrada - angle 0.
  newAngle = 0;
  
  // Wifi Setup
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Conectándose al Wifi..");
  }
  Serial.println("Conectado a la red Wifi.");
  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("Dirección IP asignada: ");
  Serial.println(WiFi.localIP()); //print LAN IP

  //Bluetooth setup
    Serial.println("Inicializando Bluetooth...");

  if (!SerialBT.begin("ESP32_BT")) {
    Serial.println("¡Error al inicializar Bluetooth!");
    while (true); // Detener ejecución en caso de error
  }
  Serial.println("Bluetooth inicializado. Nombre del dispositivo: ESP32_BT");
  SerialBT.println("Introduzca la contraseña");
}

void loop() {
  
  // Lectura sensores -  inicio gestión sensado y monitoreo BME280
  temperature = mySensor.readTempC();
  pressure = mySensor.readFloatPressure();
  altitude = mySensor.readFloatAltitudeMeters();
  humidity = mySensor.readFloatHumidity();
  int lightADC= analogRead(ldrPin);   // a menor valor, más luz
  light=calculoLux(lightADC);

  // gestión de alarmas físicas (buzzer, led) se hace siempre incluso si no hay conexión, para plena seguridad de la caja
  if(temperature>TempMax || temperature<TempMin || humidity > HumidMax || humidity < HumidMin){
    digitalWrite(ledPin, HIGH);
  } else{
    digitalWrite(ledPin, LOW);
  }

  if(light > LightThreshold && newAngle!=90){
    digitalWrite(buzzerPin, HIGH);//hacer que no suene si contraseña enviada
  } else{
    digitalWrite(buzzerPin, LOW);
  }

  
  if (WiFi.status() == WL_CONNECTED) {
    
    JsonDocument doc;

    doc["temperature"] = temperature;
    doc["pressure"] = pressure;
    doc["altitude"] = altitude;
    doc["humidity"] = humidity;
    doc["light"] = light;
    doc["door_angle"] = angle; 

    String json_string;
  
    serializeJson(doc, json_string);

    Serial.println(json_string);

    HTTPClient http;
  
    http.begin("http://192.168.1.130:5000/rt_measurements");   
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(json_string);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print(response);
      Serial.println(" - Código: " + String(httpResponseCode)); //200
    } else {
      Serial.print("Error on sending POST Request: ");
      Serial.println(httpResponseCode);
    }
    
    http.end();

    http.begin("http://192.168.1.130:5000/get_threshold");
    httpResponseCode = http.GET();
    if (httpResponseCode > 0) { // Si la solicitud fue exitosa
      String payload = http.getString(); // Obtener la respuesta
      if(payload!=server_thresholds){
        Serial.println("Respuesta del servidor:");
        Serial.println(payload);
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, payload);
        if (doc["max_temp"]["state"] == "changed") {
          TempMax = doc["max_temp"]["value"];
        }
        if (doc["min_temp"]["state"] == "changed") {
          TempMin = doc["min_temp"]["value"];
        }
  
        if (doc["max_humidity"]["state"] == "changed") {
          HumidMax = doc["max_humidity"]["value"];
        }
  
        if (doc["min_humidity"]["state"] == "changed") {
          HumidMin = doc["min_humidity"]["value"];
        }
        server_thresholds=payload;
      }
    }
    
    http.end();
    // Fin gestión sensado y monitoreo ambiente BME280
  
    // Inicio gestión puerta
    // El motor ajustará su posición a abierto o cerrado según petición cliente
    http.begin("http://192.168.1.130:5000/motor"); 
  
    httpResponseCode = http.GET();
  
    if (httpResponseCode == 200) {
      String doorResponse = http.getString();
      newAngle= doorResponse.toInt();
    }
    http.end(); // Finaliza la conexión
    
  } else {
    Serial.println("Error in WiFi connection");
  }

  //gestión de puerta por BT
  if (SerialBT.available()){ 
    String receivedData = SerialBT.readString(); // Leer el mensaje enviado
    receivedData.trim(); // Eliminar espacios en blanco o saltos de línea
    Serial.print("Contraseña recibida por BT para abrir puerta: ");
    Serial.println(receivedData);

    // Validar la contraseña
    if (receivedData == PASSWORD_BT) {
      
      if(newAngle==90){
        SerialBT.println("La puerta ya está abierta.");
        Serial.println("La puerta ya está abierta.");
      } else {
        Serial.println("¡CORRECTA!");
        SerialBT.println("¡CORRECTA! La puerta se abrirá a continuación.");
        SerialBT.println("Desconéctese para cerrarla.");
        newAngle=90;
      }
      BTClient=true;   
    } else {
      Serial.println("Contraseña incorrecta.");
      SerialBT.println("Contraseña incorrecta.");
    }
  }

  if (!SerialBT.connected() && BTClient==true) {
    if (newAngle == 90) {
      Serial.println("Conexión BT perdida, cerrando la puerta...");
      newAngle = 0;
    }
    BTClient=false;
  }
  
  if(newAngle!=angle){
    myservo.write(newAngle);
    Serial.print("Nueva posición del motor: ");
    Serial.println(newAngle);
    if(newAngle == 90) { 
      // Se inicia contador de puerta abierta
      inicioPuertaAbierta = millis();
    }else{
      inicioPuertaAbierta = 0;
    }
    angle = newAngle;
  }

  // Se cierra la puerta automáticamente tras 30 sec
  if (angle == 90 && ((millis() - inicioPuertaAbierta) >= TIEMPO_ESPERA)) {
    angle = 0;                  
    newAngle = 0;
    inicioPuertaAbierta = 0;
    myservo.write(angle);
    Serial.print("Cerrado automático de seguridad a : ");
    Serial.println(angle);
  }
  // Fin gestión puerta
  
  delay(500);
  
}
