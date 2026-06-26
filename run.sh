#!/usr/bin/env bash
# =============================================================================
# run.sh — AI Guard Demo
# Inicia el backend (FastAPI) que también sirve el frontend en el mismo puerto.
# =============================================================================
set -euo pipefail

# Resolve script dir
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ -t 1 ]; then
    R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[0;33m'; B=$'\033[0;34m'; N=$'\033[0m'
else
    R=""; G=""; Y=""; B=""; N=""
fi

# --- Pre-flight checks -------------------------------------------------------
if [ ! -d "venv" ]; then
    echo "${R}✗ venv no existe. Ejecutá primero:${N} ./setup.sh"
    exit 1
fi
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "${R}✗ Estructura del proyecto incompleta (falta backend/ o frontend/).${N}"
    exit 1
fi

# --- Activar venv ------------------------------------------------------------
# shellcheck disable=SC1091
source venv/bin/activate

# --- Cargar .env si existe ---------------------------------------------------
if [ -f ".env" ]; then
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# --- Banner ------------------------------------------------------------------
echo ""
echo "${B}============================================================${N}"
echo "${B}  AI Guard Demo · iniciando${N}"
echo "${B}============================================================${N}"
echo ""

# Mostrar modo de AI Guard (sin imprimir la key)
if [ -n "${TREND_API_KEY:-}" ]; then
    echo "  ${G}AI Guard:${N}     modo TREND-MICRO (API key configurada)"
    echo "  ${G}endpoint:${N}     ${TREND_GUARD_ENDPOINT:-https://api.trendmicro.com/v1/guard}"
else
    echo "  ${Y}AI Guard:${N}     modo MOCK (sin TREND_API_KEY — heurístico regex)"
fi

if [ -n "${OPENAI_API_KEY:-}" ]; then
    echo "  ${G}LLM:${N}          OpenAI (${OPENAI_MODEL:-gpt-4o-mini})"
else
    echo "  ${Y}LLM:${N}          simulado local (sin OPENAI_API_KEY)"
fi

echo ""
echo "  ${G}🌐 Frontend:${N}  http://localhost:${PORT}/"
echo "  ${G}🔌 API chat:${N}  http://localhost:${PORT}/chat"
echo "  ${G}🩺 Health:${N}    http://localhost:${PORT}/health"
echo "  ${G}📚 OpenAPI:${N}   http://localhost:${PORT}/docs"
echo ""
echo "  ${Y}Ctrl+C${N} para detener."
echo ""

# --- Iniciar ----------------------------------------------------------------
# 1 worker es óptimo para la demo:
#   - FastAPI sobre asyncio maneja ~10 usuarios simultáneos sin esfuerzo
#   - SessionManager vive en memoria del proceso → 1 worker = estado consistente
# Para producción multi-replica, reemplazar SessionManager por Redis/DynamoDB
# y aumentar --workers.
cd backend
exec uvicorn app:app --host "$HOST" --port "$PORT" --workers 1
