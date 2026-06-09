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
        
        kusursuz_prompt = f"{ana_konsept}, style of {tarz}, highly detailed vector art, perfectly centered, isolated on solid white background, high contrast, textless, strictly NO text, NO words, NO letters, masterpiece, 8k resolution"
        
        encoded_prompt = urllib.parse.quote(kusursuz_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=2000&height=2000&model=flux&nologo=true"
        
        # Zaman aşımını uzattık ve hata kontrolü ekledik
        response = requests.get(url, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Görsel motoru yanıt vermedi (Hata Kodu: {response.status_code})")
            
        img_data = response.content
        
        # KALİTE KONTROL: Gelen veri gerçekten bir fotoğraf mı? (1000 byte'tan küçükse bozuktur)
        if len(img_data) < 1000:
            raise Exception("Motor geçici olarak meşgul veya bozuk dosya üretti. Lütfen tekrar /uretim_baslat yazın.")
            
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [[InlineKeyboardButton("✅ Onayla & 300 DPI Matbaa Çıktısı Al", callback_data="onay_ver")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # GÜVENLİ PAKETLEME: Telegram 400 hatası vermesin diye BytesIO içine alıyoruz
        await context.bot.send_photo(
            chat_id=update.message.chat_id, 
            photo=BytesIO(img_data), 
            caption="🔥 Prototip Hazır.\n\nEğer onaylarsan doğrudan Etsy'ye yükleyebileceğin devasa kalitede PNG fırlatılacak.", 
            reply_markup=reply_markup
        )
        await mesaj.delete()
        
    except Exception as e:
        # Telegram çökmek yerine hatayı sana raporlayacak
        await mesaj.edit_text(f"🚨 Üretim Bandı Arızası: {str(e)}")
