import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, ChatAdminRequired

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
    "✨ {user}, kanallarimizga qo'shiling, keyin suhbat davom etadi!",
    "🎯 {user}, kanallar juda qiziq! Obuna bo'ling!",
    "🔥 Hey {user}! Obuna bo'lish 5 soniya!"
]

def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ])

def build_keyboard_for_channels(ch_list):
    buttons = []
    for ch in ch_list:
        title = ch.get("title", "Kanal")
        link = ch.get("invite_link") or ""
        username = ch.get("username") or ""
        if link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=link)])
        elif username:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=f"https://t.me/{username}")])
        else:
            buttons.append([InlineKeyboardButton(f"📣 {title}", callback_data="no_link")])
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

def get_keyboard():
    channels = []
    for key, ch in data.get("channels", {}).items():
        channels.append(ch)
    return build_keyboard_for_channels(channels)

async def resolve_chat_identifier(text):
    try:
        text = text.strip()
        if text.startswith("https://t.me/+") or text.startswith("https://t.me/joinchat/"):
            return {"error": "need_id", "message": "⚠️ Maxfiy kanal uchun ID yuboring!\nID: `-100xxxxxxxxx`"}
        if text.startswith("https://t.me/"):
            uname = text.replace("https://t.me/", "").split("/")[0]
            if not uname.startswith("@"):
                uname = "@" + uname
            chat = await app.get_chat(uname)
        elif text.startswith("@"):
            chat = await app.get_chat(text)
        elif text.lstrip("-").isdigit():
            chat = await app.get_chat(int(text))
        else:
            chat = await app.get_chat(text)
        return {"id": int(chat.id), "title": getattr(chat, "title", "") or "Kanal", "username": getattr(chat, "username", None)}
    except Exception:
        return None

async def check_subscription(user_id: int):
    if not data.get("channels"):
        return True, [], []
    missing = []
    errors = []
    for key, ch in data["channels"].items():
        ch_id = ch.get("id")
        if not ch_id:
            continue
        try:
            member = await app.get_chat_member(ch_id, user_id)
            status = str(getattr(member, "status", ""))
            if status in ("member", "administrator", "creator", "owner"):
                continue
            if status == "restricted" and getattr(member, "is_member", False):
                continue
            missing.append(ch)
        except UserNotParticipant:
            missing.append(ch)
        except ChatAdminRequired:
            errors.append({"channel": ch, "error": "bot_needs_admin"})
        except Exception as e:
            errors.append({"channel": ch, "error": str(e)})
    return (len(missing) == 0), missing, errors

async def lift_restriction(chat_id: int, user_id: int):
    try:
        await app.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except:
        pass

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, m):
    if m.from_user.id in ADMIN_IDS:
        await m.reply("🎛 ADMIN PANEL", reply_markup=admin_panel())
    else:
        await m.reply("👋 Salom! Men obuna tekshiruvchi botman.")

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo‘q", show_alert=True)
    user_states[uid] = "waiting_channel_add"
    await c.edit_message_text(
        "📝 Kanal qo'shish\nFormat:\n`-1001234567890`\n`@kanal`\n`-1001234567890|https://t.me/+xxxx`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def private_text(_, m):
    uid = m.from_user.id
    if uid not in ADMIN_IDS:
        return
    state = user_states.get(uid)
    if not state:
        return
    text = m.text.strip()
    if state == "waiting_channel_add":
        msg = await m.reply("⏳ Tekshirilmoqda...")
        try:
            if "|" in text:
                id_part, link_part = text.split("|", 1)
                id_part = id_part.strip()
                link_part = link_part.strip()
                if not (link_part.startswith("http://") or link_part.startswith("https://")):
                    await msg.edit_text("❌ Havola noto'g'ri.", reply_markup=admin_panel())
                    user_states.pop(uid, None)
                    return
                resolved = await resolve_chat_identifier(id_part)
                if not resolved:
                    await msg.edit_text("❌ Kanal topilmadi.", reply_markup=admin_panel())
                    user_states.pop(uid, None)
                    return
                ch_id = resolved["id"]
                title = resolved["title"]
                key = str(ch_id)
                data["channels"][key] = {"id": ch_id, "title": title, "username": resolved.get("username") or "", "invite_link": link_part, "is_private": True}
                save_data(data)
                await msg.edit_text(f"✅ Kanal qo'shildi:\n{title}\n{link_part}\n`{key}`", reply_markup=admin_panel())
                user_states.pop(uid, None)
                return
            parts = text.split()
            field = parts[0]
            resolved = await resolve_chat_identifier(field)
            if not resolved:
                await msg.edit_text("❌ Kanal topilmadi.", reply_markup=admin_panel())
                user_states.pop(uid, None)
                return
            ch_id = resolved["id"]
            title = resolved["title"]
            username = resolved.get("username")
            if len(parts) > 1:
                link = parts[1].strip()
                if not (link.startswith("http://") or link.startswith("https://")):
                    await msg.edit_text("❌ Havola noto'g'ri.", reply_markup=admin_panel())
                    user_states.pop(uid, None)
                    return
                invite_link = link
                is_priv = True
            elif username:
                invite_link = f"https://t.me/{username}"
                is_priv = False
            else:
                invite_link = ""
                is_priv = True
            key = str(ch_id)
            data["channels"][key] = {"id": ch_id, "title": title, "username": username or "", "invite_link": invite_link, "is_private": is_priv}
            save_data(data)
            await msg.edit_text(f"✅ Kanal qo'shildi:\n{title}\n{invite_link or '—'}\n`{key}`", reply_markup=admin_panel())
        except Exception as e:
            await msg.edit_text(f"❌ Xato: {e}", reply_markup=admin_panel())
        user_states.pop(uid, None)
        return
    if state == "waiting_channel_del":
        key = text
        if key in data["channels"]:
            title = data["channels"][key].get("title", "Kanal")
            del data["channels"][key]
            save_data(data)
            await m.reply(f"✅ O'chirildi: {title}", reply_markup=admin_panel())
        else:
            await m.reply("❌ Topilmadi!", reply_markup=admin_panel())
        user_states.pop(uid, None)
        return

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_cb(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo‘q", show_alert=True)
    if not data["channels"]:
        return await c.answer("❌ Kanallar yo‘q!", show_alert=True)
    user_states[uid] = "waiting_channel_del"
    txt = "📋 Kanallar:\n\n"
    for i, (cid, ch) in enumerate(data["channels"].items(), 1):
        txt += f"{i}. {ch.get('title')} — `{cid}`\n"
    await c.edit_message_text(txt + "\nID yuboring:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_cb(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo‘q", show_alert=True)
    if not data["channels"]:
        return await c.answer("❌ Kanallar yo‘q!", show_alert=True)
    txt = "📋 Kanallar:\n\n"
    for i, (cid, ch) in enumerate(data["channels"].items(), 1):
        txt += f"{i}. {ch.get('title')} — {ch.get('invite_link') or ch.get('username') or '—'} — `{cid}`\n"
    await c.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^stats$"))
async def stats_cb(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo‘q", show_alert=True)
    s = data["stats"]
    txt = f"📊 Statistika:\n\n🚫 O'chirilgan xabarlar: {s.get('blocked',0)}\n✅ Tekshirilganlar: {s.get('checked',0)}\n📣 Kanallar: {len(data.get('channels',{}))}"
    await c.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel_cb(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo‘q", show_alert=True)
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
    ok, missing, errors = await check_subscription(m.from_user.id)
    if ok:
        return
    try:
        await m.delete()
    except:
        pass
    data["stats"]["blocked"] = data["stats"].get("blocked", 0) + 1
    save_data(data)
    text = random.choice(messages).format(user=m.from_user.mention)
    kb = build_keyboard_for_channels(missing if missing else list(data["channels"].values()))
    try:
        await app.restrict_chat_member(
            chat_id=m.chat.id,
            user_id=m.from_user.id,
            permissions=ChatPermissions(),  # block sending
        )
    except:
        pass
    sent = await m.chat.send_message(text, reply_markup=kb)
    await asyncio.sleep(0)
    return

@app.on_callback_query(filters.regex("^check_sub$"))
async def check_cb(_, c):
    uid = c.from_user.id
    chat = c.message.chat if c.message else None
    ok, missing, errors = await check_subscription(uid)
    if ok:
        if chat:
            await lift_restriction(chat.id, uid)
        await c.answer("✅ Obuna tasdiqlandi! Endi yozishingiz mumkin.", show_alert=True)
        try:
            await c.message.delete()
        except:
            pass
        return
    kb = build_keyboard_for_channels(missing if missing else list(data["channels"].values()))
    await c.answer("❌ Hali obuna bo‘lmagansiz. Kerakli kanallar:", show_alert=True)
    try:
        await c.message.edit_reply_markup(kb)
    except:
        pass

if __name__ == "__main__":
    app.run()
