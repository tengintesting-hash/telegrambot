from fastapi import FastAPI
from app.api import router as api_router
from app.database import lifespan
from app.ws import ws_router

app = FastAPI(lifespan=lifespan)

app.include_router(api_router)
app.include_router(ws_router)
