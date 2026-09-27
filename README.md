
# Actividad-4---Streamlit
Sistema de control de iluminación basado en gestos  de la mano
# Gestos a luz

Aplicación para reconocer gestos de la mano con la cámara, visualizar niveles de iluminación y enviar órdenes a una ESP32 DevKit V1.

## Qué hace

La aplicación está construida con Streamlit. La cámara se muestra mediante `streamlit-webrtc` y cada fotograma se procesa con MediaPipe Gesture Recognizer.

El sistema reconoce gestos estándar de MediaPipe y los convierte en acciones:

| Gesto | Acción |
| --- | --- |
| Puño cerrado | Intensidad 30 % |
| Victoria | Intensidad 70 % |
| Palma abierta | Intensidad 100 % |
| Pulgar arriba | Secuencia 1 |
| Pulgar abajo | Secuencia 2 |

Estas asignaciones se pueden cambiar desde la barra lateral de la aplicación.

## Funcionamiento general

1. Streamlit inicia la interfaz web local.
2. `streamlit-webrtc` recibe el video de la cámara.
3. MediaPipe analiza cada fotograma y reconoce el gesto.
4. La aplicación espera varias detecciones estables para evitar activaciones accidentales.
5. La acción aparece en pantalla y, si la ESP32 está conectada, se envía por USB serie a 115200 baudios.
6. La ESP32 ejecuta la orden sobre tres LEDs.

Las órdenes serie son:

```text
PWM:30
PWM:70
PWM:100
SEQ:1
SEQ:2
```

## Ejecutar en Windows

1. Instala Python 3.11 de 64 bits.
2. Abre la carpeta `4) Streamlit`.
3. Ejecuta `run_app.bat`.
4. La primera ejecución crea un entorno virtual, instala las dependencias y descarga el modelo de MediaPipe.
5. Abre `http://localhost:8501` en Chrome o Edge.
6. Pulsa **START** en la cámara y concede permiso.

Después de apagar o reiniciar el computador, ejecuta nuevamente `run_app.bat`. El servidor local no se inicia automáticamente al encender Windows.

## Ejecutar en Linux o macOS Apple Silicon

Desde la carpeta `4) Streamlit`:

```bash
chmod +x run_app.sh
./run_app.sh
```

MediaPipe 1.0.1 no publica wheel para macOS Intel; Windows x64 es la plataforma probada.

## ESP32 y LEDs

El firmware de la placa se encuentra en `13) Reconocimiento_Gestos/firmware`.

| LED | GPIO ESP32 |
| --- | --- |
| LED 1 | GPIO 25 |
| LED 2 | GPIO 26 |
| LED 3 | GPIO 27 |

Cada LED debe conectarse con una resistencia de 220 a 330 ohmios:

```text
GPIO 25 -> resistencia -> LED 1 -> GND
GPIO 26 -> resistencia -> LED 2 -> GND
GPIO 27 -> resistencia -> LED 3 -> GND
```

## Firmware

El firmware se compila con PlatformIO:

1. Instala la extensión PlatformIO IDE en VS Code.
2. Abre `13) Reconocimiento_Gestos/firmware`.
3. Ejecuta **PlatformIO: Build**.
4. Conecta la ESP32 por USB.
5. Cierra Thonny y otros monitores serie.
6. Ejecuta **PlatformIO: Upload**.
7. En Streamlit selecciona el puerto COM y pulsa **Conectar ESP32**.

Funcionamiento: https://youtu.be/IpzNvbCflYA 
