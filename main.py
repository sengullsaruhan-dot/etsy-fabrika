import logging
import requests
import openai
import os
import asyncio
import urllib.parse
from io import BytesIO
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

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
    
    MAĞAZA KONSEPTİ:
    1. Sadece Print-on-Demand (Tişört/Poster) için uygun, tekil grafikler üret.
    2. Tasarımlar maskülen, keskin hatlı, streetwear veya Western retro estetiğinde ('Eşref Tek' tarzı sert ve net) olmalıdır.
    3. ASLA tipografi, yazı, kelime, harf içermeyecek.
    4. Odak noktası tek bir güçlü obje veya karakter olmalıdır.
    
    Bana SADECE şu formatta yanıt ver:
    [Ürün Tipi] - [Detaylı Konsept]"""
    
    if notlar:
        sistem_mesaji += f"\nPATRONUN KESİN EMRİ: {notlar}"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Etsy'de satacak, maskülen, yazısız tek bir grafik konsepti ver."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        return "Streetwear Graphic - A lone highly detailed cowboy skull with a vintage hat, pure vector style."

# ----------------- DEPARTMAN 2: SANAT YÖNETMENİ -----------------
def departman_sanat_yonetmeni(arastirma_sonucu):
    sistem_mesaji = """Sen uzman bir görsel prompt mühendisisin.
    Gelen konsepti alıp İngilizce, virgüllerle ayrılmış kusursuz bir FLUX promptuna çevir.
    
    HAYATİ PARAMETRELER:
    1. Promptun sonuna ŞUNU KESİNLİKLE EKLE: "textless, strictly NO text, NO words, NO watermarks, isolated on solid white background".
    2. Kalite için ekle: "masterpiece, sharp focus, clean crisp lines, high contrast, vector illustration style, perfectly centered".
    
    Sadece prompt metnini ver."""
    
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
        return f"{arastirma_sonucu}, masterpiece, sharp focus, vector style, textless, strictly no text, solid white background, perfectly centered"

# ----------------- DEPARTMAN 3: HIZLI PROTOTİP ÜRETİM -----------------
def departman_uretim(prompt):
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"
        
        response = requests.get(url, timeout=60) 
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logging.error(f"Üretim hatası: {e}")
        return None

# ----------------- DEPARTMAN 4: MATBAA (300 DPI UPSCALE) -----------------
def baski_kalitesine_yukselt(img_bytes):
    # Görseli hafızaya al
    img = Image.open(BytesIO(img_bytes))
    
    # 4000x4000 Piksele Keskinleştirerek Büyüt (Lanczos Algoritması)
    baski_boyutu = (4000, 4000)
    img_yuksek_kalite = img.resize(baski_boyutu, Image.Resampling.LANCZOS)
    
    # 300 DPI olarak Sıkıştırmasız PNG formatında paketle
    baski_dosyasi = BytesIO()
    img_yuksek_kalite.save(baski_dosyasi, format="PNG", dpi=(300, 300))
    baski_dosyasi.seek(0)
    
    return baski_dosyasi

# ----------------- KULLANICI ARAYÜZÜ -----------------
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    durum_mesaji = await update.message.reply_text("Strateji belirleniyor...")
    
    arastirma = departman_arastirma()
    sirket_hafizasi["urun_tipi"] = arastirma
    await durum_mesaji.edit_text(f"Strateji Belirlendi:\n{arastirma}\n\nPrototip çiziliyor...")
    
    kusursuz_prompt = departman_sanat_yonetmeni(arastirma)
    sirket_hafizasi["son_prompt"] = kusursuz_prompt
    
    img_data = departman_uretim(kusursuz_prompt)
    
    if img_data:
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [
            [InlineKeyboardButton("Onayla (300 DPI Matbaa Çıktısı Al)", callback_data="onay_ver")],
            [InlineKeyboardButton("Reddet ve Geri Bildirim Ver", callback_data="reddet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img_data,
            caption=f"Prototip Hazır.\n\nStrateji: {arastirma}",
            reply_markup=reply_markup
        )
        await durum_mesaji.delete()
    else:
        await durum_mesaji.edit_text("Üretim zaman aşımına uğradı, lütfen tekrar deneyin.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        await query.edit_message_caption(caption="Onaylandı. Matbaa görseli 4000x4000 piksel ve 300 DPI kalitesine yükseltiyor. Bu işlem birkaç saniye sürebilir...")
        
        img_data = sirket_hafizasi["bekleyen_gorsel"]
        yuksek_kalite_dosya = baski_kalitesine_yukselt(img_data)
        
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=yuksek_kalite_dosya,
            filename="Etsy_PrintReady_300DPI.png",
            caption="🏆 İşte gerçek baskı kalitesi! 300 DPI, 4000x4000 çözünürlüklü kayıpsız PNG dosyan."
        )
        
    elif query.data == "reddet":
        await query.edit_message_caption(caption="Reddedildi.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Tasarımda revize edilmesi gereken kısımları '/duzelt [notunuz]' formatında iletin."
        )

async def duzelt_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Lütfen notunuzu ekleyin. Örnek: /duzelt Daha asi görünmeli.")
        return
    
    elestiri = " ".join(context.args)
    sirket_hafizasi["patron_notlari"].append(elestiri)
    
    await update.message.reply_text(f"Not sisteme işlendi: '{elestiri}'.\nYeni üretim için /uretim_baslat yazabilirsin.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", duzelt_komutu))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("Sistem Aktif. Matbaa modülü devrede.")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
