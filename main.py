import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import os
import sqlite3
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='bot_database.db'):
        self.db_name = db_name
        self.create_tables()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, invited_by INTEGER, premium_status BOOLEAN DEFAULT 0, join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP, state TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, referred_user INTEGER, processed BOOLEAN DEFAULT 0, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, status TEXT DEFAULT 'pending', time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS premium_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, status TEXT DEFAULT 'pending', time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mandatory_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, channel_id TEXT, link TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS zayavka_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, link TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('referral_reward', '3')")
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('premium_price', '250')")
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('minimal_withdraw', '15')")
        conn.commit()
        conn.close()
    
    def user_exists(self, user_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def add_user(self, user_id: int, username: str, invited_by: Optional[int] = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, invited_by) VALUES (?, ?, ?)", (user_id, username, invited_by))
        if invited_by:
            cursor.execute("INSERT INTO referrals (user_id, referred_user) VALUES (?, ?)", (invited_by, user_id))
        conn.commit()
        conn.close()
    
    def get_balance(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def add_balance(self, user_id: int, amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
    
    def subtract_balance(self, user_id: int, amount: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
    
    def get_referred_by(self, user_id: int) -> Optional[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT invited_by FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_referral_count(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE user_id = ? AND processed = 1", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def is_referral_processed(self, referred_user: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT processed FROM referrals WHERE referred_user = ?", (referred_user,))
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    
    def mark_referral_processed(self, referred_user: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE referrals SET processed = 1 WHERE referred_user = ?", (referred_user,))
        conn.commit()
        conn.close()
    
    def get_premium_status(self, user_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT premium_status FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    
    def set_premium_status(self, user_id: int, status: bool):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET premium_status = ? WHERE user_id = ?", (1 if status else 0, user_id))
        conn.commit()
        conn.close()
    
    def get_all_users(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username FROM users")
        users = [{'user_id': row[0], 'username': row[1]} for row in cursor.fetchall()]
        conn.close()
        return users
    
    def set_user_state(self, user_id: int, state: Optional[str]):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET state = ?, last_activity = CURRENT_TIMESTAMP WHERE user_id = ?", (state, user_id))
        conn.commit()
        conn.close()
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def create_withdraw_request(self, user_id: int, amount: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO withdraw_requests (user_id, amount) VALUES (?, ?)", (user_id, amount))
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id
    
    def get_withdraw_request(self, request_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, amount, time FROM withdraw_requests WHERE id = ?", (request_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'user_id': result[0], 'amount': result[1], 'time': result[2]}
        return None
    
    def update_withdraw_status(self, request_id: int, status: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE withdraw_requests SET status = ? WHERE id = ?", (status, request_id))
        conn.commit()
        conn.close()
    
    def create_premium_request(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO premium_requests (user_id) VALUES (?)", (user_id,))
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id
    
    def get_premium_request(self, request_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, time FROM premium_requests WHERE id = ?", (request_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'user_id': result[0], 'time': result[1]}
        return None
    
    def update_premium_status_request(self, request_id: int, status: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE premium_requests SET status = ? WHERE id = ?", (status, request_id))
        conn.commit()
        conn.close()
    
    def get_mandatory_channels(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, channel_id, link FROM mandatory_channels")
        channels = [{'id': row[0], 'name': row[1], 'channel_id': row[2], 'link': row[3]} for row in cursor.fetchall()]
        conn.close()
        return channels
    
    def add_mandatory_channel(self, name: str, channel_id: str, link: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mandatory_channels (name, channel_id, link) VALUES (?, ?, ?)", (name, channel_id, link))
        conn.commit()
        conn.close()
    
    def remove_mandatory_channel(self, channel_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mandatory_channels WHERE id = ?", (channel_id,))
        conn.commit()
        conn.close()
    
    def get_zayavka_channels(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, link FROM zayavka_channels")
        channels = [{'id': row[0], 'name': row[1], 'link': row[2]} for row in cursor.fetchall()]
        conn.close()
        return channels
    
    def add_zayavka_channel(self, name: str, link: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO zayavka_channels (name, link) VALUES (?, ?)", (name, link))
        conn.commit()
        conn.close()
    
    def remove_zayavka_channel(self, channel_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM zayavka_channels WHERE id = ?", (channel_id,))
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str, default: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return int(result[0]) if result else default
    
    def set_setting(self, key: str, value: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        today = datetime.now().date()
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_time) = ?", (today,))
        today_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE processed = 1")
        total_referrals = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM withdraw_requests WHERE status = 'approved'")
        total_withdrawn = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE premium_status = 1")
        premium_users = cursor.fetchone()[0]
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity >= ?", (week_ago,))
        active_users = cursor.fetchone()[0]
        conn.close()
        return {'total_users': total_users, 'today_users': today_users, 'total_referrals': total_referrals, 'total_withdrawn': total_withdrawn, 'premium_users': premium_users, 'active_users': active_users, 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

def check_admin(user_id: int) -> bool:
    admin_ids = os.getenv("ADMIN_IDS", "").split(",")
    return str(user_id) in admin_ids

app = Client("stars_bot", api_id=int(os.getenv("API_ID")), api_hash=os.getenv("API_HASH"), bot_token=os.getenv("BOT_TOKEN"))
db = Database()

async def show_main_menu(client: Client, message: Message, user_id: int):
    is_admin = check_admin(user_id)
    buttons = [[KeyboardButton("⭐ Mening balansim")], [KeyboardButton("🔗 Referal havola")], [KeyboardButton("💳 Stars yechish")], [KeyboardButton("🎁 Premium olish (250 ⭐)")], [KeyboardButton("📘 Qo'llanma")]]
    if is_admin:
        buttons.append([KeyboardButton("🛠 Admin panel")])
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.reply_text("🏠 **Asosiy menyu**\n\nKerakli bo'limni tanlang:", reply_markup=keyboard)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    referred_by = None
    if len(message.text.split()) > 1:
        ref_id = message.text.split()[1]
        if ref_id.isdigit() and int(ref_id) != user_id:
            referred_by = int(ref_id)
    if not db.user_exists(user_id):
        db.add_user(user_id, username, referred_by)
        logger.info(f"Yangi foydalanuvchi: {user_id} (@{username})")
    mandatory_channels = db.get_mandatory_channels()
    zayavka_channels = db.get_zayavka_channels()
    buttons = []
    for channel in mandatory_channels:
        buttons.append([InlineKeyboardButton(f"📢 {channel['name']}", url=channel['link'])])
    for channel in zayavka_channels:
        buttons.append([InlineKeyboardButton(f"📢 {channel['name']}", url=channel['link'])])
    buttons.append([InlineKeyboardButton("✔ Tasdiqlash", callback_data="verify_subscription")])
    welcome_text = "🌟 **Universal Stars Bot**ga xush kelibsiz!\n\n💎 **Bot imkoniyatlari:**\n• ⭐ Stars to'plash\n• 🔗 Referal tizimi orqali daromad\n• 💳 Stars yechib olish\n• 🎁 Telegram Premium olish\n\n📊 **Narxlar:**\n• Har bir referal: 3 ⭐\n• Minimal yechish: 15 ⭐\n• Premium: 250 ⭐\n\n⚡ **Boshlash uchun majburiy kanallarga obuna bo'ling!**"
    await message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("verify_subscription"))
async def verify_subscription(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    mandatory_channels = db.get_mandatory_channels()
    not_subscribed = []
    for channel in mandatory_channels:
        channel_id = channel['channel_id']
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(channel['name'])
        except:
            not_subscribed.append(channel['name'])
    if not_subscribed:
        await callback.answer(f"❌ Iltimos quyidagi kanallarga obuna bo'ling:\n" + "\n".join([f"• {ch}" for ch in not_subscribed]), show_alert=True)
        return
    referred_by = db.get_referred_by(user_id)
    if referred_by and not db.is_referral_processed(user_id):
        referral_reward = db.get_setting('referral_reward', 3)
        db.add_balance(referred_by, referral_reward)
        db.mark_referral_processed(user_id)
        try:
            await client.send_message(referred_by, f"🎉 Sizning havolangiz orqali yangi foydalanuvchi qo'shildi!\n💰 Hisobingizga +{referral_reward} ⭐ qo'shildi!")
        except:
            pass
    await show_main_menu(client, callback.message, user_id)
    await callback.message.delete()

@app.on_message(filters.regex("⭐ Mening balansim") & filters.private)
async def my_balance(client: Client, message: Message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    referral_count = db.get_referral_count(user_id)
    premium_status = db.get_premium_status(user_id)
    status_text = "🎁 Premium" if premium_status else "👤 Oddiy"
    text = f"⭐ **Sizning balansingiz**\n\n💰 Joriy stars: **{balance} ⭐**\n👥 Taklif qilgan do'stlar: **{referral_count}**\n📊 Status: {status_text}\n\n💡 Ko'proq stars yig'ish uchun referal havolangizni ulashing!"
    await message.reply_text(text)

@app.on_message(filters.regex("🔗 Referal havola") & filters.private)
async def referral_link(client: Client, message: Message):
    user_id = message.from_user.id
    bot_username = (await client.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    text = f"🔗 **Sizning referal havolangiz:**\n\n`{ref_link}`\n\n💡 **Qanday ishlaydi?**\n• Havolani do'stlaringizga yuboring\n• Har bir yangi foydalanuvchi uchun **3 ⭐** oling\n• Do'stingiz majburiy kanallarga obuna bo'lgandan keyin bonus hisoblanadi\n\n👥 Hozirda taklif qilganlar: **{db.get_referral_count(user_id)}**"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Havolani ulashish", url=f"https://t.me/share/url?url={ref_link}")]])
    await message.reply_text(text, reply_markup=buttons)

@app.on_message(filters.regex("💳 Stars yechish") & filters.private)
async def withdraw_stars(client: Client, message: Message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    text = f"💳 **Stars yechish**\n\n💰 Sizning balansingiz: **{balance} ⭐**\n\n📊 **Yechish qiymatlari:**"
    buttons = []
    withdraw_amounts = [(15, "🐻"), (25, "🌸"), (50, "🚀"), (100, "💎")]
    for amount, emoji in withdraw_amounts:
        if balance >= amount:
            buttons.append([InlineKeyboardButton(f"{emoji} {amount} stars", callback_data=f"withdraw_{amount}")])
        else:
            buttons.append([InlineKeyboardButton(f"{emoji} {amount} stars ❌", callback_data="insufficient_balance")])
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^withdraw_"))
async def confirm_withdraw(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[1])
    balance = db.get_balance(user_id)
    if balance < amount:
        await callback.answer("❌ Hisobingizda yetarli stars yo'q!", show_alert=True)
        return
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✔ Tasdiqlash", callback_data=f"confirm_withdraw_{amount}"), InlineKeyboardButton("✖ Bekor qilish", callback_data="cancel_withdraw")]])
    await callback.message.edit_text(f"💳 Siz **{amount} ⭐** yechmoqchisiz.\n\nTasdiqlaysizmi?", reply_markup=buttons)

@app.on_callback_query(filters.regex("^confirm_withdraw_"))
async def process_withdraw(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "No username"
    amount = int(callback.data.split("_")[2])
    request_id = db.create_withdraw_request(user_id, amount)
    admin_channel = int(os.getenv("ADMIN_CHANNEL_ID"))
    emoji_map = {15: "🐻", 25: "🌸", 50: "🚀", 100: "💎"}
    admin_text = f"⭐ **Stars yechish so'rovi**\n\n👤 User: @{username}\n🆔 ID: `{user_id}`\n🔢 Miqdor: {amount} {emoji_map.get(amount, '⭐')}\n🕒 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    admin_buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✔ Tasdiqlash", callback_data=f"admin_approve_withdraw_{request_id}"), InlineKeyboardButton("✖ Rad etish", callback_data=f"admin_reject_withdraw_{request_id}")]])
    await client.send_message(admin_channel, admin_text, reply_markup=admin_buttons)
    await callback.message.edit_text("✅ So'rovingiz qabul qilindi!\n\n⏳ Admin tasdiqlashini kuting...")

@app.on_message(filters.regex("🎁 Premium olish") & filters.private)
async def get_premium(client: Client, message: Message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    premium_price = db.get_setting('premium_price', 250)
    if balance < premium_price:
        await message.reply_text(f"❌ Hisobingizda yetarli stars yo'q!\n\n💰 Sizning balansingiz: {balance} ⭐\n💎 Kerak: {premium_price} ⭐")
        return
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✔ Tasdiqlash", callback_data="confirm_premium"), InlineKeyboardButton("✖ Bekor qilish", callback_data="cancel_premium")]])
    await message.reply_text(f"🎁 **Telegram Premium olish**\n\n💰 Narx: {premium_price} ⭐\n⏰ Muddat: 1 oy\n\nAdmin orqali beriladi. Tasdiqlaysizmi?", reply_markup=buttons)

@app.on_callback_query(filters.regex("confirm_premium"))
async def process_premium(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "No username"
    premium_price = db.get_setting('premium_price', 250)
    request_id = db.create_premium_request(user_id)
    admin_channel = int(os.getenv("ADMIN_CHANNEL_ID"))
    admin_text = f"🎁 **Telegram Premium so'rovi**\n\n👤 User: @{username}\n🆔 ID: `{user_id}`\n💳 Miqdor: {premium_price} ⭐\n🕒 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    admin_buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✔ Tasdiqlash", callback_data=f"admin_approve_premium_{request_id}"), InlineKeyboardButton("✖ Rad etish", callback_data=f"admin_reject_premium_{request_id}")]])
    await client.send_message(admin_channel, admin_text, reply_markup=admin_buttons)
    await callback.message.edit_text("✅ So'rovingiz qabul qilindi!\n\n⏳ Admin tasdiqlashini kuting...")

@app.on_message(filters.regex("📘 Qo'llanma") & filters.private)
async def help_guide(client: Client, message: Message):
    text = "📘 **Bot qo'llanmasi**\n\n**⭐ Stars yig'ish:**\n• Referal havolangiz orqali do'stlaringizni taklif qiling\n• Har bir yangi foydalanuvchi uchun 3 ⭐ oling\n• Do'stingiz majburiy kanallarga obuna bo'lishi kerak\n\n**💳 Stars yechish:**\n• Minimal: 15 ⭐\n• Variantlar:\n  🐻 15 stars\n  🌸 25 stars\n  🚀 50 stars\n  💎 100 stars\n\n**🎁 Premium olish:**\n• Narx: 250 ⭐\n• Muddat: 1 oy\n• Admin orqali beriladi\n\n**🔗 Referal tizimi:**\n• Shaxsiy havolangizni oling\n• Do'stlaringizga yuboring\n• Avtomatik bonus oling"
    await message.reply_text(text)

@app.on_message(filters.regex("🛠 Admin panel") & filters.private)
async def admin_panel(client: Client, message: Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        await message.reply_text("❌ Sizda admin huquqlari yo'q!")
        return
    buttons = [[KeyboardButton("📣 Reklama yuborish")], [KeyboardButton("🔗 Majburiy kanallar"), KeyboardButton("📨 Zayavka kanallar")], [KeyboardButton("📊 Statistika")], [KeyboardButton("🔧 Narxlarni sozlash")], [KeyboardButton("🚪 Chiqish")]]
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.reply_text("🛠 **Admin Panel**\n\nKerakli bo'limni tanlang:", reply_markup=keyboard)

@app.on_message(filters.regex("🚪 Chiqish") & filters.private)
async def exit_admin(client: Client, message: Message):
    user_id = message.from_user.id
    await show_main_menu(client, message, user_id)

@app.on_message(filters.regex("📣 Reklama yuborish") & filters.private)
async def broadcast_prompt(client: Client, message: Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        return
    await message.reply_text("📣 **Reklama yuborish**\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:")
    db.set_user_state(user_id, "waiting_broadcast")

@app.on_message(filters.regex("📊 Statistika") & filters.private)
async def statistics(client: Client, message: Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        return
    stats = db.get_statistics()
    text = f"📊 **Bot statistikasi**\n\n👥 Jami foydalanuvchilar: **{stats['total_users']}**\n🆕 Bugungi yangi: **{stats['today_users']}**\n🔗 Jami referallar: **{stats['total_referrals']}**\n💰 Yechilgan stars: **{stats['total_withdrawn']} ⭐**\n🎁 Premium olganlar: **{stats['premium_users']}**\n📈 Aktiv userlar (7 kun): **{stats['active_users']}**\n\n📅 Oxirgi yangilanish: {stats['last_update']}"
    await message.reply_text(text)

@app.on_message(filters.regex("🔗 Majburiy kanallar") & filters.private)
async def manage_mandatory(client: Client, message: Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        return
    channels = db.get_mandatory_channels()
    text = "🔗 **Majburiy kanallar**\n\n"
    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']} - `{ch['channel_id']}`\n"
    else:
        text += "❌ Hozircha kanallar yo'q"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_mandatory")], [InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="remove_mandatory")]])
    await message.reply_text(text, reply_markup=buttons)

@app.on_callback_query(filters.regex("add_mandatory"))
async def add_mandatory_prompt(client: Client, callback: CallbackQuery):
    await callback.message.edit_text("➕ **Majburiy kanal qo'shish**\n\nQuyidagi formatda yuboring:\n`Kanal nomi | @kanal_username | -100xxxxxxxxx`\n\nMisol:\n`My Channel | @mychannel | -1001234567890`")
    db.set_user_state(callback.from_user.id, "adding_mandatory")

@app.on_callback_query(filters.regex("remove_mandatory"))
async def remove_mandatory_prompt(client: Client, callback: CallbackQuery):
    channels = db.get_mandatory_channels()
    if not channels:
        await callback.answer("❌ O'chiriladigan kanallar yo'q!", show_alert=True)
        return
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"delete_mandatory_{ch['id']}")])
    await callback.message.edit_text("🗑 **Kanalni o'chirish**\n\nO'chiriladigan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^delete_mandatory_"))
async def delete_mandatory_channel(client: Client, callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[2])
    db.remove_mandatory_channel(channel_id)
    await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
    await callback.message.delete()

@app.on_message(filters.regex("📨 Zayavka kanallar") & filters.private)
async def manage_zayavka(client: Client, message: Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        return
    channels = db.get_zayavka_channels()
    text = "📨 **Zayavka kanallar** (obuna tekshirilmaydi)\n\n"
    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']} - {ch['link']}\n"
    else:
        text += "❌ Hozircha kanallar yo'q"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_zayavka")], [InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="remove_zayavka")]])
    await message.reply_text(text, reply_markup=buttons)

@app.on_callback_query(filters.regex("add_zayavka"))
async def add_zayavka_prompt(client: Client, callback: CallbackQuery):
    await callback.message.edit_text("➕ **Zayavka kanal qo'shish**\n\nQuyidagi formatda yuboring:\n`Kanal nomi | https://t.me/kanal`\n\nMisol:\n`Zayavka Channel | https://t.me/zayavka`")
    db.set_user_state(callback.from_user.id, "adding_zayavka")

@app.on_callback_query(filters.regex("remove_zayavka"))
async def remove_zayavka_prompt(client: Client, callback: CallbackQuery):
    channels = db.get_zayavka_channels()
    if not channels:
        await callback.answer("❌ O'chiriladigan kanallar yo'q!", show_alert=True)
        return
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"delete_zayavka_{ch['id']}")])
    await callback.message.edit_text("🗑 **Kanalni o'chirish**\n\nO'chiriladigan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^delete_zayavka_"))
async def delete_zayavka_channel(client: Client, callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[2])
    db.remove_zayavka_channel(channel_id)
    await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
    await callback.message.delete()

@app.on_callback_query(filters.regex("^admin_approve_withdraw_"))
async def approve_withdraw(client: Client, callback: CallbackQuery):
    request_id = int(callback.data.split("_")[3])
    request = db.get_withdraw_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return
    db.subtract_balance(request['user_id'], request['amount'])
    db.update_withdraw_status(request_id, 'approved')
    try:
        await client.send_message(request['user_id'], f"✅ So'rovingiz tasdiqlandi!\n\n💰 Miqdor: {request['amount']} ⭐\n🕒 Vaqt: {request['time']}")
    except:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n✅ **Tasdiqlandi**")

@app.on_callback_query(filters.regex("^admin_reject_withdraw_"))
async def reject_withdraw(client: Client, callback: CallbackQuery):
    request_id = int(callback.data.split("_")[3])
    request = db.get_withdraw_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return
    db.update_withdraw_status(request_id, 'rejected')
    try:
        await client.send_message(request['user_id'], f"❌ So'rovingiz rad etildi!\n\n💰 Miqdor: {request['amount']} ⭐")
    except:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n❌ **Rad etildi**")

@app.on_callback_query(filters.regex("^admin_approve_premium_"))
async def approve_premium(client: Client, callback: CallbackQuery):
    request_id = int(callback.data.split("_")[3])
    request = db.get_premium_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return
    premium_price = db.get_setting('premium_price', 250)
    db.subtract_balance(request['user_id'], premium_price)
    db.set_premium_status(request['user_id'], True)
    db.update_premium_status(request_id, 'approved')
    try:
        await client.send_message(request['user_id'], f"✅ Premiumingiz tasdiqlandi!\n\n🎁 1 oylik Telegram Premium\n💰 To'lov: {premium_price} ⭐")
    except:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n✅ **Tasdiqlandi**")

@app.on_callback_query(filters.regex("^admin_reject_premium_"))
async def reject_premium(client: Client, callback: CallbackQuery):
    request_id = int(callback.data.split("_")[3])
    request = db.get_premium_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return
    db.update_premium_status(request_id, 'rejected')
    try:
        await client.send_message(request['user_id'], "❌ Premium so'rovingiz rad etildi!")
    except:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n❌ **Rad etildi**")

@app.on_message(filters.regex("🔧 Narxlarni sozlash") & filters.private)
async def settings_menu(client: Client, message: Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        return
    referral_reward = db.get_setting('referral_reward', 3)
    premium_price = db.get_setting('premium_price', 250)
    text = f"🔧 **Joriy sozlamalar**\n\n🔗 Referal bonusi: **{referral_reward} ⭐**\n💎 Premium narxi: **{premium_price} ⭐**\n\n💳 **Yechish qiymatlari:**\n🐻 15 stars\n🌸 25 stars\n🚀 50 stars\n💎 100 stars\n\n⚠ Yechish qiymatlari va emoji o'zgartirilmaydi!"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Referal bonusini o'zgartirish", callback_data="change_referral")], [InlineKeyboardButton("💎 Premium narxini o'zgartirish", callback_data="change_premium_price")]])
    await message.reply_text(text, reply_markup=buttons)

@app.on_callback_query(filters.regex("change_referral"))
async def change_referral_prompt(client: Client, callback: CallbackQuery):
    await callback.message.edit_text("🔗 **Referal bonusini o'zgartirish**\n\nYangi qiymatni kiriting (faqat raqam):")
    db.set_user_state(callback.from_user.id, "changing_referral")

@app.on_callback_query(filters.regex("change_premium_price"))
async def change_premium_prompt(client: Client, callback: CallbackQuery):
    await callback.message.edit_text("💎 **Premium narxini o'zgartirish**\n\nYangi qiymatni kiriting (faqat raqam):")
    db.set_user_state(callback.from_user.id, "changing_premium")

@app.on_callback_query(filters.regex("cancel_withdraw|cancel_premium|insufficient_balance"))
async def cancel_actions(client: Client, callback: CallbackQuery):
    if callback.data == "insufficient_balance":
        await callback.answer("❌ Hisobingizda yetarli stars yo'q!", show_alert=True)
        return
    action = "yechish" if "withdraw" in callback.data else "premium"
    await callback.message.edit_text(f"❌ {action.capitalize()} so'rovi bekor qilindi.")

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_states(client: Client, message: Message):
    user_id = message.from_user.id
    state = db.get_user_state(user_id)
    if not state:
        return
    if state == "adding_mandatory" and check_admin(user_id):
        try:
            parts = message.text.split("|")
            if len(parts) != 3:
                await message.reply_text("❌ Noto'g'ri format!\n\nTo'g'ri format:\n`Kanal nomi | @username | -100xxxxxxxxx`")
                return
            name = parts[0].strip()
            username = parts[1].strip()
            channel_id = parts[2].strip()
            link = f"https://t.me/{username.replace('@', '')}"
            db.add_mandatory_channel(name, channel_id, link)
            db.set_user_state(user_id, None)
            await message.reply_text(f"✅ Majburiy kanal qo'shildi!\n\n📢 Nomi: {name}\n🔗 Link: {link}\n🆔 ID: `{channel_id}`")
        except Exception as e:
            await message.reply_text(f"❌ Xato: {str(e)}")
    elif state == "adding_zayavka" and check_admin(user_id):
        try:
            parts = message.text.split("|")
            if len(parts) != 2:
                await message.reply_text("❌ Noto'g'ri format!\n\nTo'g'ri format:\n`Kanal nomi | https://t.me/kanal`")
                return
            name = parts[0].strip()
            link = parts[1].strip()
            db.add_zayavka_channel(name, link)
            db.set_user_state(user_id, None)
            await message.reply_text(f"✅ Zayavka kanal qo'shildi!\n\n📢 Nomi: {name}\n🔗 Link: {link}\n\n⚠ Bu kanal obuna tekshirilmaydi!")
        except Exception as e:
            await message.reply_text(f"❌ Xato: {str(e)}")
    elif state == "changing_referral" and check_admin(user_id):
        try:
            new_value = int(message.text)
            if new_value < 1 or new_value > 100:
                await message.reply_text("❌ Qiymat 1 dan 100 gacha bo'lishi kerak!")
                return
            db.set_setting('referral_reward', new_value)
            db.set_user_state(user_id, None)
            await message.reply_text(f"✅ Referal bonusi o'zgartirildi!\n\nYangi qiymat: **{new_value} ⭐**")
        except ValueError:
            await message.reply_text("❌ Iltimos, faqat raqam kiriting!")
    elif state == "changing_premium" and check_admin(user_id):
        try:
            new_value = int(message.text)
            if new_value < 50 or new_value > 1000:
                await message.reply_text("❌ Qiymat 50 dan 1000 gacha bo'lishi kerak!")
                return
            db.set_setting('premium_price', new_value)
            db.set_user_state(user_id, None)
            await message.reply_text(f"✅ Premium narxi o'zgartirildi!\n\nYangi qiymat: **{new_value} ⭐**")
        except ValueError:
            await message.reply_text("❌ Iltimos, faqat raqam kiriting!")
    elif state == "waiting_broadcast" and check_admin(user_id):
        users = db.get_all_users()
        success = 0
        failed = 0
        status_msg = await message.reply_text("📤 Yuborilmoqda...")
        for user in users:
            try:
                await client.send_message(user['user_id'], message.text)
                success += 1
            except:
                failed += 1
        db.set_user_state(user_id, None)
        await status_msg.edit_text(f"✅ Reklama yuborildi!\n\n✔ Muvaffaqiyatli: {success}\n❌ Xato: {failed}")

if __name__ == "__main__":
    logger.info("Bot ishga tushmoqda...")
    app.run()
