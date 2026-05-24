import logging
import requests
import openai
import os
import asyncio
import random
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Railway Ortam Değişkenleri
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# Şirket Hafızası (Patronun Hata Notları)
sirket_hafizasi = {
    "son_konsept": "",
    "son_prompt": "",
    "patron_notlari": [], # Beğenmediğin şeyler buraya yazılır ve ajanlar bunu okur
    "bekleyen_gorsel": None
}

# ----------------- DEPARTMANLAR (AI AJANLARI) -----------------

def departman_arastirma():
    # OpenAI GPT ile Etsy Trend Araştırması
    notlar = " ".join(sirket_hafizasi["patron_notlari"])
    sistem_mesaji = "Sen profesyonel bir Etsy pazar araştırmacısısın. Yetişkin boyama kitapları için çok satacak, ultra yaratıcı tek bir sayfa konsepti bul."
    if notlar:
        sistem_mesaji += f" DİKKAT! Patronun önceki uyarıları: {notlar}. Bunları ASLA tekrarlama!"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo", # Metin modeli ucuz ve hızlıdır
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Bana çok satacak, detaylı, tek sayfalık bir boyama kitabı konsepti ver. Sadece İngilizce konsepti yaz."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        logging.error(f"Araştırma Departmanı Çöktü: {e}")
        # GPT çalışmazsa yedek şaheser konseptler
        yedekler = [
            "A hyper-detailed mechanical owl sitting on a steampunk clockwork tree",
            "An intricate mandala made entirely of interwoven cosmic galaxies and stars",
            "A highly detailed surreal gothic castle merging with a giant old tree root system"
        ]
        return random.choice(yedekler)

def departman_sanat_yonetmeni(konsept):
    # Fikri, muazzam bir Prompt'a çevirir
    return f"masterpiece, ultra-detailed, intricate adult coloring book page, {konsept}, clean crisp black vector lines, pure white background, no shading, extremely complex line art, 8k resolution, award winning illustration --no grayscale, colors, messy lines"

def departman_uretim(prompt):
    # Ultra Kaliteli Görsel Üretim Motoru (Pollinations SDXL Parametreleri ile)
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logging.error(f"Üretim Hatası: {e}")
        return None

def paketle_pdf(img_bytes):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    img = ImageReader(BytesIO(img_bytes))
    c.drawImage(img, 47, 171, width=500, height=500)
    c.save()
    buf.seek(0)
    return buf

# ----------------- TELEGRAM YÖNETİM PANELİ -----------------

async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = await update.message.reply_text("🔍 **Etsy Araştırma Departmanı** trendleri inceliyor...")
    
    # Adım 1: Araştırma
    konsept = departman_arastirma()
    sirket_hafizasi["son_konsept"] = konsept
    await mesaj.edit_text(f"🎨 **Sanat Yönetmeni** konsepti devraldı...\nKonsept: _{konsept}_")
    
    # Adım 2: Prompt Mühendisliği
    ultra_prompt = departman_sanat_yonetmeni(konsept)
    sirket_hafizasi["son_prompt"] = ultra_prompt
    await mesaj.edit_text("⚙️ **Üretim Hattı** çalışıyor, şaheser çiziliyor... Bu birkaç saniye sürebilir.")
    
    # Adım 3: Üretim
    img_data = departman_uretim(ultra_prompt)
    
    if img_data:
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        # Adım 4: Patron Onayı (Butonlar)
        keyboard = [
            [InlineKeyboardButton("✅ Şaheser! PDF Olarak İndir", callback_data="onay_ver")],
            [InlineKeyboardButton("❌ Beğenmedim (Kalite Düşük)", callback_data="reddet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Görseli at ve onaya sun
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img_data,
            caption=f"👑 **Patron, yeni tasarım hazır.**\n\n**Konsept:** {konsept}\n\nLütfen bir işlem seç:",
            reply_markup=reply_markup
        )
        await mesaj.delete()
    else:
        await mesaj.edit_text("🚨 Fabrika üretimde hata verdi. Motorlar meşgul olabilir.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        # Onaylandı -> PDF Yap
        await query.edit_message_caption(caption="✅ Onaylandı. PDF paketleniyor...")
        img_data = sirket_hafizasi["bekleyen_gorsel"]
        pdf_dosya = paketle_pdf(img_data)
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_dosya,
            filename=f"Etsy_Premium_{random.randint(100,999)}.pdf",
            caption="🏆 İşte Satışa Hazır Premium PDF'iniz!"
        )
        
    elif query.data == "reddet":
        # Reddedildi -> Geri bildirim iste
        await query.edit_message_caption(caption="❌ Tasarım reddedildi ve çöpe atıldı.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Patron, ajanlar nerede hata yaptı? Düzeltilmesi için lütfen geri bildirimini yaz.\nÖrnek: `/duzelt Çizgiler çok inceydi, daha kalın ve net yap.`"
        )

async def duzelt_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🚨 Lütfen eleştirini ekle. Örnek: `/duzelt Karakterin yüzü bozuktu.`")
        return
    
    elestiri = " ".join(context.args)
    sirket_hafizasi["patron_notlari"].append(elestiri) # Eleştiriyi hafızaya al
    
    await update.message.reply_text(f"📝 Not alındı: '{elestiri}'. Araştırma departmanı bunu Öğrenme Defterine ekledi!\nYeni üretime başlamak için tekrar `/uretim_baslat` yazabilirsin.")

# ----------------- ANA ÇALIŞTIRICI -----------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CommandHandler("duzelt", duzelt_komutu))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("💎 Şirket ve AI Ajanları 7/24 Aktif!")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
