# main.py
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from i18n import set_locale

from config import settings
from api.routes.analyze import analyze_router
from api.routes.chat import chat_router
from api.routes.feedback import feedback_router

def pick_lang(req: Request):
    qlang = req.query_params.get("lang")
    if not qlang:
        hdr = req.headers.get("accept-language", "")
        qlang = (hdr.split(",")[0].split("-")[0] if hdr else None)
    lang = set_locale(qlang)
    # IMPORTANT: salvează pe request.state ca să fie vizibil în endpoints
    req.state.lang = lang
    return lang

def create_app() -> FastAPI:
    app = FastAPI(title="Dishwasher Troubleshooter (Prototype)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rulează dependency-ul de limbă pentru toate rutele acestor routere
    app.include_router(analyze_router, dependencies=[Depends(pick_lang)])
    app.include_router(chat_router, dependencies=[Depends(pick_lang)])
    app.include_router(feedback_router, dependencies=[Depends(pick_lang)])

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
