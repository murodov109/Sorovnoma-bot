import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus, ChatType
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

app = Client("konkurs_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "users": {},
        "channels": {},
        "groups": {},
        "required_channels": [],
        "contests": {"voice": {}, "referral": {}},
        "stats": {"total_contests": 0},
        "ads": {"text": "", "active": False},
        "referred_users": {}
    }

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

db = load_db()

async def check_subscription(client, user_id):
    if not db["required_channels"]:
        return True
    for ch in db["required_channels"]:
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                return False
        except:
            return False
    return True

async def is_channel_member(client, channel_id, user_id):
    try:
        member = await client.get_chat_member(int(channel_id), user_id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            return False
        return True
    except:
        return False

def get_sub_keyboard():
    btns = []
    for ch in db["required_channels"]:
        btns.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")])
    btns.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(btns)

@app.on_message(filters.command("start") & filters.private)
async def start_private(client, message: Message):
    user_id = str(message.from_user.id)
    
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        ref_id = message.command[1].replace("ref_", "")
        if ref_id != user_id and user_id not in db.get("referred_users", {}):
            db.setdefault("referred_users", {})[user_id] = ref_id
            for ch_id, contest in db["contests"]["referral"].items():
                if ref_id in contest.get("participants", {}):
                    contest["participants"][ref_id]["count"] = contest["participants"][ref_id].get("count", 0) + 1
                    contest["participants"][ref_id].setdefault("refs", []).append(user_id)
            save_db(db)
    
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "username": message.from_user.username,
            "name": message.from_user.first_name,
            "joined": str(datetime.now())
        }
        save_db(db)
    
    if message.from_user.id in ADMIN_IDS:
        await show_admin_panel(message)
        return
    
    if not await check_subscription(client, message.from_user.id):
        await message.reply(
            "❌ Botdan foydalanish uchun quyidagi kanallarga obuna boling:",
            reply_markup=get_sub_keyboard()
        )
        return
    
    text = """
🎉 KONKURS BOTIGA XUSH KELIBSIZ!

📋 Konkursni qanday boshlash kerak?

1️⃣ Botni kanalingizga admin qiling
2️⃣ Kanalda #start yozing
3️⃣ Konkurs turini tanlang

🏆 Konkurs turlari:

🎤 Ovozli Battle
- Ishtirokchilar royxatga yoziladi
- Har bir kishiga ovoz beriladi
- Eng kop ovoz toplagan golib

🔗 Havolali Battle
- Ishtirokchilar referal link oladi
- Kim kop odam taklif qilsa golib
- Kanalni tark etganlar avtomatik ayiriladi

👇 Botni kanalga yoki guruhga qoshing:
"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanalga qoshish", callback_data="add_channel")],
        [InlineKeyboardButton("👥 Guruhga qoshish", callback_data="add_group")]
    ])
    await message.reply(text, reply_markup=keyboard)

async def show_admin_panel(message):
    text = f"""
🔐 ADMIN PANEL

👥 Umumiy foydalanuvchilar: {len(db['users'])}
📺 Umumiy kanallar: {len(db['channels'])}
👥 Umumiy guruhlar: {len(db['groups'])}
🏆 Otkazilgan konkurslar: {db['stats']['total_contests']}

📢 Majburiy kanallar: {len(db['required_channels'])} ta

Buyruqlar:
/addchannel @username - Kanal qoshish
/delchannel @username - Kanal ochirish
/ads <matn> - Reklama yuborish
/users - Foydalanuvchilar royxati
/channels - Kanallar royxati
/groups - Guruhlar royxati
"""
    await message.reply(text)

@app.on_message(filters.command("users") & filters.private)
async def show_users(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = list(db["users"].items())[:30]
    text = "👥 FOYDALANUVCHILAR (oxirgi 30 ta)\n\n"
    for uid, data in users:
        text += f"• {data.get('name', 'User')} - {uid}\n"
    await message.reply(text)

@app.on_message(filters.command("channels") & filters.private)
async def show_channels(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = "📺 KANALLAR ROYXATI\n\n"
    for cid, data in db["channels"].items():
        text += f"• {data.get('title', 'Channel')} - {cid}\n"
    if not db["channels"]:
        text += "Hozircha yoq"
    await message.reply(text)

@app.on_message(filters.command("groups") & filters.private)
async def show_groups(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = "👥 GURUHLAR ROYXATI\n\n"
    for gid, data in db["groups"].items():
        text += f"• {data.get('title', 'Group')} - {gid}\n"
    if not db["groups"]:
        text += "Hozircha yoq"
    await message.reply(text)

@app.on_callback_query(filters.regex("^add_channel$|^add_group$"))
async def add_bot_handler(client, callback: CallbackQuery):
    bot_info = await client.get_me()
    if callback.data == "add_channel":
        text = f"📢 Botni kanalga admin qilish uchun:\n\n1. Kanalingizni oching\n2. Admin qoshish bolimiga oting\n3. @{bot_info.username} ni qoshing\n4. Barcha ruxsatlarni bering"
    else:
        text = f"👥 Botni guruhga qoshish uchun:\n\n1. Guruhingizni oching\n2. Azolar bolimiga oting\n3. @{bot_info.username} ni qoshing\n4. Admin qiling"
    await callback.answer(text, show_alert=True)

@app.on_callback_query(filters.regex("^check_sub$"))
async def check_sub_handler(client, callback: CallbackQuery):
    if await check_subscription(client, callback.from_user.id):
        await callback.message.delete()
        await start_private(client, callback.message)
    else:
        await callback.answer("❌ Hali obuna bolmadingiz!", show_alert=True)

@app.on_message(filters.regex(r"^#start$") & filters.channel)
async def start_channel(client, message: Message):
    chat = message.chat
    try:
        member = await client.get_chat_member(chat.id, (await client.get_me()).id)
        if member.status != ChatMemberStatus.ADMINISTRATOR:
            return
    except:
        return
    
    try:
        sender = await client.get_chat_member(chat.id, message.from_user.id if message.from_user else 0)
        if sender.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return
    except:
        pass
    
    ch_id = str(chat.id)
    if ch_id not in db["channels"]:
        db["channels"][ch_id] = {"title": chat.title, "username": chat.username}
        save_db(db)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎤 Ovozli Battle", callback_data=f"voice_{chat.id}")],
        [InlineKeyboardButton("🔗 Havolali Battle", callback_data=f"ref_{chat.id}")]
    ])
    await message.reply(
        "🔰 KONKURS BOSHLASH PANELI\n\n👇 Quyidan kerakli konkurs turini tanlang:",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^voice_(-?\d+)$"))
async def start_voice_battle(client, callback: CallbackQuery):
    ch_id = callback.matches[0].group(1)
    db["contests"]["voice"][ch_id] = {"participants": {}, "voters": {}, "active": True}
    db["stats"]["total_contests"] += 1
    save_db(db)
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎟 Qatnashish", callback_data=f"vjoin_{ch_id}")]])
    await callback.message.edit_text(
        "🎤 Ovozli Battle boshlandi!\n\nIshtirok etish uchun quyidagi tugmani bosing 👇",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^vjoin_(-?\d+)$"))
async def join_voice(client, callback: CallbackQuery):
    ch_id = callback.matches[0].group(1)
    user = callback.from_user
    uid = str(user.id)
    
    if ch_id not in db["contests"]["voice"]:
        await callback.answer("❌ Konkurs topilmadi!", show_alert=True)
        return
    
    if not await is_channel_member(client, ch_id, user.id):
        await callback.answer("❌ Avval kanalga azo boling!", show_alert=True)
        return
    
    contest = db["contests"]["voice"][ch_id]
    if uid not in contest["participants"]:
        contest["participants"][uid] = {
            "name": user.first_name,
            "username": user.username or user.first_name,
            "votes": 0
        }
        save_db(db)
    
    await update_voice_keyboard(client, callback.message, ch_id)
    await callback.answer("✅ Royxatga qoshildingiz!")

async def update_voice_keyboard(client, message, ch_id):
    contest = db["contests"]["voice"].get(ch_id, {})
    parts = contest.get("participants", {})
    
    buttons = []
    row = []
    for uid, data in parts.items():
        votes = data.get("votes", 0)
        name = data.get("username", "User")[:15]
        btn_text = f"@{name} [{votes}]" if votes > 0 else f"@{name}"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"vvote_{ch_id}_{uid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🎟 Qatnashish", callback_data=f"vjoin_{ch_id}")])
    
    try:
        await message.edit_reply_markup(InlineKeyboardMarkup(buttons))
    except:
        pass

@app.on_callback_query(filters.regex(r"^vvote_(-?\d+)_(\d+)$"))
async def vote_voice(client, callback: CallbackQuery):
    ch_id = callback.matches[0].group(1)
    target_id = callback.matches[0].group(2)
    voter_id = str(callback.from_user.id)
    
    contest = db["contests"]["voice"].get(ch_id)
    if not contest:
        await callback.answer("❌ Konkurs topilmadi!", show_alert=True)
        return
    
    if not await is_channel_member(client, ch_id, callback.from_user.id):
        await callback.answer("❌ Ovoz berish uchun kanalga azo boling!", show_alert=True)
        return
    
    if voter_id in contest.get("voters", {}):
        await callback.answer("❌ Siz allaqachon ovoz bergansiz!", show_alert=True)
        return
    
    if target_id == voter_id:
        await callback.answer("❌ Ozingizga ovoz bera olmaysiz!", show_alert=True)
        return
    
    if target_id in contest["participants"]:
        contest["participants"][target_id]["votes"] += 1
        contest.setdefault("voters", {})[voter_id] = target_id
        save_db(db)
        await update_voice_keyboard(client, callback.message, ch_id)
        await callback.answer("✅ Ovozingiz qabul qilindi!")

@app.on_callback_query(filters.regex(r"^ref_(-?\d+)$"))
async def start_ref_battle(client, callback: CallbackQuery):
    ch_id = callback.matches[0].group(1)
    db["contests"]["referral"][ch_id] = {"participants": {}, "active": True}
    db["stats"]["total_contests"] += 1
    save_db(db)
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Qoshilish", callback_data=f"rjoin_{ch_id}")]])
    await callback.message.edit_text(
        "🔗 Havolali Battle boshlandi!\n\nIshtirok etish uchun quyidagi tugmani bosing 👇",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^rjoin_(-?\d+)$"))
async def join_ref(client, callback: CallbackQuery):
    ch_id = callback.matches[0].group(1)
    user = callback.from_user
    uid = str(user.id)
    bot = await client.get_me()
    
    if ch_id not in db["contests"]["referral"]:
        await callback.answer("❌ Konkurs topilmadi!", show_alert=True)
        return
    
    if not await is_channel_member(client, ch_id, user.id):
        await callback.answer("❌ Avval kanalga azo boling!", show_alert=True)
        return
    
    contest = db["contests"]["referral"][ch_id]
    if uid not in contest["participants"]:
        contest["participants"][uid] = {
            "name": user.first_name,
            "username": user.username or user.first_name,
            "count": 0,
            "refs": []
        }
        save_db(db)
    
    ref_link = f"https://t.me/{bot.username}?start=ref_{uid}"
    await callback.answer(f"Havolangiz nusxalandi!\n\n{ref_link}", show_alert=True)
    await update_ref_keyboard(client, callback.message, ch_id)

async def update_ref_keyboard(client, message, ch_id):
    contest = db["contests"]["referral"].get(ch_id, {})
    parts = contest.get("participants", {})
    
    buttons = []
    row = []
    for uid, data in parts.items():
        count = data.get("count", 0)
        name = data.get("username", "User")[:15]
        btn_text = f"@{name} [{count}]" if count > 0 else f"@{name}"
        row.append(InlineKeyboardButton(btn_text, url=f"tg://user?id={uid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🚀 Qoshilish", callback_data=f"rjoin_{ch_id}")])
    
    try:
        await message.edit_reply_markup(InlineKeyboardMarkup(buttons))
    except:
        pass

@app.on_chat_member_updated()
async def member_update(client, update: ChatMemberUpdated):
    ch_id = str(update.chat.id)
    user_id = str(update.from_user.id)
    
    new = update.new_chat_member
    
    if new and new.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        if ch_id in db["contests"]["voice"]:
            contest = db["contests"]["voice"][ch_id]
            
            if user_id in contest.get("participants", {}):
                del contest["participants"][user_id]
            
            voted_for = contest.get("voters", {}).get(user_id)
            if voted_for:
                if voted_for in contest.get("participants", {}):
                    contest["participants"][voted_for]["votes"] = max(0, contest["participants"][voted_for]["votes"] - 1)
                del contest["voters"][user_id]
            
            save_db(db)
        
        if ch_id in db["contests"]["referral"]:
            contest = db["contests"]["referral"][ch_id]
            
            if user_id in contest.get("participants", {}):
                del contest["participants"][user_id]
            
            for uid, data in contest.get("participants", {}).items():
                if user_id in data.get("refs", []):
                    data["refs"].remove(user_id)
                    data["count"] = max(0, data["count"] - 1)
            
            save_db(db)

@app.on_message(filters.command("addchannel") & filters.private)
async def add_channel(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if len(message.command) < 2:
        await message.reply("❌ Kanal username kiriting: /addchannel @channel")
        return
    ch = message.command[1]
    if ch not in db["required_channels"]:
        db["required_channels"].append(ch)
        save_db(db)
        await message.reply(f"✅ {ch} majburiy kanallarga qoshildi!")
    else:
        await message.reply("❌ Bu kanal allaqachon mavjud!")

@app.on_message(filters.command("delchannel") & filters.private)
async def del_channel(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if len(message.command) < 2:
        await message.reply("❌ Kanal username kiriting: /delchannel @channel")
        return
    ch = message.command[1]
    if ch in db["required_channels"]:
        db["required_channels"].remove(ch)
        save_db(db)
        await message.reply(f"✅ {ch} majburiy kanallardan ochirildi!")
    else:
        await message.reply("❌ Bu kanal topilmadi!")

@app.on_message(filters.command("ads") & filters.private)
async def send_ads(client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.replace("/ads ", "", 1)
    if not text or text == "/ads":
        await message.reply("❌ Reklama matni kiriting!")
        return
    
    count = 0
    for uid in db["users"]:
        try:
            await client.send_message(int(uid), text)
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.reply(f"✅ Reklama {count} ta foydalanuvchiga yuborildi!")

@app.on_message(filters.new_chat_members)
async def bot_added(client, message: Message):
    bot = await client.get_me()
    for member in message.new_chat_members:
        if member.id == bot.id:
            gid = str(message.chat.id)
            if gid not in db["groups"]:
                db["groups"][gid] = {"title": message.chat.title}
                save_db(db)

print("Bot ishga tushdi!")
app.run()
