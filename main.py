import logging
import requests
import os
import asyncio
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from reportlab.pdfgen import canvas
from PIL import Image
from reportlab.lib.utils import ImageReader

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# 1. Pollinations API Motoru (API Anahtarı gerekmez, sınırsız ve hızlı)
def uret_gorsel(tema):
    try:
        # Prompt'u renklendirme kitabı için optimize ettik
        prompt = f"coloring book page for adults, {tema}, high quality, vector style, black and white, clean lines, no shading"
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logging.error(f"Üretim Hatası: {e}")
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
    
    img_data = uret_gorsel(tema)
    if img_data:
        pdf_dosya = paketle_pdf(img_data)
        await update.message.reply_document(pdf_dosya, filename="Etsy_Premium.pdf", caption=f"🏆 Hazır: {tema}")
    else:
        await update.message.reply_text("🚨 Görsel motoru şu an meşgul, lütfen tekrar dene.")

# 4. Bot Başlatıcı
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    print("💎 Fabrika 7/24 Aktif!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
