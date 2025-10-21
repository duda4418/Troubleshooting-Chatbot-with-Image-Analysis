# Simple in-memory store; swap with Redis/Postgres later.
SESSIONS: dict[str, dict] = {}
