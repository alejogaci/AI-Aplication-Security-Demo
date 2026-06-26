"""
session_manager.py
------------------
In-memory session store with per-session AI Guard state.

DESIGN NOTE
-----------
For the demo target (~10 concurrent users) an in-process dict guarded by a
threading.Lock is sufficient and avoids extra infra. For production scale or
multi-replica deployments, replace this class with a Redis or DynamoDB-backed
implementation — the public interface (create_session/get_session/set_guard/
add_history) is intentionally narrow so swapping the backend is trivial.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ create
    def create_session(self) -> str:
        sid = str(uuid.uuid4())
        with self._lock:
            self._sessions[sid] = self._blank_session(sid)
        return sid

    # --------------------------------------------------------------------- get
    def get_session(self, sid: str) -> dict:
        """Auto-creates a session if it does not exist.

        Auto-creation is intentional: it lets external callers (e.g. AI Scanner
        or curl scripts) hit /chat with an arbitrary session_id without first
        calling /session/create.
        """
        with self._lock:
            if sid not in self._sessions:
                self._sessions[sid] = self._blank_session(sid)
            # Return a shallow copy to prevent external mutation.
            return dict(self._sessions[sid])

    # -------------------------------------------------------------- set guard
    def set_guard(self, sid: str, enabled: bool) -> dict:
        with self._lock:
            if sid not in self._sessions:
                self._sessions[sid] = self._blank_session(sid)
            self._sessions[sid]["ai_guard_enabled"] = bool(enabled)
            return dict(self._sessions[sid])

    # ------------------------------------------------------------ add history
    def add_history(self, sid: str, user_msg: str, bot_msg: str,
                    guard_enabled: bool, blocked: bool) -> None:
        with self._lock:
            if sid not in self._sessions:
                return
            history = self._sessions[sid]["history"]
            history.append({
                "user": user_msg,
                "bot": bot_msg,
                "guard_enabled": guard_enabled,
                "blocked": blocked,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            # Cap history to last 20 exchanges to bound memory.
            if len(history) > 20:
                self._sessions[sid]["history"] = history[-20:]

    # ------------------------------------------------------------------ stats
    def stats(self) -> dict:
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "sessions_with_guard_on": sum(
                    1 for s in self._sessions.values() if s["ai_guard_enabled"]
                ),
            }

    # ----------------------------------------------------------------- helper
    @staticmethod
    def _blank_session(sid: str) -> dict:
        return {
            "session_id": sid,
            "ai_guard_enabled": False,  # default OFF — vulnerable for demo
            "created_at": datetime.now(timezone.utc).isoformat(),
            "history": [],
        }
