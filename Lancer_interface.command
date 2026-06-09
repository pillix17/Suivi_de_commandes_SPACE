#!/bin/bash
cd "$(dirname "$0")"

# Utilise Homebrew python3 si disponible (a Flask installé)
PYTHON=/opt/homebrew/bin/python3
if [ ! -f "$PYTHON" ]; then PYTHON=python3; fi

# Vérifie que Flask est installé
if ! "$PYTHON" -c "import flask" 2>/dev/null; then
  echo "Installation de Flask (première fois uniquement)…"
  "$PYTHON" -m pip install flask --quiet
fi

"$PYTHON" app.py
