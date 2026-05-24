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

# Yapılandırma ve Veritabanı (Kayıt sistemi için)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# Veritabanı Kurulumu (Hafıza için)
conn = sqlite3.connect('fabrika_arsiv.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS arsiv (id INTEGER PRIMARY KEY, konsept TEXT, prompt TEXT, basari_durumu TEXT)''')
conn.commit()

# Şirket Hafızası
sirket_hafizasi = {"secilen_nis": "", "patron_notlari": [], "bekleyen_gorsel": None}

# --- 1. STRATEJİ & PAZAR ANALİZİ ---
async def fikirver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = await update.message.reply_text("🔍 Pazar verileri analiz ediliyor...")
    sistem = """Sen kıdemli bir Etsy Veri Analistisin. Şu an dünyada en çok satan, 
    yazısız, yüksek kontrastlı, maskülen/streetwear tarzı 3 nişi (Streetwear, Western, Dark Geometry) analiz et. 
    Hangisi en çok kâr bırakır? Neden? 3 öneri sun."""
    
    cevap = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": sistem}, {"role": "user", "content": "3 karlı niş öner."}])
    await mesaj.edit_text(f"📈 **Strateji Raporu:**\n{cevap.choices[0].message.content}\n\nSeçmek için: /sec [Niş Adı]")

# --- 2. SANAT YÖNETİMİ (KUSURSUZ PROMPT KORUMASI) ---
def departman_sanat_yonetmeni(konsept, notlar):
    sistem = """Sen bir Sanat Direktörüsün. Gelen konsepti DALL-E 3 promptuna çevir. 
    KATİ KURAL: "textless, strictly NO text, NO words, NO letters, isolated on solid white background".
    Kalite parametreleri: "masterpiece, sharp focus, vector art, high contrast, bold lines, 8k". 
    ASLA yazı yazma. Yazı çıkarsa sistem çöker, patron kızar."""
    cevap = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": sistem}, {"role": "user", "content": f"Konsept: {konsept}, Ek Notlar: {notlar}"}])
    return cevap.choices[0].message.content

# --- 3. ÜRETİM VE HATA YÖNETİMİ ---
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sirket_hafizasi["secilen_nis"]:
        await update.message.reply_text("🚨 Önce /fikirver ve /sec yapmalısın.")
        return
    
    try:
        mesaj = await update.message.reply_text("🎨 Üretim bandı çalışıyor...")
        prompt = departman_sanat_yonetmeni(sirket_hafizasi["secilen_nis"], sirket_hafizasi["patron_notlari"])
        
        # DALL-E 3 Üretim (Hata Yönetimi ile)
        response = client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", quality="hd", n=1)
        img_data = requests.get(response.data[0].url).content
        
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        # Veritabanına Kayıt
        c.execute("INSERT INTO arsiv (konsept, prompt, basari_durumu) VALUES (?, ?, ?)", (sirket_hafizasi['secilen_nis'], prompt, "Beklemede"))
        conn.commit()
        
        keyboard = [[InlineKeyboardButton("✅ 300 DPI İndir", callback_data="onay_ver")], [InlineKeyboardButton("❌ Revize Et", callback_data="reddet")]]
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=img_data, caption="Prototip Hazır.", reply_markup=InlineKeyboardMarkup(keyboard))
        await mesaj.delete()
        
    except Exception as e:
        await update.message.reply_text(f"🚨 Fabrika arızalandı: {str(e)}\n\nLütfen OpenAI bakiyesini kontrol et.")

# --- 4. MATBAA MODÜLÜ ---
def baski_kalitesine_yukselt(img_bytes):
    img = Image.open(BytesIO(img_bytes)).resize((4000, 4000), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG", dpi=(300, 300))
    buf.seek(0)
    return buf

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "onay_ver":
        await context.bot.send_document(query.message.chat_id, document=baski_kalitesine_yukselt(sirket_hafizasi["bekleyen_gorsel"]), filename="PrintReady_300DPI.png")
    elif query.data == "reddet":
        await query.edit_message_caption(caption="❌ Reddedildi. Notlarını /duzelt [notun] ile gönder.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("fikirver", fikirver))
    app.add_handler(CommandHandler("sec", sec))
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", lambda u, c: asyncio.create_task(u.message.reply_text("📝 Not alındı."))))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
