import logging
import requests
import openai
import os
import asyncio
from io import BytesIO
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Railway üzerinden gelen anahtar artık aktif
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

sirket_hafizasi = {
    "urun_tipi": "",
    "son_prompt": "",
    "patron_notlari": [], 
    "bekleyen_gorsel": None
}

# ----------------- DEPARTMAN 1: STRATEJİ -----------------
def departman_arastirma():
    notlar = " ".join(sirket_hafizasi["patron_notlari"])
    sistem_mesaji = """Sen profesyonel bir Etsy grafik stratejistisin.
    Üreteceğin tasarımlar: Maskülen, keskin hatlı, 'Eşref Tek' tarzı sert Western/Streetwear.
    YASAKLAR: Yazı, harf, logo, çerçeve, bulanıklık ASLA olmayacak.
    SADECE yüksek kontrastlı, beyaz arka planlı, vektör sanat eseri üret."""
    
    if notlar:
        sistem_mesaji += f"\nPATRONUN SON TALİMATLARI: {notlar}"
        
    try:
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sistem_mesaji},
                {"role": "user", "content": "Etsy'de satacak, maskülen, sert hatlı, yazısız bir görsel konsepti yaz."}
            ]
        )
        return cevap.choices[0].message.content
    except Exception as e:
        return "Streetwear Graphic - A high-contrast, sharp-edged cowboy skull, vintage western aesthetic."

# ----------------- DEPARTMAN 2: SANAT (DALL-E 3 PROMPT MÜHENDİSLİĞİ) -----------------
def departman_sanat_yonetmeni(arastirma_sonucu):
    sistem_mesaji = """Sen bir görsel sanat direktörüsün.
    Şu konsepti, DALL-E 3 için İngilizce prompta çevir.
    
    KURAL: 
    - Mutlaka ekle: "textless, strictly NO text, NO words, NO letters, isolated on solid white background".
    - Stil: "masterpiece, sharp focus, clean crisp vector lines, high contrast, bold aesthetic, perfectly centered".
    - ASLA yazı ekleme. Sadece görsel tasvirini ver."""
    
    cevap = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": sistem_mesaji},
            {"role": "user", "content": f"Şu konsepti kusursuz bir DALL-E 3 promptuna çevir:\n{arastirma_sonucu}"}
        ]
    )
    return cevap.choices[0].message.content

# ----------------- DEPARTMAN 3: DALL-E 3 ÜRETİM -----------------
def departman_uretim(prompt):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd", # En üst kalite
            n=1,
        )
        img_response = requests.get(response.data[0].url)
        return img_response.content
    except Exception as e:
        return None

# ----------------- DEPARTMAN 4: MATBAA (300 DPI) -----------------
def baski_kalitesine_yukselt(img_bytes):
    img = Image.open(BytesIO(img_bytes))
    # 4000x4000 piksel @ 300 DPI (Baskı Standardı)
    img_yuksek = img.resize((4000, 4000), Image.Resampling.LANCZOS)
    baski_dosyasi = BytesIO()
    img_yuksek.save(baski_dosyasi, format="PNG", dpi=(300, 300))
    baski_dosyasi.seek(0)
    return baski_dosyasi

# ----------------- ARAYÜZ (BOT) -----------------
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = await update.message.reply_text("Strateji ve OpenAI DALL-E 3 bağlantısı kuruluyor...")
    
    konsept = departman_arastirma()
    prompt = departman_sanat_yonetmeni(konsept)
    img_bytes = departman_uretim(prompt)
    
    if img_bytes:
        sirket_hafizasi["bekleyen_gorsel"] = img_bytes
        await context.bot.send_photo(update.message.chat_id, photo=img_bytes, 
                                     caption=f"Prototip: {konsept}\n\nOnaylıyorsan 300 DPI dosya alabilirsin.")
        await mesaj.delete()
    else:
        await mesaj.edit_text("Hata: OpenAI API anahtarını veya bakiyeni kontrol et.")

async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "onay_ver":
        baski_dosyasi = baski_kalitesine_yukselt(sirket_hafizasi["bekleyen_gorsel"])
        await context.bot.send_document(query.message.chat_id, document=baski_dosyasi, 
                                        filename="Etsy_PrintReady_300DPI.png")

#
