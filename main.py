import logging
import requests
import openai
import os
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from reportlab.pdfgen import canvas
from PIL import Image, ImageStat
from reportlab.lib.utils import ImageReader

# Railway'deki "Variables" kısmından güvenli çekim
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# QC Laboratuvarı
def kalite_kontrol(img_bytes):
    try:
        img = Image.open(BytesIO(img_bytes)).convert("L")
        stat = ImageStat.Stat(img)
        if stat.stddev[0] < 40: 
            return False, "Düşük Kontrast"
        return True, "Onaylandı"
    except Exception as e:
        return False, f"Bozuk Dosya: {e}"

# Üretim Motoru (DALL-E 2/3 - Hesabına göre uygun olanı seçer)
def uret_openai(tema):
    try:
        response = client.images.generate(
            model="dall-e-2", 
            prompt=f"Professional coloring book page, {tema}, thick clean black lines, white background, no shading, high resolution.",
            n=1,
            size="1024x1024"
        )
        return requests.get(response.data[0].url).content
    except Exception as e:
        logging.error(f"OpenAI Hatası: {e}")
        return None

# PDF Paketleyici
def paketle_pdf(img_bytes):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    c.drawImage(ImageReader(BytesIO(img_bytes)), 47, 171, width=500, height=500)
    c.save()
    buf.seek(0)
    return buf

# Telegram Komutu
async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = "mystical forest animals" if not context.args else " ".join(context.args)
    await update.message.reply_text(f"🏭 Bulut Fabrikası '{tema}' için çalışıyor...")
    
    img_data = uret_openai(tema)
    if img_data:
        qc_ok, neden = kalite_kontrol(img_data)
        if qc_ok:
            await update.message.reply_document(paketle_pdf(img_data), filename="Etsy_Premium.pdf", caption=f"🏆 Hazır: {tema}")
        else:
            await update.message.reply_text(f"🚨 QC Hatası: {neden}")
    else:
        await update.message.reply_text("🚨 Görsel üretilemedi.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("uretim_baslat", baslat))
    app.run_polling()
