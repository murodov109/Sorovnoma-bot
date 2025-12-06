import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

app = Client("sub_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "data.json"
user_states = {}
temp_channels = {}

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE, "r", encoding="utf-8"))
    return {"channels": {}, "stats": {"blocked": 0, "checked": 0}}

def save_data(d):
    json.dump(d, open(DATA_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

data = load_data()

messages = [
    "😊 Salom {user}! Kanallarimizga obuna bo'lsangiz yozishingiz mumkin!",
    "🤗 {user}, avval kanallarga qo‘shiling!",
    "✨ {user}, obuna bo‘ling va davom eting!",
    "🎯 {user}, kanallar juda foydali! Obuna bo‘ling!",
    "🔥 {user}, atigi 5 soniya! Obuna bo‘ling!",
]

def get_keyboard():
    btn = []
    for i, v in data["channels"].items():
        btn.append([InlineKeyboardButton(f"📣 {v['title']}", url=v["invite_link"])])
    btn.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(btn)

async def check_subscription(uid):
    if not data["channels"]:
        return True
    for ch_id, v in data["channels"].items():
        try:
            m = await app.get_chat_member(int(ch_id), uid)
            if m.status not in ("member", "administrator", "creator"):
                return False
        except UserNotParticipant:
            return False
        except:
            return False
    return True

def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton("📋 Ro'yxat", callback_data="list_channels")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ])

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, m):
    if m.from_user.id in ADMIN_IDS:
        await m.reply("🎛 ADMIN PANEL", reply_markup=admin_panel())
    else:
        await m.reply("👋 Salom! Men obuna tekshiruvchi botman.")

@app.on_callback_query(filters.regex("add_channel"))
async def add_ch_cb(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo‘q!", True)

    user_states[c.from_user.id] = "add_ch"
    await c.edit_message_text(
        "📝 Kanal ID yoki:\n`ID|Havola`\nko‘rinishida yuboring.\n\nMisol:\n`-1001234567890`\n`-1001234567890 https://t.me/+xxxx`\n`-1001234567890|https://t.me/+xxxx`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_message(filters.private & filters.text)
async def admin_text(_, m):
    uid = m.from_user.id
    if uid not in ADMIN_IDS:
        return

    state = user_states.get(uid)
    if state != "add_ch":
        return

    txt = m.text.strip()

    if "|" in txt:
        parts = txt.split("|", 1)
    else:
        parts = txt.split()

    ch_id = parts[0]

    if not ch_id.lstrip("-").isdigit():
        return await m.reply("❌ ID noto‘g‘ri!")

    ch_id = int(ch_id)
    link = parts[1].strip() if len(parts) > 1 else None

    try:
        chat = await app.get_chat(ch_id)
    except:
        return await m.reply("❌ Kanal topilmadi!")

    title = chat.title or "Kanal"

    if not link:
        user_states[uid] = "wait_link"
        temp_channels[uid] = {"id": ch_id, "title": title}
        return await m.reply("🔗 Maxfiy kanal havolasini yuboring:")

    data["channels"][str(ch_id)] = {
        "id": ch_id,
        "title": title,
        "invite_link": link
    }
    save_data(data)
    user_states.pop(uid, None)
    await m.reply("✅ Kanal qo‘shildi!", reply_markup=admin_panel())

@app.on_message(filters.private & filters.text)
async def link_wait(_, m):
    uid = m.from_user.id
    if user_states.get(uid) != "wait_link":
        return

    link = m.text.strip()
    if not link.startswith("http"):
        return await m.reply("❌ Havola noto‘g‘ri!")

    ch = temp_channels.pop(uid)
    data["channels"][str(ch["id"])] = {
        "id": ch["id"],
        "title": ch["title"],
        "invite_link": link
    }
    save_data(data)
    user_states.pop(uid, None)
    await m.reply("✅ Kanal qo‘shildi!", reply_markup=admin_panel())

@app.on_message(filters.group & ~filters.service)
async def group_msg(_, m):
    if m.from_user.id in ADMIN_IDS:
        return

    if not data["channels"]:
        return

    data["stats"]["checked"] += 1
    save_data(data)

    ok = await check_subscription(m.from_user.id)
    if ok:
        return

    try:
        await m.delete()
    except:
        pass

    data["stats"]["blocked"] += 1
    save_data(data)

    text = random.choice(messages).format(user=m.from_user.mention)
    sent = await m.chat.send_message(text, reply_markup=get_keyboard())

    try:
        until = datetime.utcnow() + timedelta(seconds=30)
        await app.restrict_chat_member(m.chat.id, m.from_user.id, ChatPermissions(), until_date=until)
    except:
        pass

    await asyncio.sleep(30)
    try:
        await sent.delete()
    except:
        pass

@app.on_callback_query(filters.regex("check_sub"))
async def chk(_, c):
    if await check_subscription(c.from_user.id):
        await c.answer("✅ Obuna tasdiqlandi!", True)
        try:
            await c.message.delete()
        except:
            pass
    else:
        await c.answer("❌ Hali obuna bo‘lmagansiz!", True)

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    app.run()
