"""
ai_guard.py
-----------
Cliente para Trend Micro AI Guard.

Sigue las "AI Guard Best Practices" del PDF de TrendAI:
  * Chunks de hasta 500 tokens (buffer bajo el límite de 512).
  * Sliding window con 25 % de overlap.
  * Máximo 5 chunks por validación.
  * Si CUALQUIER chunk es bloqueado → bloquea toda la solicitud.
  * NUNCA incluye system prompt (no aplica acá: el caller pasa sólo el mensaje
    de usuario o sólo la respuesta del asistente).

Si la variable TREND_API_KEY no está configurada, se activa un modo MOCK
(heurístico basado en regex) para que la demo funcione out-of-the-box sin
credenciales reales. El modo real y el mock devuelven exactamente el mismo
schema, así que el backend no necesita saber cuál está activo.

Endpoint por defecto: el documento de Trend Micro indica que cada región tiene
su propia URL — pasala via TREND_GUARD_ENDPOINT en .env. El default aquí es el
ejemplo del propio doc.
"""

from __future__ import annotations

import os
import re
from typing import List

import httpx


# ---------------------------------------------------------------------------
# Patrones para el modo MOCK
# ---------------------------------------------------------------------------
# Cuando no hay TREND_API_KEY configurada, AI Guard se simula con regex.
# Esto NO reemplaza al producto real — sólo permite hacer la demo end-to-end
# sin necesidad de tener una API key activa al momento.
_MOCK_INPUT_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"forget\s+(your|all)\s+(instructions|rules)",
    r"bypass\s+(security|safety|filter|guardrails?)",
    r"override\s+(security|safety|filter)",
    r"simulate\s+being\s+compromised",
    r"\bDAN\b|\bdo\s+anything\s+now\b",
    r"jailbreak",
    r"developer\s+mode",
    r"reveal\s+(your\s+)?(system\s+)?(prompt|instructions)",
    r"give\s+me\s+(the\s+)?(passwords?|credentials?|api\s+keys?)",
    r"list\s+(all\s+)?(users|admins|credentials|secrets)",
    r"dump\s+(the\s+)?(database|env|secrets|users)",
]

# Patrones que detectan FUGA de información en la respuesta del modelo.
_MOCK_OUTPUT_PATTERNS = [
    # Credenciales en texto
    r"pwd\s*[:=]\s*\S+",
    r"password\s*[:=]\s*\S+",
    r"contraseña\s*[:=]\s*\S+",
    # IPs privadas (RFC1918)
    r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    r"\b192\.168\.\d{1,3}\.\d{1,3}\b",
    r"\b172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}\b",
    # Keys con prefijos típicos
    r"\bAKIA[A-Z0-9-]{4,}",
    r"\bsk[-_](test|live|prod)[-_][A-Za-z0-9-]{4,}",
    # System prompt leak markers
    r"system\s+prompt\s+original",
    r"you\s+are\s+(a|an|the)\s+\w+\s+assistant",
]


def _compile(patterns: List[str]) -> List[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_MOCK_INPUT_RE = _compile(_MOCK_INPUT_PATTERNS)
_MOCK_OUTPUT_RE = _compile(_MOCK_OUTPUT_PATTERNS)


# ---------------------------------------------------------------------------
# Chunking — implementa la estrategia recomendada por TrendAI
# ---------------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    """1 token ≈ 4 caracteres (estimación conservadora para inglés/español)."""
    return len(text) // 4


def sliding_window_chunks(content: str, max_tokens: int = 500,
                          max_chunks: int = 5) -> List[str]:
    """Sliding window con 25 % overlap, tope de `max_chunks`."""
    if not content or not content.strip():
        return []
    if estimate_tokens(content) <= max_tokens:
        return [content]
    chunk_chars = max_tokens * 4
    overlap = chunk_chars // 4  # 25 %
    out: List[str] = []
    start = 0
    while start < len(content) and len(out) < max_chunks:
        piece = content[start:start + chunk_chars]
        if piece.strip():
            out.append(piece)
        start += chunk_chars - overlap
    return out


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
class AIGuardClient:
    """Cliente async para Trend Micro AI Guard con fallback a modo mock."""

    DEFAULT_ENDPOINT = "https://api.trendmicro.com/v1/guard"

    def __init__(self, api_key: str | None = None,
                 endpoint: str | None = None,
                 timeout: float = 15.0) -> None:
        self.api_key = (api_key or "").strip() or None
        self.endpoint = (endpoint or "").strip() or self.DEFAULT_ENDPOINT
        self.timeout = timeout
        self.use_mock = self.api_key is None

    @property
    def mode(self) -> str:
        return "mock" if self.use_mock else "trend-micro"

    # ----------------------------------------------------------- public API
    async def validate(self, content: str, kind: str = "input") -> dict:
        """Devuelve dict con estructura uniforme:
            {
              "action": "Allow"|"Block",
              "reasons": [...],
              "mode": "mock"|"trend-micro",
              "chunks_validated": int,
              "blocked_chunk": int|None,   # sólo si Block
            }
        `kind` es "input" o "output" — sólo afecta al modo mock (patrones
        distintos para cada uno).
        """
        if not content or not content.strip():
            return self._allow(0, reason="empty content")

        if self.use_mock:
            return self._mock_validate(content, kind)
        return await self._real_validate(content)

    # ------------------------------------------------------------------ mock
    def _mock_validate(self, content: str, kind: str) -> dict:
        patterns = _MOCK_INPUT_RE if kind == "input" else _MOCK_OUTPUT_RE
        hits: List[str] = []
        for p in patterns:
            m = p.search(content)
            if m:
                hits.append(f"[Mock-{kind}] pattern matched: '{m.group(0)[:60]}'")
        if hits:
            return {
                "action": "Block",
                "reasons": hits,
                "mode": "mock",
                "chunks_validated": 1,
                "blocked_chunk": 0,
            }
        return self._allow(1, reason="mock allowed")

    # ------------------------------------------------------------------ real
    async def _real_validate(self, content: str) -> dict:
        chunks = sliding_window_chunks(content)
        if not chunks:
            return self._allow(0, reason="no chunks")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i, chunk in enumerate(chunks):
                payload = {"guard": chunk}
                try:
                    resp = await client.post(self.endpoint,
                                             json=payload, headers=headers)
                except httpx.RequestError as e:
                    # Fail-secure: bloqueo si AI Guard no responde.
                    return {
                        "action": "Block",
                        "reasons": [f"AI Guard transport error: {e}"],
                        "mode": "trend-micro",
                        "chunks_validated": i,
                        "blocked_chunk": i,
                    }
                if resp.status_code >= 500:
                    return {
                        "action": "Block",
                        "reasons": [f"AI Guard HTTP {resp.status_code}"],
                        "mode": "trend-micro",
                        "chunks_validated": i,
                        "blocked_chunk": i,
                    }
                try:
                    result = resp.json()
                except Exception:
                    return {
                        "action": "Block",
                        "reasons": [f"AI Guard non-JSON response: {resp.text[:200]}"],
                        "mode": "trend-micro",
                        "chunks_validated": i,
                        "blocked_chunk": i,
                    }
                if result.get("action") == "Block":
                    # El doc devuelve a veces "reason" (singular) y a veces "reasons".
                    reasons = result.get("reasons") or result.get("reason") or []
                    if isinstance(reasons, str):
                        reasons = [reasons]
                    return {
                        "action": "Block",
                        "reasons": reasons,
                        "mode": "trend-micro",
                        "chunks_validated": i + 1,
                        "blocked_chunk": i,
                        "raw": result,
                    }
        return self._allow(len(chunks), reason=f"all {len(chunks)} chunks allowed")

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _allow(chunks: int, reason: str) -> dict:
        return {
            "action": "Allow",
            "reasons": [reason],
            "mode": "static",
            "chunks_validated": chunks,
            "blocked_chunk": None,
        }
