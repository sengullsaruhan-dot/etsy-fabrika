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

# ----------------- DEPARTMAN 1: STRATEJİ VE ARAŞTIRMA -----------------
def departman_arastirma():
    notlar = " ".join(sirket_hafizasi["patron_notlari"])
    sistem_mesaji = """Sen profesyonel bir Etsy ürün stratejistisin.
    
    MAĞAZA KONSEPTİ VE KESİN KURALLAR:
    1. Mağazamız sadece şu ürünleri satar: Sokak giyimi (streetwear) için vektörel grafikler ve Western retro tarzı poster tasarımları. Telefon kılıfı, kupa veya rastgele eşyalar önerme.
    2. Tasarımlar maskülen, keskin hatlı, net çizgili ve 'Eşref Tek' estetiği denilen sert ve duru bir yapıda olmalıdır. Karmaşık ve çorba gibi görüntülerden kaçın.
    3. ASLA tipografi, yazı, kelime, harf veya alıntı içeren ürünler önerme. Sadece görsel illüstrasyon.
    
    Bana SADECE şu formatta yanıt ver:
    [Ürün Tipi] - [Detaylı Konsept ve Hedef Kitle]"""
    
    if notlar:
        sistem_mesaji += f"\nALINAN GERİ BİLDİRİMLER: {notlar}"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Belirlenen mağaza konseptine uygun, yüksek satış potansiyelli ve yazısız bir dijital ürün stratejisi belirle."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        logging.error(f"Araştırma hatası: {e}")
        return "Streetwear Graphic - A lone cowboy silhouette standing in a vast desert, sharp vector style, highly defined edges."

# ----------------- DEPARTMAN 2: SANAT YÖNETMENİ -----------------
def departman_sanat_yonetmeni(arastirma_sonucu):
    sistem_mesaji = """Sen uzman bir görsel prompt mühendisisin.
    Gelen konsepti alıp İngilizce, virgüllerle ayrılmış net bir prompta çevir.
    
    ZORUNLU PARAMETRELER:
    1. Promptun sonuna kesinlikle ekle: "textless, strictly NO text, NO words, NO letters, NO watermarks, NO signatures, clean solid background".
    2. Çizim kalitesi için ekle: "sharp focus, clean masculine lines, high contrast, minimalist but detailed, vector illustration style, 8k resolution".
    
    Sadece prompt metnini ver."""
    
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": f"Şu konsepti kurallara uygun bir görsel promptuna çevir:\n{arastirma_sonucu}"}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        return f"{arastirma_sonucu}, sharp focus, clean masculine lines, vector style, textless, strictly no text, no words, no watermarks, solid background, 8k resolution"

# ----------------- DEPARTMAN 3: ÜRETİM -----------------
def departman_uretim(prompt):
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logging.error(f"Üretim hatası: {e}")
        return None

# ----------------- DEPARTMAN 4: PAKETLEME -----------------
def paketle_pdf(img_bytes):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    img = ImageReader(BytesIO(img_bytes))
    c.drawImage(img, 0, 0, width=595, height=842)
    c.save()
    buf.seek(0)
    return buf

# ----------------- KULLANICI ARAYÜZÜ -----------------
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    durum_mesaji = await update.message.reply_text("Strateji ve pazar analizi başlatıldı.")
    
    arastirma = departman_arastirma()
    sirket_hafizasi["urun_tipi"] = arastirma
    await durum_mesaji.edit_text(f"Strateji Belirlendi:\n{arastirma}\n\nTeknik parametreler hazırlanıyor.")
    
    kusursuz_prompt = departman_sanat_yonetmeni(arastirma)
    sirket_hafizasi["son_prompt"] = kusursuz_prompt
    await durum_mesaji.edit_text("Görsel motoru üretimi gerçekleştiriyor. Lütfen bekleyin.")
    
    img_data = departman_uretim(kusursuz_prompt)
    
    if img_data:
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [
            [InlineKeyboardButton("Onayla ve İndir", callback_data="onay_ver")],
            [InlineKeyboardButton("Reddet ve Geri Bildirim Ver", callback_data="reddet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img_data,
            caption=f"Yeni Ürün Prototiplendi.\n\nStrateji: {arastirma}",
            reply_markup=reply_markup
        )
        await durum_mesaji.delete()
    else:
        await durum_mesaji.edit_text("Bağlantı hatası oluştu, lütfen işlemi tekrarlayın.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        await query.edit_message_caption(caption="Onaylandı. Dosya hazırlanıyor.")
        img_data = sirket_hafizasi["bekleyen_gorsel"]
        pdf_dosya = paketle_pdf(img_data)
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_dosya,
            filename="Tasari_Export.pdf",
            caption="Baskıya ve satışa hazır dosya."
        )
        
    elif query.data == "reddet":
        await query.edit_message_caption(caption="Reddedildi.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Tasarımda revize edilmesi gereken kısımları '/duzelt [notunuz]' formatında iletin."
        )

async def duzelt_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Geri bildirim metni bulunamadı. Örnek kullanım: /duzelt Çizgiler daha kalın olmalı.")
        return
    
    elestiri = " ".join(context.args)
    sirket_hafizasi["patron_notlari"].append(elestiri)
    
    await update.message.reply_text(f"Geri bildirim sisteme kaydedildi: '{elestiri}'.\nYeni iterasyon için /uretim_baslat komutunu çalıştırabilirsiniz.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", duzelt_komutu))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("Sistem Aktif.")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
