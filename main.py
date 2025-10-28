from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes.analyze import analyze_router
from api.routes.chat import chat_router
from api.routes.feedback import feedback_router

def create_app() -> FastAPI:
    app = FastAPI(title="Dishwasher Troubleshooter (Prototype)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(analyze_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)

    return app

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
