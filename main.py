import logging
import requests
import openai
import os
import asyncio
import sqlite3
from io import BytesIO
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# Veritabanını RAM üzerinde çalıştır (Hata vermemesi için)
conn = sqlite3.connect(':memory:', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE arsiv (id INTEGER PRIMARY KEY, konsept TEXT, prompt TEXT)')

sirket_hafizasi = {"secilen_nis": "", "patron_notlari": [], "bekleyen_gorsel": None}

async def fikirver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = await update.message.reply_text("🔍 Pazar verileri analiz ediliyor...")
    try:
        sistem = "Sen Etsy stratejistisin. Streetwear, Western Retro, Dark Geometry nişlerini analiz et."
        cevap = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": sistem}, {"role": "user", "content": "3 karlı niş öner."}])
        await mesaj.edit_text(f"📈 **Strateji:**\n{cevap.choices[0].message.content}\n\n/sec [İsim] ile seç.")
    except Exception as e:
        await mesaj.edit_text(f"🚨 Hata: {e}")

async def sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sirket_hafizasi["secilen_nis"] = " ".join(context.args)
    await update.message.reply_text(f"✅ Strateji: {sirket_hafizasi['secilen_nis']}")

async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sirket_hafizasi["secilen_nis"]:
        await update.message.reply_text("🚨 /fikirver yapmadın!")
        return
    mesaj = await update.message.reply_text("🎨 Üretiliyor...")
    try:
        # Prompt Oluşturma
        konsept = sirket_hafizasi["secilen_nis"]
        prompt = f"{konsept}, masterpiece, sharp focus, vector art, high contrast, textless, strictly NO text, NO words, isolated on white background"
        
        # DALL-E 3
        response = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="hd", n=1)
        img_data = requests.get(response.data[0].url).content
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [[InlineKeyboardButton("✅ 300 DPI İndir", callback_data="onay_ver")]]
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=img_data, caption="Prototip hazır.", reply_markup=InlineKeyboardMarkup(keyboard))
        await mesaj.delete()
    except Exception as e:
        await update.message.reply_text(f"🚨 Üretim Hatası: {str(e)}")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "onay_ver":
        # 300 DPI İşlemci
        img = Image.open(BytesIO(sirket_hafizasi["bekleyen_gorsel"])).resize((4000, 4000), Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        await context.bot.send_document(query.message.chat_id, document=buf, filename="Final_Print_300DPI.png")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("fikirver", fikirver))
    app.add_handler(CommandHandler("sec", sec))
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    app.run_polling()
