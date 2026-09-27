@echo off
setlocal
cd /d "%~dp0"

echo Gestos a luz - inicializador Streamlit

echo.
where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: No se encontro el lanzador py de Python.
  echo Instala Python 3.11 de 64 bits desde https://www.python.org/downloads/ y activa "Add python.exe to PATH".
  pause
  exit /b 1
)

py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.11 no esta instalado.
  echo Instala Python 3.11 de 64 bits desde https://www.python.org/downloads/.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creando el entorno virtual local...
  py -3.11 -m venv .venv
  if errorlevel 1 goto setup_error
)

".venv\Scripts\python.exe" -c "import av, cv2, mediapipe, requests, serial, streamlit, streamlit_webrtc" >nul 2>&1
if errorlevel 1 (
  echo Instalando dependencias, puede tardar unos minutos...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto setup_error
)

echo Abriendo Streamlit en http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run main.py
if errorlevel 1 goto run_error
exit /b 0

:setup_error
echo.
echo ERROR: No se pudo preparar Python o instalar las dependencias.
echo Revisa tu conexion a Internet y el archivo requirements.txt.
pause
exit /b 1

:run_error
echo.
echo Streamlit se detuvo con un error. Revisa el mensaje anterior.
pause
exit /b 1
