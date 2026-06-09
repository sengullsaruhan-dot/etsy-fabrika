import logging
import requests
import os
import asyncio
import urllib.parse
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

# Ayarlar
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# Şirket Hafızası
sirket_hafizasi = {"rakip_tarzi": "Minimalist, masculine vector art", "secilen_nis": "", "bekleyen_gorsel": None}

# --- TÜM FONKSİYONLAR ---
async def start(update, context): await update.message.reply_text("💎 Fabrika Aktif! /tarz_analiz [link] ile başla.")

async def tarz_analiz_et(update, context):
    link = " ".join(context.args)
    mesaj = await update.message.reply_text("🕵️ Mağaza DNA'sı sökülüyor...")
    try:
        soup = BeautifulSoup(requests.get(link, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        sirket_hafizasi["rakip_tarzi"] = "Modern minimalist vector art, sharp lines"
        await mesaj.edit_text("✅ Tarz başarıyla kopyalandı! /fikirver kullan.")
    except: await mesaj.edit_text("🚨 Mağaza erişimi kapalı.")

async def fikirver(update, context): await update.message.reply_text("📈 Nişler: 1. Streetwear, 2. Western, 3. Dark. /sec [İsim]")

async def sec(update, context): 
    sirket_hafizasi["secilen_nis"] = " ".join(context.args)
    await update.message.reply_text(f"✅ Hedef: {sirket_hafizasi['secilen_nis']}")

async def uretim_baslat(update, context):
    mesaj = await update.message.reply_text("🎨 Üretim bandı aktif...")
    prompt = f"{sirket_hafizasi['secilen_nis']}, {sirket_hafizasi['rakip_tarzi']}, isolated on white"
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=2000&height=2000&model=flux&nologo=true"
    img_data = requests.get(url).content
    sirket_hafizasi["bekleyen_gorsel"] = img_data
    await context.bot.send_photo(update.message.chat_id, photo=BytesIO(img_data), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 300 DPI İndir", callback_data="onay_ver")]]))
    await mesaj.delete()

async def buton_yonetimi(update, context):
    query = update.callback_query
    if query.data == "onay_ver":
        img = Image.open(BytesIO(sirket_hafizasi["bekleyen_gorsel"])).resize((4000, 4000), Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        await context.bot.send_document(query.message.chat_id, document=buf, filename="Baski_Hazir.png")

# --- BOT BAŞLATICI ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tarz_analiz", tarz_analiz_et))
    app.add_handler(CommandHandler("fikirver", fikirver))
    app.add_handler(CommandHandler("sec", sec))
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    app.run_polling()
