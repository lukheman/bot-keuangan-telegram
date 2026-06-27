import asyncio
import os
import sys

# Ensure the root directory is in the python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Response
from telegram import Update
from main import create_app
import logging

# Set up simple logging for the webhook
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize python-telegram-bot application
ptb_app = create_app()

# We need to initialize the ptb_app manually because we are bypassing run_webhook
_is_initialized = False

async def get_ptb_app():
    global _is_initialized
    if not _is_initialized:
        await ptb_app.initialize()
        await ptb_app.start()
        _is_initialized = True
    return ptb_app

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    try:
        # Get the ptb app instance
        bot_app = await get_ptb_app()
        
        # Parse the incoming JSON into a Telegram Update object
        payload = await request.json()
        update = Update.de_json(payload, bot_app.bot)
        
        # Process the update
        await bot_app.process_update(update)
        
        return Response(status_code=200, content="ok")
    except Exception as e:
@app.get("/")
@app.get("/api/webhook")
async def bot_info():
    return {
        "status": "success",
        "message": "Bot Keuangan berjalan normal di Vercel Serverless.",
        "telegram_webhook_ready": True
    }
