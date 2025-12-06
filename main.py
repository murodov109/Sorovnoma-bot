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
    "✨ {user}, kanallarimizga qo'shiling, keyin suhbat davom etadi!",
    "🎯 {user}, kanallar juda qiziq! Obuna bo'ling!",
    "🔥 Hey {user}! Obuna bo'lish 5 soniya!",
    "💫 {user}, ajoyibligingizni davom ettiring — kanalga obuna bo'ling!",
    "🚀 Do'stim {user}, foydali ma'lumotlar kutmoqda!",
    "🌟 {user}, yozish uchun faqat obuna bo‘lish kerak.",
    "💎 {user}, siz bizning muhim a'zomiz!",
    "🎉 {user}, yangiliklarni o'tkazib yubormang!"
]

def get_keyboard():
    buttons = []
    for key, ch in data["channels"].items():
        title = ch.get("title", "Kanal")
        link = ch.get("invite_link")
        if link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=link)])
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def resolve_chat_identifier(text):
    try:
        if text.startswith("https://t.me/+") or text.startswith("https://t.me/joinchat/"):
            return {
                "error": "need_id",
                "message": "⚠️ Maxfiy kanal uchun ID yuboring!\nID: `-100xxxxxxxxx`"
            }

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

        return {
            "id": int(chat.id),
            "title": getattr(chat, "title", ""),
            "username": getattr(chat, "username", None)
        }
    except:
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
            status = str(member.status)
            if status in ["member", "administrator", "creator"]:
                continue
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
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ])

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if message.from_user.id in ADMIN_IDS:
        await message.reply("🎛 ADMIN PANEL", reply_markup=admin_panel())
    else:
        await message.reply("👋 Salom! Men obuna tekshiruvchi botman.")

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(client, callback):
    uid = callback.from_user.id
    if uid not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo‘q", show_alert=True)
        return

    user_states[uid] = "waiting_channel_add"
    await callback.edit_message_text(
        "📝 Kanal ID yoki username yuboring.\n"
        "Format:\n`-1001234567890`\n`@kanal`\n`-1001234567890 https://t.me/+link`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_callback(client, callback):
    uid = callback.from_user.id
    if uid not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo‘q", show_alert=True)
        return

    if not data["channels"]:
        await callback.answer("❌ Kanallar yo‘q!", show_alert=True)
        return

    user_states[uid] = "waiting_channel_del"
    txt = "📋 Kanallar:\n\n"
    for i, (cid, ch) in enumerate(data["channels"].items(), 1):
        txt += f"{i}. {ch.get('title')} — `{cid}`\n"

    await callback.edit_message_text(
        txt + "\nO'chirish uchun kanal ID yuboring:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_callback(client, callback):
    uid = callback.from_user.id
    if uid not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo‘q", show_alert=True)
        return

    if not data["channels"]:
        await callback.answer("❌ Kanallar yo‘q!", show_alert=True)
        return

    txt = "📋 Kanallar:\n\n"
    for i, (cid, ch) in enumerate(data["channels"].items(), 1):
        txt += f"{i}. {ch.get('title')} — `{cid}`\n"

    await callback.edit_message_text(
        txt,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^stats$"))
async def stats_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo‘q", show_alert=True)
        return

    s = data["stats"]
    txt = f"""📊 Statistika:

🚫 O'chirilgan xabarlar: {s.get('blocked', 0)}
✅ Tekshirilganlar: {s.get('checked', 0)}
📣 Kanallar: {len(data['channels'])}
"""
    await callback.edit_message_text(
        txt,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel_callback(client, callback):
    await callback.edit_message_text("🎛 ADMIN PANEL", reply_markup=admin_panel())

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def text_handler(client, message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        return

    state = user_states.get(uid)
    if not state:
        return

    text = message.text.strip()

    if state == "waiting_channel_del":
        if text in data["channels"]:
            title = data["channels"][text]["title"]
            del data["channels"][text]
            save_data(data)
            await message.reply(f"✅ O‘chirildi: {title}", reply_markup=admin_panel())
        else:
            await message.reply("❌ Topilmadi!", reply_markup=admin_panel())

        user_states.pop(uid, None)
        return

    if state == "waiting_channel_add":
        msg = await message.reply("⏳ Tekshirilmoqda...")

        try:
            parts = text.split()
            ch_field = parts[0]
            custom = parts[1] if len(parts) > 1 else None

            resolved = await resolve_chat_identifier(ch_field)
            if not resolved:
                await msg.edit_text("❌ Kanal topilmadi!", reply_markup=admin_panel())
                user_states.pop(uid, None)
                return

            if resolved.get("error"):
                await msg.edit_text(resolved["message"], reply_markup=admin_panel())
                user_states.pop(uid, None)
                return

            cid = resolved["id"]
            title = resolved["title"] or "Kanal"
            username = resolved["username"]

            if custom:
                link = custom
                is_priv = True
            elif username:
                link = f"https://t.me/{username}"
                is_priv = False
            else:
                is_priv = True
                link = ""

            key = str(cid)
            data["channels"][key] = {
                "id": cid,
                "title": title,
                "username": username or "",
                "invite_link": link,
                "is_private": is_priv
            }
            save_data(data)

            await msg.edit_text(
                f"✅ Qo‘shildi!\n\n📌 {title}\n🆔 `{key}`\n🔗 {link}",
                reply_markup=admin_panel()
            )

        except Exception as e:
            await msg.edit_text(f"❌ Xato: {e}", reply_markup=admin_panel())

        user_states.pop(uid, None)
        return

@app.on_message(filters.group & ~filters.service)
async def group_handler(client, message):
    if not message.from_user:
        return

    if message.from_user.id in ADMIN_IDS:
        return

    if not data.get("channels"):
        return

    data["stats"]["checked"] += 1
    save_data(data)

    ok = await check_subscription(message.from_user.id)
    if not ok:
        try:
            await message.delete()
        except:
            pass

        data["stats"]["blocked"] += 1
        save_data(data)

        txt = random.choice(messages).format(user=message.from_user.mention)

        try:
            until = int((datetime.utcnow() + timedelta(seconds=30)).timestamp())
            await client.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                ChatPermissions(),
                until_date=until
            )
        except:
            pass

        sent = await client.send_message(message.chat.id, txt, reply_markup=get_keyboard())
        await asyncio.sleep(30)
        try:
            await sent.delete()
        except:
            pass

@app.on_callback_query(filters.regex("^check_sub$"))
async def callback_handler(client, callback):
    ok = await check_subscription(callback.from_user.id)
    if ok:
        await callback.answer("✅ Obuna tekshirildi!", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
    else:
        await callback.answer("❌ Hali obuna bo‘lmagansiz!", show_alert=True)

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    app.run()
