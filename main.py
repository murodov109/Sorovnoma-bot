import os
import sqlite3
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip()]
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL_ID")
DB = os.getenv("DB_PATH","/mnt/data/bot.db")
PREMIUM_COST = int(os.getenv("PREMIUM_COST", "250"))
REF_REWARD = int(os.getenv("REF_REWARD", "3"))
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "15"))
EMOJI_MAP = {15:"🐻",25:"🌸",50:"🚀",100:"💎"}

os.makedirs(os.path.dirname(DB), exist_ok=True)
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
conn = sqlite3.connect(DB, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY,
 tg_id INTEGER UNIQUE,
 username TEXT,
 first_name TEXT,
 balance INTEGER DEFAULT 0,
 invited_by INTEGER,
 is_admin INTEGER DEFAULT 0,
 joined_at TEXT,
 premium_until TEXT
);
CREATE TABLE IF NOT EXISTS referrals(
 id INTEGER PRIMARY KEY,
 referrer INTEGER,
 referee INTEGER,
 status TEXT,
 created_at TEXT
);
CREATE TABLE IF NOT EXISTS channels(
 id INTEGER PRIMARY KEY,
 chat_id TEXT UNIQUE,
 title TEXT,
 is_zayavka INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS withdrawals(
 id INTEGER PRIMARY KEY,
 user_id INTEGER,
 amount INTEGER,
 status TEXT,
 created_at TEXT
);
CREATE TABLE IF NOT EXISTS premium_requests(
 id INTEGER PRIMARY KEY,
 user_id INTEGER,
 amount INTEGER,
 status TEXT,
 created_at TEXT
);
CREATE TABLE IF NOT EXISTS settings(
 k TEXT PRIMARY KEY,
 v TEXT
);
""")
conn.commit()

def get_setting(k, default=None):
    cur.execute("SELECT v FROM settings WHERE k=?", (k,))
    r = cur.fetchone()
    return r["v"] if r else default

def set_setting(k,v):
    cur.execute("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)",(k,str(v)))
    conn.commit()

def ensure_user(m):
    cur.execute("SELECT * FROM users WHERE tg_id=?", (m.from_user.id,))
    if cur.fetchone(): return
    cur.execute("INSERT INTO users(tg_id,username,first_name,joined_at,is_admin) VALUES(?,?,?,?,?)",
                (m.from_user.id, m.from_user.username or "", m.from_user.first_name or "", datetime.utcnow().isoformat(), 1 if m.from_user.id in ADMIN_IDS else 0))
    conn.commit()

def create_referral(ref_code, new_user_id):
    cur.execute("SELECT id FROM users WHERE tg_id=?", (ref_code,))
    r = cur.fetchone()
    if not r: return
    referrer_id = r["id"]
    cur.execute("SELECT id FROM referrals WHERE referrer=? AND referee=?",(referrer_id,new_user_id))
    if cur.fetchone(): return
    cur.execute("INSERT INTO referrals(referrer,referee,status,created_at) VALUES(?,?,?,?)",
                (referrer_id,new_user_id,"pending",datetime.utcnow().isoformat()))
    conn.commit()

async def check_mandatory_subs(user_id):
    cur.execute("SELECT chat_id,is_zayavka FROM channels")
    rows = cur.fetchall()
    mandatories = [r["chat_id"] for r in rows if r["is_zayavka"]==0]
    for chat in mandatories:
        try:
            mem = await app.get_chat_member(chat, user_id)
            if mem.status in ("left","kicked"): return False
        except:
            return False
    return True

def main_menu_kb(is_admin=False):
    buttons = [
        [KeyboardButton("⭐ Mening balansim"), KeyboardButton("🔗 Referal havola")],
        [KeyboardButton("💳 Stars yechish"), KeyboardButton("🎁 Premium olish")],
        [KeyboardButton("📘 Qo‘llanma")]
    ]
    if is_admin: buttons.append([KeyboardButton("🛠 Admin panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def withdraw_inline():
    row = []
    for v in [15,25,50,100]:
        row.append(InlineKeyboardButton(f"{EMOJI_MAP[v]} {v}", callback_data=f"withdraw_{v}"))
    return InlineKeyboardMarkup([row])

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    ensure_user(message)
    args = message.text.split()
    if len(args)>1:
        try:
            ref = int(args[1])
            cur.execute("SELECT id FROM users WHERE tg_id=?", (ref,))
            if cur.fetchone():
                create_referral(ref, message.from_user.id)
        except:
            pass
    cur.execute("SELECT chat_id,is_zayavka FROM channels")
    rows = cur.fetchall()
    kb = []
    for r in rows:
        kb.append([InlineKeyboardButton(r["chat_id"], url=r["chat_id"])])
    kb_markup = InlineKeyboardMarkup(kb) if kb else None
    text = "Botga xush kelibsiz. Iltimos, quyidagi kanallarga obuna bo‘ling."
    await message.reply(text, reply_markup=kb_markup)
    await message.reply("✔ Tasdiqlash", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✔ Tasdiqlash", callback_data="confirm_subs")]]))

@app.on_callback_query()
async def cb(client, callback_query):
    data = callback_query.data
    uid = callback_query.from_user.id
    if data=="confirm_subs":
        ok = await check_mandatory_subs(uid)
        if ok:
            cur.execute("SELECT is_admin FROM users WHERE tg_id=?", (uid,))
            r = cur.fetchone()
            is_admin = True if r and r["is_admin"]==1 else False
            await callback_query.message.reply("✅ Tasdiqlandi. Asosiy panel.", reply_markup=main_menu_kb(is_admin))
            await callback_query.answer()
            cur.execute("SELECT id,referrer FROM referrals WHERE referee=(SELECT id FROM users WHERE tg_id=?) AND status='pending'",(uid,))
            pending = cur.fetchall()
            for p in pending:
                cur.execute("UPDATE referrals SET status='confirmed' WHERE id=?",(p["id"],))
                cur.execute("UPDATE users SET balance = balance + ? WHERE id=?",(REF_REWARD,p["referrer"]))
            conn.commit()
        else:
            await callback_query.answer("Iltimos, majburiy kanallarga obuna bo‘ling.", show_alert=True)
        return
    if data.startswith("withdraw_"):
        amount = int(data.split("_")[1])
        cur.execute("SELECT balance FROM users WHERE tg_id=?",(uid,))
        r = cur.fetchone()
        bal = r["balance"] if r else 0
        if bal < amount or amount < MIN_WITHDRAW:
            await callback_query.answer("Hisobingizda yetarli mablag' yo'q", show_alert=True)
            return
        cur.execute("INSERT INTO withdrawals(user_id,amount,status,created_at) VALUES((SELECT id FROM users WHERE tg_id=?),?,?,?)",
                    (uid,amount,"pending",datetime.utcnow().isoformat()))
        conn.commit()
        cur.execute("SELECT id FROM withdrawals WHERE rowid=last_insert_rowid()")
        wid = cur.fetchone()["id"]
        text = f"⭐ Yangi yechish so‘rovi\n\nUser: @{callback_query.from_user.username or callback_query.from_user.first_name}\nMiqdor: {amount} {EMOJI_MAP.get(amount,'')}\nID: {wid}\nVaqt: {datetime.utcnow().isoformat()}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_w_{wid}"), InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_w_{wid}")]])
        for a in ADMIN_IDS:
            try: await app.send_message(a, text, reply_markup=kb)
            except: pass
        await callback_query.message.reply("So‘rovingiz yuborildi. Adminlar tekshiradi.")
        await callback_query.answer()
        return
    if data.startswith("approve_w_") or data.startswith("reject_w_"):
        if callback_query.from_user.id not in ADMIN_IDS:
            await callback_query.answer("Ruxsat yo'q", show_alert=True); return
        parts = data.split("_")
        action = parts[0]; wid = int(parts[2])
        cur.execute("SELECT withdrawals.id,users.tg_id,withdrawals.amount FROM withdrawals JOIN users ON withdrawals.user_id=users.id WHERE withdrawals.id=?",(wid,))
        r = cur.fetchone()
        if not r: await callback_query.answer("Topilmadi"); return
        if action=="approve":
            cur.execute("UPDATE withdrawals SET status='approved' WHERE id=?",(wid,))
            cur.execute("UPDATE users SET balance = balance - ? WHERE tg_id=?",(r["amount"], r["tg_id"]))
            conn.commit()
            try:
                await app.send_message(NOTIFY_CHANNEL, f"✅ Pul yechish tasdiqlandi\nUser: @{callback_query.from_user.username}\nMiqdor: {r['amount']}")
            except: pass
            try:
                await app.send_message(r["tg_id"], f"✅ Sizning so‘rovingiz tasdiqlandi. Miqdor: {r['amount']}")
            except: pass
            await callback_query.answer("Tasdiqlandi")
        else:
            cur.execute("UPDATE withdrawals SET status='rejected' WHERE id=?",(wid,))
            conn.commit()
            try:
                await app.send_message(r["tg_id"], f"❌ Sizning so‘rovingiz rad etildi. ID: {wid}")
            except: pass
            await callback_query.answer("Rad etildi")
        return

@app.on_message(filters.text)
async def text_handler(client, message):
    ensure_user(message)
    uid = message.from_user.id
    txt = message.text.strip()
    cur.execute("SELECT is_admin FROM users WHERE tg_id=?",(uid,))
    is_admin = cur.fetchone()["is_admin"]==1
    if txt=="⭐ Mening balansim":
        cur.execute("SELECT balance FROM users WHERE tg_id=?",(uid,))
        bal = cur.fetchone()["balance"]
        await message.reply(f"Sizda: {bal} ⭐")
        return
    if txt=="🔗 Referal havola":
        cur.execute("SELECT id FROM users WHERE tg_id=?",(uid,))
        user = cur.fetchone()
        if user:
            link = f"https://t.me/{(await app.get_me()).username}?start={uid}"
            await message.reply(f"Sizning havolangiz: {link}")
        return
    if txt=="💳 Stars yechish":
        await message.reply("Qiymatni tanlang:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"{EMOJI_MAP[v]} {v}", callback_data=f"withdraw_{v}") for v in [15,25,50,100]]]))
        return
    if txt=="🎁 Premium olish":
        cur.execute("SELECT balance FROM users WHERE tg_id=?",(uid,))
        bal = cur.fetchone()["balance"]
        if bal < PREMIUM_COST:
            await message.reply("Hisobingizda yetarli mablag' yo'q")
            return
        cur.execute("INSERT INTO premium_requests(user_id,amount,status,created_at) VALUES((SELECT id FROM users WHERE tg_id=?),?,?,?)",
                    (uid,PREMIUM_COST,"pending",datetime.utcnow().isoformat()))
        conn.commit()
        cur.execute("SELECT id FROM premium_requests WHERE rowid=last_insert_rowid()")
        pid = cur.fetchone()["id"]
        text = f"🎁 Premium so‘rovi\nUser: @{message.from_user.username or message.from_user.first_name}\nMiqdor: {PREMIUM_COST}\nID: {pid}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_p_{pid}"), InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_p_{pid}")]])
        for a in ADMIN_IDS:
            try: await app.send_message(a, text, reply_markup=kb)
            except: pass
        await message.reply("Premium so‘rovingiz yuborildi. Adminlar tekshiradi.")
        return
    if txt=="📘 Qo‘llanma":
        s = f"Referal: har bir tasdiqlangan do‘st uchun +{REF_REWARD} ⭐\nYechish qiymatlari: 15🐻,25🌸,50🚀,100💎\nPremium: {PREMIUM_COST} ⭐"
        await message.reply(s)
        return
    if txt=="🛠 Admin panel" and is_admin:
        kb = ReplyKeyboardMarkup([
            [KeyboardButton("📣 Reklama yuborish"), KeyboardButton("🔗 Majburiy kanallar")],
            [KeyboardButton("📨 Zayavka kanal qo‘shish"), KeyboardButton("📊 Statistika")],
            [KeyboardButton("💵 Yechish so‘rovlari"), KeyboardButton("🎁 Premium so‘rovlari")],
            [KeyboardButton("🔧 Narxlarni sozlash"), KeyboardButton("🚪 Chiqish")]
        ], resize_keyboard=True)
        await message.reply("Admin panel", reply_markup=kb)
        return
    if txt=="🚪 Chiqish":
        await message.reply("Asosiy panelga qaytdingiz.", reply_markup=main_menu_kb(is_admin))
        return

@app.on_callback_query(filters.regex(r"approve_p_\d+|reject_p_\d+"))
async def handle_premium_approve(client, cq):
    if cq.from_user.id not in ADMIN_IDS:
        await cq.answer("Ruxsat yo'q", show_alert=True); return
    parts = cq.data.split("_")
    action = parts[0]; pid = int(parts[2])
    cur.execute("SELECT pr.id,users.tg_id,pr.amount FROM premium_requests pr JOIN users ON pr.user_id=users.id WHERE pr.id=?",(pid,))
    r = cur.fetchone()
    if not r: await cq.answer("Not found"); return
    if action=="approve":
        cur.execute("UPDATE premium_requests SET status='approved' WHERE id=?",(pid,))
        cur.execute("UPDATE users SET balance = balance - ? WHERE tg_id=?",(r["amount"], r["tg_id"]))
        conn.commit()
        try: await app.send_message(r["tg_id"], f"✅ Premium so‘rovingiz tasdiqlandi. {r['amount']}⭐ yechildi.")
        except: pass
        await cq.answer("Tasdiqlandi")
    else:
        cur.execute("UPDATE premium_requests SET status='rejected' WHERE id=?",(pid,))
        conn.commit()
        try: await app.send_message(r["tg_id"], f"❌ Premium so‘rovingiz rad etildi. ID:{pid}")
        except: pass
        await cq.answer("Rad etildi")

if __name__=="__main__":
    print("✅ Bot ishga tushdi")
    for a in ADMIN_IDS:
        try:
            app.start()
            app.send_message(a, "✅ Bot ishga tushdi")
        except: pass
    app.run()
