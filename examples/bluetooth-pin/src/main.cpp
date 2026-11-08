#include <Arduino.h>
#include <BluetoothSerial.h>
#include "sdkconfig.h"
#if !defined(CONFIG_AUTOSTART_ARDUINO) || !defined(CONFIG_BT_SPP_ENABLED) || defined(CONFIG_BT_SSP_ENABLED)
#error Use the RCDEV Arduino + ESP-IDF platform
#endif

// Four decimal digits, including leading zeros. Change, rebuild, upload,
// then remove previous pairing on the client before testing the new PIN.
constexpr char BLUETOOTH_PIN[] = "1234";
constexpr char BLUETOOTH_NAME[] = "RCDEV";
BluetoothSerial BT;
bool ready = false;

void setup() {
  Serial.begin(115200);
  ready = BT.setPin(BLUETOOTH_PIN) && BT.begin(BLUETOOTH_NAME);
  if (!ready) {
    BT.end();
    Serial.println("Bluetooth no disponible");
    return;
  }
  Serial.println("RCDEV listo: Bluetooth Classic SPP");
}

void loop() {
  if (!ready) return;
  if (BT.available()) {
    const int c = BT.read();
    Serial.write(c);
    BT.write(c); // Echo
  }
  delay(1);
}
