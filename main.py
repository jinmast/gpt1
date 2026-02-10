"""Application entrypoint."""

from fastapi import FastAPI

from scheduler_app.routers.google_calendar_router import router as google_calendar_router

app = FastAPI(title="Scheduler App")
app.include_router(google_calendar_router)
