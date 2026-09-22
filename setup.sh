#!/bin/sh
# FIA Core setup for macOS / Linux (also works in Git Bash on Windows).
# Creates .venv inside the project, installs fia-core-full there and runs
# `fia init`. Re-running is safe: nothing is overwritten.
#
# Usage:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/mcpedrogm-art/fia-core/main/setup.sh)"
#   ./setup.sh [--dir PATH] [--modules ui,security]

set -eu

DIR="."
MODULES=""
while [ $# -gt 0 ]; do
    case "$1" in
        --dir) DIR="${2:?falta el valor de --dir}"; shift 2 ;;
        --modules) MODULES="${2:?falta el valor de --modules}"; shift 2 ;;
        *) echo "Opcion desconocida: $1" >&2; exit 2 ;;
    esac
done

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "ERROR: no se encontro python3 en el PATH. Instala Python 3.8+." >&2
    exit 1
fi

case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*)
        VENV_PY="Scripts/python.exe"
        VENV_FIA="Scripts/fia.exe"
        ACTIVATE=".venv/Scripts/activate"
        ;;
    *)
        VENV_PY="bin/python"
        VENV_FIA="bin/fia"
        ACTIVATE=".venv/bin/activate"
        ;;
esac

cd "$DIR"
PROJECT="$(pwd)"

if [ -x ".venv/$VENV_PY" ]; then
    echo "[1/3] .venv ya existe, se reutiliza"
else
    echo "[1/3] Creando entorno virtual en .venv ..."
    "$PYTHON" -m venv .venv
fi

echo "[2/3] Instalando fia-core-full dentro del proyecto ..."
".venv/$VENV_PY" -m pip install --disable-pip-version-check --quiet --upgrade fia-core-full

if [ ! -x ".venv/$VENV_FIA" ]; then
    echo "ERROR: la instalacion no genero el comando fia." >&2
    exit 1
fi

echo "[3/3] Inicializando el proyecto (PROJECT.md, TASK.md, .fia/) ..."
if [ -n "$MODULES" ]; then
    ".venv/$VENV_FIA" init -d "$PROJECT" --modules "$MODULES"
else
    ".venv/$VENV_FIA" init -d "$PROJECT"
fi

if [ -f .gitignore ]; then
    grep -qx '.venv/' .gitignore 2>/dev/null || printf '.venv/\n' >> .gitignore
else
    printf '.venv/\n' > .gitignore
fi

echo ""
echo "Listo. Nada se ha instalado fuera de este proyecto."
echo ""
echo "Para usarlo, desde esta carpeta:"
echo "  .venv/$VENV_FIA status"
echo "  .venv/$VENV_FIA test -- <tu comando de test>"
echo "  .venv/$VENV_FIA verify"
echo ""
echo "O activa el entorno una vez por sesion y usa 'fia' directamente:"
echo "  . $ACTIVATE"
