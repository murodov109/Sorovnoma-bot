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
temp_channel = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channels": {}, "stats": {"blocked": 0, "checked": 0}}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

data = load_data()

messages = [
    "😊 Salom {user}! Kanallarimizga obuna bo'lsangiz, guruhda erkin suhbatlashishingiz mumkin!",
    "🤗 Assalomu alaykum {user}! Iltimos avval kanallarimizga a'zo bo'ling, keyin yozamiz!",
    "✨ {user}, bir daqiqa vaqt ajratib kanallarimizga qo'shiling, keyin suhbat davom etadi!",
    "🎯 {user}, bizning kanallar juda qiziq! Obuna bo'ling va guruhda faol bo'ling!",
    "🔥 Hey {user}! Kanalga obuna bo'lish 5 soniya, lekin foydasi katta. Qani tezroq!"
]

def admin_panel():
    keyboard = [
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_keyboard():
    buttons = []
    for key, ch in data.get("channels", {}).items():
        title = ch.get("title", "Kanal")
        link = ch.get("invite_link", "")
        if link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=link)])
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def resolve_chat_identifier(text):
    try:
        text = text.strip()
        if text.startswith("https://t.me/+") or text.startswith("https://t.me/joinchat/"):
            return {"error": "need_id", "message": "⚠️ Maxfiy kanal uchun ID yuboring!\n\nID: `-100xxxxxxxxx` ko'rinishida yuboring."}
        if text.startswith("https://t.me/"):
            username = text.replace("https://t.me/", "").split("/")[0]
            if not username.startswith("@"):
                username = "@" + username
            chat = await app.get_chat(username)
        elif text.startswith("@"):
            chat = await app.get_chat(text)
        elif text.lstrip("-").isdigit():
            chat = await app.get_chat(int(text))
        else:
            chat = await app.get_chat(text)
        return {"id": int(chat.id), "title": getattr(chat, "title", "") or "Kanal", "username": getattr(chat, "username", None)}
    except Exception:
        return None

async def check_subscription(user_id: int) -> bool:
    if not data.get("channels"):
        return True
    for key, ch in data["channels"].items():
        ch_id = ch.get("id")
        if not ch_id:
            continue
        try:
            member = await app.get_chat_member(ch_id, user_id)
            status = getattr(member, "status", "")
            if str(status) in ["member", "administrator", "creator", "owner"]:
                continue
            if str(status) == "restricted" and getattr(member, "is_member", False):
                continue
            return False
        except UserNotParticipant:
            return False
        except Exception:
            return False
    return True

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, m):
    if m.from_user.id in ADMIN_IDS:
        await m.reply("🎛 ADMIN PANEL", reply_markup=admin_panel())
    else:
        await m.reply("👋 Salom! Men guruh uchun obuna tekshirish botiman.")

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
    user_states[c.from_user.id] = "waiting_channel_add"
    await c.edit_message_text(
        "📝 Kanal qo'shish\n\nID yuboring yoki `ID|Havola` formatida yuboring.\nMisol:\n`-1001234567890`\n`-1001234567890|https://t.me/+xxxxx`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_message(filters.private & filters.text & ~filters.command(["start"]))
async def private_text(_, m):
    uid = m.from_user.id
    if uid not in ADMIN_IDS:
        return
    state = user_states.get(uid)
    if not state:
        return

    text = m.text.strip()

    if state == "waiting_channel_add":
        if "|" in text:
            id_part, link_part = text.split("|", 1)
            id_part = id_part.strip()
            link_part = link_part.strip()
            resolved = await resolve_chat_identifier(id_part)
            if not resolved:
                await m.reply("❌ Kanal topilmadi yoki noto'g'ri ID.")
                user_states.pop(uid, None)
                return
            ch_id = resolved["id"]
            title = resolved.get("title", "Kanal")
            invite_link = link_part
            key = str(ch_id)
            data["channels"][key] = {"id": ch_id, "title": title, "invite_link": invite_link}
            save_data(data)
            user_states.pop(uid, None)
            await m.reply(f"✅ Kanal tasdiqlandi va qo'shildi:\n{title}\n`{key}`\n{invite_link}", reply_markup=admin_panel())
            return
        parts = text.split()
        id_candidate = parts[0].strip()
        resolved = await resolve_chat_identifier(id_candidate)
        if not resolved:
            await m.reply("❌ Kanal topilmadi yoki noto'g'ri ID.")
            user_states.pop(uid, None)
            return
        ch_id = resolved["id"]
        title = resolved.get("title", "Kanal")
        if len(parts) > 1:
            invite_link = parts[1].strip()
            key = str(ch_id)
            data["channels"][key] = {"id": ch_id, "title": title, "invite_link": invite_link}
            save_data(data)
            user_states.pop(uid, None)
            await m.reply(f"✅ Kanal tasdiqlandi va qo'shildi:\n{title}\n`{key}`\n{invite_link}", reply_markup=admin_panel())
            return
        temp_channel[uid] = {"id": ch_id, "title": title}
        user_states[uid] = "waiting_channel_link"
        await m.reply("🔗 Maxfiy kanal havolasini yuboring (yoki `cancel` yozing):")

    elif state == "waiting_channel_link":
        if text.lower() == "cancel":
            temp_channel.pop(uid, None)
            user_states.pop(uid, None)
            return await m.reply("❌ Bekor qilindi.", reply_markup=admin_panel())
        invite_link = text.strip()
        ch = temp_channel.pop(uid, None)
        if not ch:
            user_states.pop(uid, None)
            return await m.reply("❌ Xatolik.", reply_markup=admin_panel())
        ch_id = ch["id"]
        title = ch["title"]
        key = str(ch_id)
        data["channels"][key] = {"id": ch_id, "title": title, "invite_link": invite_link}
        save_data(data)
        user_states.pop(uid, None)
        await m.reply(f"✅ Kanal tasdiqlandi va qo'shildi:\n{title}\n`{key}`\n{invite_link}", reply_markup=admin_panel())

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_callback(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
    if not data["channels"]:
        return await c.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
    user_states[c.from_user.id] = "waiting_channel_del"
    text = "📋 Kanallar ro'yxati:\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum")
        text += f"{i}. {title}\n   `{ch_id}`\n\n"
    text += "ID yoki nom yuboring:"
    await c.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_message(filters.private & filters.text & ~filters.command(["start"]))
async def del_handler(_, m):
    uid = m.from_user.id
    if uid not in ADMIN_IDS:
        return
    state = user_states.get(uid)
    if state != "waiting_channel_del":
        return
    key = m.text.strip()
    found = None
    if key in data["channels"]:
        found = key
    else:
        for k, v in data["channels"].items():
            if v.get("title", "").lower() == key.lower():
                found = k
                break
    if found:
        title = data["channels"][found].get("title", "Noma'lum")
        del data["channels"][found]
        save_data(data)
        await m.reply(f"✅ Kanal o'chirildi: {title}", reply_markup=admin_panel())
    else:
        await m.reply("❌ Bu kanal ro'yxatda yo'q!", reply_markup=admin_panel())
    user_states.pop(uid, None)

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_callback(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
    if not data["channels"]:
        return await c.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
    text = "📋 Kanallar ro'yxati:\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        link = ch_info.get("invite_link", "")
        text += f"{i}. {title}\n   {link}\n   `{ch_id}`\n\n"
    await c.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^stats$"))
async def stats_callback(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
    text = f"📊 Statistika:\n\n🚫 O'chirilgan xabarlar: {data['stats'].get('blocked',0)}\n✅ Tekshirilgan foydalanuvchilar: {data['stats'].get('checked',0)}\n📣 Kanallar soni: {len(data.get('channels',{}))}"
    await c.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel_callback(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
    await c.edit_message_text("🎛 ADMIN PANEL", reply_markup=admin_panel())

@app.on_message(filters.group & ~filters.service)
async def group_handler(_, m):
    if not m.from_user:
        return
    if m.from_user.id in ADMIN_IDS:
        return
    if not data.get("channels"):
        return
    data["stats"]["checked"] = data["stats"].get("checked", 0) + 1
    save_data(data)
    allowed = await check_subscription(m.from_user.id)
    if allowed:
        return
    try:
        await m.delete()
    except:
        pass
    data["stats"]["blocked"] = data["stats"].get("blocked", 0) + 1
    save_data(data)
    text = random.choice(messages).format(user=m.from_user.mention)
    sent = await m.chat.send_message(text, reply_markup=get_keyboard())
    try:
        until = int((datetime.utcnow() + timedelta(seconds=30)).timestamp())
        await app.restrict_chat_member(m.chat.id, m.from_user.id, ChatPermissions(), until_date=until)
    except:
        pass
    await asyncio.sleep(30)
    try:
        await sent.delete()
    except:
        pass

@app.on_callback_query(filters.regex("^check_sub$"))
async def check_cb(_, c):
    ok = await check_subscription(c.from_user.id)
    if ok:
        await c.answer("✅ Ajoyib! Endi guruhda erkin yozishingiz mumkin!", show_alert=True)
        try:
            await c.message.delete()
        except:
            pass
    else:
        await c.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

if __name__ == "__main__":
    app.run()
