# Circuito para ESP32 DevKit V1

Este montaje usa tres LEDs indicadores de baja tensión. La cámara y MediaPipe reconocen el gesto en el computador; la ESP32 recibe órdenes por USB serie y controla las salidas. Los tres LEDs muestran juntos el nivel PWM seleccionado; durante las secuencias se encienden uno por uno. Esta versión no conecta sensores flex: los 21 puntos de la mano se detectan con la webcam.

## Materiales

- ESP32 DevKit V1 y cable USB de datos.
- 3 LEDs (por ejemplo, rojo, amarillo y verde).
- 3 resistencias de 220 a 330 ohmios, una por LED.
- Protoboard y cables Dupont.

## Conexiones

Haz el cableado con la ESP32 desconectada del USB. La pata larga del LED es el ánodo (+) y la corta, normalmente junto al lado plano del encapsulado, es el cátodo (-).

| Canal | Salida ESP32 | Recorrido en serie hacia GND |
| --- | --- | --- |
| Luz 1 | GPIO 25 | GPIO 25 → resistencia 220–330 Ω → ánodo LED 1; cátodo → GND |
| Luz 2 | GPIO 26 | GPIO 26 → resistencia 220–330 Ω → ánodo LED 2; cátodo → GND |
| Luz 3 | GPIO 27 | GPIO 27 → resistencia 220–330 Ω → ánodo LED 3; cátodo → GND |

```text
ESP32 GPIO25 ──[220–330 Ω]──|>|── GND   LED 1
ESP32 GPIO26 ──[220–330 Ω]──|>|── GND   LED 2
ESP32 GPIO27 ──[220–330 Ω]──|>|── GND   LED 3
ESP32 GND ───────────────────────────── GND común de la protoboard
```

No unas directamente un GPIO a GND ni conectes LEDs sin resistencia. No conectes la tira o lámpara de potencia de la maqueta directamente a la ESP32: las salidas GPIO son de 3.3 V y poca corriente. Para una carga mayor habrá que diseñar una etapa con MOSFET/transistor y fuente apropiada por separado.

## Cargar el firmware desde Visual Studio Code

1. Instala la extensión **PlatformIO IDE** desde Extensions en VS Code.
2. Abre `13) Reconocimiento_Gestos/firmware` con **File → Open Folder...** o añádela al workspace de VS Code. Si VS Code pregunta si confías en los autores, confirma solo si reconoces esta carpeta.
3. Conecta la placa por USB con un cable de datos. Si Streamlit ya estaba conectado a la ESP32, pulsa **Desconectar ESP32**. Cierra Thonny y cualquier monitor serie que pueda ocupar el COM.
4. Elige **PlatformIO: Build** desde la barra inferior o la paleta `Ctrl+Shift+P`. En el primer Build se descargan la plataforma y el compilador de Espressif; necesita Internet.
5. Cuando Build indique éxito, elige **PlatformIO: Upload**. Selecciona el COM de la ESP32 si hay varios. Si el cargador se queda esperando, mantén `BOOT` al iniciar Upload y suéltalo al comenzar la escritura.
6. Desconecta USB antes de hacer el circuito de la tabla. Verifica polaridad y que cada LED tenga su resistencia en serie; luego vuelve a conectar USB.
7. En Windows, inicia la app con `4) Streamlit/run_app.bat`; en macOS/Linux usa `4) Streamlit/run_app.sh`. Abre `http://localhost:8501` en Chrome o Edge.
8. En la barra lateral de Streamlit elige el COM de la ESP32 y pulsa **Conectar ESP32**. El firmware y la app usan 115200 baudios; no abras ese puerto también en Thonny/Serial Monitor.
9. Pulsa **START** en el reproductor de cámara y concede permiso. Prueba puño, victoria y palma abierta. Los tres LEDs deben cambiar juntos a 30 %, 70 % y 100 %. Pulgar arriba hace 1→2→3 cuatro veces; pulgar abajo hace 3→2→1 cuatro veces. Al terminar una secuencia, las salidas se apagan.

La app Streamlit y el firmware usan el mismo protocolo ASCII, una orden por línea: `PWM:30`, `PWM:70`, `PWM:100`, `SEQ:1`, `SEQ:2`. Cada paso de secuencia dura 170 ms. La imagen original solo menciona dos modos, no define su orden ni duración; estos recorridos son una interpretación inicial. Si PlatformIO muestra `Could not open COM...`, desconecta y reconecta el USB de datos, consulta el nuevo COM en el Administrador de dispositivos, actualiza la lista de puertos de PlatformIO y repite Upload. Asegúrate de que Streamlit/Thonny/Monitor Serie no estén conectados a ese puerto.