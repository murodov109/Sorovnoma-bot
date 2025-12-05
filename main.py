import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, ChannelInvalid, UsernameInvalid, UserIsBlocked, RPCError

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
    "✨ {user}, bir daqiqa vaqt ajratib kanallarimizga qo'shiling, keyin suhbat davom etadi!",
    "🎯 {user}, bizning kanallar juda qiziq! Obuna bo'ling va guruhda faol bo'ling!",
    "🔥 Hey {user}! Kanalga obuna bo'lish 5 soniya, lekin foydasi katta. Qani tezroq!",
    "💫 {user}, siz ajoyib odamsiz! Endi kanalga ham obuna bo'lib ajoyibligingizni davom ettiring!",
    "🚀 Do'stim {user}, kanallarimizda ko'p foydali ma'lumotlar bor. Obuna bo'ling!",
    "🌟 {user}, guruhda yozish uchun faqat kanalga obuna bo'lish kerak. Juda oson!",
    "💎 {user}, siz bizning muhim a'zomiz! Kanalga ham qo'shiling va davom eting!",
    "🎉 {user}, kanallarimizda yangiliklar kutmoqda! Obuna bo'ling va o'tkazib yubormang!"
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
    for i, (channel_id, channel_info) in enumerate(data["channels"].items(), 1):
        invite_link = channel_info.get("invite_link", "")
        title = channel_info.get("title", f"{i}-Kanal")
        if invite_link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=invite_link)])
        else:
            buttons.append([InlineKeyboardButton(f"📣 {title}", callback_data="no_link")])
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def check_subscription(user_id: int) -> bool:
    if not data.get("channels"):
        return True
    for ch_key in list(data["channels"].keys()):
        try:
            target = int(ch_key)
        except:
            target = ch_key
        try:
            member = await app.get_chat_member(target, user_id)
            status = getattr(member, "status", "")
            if status in ("member", "administrator", "creator"):
                continue
            return False
        except UserNotParticipant:
            return False
        except (ChannelInvalid, UsernameInvalid, UserIsBlocked, RPCError):
            return False
        except Exception:
            return False
    return True

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    uid = message.from_user.id
    if uid in ADMIN_IDS:
        await message.reply("🎛 Admin Panel", reply_markup=admin_panel())
    else:
        await message.reply("👋 Salom! Men guruh uchun obuna tekshirish botiman.")

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    user_states[callback.from_user.id] = "waiting_channel_add"
    await callback.edit_message_text("📝 Kanal qo'shish\n\nKanal ID, username yoki invite link yuboring:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    if not data["channels"]:
        await callback.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
        return
    user_states[callback.from_user.id] = "waiting_channel_del"
    text = "📋 Kanallar ro'yxati:\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        ch_type = "🔒 Yopiq" if ch_info.get("is_private") else "🔓 Ochiq"
        text += f"{i}. {ch_type} {title}\n   `{ch_id}`\n\n"
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    if not data["channels"]:
        await callback.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
        return
    text = "📋 Kanallar ro'yxati:\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        ch_type = "🔒 Yopiq" if ch_info.get("is_private") else "🔓 Ochiq"
        text += f"{i}. {ch_type} {title}\n   `{ch_id}`\n\n"
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^stats$"))
async def stats_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    text = (
        "📊 Statistika:\n\n"
        f"🚫 O'chirilgan xabarlar: {data['stats'].get('blocked',0)}\n"
        f"✅ Tekshirilgan foydalanuvchilar: {data['stats'].get('checked',0)}\n"
        f"📣 Kanallar soni: {len(data.get('channels',{}))}"
    )
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def text_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state:
        return
    text = message.text.strip()
    if state == "waiting_channel_del":
        ch_key = text.strip()
        if ch_key in data["channels"]:
            title = data["channels"][ch_key].get("title", "Noma'lum")
            del data["channels"][ch_key]
            save_data(data)
            await message.reply(f"✅ Kanal o'chirildi: {title}", reply_markup=admin_panel())
        else:
            found = None
            for k,v in data["channels"].items():
                if v.get("title","").lower() == text.lower() or k == text:
                    found = k
                    break
            if found:
                title = data["channels"][found].get("title","Noma'lum")
                del data["channels"][found]
                save_data(data)
                await message.reply(f"✅ Kanal o'chirildi: {title}", reply_markup=admin_panel())
            else:
                await message.reply("❌ Bu kanal ro'yxatda yo'q!")
        user_states.pop(user_id, None)
        return
    if state == "waiting_channel_add":
        try:
            chat = None
            channel_id_str = None
            try:
                chat = await app.get_chat(text)
                channel_id_str = str(chat.id)
            except:
                if text.startswith("@") or text.startswith("-100") or "t.me" in text or text.startswith("http"):
                    channel_id_str = text.strip()
                else:
                    channel_id_str = text.strip()
            title = getattr(chat, "title", channel_id_str)
            invite_link = ""
            is_private = False
            try:
                if chat and getattr(chat, "username", None):
                    invite_link = f"https://t.me/{chat.username}"
                    is_private = False
                else:
                    try:
                        invite_link = await app.export_chat_invite_link(int(channel_id_str)) if channel_id_str.lstrip("-").isdigit() else ""
                        is_private = bool(invite_link) or True
                    except:
                        invite_link = ""
                        is_private = True
            except:
                invite_link = ""
                is_private = True
            key = channel_id_str if isinstance(channel_id_str, str) else str(channel_id_str)
            data["channels"][key] = {"title": title, "invite_link": invite_link, "is_private": is_private}
            save_data(data)
            ch_type = "🔒 Yopiq" if is_private else "🔓 Ochiq"
            await message.reply(f"✅ Kanal qo'shildi!\nNomi: {title}\nTuri: {ch_type}\nID: `{key}`", reply_markup=admin_panel())
        except Exception:
            await message.reply("❌ Kanal qo'shishda xatolik yuz berdi.")
        user_states.pop(user_id, None)
        return

@app.on_message(filters.group & ~filters.service)
async def group_handler(client, message):
    if message.from_user.id in ADMIN_IDS:
        return
    if not data.get("channels"):
        return
    data["stats"]["checked"] = data["stats"].get("checked",0) + 1
    save_data(data)
    allowed = await check_subscription(message.from_user.id)
    if not allowed:
        try:
            await message.delete()
        except:
            pass
        data["stats"]["blocked"] = data["stats"].get("blocked",0) + 1
        save_data(data)
        text = random.choice(messages).format(user=message.from_user.mention)
        until = int((datetime.utcnow() + timedelta(seconds=10)).timestamp())
        try:
            await client.restrict_chat_member(chat_id=message.chat.id, user_id=message.from_user.id, permissions=ChatPermissions(), until_date=until)
        except:
            pass
        sent = await client.send_message(message.chat.id, text, reply_markup=get_keyboard())
        await asyncio.sleep(30)
        try:
            await sent.delete()
        except:
            pass

@app.on_callback_query(filters.regex("^check_sub$"))
async def callback_handler(client, callback):
    ok = await check_subscription(callback.from_user.id)
    if ok:
        await callback.answer("✅ Ajoyib! Endi guruhda erkin yozishingiz mumkin!", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
    else:
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

if __name__ == "__main__":
    app.run()
