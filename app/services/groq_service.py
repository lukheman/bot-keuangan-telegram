import json
import re
import logging
import base64
from groq import AsyncGroq
from app.core.config import settings
from app.core.prompts import VISION_EXTRACTION_PROMPT, TEXT_EXTRACTION_PROMPT
from dataclasses import dataclass

logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

@dataclass
class TransactionResult:
    type: str           # "INCOME" atau "EXPENSE"
    amount: float
    description: str
    category: str
    wallet_name: str
    confidence: float   # 0.0 - 1.0
    raw_text: str
    is_valid: bool
    reason: str

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def analyze_transaction(image_path: str, caption: str = None) -> TransactionResult:
    logger.info(f"Menganalisis gambar {image_path} langsung dengan Groq Vision AI. Caption: {caption}")

    if not client:
        logger.error("GROQ_API_KEY belum dikonfigurasi.")
        return TransactionResult("EXPENSE", 0, "", "Lainnya", "Utama", 0.0, "", False, "GROQ_API_KEY belum dikonfigurasi di .env")

    try:
        base64_image = encode_image(image_path)

        prompt_text = VISION_EXTRACTION_PROMPT
        if caption:
            prompt_text += f"\n\nINSTRUKSI SANGAT PENTING \nPengguna memberikan caption/teks berikut bersamaan dengan gambar: \"{caption}\"\nKamu WAJIB menjadikan teks ini sebagai prioritas UTAMA penentu jenis transaksi (INCOME atau EXPENSE). Jika pengguna bilang ini pemasukan/pendapatan, paksa 'type' menjadi 'INCOME' walaupun gambarnya terlihat seperti struk belanja biasa!"

        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            )

        raw = response.choices[0].message.content.strip()
        logger.debug(f"Respons mentah dari Groq: {raw}")

        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(clean)
        logger.info(f"Berhasil mem-parsing JSON dari Groq: {data}")

        amount_val = data.get("amount")
        amount = float(amount_val) if amount_val is not None else 0.0

        return TransactionResult(
            type=data.get("type", "EXPENSE"),
            amount=amount,
            description=data.get("description", "Transaksi"),
            category=data.get("category", "Lainnya"),
            wallet_name=data.get("wallet_name") if data.get("wallet_name") else None,
            confidence=float(data.get("confidence", 0.5)),
            raw_text="",
            is_valid=data.get("is_valid", True),
            reason=data.get("reason", ""),
        )

    except Exception as e:
        logger.error(f"Gagal menganalisis dengan Groq: {str(e)}", exc_info=True)
        return TransactionResult(
            type="EXPENSE",
            amount=0,
            description="",
            category="Lainnya",
            wallet_name=None,
            confidence=0.0,
            raw_text="",
            is_valid=False,
            reason=f"Gagal menganalisis (Groq): {str(e)}",
        )

async def analyze_text_transaction(text: str) -> TransactionResult:
    logger.info(f"Menganalisis teks dengan Groq AI: {text}")

    if not client:
        logger.error("GROQ_API_KEY belum dikonfigurasi.")
        return TransactionResult("EXPENSE", 0, "", "Lainnya", "Utama", 0.0, "", False, "GROQ_API_KEY belum dikonfigurasi")

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": TEXT_EXTRACTION_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=512,
        )

        raw = response.choices[0].message.content.strip()
        logger.debug(f"Respons mentah (Teks) dari Groq: {raw}")

        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(clean)

        amount_val = data.get("amount")
        amount = float(amount_val) if amount_val is not None else 0.0

        return TransactionResult(
            type=data.get("type", "EXPENSE"),
            amount=amount,
            description=data.get("description", "Transaksi"),
            category=data.get("category", "Lainnya"),
            wallet_name=data.get("wallet_name") if data.get("wallet_name") else None,
            confidence=float(data.get("confidence", 0.9)),
            raw_text=text,
            is_valid=data.get("is_valid", True),
            reason=data.get("reason", ""),
        )

    except Exception as e:
        logger.error(f"Gagal menganalisis teks dengan Groq: {str(e)}", exc_info=True)
        return TransactionResult(
            type="EXPENSE", amount=0, description="", category="Lainnya",
            wallet_name=None, confidence=0.0, raw_text=text,
            is_valid=False, reason=f"Gagal menganalisis teks: {str(e)}"
        )
