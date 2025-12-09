import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait, UserAlreadyParticipant

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
    return {"channels": {}, "stats": {"blocked": 0, "checked": 0, "requests_sent": 0}}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

data = load_data()

messages = [
    "😊 Salom {user}! Quyidagi kanallarga qo'shilish so'rovi yuboring, keyin guruhda erkin yozishingiz mumkin!",
    "🤗 Assalomu alaykum {user}! Iltimos kanallarga qo'shilish so'rovi yuboring!",
    "✨ {user}, kanallar tugmasiga bosib so'rov yuboring, keyin suhbat davom etadi!",
    "🎯 {user}, kanallar juda qiziq! So'rov yuboring!",
    "🔥 Hey {user}! Har bir kanal tugmasiga bosing!",
    "💫 {user}, siz ajoyib odamsiz! Kanallarga so'rov yuboring!",
    "🚀 Do'stim {user}, kanallarimizda foydali ma'lumotlar bor. So'rov yuboring!",
    "🌟 {user}, guruhda yozish uchun kanallarga so'rov yuborish kerak!",
    "💎 {user}, siz muhim a'zomiz! Kanallarga qo'shiling!",
    "🎉 {user}, kanallarimizda yangiliklar kutmoqda! So'rov yuboring!"
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
        ch_id = ch.get("id")
        
        if ch_id:
            buttons.append([InlineKeyboardButton(
                f"📣 {title} - So'rov yuborish", 
                callback_data=f"join_request_{ch_id}"
            )])
    
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
        return True, []
    
    missing = []
    all_channels = list(data["channels"].values())
    
    for ch in all_channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue
        
        is_member = False
        
        try:
            member = await app.get_chat_member(ch_id, user_id)
            status = str(member.status)
            
            if status in ["ChatMemberStatus.OWNER", "ChatMemberStatus.ADMINISTRATOR", "ChatMemberStatus.MEMBER"]:
                is_member = True
            elif "owner" in status.lower() or "creator" in status.lower():
                is_member = True
            elif "administrator" in status.lower() or "admin" in status.lower():
                is_member = True
            elif "member" in status.lower():
                is_member = True
            
        except UserNotParticipant:
            is_member = False
        except FloodWait as e:
            await asyncio.sleep(min(e.value, 3))
            try:
                member = await app.get_chat_member(ch_id, user_id)
                status = str(member.status)
                if any(x in status.lower() for x in ["owner", "creator", "administrator", "admin", "member"]):
                    is_member = True
            except:
                is_member = False
        except ChatAdminRequired:
            is_member = False
        except Exception:
            is_member = False
        
        if not is_member:
            missing.append(ch)
    
    return len(missing) == 0, missing

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
    except:
        pass

async def restrict_user(chat_id: int, user_id: int):
    try:
        await app.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_send_polls=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )
    except:
        pass

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
        "3️⃣ Faqat ID:\n`-1001234567890`\n\n"
        "⚠️ **MUHIM:** Bot kanallarda admin bo'lishi kerak!",
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
    requests_sent = data["stats"].get("requests_sent", 0)
    channels_count = len(data.get("channels", {}))
    
    text = "📊 **Statistika:**\n\n"
    text += f"🔒 To'xtatilgan xabarlar: **{blocked}**\n"
    text += f"✅ Tekshirilgan xabarlar: **{checked}**\n"
    text += f"📤 Yuborilgan so'rovlar: **{requests_sent}**\n"
    text += f"📣 Kanallar soni: **{channels_count}**\n"
    
    await c.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^join_request_"))
async def join_request_callback(_, c):
    try:
        channel_id = int(c.data.split("_")[2])
        user_id = c.from_user.id
        
        channel_info = None
        for ch in data["channels"].values():
            if ch.get("id") == channel_id:
                channel_info = ch
                break
        
        if not channel_info:
            await c.answer("❌ Kanal topilmadi!", show_alert=True)
            return
        
        try:
            member = await app.get_chat_member(channel_id, user_id)
            status = str(member.status)
            
            if any(x in status.lower() for x in ["owner", "creator", "administrator", "admin", "member"]):
                await c.answer("✅ Siz allaqachon bu kanalda a'zosiz!", show_alert=True)
                
                if c.message and c.message.chat:
                    await lift_restriction(c.message.chat.id, user_id)
                
                return
        except UserNotParticipant:
            pass
        except:
            pass
        
        try:
            invite_link = await app.create_chat_invite_link(
                channel_id,
                creates_join_request=True
            )
            
            await c.answer(
                f"✅ Qo'shilish so'rovi yuborildi!\n\n"
                f"Kanal adminlari tasdiqlashini kuting.",
                show_alert=True
            )
            
            data["stats"]["requests_sent"] = data["stats"].get("requests_sent", 0) + 1
            save_data(data)
            
            if c.message and c.message.chat:
                await lift_restriction(c.message.chat.id, user_id)
            
            try:
                await app.send_message(
                    user_id,
                    f"📤 **Qo'shilish so'rovi yuborildi!**\n\n"
                    f"📣 Kanal: {channel_info.get('title', 'Kanal')}\n\n"
                    f"✅ Kanal adminlari sizning so'rovingizni ko'rib chiqadi.\n"
                    f"⏳ Tasdiqlashni kuting!\n\n"
                    f"💡 So'rovingiz tasdiqlangach, guruhda erkin yozishingiz mumkin."
                )
            except:
                pass
                
        except UserAlreadyParticipant:
            await c.answer("✅ Siz allaqachon bu kanalda a'zosiz!", show_alert=True)
            if c.message and c.message.chat:
                await lift_restriction(c.message.chat.id, user_id)
        except Exception as e:
            print(f"Join request xatosi: {e}")
            await c.answer(
                "❌ So'rov yuborishda xatolik!\n\n"
                "Iltimos qo'lda kanal linkiga o'ting va so'rov yuboring.",
                show_alert=True
            )
            
    except Exception as e:
        print(f"Callback xatosi: {e}")
        await c.answer("❌ Xatolik yuz berdi!", show_alert=True)

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
                    f"🆔 ID: `{key}`\n\n"
                    f"⚠️ Bot bu kanalda admin bo'lishi kerak!",
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
                f"🆔 ID: `{key}`\n\n"
                f"⚠️ Bot bu kanalda admin bo'lishi kerak!",
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
    try:
        if not m.from_user:
            return
        
        if m.from_user.id in ADMIN_IDS:
            return
        
        if not data.get("channels"):
            return
        
        data["stats"]["checked"] = data["stats"].get("checked", 0) + 1
        save_data(data)
        
        is_subscribed, missing = await check_subscription(m.from_user.id)
        
        if is_subscribed:
            await lift_restriction(m.chat.id, m.from_user.id)
            return
        
        try:
            await m.delete()
        except:
            pass
        
        data["stats"]["blocked"] = data["stats"].get("blocked", 0) + 1
        save_data(data)
        
        await restrict_user(m.chat.id, m.from_user.id)
        
        text = random.choice(messages).format(user=m.from_user.mention)
        kb = build_keyboard_for_channels(missing if missing else list(data["channels"].values()))
        
        try:
            sent_msg = await app.send_message(
                chat_id=m.chat.id,
                text=text,
                reply_markup=kb
            )
        except:
            pass
            
    except:
        pass

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Bot ishga tushdi!")
    print("=" * 50)
    print("\n✅ IMKONIYATLAR:")
    print("1. Xabarlarni tekshirish va o'chirish")
    print("2. Kanal tugmasiga bosilganda so'rov yuborish")
    print("3. So'rov yuborilgach guruhda yozish ruxsati")
    print("4. Kanal adminlari so'rovlarni ko'radi")
    print("\n⚠️ MUHIM:")
    print("• Bot guruhda admin bo'lishi kerak")
    print("• Bot kanallarda admin bo'lishi kerak")
    print("• 'Invite Users via Link' huquqi yoqilgan bo'lsin")
    print("\n" + "=" * 50 + "\n")
    app.run()
