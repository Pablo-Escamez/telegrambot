
import logging
import os
from io import BytesIO
import httpx
from fastapi import APIRouter, Request, Response, FastAPI  # <-- Importamos FastAPI aquí


app = FastAPI()

telegram_router = APIRouter()


logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

@telegram_router.post("/telegram_response")
async def telegram_handler(request: Request) -> Response:
    # Tu lógica del webhook va aquí...
    # Por ahora, solo devolvemos OK para probar.
    data = await request.json()
    logger.info(f"Recibido de Telegram: {data}")
    return Response(content="OK", status_code=200)

app.include_router(telegram_router)

@app.get("/")
def read_root():
    return {"message": "Servicio de Bot para Telegram está corriendo correctamente!"}
