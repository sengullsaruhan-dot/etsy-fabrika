import logging
import requests
import openai
import os
import asyncio
import urllib.parse
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

sirket_hafizasi = {
    "urun_tipi": "",
    "son_prompt": "",
    "patron_notlari": [], 
    "bekleyen_gorsel": None
}

# ----------------- DEPARTMAN 1: CEO & ARAŞTIRMACI -----------------
def departman_arastirma():
    notlar = " ".join(sirket_hafizasi["patron_notlari"])
    sistem_mesaji = """Sen üst düzey bir Etsy ürün stratejistisin.
    
    KESİN KURALLARIN:
    1. ASLA tipografi, yazı, kelime, harf veya alıntı (quote) içeren ürünler önerme. Yapay zeka yazıları bozar.
    2. Tasarımlar karmaşık bir "çorba" olmamalı. Tek bir net odak noktası (ana obje/karakter) olmalı.
    3. Konseptlerin her zaman 'Western Retro', 'Streetwear (Sokak Stili)', veya keskin hatlı ikonik tasarımlar üzerine olmalı.
    
    Bana SADECE şu formatta yanıt ver:
    [Ürün Tipi] - [Detaylı Konsept ve Hedef Kitle]"""
    
    if notlar:
        sistem_mesaji += f"\nPATRONUN KESİN EMRİ: {notlar}"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Bana yazısız, keskin hatlı, çok satacak bir dijital ürün konsepti ver."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        logging.error(f"Araştırma Çöktü: {e}")
        return "Streetwear T-Shirt Graphic - A lone cowboy silhouette standing in a vast desert, sharp vector style, no text."

# ----------------- DEPARTMAN 2: SANAT YÖNETMENİ -----------------
def departman_sanat_yonetmeni(arastirma_sonucu):
    sistem_mesaji = """Sen dünyanın en iyi görsel Prompt mühendisisin.
    Gelen konsepti alıp İngilizce, virgüllerle ayrılmış kusursuz bir prompta çevir.
    
    HAYATİ KURALLAR (Bunları prompta mutlaka dahil et):
    1. Mutlaka şunu ekle: "textless, strictly NO text, NO words, NO letters, NO watermarks, NO signatures, clean background".
    2. Tasarımın çamur gibi olmaması için şu terimleri kullan: "sharp focus, clean lines, high contrast, masterpiece, 8k resolution, vector illustration style".
    3. Konuya göre "Western retro aesthetic" veya "streetwear graphic design" terimlerini ekle.
    
    Sadece prompt metnini ver, başka hiçbir şey yazma."""
    
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": f"Şu konsepti kusursuz bir görsel promptuna çevir:\n{arastirma_sonucu}"}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        return f"{arastirma_sonucu}, masterpiece, sharp focus, vector style, textless, strictly no text, no words, no watermarks, clean background, 8k resolution"

# ----------------- DEPARTMAN 3: ÜRETİM (FLUX MOTORU) -----------------
def departman_uretim(prompt):
    try:
        # Prompt'u URL için güvenli hale getiriyoruz
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logging.error(f"Üretim Hatası: {e}")
        return None

# ----------------- DEPARTMAN 4: PAKETLEME VE LOJİSTİK -----------------
def paketle_pdf(img_bytes):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    img = ImageReader(BytesIO(img_bytes))
    c.drawImage(img, 0, 0, width=595, height=842)
    c.save()
    buf.seek(0)
    return buf

# ----------------- TELEGRAM PANELİ -----------------
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    durum_mesaji = await update.message.reply_text("Strateji belirleniyor...")
    
    arastirma = departman_arastirma()
    sirket_hafizasi["urun_tipi"] = arastirma
    await durum_mesaji.edit_text(f"Karar Verildi:\n{arastirma}\n\nPrompt yazılıyor...")
    
    kusursuz_prompt = departman_sanat_yonetmeni(arastirma)
    sirket_hafizasi["son_prompt"] = kusursuz_prompt
    await durum_mesaji.edit_text("Görsel motoru çalışıyor, detaylar işleniyor...")
    
    img_data = departman_uretim(kusursuz_prompt)
    
    if img_data:
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [
            [InlineKeyboardButton("Onayla ve PDF Yap", callback_data="onay_ver")],
            [InlineKeyboardButton("Reddet (Hatalı/Kalitesiz)", callback_data="reddet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img_data,
            caption=f"Yeni Ürün Prototiplendi.\n\nStrateji: {arastirma}\n\nİşlem seçiniz:",
            reply_markup=reply_markup
        )
        await durum_mesaji.delete()
    else:
        await durum_mesaji.edit_text("Bağlantı hatası, lütfen tekrar deneyin.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        await query.edit_message_caption(caption="Onaylandı. PDF hazırlanıyor...")
        img_data = sirket_hafizasi["bekleyen_gorsel"]
        pdf_dosya = paketle_pdf(img_data)
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_dosya,
            filename=f"Premium_Design.pdf",
            caption="Satışa hazır PDF dosyası."
        )
        
    elif query.data == "reddet":
        await query.edit_message_caption(caption="Reddedildi. Sebep bekleniyor.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Tasarımda ne eksikti? Lütfen '/duzelt [sebebiniz]' formatında geri bildirim yazın."
        )

async def duzelt_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Lütfen eleştirinizi ekleyin. Örnek: /duzelt Ana obje çok küçüktü.")
        return
    
    elestiri = " ".join(context.args)
    sirket_hafizasi["patron_notlari"].append(elestiri)
    
    await update.message.reply_text(f"Geri bildirim sisteme eklendi: '{elestiri}'.\nYeni üretim için /uretim_baslat komutunu kullanabilirsiniz.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", duzelt_komutu))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("Sistem Aktif!")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
