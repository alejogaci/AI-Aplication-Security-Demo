#!/usr/bin/env bash
# =============================================================================
# setup.sh — AI Guard Demo
# Crea venv, instala dependencias, prepara .env. Idempotente.
# =============================================================================
set -euo pipefail

# Resolve script dir (so it works no matter cwd)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors (no-op si no es tty)
if [ -t 1 ]; then
    R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[0;33m'; B=$'\033[0;34m'; N=$'\033[0m'
else
    R=""; G=""; Y=""; B=""; N=""
fi

banner() {
    echo ""
    echo "${B}=============================================${N}"
    echo "${B}  $1${N}"
    echo "${B}=============================================${N}"
}

banner "AI Guard Demo · Setup"

# --- 1. Detectar Python ------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "${R}✗ Python 3 no encontrado. Instalá Python 3.9 o superior.${N}"
    exit 1
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
PY_OK=$($PYTHON -c 'import sys; print(int(sys.version_info >= (3, 9)))')
if [ "$PY_OK" != "1" ]; then
    echo "${R}✗ Python ${PY_VERSION} detectado. Se requiere 3.9+.${N}"
    exit 1
fi
echo "${G}✓${N} Python ${PY_VERSION} detectado ($PYTHON)"

# --- 2. Virtual env ----------------------------------------------------------
if [ ! -d "venv" ]; then
    echo "${Y}→${N} Creando virtualenv en ./venv"
    $PYTHON -m venv venv
else
    echo "${G}✓${N} Virtualenv ya existe en ./venv"
fi

# Activar venv
# shellcheck disable=SC1091
source venv/bin/activate

# --- 3. Instalar deps --------------------------------------------------------
echo "${Y}→${N} Actualizando pip..."
pip install --quiet --upgrade pip

echo "${Y}→${N} Instalando dependencias del backend..."
pip install --quiet -r backend/requirements.txt
echo "${G}✓${N} Dependencias instaladas"

# --- 4. Setup .env -----------------------------------------------------------
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "${G}✓${N} Archivo ${B}.env${N} creado a partir de .env.example"
    echo "  ${Y}Tip:${N} sin TREND_API_KEY el sistema corre en modo MOCK (heurístico)."
    echo "       Funcional para demo sin necesidad de credenciales reales."
else
    echo "${G}✓${N} Archivo .env ya existe — no se sobrescribe"
fi

# --- 5. Verificación rápida --------------------------------------------------
echo ""
echo "${Y}→${N} Verificando imports del backend..."
(cd backend && python -c "
import app
import ai_guard
import llm_handler
import session_manager
print('   imports OK')
")

# --- 6. Done -----------------------------------------------------------------
banner "Setup completo"
echo "${G}✓${N} Todo listo. Para iniciar:"
echo ""
echo "    ${B}./run.sh${N}"
echo ""
echo "Luego abrí: ${B}http://localhost:8000${N}"
echo ""
