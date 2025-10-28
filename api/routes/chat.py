from fastapi import APIRouter, HTTPException
from flow import FLOW, FALLBACK
from services.openai_service import detect_intent_from_text
from models import ChatReq, ChatResp
from state import SESSIONS
from utils.formatting import actions_to_text

chat_router = APIRouter(prefix="", tags=["chat"])

def norm(s: str | None) -> str:
    return (s or "").strip().lower()

GENERIC_BACKUP = [
    {"type": "setting", "target": "cycle", "value": "intensive"},
    {"type": "maintenance", "target": "spray_arms", "value": "check_and_clean"},
    {"type": "placement", "target": "device", "value": "upper_rack_front"}
]

@chat_router.post("/chat", response_model=ChatResp)
def chat(req: ChatReq):
    s = SESSIONS.get(req.session_id)
    if not s:
        raise HTTPException(404, "Unknown session_id")

    s.setdefault("phase", "intro")
    s.setdefault("alt_idx", 0)  # which alternatives set we’re on



    # --- INTENT DETECTION FROM USER TEXT (if no label set or fallback) ---
    label = s.get("label", FALLBACK)
    ui = norm(req.user_input)
    if (not s.get("label")) and ui:
        try:
            intent_result = detect_intent_from_text(ui)
            intent_label = intent_result.get("intent", "").lower().replace(" ", "_")
            confidence = float(intent_result.get("confidence", 0))
            # If intent is a known label, use it; else fallback
            if intent_label in FLOW:
                label = intent_label
                s["label"] = label
                s["confidence"] = confidence
            else:
                label = FALLBACK
                s["label"] = label
                s["confidence"] = confidence
        except Exception as e:
            print(f"[ERROR] Intent detection failed: {e}")
            label = FALLBACK
            s["label"] = label
            s["confidence"] = 0.0
    else:
        label = s.get("label", FALLBACK)
    # DEBUG: Afișează label-ul și cheile disponibile în FLOW
    print(f"[DEBUG] label: {label}")
    print(f"[DEBUG] FLOW keys: {list(FLOW.keys())}")
    node = FLOW.get(label, FLOW[FALLBACK])
    # ui is already set above

    ev = norm(req.event)

    # Map some common text → events (safety net)
    if ev == "start" and ui in {"yes", "y"}:
        ev = "confirm"
    elif ev == "start" and ui in {"no", "n"}:
        ev = "done"
    elif ui in {"solved", "resolved"}:
        ev = "solved"
    elif ui in {"not solved", "not_solved", "nope"}:
        ev = "not_solved"
    elif ui in {"try again", "try_again", "retry"}:
        ev = "try_again"
    elif ui in {"more", "more options", "next"}:
        ev = "not_solved"  # treat “more options” as request for next set

    # ---- INTRO ----
    # Afișează mesajul introductiv DOAR dacă evenimentul este 'start' și faza nu a trecut deja în 'steps'.
    # Dacă utilizatorul apasă "Yes" (confirm) după intro, nu mai reintrăm aici.
    if ev == "start" and s["phase"] == "intro":
        msg = (
            f"I see signs of **{label}** (confidence {s['confidence']:.2f}).\n"
            f"Likely causes: {', '.join(node.get('causes', []))}.\n"
            "Want tailored steps?"
        )
        return {"message": msg, "quick_replies": ["Yes", "No"], "actions": []}

    # ---- PRIMARY STEPS ----
    if ev == "confirm":
        s["phase"] = "steps"
        s["alt_idx"] = 0  # reset alternatives for this session
        actions = node.get("actions", [])
        friendly = actions_to_text(actions)
        msg = f"Do these now:\n{friendly}\n\nDid that help?"
        return {
            "message": msg,
            "quick_replies": ["Solved", "Not solved", "More options", "Try again"],
            "actions": actions
        }

    # ---- NOT SOLVED / NEXT OPTIONS ----
    if ev in {"not_solved", "try_again"}:
        s["phase"] = "alternatives"
        alts = node.get("alternatives", [])
        if s["alt_idx"] < len(alts):
            actions = alts[s["alt_idx"]]
            s["alt_idx"] += 1
            friendly = actions_to_text(actions)
            msg = (
                "Alright, let's try another set of options:\n"
                f"{friendly}\n\nLet me know if that helped."
            )
            # If there are more after this, keep “More options”
            more_exists = s["alt_idx"] < len(alts)
            quick = ["Solved", "Not solved"]
            if more_exists:
                quick.append("More options")
            quick.append("Try again")
            return {"message": msg, "quick_replies": quick, "actions": actions}
        else:
            # No more label-specific alternatives → generic backup
            friendly = actions_to_text(GENERIC_BACKUP)
            msg = (
                "We're out of label-specific options. Try these general backup steps:\n"
                f"{friendly}\n\nDid that help?"
            )
            return {
                "message": msg,
                "quick_replies": ["Solved", "Not solved"],
                "actions": GENERIC_BACKUP
            }

    # ---- END / SOLVED ----
    if ev in {"solved", "done"}:
        s["phase"] = "end"
        s["status"] = "solved" if ev == "solved" else "finished"
        return {
            "message": "Great—session finished. You can send feedback so we improve.",
            "quick_replies": ["Send feedback"],
            "actions": []
        }

    # ---- DEFAULT ----
    return {"message": "Tap a button to continue.", "quick_replies": ["Yes", "No"], "actions": []}
