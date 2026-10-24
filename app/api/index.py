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

@app.get("/api/cron/daily-report")
async def cron_daily_report(request: Request):
    """Dipicu Vercel Cron sekali sehari (12:00 UTC = 20:00 WITA).
    Mengirim laporan ke user yang sudah jam 8 malam waktu lokalnya.

    Amankan dengan env CRON_SECRET (kirim sebagai ?secret= atau header Authorization).
    """
    from app.core.config import settings as cron_settings

    if cron_settings.CRON_SECRET:
        given = request.query_params.get("secret", "")
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            given = auth[7:].strip()
        if given != cron_settings.CRON_SECRET:
            return Response(status_code=403, content="Forbidden")

    try:
        from bot.handlers.report import kirim_laporan_harian_otomatis

        bot_app = await get_ptb_app()
        hasil = await kirim_laporan_harian_otomatis(bot_app.bot)
        return {"status": "success", **hasil}
    except Exception as e:
        logger.error(f"Error cron daily-report: {e}", exc_info=True)
        return Response(status_code=500, content="Internal Server Error")

@app.get("/api/set_webhook")
async def set_webhook(request: Request):
    bot_app = await get_ptb_app()
    webhook_url = f"https://{request.url.hostname}/api/webhook"
    
    # Check config first
    from app.core.config import settings
    if settings.WEBHOOK_URL:
        webhook_url = settings.WEBHOOK_URL
        
    await bot_app.bot.set_webhook(url=webhook_url)
    return {"status": "success", "message": f"Webhook berhasil dipasang ke {webhook_url}"}

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
from app.core.timezone import local_now
from app.core.timezone import to_local_datetime
from app.models import Category, User, Transaction, TransactionType, Wallet
from sqlalchemy import desc, func, select
import datetime
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import uuid

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
            today = local_now(user.timezone).date()

            async def get_transactions_since(start_date):
                tx_stmt = (
                    select(Transaction)
                    .options(joinedload(Transaction.category))
                    .where(Transaction.user_id == user.id)
                    .order_by(desc(Transaction.created_at), desc(Transaction.id))
                )
                transactions = (await session.execute(tx_stmt)).scalars().all()
                local_transactions = []
                for transaction in transactions:
                    transaction.local_created_at = to_local_datetime(transaction.created_at, user.timezone)
                    if start_date <= transaction.local_created_at.date() <= today:
                        transaction.date = transaction.local_created_at.date()
                        local_transactions.append(transaction)
                return local_transactions

            transactions_today = await get_transactions_since(today)
            transactions_week = await get_transactions_since(today - timedelta(days=today.weekday()))
            transactions_month = await get_transactions_since(today.replace(day=1))
            
            # Hitung statistik bulan ini
            current_month = today.replace(day=1)
            month_tx = [
                transaction
                for transaction in transactions_month
                if transaction.local_created_at.date() >= current_month
            ]
            
            total_income = sum(tx.amount for tx in month_tx if tx.type == TransactionType.INCOME)
            total_expense = sum(tx.amount for tx in month_tx if tx.type == TransactionType.EXPENSE)

            category_totals = {}
            for transaction in month_tx:
                category_name = transaction.category.name if transaction.category else "Lainnya"
                key = (transaction.type, category_name)
                category_totals[key] = category_totals.get(key, 0) + transaction.amount
            category_rows = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
            income_categories = [
                {"name": name, "total": float(total)}
                for (transaction_type, name), total in category_rows
                if transaction_type == TransactionType.INCOME
            ]
            expense_categories = [
                {"name": name, "total": float(total)}
                for (transaction_type, name), total in category_rows
                if transaction_type == TransactionType.EXPENSE
            ]
            
            # Total Saldo (dari tabel wallets bisa juga, tapi untuk simple kita ambil dari user.wallets)
            # Karena eager loading belum disetup, kita ambil manual
            wallet_stmt = select(Wallet).where(Wallet.user_id == user.id)
            wallets = (await session.execute(wallet_stmt)).scalars().all()
            total_balance = sum(w.balance for w in wallets)
            
            return templates.TemplateResponse(
                request=request,
                name="dashboard.html",
                context={
                    "user": user,
                    "transactions_today": transactions_today,
                    "transactions_week": transactions_week,
                    "transactions_month": transactions_month,
                    "total_income": float(total_income),
                    "total_expense": float(total_expense),
                    "total_balance": float(total_balance),
                    "wallets": wallets,
                    "income_categories": income_categories,
                    "expense_categories": expense_categories,
                    "request_month": today.month,
                    "request_year": today.year,
                }
            )
            
    except jwt.InvalidTokenError:
        return RedirectResponse(url="/login")

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("auth_token")
    return response

@app.get("/api/reports/monthly")
async def download_monthly_report(request: Request, year: int | None = None, month: int | None = None):
    """Unduh laporan keuangan satu bulan sebagai file JSON.

    Contoh: /api/reports/monthly?year=2026&month=10
    Tanpa parameter -> bulan berjalan menurut zona waktu user.
    """
    from fastapi.responses import Response as FastAPIResponse

    token = request.cookies.get("auth_token")
    if not token:
        return RedirectResponse(url="/login")

    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")

        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user:
                return RedirectResponse(url="/login")
            today = local_now(user.timezone).date()

        target_year = year or today.year
        target_month = month or today.month
        if not 1 <= target_month <= 12:
            return FastAPIResponse(status_code=400, content="Bulan harus 1-12")

        from app.services.report_service import get_monthly_export

        data = await get_monthly_export(telegram_id, target_year, target_month)
        if data is None:
            return FastAPIResponse(status_code=404, content="User tidak ditemukan")

        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        filename = f"laporan-{target_year}-{target_month:02d}.json"
        return FastAPIResponse(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except jwt.InvalidTokenError:
        return RedirectResponse(url="/login")

@app.put("/api/transactions/{transaction_id}")
async def update_transaction(transaction_id: str, request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return Response(status_code=401)

    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        data = await request.json()
        transaction_uuid = uuid.UUID(transaction_id)
        amount = Decimal(str(data.get("amount")))
        description = str(data.get("description", "")).strip()
        category_name = str(data.get("category", "")).strip()
        if amount <= 0 or not description or not category_name:
            return Response(status_code=400)

        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user:
                return Response(status_code=401)

            transaction = (await session.execute(select(Transaction).where(
                Transaction.id == transaction_uuid,
                Transaction.user_id == user.id,
            ))).scalar_one_or_none()
            if not transaction:
                return Response(status_code=404)

            wallet = await session.get(Wallet, transaction.wallet_id)
            if wallet:
                difference = amount - transaction.amount
                wallet.balance += difference if transaction.type == TransactionType.INCOME else -difference

            category = (await session.execute(select(Category).where(
                Category.user_id == user.id,
                Category.type == transaction.type,
                Category.name == category_name,
            ))).scalar_one_or_none()
            if not category:
                category = Category(user_id=user.id, name=category_name, type=transaction.type)
                session.add(category)
                await session.flush()

            transaction.amount = amount
            transaction.description = description
            transaction.category_id = category.id
            await session.commit()
            return {"status": "success"}
    except (jwt.InvalidTokenError, ValueError, InvalidOperation):
        return Response(status_code=400)
    except Exception:
        return Response(status_code=400)

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return Response(status_code=401)

    try:
        payload = jwt.decode(token, settings.TELEGRAM_TOKEN, algorithms=["HS256"])
        telegram_id = payload.get("telegram_id")
        data = await request.json()
        correct_balance = bool(data.get("correct_balance", False))
        transaction_uuid = uuid.UUID(transaction_id)

        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
            if not user:
                return Response(status_code=401)

            transaction = (await session.execute(select(Transaction).where(
                Transaction.id == transaction_uuid,
                Transaction.user_id == user.id,
            ))).scalar_one_or_none()
            if not transaction:
                return Response(status_code=404)

            if correct_balance:
                wallet = await session.get(Wallet, transaction.wallet_id)
                if wallet:
                    if transaction.type == TransactionType.INCOME:
                        wallet.balance -= transaction.amount
                    else:
                        wallet.balance += transaction.amount

            await session.delete(transaction)
            await session.commit()
            return {"status": "success"}
    except (jwt.InvalidTokenError, ValueError):
        return Response(status_code=400)
    except Exception:
        return Response(status_code=400)

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


# ================= HERMES API (API key, buat asisten) =================
def _check_hermes_key(request: Request) -> bool:
    from app.core.config import settings as _s
    key = _s.HERMES_API_KEY
    if not key:
        return False
    given = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        given = auth[7:].strip() or given
    return given == key


@app.get("/api/hermes/saldo")
async def hermes_saldo(request: Request, telegram_id: int):
    if not _check_hermes_key(request):
        return Response(status_code=401, content="Unauthorized: HERMES_API_KEY salah / belum diset")
    from app.core.database import AsyncSessionLocal as _Session
    from app.models import User as _User, Wallet as _Wallet
    from sqlalchemy import select as _select
    async with _Session() as session:
        user = (await session.execute(_select(_User).where(_User.telegram_id == telegram_id))).scalar_one_or_none()
        if not user:
            return {"status": "success", "telegram_id": telegram_id, "wallets": [], "total_balance": 0}
        wallets = (await session.execute(_select(_Wallet).where(_Wallet.user_id == user.id))).scalars().all()
        data = [{"id": str(w.id), "name": w.name, "balance": float(w.balance), "is_primary": w.is_primary} for w in wallets]
        return {"status": "success", "telegram_id": telegram_id, "wallets": data, "total_balance": sum(d["balance"] for d in data)}


@app.post("/api/hermes/catet")
async def hermes_catet(request: Request):
    if not _check_hermes_key(request):
        return Response(status_code=401, content="Unauthorized: HERMES_API_KEY salah / belum diset")
    import decimal as _decimal
    from app.services.transaction_service import record_transaction as _record
    from app.models.category import TransactionType as _TxType
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400, content="Body harus JSON")
    try:
        telegram_id = int(body.get("telegram_id"))
        raw_type = str(body.get("type", "")).strip().upper()
        amount = _decimal.Decimal(str(body.get("amount")))
        description = str(body.get("description", "")).strip()
        category = (body.get("category") or None)
        wallet = (body.get("wallet") or None)
    except Exception:
        return Response(status_code=400, content="Field wajib: telegram_id(int), type, amount")
    if raw_type in ("INCOME", "MASUK", "PEMASUKAN", "IN"):
        tx_type = _TxType.INCOME
    elif raw_type in ("EXPENSE", "KELUAR", "PENGELUARAN", "OUT", "BELANJA"):
        tx_type = _TxType.EXPENSE
    else:
        return Response(status_code=400, content="type harus INCOME atau EXPENSE")
    if amount <= 0 or not description:
        return Response(status_code=400, content="amount harus >0 dan description wajib diisi")

    class _TU:
        pass
    tu = _TU()
    tu.id = telegram_id
    tu.username = str(body.get("username") or f"hermes-{telegram_id}")
    tu.full_name = str(body.get("full_name") or tu.username)
    try:
        tx = await _record(tu, amount, description, tx_type, category, wallet)
    except ValueError as e:
        return Response(status_code=400, content=str(e))
    except Exception as e:
        return Response(status_code=500, content=f"Gagal catat: {e}")
    return {"status": "success", "id": str(tx.id), "type": tx.type.value if hasattr(tx.type, "value") else str(tx.type),
            "amount": float(tx.amount), "description": tx.description,
            "category": getattr(tx, "category_name", None), "wallet": getattr(tx, "wallet_name", None)}


@app.get("/api/hermes/ringkasan")
async def hermes_ringkasan(request: Request, telegram_id: int, periode: str = "harian"):
    if not _check_hermes_key(request):
        return Response(status_code=401, content="Unauthorized: HERMES_API_KEY salah / belum diset")
    import datetime as _dt
    from app.services.report_service import get_daily_summary as _harian, get_weekly_summary as _mingguan, get_monthly_summary as _bulanan
    from app.services.report_service import get_user_local_date as _tgl
    p = periode.strip().lower()
    today = await _tgl(telegram_id)
    if p in ("harian", "hari", "daily", "today"):
        txs, masuk, keluar = await _harian(telegram_id, today)
        label = f"harian {today.isoformat()}"
    elif p in ("mingguan", "minggu", "weekly"):
        txs, masuk, keluar = await _mingguan(telegram_id, today)
        label = f"mingguan sampai {today.isoformat()}"
    else:
        txs, masuk, keluar = await _bulanan(telegram_id, today.year, today.month)
        label = f"bulanan {today.year}-{today.month:02d}"
    if txs is None:
        return Response(status_code=404, content="User tidak ditemukan")
    items = [{"id": str(t.id), "amount": float(t.amount),
              "type": t.type.value if hasattr(t.type, "value") else str(t.type),
              "description": t.description,
              "category": t.category.name if getattr(t, "category", None) else "Lainnya",
              "wallet": t.wallet.name if getattr(t, "wallet", None) else None,
              "date": t.local_created_at.date().isoformat() if getattr(t, "local_created_at", None) else None} for t in txs[:50]]
    return {"status": "success", "periode": label, "total_income": masuk, "total_expense": keluar,
            "balance": masuk - keluar, "count": len(txs), "transactions": items}
