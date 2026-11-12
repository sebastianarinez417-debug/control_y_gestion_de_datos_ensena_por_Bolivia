#!/bin/bash
# Doble clic en macOS. La primera vez: clic derecho > Abrir.
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then echo "[ERROR] Instale Python 3.11+ desde https://www.python.org/downloads/"; open https://www.python.org/downloads/; read -p "Pulse Enter para cerrar"; exit 1; fi
"$PY" iniciar.py --internet
read -p "Pulse Enter para cerrar"
