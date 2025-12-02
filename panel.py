from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

def register_admin_handlers(app: Client, db, check_admin, show_main_menu):
    
    @app.on_message(filters.regex("🛠 Admin panel") & filters.private)
    async def admin_panel(client: Client, message: Message):
        user_id = message.from_user.id
        if not check_admin(user_id):
            await message.reply_text("❌ Sizda admin huquqlari yo'q!")
            return
        buttons = [[KeyboardButton("📣 Reklama yuborish")], [KeyboardButton("🔗 Majburiy kanallar"), KeyboardButton("📨 Zayavka kanallar")], [KeyboardButton("📊 Statistika")], [KeyboardButton("🔧 Narxlarni sozlash")], [KeyboardButton("🚪 Chiqish")]]
        keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await message.reply_text("🛠 **Admin Panel**\n\nKerakli bo'limni tanlang:", reply_markup=keyboard)
    
    @app.on_message(filters.regex("🚪 Chiqish") & filters.private)
    async def exit_admin(client: Client, message: Message):
        user_id = message.from_user.id
        await show_main_menu(client, message, user_id)
    
    @app.on_message(filters.regex("📣 Reklama yuborish") & filters.private)
    async def broadcast_prompt(client: Client, message: Message):
        user_id = message.from_user.id
        if not check_admin(user_id):
            return
        await message.reply_text("📣 **Reklama yuborish**\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:")
        db.set_user_state(user_id, "waiting_broadcast")
    
    @app.on_message(filters.regex("📊 Statistika") & filters.private)
    async def statistics(client: Client, message: Message):
        user_id = message.from_user.id
        if not check_admin(user_id):
            return
        stats = db.get_statistics()
        text = f"📊 **Bot statistikasi**\n\n👥 Jami foydalanuvchilar: **{stats['total_users']}**\n🆕 Bugungi yangi: **{stats['today_users']}**\n🔗 Jami referallar: **{stats['total_referrals']}**\n💰 Yechilgan stars: **{stats['total_withdrawn']} ⭐**\n🎁 Premium olganlar: **{stats['premium_users']}**\n📈 Aktiv userlar (7 kun): **{stats['active_users']}**\n\n📅 Oxirgi yangilanish: {stats['last_update']}"
        await message.reply_text(text)
    
    @app.on_message(filters.regex("🔗 Majburiy kanallar") & filters.private)
    async def manage_mandatory(client: Client, message: Message):
        user_id = message.from_user.id
        if not check_admin(user_id):
            return
        channels = db.get_mandatory_channels()
        text = "🔗 **Majburiy kanallar**\n\n"
        if channels:
            for i, ch in enumerate(channels, 1):
                text += f"{i}. {ch['name']} - `{ch['channel_id']}`\n"
        else:
            text += "❌ Hozircha kanallar yo'q"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_mandatory")], [InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="remove_mandatory")]])
        await message.reply_text(text, reply_markup=buttons)
    
    @app.on_callback_query(filters.regex("add_mandatory"))
    async def add_mandatory_prompt(client: Client, callback: CallbackQuery):
        await callback.message.edit_text("➕ **Majburiy kanal qo'shish**\n\nQuyidagi formatda yuboring:\n`Kanal nomi | @kanal_username | -100xxxxxxxxx`\n\nMisol:\n`My Channel | @mychannel | -1001234567890`")
        db.set_user_state(callback.from_user.id, "adding_mandatory")
    
    @app.on_callback_query(filters.regex("remove_mandatory"))
    async def remove_mandatory_prompt(client: Client, callback: CallbackQuery):
        channels = db.get_mandatory_channels()
        if not channels:
            await callback.answer("❌ O'chiriladigan kanallar yo'q!", show_alert=True)
            return
        buttons = []
        for ch in channels:
            buttons.append([InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"delete_mandatory_{ch['id']}")])
        await callback.message.edit_text("🗑 **Kanalni o'chirish**\n\nO'chiriladigan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
    
    @app.on_callback_query(filters.regex("^delete_mandatory_"))
    async def delete_mandatory_channel(client: Client, callback: CallbackQuery):
        channel_id = int(callback.data.split("_")[2])
        db.remove_mandatory_channel(channel_id)
        await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
        await callback.message.delete()
    
    @app.on_message(filters.regex("📨 Zayavka kanallar") & filters.private)
    async def manage_zayavka(client: Client, message: Message):
        user_id = message.from_user.id
        if not check_admin(user_id):
            return
        channels = db.get_zayavka_channels()
        text = "📨 **Zayavka kanallar** (obuna tekshirilmaydi)\n\n"
        if channels:
            for i, ch in enumerate(channels, 1):
                text += f"{i}. {ch['name']} - {ch['link']}\n"
        else:
            text += "❌ Hozircha kanallar yo'q"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_zayavka")], [InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="remove_zayavka")]])
        await message.reply_text(text, reply_markup=buttons)
    
    @app.on_callback_query(filters.regex("add_zayavka"))
    async def add_zayavka_prompt(client: Client, callback: CallbackQuery):
        await callback.message.edit_text("➕ **Zayavka kanal qo'shish**\n\nQuyidagi formatda yuboring:\n`Kanal nomi | https://t.me/kanal`\n\nMisol:\n`Zayavka Channel | https://t.me/zayavka`")
        db.set_user_state(callback.from_user.id, "adding_zayavka")
    
    @app.on_callback_query(filters.regex("remove_zayavka"))
    async def remove_zayavka_prompt(client: Client, callback: CallbackQuery):
        channels = db.get_zayavka_channels()
        if not channels:
            await callback.answer("❌ O'chiriladigan kanallar yo'q!", show_alert=True)
            return
        buttons = []
        for ch in channels:
            buttons.append([InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"delete_zayavka_{ch['id']}")])
        await callback.message.edit_text("🗑 **Kanalni o'chirish**\n\nO'chiriladigan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
    
    @app.on_callback_query(filters.regex("^delete_zayavka_"))
    async def delete_zayavka_channel(client: Client, callback: CallbackQuery):
        channel_id = int(callback.data.split("_")[2])
        db.remove_zayavka_channel(channel_id)
        await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
        await callback.message.delete()
    
    @app.on_callback_query(filters.regex("^admin_approve_withdraw_"))
    async def approve_withdraw(client: Client, callback: CallbackQuery):
        request_id = int(callback.data.split("_")[3])
        request = db.get_withdraw_request(request_id)
        if not request:
            await callback.answer("❌ So'rov topilmadi!", show_alert=True)
            return
        db.subtract_balance(request['user_id'], request['amount'])
        db.update_withdraw_status(request_id, 'approved')
        emoji_map = {15: "🧸", 25: "🌹", 50: "🚗", 100: "💍"}
        try:
            await client.send_message(request['user_id'], f"✅ So'rovingiz tasdiqlandi!\n\n🎁 Sovg'a: {emoji_map.get(request['amount'], '⭐')}\n💰 Miqdor: {request['amount']} ⭐\n🕒 Vaqt: {request['time']}")
        except:
            pass
        await callback.message.edit_text(callback.message.text + "\n\n✅ **Tasdiqlandi**")
    
    @app.on_callback_query(filters.regex("^admin_reject_withdraw_"))
    async def reject_withdraw(client: Client, callback: CallbackQuery):
        request_id = int(callback.data.split("_")[3])
        request = db.get_withdraw_request(request_id)
        if not request:
            await callback.answer("❌ So'rov topilmadi!", show_alert=True)
            return
        db.update_withdraw_status(request_id, 'rejected')
        try:
            await client.send_message(request['user_id'], f"❌ So'rovingiz rad etildi!\n\n💰 Miqdor: {request['amount']} ⭐")
        except:
            pass
        await callback.message.edit_text(callback.message.text + "\n\n❌ **Rad etildi**")
    
    @app.on_callback_query(filters.regex("^admin_approve_premium_"))
    async def approve_premium(client: Client, callback: CallbackQuery):
        request_id = int(callback.data.split("_")[3])
        request = db.get_premium_request(request_id)
        if not request:
            await callback.answer("❌ So'rov topilmadi!", show_alert=True)
            return
        premium_price = db.get_setting('premium_price', 250)
        db.subtract_balance(request['user_id'], premium_price)
        db.set_premium_status(request['user_id'], True)
        db.update_premium_status_request(request_id, 'approved')
        try:
            await client.send_message(request['user_id'], f"✅ Premiumingiz tasdiqlandi!\n\n🎁 1 oylik Telegram Premium\n💰 To'lov: {premium_price} ⭐")
        except:
            pass
        await callback.message.edit_text(callback.message.text + "\n\n✅ **Tasdiqlandi**")
    
    @app.on_callback_query(filters.regex("^admin_reject_premium_"))
    async def reject_premium(client: Client, callback: CallbackQuery):
        request_id = int(callback.data.split("_")[3])
        request = db.get_premium_request(request_id)
        if not request:
            await callback.answer("❌ So'rov topilmadi!", show_alert=True)
            return
        db.update_premium_status_request(request_id, 'rejected')
        try:
            await client.send_message(request['user_id'], "❌ Premium so'rovingiz rad etildi!")
        except:
            pass
        await callback.message.edit_text(callback.message.text + "\n\n❌ **Rad etildi**")
    
    @app.on_message(filters.regex("🔧 Narxlarni sozlash") & filters.private)
    async def settings_menu(client: Client, message: Message):
        user_id = message.from_user.id
        if not check_admin(user_id):
            return
        referral_reward = db.get_setting('referral_reward', 3)
        premium_price = db.get_setting('premium_price', 250)
        text = f"🔧 **Joriy sozlamalar**\n\n🔗 Referal bonusi: **{referral_reward} ⭐**\n💎 Premium narxi: **{premium_price} ⭐**\n\n🎁 **Sovg'a qiymatlari:**\n🧸 15 ⭐\n🌹 25 ⭐\n🚗 50 ⭐\n💍 100 ⭐\n\n⚠ Sovg'a qiymatlari va emojilari o'zgartirilmaydi!"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Referal bonusini o'zgartirish", callback_data="change_referral")], [InlineKeyboardButton("💎 Premium narxini o'zgartirish", callback_data="change_premium_price")]])
        await message.reply_text(text, reply_markup=buttons)
    
    @app.on_callback_query(filters.regex("change_referral"))
    async def change_referral_prompt(client: Client, callback: CallbackQuery):
        await callback.message.edit_text("🔗 **Referal bonusini o'zgartirish**\n\nYangi qiymatni kiriting (faqat raqam):")
        db.set_user_state(callback.from_user.id, "changing_referral")
    
    @app.on_callback_query(filters.regex("change_premium_price"))
    async def change_premium_prompt(client: Client, callback: CallbackQuery):
        await callback.message.edit_text("💎 **Premium narxini o'zgartirish**\n\nYangi qiymatni kiriting (faqat raqam):")
        db.set_user_state(callback.from_user.id, "changing_premium")
    
    @app.on_message(filters.private & filters.text & ~filters.command("start"))
    async def handle_states(client: Client, message: Message):
        user_id = message.from_user.id
        state = db.get_user_state(user_id)
        if not state:
            return
        if state == "adding_mandatory" and check_admin(user_id):
            try:
                parts = message.text.split("|")
                if len(parts) != 3:
                    await message.reply_text("❌ Noto'g'ri format!\n\nTo'g'ri format:\n`Kanal nomi | @username | -100xxxxxxxxx`")
                    return
                name = parts[0].strip()
                username = parts[1].strip()
                channel_id = parts[2].strip()
                link = f"https://t.me/{username.replace('@', '')}"
                db.add_mandatory_channel(name, channel_id, link)
                db.set_user_state(user_id, None)
                await message.reply_text(f"✅ Majburiy kanal qo'shildi!\n\n📢 Nomi: {name}\n🔗 Link: {link}\n🆔 ID: `{channel_id}`")
            except Exception as e:
                await message.reply_text(f"❌ Xato: {str(e)}")
        elif state == "adding_zayavka" and check_admin(user_id):
            try:
                parts = message.text.split("|")
                if len(parts) != 2:
                    await message.reply_text("❌ Noto'g'ri format!\n\nTo'g'ri format:\n`Kanal nomi | https://t.me/kanal`")
                    return
                name = parts[0].strip()
                link = parts[1].strip()
                db.add_zayavka_channel(name, link)
                db.set_user_state(user_id, None)
                await message.reply_text(f"✅ Zayavka kanal qo'shildi!\n\n📢 Nomi: {name}\n🔗 Link: {link}\n\n⚠ Bu kanal obuna tekshirilmaydi!")
            except Exception as e:
                await message.reply_text(f"❌ Xato: {str(e)}")
        elif state == "changing_referral" and check_admin(user_id):
            try:
                new_value = int(message.text)
                if new_value < 1 or new_value > 100:
                    await message.reply_text("❌ Qiymat 1 dan 100 gacha bo'lishi kerak!")
                    return
                db.set_setting('referral_reward', new_value)
                db.set_user_state(user_id, None)
                await message.reply_text(f"✅ Referal bonusi o'zgartirildi!\n\nYangi qiymat: **{new_value} ⭐**")
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam kiriting!")
        elif state == "changing_premium" and check_admin(user_id):
            try:
                new_value = int(message.text)
                if new_value < 50 or new_value > 1000:
                    await message.reply_text("❌ Qiymat 50 dan 1000 gacha bo'lishi kerak!")
                    return
                db.set_setting('premium_price', new_value)
                db.set_user_state(user_id, None)
                await message.reply_text(f"✅ Premium narxi o'zgartirildi!\n\nYangi qiymat: **{new_value} ⭐**")
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam kiriting!")
        elif state == "waiting_broadcast" and check_admin(user_id):
            users = db.get_all_users()
            success = 0
            failed = 0
            status_msg = await message.reply_text("📤 Yuborilmoqda...")
            for user in users:
                try:
                    await client.send_message(user['user_id'], message.text)
                    success += 1
                except:
                    failed += 1
            db.set_user_state(user_id, None)
            await status_msg.edit_text(f"✅ Reklama yuborildi!\n\n✔ Muvaffaqiyatli: {success}\n❌ Xato: {failed}")
