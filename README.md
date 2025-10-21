# Troubleshooting Chatbot with Image Analysis

A small FastAPI service that analyzes images of dishwasher results (e.g., spots, streaks) and runs an interactive troubleshooting flow with users. This README explains the API endpoints, request/response formats, session behavior, and how to run the server.

## Table of contents

- Overview
- API Endpoints
  - POST /analyze
  - POST /chat
  - POST /feedback
- Session handling
- Run locally
- Production notes
- Contributing

## Overview

This service accepts an image and optional user notes, uses an AI image classifier to predict an issue label (for example: "spots", "streaks"), and then guides the user through step-by-step troubleshooting actions via an interactive chat-like flow. Sessions are kept in-memory for simplicity; see "Production notes" for persistence recommendations.

## API Endpoints

### POST /analyze

Starts a new troubleshooting session by analyzing an uploaded image.

Request (multipart/form-data):

```http
POST /analyze
Content-Type: multipart/form-data

- image: file (required) — photo of dishwasher results
- notes: string (optional) — additional user notes
```

Successful response (JSON):

```json
{
  "label": "spots",
  "confidence": 0.84,
  "session_id": "a1b2c3d4-5678"
}
```

Behavior:
- Creates a new session stored in memory (SESSIONS dict) with the AI prediction and confidence.
- The returned session_id must be included in subsequent /chat and /feedback calls.

### POST /chat

Continues the interactive troubleshooting flow for a session. Each call advances or branches the conversation depending on the event.

Request (JSON):

```json
{
  "session_id": "a1b2c3d4-5678",
  "event": "start | confirm | not_solved | try_again | solved | done",
  "user_input": "optional user text"
}
```

Events and behavior:
- start: Introduces the detected issue and asks the user if they'd like step-by-step guidance.
- confirm: Sends the first set of recommended actions for the predicted issue.
- not_solved / try_again: Cycles through alternative actions or troubleshooting steps, if available.
- solved / done: Marks the session as finished and requests optional feedback.

Response (JSON):

```json
{
  "message": "Do these now:\n• Settings → rinse aid: level_3_or_higher...",
  "quick_replies": ["Solved", "Not solved", "More options", "Try again"],
  "actions": [
    {"type": "setting", "target": "rinse_aid", "value": "level_3_or_higher"}
  ]
}
```

Notes:
- "actions" contains structured steps that client apps can render as UI actions.
- "quick_replies" suggests user responses for a better conversational UX.

### POST /feedback

Collects optional user feedback at the end of the troubleshooting flow to measure success and (optionally) improve the model.

Request (JSON):

```json
{
  "session_id": "a1b2c3d4-5678",
  "solved": true,
  "final_label": "spots",
  "notes": "Fixed by increasing rinse aid."
}
```

Response:

```json
{"status": "ok"}
```

## Session handling

- /analyze creates and seeds a session in memory (an entry in SESSIONS).
- /chat and /feedback use the same session_id to continue or finish the session.
- Warning: Sessions are in-memory and will be lost if the server restarts. For production use a persistent store such as Redis or a database.

## Run locally

To run the server for development:

```bash
uvicorn main:app --reload --port 8000
```

## Production notes

- Replace in-memory session storage with Redis or a database for reliability.
- Add authentication and rate limiting if you expose the API publicly.
- Sanitize and validate uploaded images before processing.
- Consider opt-in data collection and privacy notices if storing user photos for model improvement.

## Contributing

Contributions are welcome. Please open issues or pull requests with improvements, bug fixes, or feature proposals.


---

If you want, I can also:
- Add a short example client script showing how to call /analyze and /chat,
- Split the README into a shorter overview and a separate docs/ folder for full API reference.
