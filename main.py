import os
import asyncio
import random
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait, ChannelInvalid, UsernameInvalid, UserIsBlocked
from datetime import datetime, timedelta

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

app = Client("sub_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "data.json"
user_states = {}

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

def admin_panel():
    keyboard = [
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_subscription(user_id):
    for channel_id, channel_info in data["channels"].items():
        try:
            member = await app.get_chat_member(channel_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                continue
            else:
                return False
        except UserNotParticipant:
            return False
        except Exception as e:
            continue
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
    if message.from_user.id in ADMIN_IDS:
        await message.reply(
            "🎛 *Admin Panel*\n\n"
            "Botni boshqarish uchun quyidagi tugmalardan foydalaning:",
            reply_markup=admin_panel()
        )
    else:
        await message.reply("👋 Salom! Men guruh uchun obuna tekshirish botiman.")

@app.on_callback_query(filters.regex("admin_panel"))
async def show_admin_panel(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    
    await callback.edit_message_text(
        "🎛 *Admin Panel*\n\n"
        "Botni boshqarish uchun quyidagi tugmalardan foydalaning:",
        reply_markup=admin_panel()
    )

@app.on_callback_query(filters.regex("add_channel"))
async def add_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    
    user_states[callback.from_user.id] = "waiting_channel_add"
    await callback.edit_message_text(
        "📝 *Kanal qo'shish*\n\n"
        "Kanal ID, username yoki invite link yuboring:\n\n"
        "Masalan:\n"
        "• `@kanalname` (ochiq kanal)\n"
        "• `-1001234567890` (ID)\n"
        "• `https://t.me/+AbCdEfGhIjK` (invite link)\n\n"
        "⚠️ Bot kanalda admin bo'lishi shart!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("del_channel"))
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
    
    await callback.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("list_channels"))
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
    
    await callback.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_callback_query(filters.regex("stats"))
async def stats_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    
    text = (
        "📊 *Statistika:*\n\n"
        f"🚫 O'chirilgan xabarlar: {data['stats']['blocked']}\n"
        f"✅ Tekshirilgan foydalanuvchilar: {data['stats']['checked']}\n"
        f"📣 Kanallar soni: {len(data['channels'])}"
    )
    
    await callback.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
    )

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def text_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if not state:
        return
    
    text = message.text.strip()
    
    if state == "waiting_channel_add" or state == "waiting_channel_del":
        try:
            channel_id = None
            chat = None
            
            if "t.me/" in text or "+" in text:
                try:
                    chat = await app.get_chat(text)
                    channel_id = str(chat.id)
                except:
                    await message.reply("❌ Kanal topilmadi! Iltimos to'g'ri havola yuboring.")
                    return
            elif text.startswith("@"):
                try:
                    chat = await app.get_chat(text)
                    channel_id = str(chat.id)
                except:
                    await message.reply("❌ Kanal topilmadi! Username noto'g'ri.")
                    return
            elif text.startswith("-100"):
                try:
                    chat = await app.get_chat(int(text))
                    channel_id = text
                except:
                    await message.reply("❌ Kanal topilmadi! ID noto'g'ri.")
                    return
            else:
                await message.reply("❌ Noto'g'ri format! Iltimos username, ID yoki link yuboring.")
                return
            
            if state == "waiting_channel_del":
                if channel_id in data["channels"]:
                    title = data["channels"][channel_id].get("title", "Noma'lum")
                    del data["channels"][channel_id]
                    save_data(data)
                    await message.reply(
                        f"✅ Kanal o'chirildi: {title}",
                        reply_markup=admin_panel()
                    )
                else:
                    await message.reply("❌ Bu kanal ro'yxatda yo'q!")
                user_states.pop(user_id, None)
                return
            
            try:
                bot_member = await app.get_chat_member(channel_id, "me")
                
                if bot_member.status != "administrator":
                    await message.reply("❌ Bot bu kanalda admin emas! Iltimos botni kanalga admin qiling.")
                    return
                
                can_invite = bot_member.privileges and bot_member.privileges.can_invite_users
                if not can_invite:
                    await message.reply("⚠️ Bot kanalda admin, lekin 'Invite users' huquqi yo'q! Bu huquqni bering.")
                
            except Exception as e:
                await message.reply(f"❌ Xatolik: Bot kanalda admin emas yoki kanal mavjud emas!\n\n{str(e)}")
                return
            
            invite_link = ""
            is_private = False
            
            try:
                if hasattr(chat, 'username') and chat.username:
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
                f"ID: `{channel_id}`",
                reply_markup=admin_panel()
            )
            user_states.pop(user_id, None)
            
        except Exception as e:
            await message.reply(f"❌ Xatolik yuz berdi: {str(e)}")

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
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

if __name__ == "__main__":
    print("🚀 Bot ishga tushdi...")
    app.run()
