import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait

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
    "💫 {user}, siz ajoyib odamsiz! Endi kanalga ham obuna bo'ling!",
    "🚀 Do'stim {user}, kanallarimizda foydali ma'lumotlar bor. Obuna bo'ling!",
    "🌟 {user}, guruhda yozish uchun kanalga obuna bo'lish kerak!",
    "💎 {user}, siz muhim a'zomiz! Kanalga qo'shiling!",
    "🎉 {user}, kanallarimizda yangiliklar kutmoqda! Obuna bo'ling!"
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
        link = ch.get("invite_link", "")
        username = ch.get("username", "")
        
        if link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=link)])
        elif username:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=f"https://t.me/{username}")])
        else:
            buttons.append([InlineKeyboardButton(f"📣 {title}", callback_data="no_link")])
    
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

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
        
        return {
            "id": int(chat.id),
            "title": getattr(chat, "title", "") or "Kanal",
            "username": getattr(chat, "username", None)
        }
    except Exception as e:
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
        except FloodWait as e:
            await asyncio.sleep(e.value)
            missing.append(ch)
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
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
        )
    except Exception as e:
        print(f"Ruxsat berishda xato: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, m):
    if m.from_user.id in ADMIN_IDS:
        await m.reply("🎛 **ADMIN PANEL**\n\nQuyidagi tugmalardan birini tanlang:", reply_markup=admin_panel())
    else:
        await m.reply("👋 Salom! Men obuna tekshiruvchi botman.\n\nMen guruhda faqat kanallarga obuna bo'lgan foydalanuvchilarga xabar yozishga ruxsat beraman.")

@app.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel_callback(_, c):
    if c.from_user.id not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo'q", show_alert=True)
    await c.edit_message_text("🎛 **ADMIN PANEL**\n\nQuyidagi tugmalardan birini tanlang:", reply_markup=admin_panel())

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo'q", show_alert=True)
    
    user_states[uid] = "waiting_channel_add"
    await c.edit_message_text(
        "📝 **Kanal qo'shish**\n\n"
        "Quyidagi formatlardan birini yuboring:\n\n"
        "1️⃣ Ochiq kanal:\n`@kanalUsername`\n`https://t.me/kanalUsername`\n\n"
        "2️⃣ Maxfiy kanal (ID va havola):\n`-1001234567890|https://t.me/+xxxx`\n\n"
        "3️⃣ Faqat ID:\n`-1001234567890`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_callback(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo'q", show_alert=True)
    
    if not data.get("channels"):
        return await c.answer("📋 Kanallar ro'yxati bo'sh!", show_alert=True)
    
    user_states[uid] = "waiting_channel_del"
    text = "🗑 **Kanal o'chirish**\n\nQaysi kanalni o'chirmoqchisiz?\nKanal ID sini yuboring:\n\n"
    for key, ch in data["channels"].items():
        text += f"• `{key}` - {ch.get('title', 'Kanal')}\n"
    
    await c.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_callback(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo'q", show_alert=True)
    
    if not data.get("channels"):
        await c.edit_message_text(
            "📋 **Kanallar ro'yxati**\n\nHozircha kanallar qo'shilmagan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )
        return
    
    text = "📋 **Kanallar ro'yxati:**\n\n"
    for idx, (key, ch) in enumerate(data["channels"].items(), 1):
        title = ch.get("title", "Kanal")
        link = ch.get("invite_link", "")
        username = ch.get("username", "")
        
        text += f"{idx}. **{title}**\n"
        text += f"   ID: `{key}`\n"
        if username:
            text += f"   Username: @{username}\n"
        if link:
            text += f"   Havola: {link}\n"
        text += "\n"
    
    await c.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^stats$"))
async def stats_callback(_, c):
    uid = c.from_user.id
    if uid not in ADMIN_IDS:
        return await c.answer("❌ Ruxsat yo'q", show_alert=True)
    
    blocked = data["stats"].get("blocked", 0)
    checked = data["stats"].get("checked", 0)
    channels_count = len(data.get("channels", {}))
    
    text = "📊 **Statistika:**\n\n"
    text += f"🔒 To'xtatilgan xabarlar: **{blocked}**\n"
    text += f"✅ Tekshirilgan xabarlar: **{checked}**\n"
    text += f"📣 Kanallar soni: **{channels_count}**\n"
    
    await c.edit_message_text(
        text,
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
                    await msg.edit_text("❌ Havola noto'g'ri. `https://` bilan boshlashi kerak.", reply_markup=admin_panel())
                    user_states.pop(uid, None)
                    return
                
                resolved = await resolve_chat_identifier(id_part)
                if not resolved:
                    await msg.edit_text("❌ Kanal topilmadi. ID ni to'g'ri kiriting.", reply_markup=admin_panel())
                    user_states.pop(uid, None)
                    return
                
                ch_id = resolved["id"]
                title = resolved["title"]
                key = str(ch_id)
                
                data["channels"][key] = {
                    "id": ch_id,
                    "title": title,
                    "username": resolved.get("username", ""),
                    "invite_link": link_part,
                    "is_private": True
                }
                save_data(data)
                
                await msg.edit_text(
                    f"✅ **Kanal qo'shildi!**\n\n"
                    f"📣 Nomi: {title}\n"
                    f"🔗 Havola: {link_part}\n"
                    f"🆔 ID: `{key}`",
                    reply_markup=admin_panel()
                )
                user_states.pop(uid, None)
                return
            
            resolved = await resolve_chat_identifier(text)
            if not resolved:
                await msg.edit_text("❌ Kanal topilmadi. Username yoki ID ni to'g'ri kiriting.", reply_markup=admin_panel())
                user_states.pop(uid, None)
                return
            
            ch_id = resolved["id"]
            title = resolved["title"]
            username = resolved.get("username")
            
            if username:
                invite_link = f"https://t.me/{username}"
                is_priv = False
            else:
                invite_link = ""
                is_priv = True
            
            key = str(ch_id)
            data["channels"][key] = {
                "id": ch_id,
                "title": title,
                "username": username or "",
                "invite_link": invite_link,
                "is_private": is_priv
            }
            save_data(data)
            
            await msg.edit_text(
                f"✅ **Kanal qo'shildi!**\n\n"
                f"📣 Nomi: {title}\n"
                f"🔗 Havola: {invite_link or 'Yo`q (Maxfiy kanal)'}\n"
                f"🆔 ID: `{key}`",
                reply_markup=admin_panel()
            )
        except Exception as e:
            await msg.edit_text(f"❌ Xato: {e}", reply_markup=admin_panel())
        
        user_states.pop(uid, None)
        return
    
    elif state == "waiting_channel_del":
        key = text.strip()
        if key in data["channels"]:
            ch_title = data["channels"][key].get("title", "Kanal")
            del data["channels"][key]
            save_data(data)
            await m.reply(f"✅ **Kanal o'chirildi:** {ch_title}", reply_markup=admin_panel())
        else:
            await m.reply("❌ Bunday ID topilmadi.", reply_markup=admin_panel())
        
        user_states.pop(uid, None)
        return

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
        await lift_restriction(m.chat.id, m.from_user.id)
        return
    
    try:
        await m.delete()
    except Exception as e:
        print(f"Xabar o'chirishda xato: {e}")
    
    data["stats"]["blocked"] = data["stats"].get("blocked", 0) + 1
    save_data(data)
    
    text = random.choice(messages).format(user=m.from_user.mention)
    kb = build_keyboard_for_channels(missing if missing else list(data["channels"].values()))
    
    try:
        await app.restrict_chat_member(
            chat_id=m.chat.id,
            user_id=m.from_user.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
        )
    except Exception as e:
        print(f"Cheklashda xato: {e}")
    
    try:
        await m.chat.send_message(text, reply_markup=kb)
    except Exception as e:
        print(f"Xabar yuborishda xato: {e}")

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
    await c.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
    
    try:
        await c.message.edit_reply_markup(kb)
    except:
        pass

@app.on_callback_query(filters.regex("^no_link$"))
async def no_link_cb(_, c):
    await c.answer("⚠️ Bu kanal uchun havola mavjud emas.", show_alert=True)

if __name__ == "__main__":
    print("=" * 50)
    print("Bot ishga tushdi!")
    print("=" * 50)
    app.run()
