"""Application entrypoint."""

from pathlib import Path
import sys

from fastapi import FastAPI


SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from scheduler_app.routers.google_calendar_router import router as google_calendar_router

app = FastAPI(title="Scheduler App")
app.include_router(google_calendar_router)
