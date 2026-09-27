#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.11 is required. Install it, then run this script again." >&2
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

if ! .venv/bin/python -c 'import av, cv2, mediapipe, requests, serial, streamlit, streamlit_webrtc' >/dev/null 2>&1; then
  echo "Installing application dependencies..."
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python -m streamlit run main.py
