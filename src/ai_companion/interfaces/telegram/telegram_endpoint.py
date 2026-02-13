
from fastapi import FastAPI
from ai_companion.interfaces.telegram.telegram_response import telegram_router

app = FastAPI()

app.include_router(telegram_router)
