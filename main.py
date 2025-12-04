import os
import asyncio
import random
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait, ChannelInvalid, UsernameInvalid
from datetime import datetime, timedelta

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

app = Client("sub_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"channels": {}, "stats": {"blocked": 0, "checked": 0}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data = load_data()

messages = [
    "😊 Salom {user}! Kanallarimizga obuna bo'lsangiz, guruhda erkin suhbatlashishingiz mumkin!",
    "🤗 Assalomu alaykum {user}! Iltimos avval kanallarimizga a'zo bo'ling, keyin yozamiz!",
    "✨ {user}, bir daqiqa vaqt ajratib kanallarimizga qo'shiling, keyin suhbat davom etadi!",
    "🎯 {user}, bizning kanallar juda qiziq! Obuna bo'ling va guruhda faol bo'ling!",
    "🔥 Hey {user}! Kanalga obuna bo'lish 5 soniya, lekin foydasi katta. Qani tezroq!",
    "💫 {user}, siz ajoyib odamsiz! Endi kanalga ham obuna bo'lib ajoyibligingizni davom ettiring!",
    "🚀 Do'stim {user}, kanallarimizda ko'p foydali ma'lumotlar bor. Obuna bo'ling!",
    "🌟 {user}, guruhda yozish uchun faqat kanalga obuna bo'lish kerak. Juda oson!",
    "💎 {user}, siz bizning muhim a'zomiz! Kanalga ham qo'shiling va davom eting!",
    "🎉 {user}, kanallarimizda yangiliklar kutmoqda! Obuna bo'ling va o'tkazib yubormang!"
]

async def check_subscription(user_id):
    for channel_id, channel_info in data["channels"].items():
        try:
            member = await app.get_chat_member(channel_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                continue
            elif member.status == "restricted":
                return False
            else:
                return False
        except UserNotParticipant:
            try:
                chat = await app.get_chat(channel_id)
                if hasattr(chat, 'join_requests_count'):
                    requests = []
                    async for request in app.get_chat_join_requests(channel_id):
                        if request.user.id == user_id:
                            return True
                    return False
                else:
                    return False
            except:
                return False
        except Exception:
            return False
    return True

def get_keyboard():
    buttons = []
    for i, (channel_id, channel_info) in enumerate(data["channels"].items(), 1):
        invite_link = channel_info.get("invite_link", "")
        title = channel_info.get("title", f"{i}-Kanal")
        
        if invite_link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=invite_link)])
        elif channel_id.startswith("-100"):
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=f"https://t.me/c/{channel_id[4:]}/1")])
        else:
            channel_clean = channel_id.replace("@", "")
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=f"https://t.me/{channel_clean}")])
    
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if message.from_user.id in ADMIN_IDS:
        await message.reply(
            "🎛 *Admin Panel*\n\n"
            "📋 Buyruqlar:\n"
            "/addchannel - Kanal qo'shish\n"
            "/delchannel - Kanal o'chirish\n"
            "/channels - Kanallar ro'yxati\n"
            "/stats - Statistika\n\n"
            "💡 *Yopiq kanal qo'shish uchun:*\n"
            "Bot kanalda admin bo'lishi va quyidagi huquqlarga ega bo'lishi kerak:\n"
            "✅ Invite users\n"
            "✅ Manage chat"
        )
    else:
        await message.reply("👋 Salom! Men guruh uchun obuna tekshirish botiman.")

@app.on_message(filters.command("addchannel") & filters.private)
async def add_channel_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.reply(
        "📝 *Kanal qo'shish*\n\n"
        "Kanal ID, username yoki invite link yuboring:\n\n"
        "Masalan:\n"
        "• `@kanalname` (ochiq kanal)\n"
        "• `-1001234567890` (yopiq kanal ID)\n"
        "• `https://t.me/+AbCdEfGhIjK` (yopiq kanal invite link)\n\n"
        "⚠️ Bot kanalda admin bo'lishi shart!"
    )

@app.on_message(filters.command("delchannel") & filters.private)
async def del_channel_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not data["channels"]:
        await message.reply("❌ Kanallar ro'yxati bo'sh!")
        return
    
    text = "📋 *Kanallar ro'yxati:*\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        text += f"{i}. {title}\n   `{ch_id}`\n\n"
    text += "✏️ O'chirish uchun kanal ID yoki username yuboring:"
    await message.reply(text)

@app.on_message(filters.command("channels") & filters.private)
async def channels_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not data["channels"]:
        await message.reply("❌ Hozircha kanallar qo'shilmagan!")
        return
    
    text = "📋 *Kanallar ro'yxati:*\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        ch_type = "🔒 Yopiq" if ch_info.get("is_private") else "🔓 Ochiq"
        text += f"{i}. {ch_type} {title}\n   `{ch_id}`\n\n"
    await message.reply(text)

@app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = (
        "📊 *Statistika:*\n\n"
        f"🚫 O'chirilgan xabarlar: {data['stats']['blocked']}\n"
        f"✅ Tekshirilgan foydalanuvchilar: {data['stats']['checked']}\n"
        f"📣 Kanallar soni: {len(data['channels'])}"
    )
    await message.reply(text)

@app.on_message(filters.private & filters.text & ~filters.command(["start", "addchannel", "delchannel", "channels", "stats"]))
async def text_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text.strip()
    
    if text.startswith("@") or text.startswith("-100") or "t.me/" in text:
        try:
            if "t.me/" in text:
                if "+joinchat/" in text or "t.me/+" in text:
                    chat = await app.join_chat(text)
                    channel_id = str(chat.id)
                else:
                    username = text.split("t.me/")[-1].split("/")[0]
                    chat = await app.get_chat(username)
                    channel_id = str(chat.id)
            else:
                chat = await app.get_chat(text)
                channel_id = text
            
            if channel_id in data["channels"]:
                del data["channels"][channel_id]
                save_data(data)
                await message.reply(f"✅ Kanal o'chirildi: {chat.title}")
                return
            
            bot_member = await app.get_chat_member(channel_id, "me")
            if bot_member.status != "administrator":
                await message.reply("❌ Bot bu kanalda admin emas!")
                return
            
            invite_link = ""
            is_private = False
            
            try:
                if chat.username:
                    invite_link = f"https://t.me/{chat.username}"
                else:
                    is_private = True
                    try:
                        link = await app.export_chat_invite_link(channel_id)
                        invite_link = link
                    except:
                        invite_link = f"https://t.me/c/{str(chat.id)[4:]}/1"
            except:
                is_private = True
                invite_link = f"https://t.me/c/{str(chat.id)[4:]}/1"
            
            data["channels"][channel_id] = {
                "title": chat.title,
                "invite_link": invite_link,
                "is_private": is_private
            }
            save_data(data)
            
            ch_type = "🔒 Yopiq" if is_private else "🔓 Ochiq"
            await message.reply(
                f"✅ Kanal qo'shildi!\n\n"
                f"Nomi: {chat.title}\n"
                f"Turi: {ch_type}\n"
                f"ID: `{channel_id}`"
            )
        except Exception as e:
            await message.reply(f"❌ Xatolik: {str(e)}\n\nKanal topilmadi yoki bot admin emas!")

@app.on_message(filters.group & ~filters.service)
async def group_handler(client, message):
    if message.from_user.id in ADMIN_IDS:
        return
    
    if not data["channels"]:
        return
    
    data["stats"]["checked"] += 1
    
    if not await check_subscription(message.from_user.id):
        try:
            await message.delete()
            data["stats"]["blocked"] += 1
            save_data(data)
            
            text = random.choice(messages).format(user=message.from_user.mention)
            
            await message.chat.restrict_member(
                message.from_user.id,
                ChatPermissions(),
                datetime.now() + timedelta(seconds=10)
            )
            
            sent = await client.send_message(message.chat.id, text, reply_markup=get_keyboard())
            await asyncio.sleep(30)
            try:
                await sent.delete()
            except:
                pass
        except Exception:
            pass

@app.on_callback_query(filters.regex("check_sub"))
async def callback_handler(client, callback):
    if await check_subscription(callback.from_user.id):
        await callback.answer("✅ Ajoyib! Endi guruhda erkin yozishingiz mumkin!", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
    else:
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz yoki zayafka yuborishingiz kerak!", show_alert=True)

if __name__ == "__main__":
    print("🚀 Bot ishga tushdi...")
    app.run()
