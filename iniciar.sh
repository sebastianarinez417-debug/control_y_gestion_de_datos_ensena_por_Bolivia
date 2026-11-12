#!/bin/bash
# Linux:  ./iniciar.sh            (red local)
#         ./iniciar.sh --internet (además, enlace de internet)
cd "$(dirname "$0")"
exec python3 iniciar.py "$@"
