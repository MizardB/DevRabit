# 🤖 RCDEV (Robótica Competitiva Developer)

Plataforma de desarrollo para **PlatformIO** orientada a robótica competitiva sobre **ESP32 DOIT DevKit V1**, con **Arduino + ESP-IDF** y servidor **Bluetooth Classic SPP**. El soporte documentado se limita a esta placa, combinación de frameworks y modo servidor; no incluye otras variantes ESP32, BLE ni modo SPP maestro.

[![PlatformIO](https://img.shields.io/badge/PlatformIO-Core%206%2B-orange.svg)](https://platformio.org/)
[![Framework](https://img.shields.io/badge/Framework-Arduino%202.0.17%20%2B%20ESP--IDF%204.4.7-blue.svg)](https://github.com/espressif/arduino-esp32)
[![OS](https://img.shields.io/badge/OS-Windows%2011%20%7C%20Linux%20%7C%20NixOS-green.svg)](#-compatibilidad)
[![License](https://img.shields.io/badge/License-MIT%20%2F%20Apache--2.0-lightgrey.svg)](LICENSE)

---

## ❓ ¿Por qué existe RCDEV?

En robótica competitiva (fútbol de robots, velocistas, minisumo, etc.), la comunicación serial inalámbrica con mandos y terminales debe ser rápida, directa y sin fallos de emparejamiento.

En la plataforma oficial de Espressif (`espressif32`):
1. El SDK de ESP-IDF viene preconfigurado con **SSP (Secure Simple Pairing)** activado de forma obligatoria.
2. Al estar SSP activo, **`BluetoothSerial.setPin()` no funciona**: la pila Bluetooth rechaza o ignora el PIN numérico de 4 dígitos y busca métodos de autenticación modernos o dinámicos incompatibles con muchos mandos y terminales SPP.
3. Usar `#define` o macros en tu sketch de Arduino no lo soluciona, ya que la pila Bluetooth de ESP-IDF viene precompilada en las librerías oficiales.

### La solución de RCDEV
RCDEV reconstruye el entorno con **SSP desactivado** a nivel de SDK y adapta internamente `BluetoothSerial` para que puedas usar un PIN numérico clásico fijo de 4 dígitos (`"0000"` a `"9999"`) de forma nativa sobre Arduino y ESP-IDF, sin configuraciones complejas de `menuconfig`.

---

## 💻 Compatibilidad

* 🪟 **Windows 11**: Validado manualmente por el mantenedor en placa real: emparejamiento con PIN correcto, rechazo del PIN incorrecto y comunicación SPP con eco.
* 🐧 **Linux & NixOS**: Uso desde terminal (`pio run`) o VS Code con PlatformIO; esto no implica validación de emparejamiento en hardware.

---

## 🚀 Inicio Rápido (Solo 2 archivos)

Para usar RCDEV en tu proyecto, no necesitas clonar este repositorio ni escribir archivos CMake. Solo crea un proyecto en PlatformIO y coloca estos dos archivos:

### 1. `platformio.ini`

```ini
[platformio]
default_envs = rcdev

[env:rcdev]
platform = https://github.com/MizardB/RCDEV/archive/refs/tags/v0.1.0.zip
board = esp32doit-devkit-v1
framework = arduino, espidf
monitor_speed = 115200
upload_speed = 921600
board_build.esp-idf.sdkconfig_path = .pio/build/rcdev/sdkconfig
```

> **Nota para desarrollo local:** Si estás modificando la propia plataforma en tu equipo, puedes usar `platform = symlink://<ruta-a-la-plataforma>`.

---

### 2. `src/main.cpp`

```cpp
#include <Arduino.h>
#include <BluetoothSerial.h>

// PIN legacy: exactamente 4 dígitos decimales ("0000" a "9999")
constexpr char BLUETOOTH_PIN[] = "9876";
constexpr char BLUETOOTH_NAME[] = "RCDEV";

BluetoothSerial BT;
bool ready = false;

void setup() {
  Serial.begin(115200);

  // IMPORTANTE: setPin() DEBE ejecutarse antes de begin()
  ready = BT.setPin(BLUETOOTH_PIN) && BT.begin(BLUETOOTH_NAME);
  if (!ready) {
    BT.end();
    Serial.println("❌ Error: Bluetooth no disponible o PIN invalido.");
    return;
  }

  Serial.printf("✅ Bluetooth listo: '%s' con PIN '%s'\n", BLUETOOTH_NAME, BLUETOOTH_PIN);
}

void loop() {
  if (!ready) return;

  // Eco bidireccional Bluetooth <-> Monitor Serial
  if (BT.available()) {
    const int c = BT.read();
    Serial.write(c);
    BT.write(c);
  }

  if (Serial.available()) {
    const int c = Serial.read();
    BT.write(c);
  }

  delay(1);
}
```

---

## 🛠️ Comandos útiles

Desde la terminal en la carpeta de tu proyecto (o la terminal de PlatformIO):

```bash
# Compilar el proyecto
pio run

# Subir a la placa (sustituye COM5 por tu puerto serie real)
pio run -t upload --upload-port COM5

# Abrir el monitor serial
pio device monitor --baud 115200
```

---

## ⚠️ Reglas importantes del PIN

* **Exactamente 4 dígitos decimales:** Admite cualquier combinación de 4 números (como `"1234"`, `"9876"` o `"0000"`). Cualquier longitud distinta o carácter no numérico hace que `setPin()` retorne `false`; el ejemplo comprueba ese resultado y no inicia Bluetooth si falla.
* **Orden de llamada:** `BT.setPin()` debe ejecutarse **antes** de `BT.begin()`.
* **Seguridad:** El PIN legacy de 4 dígitos busca compatibilidad, no ofrece seguridad fuerte.
* **Dispositivos previamente vinculados:** Cambiar el PIN no necesariamente revoca los vínculos guardados. **Desvincula/olvida el dispositivo** en tu teléfono o PC antes de volver a emparejarlo con el PIN nuevo.

---

<details>
<summary>🔍 Detalles de arquitectura interna (Avanzado)</summary>

### Integración CMake
Al compilar por primera vez, RCDEV genera automáticamente la configuración CMake requerida en la raíz y en `src/`:
* Incluye `secure-spp.cmake` después de `project()` para aplicar la configuración de seguridad SPP.
* Registra el componente Arduino de forma dinámica (`${RCDEV_ARDUINO_COMPONENT}`).
* Previene que PlatformIO compile una copia duplicada o no parcheada de `BluetoothSerial`.

### Verificación y tests en host
Para desarrolladores de la plataforma en entornos Linux/host (Python 3 + g++):
```bash
pio run -d examples/bluetooth-pin
python3 -B tests/check-build.py examples/bluetooth-pin/.pio/build/rcdev \
  ~/.platformio/packages/framework-arduinoespressif32/libraries/BluetoothSerial/src/BluetoothSerial.cpp
```
</details>

---

## 📄 Licencia

* Código propio de RCDEV: [MIT](LICENSE).
* Código base de PlatformIO adaptado: [Apache-2.0](LICENSE.platformio).
