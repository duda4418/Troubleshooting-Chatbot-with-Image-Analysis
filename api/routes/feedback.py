from fastapi import APIRouter, HTTPException

from models import FeedbackReq
from state import SESSIONS

feedback_router = APIRouter(prefix="", tags=["feedback"])

@feedback_router.post("/feedback")
def feedback(body: FeedbackReq):
    s = SESSIONS.get(body.session_id)
    if not s:
        raise HTTPException(404, _("Unknown session_id"))
    s["status"] = "solved" if body.solved else "unsolved"
    s.setdefault("feedback", {})
    s["feedback"]["final_label"] = body.final_label
    s["feedback"]["notes"] = body.notes
    return {"status": "ok"}
