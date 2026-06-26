import json
import re
import logging
import base64
from groq import AsyncGroq
from app.core.config import settings
from dataclasses import dataclass

logger = logging.getLogger(__name__)

client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

@dataclass
class TransactionResult:
    type: str           # "INCOME" atau "EXPENSE"
    amount: float
    description: str
    category: str
    confidence: float   # 0.0 - 1.0
    raw_text: str
    is_valid: bool
    reason: str

SYSTEM_PROMPT = """
Kamu adalah asisten keuangan yang menganalisis gambar struk belanja, nota, atau bukti transaksi keuangan.

Tugasmu adalah mengekstrak informasi transaksi dari gambar dan mengembalikan HANYA JSON murni (tanpa teks penjelasan apapun) dengan format persis seperti ini:
{
  "type": "INCOME" atau "EXPENSE",
  "amount": <angka tanpa titik/koma, contoh: 50000>,
  "description": "<daftar barang yang dibeli dipisahkan dengan koma. Jika bukan struk belanja, isi dengan deskripsi singkat>",
  "category": "<salah satu: Makanan, Transportasi, Belanja, Kesehatan, Hiburan, Tagihan, Gaji, Investasi, Lainnya>",
  "confidence": <0.0 sampai 1.0>,
  "is_valid": <true jika ini adalah transaksi keuangan, false jika bukan>,
  "reason": "<alasan jika is_valid false, kosong jika valid>"
}

Aturan:
- Jika ada banyak item, jumlahkan semuanya menjadi satu total.
- Gunakan TOTAL atau GRAND TOTAL jika tersedia.
- Struk belanja = EXPENSE, bukti transfer masuk = INCOME, slip gaji = INCOME.
- Jika gambar tidak jelas atau bukan transaksi keuangan, set is_valid: false.
- Dilarang memberikan teks pengantar atau penutup. Berikan JSON murni.
""".strip()

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def analyze_transaction(image_path: str) -> TransactionResult:
    logger.info(f"Menganalisis gambar {image_path} langsung dengan Groq Vision AI.")

    if not client:
        logger.error("GROQ_API_KEY belum dikonfigurasi.")
        return TransactionResult("EXPENSE", 0, "", "Lainnya", 0.0, "", False, "GROQ_API_KEY belum dikonfigurasi di .env")

    try:
        base64_image = encode_image(image_path)
        response = await client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT},
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

        return TransactionResult(
            type=data.get("type", "EXPENSE"),
            amount=float(data.get("amount", 0)),
            description=data.get("description", "Transaksi"),
            category=data.get("category", "Lainnya"),
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
            confidence=0.0,
            raw_text="",
            is_valid=False,
            reason=f"Gagal menganalisis (Groq): {str(e)}",
        )
