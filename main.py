import os
import re
import json
import asyncio
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import UserNotParticipant, FloodWait
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))

app = Client("video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "bot_data.json"

URL_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|youtube\.com|youtu\.be|tiktok\.com|twitter\.com|x\.com|facebook\.com|fb\.watch|vimeo\.com|dailymotion\.com|twitch\.tv|reddit\.com|pinterest\.com|vm\.tiktok\.com)[^\s]+)'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": [], "channels": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_channels():
    return load_data().get("channels", [])

def add_channel(channel):
    data = load_data()
    channel = channel.replace("@", "").strip()
    if channel and channel not in data["channels"]:
        data["channels"].append(channel)
        save_data(data)
        return True
    return False

def remove_channel(index):
    data = load_data()
    if 0 <= index < len(data["channels"]):
        removed = data["channels"].pop(index)
        save_data(data)
        return removed
    return None

def add_user(user_id):
    data = load_data()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

def get_users():
    return load_data().get("users", [])

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users")],
        [InlineKeyboardButton("📢 Kanallar ro'yxati", callback_data="channels")],
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel"),
         InlineKeyboardButton("➖ Kanal o'chirish", callback_data="remove_channel")],
        [InlineKeyboardButton("📨 Xabar yuborish", callback_data="broadcast")]
    ])

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_menu")]])

pending_action = {}

async def check_subscription(client: Client, user_id: int) -> bool:
    channels = get_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            await client.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return False
        except Exception:
            continue
    return True

def get_subscribe_buttons():
    channels = get_channels()
    buttons = []
    for i, channel in enumerate(channels):
        buttons.append([InlineKeyboardButton(f"📢 {channel}", url=f"https://t.me/{channel}")])
    buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

def get_ydl_opts(url):
    is_instagram = "instagram.com" in url
    is_tiktok = "tiktok.com" in url
    
    cookies_file = "cookies.txt"
    
    opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 60,
        'retries': 5,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_color': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'extractor_retries': 3,
        'file_access_retries': 3,
        'fragment_retries': 10,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    }
    
    if is_instagram:
        opts['http_headers']['Referer'] = 'https://www.instagram.com/'
        opts['http_headers']['Origin'] = 'https://www.instagram.com'
        opts['http_headers']['X-IG-App-ID'] = '936619743392459'
        if os.path.exists(cookies_file):
            opts['cookiefile'] = cookies_file
    
    if is_tiktok:
        opts['http_headers']['Referer'] = 'https://www.tiktok.com/'
        if os.path.exists(cookies_file):
            opts['cookiefile'] = cookies_file
    
    return opts

async def download_video(url: str) -> str | None:
    os.makedirs('downloads', exist_ok=True)
    
    ydl_opts = get_ydl_opts(url)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename
                
                for ext in ['mp4', 'webm', 'mkv', 'mov']:
                    alt_file = filename.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(alt_file):
                        return alt_file
    except Exception as e:
        print(f"Download error: {e}")
    
    return None

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, msg: Message):
    add_user(msg.from_user.id)
    
    if not await check_subscription(client, msg.from_user.id):
        await msg.reply(
            "👋 Assalomu alaykum!\n\n"
            "🔒 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_subscribe_buttons()
        )
        return
    
    await msg.reply(
        "👋 Xush kelibsiz!\n\n"
        "🎬 Men ijtimoiy tarmoqlardan video yuklab beraman:\n\n"
        "📱 Instagram - Reels, Post, Story\n"
        "🎥 YouTube - Video, Shorts\n"
        "🎵 TikTok - Video\n"
        "🐦 Twitter/X - Video\n"
        "📘 Facebook - Video\n"
        "🎬 Vimeo, Dailymotion va boshqalar\n\n"
        "📎 Foydalanish: Video havolasini yuboring!"
    )

@app.on_message(filters.command("admin") & filters.private)
async def admin_cmd(client: Client, msg: Message):
    if msg.from_user.id not in ADMINS:
        await msg.reply("❌ Sizda admin huquqi yo'q!")
        return
    
    await msg.reply(
        "🛠 Admin Panel\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=get_main_menu()
    )

@app.on_callback_query()
async def callback_handler(client: Client, cb: CallbackQuery):
    user_id = cb.from_user.id
    data = cb.data
    
    if data == "check_sub":
        if await check_subscription(client, user_id):
            await cb.message.edit_text(
                "✅ Obuna tasdiqlandi!\n\n"
                "🎬 Endi video havolasini yuboring!"
            )
        else:
            await cb.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
        return
    
    if user_id not in ADMINS:
        await cb.answer("❌ Sizda admin huquqi yo'q!", show_alert=True)
        return
    
    if data == "back_to_menu":
        pending_action.pop(user_id, None)
        await cb.message.edit_text(
            "🛠 Admin Panel\n\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=get_main_menu()
        )
    
    elif data == "stats":
        users = get_users()
        channels = get_channels()
        await cb.message.edit_text(
            f"📊 Statistika\n\n"
            f"👥 Jami foydalanuvchilar: {len(users)} ta\n"
            f"📢 Majburiy kanallar: {len(channels)} ta",
            reply_markup=get_back_button()
        )
    
    elif data == "users":
        users = get_users()
        users_text = ", ".join(map(str, users[:20]))
        if len(users) > 20:
            users_text += "..."
        await cb.message.edit_text(
            f"👥 Foydalanuvchilar\n\n"
            f"📈 Jami: {len(users)} ta\n\n"
            f"🆔 ID lar:\n{users_text}" if users else "👥 Foydalanuvchilar\n\nHozircha foydalanuvchi yo'q",
            reply_markup=get_back_button()
        )
    
    elif data == "channels":
        channels = get_channels()
        if channels:
            channels_text = "\n".join([f"{i+1}. @{c}" for i, c in enumerate(channels)])
        else:
            channels_text = "Hozircha kanal yo'q"
        await cb.message.edit_text(
            f"📢 Majburiy obuna kanallari:\n\n{channels_text}",
            reply_markup=get_back_button()
        )
    
    elif data == "add_channel":
        pending_action[user_id] = "add_channel"
        await cb.message.edit_text(
            "➕ Kanal qo'shish\n\n"
            "📝 Kanal username ni yuboring:\n\n"
            "Masalan: @kanal_nomi yoki kanal_nomi\n\n"
            "⚠️ Bot kanalda admin bo'lishi kerak!",
            reply_markup=get_back_button()
        )
    
    elif data == "remove_channel":
        channels = get_channels()
        if not channels:
            await cb.answer("❌ Hozircha kanallar yo'q!", show_alert=True)
            return
        pending_action[user_id] = "remove_channel"
        channels_text = "\n".join([f"{i+1}. @{c}" for i, c in enumerate(channels)])
        await cb.message.edit_text(
            f"➖ Kanal o'chirish\n\n"
            f"📋 Mavjud kanallar:\n{channels_text}\n\n"
            f"📝 O'chirmoqchi bo'lgan kanal raqamini yuboring:",
            reply_markup=get_back_button()
        )
    
    elif data == "broadcast":
        pending_action[user_id] = "broadcast"
        await cb.message.edit_text(
            "📨 Xabar yuborish\n\n"
            "📝 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:",
            reply_markup=get_back_button()
        )

@app.on_message(filters.private & filters.text & ~filters.command(["start", "admin"]))
async def handle_message(client: Client, msg: Message):
    user_id = msg.from_user.id
    add_user(user_id)
    text = msg.text.strip()
    
    if user_id in pending_action:
        action = pending_action.pop(user_id)
        
        if action == "add_channel":
            channel = text.replace("@", "").strip()
            if add_channel(channel):
                await msg.reply(
                    f"✅ Kanal qo'shildi!\n\n"
                    f"📢 @{channel} majburiy obuna ro'yxatiga qo'shildi.",
                    reply_markup=get_back_button()
                )
            else:
                await msg.reply(
                    "❌ Xatolik!\n\n"
                    "Kanal allaqachon mavjud yoki noto'g'ri format.",
                    reply_markup=get_back_button()
                )
            return
        
        elif action == "remove_channel":
            try:
                index = int(text) - 1
                removed = remove_channel(index)
                if removed:
                    await msg.reply(
                        f"✅ Kanal o'chirildi!\n\n"
                        f"📢 @{removed} ro'yxatdan o'chirildi.",
                        reply_markup=get_back_button()
                    )
                else:
                    await msg.reply("❌ Noto'g'ri raqam!", reply_markup=get_back_button())
            except ValueError:
                await msg.reply("❌ Raqam kiriting!", reply_markup=get_back_button())
            return
        
        elif action == "broadcast":
            users = get_users()
            sent, failed = 0, 0
            status_msg = await msg.reply("📨 Xabar yuborilmoqda...")
            
            for uid in users:
                try:
                    await client.send_message(uid, text)
                    sent += 1
                    await asyncio.sleep(0.05)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception:
                    failed += 1
            
            await status_msg.edit_text(
                f"📨 Xabar yuborildi!\n\n"
                f"✅ Yuborildi: {sent} ta\n"
                f"❌ Yuborilmadi: {failed} ta",
                reply_markup=get_back_button()
            )
            return
    
    if not await check_subscription(client, user_id):
        await msg.reply(
            "🔒 Avval kanallarga obuna bo'ling:",
            reply_markup=get_subscribe_buttons()
        )
        return
    
    urls = re.findall(URL_REGEX, text)
    if not urls:
        await msg.reply(
            "📎 Video havolasini yuboring!\n\n"
            "🌐 Qo'llab-quvvatlanadigan platformalar:\n"
            "Instagram, YouTube, TikTok, Twitter, Facebook va boshqalar"
        )
        return
    
    for url in urls:
        status_msg = await msg.reply("⏳ Video yuklanmoqda...\n\nIltimos, kuting...")
        
        try:
            video_path = await download_video(url)
            
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                
                if file_size > 50 * 1024 * 1024:
                    await status_msg.edit_text("❌ Video hajmi 50MB dan katta!")
                    os.remove(video_path)
                    continue
                
                await status_msg.edit_text("📤 Video yuborilmoqda...")
                
                await msg.reply_video(
                    video=video_path,
                    caption="✅ Video yuklandi!\n\n🤖 Bot orqali yuklandi"
                )
                await status_msg.delete()
                os.remove(video_path)
            else:
                await status_msg.edit_text(
                    "⚠️ Video yuklab bo'lmadi\n\n"
                    "Sabablari:\n"
                    "- Havola noto'g'ri yoki eskirgan\n"
                    "- Video yopiq akkauntda\n"
                    "- Platforma cheklovlari\n\n"
                    "💡 Maslahat: Reels havolasini to'g'ridan-to'g'ri nusxalang"
                )
        except Exception as e:
            print(f"Error: {e}")
            await status_msg.edit_text(
                "⚠️ Xatolik yuz berdi\n\n"
                "🔄 Qaytadan urinib ko'ring!"
            )

print("🤖 Bot ishga tushdi!")
app.run()
