#include <ESP32PWM.h>
#include <ESP32Servo.h>

Servo myServo;

int servoPin = 18;
int val = 0;

void setup() {
  Serial.begin(115200);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  myServo.setPeriodHertz(50);             // Standard servo frequency
  myServo.attach(servoPin, 800, 22000);    // Wider pulse range
}

//void loop() {
  //if (val >= 180)
  //  val = 0;

  //Serial.println(val);
 // myServo.write(val);   // 0–180 mapped to 500–2500 µs
  //val += 1;
 // delay(25);
//}
void loop(){
  for (int pos = 0; pos <= 180; pos += 2
  ) { // goes from 0 degrees to 180 degrees
   // in steps of 1 degree
   myServo.write(pos);              // tell servo to go to position in variable 'pos'
                          // waits 15 ms for the servo to reach the position
  }
 for (int pos = 180; pos >= 0; pos -= 2) { // goes from 180 degrees to 0 degrees
   myServo.write(pos);              // tell servo to go to position in variable 'pos'
                  // waits 15 ms for the servo to reach the position
  }
}
//void loop() {
 // myServo.write(0);
 // delay(500);     // time to reach 0

 // myServo.write(180);  // MG996R is ~120° total anyway
 // delay(1000);     
//}
