from fastapi import APIRouter, HTTPException

from flow import FLOW, FALLBACK
from models import ChatReq, ChatResp
from state import SESSIONS
from utils.formatting import actions_to_text

chat_router = APIRouter(prefix="", tags=["chat"])

@chat_router.post("/chat", response_model=ChatResp)
def chat(req: ChatReq):
    s = SESSIONS.get(req.session_id)
    if not s:
        raise HTTPException(404, "Unknown session_id")

    label = s.get("label", FALLBACK)
    node = FLOW.get(label, FLOW[FALLBACK])

    if req.event == "start":
        msg = (
            f"I see signs of **{label}** (confidence {s['confidence']:.2f}).\n"
            f"Likely causes: {', '.join(node['causes'])}.\n"
            "Want tailored steps?"
        )
        return {"message": msg, "quick_replies": ["Yes", "No"], "actions": []}

    if req.event == "confirm":
        actions = node["actions"]
        friendly = actions_to_text(actions)
        msg = f"Do these now:\n{friendly}\n\nDid that help?"
        return {"message": msg, "quick_replies": ["Solved", "Not solved", "Try again"], "actions": actions}

    if req.event in ("not_solved", "try_again"):
        actions = [
            {"type": "setting", "target": "cycle", "value": "intensive"},
            {"type": "maintenance", "target": "spray_arms", "value": "check_and_clean"},
            {"type": "placement", "target": "device", "value": "upper_rack_front"},
        ]
        msg = "No worries. Backup steps below. After trying them, let me know the outcome."
        return {"message": msg, "quick_replies": ["Solved", "Not solved"], "actions": actions}

    if req.event == "done":
        return {"message": "Session finished. You can send feedback so we improve.", "quick_replies": ["Send feedback"], "actions": []}

    return {"message": "Tap a button to continue.", "quick_replies": ["Yes", "No"], "actions": []}
