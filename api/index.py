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
        logger.error(f"Error handling webhook: {e}")
        return Response(status_code=500, content="Internal Server Error")

from fastapi.responses import HTMLResponse

@app.get("/")
@app.get("/api/webhook")
async def bot_info():
    return {
        "status": "success",
        "message": "Bot Keuangan berjalan normal di Vercel Serverless.",
        "telegram_webhook_ready": True
    }

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    template_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates', 'login.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Template tidak ditemukan</h1>", status_code=404)

@app.get("/api/auth", response_class=HTMLResponse)
async def telegram_auth(request: Request):
    # Telegram mengirim data auth lewat query parameters
    params = dict(request.query_params)
    
    if not params.get("id"):
        return HTMLResponse("<h1>Error: Data login tidak valid</h1>", status_code=400)
        
    username = params.get("username", "Pengguna")
    first_name = params.get("first_name", "")
    
    # Di masa depan, di sini kita akan memverifikasi 'hash' menggunakan bot token
    # dan membuatkan sesi/JWT token untuk pengguna web.
    
    html_success = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>Login Berhasil</title>
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
            .card {{ background: rgba(30,41,59,0.7); padding: 40px; border-radius: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }}
            h1 {{ color: #10b981; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>✅ Login Berhasil!</h1>
            <p>Selamat datang, <b>{first_name} (@{username})</b>!</p>
            <p>Akun Telegram Anda ({params.get('id')}) berhasil terhubung dengan Web App.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_success, status_code=200)

import jwt
from app.core.config import settings

@app.get("/api/auth/token", response_class=HTMLResponse)
async def token_auth(request: Request):
    token = request.query_params.get("token")
    if not token:
        return HTMLResponse("<h1>Error: Token tidak ditemukan</h1>", status_code=400)
        
    try:
        # Decode and verify the JWT
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        
        name = payload.get("name", "Pengguna")
        telegram_id = payload.get("telegram_id")
        
        html_success = f"""
        <!DOCTYPE html>
        <html lang="id">
        <head>
            <meta charset="UTF-8">
            <title>Login Berhasil</title>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                .card {{ background: rgba(30,41,59,0.7); padding: 40px; border-radius: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }}
                h1 {{ color: #10b981; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>✅ Autentikasi Web Berhasil!</h1>
                <p>Selamat datang, <b>{name}</b>!</p>
                <p>Sistem telah mengenali Anda dari tautan Token Bot (Telegram ID: {telegram_id}).</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_success, status_code=200)
    except jwt.ExpiredSignatureError:
        return HTMLResponse("<h1>Error: Token sudah kedaluwarsa</h1><p>Silakan minta token baru di bot Telegram Anda.</p>", status_code=400)
    except jwt.InvalidTokenError:
        return HTMLResponse("<h1>Error: Token tidak valid</h1>", status_code=400)
