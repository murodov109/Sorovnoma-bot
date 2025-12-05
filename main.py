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

def get_keyboard():
    buttons = []
    for i, (key, ch_info) in enumerate(data["channels"].items(), 1):
        invite_link = ch_info.get("invite_link", "")
        title = ch_info.get("title", f"{i}-Kanal")
        if invite_link:
            buttons.append([InlineKeyboardButton(f"📣 {title}", url=invite_link)])
        else:
            username = ch_info.get("username", "")
            if username:
                buttons.append([InlineKeyboardButton(f"📣 {title}", url=f"https://t.me/{username}")])
    buttons.append([InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def resolve_chat_identifier(text):
    try:
        if text.startswith("https://t.me/+") or text.startswith("https://t.me/joinchat/"):
            
            if text.startswith("https://t.me/+"):
                invite_hash = text.split("+")[1].split("/")[0].split("?")[0]
            else:
                invite_hash = text.split("joinchat/")[1].split("/")[0].split("?")[0]
            
            try:
                from pyrogram.raw.functions.messages import CheckChatInvite, ImportChatInvite
                from pyrogram.raw.types import ChatInviteAlready, ChatInvite
                
                check_result = await app.invoke(CheckChatInvite(hash=invite_hash))
                
                if isinstance(check_result, ChatInviteAlready):
                    chat = check_result.chat
                    
                    if hasattr(chat, 'id'):
                        raw_id = chat.id
                        if str(raw_id).startswith("-100"):
                            chat_id = raw_id
                        else:
                            chat_id = int(f"-100{raw_id}")
                        
                        title = getattr(chat, 'title', 'Kanal')
                        
                        return {
                            "id": chat_id,
                            "title": title,
                            "username": getattr(chat, 'username', None),
                            "invite_link": text
                        }
                
                elif isinstance(check_result, ChatInvite):
                    
                    try:
                        import_result = await app.invoke(ImportChatInvite(hash=invite_hash))
                        await asyncio.sleep(1)
                        
                        if hasattr(import_result, 'chats') and len(import_result.chats) > 0:
                            chat = import_result.chats[0]
                            raw_id = chat.id
                            
                            if str(raw_id).startswith("-100"):
                                chat_id = raw_id
                            else:
                                chat_id = int(f"-100{raw_id}")
                            
                            title = getattr(chat, 'title', 'Kanal')
                            
                            return {
                                "id": chat_id,
                                "title": title,
                                "username": getattr(chat, 'username', None),
                                "invite_link": text
                            }
                    except:
                        pass
                    
                    title = getattr(check_result, 'title', 'Maxfiy Kanal')
                    
                    if hasattr(check_result, 'chat'):
                        chat = check_result.chat
                        raw_id = chat.id
                        if str(raw_id).startswith("-100"):
                            chat_id = raw_id
                        else:
                            chat_id = int(f"-100{raw_id}")
                        
                        return {
                            "id": chat_id,
                            "title": getattr(chat, 'title', title),
                            "username": None,
                            "invite_link": text
                        }
                    
                    try:
                        await app.join_chat(text)
                        await asyncio.sleep(2)
                        chat = await app.get_chat(text)
                        return {
                            "id": int(chat.id),
                            "title": getattr(chat, "title", title),
                            "username": None,
                            "invite_link": text
                        }
                    except:
                        pass
                
            except Exception as e:
                print(f"CheckChatInvite error: {e}")
            
            try:
                await app.join_chat(text)
                await asyncio.sleep(2)
                chat = await app.get_chat(text)
                return {
                    "id": int(chat.id),
                    "title": getattr(chat, "title", "Maxfiy Kanal"),
                    "username": None,
                    "invite_link": text
                }
            except Exception as e:
                print(f"join_chat error: {e}")
            
            for peer in await app.get_dialogs():
                if hasattr(peer.chat, 'id'):
                    try:
                        chat = await app.get_chat(peer.chat.id)
                        if hasattr(chat, 'invite_link') and chat.invite_link:
                            if invite_hash in str(chat.invite_link):
                                return {
                                    "id": int(chat.id),
                                    "title": getattr(chat, "title", "Kanal"),
                                    "username": getattr(chat, "username", None),
                                    "invite_link": text
                                }
                    except:
                        continue
            
            return None
            
        elif text.startswith("https://t.me/"):
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
    except Exception as e:
        print(f"Resolve error: {e}")
        return None

async def check_subscription(user_id: int) -> bool:
    if not data.get("channels"):
        return True
    
    for key, ch_info in data["channels"].items():
        ch_id = ch_info.get("id")
        
        if not ch_id:
            continue
        
        try:
            member = await app.get_chat_member(ch_id, user_id)
            status = member.status.value if hasattr(member.status, 'value') else str(member.status)
            
            if status in ["member", "administrator", "creator", "owner"]:
                continue
            else:
                return False
                
        except UserNotParticipant:
            return False
        except Exception as e:
            print(f"Check error for channel {ch_id}: {e}")
            return False
    
    return True

def admin_panel():
    keyboard = [
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    uid = message.from_user.id
    if uid in ADMIN_IDS:
        await message.reply("🎛 **ADMIN PANEL**", reply_markup=admin_panel())
    else:
        await message.reply("👋 Salom! Men guruh uchun obuna tekshirish botiman.")

@app.on_callback_query(filters.regex("^add_channel$"))
async def add_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    user_states[callback.from_user.id] = "waiting_channel_add"
    await callback.edit_message_text("📝 **Kanal qo'shish**\n\nKanal username (@kanal), ID (-100...) yoki link (https://t.me/kanal) yuboring:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^del_channel$"))
async def del_channel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    if not data["channels"]:
        await callback.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
        return
    user_states[callback.from_user.id] = "waiting_channel_del"
    text = "📋 **Kanallar ro'yxati:**\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        ch_type = "🔒 Yopiq" if ch_info.get("is_private") else "🔓 Ochiq"
        text += f"{i}. {ch_type} **{title}**\n   `{ch_id}`\n\n"
    text += "\nO'chirish uchun kanal ID yoki nomini yuboring:"
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^list_channels$"))
async def list_channels_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    if not data["channels"]:
        await callback.answer("❌ Hozircha kanallar qo'shilmagan!", show_alert=True)
        return
    text = "📋 **Kanallar ro'yxati:**\n\n"
    for i, (ch_id, ch_info) in enumerate(data["channels"].items(), 1):
        title = ch_info.get("title", "Noma'lum kanal")
        username = ch_info.get("username", "")
        ch_type = "🔒 Yopiq" if ch_info.get("is_private") else "🔓 Ochiq"
        text += f"{i}. {ch_type} **{title}**\n"
        if username:
            text += f"   @{username}\n"
        text += f"   `{ch_id}`\n\n"
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^stats$"))
async def stats_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    text = f"""📊 **Statistika:**

🚫 O'chirilgan xabarlar: {data['stats'].get('blocked', 0)}
✅ Tekshirilgan foydalanuvchilar: {data['stats'].get('checked', 0)}
📣 Kanallar soni: {len(data.get('channels', {}))}"""
    await callback.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))

@app.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel_callback(client, callback):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    await callback.edit_message_text("🎛 **ADMIN PANEL**", reply_markup=admin_panel())

@app.on_message(filters.private & filters.text & ~filters.command(["start"]))
async def text_handler(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if not state:
        return
    
    text = message.text.strip()
    
    if state == "waiting_channel_del":
        key = text.strip()
        if key in data["channels"]:
            title = data["channels"][key].get("title", "Noma'lum")
            del data["channels"][key]
            save_data(data)
            await message.reply(f"✅ Kanal o'chirildi: **{title}**", reply_markup=admin_panel())
        else:
            found = None
            for k, v in data["channels"].items():
                if v.get("title", "").lower() == text.lower() or k == text:
                    found = k
                    break
            if found:
                title = data["channels"][found].get("title", "Noma'lum")
                del data["channels"][found]
                save_data(data)
                await message.reply(f"✅ Kanal o'chirildi: **{title}**", reply_markup=admin_panel())
            else:
                await message.reply("❌ Bu kanal ro'yxatda yo'q!", reply_markup=admin_panel())
        user_states.pop(user_id, None)
        return
    
    if state == "waiting_channel_add":
        try:
            msg = await message.reply("⏳ Kanal tekshirilmoqda...")
            
            resolved = await resolve_chat_identifier(text)
            
            if not resolved:
                await msg.edit_text("❌ Kanal topilmadi yoki bot kanalga kira olmadi.\n\n**Sabablari:**\n• Havola noto'g'ri\n• Bot kanaldan chiqarilgan\n• Havola muddati tugagan", reply_markup=admin_panel())
                user_states.pop(user_id, None)
                return
            
            ch_id = resolved["id"]
            title = resolved.get("title") or "Maxfiy Kanal"
            username = resolved.get("username")
            
            if "invite_link" in resolved and resolved["invite_link"]:
                invite_link = resolved["invite_link"]
                is_private = True
            elif username:
                invite_link = f"https://t.me/{username}"
                is_private = False
            else:
                invite_link = text if text.startswith("http") else ""
                is_private = True
            
            key = str(ch_id)
            data["channels"][key] = {
                "id": ch_id,
                "title": title,
                "username": username or "",
                "invite_link": invite_link,
                "is_private": is_private
            }
            save_data(data)
            
            ch_type = "🔒 Yopiq" if is_private else "🔓 Ochiq"
            await msg.edit_text(f"✅ **Kanal muvaffaqiyatli qo'shildi!**\n\n📌 Nomi: **{title}**\n🔐 Turi: {ch_type}\n🆔 ID: `{key}`", reply_markup=admin_panel())
        except Exception as e:
            print(f"Add channel error: {e}")
            await message.reply(f"❌ Xatolik yuz berdi: {str(e)}", reply_markup=admin_panel())
        user_states.pop(user_id, None)
        return

@app.on_message(filters.group & ~filters.service)
async def group_handler(client, message):
    if not message.from_user:
        return
    
    if message.from_user.id in ADMIN_IDS:
        return
    
    if not data.get("channels"):
        return
    
    data["stats"]["checked"] = data["stats"].get("checked", 0) + 1
    save_data(data)
    
    allowed = await check_subscription(message.from_user.id)
    
    if not allowed:
        try:
            await message.delete()
        except:
            pass
        
        data["stats"]["blocked"] = data["stats"].get("blocked", 0) + 1
        save_data(data)
        
        text = random.choice(messages).format(user=message.from_user.mention)
        
        try:
            until = int((datetime.utcnow() + timedelta(seconds=30)).timestamp())
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
    print("Bot ishga tushdi...")
    app.run()
