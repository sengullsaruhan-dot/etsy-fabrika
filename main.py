import logging
import requests
import openai
import os
import asyncio
import urllib.parse
from io import BytesIO
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
    
    MAĞAZA KONSEPTİ VE KESİN KURALLAR:
    1. Sadece Print-on-Demand (Tişört/Sweatshirt baskısı) veya Dijital Poster için uygun, tekil ve devasa kalitede grafikler önereceksin.
    2. Tasarımlar maskülen, keskin hatlı, streetwear (sokak stili) veya Western retro estetiğinde ('Eşref Tek' tarzı sert ve net) olmalıdır.
    3. ASLA VE ASLA tipografi, yazı, kelime, harf, logo veya çerçeve içermeyecek. Karmaşık çorba gibi görüntüler YASAK.
    4. Odak noktası tek bir güçlü obje veya karakter olmalıdır.
    
    Bana SADECE şu formatta yanıt ver:
    [Ürün Tipi] - [Detaylı Konsept ve Hedef Kitle]"""
    
    if notlar:
        sistem_mesaji += f"\nALINAN GERİ BİLDİRİMLER (BUNLARA KESİNLİKLE UY): {notlar}"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Etsy'de rakipsiz olacak, tek bir odak noktası olan, yazısız bir dijital grafik stratejisi belirle."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        logging.error(f"Araştırma hatası: {e}")
        return "Streetwear T-Shirt Graphic - A lone highly detailed cowboy skull with a vintage hat, pure vector style."

# ----------------- DEPARTMAN 2: SANAT YÖNETMENİ -----------------
def departman_sanat_yonetmeni(arastirma_sonucu):
    sistem_mesaji = """Sen uzman bir görsel prompt mühendisisin.
    Gelen konsepti alıp İngilizce, virgüllerle ayrılmış kusursuz bir FLUX promptuna çevir.
    
    HAYATİ PARAMETRELER:
    1. Promptun sonuna ŞUNU KESİNLİKLE EKLE: "textless, strictly NO text, NO words, NO letters, NO fonts, NO watermarks, NO signatures, isolated on solid white background".
    2. Kalite için ekle: "masterpiece, sharp focus, clean crisp lines, high contrast, minimalist but highly detailed, vector illustration style, 8k resolution, perfectly centered".
    
    Sadece prompt metnini ver, tek kelime fazla yazma."""
    
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
        return f"{arastirma_sonucu}, masterpiece, sharp focus, vector style, textless, strictly no text, no words, no watermarks, solid white background, perfectly centered, 8k resolution"

# ----------------- DEPARTMAN 3: ÜRETİM (ETSY STANDARTLARI) -----------------
def departman_uretim(prompt):
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        # Etsy standardı için çözünürlüğü 2000x2000 piksel olarak zorluyoruz.
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=2000&height=2000&model=flux&nologo=true&enhance=true"
        
        response = requests.get(url, timeout=60) # Yüksek çözünürlük için zaman aşımını uzattık
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logging.error(f"Üretim hatası: {e}")
        return None

# ----------------- KULLANICI ARAYÜZÜ -----------------
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    durum_mesaji = await update.message.reply_text("Strateji ve pazar analizi başlatıldı...")
    
    arastirma = departman_arastirma()
    sirket_hafizasi["urun_tipi"] = arastirma
    await durum_mesaji.edit_text(f"Strateji Belirlendi:\n{arastirma}\n\nTeknik parametreler hazırlanıyor...")
    
    kusursuz_prompt = departman_sanat_yonetmeni(arastirma)
    sirket_hafizasi["son_prompt"] = kusursuz_prompt
    await durum_mesaji.edit_text("Etsy uyumlu yüksek çözünürlüklü (2000x2000) görsel üretiliyor. Lütfen bekleyin...")
    
    img_data = departman_uretim(kusursuz_prompt)
    
    if img_data:
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [
            [InlineKeyboardButton("Onayla ve Yüksek Kalite İndir", callback_data="onay_ver")],
            [InlineKeyboardButton("Reddet ve Geri Bildirim Ver", callback_data="reddet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Önizleme olarak gönder
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img_data,
            caption=f"Yeni Ürün Prototiplendi.\n\nStrateji: {arastirma}",
            reply_markup=reply_markup
        )
        await durum_mesaji.delete()
    else:
        await durum_mesaji.edit_text("Üretim zaman aşımına uğradı, lütfen işlemi tekrarlayın.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        await query.edit_message_caption(caption="Onaylandı. Sıkıştırılmamış kaynak dosya hazırlanıyor...")
        img_data = sirket_hafizasi["bekleyen_gorsel"]
        
        # Görseli Telegram'dan "Dosya" olarak gönderiyoruz (Kalite düşmemesi için)
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=BytesIO(img_data),
            filename="Etsy_HighRes_2000x2000.png",
            caption="Baskıya ve Etsy'ye doğrudan yüklemeye hazır yüksek çözünürlüklü dosya."
        )
        
    elif query.data == "reddet":
        await query.edit_message_caption(caption="Reddedildi.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Tasarımda revize edilmesi gereken kısımları '/duzelt [notunuz]' formatında iletin."
        )

async def duzelt_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Geri bildirim metni bulunamadı. Örnek kullanım: /duzelt Ana obje çok küçüktü, ekranı kaplamalı.")
        return
    
    elestiri = " ".join(context.args)
    sirket_hafizasi["patron_notlari"].append(elestiri)
    
    await update.message.reply_text(f"Geri bildirim sisteme kaydedildi: '{elestiri}'.\nYeni üretim için /uretim_baslat komutunu çalıştırabilirsiniz.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", duzelt_komutu))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("Sistem Aktif ve Etsy Standartlarında Çalışıyor.")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
