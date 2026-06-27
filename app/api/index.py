import asyncio
import os
import sys
import json

# Ensure the root directory is in the python path
# Now located at app/api/index.py, so we need 3 dirnames to get to root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

@app.get("/manifest.json")
async def get_manifest():
    manifest_data = {
        "name": "Bot Keuangan Pintar",
        "short_name": "Keuangan",
        "start_url": "/dashboard",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#10b981",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/2933/2933116.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "https://cdn-icons-png.flaticon.com/512/2933/2933116.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return Response(content=json.dumps(manifest_data), media_type="application/manifest+json")

@app.get("/sw.js")
async def get_sw():
    js_content = """
const CACHE_NAME = 'keuangan-pwa-v1';
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll([
      '/login'
    ]))
  );
});
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request))
  );
});
"""
    return Response(content=js_content, media_type="application/javascript")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'login.html')
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

from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.database import AsyncSessionLocal
from app.models import User, Transaction, TransactionType
from sqlalchemy import select, desc
import datetime

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))

@app.get("/api/auth/token")
async def token_auth(request: Request, response: Response):
    token = request.query_params.get("token")
    if not token:
        return HTMLResponse("<h1>Error: Token tidak ditemukan</h1>", status_code=400)
        
    try:
        # Decode and verify the JWT
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        
        # Redirect ke dashboard dan set cookie
        redirect = RedirectResponse(url="/dashboard", status_code=302)
        redirect.set_cookie(key="auth_token", value=token, httponly=True, max_age=3600*24)
        return redirect
    except jwt.ExpiredSignatureError:
        return HTMLResponse("<h1>Error: Token sudah kedaluwarsa</h1><p>Silakan minta token baru di bot Telegram Anda.</p>", status_code=400)
    except jwt.InvalidTokenError:
        return HTMLResponse("<h1>Error: Token tidak valid</h1>", status_code=400)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return RedirectResponse(url="/login")
        
    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = (await session.execute(stmt)).scalar_one_or_none()
            
            if not user:
                return RedirectResponse(url="/login")
                
            from sqlalchemy.orm import joinedload
            # Ambil transaksi terbaru (limit 10)
            tx_stmt = select(Transaction).options(joinedload(Transaction.category)).where(Transaction.user_id == user.id).order_by(desc(Transaction.date), desc(Transaction.id)).limit(10)
            transactions = (await session.execute(tx_stmt)).scalars().all()
            
            # Hitung statistik bulan ini
            current_month = datetime.date.today().replace(day=1)
            stat_stmt = select(Transaction).where(Transaction.user_id == user.id, Transaction.date >= current_month)
            month_tx = (await session.execute(stat_stmt)).scalars().all()
            
            total_income = sum(tx.amount for tx in month_tx if tx.type == TransactionType.INCOME)
            total_expense = sum(tx.amount for tx in month_tx if tx.type == TransactionType.EXPENSE)
            
            # Total Saldo (dari tabel wallets bisa juga, tapi untuk simple kita ambil dari user.wallets)
            # Karena eager loading belum disetup, kita ambil manual
            from app.models import Wallet
            wallet_stmt = select(Wallet).where(Wallet.user_id == user.id)
            wallets = (await session.execute(wallet_stmt)).scalars().all()
            total_balance = sum(w.balance for w in wallets)
            
            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context={
                    "user": user,
                    "transactions": transactions,
                    "total_income": float(total_income),
                    "total_expense": float(total_expense),
                    "total_balance": float(total_balance),
                    "wallets": wallets
                }
            )
            
    except jwt.InvalidTokenError:
        return RedirectResponse(url="/login")

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("auth_token")
    return response

import sqlalchemy as sa
@app.post("/api/wallets/{wallet_id}/set-primary")
async def set_primary_wallet(wallet_id: str, request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return Response(status_code=401)
        
    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user: return Response(status_code=401)
            
            from app.models import Wallet
            await session.execute(
                sa.update(Wallet).where(Wallet.user_id == user.id).values(is_primary=False)
            )
            
            # import uuid
            import uuid
            try:
                wallet_uuid = uuid.UUID(wallet_id)
            except ValueError:
                return Response(status_code=400)
                
            await session.execute(
                sa.update(Wallet).where(Wallet.id == wallet_uuid, Wallet.user_id == user.id).values(is_primary=True)
            )
            await session.commit()
            
            return {"status": "success"}
    except jwt.InvalidTokenError:
        return Response(status_code=401)

@app.post("/api/wallets")
async def create_wallet(request: Request):
    token = request.cookies.get("auth_token")
    if not token: return Response(status_code=401)
    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        data = await request.json()
        
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user: return Response(status_code=401)
            
            from app.models import Wallet
            new_wallet = Wallet(user_id=user.id, name=data.get("name"), balance=data.get("balance", 0), is_primary=False)
            session.add(new_wallet)
            await session.commit()
            return {"status": "success"}
    except Exception as e:
        return Response(status_code=400)

@app.put("/api/wallets/{wallet_id}")
async def update_wallet(wallet_id: str, request: Request):
    token = request.cookies.get("auth_token")
    if not token: return Response(status_code=401)
    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        data = await request.json()
        
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user: return Response(status_code=401)
            
            from app.models import Wallet
            import uuid
            try:
                wallet_uuid = uuid.UUID(wallet_id)
            except ValueError:
                return Response(status_code=400)
                
            wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet_uuid, Wallet.user_id == user.id))).scalar_one_or_none()
            if not wallet: return Response(status_code=404)
            
            if "name" in data: wallet.name = data["name"]
            if "balance" in data: wallet.balance = data["balance"]
            
            await session.commit()
            return {"status": "success"}
    except Exception as e:
        return Response(status_code=400)

@app.delete("/api/wallets/{wallet_id}")
async def delete_wallet(wallet_id: str, request: Request):
    token = request.cookies.get("auth_token")
    if not token: return Response(status_code=401)
    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user: return Response(status_code=401)
            
            from app.models import Wallet, Transaction
            import uuid
            try:
                wallet_uuid = uuid.UUID(wallet_id)
            except ValueError:
                return Response(status_code=400)
                
            wallet = (await session.execute(select(Wallet).where(Wallet.id == wallet_uuid, Wallet.user_id == user.id))).scalar_one_or_none()
            if not wallet: return Response(status_code=404)
            
            # Delete related transactions first to prevent foreign key errors
            await session.execute(sa.delete(Transaction).where(Transaction.wallet_id == wallet.id))
            await session.delete(wallet)
            await session.commit()
            return {"status": "success"}
    except Exception as e:
        return Response(status_code=400)

