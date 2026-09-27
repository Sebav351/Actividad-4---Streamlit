from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any

import av
import cv2
import mediapipe as mp
import requests
import serial
import serial.tools.list_ports
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer


st.set_page_config(page_title="Gestos a luz", page_icon="💡", layout="wide")

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)
MODEL_PATH = Path(__file__).parent / "models" / "gesture_recognizer.task"
GESTURES = {
    "Closed_Fist": "Puño cerrado",
    "Open_Palm": "Palma abierta",
    "Pointing_Up": "Señalar arriba",
    "Thumb_Down": "Pulgar abajo",
    "Thumb_Up": "Pulgar arriba",
    "Victory": "Victoria",
    "ILoveYou": "I love you",
}
ACTION_LABELS = {
    "pwm30": "Intensidad 30 %",
    "pwm70": "Intensidad 70 %",
    "pwm100": "Intensidad 100 %",
    "sequence1": "Secuencia modo 1",
    "sequence2": "Secuencia modo 2",
}
DEFAULT_MAPPING = {
    "pwm30": "Closed_Fist",
    "pwm70": "Victory",
    "pwm100": "Open_Palm",
    "sequence1": "Thumb_Up",
    "sequence2": "Thumb_Down",
}
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)


def ensure_model() -> str:
    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 1_000_000:
        return str(MODEL_PATH)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(MODEL_URL, timeout=(10, 120))
    response.raise_for_status()
    temporary_path = MODEL_PATH.with_suffix(".download")
    temporary_path.write_bytes(response.content)
    if temporary_path.stat().st_size < 1_000_000:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError("El archivo descargado no parece ser un modelo MediaPipe válido.")
    temporary_path.replace(MODEL_PATH)
    return str(MODEL_PATH)


class GestureVideoProcessor:
    def __init__(self, model_path: str) -> None:
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.55,
            min_hand_presence_confidence=0.55,
            min_tracking_confidence=0.5,
        )
        self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
        self.inference_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.action_queue: queue.Queue[dict[str, str]] = queue.Queue()
        self.latest: dict[str, Any] = {
            "gesture": "Sin mano detectada",
            "confidence": 0.0,
            "handedness": "Esperando cámara",
            "action": "Sin acción",
        }
        self.threshold = 0.55
        self.mapping = dict(DEFAULT_MAPPING)
        self.candidate = ""
        self.candidate_frames = 0
        self.last_triggered = ""
        self.no_hand_frames = 0
        self.last_timestamp_ms = 0

    def configure(self, threshold: float, mapping: dict[str, str]) -> None:
        with self.state_lock:
            self.threshold = threshold
            self.mapping = dict(mapping)

    def snapshot(self) -> dict[str, Any]:
        with self.state_lock:
            return dict(self.latest)

    def _draw_landmarks(self, image: Any, landmarks: Any) -> None:
        height, width = image.shape[:2]
        points = [(int(point.x * width), int(point.y * height)) for point in landmarks]
        for start, end in HAND_CONNECTIONS:
            cv2.line(image, points[start], points[end], (65, 220, 242), 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(image, point, max(3, width // 180), (80, 110, 255), -1, cv2.LINE_AA)

    def _update_result(self, gesture: str, confidence: float, handedness: str) -> None:
        action: str | None = None
        with self.state_lock:
            if not gesture or gesture == "None":
                self.no_hand_frames += 1
                self.candidate = ""
                self.candidate_frames = 0
                if self.no_hand_frames > 15:
                    self.last_triggered = ""
                self.latest = {
                    "gesture": "Sin mano detectada",
                    "confidence": 0.0,
                    "handedness": "Esperando una mano",
                    "action": self.latest["action"],
                }
                return

            self.no_hand_frames = 0
            self.latest = {
                "gesture": GESTURES.get(gesture, gesture),
                "confidence": confidence,
                "handedness": handedness,
                "action": self.latest["action"],
            }
            if confidence < self.threshold:
                self.candidate = ""
                self.candidate_frames = 0
                return

            if self.candidate == gesture:
                self.candidate_frames += 1
            else:
                self.candidate = gesture
                self.candidate_frames = 1

            if self.candidate_frames >= 5 and gesture != self.last_triggered:
                self.last_triggered = gesture
                action = next(
                    (name for name, mapped_gesture in self.mapping.items() if mapped_gesture == gesture),
                    None,
                )
                if action:
                    self.latest["action"] = ACTION_LABELS[action]

        if action:
            self.action_queue.put({"action": action, "gesture": gesture})

    def process_frame(self, frame: av.VideoFrame) -> av.VideoFrame:
        image = frame.to_ndarray(format="bgr24")
        image = cv2.flip(image, 1)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

        try:
            with self.inference_lock:
                timestamp_ms = max(time.monotonic_ns() // 1_000_000, self.last_timestamp_ms + 1)
                self.last_timestamp_ms = timestamp_ms
                result = self.recognizer.recognize_for_video(mp_image, timestamp_ms)

            if result.gestures and result.gestures[0]:
                category = result.gestures[0][0]
                hand = result.handedness[0][0].category_name if result.handedness else "Mano detectada"
                self._update_result(category.category_name, category.score, hand)
                if result.hand_landmarks:
                    self._draw_landmarks(image, result.hand_landmarks[0])
                display = f"{GESTURES.get(category.category_name, category.category_name)} {category.score:.0%}"
                cv2.putText(image, display, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (225, 245, 225), 2, cv2.LINE_AA)
            else:
                self._update_result("", 0.0, "Esperando una mano")
                cv2.putText(image, "Muestra una mano", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (225, 245, 225), 2, cv2.LINE_AA)
        except Exception as error:
            with self.state_lock:
                self.latest["action"] = f"Error de MediaPipe: {error}"

        return av.VideoFrame.from_ndarray(image, format="bgr24")


def initialize_session() -> None:
    st.session_state.setdefault("mapping", dict(DEFAULT_MAPPING))
    st.session_state.setdefault("threshold", 0.55)
    st.session_state.setdefault("serial_port", None)
    st.session_state.setdefault("active_level", 0)
    st.session_state.setdefault("active_sequence", 0)
    st.session_state.setdefault("sequence_started", 0.0)
    st.session_state.setdefault("last_action", "Todavía no se ha enviado ninguna orden")
    if "gesture_processor" not in st.session_state:
        try:
            with st.spinner("Preparando el modelo MediaPipe (solo la primera vez)..."):
                st.session_state.gesture_processor = GestureVideoProcessor(ensure_model())
        except (requests.RequestException, OSError, RuntimeError) as error:
            st.error(
                "No se pudo preparar el modelo de gestos. Comprueba la conexión a Internet "
                "y vuelve a iniciar la aplicación."
            )
            st.code(str(error))
            st.stop()


def send_pending_actions(processor: GestureVideoProcessor) -> None:
    while True:
        try:
            event = processor.action_queue.get_nowait()
        except queue.Empty:
            break

        action = event["action"]
        st.session_state.last_action = f"{GESTURES[event['gesture']]} → {ACTION_LABELS[action]}"
        if action.startswith("pwm"):
            level = int(action.removeprefix("pwm"))
            st.session_state.active_level = level
            st.session_state.active_sequence = 0
            command = f"PWM:{level}"
        else:
            sequence = 1 if action == "sequence1" else 2
            st.session_state.active_level = 0
            st.session_state.active_sequence = sequence
            st.session_state.sequence_started = time.monotonic()
            command = f"SEQ:{sequence}"

        connection = st.session_state.serial_port
        if connection is not None and connection.is_open:
            try:
                connection.write(f"{command}\n".encode("ascii"))
                st.session_state.last_action += " · enviado a ESP32"
            except serial.SerialException as error:
                st.session_state.last_action += f" · error serie: {error}"


def connect_board(port_name: str) -> None:
    try:
        st.session_state.serial_port = serial.Serial(port_name, 115200, timeout=0.1, write_timeout=1)
        st.session_state.active_level = 0
        st.session_state.active_sequence = 0
        st.session_state.last_action = "ESP32 conectada; salidas apagadas hasta detectar un gesto"
        st.success(f"ESP32 conectada en {port_name} a 115200 baudios.")
    except serial.SerialException as error:
        st.session_state.serial_port = None
        st.error(f"No se pudo abrir {port_name}: {error}. Cierra Thonny/Monitor Serie y vuelve a intentar.")


st.markdown(
    """
    <style>
    .stApp { background: #f3f5f0; color: #202723; }
    .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stWidgetLabel"] { color: #202723; }
    h1, h2, h3 { color: #202723; letter-spacing: -0.03em; }
    [data-testid="stMetric"] { background: #fbfcf8; border: 1px solid #d9dfd7; padding: 12px; }
    div[data-testid="stProgress"] > div { background-color: #e0e6dc; }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_session()
processor: GestureVideoProcessor = st.session_state.gesture_processor

st.title("Gestos a luz")
st.caption("MediaPipe en tiempo real · Streamlit · ESP32 DevKit V1")
st.info("La cámara se procesa en este computador. No se envía video a la ESP32 ni a un servicio externo.", icon="🔒")

with st.sidebar:
    st.header("Asignación de gestos")
    st.session_state.threshold = st.slider("Confianza mínima", 0.40, 0.95, st.session_state.threshold, 0.05)
    mapping: dict[str, str] = {}
    gesture_ids = list(GESTURES)
    for action, label in ACTION_LABELS.items():
        selected = st.selectbox(
            label,
            gesture_ids,
            index=gesture_ids.index(st.session_state.mapping[action]),
            format_func=lambda value: GESTURES[value],
            key=f"select_{action}",
        )
        mapping[action] = selected
    if len(set(mapping.values())) != len(mapping):
        st.warning("Cada acción debe usar un gesto distinto; si se repite, solo se ejecutará la primera coincidencia.")
    st.session_state.mapping = mapping
    processor.configure(st.session_state.threshold, mapping)

    st.divider()
    st.header("Puerto serie ESP32")
    ports = list(serial.tools.list_ports.comports())
    port_choices = {f"{port.device} · {port.description}": port.device for port in ports}
    if port_choices:
        selected_port = st.selectbox("Puerto COM", list(port_choices), key="serial_port_select")
    else:
        selected_port = None
        st.caption("No se detectaron puertos. Conecta la placa por USB y actualiza la página.")

    serial_connection = st.session_state.serial_port
    if serial_connection is not None and serial_connection.is_open:
        st.success(f"Conectada: {serial_connection.port}")
        if st.button("Desconectar ESP32", use_container_width=True):
            serial_connection.close()
            st.session_state.serial_port = None
            st.rerun()
    elif selected_port is not None and st.button("Conectar ESP32", type="primary", use_container_width=True):
        connect_board(port_choices[selected_port])
        if st.session_state.serial_port is not None:
            st.rerun()

    st.caption("Protocolo: PWM:30 / PWM:70 / PWM:100 / SEQ:1 / SEQ:2 · 115200 baudios")


@st.fragment(run_every="300ms")
def live_dashboard() -> None:
    current_processor: GestureVideoProcessor = st.session_state.gesture_processor
    send_pending_actions(current_processor)

    camera_column, result_column = st.columns([1.7, 0.8], gap="large")
    with camera_column:
        st.subheader("Cámara en vivo")
        webrtc_streamer(
            key="gesture-camera",
            mode=WebRtcMode.SENDRECV,
            video_frame_callback=current_processor.process_frame,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        st.caption("Pulsa START en el reproductor y concede permiso para usar la cámara.")

    snapshot = current_processor.snapshot()
    with result_column:
        st.subheader("Reconocimiento")
        st.metric("Gesto", snapshot["gesture"])
        st.metric("Confianza", f"{snapshot['confidence']:.0%}")
        st.caption(snapshot["handedness"])
        st.markdown("**Última acción**")
        st.write(st.session_state.last_action)

    st.divider()
    st.subheader("Respuesta de luces")
    st.caption("Los tres LEDs indicadores comparten el nivel PWM; las secuencias los recorren uno por uno.")
    level_columns = st.columns(3)
    for column, level, color in zip(level_columns, (30, 70, 100), ("🟡", "🔵", "🔴")):
        with column:
            st.metric(f"{color} Intensidad {level} %", "ACTIVA" if st.session_state.active_level == level else "—")
            st.progress(level if st.session_state.active_level == level else 0)

    sequence = st.session_state.active_sequence
    elapsed = time.monotonic() - st.session_state.sequence_started
    if sequence and elapsed >= 2.04:
        st.session_state.active_sequence = 0
        sequence = 0
    if sequence:
        step = int(elapsed / 0.17) % 3
        lit_led = step + 1 if sequence == 1 else 3 - step
        st.success(f"Secuencia modo {sequence} en ejecución · LED {lit_led} de 3")
    elif st.session_state.active_level:
        st.success(f"Modo PWM activo: {st.session_state.active_level} %")
    else:
        st.caption("Sin salida activa")


live_dashboard()

st.divider()
st.caption("Gestos configurables: puño → 30 %, victoria → 70 %, palma abierta → 100 %, pulgar arriba/abajo → secuencias 1/2.")
