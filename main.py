async def uretim_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sirket_hafizasi["secilen_nis"]:
        await update.message.reply_text("🚨 /fikirver yapmadın!")
        return
    mesaj = await update.message.reply_text("🎨 Dijital tasarım atölyesi çalışıyor...")
    
    try:
        # DALL-E 3'ü sildik, yerine sınırsız üretim yapan Flux motorunu koyduk:
        prompt = f"{sirket_hafizasi['secilen_nis']}, digital vector design, flat streetwear style, high contrast, white background, 8k"
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Üretim motoru
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=2000&height=2000&model=flux&nologo=true"
        img_data = requests.get(url).content
        
        sirket_hafizasi["bekleyen_gorsel"] = img_data
        
        keyboard = [[InlineKeyboardButton("✅ 300 DPI İndir", callback_data="onay_ver")]]
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=img_data, caption="Prototip hazır.", reply_markup=InlineKeyboardMarkup(keyboard))
        await mesaj.delete()
    except Exception as e:
        await update.message.reply_text(f"🚨 Fabrika arızası: {str(e)}")
