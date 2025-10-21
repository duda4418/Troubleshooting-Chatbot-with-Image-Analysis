API Endpoints Overview


POST /analyze
Accepts an image of dishwasher results (plus optional user note), runs AI-based image analysis, and starts a troubleshooting session.

Response

{
  "label": "spots",
  "confidence": 0.84,
  "session_id": "a1b2c3d4-5678"
}


Creates a new troubleshooting session in memory, storing the AI’s predicted label and confidence score.

POST /chat

Handles the interactive troubleshooting flow.
Each call continues the conversation for the given session.

Request

{
  "session_id": "a1b2c3d4-5678",
  "event": "start | confirm | not_solved | try_again | solved | done",
  "user_input": "optional user text"
}


Behavior

start: Introduces the issue and asks if the user wants steps.

confirm: Sends the first recommended actions.

not_solved / try_again: Cycles through alternative actions (if available).

solved / done: Ends the session and prompts for feedback.

Response

{
  "message": "Do these now:\n• Setting → rinse aid: level_3_or_higher...",
  "quick_replies": ["Solved", "Not solved", "More options", "Try again"],
  "actions": [
    {"type": "setting", "target": "rinse_aid", "value": "level_3_or_higher"},
    ...
  ]
}

POST /feedback

Collects user feedback at the end of the troubleshooting flow.

Request

{
  "session_id": "a1b2c3d4-5678",
  "solved": true,
  "final_label": "spots",
  "notes": "Fixed by increasing rinse aid."
}


Response

{"status": "ok"}


Used to track success rates and optionally improve the model with user data.


Session handling
All endpoints share a common session_id:

/analyze creates it and seeds the session in memory (SESSIONS dict).

/chat and /feedback continue the same session.

⚠️ In-memory sessions reset if the server restarts — for production, use Redis or a database.


Run server: uvicorn main:app --reload --port 8000
