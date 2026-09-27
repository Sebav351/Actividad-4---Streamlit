# Hardware Gestos a luz

La aplicación principal ahora es Streamlit y vive en [4) Streamlit](../4%20Streamlit/README.md). Esta carpeta conserva el firmware PlatformIO para la ESP32 DevKit V1 y la guía de cableado.

- Firmware: `firmware/`
- Cableado, carga y seguridad: [CIRCUITO.md](CIRCUITO.md)
- Interfaz, instalación de Python, cámara y ejecución Streamlit: [guía de la app](../4%20Streamlit/README.md)

La app Python envía por USB serie a 115200 baudios `PWM:30`, `PWM:70`, `PWM:100`, `SEQ:1` o `SEQ:2`. Las secuencias recorren los tres LEDs en sentidos contrarios. Son patrones iniciales porque la ilustración no fija orden ni duración.
