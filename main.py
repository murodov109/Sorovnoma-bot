import os
import asyncio
import random
import json
import logging
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, UserIsBlocked, ChannelInvalid, UsernameInvalid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = []
if os.getenv("ADMIN_IDS"):
    try:
        ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS").split(",") if x.strip()]
    except:
        ADMIN_IDS = []

app = Client("sub_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "data.json"
user_states = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"channels": {}, "stats": {"blocked": 0, "checked": 0}}

def save_data(d):
    with open(DATA_FILE, "w") as f:
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

async def check_subscription(user_id: int) -> bool:
    if not data.get("channels"):
        return True
    for ch_id_str in list(data["channels"].keys()):
        try:
            ch_id = int(ch_id_str)
        except:
            continue
        try:
            member = await app.get_chat_member(ch_id, user_id)
            status = getattr(member, "status", "")
            if status in ("member", "administrator", "creator"):
                continue
            return False
        except UserNotParticipant:
            return False
        except (UserIsBlocked, ChannelInvalid, UsernameInvalid):
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
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    uid = message.from_user.id
    if uid in ADMIN_IDS:
        await message.reply("🎛 *Admin Panel*\n\nBotni boshqarish uchun quyidagi tugmalardan foydalaning:", reply_markup=admin_panel())
    else:
        await message.reply("👋 Salom! Men guruh uchun obuna tekshirish botiman.")

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    user_states[callback.from_user.id] = "waiting_channel_add"
    await callback.edit_message_text(
        "📝 *Kanal qo'shish*\n\nKanal ID, username yoki invite link yuboring:\n\nMasalan:\n• `@kanalname`\n• `-1001234567890`\n• `https://t.me/+AbCdEfGhIjK`\n\n⚠️ Bot kanalda admin bo'lishi shart!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    if not data["channels"]:
        await callback.answer("❌ Kanallar ro'yxati bo'sh!", show_alert=True)
        return
    user_states[callback.from_user.id] = "waiting_channel_del"
    text = "📋 *Kanallar ro'yxati:*\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        text += f"{i}. {title}\n   `{ch_id}`\n\n"
    text += "✏️ O'chirish uchun kanal ID yoki username yuboring:"
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    if not data["channels"]:
        await callback.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
        return
    text = "📋 *Kanallar ro'yxati:*\n\n"
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
        "📊 *Statistika:*\n\n"
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
    try:
        chat = None
        channel_id_str = None
        if "t.me/" in text or text.startswith("https://") or "+" in text:
            try:
                chat = await app.get_chat(text)
                channel_id_str = str(chat.id)
            except Exception as e:
                await message.reply("❌ Kanal topilmadi! Iltimos to'g'ri havola yuboring.")
                user_states.pop(user_id, None)
                return
        elif text.startswith("@"):
            try:
                chat = await app.get_chat(text)
                channel_id_str = str(chat.id)
            except Exception:
                await message.reply("❌ Kanal topilmadi! Username noto'g'ri.")
                user_states.pop(user_id, None)
                return
        elif text.startswith("-100"):
            try:
                cid = int(text)
                chat = await app.get_chat(cid)
                channel_id_str = str(cid)
            except Exception:
                await message.reply("❌ Kanal topilmadi! ID noto'g'ri.")
                user_states.pop(user_id, None)
                return
        else:
            await message.reply("❌ Noto'g'ri format! Iltimos username, ID yoki link yuboring.")
            user_states.pop(user_id, None)
            return

        if state == "waiting_channel_del":
            if channel_id_str in data["channels"]:
                title = data["channels"][channel_id_str].get("title", "Noma'lum")
                del data["channels"][channel_id_str]
                save_data(data)
                await message.reply(f"✅ Kanal o'chirildi: {title}", reply_markup=admin_panel())
            else:
                await message.reply("❌ Bu kanal ro'yxatda yo'q!")
            user_states.pop(user_id, None)
            return

        # verify bot is admin in channel
        try:
            bot_member = await app.get_chat_member(int(channel_id_str), "me")
            bot_status = getattr(bot_member, "status", "")
            if bot_status not in ("administrator", "creator"):
                await message.reply("❌ Bot bu kanalda admin emas! Iltimos botni kanalga admin qiling.")
                user_states.pop(user_id, None)
                return
            can_invite = False
            if hasattr(bot_member, "privileges") and bot_member.privileges:
                can_invite = getattr(bot_member.privileges, "can_invite_users", False)
            else:
                can_invite = getattr(bot_member, "can_invite_users", False)
            if not can_invite:
                await message.reply("⚠️ Bot kanalda admin, lekin 'Invite users' huquqi yo'q! Bu huquqni bering.")
        except Exception as e:
            await message.reply("❌ Xatolik: Bot kanalda admin emas yoki kanal mavjud emas!")
            user_states.pop(user_id, None)
            return

        invite_link = ""
        is_private = False
        try:
            if getattr(chat, "username", None):
                invite_link = f"https://t.me/{chat.username}"
            else:
                is_private = True
                try:
                    link = await app.export_chat_invite_link(int(channel_id_str))
                    invite_link = link
                except Exception:
                    invite_link = f"https://t.me/c/{str(chat.id)[4:]}/1"
        except Exception:
            is_private = True
            invite_link = f"https://t.me/c/{str(chat.id)[4:]}/1"

        data["channels"][channel_id_str] = {
            "title": getattr(chat, "title", str(channel_id_str)),
            "invite_link": invite_link,
            "is_private": is_private
        }
        save_data(data)
        ch_type = "🔒 Yopiq" if is_private else "🔓 Ochiq"
        await message.reply(
            f"✅ Kanal qo'shildi!\n\nNomi: {getattr(chat,'title', 'Noma''lum')}\nTuri: {ch_type}\nID: `{channel_id_str}`",
            reply_markup=admin_panel()
        )
        user_states.pop(user_id, None)
    except Exception as e:
        await message.reply(f"❌ Xatolik yuz berdi: {str(e)}")
        user_states.pop(user_id, None)

@app.on_message(filters.group & ~filters.service)
async def group_handler(client, message):
    if message.from_user.id in ADMIN_IDS:
        return
    if not data.get("channels"):
        return
    data["stats"]["checked"] = data["stats"].get("checked", 0) + 1
    save_data(data)
    allowed = await check_subscription(message.from_user.id)
    if not allowed:
        try:
            try:
                await message.delete()
            except:
                pass
            data["stats"]["blocked"] = data["stats"].get("blocked", 0) + 1
            save_data(data)
            text = random.choice(messages).format(user=message.from_user.mention)
            until = datetime.utcnow() + timedelta(seconds=10)
            try:
                await client.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    permissions=ChatPermissions(),
                    until_date=until
                )
            except:
                pass
            sent = await client.send_message(message.chat.id, text, reply_markup=get_keyboard())
            await asyncio.sleep(30)
            try:
                await sent.delete()
            except:
                pass
        except Exception:
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
    print("🚀 Bot ishga tushdi...")
    app.run()
