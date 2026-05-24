import logging
import requests
import openai
import os
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from reportlab.pdfgen import canvas
from PIL import Image
from reportlab.lib.utils import ImageReader

# Railway'deki "Variables" kısmından anahtarları çeker
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# 1. OpenAI Üretim Motoru (Model hata yönetimi ile)
def uret_openai(tema):
    models = ["dall-e-3", "dall-e-2"]
    for model_name in models:
        try:
            response = client.images.generate(
                model=model_name,
                prompt=f"Professional coloring book page for adults, {tema}, thick clean black lines, white background, high resolution.",
                n=1, size="1024x1024"
            )
            return requests.get(response.data[0].url).content
        except Exception as e:
            logging.error(f"{model_name} denendi, hata: {e}")
    return None

# 2. PDF Paketleyici
def paketle_pdf(img_bytes):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    img = ImageReader(BytesIO(img_bytes))
    c.drawImage(img, 47, 171, width=500, height=500)
    c.save()
    buf.seek(0)
    return buf

# 3. Telegram Komutu
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = "mystical forest" if not context.args else " ".join(context.args)
    await update.message.reply_text(f"🏭 Fabrika '{tema}' için çalışıyor...")
    
    img_data = uret_openai(tema)
    if img_data:
        pdf_dosya = paketle_pdf(img_data)
        await update.message.reply_document(pdf_dosya, filename="Etsy_Premium.pdf", caption=f"🏆 Hazır: {tema}")
    else:
        await update.message.reply_text("🚨 OpenAI tüm modellerde hata verdi. Lütfen bakiye/anahtar kontrolü yap.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Çakışmaları engellemek için kesin çözüm
    app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    print("💎 Fabrika 7/24 Aktif!")
    app.run_polling()
