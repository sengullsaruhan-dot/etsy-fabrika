import logging
import requests
import openai
import os
import asyncio
import random
import urllib.parse
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Railway Ortam Değişkenleri
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# Şirket Hafızası (Öğrenen Algoritma)
sirket_hafizasi = {
    "urun_tipi": "",
    "son_prompt": "",
    "patron_notlari": [], 
    "bekleyen_gorsel": None
}

# ----------------- DEPARTMAN 1: CEO & ARAŞTIRMACI -----------------
def departman_arastirma():
    notlar = " ".join(sirket_hafizasi["patron_notlari"])
    sistem_mesaji = """Sen milyoner bir Etsy stratejistisin. Görevin, bugün Etsy'de en çok satacak, rekabetin düşük olduğu dijital ürünü belirlemek.
    Ürün tipleri şunlar olabilir: Western retro posterler, streetwear tişört grafikleri, minimalist duvar sanatı, vintage tipografi tasarımları veya kupa baskıları.
    Bana SADECE şu formatta yanıt ver:
    [Ürün Tipi] - [Detaylı Konsept ve Hedef Kitle]"""
    
    if notlar:
        sistem_mesaji += f"\nPATRONUN KESİN EMRİ (Bunlara dikkat et): {notlar}"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Bugün Etsy'de ne satıyoruz? En karlı dijital ürün konseptini ver."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        logging.error(f"Araştırma Departmanı Çöktü: {e}")
        return "Western Retro Wall Art - A vintage cowboy riding a mechanical horse in a neon desert, target audience: streetwear enthusiasts and retro decor lovers."

# ----------------- DEPARTMAN 2: SANAT YÖNETMENİ (Kusursuz Prompt) -----------------
def departman_sanat_yonetmeni(arastirma_sonucu):
    sistem_mesaji = """Sen dünyanın en iyi AI Prompt Mühendisisin. Gelen Etsy konseptini alıp, FLUX AI motorunun anlayacağı 'Kusursuz, ultra-gerçekçi, 8k çözünürlüklü, ödüllü' bir İngilizce prompta çevireceksin. 
    Promptun içinde ışıklandırma (cinematic lighting), stil (vector, retro, photorealistic vb.), kalite (masterpiece, highly detailed) ve negatif promptları hissettiren kesin komutlar olmalı. Sadece prompt metnini yaz."""
    
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": f"Şu konsept için muazzam bir görsel promptu yaz:\n{arastirma_sonucu}"}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        return f"masterpiece, best quality, ultra-detailed, {arastirma_sonucu}, cinematic lighting, vibrant colors, 8k resolution, award-winning digital art"

# ----------------- DEPARTMAN 3: ÜRETİM (FLUX MOTORU) -----------------
def departman_uretim(prompt):
    try:
        # Dünyanın en iyi açık kaynak modeli FLUX'u kullanıyoruz
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&enhance=true"
        
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
    c = canvas.Canvas(buf, pagesize=(595, 842)) # A4 Boyutu
    img = ImageReader(BytesIO(img_bytes))
    c.drawImage(img, 0, 0, width=595, height=842) # Tam sayfa yüksek kalite baskı
    c.save()
    buf.seek(0)
    return buf

# ----------------- TELEGRAM PANELİ VE ONAY MEKANİZMASI -----------------
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    durum_mesaji = await update.message.reply_text("📊 **Etsy Stratejisti** pazar analizi yapıyor...")
    
    arastirma = departman_arastirma()
    sirket_hafizasi["urun_tipi"] = arastirma
    await durum_mesaji.edit_text(f"🎯 **Karar Verildi:**\n_{arastirma}_\n\n🎨 **Sanat Yönetmeni** kusursuz promptu yazıyor...")
    
    kusursuz_prompt = departman_sanat_yonetmeni(arastirma)
    sirket_hafizasi["son_prompt"] = kusursuz_prompt
    await durum_mesaji.edit_text("⚙️ **FLUX Motoru** şaheseri üretiyor. Bu detaylı bir işlem, birkaç saniye sürebilir...")
    
    img_data = departman_uretim(kusursuz_prompt)
    
    if img_data:
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [
            [InlineKeyboardButton("✅ Mükemmel! Satışa Hazırla (PDF)", callback_data="onay_ver")],
            [InlineKeyboardButton("❌ Kaliteyi Beğenmedim", callback_data="reddet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img_data,
            caption=f"👑 **Patron, yeni ürün prototipi hazır.**\n\n**Strateji:** {arastirma}\n\nLütfen incele ve kararını ver:",
            reply_markup=reply_markup
        )
        await durum_mesaji.delete()
    else:
        await durum_mesaji.edit_text("🚨 Fabrika üretimde hata verdi. Ağ yoğun olabilir, tekrar deneyin.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        await query.edit_message_caption(caption="✅ Onaylandı. Tam sayfa yüksek çözünürlüklü PDF hazırlanıyor...")
        img_data = sirket_hafizasi["bekleyen_gorsel"]
        pdf_dosya = paketle_pdf(img_data)
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_dosya,
            filename=f"Etsy_Premium_Product.pdf",
            caption="🏆 İşte Satışa Hazır Premium Dosyanız!"
        )
        
    elif query.data == "reddet":
        await query.edit_message_caption(caption="❌ Ürün reddedildi. Şirket hafızasına kaydedilmesi için sebep bekleniyor.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Patron, bu üründe ne eksikti? Düzeltilmesi için lütfen geri bildirimini yaz.\nÖrnek: `/duzelt Renkler çok soluktu, daha canlı ve 'Eşref Tek' estetiğinde keskin hatlar kullan.`"
        )

async def duzelt_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🚨 Lütfen eleştirini ekle. Örnek: `/duzelt Daha streetwear tarzı olsun.`")
        return
    
    elestiri = " ".join(context.args)
    sirket_hafizasi["patron_notlari"].append(elestiri)
    
    await update.message.reply_text(f"📝 Şirket Hafızasına Eklendi: '{elestiri}'.\nTüm departmanlar bu uyarıyı dikkate alacak.\nYeni ürün araştırması için tekrar `/uretim_baslat` yazabilirsin.")

# ----------------- ANA ÇALIŞTIRICI -----------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", duzelt_komutu))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("💎 Gelişmiş AI Şirketi 7/24 Aktif!")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
