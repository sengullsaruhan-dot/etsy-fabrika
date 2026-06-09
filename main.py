import logging
import requests
import openai
import os
import asyncio
import urllib.parse
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- SİSTEM AYARLARI VE GÜVENLİK ---
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# --- ŞİRKETİN BEYNİ (Hafıza) ---
sirket_hafizasi = {
    "rakip_tarzi": "Maskülen, sert hatlı, Eşref Tek stili, vintage western veya temiz minimalist streetwear vektörleri.", 
    "secilen_nis": "", 
    "bekleyen_gorsel": None
}

# --- DEPARTMAN 1: RAKİP DEDEKTİFİ (Etsy Link Analizi) ---
async def tarz_analiz_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🚨 Lütfen bir Etsy mağaza linki ekle.\nÖrnek: /tarz_analiz https://www.etsy.com/shop/TheUrbanArtisanCo")
        return

    link = context.args[0]
    mesaj = await update.message.reply_text("🕵️ Mağaza DNA'sı sökülüyor. Ürünler ve etiketler inceleniyor...")
    
    try:
        # Siteyi kazı ve başlıkları al
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        basliklar = [h.text.strip() for h in soup.find_all('h2')][:10]
        
        # GPT-3.5 ile tarzı analiz et ve filtre oluştur
        sistem_istegi = """Sen bir Sanat Direktörüsün. Gelen Etsy ürün başlıklarına bakarak bu mağazanın estetik tarzını tek bir İngilizce tasarım prompt filtresine dönüştür. Sadece İngilizce tasarım terimleri kullan. Örnek: 'minimalist line art, dark geometric aesthetic, clean monochrome vector'"""
        
        analiz = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": sistem_istegi}, {"role": "user", "content": str(basliklar)}]
        )
        
        sirket_hafizasi["rakip_tarzi"] = analiz.choices[0].message.content
        await mesaj.edit_text(f"✅ Rakip mağaza kopyalandı!\n\n**Yeni Tarz Filtresi:** {sirket_hafizasi['rakip_tarzi']}\n\nArtık üretimler bu premium tarza göre yapılacak. Şimdi /fikirver komutunu kullan.")
        
    except Exception as e:
        await mesaj.edit_text(f"🚨 Dedektif engellendi: Link geçersiz veya Etsy erişimi reddetti. Varsayılan tarz ile devam ediliyor.")

# --- DEPARTMAN 2: PAZAR STRATEJİSTİ ---
async def fikirver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = await update.message.reply_text("🔍 Mevcut tarza uygun kârlı nişler bulunuyor...")
    try:
        sistem = f"Sen Etsy uzmanısın. Şu tarza uygun 3 adet 'Dijital Tasarım' nişi (tişört/poster) öner: {sirket_hafizasi['rakip_tarzi']}"
        cevap = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "system", "content": sistem}, {"role": "user", "content": "3 niş öner."}]
        )
        await mesaj.edit_text(f"📈 **Yeni Nesil Strateji Raporu:**\n\n{cevap.choices[0].message.content}\n\nSeçimini kilitmek için: /sec [Konsept Adı]")
    except Exception as e:
        await mesaj.edit_text(f"🚨 Strateji Hatası: {e}")

async def sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sirket_hafizasi["secilen_nis"] = " ".join(context.args)
    await update.message.reply_text(f"✅ Üretim hedefi kilitlendi: '{sirket_hafizasi['secilen_nis']}'.\n\nŞimdi atölyeyi çalıştırmak için /uretim_baslat yaz.")

# --- DEPARTMAN 3: ÜRETİM BANDI (Sınırsız & Hatasız Flux Motoru) ---
async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sirket_hafizasi["secilen_nis"]:
        await update.message.reply_text("🚨 Önce hedefini belirle! /sec [Konsept] yaz.")
        return
        
    mesaj = await update.message.reply_text("🎨 Fabrika çalışıyor... Bu işlem birkaç saniye sürebilir.")
    
    try:
        # ZEKİ PROMPT MÜHENDİSLİĞİ: Tarz + Niş + Kesin Kurallar
        ana_konsept = sirket_hafizasi['secilen_nis']
        tarz = sirket_hafizasi['rakip_tarzi']
        
        # Bu prompt hata yapmaz, yazı yazmaz, arka planı beyaz tutar.
        kusursuz_prompt = f"{ana_konsept}, style of {tarz}, highly detailed vector art, perfectly centered, isolated on solid white background, high contrast, textless, strictly NO text, NO words, NO letters, masterpiece, 8k resolution"
        
        encoded_prompt = urllib.parse.quote(kusursuz_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=2000&height=2000&model=flux&nologo=true"
        
        response = requests.get(url, timeout=30)
        img_data = response.content
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [[InlineKeyboardButton("✅ Onayla & 300 DPI Matbaa Çıktısı Al", callback_data="onay_ver")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=img_data, caption="🔥 Prototip Hazır.\n\nEğer onaylarsan doğrudan Etsy'ye yükleyebileceğin devasa kalitede PNG fırlatılacak.", reply_markup=reply_markup)
        await mesaj.delete()
        
    except Exception as e:
        await mesaj.edit_text(f"🚨 Üretim Bandı Arızası: {str(e)}")

# --- DEPARTMAN 4: MATBAA (300 DPI Upscale) ---
async def buton_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "onay_ver":
        await query.edit_message_caption(caption="⏳ Matbaa görseli işliyor... Pikseller 4000x4000'e çıkarılıyor ve 300 DPI kodu gömülüyor...")
        try:
            # Pürüzsüz büyütme (Lanczos) ve 300 DPI kayıt
            img = Image.open(BytesIO(sirket_hafizasi["bekleyen_gorsel"])).resize((4000, 4000), Image.Resampling.LANCZOS)
            baski_dosyasi = BytesIO()
            img.save(baski_dosyasi, format="PNG", dpi=(300, 300))
            baski_dosyasi.seek(0)
            
            await context.bot.send_document(
                chat_id=query.message.chat_id, 
                document=baski_dosyasi, 
                filename="Etsy_PrintReady_300DPI.png",
                caption="🏆 İşte gerçek baskı kalitesi! Tişörte veya postere basılmaya hazır."
            )
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"🚨 Matbaa Arızası: {e}")

# --- FABRİKA ŞALTERİ ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Komutların Bağlanması
    app.add_handler(CommandHandler("tarz_analiz", tarz_analiz_et))
    app.add_handler(CommandHandler("fikirver", fikirver))
    app.add_handler(CommandHandler("sec", sec))
    app.add_handler(CommandHandler("uretim_baslat", uretim_baslat))
    app.add_handler(CallbackQueryHandler(buton_yonetimi))
    
    print("💎 Endüstriyel Fabrika %100 Kapasiteyle Çalışıyor.")
    app.run_polling()
