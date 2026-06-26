"""
app.py
------
FastAPI app — punto de entrada principal.

Endpoints:
  POST   /chat                  → Conversación. Compatible con AI Scanner.
  POST   /session/create        → Crea sesión nueva y devuelve session_id.
  POST   /session/guard         → Activa/desactiva AI Guard por sesión.
  GET    /session/{sid}         → Devuelve estado actual de la sesión.
  GET    /health                → Liveness/Status (modo guard, sesiones).
  GET    /                      → Frontend (UI estática).
  GET    /docs                  → Swagger UI auto-generado.

Notas:
  * Concurrencia: FastAPI corre sobre asyncio. 1 worker maneja ~10 usuarios
    simultáneos sin problema (los handlers son async y la única operación de
    I/O bloqueante — la llamada a Trend AI Guard — se hace con httpx.AsyncClient).
  * El estado por sesión vive en memoria del proceso. Si necesitás multi-replica
    o persistencia, reemplazá session_manager.SessionManager por una versión
    sobre Redis/DynamoDB sin tocar este archivo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_guard import AIGuardClient
from llm_handler import LLMHandler, detect_attack
from session_manager import SessionManager

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
# Cargamos .env desde el directorio padre del backend (raíz del proyecto).
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(
    title="AI Guard Demo Chatbot",
    description=(
        "Chatbot intencionalmente vulnerable para demos de Trend Micro AI Guard "
        "y AI Scanner. AI Guard se activa/desactiva por sesión."
    ),
    version="1.0.0",
)

# CORS abierto para facilitar la demo (frontend y backend mismo origen igual).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Componentes singleton.
session_mgr = SessionManager()
ai_guard = AIGuardClient(
    api_key=os.getenv("TREND_API_KEY"),
    endpoint=os.getenv("TREND_GUARD_ENDPOINT"),
)
llm = LLMHandler()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje del usuario (puede ser malicioso para demo).")
    session_id: Optional[str] = Field(
        None, description="ID de sesión. Si no se pasa, se crea automáticamente."
    )
    ai_guard_enabled: Optional[bool] = Field(
        None,
        description=(
            "Override por request. Si se omite, se usa el estado de la sesión. "
            "Útil para AI Scanner: permite probar ambos modos sin tocar /session/guard."
        ),
    )


class ChatResponse(BaseModel):
    session_id: str
    ai_guard_enabled: bool
    blocked: bool
    stage: Optional[str] = None  # "input" | "output" | None
    response: str
    guard_reasons: list = []
    attack_patterns_detected: list = []
    guard_mode: str


class GuardToggleRequest(BaseModel):
    session_id: str
    enabled: bool


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "guard_mode": ai_guard.mode,        # "mock" or "trend-micro"
        "guard_endpoint": ai_guard.endpoint if ai_guard.mode == "trend-micro" else None,
        "llm_mode": "openai" if llm.use_openai else "local-simulated",
        "sessions": session_mgr.stats(),
    }


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@app.post("/session/create")
async def session_create() -> dict:
    sid = session_mgr.create_session()
    return session_mgr.get_session(sid)


@app.get("/session/{sid}")
async def session_get(sid: str) -> dict:
    return session_mgr.get_session(sid)


@app.post("/session/guard")
async def session_set_guard(req: GuardToggleRequest) -> dict:
    return session_mgr.set_guard(req.session_id, req.enabled)


# ---------------------------------------------------------------------------
# Chat — el endpoint que también consume AI Scanner
# ---------------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message no puede estar vacío")

    # Resolver sesión.
    sid = req.session_id or session_mgr.create_session()
    session = session_mgr.get_session(sid)

    # Resolver estado de AI Guard.
    # Precedencia: override por request > estado de sesión > default (False).
    if req.ai_guard_enabled is not None:
        guard_on = bool(req.ai_guard_enabled)
    else:
        guard_on = bool(session.get("ai_guard_enabled", False))

    attack_hits = detect_attack(req.message)

    # ---------- Etapa 1: validar INPUT con AI Guard ----------
    if guard_on:
        in_check = await ai_guard.validate(req.message, kind="input")
        if in_check["action"] == "Block":
            response_text = (
                "⛔ Tu mensaje fue bloqueado por Trend Micro AI Guard antes de "
                "llegar al modelo. Motivos: " + "; ".join(in_check["reasons"][:3])
            )
            session_mgr.add_history(sid, req.message, response_text, guard_on, True)
            return ChatResponse(
                session_id=sid,
                ai_guard_enabled=True,
                blocked=True,
                stage="input",
                response=response_text,
                guard_reasons=in_check["reasons"],
                attack_patterns_detected=attack_hits,
                guard_mode=in_check["mode"],
            )

    # ---------- Etapa 2: generar respuesta del modelo ----------
    model_response = llm.generate(req.message, guard_enabled=guard_on)

    # ---------- Etapa 3: validar OUTPUT con AI Guard ----------
    if guard_on:
        out_check = await ai_guard.validate(model_response, kind="output")
        if out_check["action"] == "Block":
            sanitized = (
                "⛔ La respuesta del modelo fue bloqueada por Trend Micro AI Guard "
                "antes de mostrarse al usuario. Motivos: "
                + "; ".join(out_check["reasons"][:3])
            )
            session_mgr.add_history(sid, req.message, sanitized, guard_on, True)
            return ChatResponse(
                session_id=sid,
                ai_guard_enabled=True,
                blocked=True,
                stage="output",
                response=sanitized,
                guard_reasons=out_check["reasons"],
                attack_patterns_detected=attack_hits,
                guard_mode=out_check["mode"],
            )

    # ---------- OK: respuesta pasa ----------
    session_mgr.add_history(sid, req.message, model_response, guard_on, False)
    return ChatResponse(
        session_id=sid,
        ai_guard_enabled=guard_on,
        blocked=False,
        stage=None,
        response=model_response,
        guard_reasons=[],
        attack_patterns_detected=attack_hits,
        guard_mode=ai_guard.mode if guard_on else "disabled",
    )


# ---------------------------------------------------------------------------
# Frontend estático — debe ir AL FINAL para no interceptar rutas de API
# ---------------------------------------------------------------------------
FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )
else:
    @app.get("/")
    async def root_fallback() -> dict:
        return {"message": "Frontend no encontrado en " + str(FRONTEND_DIR),
                "api_docs": "/docs"}
