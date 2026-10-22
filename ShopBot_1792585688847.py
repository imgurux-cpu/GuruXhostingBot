import logging
import sqlite3
import re
import os
import time
import json
import csv
import io
import html as html_lib
import hashlib
import hmac
import math
import asyncio
import threading
import uuid
import requests
from urllib.parse import urlencode, urlparse
from contextvars import ContextVar
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# ==================== Configuration ====================
BOT_TOKEN = "8993290288:AAHOzuz0VzI_lhOf_sn5dX99q24KQFz1q_M"
SUPER_ADMIN_ID = 8338141509
# Local SQLite database; the admin Backup File button creates manual snapshots.
RUNTIME_DB_PATH = os.getenv("RUNTIME_DB_PATH", "gx_shop.db")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "").strip()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== Premium Emoji & Button Color ====================
PREMIUM_ICONS = {
    "back": "5267490665117275176",
    "close": "5420130255174145507",     # ❌
    "done": "5352694861990501856",      # ✅
    "refresh": "5375338737028841420",   # 🔄
    "warn": "5336944168944047463",      # ⚠️
    "stop": "5420118804791336929",      # 🛑
    "gear": "5420155432272438703",      # ⚙️
    "user": "5352861489541714456",      # 👤
    "group": "5420145051336485498",     # 🫂
    "king": "5217822164362739968",      # 👑
    "dashboard": "5352877703043258544", # 📊
    "fire": "5337267511261960341",      # 🔥
    "new": "5382357040008021292",       # 🆕
    "add": "5420323438508155202",       # ➕
    "delete": "5422557736330106570",    # 🗑
    "search": "5463352748751753567",    # 🔍
    "note": "5395444784611480792",      # ✏️
    "world": "5336972142066047577",     # 🌐
    "link": "5420517437885943844",      # 🔗
    "gem": "5352838545826420397",       # 💎
    "gift": "5420396762189831222",      # 🎁
    "wait": "5337172996211648018",      # ⌛
    "bkash": "5348469219761626211",     # 💸 bKash
    "nagad": "5352985330628730418",     # Nagad
    "rocket": "5346042941196507141",    # Rocket
    "upay": "6205972007482300169",      # Upay
    "binance": "6253780203282113440",   # Binance
    "card": "5190899075968441286",      # 💳
    "money": "5190576863226933563",     # 💰
    "chat": "5192704641564974847",      # 💬
    "support": "6052964261418769099",   # Support custom emoji
    "transaction": "6089234491434341490", # Transaction ID
    "deposit": "6073556477824472025",     # Deposit
    "balance": "6073556477824472025",     # Balance
    "profile": "6312024679984929396",     # My Profile
    "buy": "6071402452941279514",         # Buy
    "shield": "5190447043545438788",    # 🛡
    "folder": "5352721946054268944",    # 📁
    "rocket_icon": "5352597830089347330", # 🚀
    "bag": "5229064374403998351",       # 🛍
    "megaphone": "5424818078833715060", # 📣
    "send": "5353001161878182134",      # 📤
    "handshake": "5192805934073685937", # 🤝
    "calendar": "5352585194295564660",  # 📅
    "lock": "5353022963132174959",      # 🔐
    "pin": "5352922460897452503",       # 📍
    "number": "5352862640592949843",    # 🔢
    "balance_main": "6206096153511990389", # 💎 Balance Control Main Icon
    "balance_add": "6206375377925839184",  # ➕ Add Balance Icon
    "balance_cut": "5445267414562389170",  # ➖ Cut Balance Icon
    # Custom Emoji Map
    "owl_proxy": "5280812193380605697",
    "north_vpn": "5345970940364770589",
    "proton_vpn": "5348390922507817684",
    "express_vpn": "5346335574498251610",
    "gmail": "5348494358205207761",
    "proxy": "5796407074346767851",
    "vpn_icon": "5794362687093740845"
}

FALLBACK_ICONS = {
    "back": "◀️", "close": "❌", "done": "✅", "refresh": "🔄",
    "warn": "⚠️", "stop": "🛑", "gear": "⚙️", "user": "👤",
    "group": "👥", "king": "👑", "dashboard": "📊", "fire": "🔥",
    "new": "🆕", "add": "➕", "delete": "🗑️", "search": "🔍",
    "note": "✏️", "world": "🌐", "link": "🔗", "gem": "💎",
    "gift": "🎁", "wait": "⌛", "bkash": "💸", "nagad": "💸",
    "rocket": "🚀", "upay": "💸", "binance": "💠", "card": "💳",
    "money": "💰", "chat": "💬", "support": "🗣️",
    "transaction": "🧾", "deposit": "💠", "balance": "💠",
    "profile": "👤", "buy": "🛍️", "shield": "🛡️", "folder": "📁",
    "rocket_icon": "🚀", "bag": "🛍️", "megaphone": "📣",
    "send": "📤", "handshake": "🤝", "calendar": "📅", "lock": "🔐",
    "pin": "📍", "number": "🔢", "balance_main": "💠",
    "balance_add": "➕", "balance_cut": "➖",
}


def set_current_user(user):
    """Render premium custom emoji only for premium viewers."""
    _current_user_is_premium.set(bool(getattr(user, "is_premium", False)))


def _button_text_with_fallback(text, icon):
    return text


def normalize_button_text(text):
    """Remove a normal-emoji fallback before matching reply-keyboard actions."""
    normalized = str(text or "").strip()
    for fallback in sorted(set(FALLBACK_ICONS.values()), key=len, reverse=True):
        if normalized.startswith(fallback):
            return normalized[len(fallback):].strip()
    return normalized


def pbtn(text, icon=None, style="primary", callback_data=None, url=None):
    kwargs = {}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    emoji_id = PREMIUM_ICONS.get(icon) if icon else None
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if style:
        kwargs["style"] = style
    return InlineKeyboardButton(_button_text_with_fallback(text, icon), **kwargs)

def rkbtn(text, icon=None, style="primary"):
    kwargs = {}
    emoji_id = PREMIUM_ICONS.get(icon) if icon else None
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if style:
        kwargs["style"] = style
    return KeyboardButton(_button_text_with_fallback(text, icon), **kwargs)

TEXT_EMOJI = {
    "❌": "5420130255174145507", "✅": "5352694861990501856", "💰": "5190576863226933563",
    "👤": "5352861489541714456", "💎": "5352838545826420397", "💳": "5190899075968441286",
    "🎁": "5420396762189831222", "🛍": "5229064374403998351", "🛍️": "5229064374403998351",
    "📅": "5352585194295564660", "🏷": "5222444124698853913", "🏷️": "5222444124698853913",
    "⚠": "5336944168944047463", "⚠️": "5336944168944047463", "🔗": "5420517437885943844",
    "📁": "5352721946054268944", "🔢": "5352862640592949843", "📢": "5424818078833715060",
    "🎉": "5461151367559141950", "⚙": "5420155432272438703", "⚙️": "5420155432272438703",
    "🟢": "5416081784641168838", "🔴": "5411225014148014586", "👑": "5217822164362739968",
    "📊": "5352877703043258544", "💬": "5192704641564974847", "🚀": "5352597830089347330",
    "👥": "5420145051336485498", "🚫": "5334807341109908955", "👋": "5353027129250453493",
    "🤑": "6237742262822901946", "💡": "5422439311196834318", "🏆": "5217822164362739968",
    "🧾": "6089234491434341490",
    "💠": "6073556477824472025",
    "🌸": "5348469219761626211", "🟠": "6205988689135277308", "🔄": "5375338737028841420",
    "🛑": "5420118804791336929", "🫂": "5420145051336485498", "🔥": "5337267511261960341",
    "➕": "5420323438508155202", "🗑": "5422557736330106570", "🔍": "5463352748751753567",
    "✏": "5395444784611480792", "✏️": "5395444784611480792", "🌐": "5336972142066047577",
    "💸": "5348469219761626211", "🛡": "5190447043545438788", "📣": "5352980533150259581",
    "📤": "5353001161878182134", "🤝": "5192805934073685937", "🔐": "5353022963132174959",
    "📍": "5352922460897452503", "📱": "5355208818017999139", "⚡": "5456140674028019486",
    "🗣": "6052964261418769099", "🗣️": "6052964261418769099", "🥇": "5440539497383087970",
    "🥈": "5447203607294265305", "🥉": "5453902265922376865", "🔹": "5352638632278660622",
    "🔑": "6316670168151893216", "📦": "5352721946054268944",
}

def pe(text):
    result = text
    for ch, eid in TEXT_EMOJI.items():
        if ch in result:
            result = result.replace(ch, f'<tg-emoji emoji-id="{eid}">{ch}</tg-emoji>')
    return result

def get_product_icon_key(title):
    t_lower = title.lower()
    if 'owl' in t_lower:
        return 'owl_proxy'
    elif 'proton' in t_lower:
        return 'proton_vpn'
    elif 'express' in t_lower:
        return 'express_vpn'
    elif 'north' in t_lower or 'nord' in t_lower:
        return 'north_vpn'
    elif 'gmail' in t_lower:
        return 'gmail'
    elif 'proxy' in t_lower:
        return 'proxy'
    elif 'vpn' in t_lower:
        return 'vpn_icon'
    return 'fire'

# ==================== Database Setup ====================
_current_user_is_premium = ContextVar("current_user_is_premium", default=False)
_force_join_cache = {}
_force_join_cache_lock = threading.Lock()
_deposit_lock = threading.Lock()


def get_db():
    if RUNTIME_DB_PATH != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(RUNTIME_DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(
        RUNTIME_DB_PATH,
        check_same_thread=False,
        timeout=30,
    )
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA synchronous = FULL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT DEFAULT '',
            balance REAL DEFAULT 0.0,
            ref_earnings REAL DEFAULT 0.0,
            referred_by INTEGER DEFAULT 0,
            joined_date TEXT,
            is_banned INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS channels (username TEXT PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS categories (name TEXT PRIMARY KEY)')

    # Safe, in-place migrations for existing bot databases.
    user_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(users)")}
    if "username" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT ''")
    channel_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(channels)")
    }
    if "join_url" not in channel_columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN join_url TEXT DEFAULT ''")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            name TEXT PRIMARY KEY,
            number_or_address TEXT,
            min_deposit REAL DEFAULT 10.0,
            icon_key TEXT DEFAULT 'card'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            title TEXT,
            price REAL,
            item_data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            price REAL,
            date TEXT,
            item_data TEXT,
            order_ref TEXT
        )
    ''')
    purchase_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(purchases)")
    }
    if "item_data" not in purchase_columns:
        cursor.execute("ALTER TABLE purchases ADD COLUMN item_data TEXT")
    if "order_ref" not in purchase_columns:
        cursor.execute("ALTER TABLE purchases ADD COLUMN order_ref TEXT")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            trx_id TEXT UNIQUE,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'pending',
            approved_by INTEGER,
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payout_details TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_by INTEGER,
            reviewed_at TIMESTAMP
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('referral_bonus', '0')")
    cursor.execute("DELETE FROM settings WHERE key = 'referral_commission'")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('support_link', 'https://t.me/your_support_username')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('force_join_status', 'ON')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('log_group_id', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('deposit_notify_enabled', 'OFF')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('deposit_notify_chat_id', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('deposit_notify_type', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '10')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('withdraw_notify_enabled', 'OFF')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('withdraw_notify_chat_id', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usdt_rate', '120')")

    default_methods = [
        ('bKash', '01700000000', 10.0, 'bkash'),
        ('Nagad', '01700000000', 10.0, 'nagad'),
        ('Rocket', '01700000000', 10.0, 'rocket'),
        ('Upay', '01700000000', 10.0, 'upay'),
        ('Binance', '1261150963', 0.1, 'binance')
    ]
    for m_name, m_num, m_min, m_icon in default_methods:
        cursor.execute(
            "INSERT OR IGNORE INTO payment_methods "
            "(name, number_or_address, min_deposit, icon_key) VALUES (?, ?, ?, ?)",
            (m_name, m_num, m_min, m_icon),
        )

    cursor.execute(
        "UPDATE payment_methods SET number_or_address = ? "
        "WHERE name = 'Binance' AND number_or_address = 'binance_pay_id_here'",
        ("1261150963",)
    )
    cursor.execute(
        "DELETE FROM payment_methods WHERE name IN "
        "('Gmail', 'North VPN', 'Proton VPN', 'Express VPN', 'OWL Proxy')"
    )

    # Existing installations may already have the deposits table without the
    # screenshot column. Keep their data and add the new manual-review field.
    try:
        cursor.execute("ALTER TABLE deposits ADD COLUMN screenshot_file_id TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
def complete_product_purchase(user_id, title, category, quantity, unit_price):
    """Debit balance and consume unique product rows in one serialized transaction."""
    conn = get_db()
    total_price = float(unit_price) * int(quantity)
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    order_ref = uuid.uuid4().hex
    try:
        conn.execute("BEGIN IMMEDIATE")
        user_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not user_row:
            conn.rollback()
            return {"status": "user_missing"}

        if user_row["balance"] < total_price:
            conn.rollback()
            return {
                "status": "insufficient_balance",
                "balance": user_row["balance"],
                "total_price": total_price,
            }

        items = conn.execute(
            "SELECT id, item_data FROM products "
            "WHERE category = ? AND title = ? ORDER BY id LIMIT ?",
            (category, title, quantity),
        ).fetchall()
        if len(items) < quantity:
            conn.rollback()
            return {"status": "out_of_stock"}

        debit = conn.execute(
            "UPDATE users SET balance = balance - ? "
            "WHERE user_id = ? AND balance >= ?",
            (total_price, user_id, total_price),
        )
        if debit.rowcount != 1:
            conn.rollback()
            return {"status": "insufficient_balance"}

        for item in items:
            deleted = conn.execute(
                "DELETE FROM products WHERE id = ?", (item["id"],)
            )
            if deleted.rowcount != 1:
                raise sqlite3.IntegrityError("Product stock was already consumed.")
            conn.execute(
                "INSERT INTO purchases "
                "(user_id, title, price, date, item_data, order_ref) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, title, unit_price, today, item["item_data"], order_ref),
            )

        conn.commit()
        return {
            "status": "ok",
            "items": [item["item_data"] for item in items],
            "total_price": total_price,
            "date": today,
            "order_ref": order_ref,
        }
    except Exception:
        conn.rollback()
        logging.exception("Atomic product purchase failed.")
        return {"status": "error"}
    finally:
        conn.close()

# ==================== Helper Functions ====================
def is_admin(user_id):
    if int(user_id) == SUPER_ADMIN_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def is_user_banned(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return (res['is_banned'] == 1) if res else False

def get_all_admin_ids():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    rows = cursor.fetchall()
    conn.close()
    return [row['user_id'] for row in rows]

def get_total_users_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users")
    res = cursor.fetchone()
    conn.close()
    return res['total'] if res else 0

def get_or_create_user(user_id, name, ref_id=0, username=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            today = datetime.now().strftime("%Y-%m-%d")
            safe_ref_id = int(ref_id or 0)
            if safe_ref_id == int(user_id):
                safe_ref_id = 0
            cursor.execute(
                "INSERT INTO users "
                "(user_id, first_name, username, balance, ref_earnings, "
                "referred_by, joined_date, is_banned) "
                "VALUES (?, ?, ?, 0.0, 0.0, ?, ?, 0)",
                (user_id, name, username or "", safe_ref_id, today),
            )
            if safe_ref_id > 0:
                bonus_row = cursor.execute(
                    "SELECT value FROM settings WHERE key = 'referral_bonus'"
                ).fetchone()
                try:
                    referral_bonus = float(bonus_row["value"]) if bonus_row else 0.0
                except (TypeError, ValueError):
                    referral_bonus = 0.0
                if math.isfinite(referral_bonus) and referral_bonus > 0:
                    cursor.execute(
                        "UPDATE users SET balance = balance + ?, "
                        "ref_earnings = ref_earnings + ? WHERE user_id = ?",
                        (referral_bonus, referral_bonus, safe_ref_id),
                    )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    elif username and user["username"] != username:
        cursor.execute(
            "UPDATE users SET first_name = ?, username = ? WHERE user_id = ?",
            (name, username, user_id),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def get_setting(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res['value'] if res else ""

def set_setting(key, value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def get_pending_deposit(user_id):
    """Return the user's oldest pending deposit, if one exists."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, amount, method, trx_id, created_at FROM deposits "
        "WHERE user_id = ? AND status = 'pending' ORDER BY id ASC LIMIT 1",
        (user_id,),
    )
    pending = cursor.fetchone()
    conn.close()
    return pending


def get_pending_withdrawal(user_id):
    conn = get_db()
    pending = conn.execute(
        "SELECT id, amount, created_at FROM withdrawals "
        "WHERE user_id = ? AND status = 'pending' ORDER BY id ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return pending


def create_withdrawal_request(user_id, amount, payout_details):
    """Reserve the requested balance and create one pending withdrawal atomically."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return {"status": "invalid_request"}
    payout_details = str(payout_details or "").strip()
    if (
        not math.isfinite(amount) or amount <= 0
        or not payout_details or len(payout_details) > 300
    ):
        return {"status": "invalid_request"}

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id FROM withdrawals "
            "WHERE user_id = ? AND status = 'pending' LIMIT 1",
            (user_id,),
        ).fetchone()
        if existing:
            conn.rollback()
            return {"status": "pending_exists"}

        debit = conn.execute(
            "UPDATE users SET balance = balance - ? "
            "WHERE user_id = ? AND balance >= ?",
            (amount, user_id, amount),
        )
        if debit.rowcount != 1:
            conn.rollback()
            return {"status": "insufficient_balance"}

        cursor = conn.execute(
            "INSERT INTO withdrawals (user_id, amount, payout_details) "
            "VALUES (?, ?, ?)",
            (user_id, amount, payout_details),
        )
        conn.commit()
        return {"status": "ok", "withdrawal_id": cursor.lastrowid}
    except Exception:
        conn.rollback()
        logging.exception("Could not create withdrawal request.")
        return {"status": "error"}
    finally:
        conn.close()


def review_withdrawal_request(withdrawal_id, admin_id, approve):
    """Approve a reserved withdrawal or refund it once when rejected."""
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT user_id, amount, payout_details, status "
            "FROM withdrawals WHERE id = ?",
            (withdrawal_id,),
        ).fetchone()
        if not row:
            conn.rollback()
            return {"status": "not_found"}
        if row["status"] != "pending":
            conn.rollback()
            return {"status": "already_processed"}

        new_status = "approved" if approve else "rejected"
        updated = conn.execute(
            "UPDATE withdrawals SET status = ?, reviewed_by = ?, reviewed_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (new_status, admin_id, datetime.now(), withdrawal_id),
        )
        if updated.rowcount != 1:
            conn.rollback()
            return {"status": "already_processed"}
        if not approve:
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (row["amount"], row["user_id"]),
            )
        conn.commit()
        return {
            "status": new_status,
            "user_id": row["user_id"],
            "amount": row["amount"],
            "payout_details": row["payout_details"],
        }
    except Exception:
        conn.rollback()
        logging.exception("Could not review withdrawal request.")
        return {"status": "error"}
    finally:
        conn.close()


def deposit_notifications_enabled():
    return (
        get_setting("deposit_notify_enabled") == "ON"
        and bool(get_setting("deposit_notify_chat_id").strip())
    )


def withdrawal_notifications_enabled():
    return (
        get_setting("withdraw_notify_enabled") == "ON"
        and bool(get_setting("withdraw_notify_chat_id").strip())
    )


def get_min_withdraw_amount():
    try:
        amount = float(get_setting("min_withdraw") or 10)
        return amount if math.isfinite(amount) and amount > 0 else 10.0
    except (TypeError, ValueError):
        return 10.0


async def send_deposit_notification(context, text, reply_markup=None):
    """Send deposit alerts to the configured group/channel only."""
    if not deposit_notifications_enabled():
        return False

    target = get_setting("deposit_notify_chat_id").strip()
    try:
        await context.bot.send_message(
            chat_id=target,
            text=pe(text),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return True
    except Exception as error:
        logging.error("Deposit notification target failed: %s", error)
        return False


async def send_withdrawal_notification(context, text, reply_markup=None):
    """Send withdrawal requests to their separately configured review group."""
    if not withdrawal_notifications_enabled():
        return False

    target = get_setting("withdraw_notify_chat_id").strip()
    try:
        await context.bot.send_message(
            chat_id=target,
            text=pe(text),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return True
    except Exception as error:
        logging.error("Withdrawal notification target failed: %s", error)
        return False


async def send_deposit_photo_notification(
    context, screenshot_file_id, caption, reply_markup=None
):
    """Send a manual-deposit screenshot to the configured review target."""
    if not deposit_notifications_enabled():
        return False

    target = get_setting("deposit_notify_chat_id").strip()
    try:
        await context.bot.send_photo(
            chat_id=target,
            photo=screenshot_file_id,
            caption=pe(caption),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return True
    except Exception as error:
        logging.error("Deposit screenshot notification target failed: %s", error)
        return False


def check_binance_payment(order_or_transaction_id, expected_usdt):
    """Verify the submitted Binance Pay ID and amount against Binance history."""
    if (
        not BINANCE_API_KEY
        or not BINANCE_SECRET_KEY
        or BINANCE_API_KEY.startswith("PASTE_")
        or BINANCE_SECRET_KEY.startswith("PASTE_")
    ):
        return False, 0.0, "Binance API credentials এখনো environment-এ সেট করা হয়নি।"

    target_id = str(order_or_transaction_id or "").strip()
    try:
        expected_usdt = float(expected_usdt)
    except (TypeError, ValueError):
        return False, 0.0, "Deposit amount সঠিক নয়।"
    if not target_id or not math.isfinite(expected_usdt) or expected_usdt <= 0:
        return False, 0.0, "Transaction ID বা amount সঠিক নয়।"

    endpoint = "https://api.binance.com/sapi/v1/pay/transactions"
    query = urlencode({
        "timestamp": int(time.time() * 1000),
        "recvWindow": 5000,
    })
    signature = hmac.new(
        BINANCE_SECRET_KEY.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    try:
        response = requests.get(
            f"{endpoint}?{query}&signature={signature}",
            headers={"X-MBX-APIKEY": BINANCE_API_KEY},
            timeout=15,
        )
        if response.status_code != 200:
            logging.error(
                "Binance Pay verification API returned HTTP %s",
                response.status_code,
            )
            return False, 0.0, "Binance API permission বা server error হয়েছে।"
        payload = response.json()
        transactions = (
            payload.get("data", []) if isinstance(payload, dict) else payload
        )
        if isinstance(transactions, dict):
            transactions = transactions.get("data", [])
        if not isinstance(transactions, list):
            return False, 0.0, "Binance response format সঠিক নয়।"

        for item in transactions:
            if not isinstance(item, dict):
                continue
            candidate_ids = {
                str(item.get(key, "") or "").strip()
                for key in ("orderId", "transactionId", "order_id", "transaction_id")
            }
            if target_id not in candidate_ids:
                continue
            currency = str(item.get("currency", "USDT") or "").upper()
            try:
                paid_amount = float(item.get("amount", 0))
            except (TypeError, ValueError):
                paid_amount = 0.0
            if (
                currency != "USDT"
                or not math.isfinite(paid_amount)
                or paid_amount <= 0
            ):
                return False, 0.0, "এই ID-তে valid USDT payment পাওয়া যায়নি।"
            status = str(item.get("status", "") or "").upper()
            if status and status not in {
                "SUCCESS", "COMPLETED", "PAID", "1", "FINISHED"
            }:
                return False, 0.0, "Binance payment এখনো successful নয়।"
            if abs(paid_amount - expected_usdt) > 0.01:
                return (
                    False,
                    paid_amount,
                    f"Amount mismatch: আপনার দেয়া {expected_usdt:g} USDT, "
                    f"Binance-এ {paid_amount:g} USDT।",
                )
            return True, paid_amount, f"{paid_amount:g} USDT verified"
        return False, 0.0, "এই ID Binance Pay history-তে পাওয়া যায়নি।"
    except (requests.RequestException, ValueError) as error:
        logging.error("Binance Pay verification request failed: %s", error)
        return False, 0.0, "Binance verification সাময়িকভাবে ব্যর্থ হয়েছে।"
    except Exception as error:
        logging.exception("Binance Pay verification failed: %s", error)
        return False, 0.0, "Binance verification error হয়েছে।"


def credit_binance_deposit(user_id, amount_usdt, trx_id, rate):
    """Credit one verified Binance payment exactly once, in a single DB txn."""
    try:
        amount_usdt = float(amount_usdt)
        rate = float(rate)
    except (TypeError, ValueError):
        return False, 0.0, None, 0.0
    if (
        not math.isfinite(amount_usdt) or amount_usdt <= 0
        or not math.isfinite(rate) or rate <= 0
    ):
        return False, 0.0, None, 0.0
    trx_id = str(trx_id or "").strip()
    if not trx_id:
        return False, 0.0, None, 0.0
    bdt_amount = round(amount_usdt * rate, 2)

    with _deposit_lock:
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            duplicate = conn.execute(
                "SELECT 1 FROM deposits "
                "WHERE lower(trim(trx_id)) = lower(trim(?)) LIMIT 1",
                (trx_id,),
            ).fetchone()
            user_row = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if duplicate or not user_row:
                conn.rollback()
                return False, 0.0, None, 0.0

            conn.execute(
                "INSERT INTO deposits "
                "(user_id, amount, method, trx_id, status, approved_by, approved_at) "
                "VALUES (?, ?, 'Binance', ?, 'approved', ?, ?)",
                (user_id, amount_usdt, trx_id, SUPER_ADMIN_ID, datetime.now()),
            )
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (bdt_amount, user_id),
            )
            conn.commit()
            return True, bdt_amount, None, 0.0
        except sqlite3.IntegrityError:
            conn.rollback()
            logging.warning("Duplicate Binance transaction credit blocked.")
            return False, 0.0, None, 0.0
        except Exception:
            conn.rollback()
            logging.exception("Could not credit verified Binance deposit.")
            return False, 0.0, None, 0.0
        finally:
            conn.close()


BOT_BACKUP_TABLES = (
    "users", "admins", "settings", "channels", "categories",
    "payment_methods", "products", "purchases", "deposits", "withdrawals",
)
BOT_BACKUP_HEADERS = ("table", "record_key", "record_json")


def _get_backup_rows():
    """Serialize every durable bot table as unique keyed backup rows."""
    conn = get_db()
    values = [list(BOT_BACKUP_HEADERS)]
    try:
        conn.execute("BEGIN")
        for table_name in BOT_BACKUP_TABLES:
            columns = list(conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall())
            if not columns:
                raise RuntimeError(f"Database table is missing: {table_name}")
            primary_keys = [
                row["name"] for row in sorted(
                    (column for column in columns if column["pk"]),
                    key=lambda column: column["pk"],
                )
            ]
            cursor = conn.execute(f'SELECT * FROM "{table_name}"')
            column_names = [item[0] for item in cursor.description]
            for row in cursor.fetchall():
                record = {name: row[name] for name in column_names}
                if primary_keys:
                    key_values = [record[name] for name in primary_keys]
                else:
                    key_values = [hashlib.sha256(
                        json.dumps(
                            record, ensure_ascii=False, sort_keys=True,
                            default=str,
                        ).encode("utf-8")
                    ).hexdigest()]
                record_key = json.dumps(
                    key_values, ensure_ascii=False, separators=(",", ":"),
                    default=str,
                )
                record_json = json.dumps(
                    record, ensure_ascii=False, sort_keys=True, default=str,
                )
                values.append([table_name, record_key, record_json])
    finally:
        conn.close()
    values[1:] = sorted(values[1:], key=lambda row: (row[0], row[1]))
    return values


def build_full_backup():
    """Build a complete local database backup file."""
    rows = _get_backup_rows()
    tables = {table_name: [] for table_name in BOT_BACKUP_TABLES}
    for table_name, _record_key, record_json in rows[1:]:
        tables[table_name].append(json.loads(record_json))
    return {
        "backup_format": "gx-shop-full-state",
        "backup_version": 1,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "tables": tables,
    }


def reset_all_bot_data():
    """Clear all business/admin records while keeping the owner able to recover."""
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        for table_name in BOT_BACKUP_TABLES:
            conn.execute(f'DELETE FROM "{table_name}"')
        conn.execute(
            "DELETE FROM sqlite_sequence "
            "WHERE name IN ('products', 'purchases', 'deposits', 'withdrawals')"
        )
        conn.execute(
            "INSERT INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,)
        )
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [
                ("referral_bonus", "0"),
                ("support_link", "https://t.me/your_support_username"),
                ("force_join_status", "ON"),
                ("log_group_id", ""),
                ("deposit_notify_enabled", "OFF"),
                ("deposit_notify_chat_id", ""),
                ("deposit_notify_type", ""),
                ("min_withdraw", "10"),
                ("withdraw_notify_enabled", "OFF"),
                ("withdraw_notify_chat_id", ""),
                ("usdt_rate", "120"),
            ],
        )
        conn.executemany(
            "INSERT INTO payment_methods "
            "(name, number_or_address, min_deposit, icon_key) "
            "VALUES (?, ?, ?, ?)",
            [
                ("bKash", "01700000000", 10.0, "bkash"),
                ("Nagad", "01700000000", 10.0, "nagad"),
                ("Rocket", "01700000000", 10.0, "rocket"),
                ("Upay", "01700000000", 10.0, "upay"),
                ("Binance", "1261150963", 0.1, "binance"),
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    with _force_join_cache_lock:
        _force_join_cache.clear()


async def safe_delete_msg(context, chat_id, message_id):
    try:
        if message_id:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def parse_force_join_channel_input(raw_value):
    """Accept public usernames, IDs, or a private chat ID paired with its invite."""
    text = str(raw_value or "").strip()
    if not text:
        return None, None, "Channel info খালি রাখা যাবে না।"

    target, separator, invite = text.partition("|")
    target = target.strip()
    invite = invite.strip() if separator else ""
    if invite and not re.match(r"^https?://t\.me/(?:\+|joinchat/)", invite, re.I):
        return None, None, "Private invite linkটি https://t.me/+... format-এ দিন।"

    if re.fullmatch(r"-100\d{5,}", target):
        if not invite:
            return None, None, (
                "Private channel-এর invite link-সহ Chat ID দিন: "
                "-1001234567890 | https://t.me/+invite"
            )
        return target, invite, None

    if target.startswith(("https://t.me/", "http://t.me/")):
        parsed = urlparse(target)
        path = parsed.path.strip("/")
        if path.startswith("+") or path.startswith("joinchat/"):
            return None, None, (
                "Private invite link দিয়ে membership verify করা যায় না। "
                "Chat ID | invite link দিন, যেমন -1001234567890 | https://t.me/+..."
            )
        target = path.split("/", 1)[0]
    target = target.lstrip("@")
    if invite:
        return None, None, (
            "আলাদা invite link শুধু private channel-এর Chat ID-এর সঙ্গে দিন।"
        )
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", target):
        return f"@{target}", invite or f"https://t.me/{target}", None
    return None, None, (
        "Public channel-এর @username দিন, অথবা private channel-এর "
        "-100 Chat ID | invite link দিন।"
    )


def force_join_button_url(channel_ref):
    """Return a working public/invite link for the force-join prompt."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT join_url FROM channels WHERE username = ?",
            (str(channel_ref),),
        ).fetchone()
        if row and row["join_url"]:
            return row["join_url"]
    finally:
        conn.close()

    value = str(channel_ref or "").strip()
    if value.startswith(("https://t.me/", "http://t.me/")):
        _, join_url, error = parse_force_join_channel_input(value)
        if not error:
            return join_url
    if value.startswith("@"):
        return f"https://t.me/{value[1:]}"
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
        return f"https://t.me/{value}"
    return None


async def check_force_join(user_id, context: ContextTypes.DEFAULT_TYPE):
    if get_setting('force_join_status') != 'ON':
        return True, []

    # Membership checks are Telegram API calls. Cache only a successful check
    # briefly so every reply-keyboard click does not wait on the network.
    with _force_join_cache_lock:
        cached_at = _force_join_cache.get(user_id)
    if cached_at and time.monotonic() - cached_at < 5:
        return True, []
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM channels")
    channels = [row['username'] for row in cursor.fetchall()]
    conn.close()

    not_joined = []
    for ch in channels:
        if str(ch).startswith(("@", "http://", "https://")) or re.fullmatch(
            r"-100\d{5,}", str(ch)
        ):
            parsed_target, _, parse_error = parse_force_join_channel_input(ch)
            ch_clean = parsed_target if not parse_error else str(ch)
        else:
            parsed_target, _, parse_error = parse_force_join_channel_input(ch)
            ch_clean = parsed_target if not parse_error else f"@{ch}"
        try:
            chat_id = int(ch_clean) if re.fullmatch(r"-100\d{5,}", ch_clean) else ch_clean
            member = await context.bot.get_chat_member(
                chat_id=chat_id, user_id=user_id
            )
            if member.status in ['left', 'kicked'] or (
                member.status == "restricted"
                and not getattr(member, "is_member", False)
            ):
                not_joined.append(ch_clean)
        except Exception:
            not_joined.append(ch_clean)
            
    if not not_joined:
        with _force_join_cache_lock:
            _force_join_cache[user_id] = time.monotonic()
    return (len(not_joined) == 0), not_joined

# ==================== Keyboards & UI Renderers ====================
def get_main_keyboard(user_id):
    keyboard = [
        [rkbtn("Buy Products", icon="buy", style="primary")],
        [
            rkbtn("My Profile", icon="profile"),
            rkbtn("Deposit", icon="deposit", style="success"),
        ],
        [
            rkbtn("Withdraw", icon="money", style="success"),
            rkbtn("Referral", icon="gift"),
        ],
    ]
    if is_admin(user_id):
        keyboard.append([rkbtn("Admin Panel", icon="gear", style="danger")])
    else:
        keyboard.append([rkbtn("Support", icon="support", style="primary")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def build_quantity_keyboard(quantity):
    return InlineKeyboardMarkup([
        [
            pbtn("➖", icon="warn", style="danger", callback_data="qty_minus"),
            pbtn(f"{quantity}", icon="number", style="primary", callback_data="qty_noop"),
            pbtn("➕", icon="fire", style="success", callback_data="qty_plus")
        ],
        [pbtn("Custom Quantity", icon="note", style="primary", callback_data="qty_custom")],
        [
            pbtn("কনফার্ম", icon="done", style="success", callback_data="qty_confirm"),
            pbtn("Cancel", icon="close", style="danger", callback_data="qty_cancel")
        ]
    ])

async def send_admin_panel(update: Update):
    usdt_rate = get_setting('usdt_rate') or "120"
    log_group = get_setting('log_group_id') or "Not Set"
    total_users = get_total_users_count()
    
    keyboard = [
        [pbtn("User Mgmt", icon="user", callback_data='admin_user_mgmt')],
        [
            pbtn("Group Log", icon="link", callback_data='admin_group_log'),
            pbtn("Deposit Alerts", icon="megaphone", callback_data="admin_deposit_notify")
        ],
        [
            pbtn("Min Withdraw", icon="money", callback_data="admin_withdraw_min"),
            pbtn("Withdraw Group", icon="group", callback_data="admin_withdraw_notify")
        ],
        [pbtn("Pending Withdrawals", icon="money", callback_data="admin_withdrawals")],
        [pbtn("Broadcast", icon="megaphone", callback_data='admin_broadcast')],
        [
            pbtn("Leaderboard", icon="king", callback_data='view_leaderboard'),
            pbtn("Admins", icon="shield", callback_data='admin_mgmt')
        ],
        [
            pbtn("Force Join", icon="group", callback_data='admin_fj_sys'),
            pbtn("Categories", icon="folder", callback_data='admin_cat_mgmt')
        ],
        [pbtn("Add Product", icon="new", style="success", callback_data='admin_add_prod')],
        [
            pbtn("GX Control", icon="gear", style="danger", callback_data='admin_gx_control')
        ],
        [
            pbtn("Backup File", icon="folder", style="success", callback_data="admin_backup_file"),
            pbtn("Delete All Data", icon="delete", style="danger", callback_data="admin_delete_all")
        ],
        [pbtn("Close", icon="close", style="danger", callback_data='close_msg')],
    ]
    
    text = (
        f"⚙️ <b>SYSTEM SETTINGS</b>\n"
        f"Manage advanced bot configurations below:\n\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"💲 <b>USDT Rate:</b> <code>1$ = {usdt_rate} BDT</code>\n"
        f"📢 <b>Activity Log ID:</b> <code>{log_group}</code>\n"
        f"💠 <b>Deposit Alerts:</b> "
        f"<code>{get_setting('deposit_notify_chat_id') if deposit_notifications_enabled() else 'OFF'}</code>"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def render_categories_menu(update_or_query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    cats = cursor.fetchall()
    conn.close()

    if not cats:
        text = "❌ <b>কোনো ক্যাটাগরি যোগ করা নেই!</b>"
        keyboard = InlineKeyboardMarkup([[pbtn("Close", icon="close", style="danger", callback_data="close_msg")]])
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(pe(text), reply_markup=keyboard, parse_mode="HTML")
        elif hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text(pe(text), reply_markup=keyboard, parse_mode="HTML")
        else:
            await update_or_query.reply_text(pe(text), reply_markup=keyboard, parse_mode="HTML")
        return

    keyboard = []
    row = []
    for c in cats:
        cat_name = c['name']
        cat_icon = get_product_icon_key(cat_name)
        row.append(pbtn(cat_name, icon=cat_icon, callback_data=f"buycat_{cat_name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([pbtn("Close", icon="close", style="danger", callback_data="close_msg")])

    text = "🎯 <b>ক্যাটাগরি সিলেক্ট করুন:</b>"
    
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update_or_query.reply_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ==================== Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    set_current_user(user)
    context.user_data.clear()

    if is_user_banned(user.id):
        await update.message.reply_text(pe("🚫 <b>আপনি এই বট থেকে ব্যান হয়ে গেছেন!</b>"), parse_mode="HTML")
        return

    ref_id = 0
    if context.args:
        try:
            possible_id = int(context.args[0])
            if possible_id != user.id:
                ref_id = possible_id
        except ValueError:
            pass
    context.user_data["pending_ref_id"] = ref_id

    is_joined, missing_channels = (
        (True, []) if is_admin(user.id)
        else await check_force_join(user.id, context)
    )
    if not is_joined:
        buttons = []
        for ch in missing_channels:
            join_url = force_join_button_url(ch)
            if join_url:
                buttons.append([
                    pbtn("JOIN CHANNEL", icon="link", style="primary", url=join_url)
                ])
        buttons.append([pbtn("Verify / Check Again", icon="refresh", style="success", callback_data="check_join")])
        
        await update.message.reply_text(
            pe("⚠️ <b>বট ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন:</b>"),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML"
        )
        return

    get_or_create_user(
        user.id,
        user.first_name,
        context.user_data.pop("pending_ref_id", ref_id),
        getattr(user, "username", "") or "",
    )
    welcome_msg = f"👋 <b>Mail & ProxySell Bot</b> এ আপনাকে স্বাগতম, {user.first_name}!\n\nনিচের মেনু থেকে আপনার সেবাটি বাছুন:"
    await update.message.reply_text(pe(welcome_msg), reply_markup=get_main_keyboard(user.id), parse_mode="HTML")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    action_text = normalize_button_text(text)
    user = update.effective_user
    set_current_user(user)
    state = context.user_data.get('state')

    if is_user_banned(user.id):
        await update.message.reply_text(pe("🚫 <b>আপনি এই বট থেকে ব্যান হয়ে গেছেন!</b>"), parse_mode="HTML")
        return

    if not is_admin(user.id):
        is_joined, _ = await check_force_join(user.id, context)
        if not is_joined:
            await start(update, context)
            return

    db_user = get_or_create_user(
        user.id, user.first_name, username=getattr(user, "username", "") or ""
    )

    # Balance Control States (Admin)
    if is_admin(user.id) and state in ['admin_add_balance', 'admin_cut_balance']:
        try:
            user_id_str, amount_str = text.strip().split()
            target_user_id = int(user_id_str)
            amount = float(amount_str)
        except ValueError:
            await update.message.reply_text(
                pe("❌ ভুল ফরম্যাট! দয়া করে সঠিক ফরম্যাটে লিখুন: `User_ID Amount` (যেমন: `123456789 100`)"), 
                parse_mode="HTML"
            )
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_user_id,))
        target_user = cursor.fetchone()

        if not target_user:
            await update.message.reply_text(pe("❌ এই ইউজার আইডিটি ডাটাবেজে পাওয়া যায়নি!"), parse_mode="HTML")
            conn.close()
            return

        if state == 'admin_add_balance':
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user_id))
            conn.commit()
            msg = f"✅ সফলভাবে ইউজার `<code>{target_user_id}</code>` এর অ্যাকাউন্টে **{amount} BDT** যোগ করা হয়েছে।"
            try:
                await context.bot.send_message(chat_id=target_user_id, text=pe(f"🎉 আপনার অ্যাকাউন্টে অ্যাডমিন দ্বারা **{amount} BDT** যোগ করা হয়েছে!"), parse_mode="HTML")
            except Exception:
                pass
        elif state == 'admin_cut_balance':
            if target_user['balance'] < amount:
                await update.message.reply_text(pe("❌ ওই ইউজারের অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই!"), parse_mode="HTML")
                conn.close()
                return
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, target_user_id))
            conn.commit()
            msg = f"✅ সফলভাবে ইউজার `<code>{target_user_id}</code>` এর অ্যাকাউন্ট থেকে **{amount} BDT** কেটে নেওয়া হয়েছে।"
            try:
                await context.bot.send_message(chat_id=target_user_id, text=pe(f"⚠️ আপনার অ্যাকাউন্ট থেকে অ্যাডমিন দ্বারা **{amount} BDT** কেটে নেওয়া হয়েছে!"), parse_mode="HTML")
            except Exception:
                pass

        conn.close()
        context.user_data.pop('state', None)
        await update.message.reply_text(pe(msg), reply_markup=InlineKeyboardMarkup([[pbtn("Back to GX Control", icon="back", callback_data="admin_gx_control")]]), parse_mode="HTML")
        return

    # Deposit Amount State
    if (
        state == 'awaiting_deposit_amount'
        and action_text in {
            "Buy Products", "My Profile", "Deposit", "Withdraw", "Referral", "Support",
            "Admin Panel",
        }
    ):
        await safe_delete_msg(
            context, user.id, context.user_data.pop("last_msg_id", None)
        )
        for key in ("state", "dep_method", "dep_amount", "dep_usdt", "last_msg_id"):
            context.user_data.pop(key, None)
        state = None

    if state == 'awaiting_deposit_amount':
        await safe_delete_msg(context, user.id, update.message.message_id)
        last_bot_msg_id = context.user_data.get('last_msg_id')
        await safe_delete_msg(context, user.id, last_bot_msg_id)

        try:
            val_input = float(text.strip())
            if not math.isfinite(val_input) or val_input <= 0:
                raise ValueError
            method_name = context.user_data.get('dep_method')

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT number_or_address, min_deposit FROM payment_methods WHERE name = ?", (method_name,))
            m_data = cursor.fetchone()
            conn.close()

            min_limit = m_data['min_deposit'] if m_data else 10.0
            num = m_data['number_or_address'] if m_data else "Not Set"

            if val_input < min_limit:
                unit = "USDT" if method_name.lower() == 'binance' else "BDT"
                m = await context.bot.send_message(chat_id=user.id, text=pe(f"❌ {method_name} এ সর্বনিম্ন ডিপোজিট {min_limit} {unit}!"), parse_mode="HTML")
                context.user_data['last_msg_id'] = m.message_id
                return
            
            if method_name.lower() == 'binance':
                try:
                    usdt_rate = float(get_setting('usdt_rate'))
                except ValueError:
                    usdt_rate = 120.0
                
                calculated_bdt = val_input * usdt_rate
                context.user_data['dep_amount'] = calculated_bdt
                context.user_data['dep_usdt'] = val_input
                context.user_data['state'] = 'awaiting_trxid'
                
                msg = (
                    f"💠 <b>{method_name} Pay Instructions:</b>\n\n"
                    f"📱 Pay ID: <code>{num}</code>\n"
                    f"💲 Amount: <b>{val_input} USDT</b>\n"
                    f"💠 Balance Added: <b>{calculated_bdt:.2f} BDT</b> (Rate: 1$ = {usdt_rate:.2f} BDT)\n\n"
                    f"👉 ওপরের আইডিতে <b>{val_input} USDT</b> পাঠানোর পর <b>🧾 Transaction ID (TrxID)</b> টাইপ করে পাঠান:"
                )
            else:
                context.user_data['dep_amount'] = val_input
                context.user_data['dep_usdt'] = 0
                context.user_data['state'] = 'awaiting_trxid'
                
                msg = (
                    f"💠 <b>{method_name} Cash Out / Send Money Instructions:</b>\n\n"
                    f"📱 Number / ID: <code>{num}</code>\n"
                    f"💰 Amount: <b>{val_input:.2f} BDT</b>\n\n"
                    f"👉 ওপরের নম্বরে/আইডিতে টাকা পাঠানোর পর <b>🧾 Transaction ID (TrxID)</b> টাইপ করে পাঠান:"
                )

            m = await context.bot.send_message(chat_id=user.id, text=pe(msg), parse_mode="HTML")
            context.user_data['last_msg_id'] = m.message_id
            return
        except ValueError:
            m = await context.bot.send_message(
                chat_id=user.id,
                text=pe("❌ পরিমাণ অবশ্যই 0-এর বেশি সংখ্যা হতে হবে!"),
                parse_mode="HTML",
            )
            context.user_data['last_msg_id'] = m.message_id
            return

    if (
        state in {"awaiting_withdraw_amount", "awaiting_withdraw_details"}
        and action_text in {
            "Buy Products", "My Profile", "Deposit", "Withdraw", "Referral",
            "Support", "Admin Panel",
        }
    ):
        for key in (
            "state", "withdraw_amount", "withdrawal_id", "last_msg_id"
        ):
            context.user_data.pop(key, None)
        state = None

    if state == "awaiting_withdraw_amount":
        try:
            amount = float(text.strip())
        except ValueError:
            await update.message.reply_text(
                pe("❌ Withdraw amount সংখ্যায় দিন।"),
                parse_mode="HTML",
            )
            return
        amount = round(amount, 2)
        if not math.isfinite(amount) or amount <= 0:
            await update.message.reply_text(
                pe("❌ Withdraw amount 0-এর বেশি হতে হবে।"),
                parse_mode="HTML",
            )
            return
        min_withdraw = get_min_withdraw_amount()
        if amount < min_withdraw:
            await update.message.reply_text(
                pe(
                    f"❌ সর্বনিম্ন withdraw amount {min_withdraw:.2f} BDT।"
                ),
                parse_mode="HTML",
            )
            return
        if amount > db_user["balance"]:
            await update.message.reply_text(
                pe(
                    f"❌ ব্যালেন্স পর্যাপ্ত নয়। আপনার ব্যালেন্স "
                    f"{db_user['balance']:.2f} BDT।"
                ),
                parse_mode="HTML",
            )
            return
        context.user_data["withdraw_amount"] = amount
        context.user_data["state"] = "awaiting_withdraw_details"
        await update.message.reply_text(
            pe(
                "📲 টাকা পাওয়ার মাধ্যম ও account/number দিন "
                "(যেমন: bKash 01XXXXXXXXX)।"
            ),
            parse_mode="HTML",
        )
        return

    if state == "awaiting_withdraw_details":
        payout_details = text.strip()
        if len(payout_details) < 3 or len(payout_details) > 300:
            await update.message.reply_text(
                pe("❌ Payment details 3–300 অক্ষরের মধ্যে দিন।"),
                parse_mode="HTML",
            )
            return
        amount = float(context.user_data.get("withdraw_amount", 0) or 0)
        result = create_withdrawal_request(user.id, amount, payout_details)
        if result["status"] == "pending_exists":
            context.user_data.clear()
            await update.message.reply_text(
                pe("⏳ আপনার একটি withdraw request আগে থেকেই pending আছে।"),
                parse_mode="HTML",
            )
            return
        if result["status"] == "insufficient_balance":
            context.user_data.clear()
            current_user = get_or_create_user(
                user.id, user.first_name,
                username=getattr(user, "username", "") or "",
            )
            await update.message.reply_text(
                pe(
                    f"❌ ব্যালেন্স পর্যাপ্ত নয়। বর্তমান ব্যালেন্স "
                    f"{current_user['balance']:.2f} BDT।"
                ),
                parse_mode="HTML",
            )
            return
        if result["status"] != "ok":
            context.user_data.clear()
            await update.message.reply_text(
                pe("❌ Withdraw request জমা হয়নি। কিছুক্ষণ পর আবার চেষ্টা করুন।"),
                parse_mode="HTML",
            )
            return

        withdrawal_id = result["withdrawal_id"]
        context.user_data.clear()
        await update.message.reply_text(
            pe(
                f"✅ <b>Withdraw request জমা হয়েছে।</b>\n"
                f"Amount: <b>{amount:.2f} BDT</b>\n"
                "Admin review না করা পর্যন্ত এই টাকা balance থেকে reserve থাকবে।"
            ),
            parse_mode="HTML",
        )
        admin_keyboard = InlineKeyboardMarkup([
            [pbtn(
                "Approve",
                icon="done",
                style="success",
                callback_data=f"withdraw_approve_{withdrawal_id}",
            )],
            [pbtn(
                "Reject & Refund",
                icon="close",
                style="danger",
                callback_data=f"withdraw_reject_{withdrawal_id}",
            )],
        ])
        safe_name = html_lib.escape(str(user.first_name or "User"))
        safe_details = html_lib.escape(payout_details)
        admin_message = (
            "💸 <b>নতুন withdraw request</b>\n\n"
            f"👤 User: {safe_name} (<code>{user.id}</code>)\n"
            f"💰 Amount: <b>{amount:.2f} BDT</b>\n"
            f"📲 Payout details: <code>{safe_details}</code>\n"
            f"🧾 Request: <code>#{withdrawal_id}</code>"
        )
        notification_sent = await send_withdrawal_notification(
            context,
            admin_message,
            reply_markup=admin_keyboard,
        )
        if not notification_sent:
            for admin_id in get_all_admin_ids():
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message,
                        reply_markup=admin_keyboard,
                        parse_mode="HTML",
                    )
                except Exception as error:
                    logging.error("Could not notify admin about withdrawal: %s", error)
        return

    # Add Payment Method States (Admin)
    if is_admin(user.id):
        if state == "awaiting_min_withdraw":
            try:
                min_amount = float(text.strip())
                if not math.isfinite(min_amount) or min_amount <= 0:
                    raise ValueError
                set_setting("min_withdraw", str(min_amount))
                context.user_data.clear()
                await update.message.reply_text(
                    pe(
                        f"✅ Minimum withdrawal <b>{min_amount:.2f} BDT</b> "
                        "সেভ করা হয়েছে।"
                    ),
                    parse_mode="HTML",
                )
            except ValueError:
                await update.message.reply_text(
                    pe("❌ Minimum withdrawal অবশ্যই 0-এর বেশি সংখ্যা হতে হবে।"),
                    parse_mode="HTML",
                )
            return

        if state == 'awaiting_usdt_rate':
            try:
                rate_val = float(text.strip())
                set_setting('usdt_rate', str(rate_val))
                context.user_data.clear()
                await update.message.reply_text(pe(f"✅ Binance USDT Rate <b>1$ = {rate_val:.2f} BDT</b> সেভ করা হয়েছে!"), parse_mode="HTML")
            except ValueError:
                await update.message.reply_text(pe("❌ ডলারের রেট অবশ্যই সংখ্যায় টাইপ করুন!"), parse_mode="HTML")
            return

        if state == 'add_pay_step1_name':
            context.user_data['new_pay_name'] = text.strip()
            context.user_data['state'] = 'add_pay_step2_num'
            await update.message.reply_text(pe(f"📱 <b>{text.strip()}</b> এর একাউন্ট নম্বর / Binance Pay ID দিন:"), parse_mode="HTML")
            return

        elif state == 'add_pay_step2_num':
            context.user_data['new_pay_num'] = text.strip()
            context.user_data['state'] = 'add_pay_step3_min'
            p_name = context.user_data.get('new_pay_name', '')
            unit_txt = "USDT (যেমন: 0.1)" if 'binance' in p_name.lower() else "টাকা (যেমন: 10)"
            await update.message.reply_text(pe(f"💠 এই মেথডের জন্য <b>Minimum Deposit Limit</b> কত দিতে চান? ({unit_txt}):"), parse_mode="HTML")
            return

        elif state == 'add_pay_step3_min':
            try:
                min_dep = float(text.strip())
                if not math.isfinite(min_dep) or min_dep <= 0:
                    raise ValueError
                name = context.user_data.get('new_pay_name')
                num = context.user_data.get('new_pay_num')

                name_lower = name.lower()
                icon_key = 'card'
                if 'bkash' in name_lower: icon_key = 'bkash'
                elif 'nagad' in name_lower: icon_key = 'nagad'
                elif 'rocket' in name_lower: icon_key = 'rocket'
                elif 'upay' in name_lower: icon_key = 'upay'
                elif 'binance' in name_lower: icon_key = 'binance'

                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO payment_methods (name, number_or_address, min_deposit, icon_key) VALUES (?, ?, ?, ?)",
                    (name, num, min_dep, icon_key)
                )
                conn.commit()
                conn.close()

                unit_txt = "USDT" if 'binance' in name_lower else "BDT"
                context.user_data.clear()
                await update.message.reply_text(
                    pe(f"✅ <b>পেমেন্ট মেথড সফলভাবে যোগ/আপডেট হয়েছে!</b>\n\n"
                       f"💳 <b>Name:</b> {name}\n"
                       f"📱 <b>Number/ID:</b> <code>{num}</code>\n"
                       f"💠 <b>Min Deposit:</b> {min_dep} {unit_txt}"),
                    parse_mode="HTML"
                )
                return
            except ValueError:
                await update.message.reply_text(
                    pe("❌ Minimum Deposit অবশ্যই 0-এর বেশি সংখ্যা হতে হবে!"),
                    parse_mode="HTML",
                )
                return

    # Broadcast State (Admin)
    if is_admin(user.id) and state == 'awaiting_broadcast_msg':
        context.user_data.clear()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
        all_users = cursor.fetchall()
        conn.close()

        await update.message.reply_text(pe("⏳ <b>ব্রডকাস্ট পাঠানো শুরু হয়েছে...</b>"), parse_mode="HTML")
        
        success = 0
        failed = 0
        
        for u in all_users:
            try:
                await context.bot.copy_message(
                    chat_id=u['user_id'],
                    from_chat_id=user.id,
                    message_id=update.message.message_id
                )
                success += 1
            except Exception:
                failed += 1

        await update.message.reply_text(
            pe(f"✅ <b>Broadcast Complete!</b>\n\n"
            f"🟢 <b>সফল:</b> {success} জন\n"
            f"🔴 <b>ব্যর্থ (Blocked):</b> {failed} জন"),
            parse_mode="HTML"
        )
        return

    # Custom Quantity State
    if state == 'awaiting_custom_qty':
        await safe_delete_msg(context, user.id, update.message.message_id)
        last_bot_msg_id = context.user_data.get('last_msg_id')
        await safe_delete_msg(context, user.id, last_bot_msg_id)

        try:
            qty = int(text)
            if qty <= 0:
                m = await context.bot.send_message(chat_id=user.id, text=pe("❌ সর্বনিম্ন পরিমাণ ১ হতে হবে!"), parse_mode="HTML")
                context.user_data['last_msg_id'] = m.message_id
                return
            
            p_id = context.user_data.get('buy_pid')
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT title, category, price FROM products WHERE id = ?", (p_id,))
            res = cursor.fetchone()

            if not res:
                m = await context.bot.send_message(chat_id=user.id, text=pe("❌ প্রোডাক্টটি পাওয়া যায়নি!"), parse_mode="HTML")
                conn.close()
                context.user_data['last_msg_id'] = m.message_id
                return

            title = res['title']
            cat_name = res['category']
            price = res['price']

            cursor.execute("SELECT COUNT(*) as stock FROM products WHERE title = ? AND category = ?", (title, cat_name))
            stock_res = cursor.fetchone()
            stock = stock_res['stock'] if stock_res else 0
            conn.close()

            if stock == 0:
                m = await context.bot.send_message(chat_id=user.id, text=pe("❌ এই প্রোডাক্টটি আউট অফ স্টক!"), parse_mode="HTML")
                context.user_data['last_msg_id'] = m.message_id
                return

            if qty > stock:
                m = await context.bot.send_message(chat_id=user.id, text=pe(f"❌ স্টকে এতগুলো নেই! সর্বোচ্চ আছে: {stock} টি।"), parse_mode="HTML")
                context.user_data['last_msg_id'] = m.message_id
                return

            context.user_data['buy_qty'] = qty
            total = price * qty

            msg = (
                f"🏷️ <b>{title}</b>\n"
                f"💎 প্রাইস: {price:.2f} BDT\n"
                f"📦 স্টক: {stock}\n\n"
                f"<b>পরিমাণ:</b> {qty}\n"
                f"<b>মোট:</b> 💎 {total:.2f} BDT"
            )
            context.user_data['state'] = None
            m = await context.bot.send_message(chat_id=user.id, text=pe(msg), reply_markup=build_quantity_keyboard(qty), parse_mode="HTML")
            context.user_data['last_msg_id'] = m.message_id
            return
        except ValueError:
            m = await context.bot.send_message(chat_id=user.id, text=pe("❌ পরিমাণ অবশ্যই সংখ্যায় টাইপ করুন!"), parse_mode="HTML")
            context.user_data['last_msg_id'] = m.message_id
            return

    # Admin States
    if is_admin(user.id):
        if state == 'awaiting_search_user_id':
            try:
                target_id = int(text.strip())
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_id,))
                u_info = cursor.fetchone()

                if not u_info:
                    await update.message.reply_text(pe("❌ এই আইডি-র কোনো ইউজার ডাটাবেজে পাওয়া যায়নি!"), parse_mode="HTML")
                    conn.close()
                    return

                cursor.execute("SELECT COUNT(*) as total_buy FROM purchases WHERE user_id = ?", (target_id,))
                total_buy = cursor.fetchone()['total_buy']
                conn.close()

                status_txt = "🔴 Banned" if u_info['is_banned'] == 1 else "🟢 Active"
                ban_btn_txt = "🟢 Unban User" if u_info['is_banned'] == 1 else "🔴 Ban User"

                ban_style = "success" if u_info['is_banned'] == 1 else "danger"
                ban_icon = "done" if u_info['is_banned'] == 1 else "stop"
                keyboard = [
                    [pbtn(ban_btn_txt.split(" ", 1)[1] if " " in ban_btn_txt else ban_btn_txt, icon=ban_icon, style=ban_style, callback_data=f"toggle_ban_{target_id}")],
                    [pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")]
                ]

                u_msg = (
                    f"👤 <b>USER DETAILS</b>\n\n"
                    f"🆔 <b>User ID:</b> <code>{u_info['user_id']}</code>\n"
                    f"👤 <b>Name:</b> {u_info['first_name']}\n"
                    f"💠 <b>Balance:</b> {u_info['balance']:.2f} BDT\n"
                    f"🛍️ <b>Total Orders:</b> {total_buy} Pcs\n"
                    f"📅 <b>Joined:</b> {u_info['joined_date']}\n"
                    f"⚡ <b>Status:</b> {status_txt}"
                )
                context.user_data.clear()
                await update.message.reply_text(pe(u_msg), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                return
            except ValueError:
                await update.message.reply_text(pe("❌ Telegram User ID অবশ্যই সংখ্যায় হতে হবে!"), parse_mode="HTML")
                return

        elif state == "awaiting_withdraw_notify_target":
            try:
                chat = await context.bot.get_chat(text.strip())
                if chat.type not in {"group", "supergroup"}:
                    raise ValueError("Targetটি Telegram group/supergroup নয়।")

                bot_user = await context.bot.get_me()
                bot_member = await context.bot.get_chat_member(chat.id, bot_user.id)
                if bot_member.status not in {"administrator", "creator"}:
                    raise ValueError("এই group-এ bot administrator নয়।")

                set_setting("withdraw_notify_chat_id", str(chat.id))
                set_setting("withdraw_notify_enabled", "ON")
                context.user_data.clear()
                await update.message.reply_text(
                    pe(
                        "✅ Withdrawal request group-এ চালু হয়েছে!\n"
                        f"Chat ID: <code>{chat.id}</code>\n"
                        "এখন pending withdraw request ও approve/reject buttons "
                        "এই group-এ যাবে।"
                    ),
                    parse_mode="HTML",
                )
            except Exception as error:
                logging.error("Withdrawal notification target validation failed: %s", error)
                await update.message.reply_text(
                    pe(
                        "❌ Group সেভ করা যায়নি। Bot-কে target group-এ "
                        "administrator করুন এবং group Chat ID পাঠান।"
                    ),
                    parse_mode="HTML",
                )
            return

        elif state == 'awaiting_deposit_notify_target':
            raw_target = text.strip()
            requested_type = context.user_data.get("deposit_notify_type", "group")
            try:
                chat = await context.bot.get_chat(raw_target)
                expected_types = {"group", "supergroup"} if requested_type == "group" else {"channel"}
                if chat.type not in expected_types:
                    expected_label = "group/supergroup" if requested_type == "group" else "channel"
                    raise ValueError(f"Targetটি Telegram {expected_label} নয়।")

                bot_user = await context.bot.get_me()
                bot_member = await context.bot.get_chat_member(chat.id, bot_user.id)
                if bot_member.status not in {"administrator", "creator"}:
                    raise ValueError("এই target-এ bot administrator নয়।")

                set_setting("deposit_notify_chat_id", str(chat.id))
                set_setting("deposit_notify_type", chat.type)
                set_setting("deposit_notify_enabled", "ON")
                context.user_data.clear()
                await update.message.reply_text(
                    pe(
                        f"✅ Deposit alerts <b>{chat.type}</b>-এ চালু হয়েছে!\n"
                        f"Chat ID: <code>{chat.id}</code>\n\n"
                        "এখন pending manual deposit request এবং approval notification "
                        "এখানেই যাবে।"
                    ),
                    parse_mode="HTML",
                )
            except Exception as error:
                logging.error("Deposit notification target validation failed: %s", error)
                await update.message.reply_text(
                    pe(
                        "❌ Target সেভ করা যায়নি। Bot-কে target group/channel-এ "
                        "administrator করুন এবং আবার সঠিক Chat ID বা @username পাঠান।"
                    ),
                    parse_mode="HTML",
                )
            return

        elif state == 'awaiting_group_id':
            grp_id = text.strip()
            set_setting('log_group_id', grp_id)
            context.user_data.clear()
            await update.message.reply_text(pe(f"✅ Log Group ID সফলভাবে সেভ হয়েছে: <code>{grp_id}</code>"), parse_mode="HTML")
            return

        elif state == 'add_prod_step1_name':
            context.user_data['add_title'] = text.strip()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories")
            cats = [r['name'] for r in cursor.fetchall()]
            conn.close()

            if not cats:
                await update.message.reply_text(pe("❌ আগে অ্যাডমিন প্যানেল থেকে একটি ক্যাটাগরি তৈরি করে নিন!"), parse_mode="HTML")
                context.user_data.clear()
                return

            keyboard = [[pbtn(c, icon=get_product_icon_key(c), style="danger", callback_data=f"seladdcat_{c}")] for c in cats]
            await update.message.reply_text(pe("🏷️ প্রোডাক্টের জন্য <b>Category</b> সিলেক্ট করুন:"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            return

        elif state == 'add_prod_step3_price':
            try:
                context.user_data['add_price'] = float(text.strip())
                context.user_data['state'] = 'add_prod_step4_stock'
                await update.message.reply_text(pe("📦 এবার <b>All Products / Stock Data</b> একসাথে পাঠিয়ে দিন:"), parse_mode="HTML")
            except ValueError:
                await update.message.reply_text(pe("❌ Price অবশ্যই সংখ্যায় দিন!"), parse_mode="HTML")
            return

        elif state == 'add_prod_step4_stock':
            title = context.user_data.get('add_title')
            category = context.user_data.get('add_category')
            price = context.user_data.get('add_price')

            raw_blocks = re.split(r'\n\s*\n|\n(?=\d+\.\s*Host:|\n?Host:)', text.strip())
            items_to_add = [b.strip() for b in raw_blocks if b.strip()]

            if not items_to_add:
                items_to_add = [line.strip() for line in text.strip().split('\n') if line.strip()]

            conn = get_db()
            cursor = conn.cursor()
            for item_data in items_to_add:
                cursor.execute(
                    "INSERT INTO products (category, title, price, item_data) VALUES (?, ?, ?, ?)",
                    (category, title, price, item_data)
                )
            conn.commit()

            # Product count check after insert
            cursor.execute("SELECT COUNT(*) as current_stock FROM products WHERE title = ? AND category = ?", (title, category))
            total_stock_now = cursor.fetchone()['current_stock']

            # Get all non-banned users for Auto Broadcast
            cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
            all_users = cursor.fetchall()
            conn.close()

            context.user_data.clear()
            
            # Admin confirmation message
            await update.message.reply_text(
                pe(f"🎉 <b>সফলভাবে {len(items_to_add)} টি স্টক যোগ হয়েছে!</b>\n\n"
                f"📦 <b>Name:</b> {title}\n"
                f"🏷️ <b>Category:</b> {category}\n"
                f"💰 <b>Price:</b> {price:.2f} BDT\n\n"
                f"📢 <i>মেম্বারদের কাছে অটো ব্রডকাস্ট পাঠানো হচ্ছে...</i>"),
                parse_mode="HTML"
            )

            # ==================== AUTO BROADCAST FEATURE ====================
            broadcast_text = (
                f"🔥 <b>NEW PRODUCT AVAILABLE!</b> 🔥\n\n"
                f"🏷️ <b>Product:</b> {title}\n"
                f"📁 <b>Category:</b> {category}\n"
                f"💰 <b>Price:</b> {price:.2f} BDT\n"
                f"📦 <b>Total Stock:</b> {total_stock_now} Pcs\n\n"
                f"👉 এখনই কিনতে বট থেকে <b>Buy Products</b> এ চাপ দিন!"
            )
            
            buy_keyboard = InlineKeyboardMarkup([
                [pbtn("Buy Now", icon="buy", style="danger", callback_data=f"buycat_{category}")]
            ])

            for u in all_users:
                try:
                    await context.bot.send_message(
                        chat_id=u['user_id'],
                        text=pe(broadcast_text),
                        reply_markup=buy_keyboard,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return

        elif state == 'awaiting_new_category':
            cat_name = text.strip().upper()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat_name,))
            conn.commit()
            conn.close()
            context.user_data.clear()
            await update.message.reply_text(pe(f"✅ নতুন ক্যাটাগরি <b>{cat_name}</b> যোগ হয়েছে!"), parse_mode="HTML")
            return

        elif state == 'awaiting_new_admin_id':
            try:
                new_id = int(text)
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
                conn.commit()
                conn.close()
                context.user_data.clear()
                await update.message.reply_text(pe(f"✅ User <code>{new_id}</code> নতুন অ্যাডমিন হিসেবে যুক্ত হয়েছে!"), parse_mode="HTML")
            except ValueError:
                await update.message.reply_text(pe("❌ আইডি অবশ্যই সংখ্যায় দিন!"), parse_mode="HTML")
            return

        elif state == 'awaiting_add_channel':
            ch_username, join_url, parse_error = parse_force_join_channel_input(text)
            if parse_error:
                await update.message.reply_text(
                    pe(
                        f"❌ {parse_error}\n\n"
                        "বটকে channel admin করতে হবে এবং private channel হলে "
                        "<code>-100 Chat ID | invite link</code> দিন।"
                    ),
                    parse_mode="HTML",
                )
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO channels (username, join_url) VALUES (?, ?) "
                "ON CONFLICT(username) DO UPDATE SET join_url = excluded.join_url",
                (ch_username, join_url or ""),
            )
            conn.commit()
            conn.close()
            with _force_join_cache_lock:
                _force_join_cache.clear()
            context.user_data.clear()
            await update.message.reply_text(pe(f"✅ চ্যানেল <code>{ch_username}</code> যুক্ত হয়েছে!"), parse_mode="HTML")
            return

        elif state == 'awaiting_support_link':
            set_setting('support_link', text.strip())
            context.user_data.clear()
            await update.message.reply_text(pe(f"✅ নতুন সাপোর্ট লিংক সেভ হয়েছে: {text.strip()}"), parse_mode="HTML")
            return

        elif state == 'awaiting_ref_bonus':
            try:
                bonus_val = float(text.strip())
                if not math.isfinite(bonus_val) or bonus_val < 0:
                    raise ValueError
                set_setting('referral_bonus', str(round(bonus_val, 2)))
                context.user_data.clear()
                await update.message.reply_text(
                    pe(
                        f"✅ Fixed referral bonus "
                        f"<b>{round(bonus_val, 2):.2f} BDT</b> সেভ হয়েছে।"
                    ),
                    parse_mode="HTML",
                )
            except ValueError:
                await update.message.reply_text(
                    pe("❌ Bonus 0 বা তার বেশি BDT হিসেবে দিন।"),
                    parse_mode="HTML",
                )
            return

    # Deposit TrxID Input State
    if state == 'awaiting_trxid':
        await safe_delete_msg(context, user.id, update.message.message_id)
        last_bot_msg_id = context.user_data.get('last_msg_id')
        await safe_delete_msg(context, user.id, last_bot_msg_id)

        method = context.user_data.get('dep_method', 'Payment')
        amount = float(context.user_data.get('dep_amount', 0))
        dep_usdt = float(context.user_data.get('dep_usdt', 0))
        trx_id = text.strip()

        # ==================== Duplicate TrxID Check ====================
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM deposits "
            "WHERE lower(trim(trx_id)) = lower(trim(?)) LIMIT 1",
            (trx_id,),
        )
        existing_trx = cursor.fetchone()

        if existing_trx:
            conn.close()
            m = await context.bot.send_message(
                chat_id=user.id, 
                text=pe("❌ <b>এই 🧾 Transaction ID (TrxID) টি আগেই ব্যবহার করা হয়েছে!</b>\nদয়া করে সঠিক এবং নতুন TrxID টাইপ করে পাঠান:"), 
                parse_mode="HTML"
            )
            context.user_data['last_msg_id'] = m.message_id
            return

        cursor.execute(
            "SELECT amount, method, trx_id FROM deposits "
            "WHERE user_id = ? AND status = 'pending' LIMIT 1",
            (user.id,),
        )
        if cursor.fetchone():
            conn.close()
            context.user_data.clear()
            await context.bot.send_message(
                chat_id=user.id,
                text=pe(
                    "⏳ আপনার একটি ডিপোজিট রিকোয়েস্ট আগেই pending আছে। "
                    "সেটি approve বা reject না হওয়া পর্যন্ত আরেকটি deposit করা যাবে না।"
                ),
                parse_mode="HTML",
            )
            return

        conn.close()
        if method.lower() == "binance":
            if not dep_usdt or dep_usdt <= 0:
                context.user_data.clear()
                await context.bot.send_message(
                    chat_id=user.id,
                    text=pe("❌ Binance USDT amount পাওয়া যায়নি। Deposit আবার শুরু করুন।"),
                    parse_mode="HTML",
                )
                return
            checking_message = await context.bot.send_message(
                chat_id=user.id,
                text=pe("⏳ Binance Pay transaction verify হচ্ছে..."),
                parse_mode="HTML",
            )
            is_valid, paid_usdt, result_text = await asyncio.to_thread(
                check_binance_payment, trx_id, dep_usdt
            )
            await safe_delete_msg(context, user.id, checking_message.message_id)
            if not is_valid:
                retry_message = await context.bot.send_message(
                    chat_id=user.id,
                    text=pe(
                        f"❌ <b>Payment verify হয়নি:</b> {result_text}\n\n"
                        "সঠিক Binance Order/Transaction ID আবার পাঠান:"
                    ),
                    parse_mode="HTML",
                )
                context.user_data["last_msg_id"] = retry_message.message_id
                return

            try:
                usdt_rate = float(get_setting("usdt_rate") or 120)
            except (TypeError, ValueError):
                usdt_rate = 120.0
            credited, credited_bdt, _, _ = await asyncio.to_thread(
                credit_binance_deposit,
                user.id,
                paid_usdt,
                trx_id,
                usdt_rate,
            )
            if not credited:
                context.user_data.clear()
                await context.bot.send_message(
                    chat_id=user.id,
                    text=pe(
                        "❌ এই transaction ID আগেই ব্যবহার হয়েছে অথবা deposit "
                        "credit করা যায়নি। Balance double-credit করা হয়নি।"
                    ),
                    parse_mode="HTML",
                )
                return

            context.user_data.clear()
            await context.bot.send_message(
                chat_id=user.id,
                text=pe(
                    "✅ <b>Binance Pay verified এবং deposit auto-approved!</b>\n\n"
                    f"💲 Payment: <b>{paid_usdt:.2f} USDT</b>\n"
                    f"💠 Balance added: <b>{credited_bdt:.2f} BDT</b>\n"
                    f"📊 Rate: 1 USDT = {usdt_rate:.2f} BDT"
                ),
                parse_mode="HTML",
            )
            notification = (
                "✅ <b>Binance Auto-Approved</b>\n"
                f"👤 User: <code>{user.id}</code> "
                f"(@{getattr(user, 'username', '') or 'no-username'})\n"
                f"💲 {paid_usdt:.2f} USDT → {credited_bdt:.2f} BDT\n"
                f"🧾 TrxID: <code>{trx_id}</code>"
            )
            if not await send_deposit_notification(context, notification):
                log_group = get_setting("log_group_id")
                if log_group:
                    try:
                        await context.bot.send_message(
                            chat_id=log_group,
                            text=pe(notification),
                            parse_mode="HTML",
                        )
                    except Exception:
                        logging.info("Binance deposit log message could not be sent.")
            return

        context.user_data['dep_trx_id'] = trx_id
        context.user_data['state'] = 'awaiting_deposit_screenshot'
        m = await context.bot.send_message(
            chat_id=user.id,
            text=pe(
                "📸 এখন একই payment-এর একটি পরিষ্কার screenshot পাঠান।\n\n"
                "Screenshot না পাঠালে admin-এর কাছে request যাবে না।"
            ),
            parse_mode="HTML",
        )
        context.user_data['last_msg_id'] = m.message_id
        return

    # Main Keyboard Actions
    if action_text == "Buy Products":
        await render_categories_menu(update)

    elif action_text == "My Profile":
        ref_income = db_user['ref_earnings'] if db_user['ref_earnings'] else 0.0
        
        profile_text = (
            f"👤 <b>আপনার প্রোফাইল:</b>\n\n"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"💠 <b>ব্যালেন্স:</b> {db_user['balance']:.2f} BDT\n"
            f"🎁 <b>রেফার থেকে আয়:</b> {ref_income:.2f} BDT"
        )
        keyboard = [
            [pbtn("হিস্ট্রি", icon="bag", callback_data='purchases')],
            [pbtn("Close", icon="close", style="danger", callback_data="close_msg")]
        ]
        await update.message.reply_text(pe(profile_text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif action_text == "Referral":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user.id}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as ref_count FROM users WHERE referred_by = ?", (user.id,))
        ref_count = cursor.fetchone()['ref_count']
        conn.close()

        ref_bonus = float(get_setting('referral_bonus') or 0)
        ref_income = db_user['ref_earnings'] if db_user['ref_earnings'] else 0.0

        ref_text = (
            f"👥 <b>রেফারেল প্রোগ্রাম</b>\n\n"
            f"🔗 <b>আপনার লিঙ্ক:</b>\n<code>{ref_link}</code>\n\n"
            f"📊 <b>মোট রেফার করেছেন:</b> {ref_count} জন\n"
            f"💰 <b>রেফার থেকে মোট আয়:</b> {ref_income:.2f} BDT\n"
            f"🎁 <b>প্রতি নতুন referral-এর fixed bonus:</b> {ref_bonus:.2f} BDT\n\n"
            "নতুন ইউজার আপনার লিঙ্ক দিয়ে প্রথমবার join করলে bonus একবারই যোগ হবে।"
        )
        await update.message.reply_text(pe(ref_text), parse_mode="HTML")

    elif action_text == "Deposit":
        pending = get_pending_deposit(user.id)
        if pending:
            await update.message.reply_text(
                pe(
                    "⏳ <b>আপনার একটি ডিপোজিট রিকোয়েস্ট এখনও অপেক্ষমাণ আছে।</b>\n\n"
                    f"💰 Amount: <b>{pending['amount']:.2f} BDT</b>\n"
                    f"💳 Method: <b>{pending['method']}</b>\n"
                    f"🧾 TrxID: <code>{pending['trx_id']}</code>\n\n"
                    "অ্যাডমিন approve বা reject না করা পর্যন্ত নতুন ডিপোজিট করা যাবে না।"
                ),
                parse_mode="HTML",
            )
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, min_deposit, icon_key FROM payment_methods")
        methods = cursor.fetchall()
        conn.close()

        if not methods:
            await update.message.reply_text(pe("❌ বর্তমানে কোনো পেমেন্ট মেথড খালি/উপলব্ধ নেই!"), parse_mode="HTML")
            return

        keyboard = []
        row = []
        for m in methods:
            m_name = m['name']
            m_min = m['min_deposit']
            m_icon = m['icon_key']
            
            unit = "USDT" if m_name.lower() == 'binance' else "BDT"
            btn_txt = f"{m_name} (Min {m_min} {unit})" if m_name.lower() == 'binance' else f"{m_name} (Min {m_min:.0f} BDT)"
            
            row.append(pbtn(btn_txt, icon=m_icon, callback_data=f'depmethod_{m_name}'))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.append([pbtn("Close", icon="close", style="danger", callback_data="close_msg")])

        await update.message.reply_text(pe("💠 <b>ডিপোজিট পেমেন্ট মাধ্যম বেছে নিন:</b>"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif action_text == "Withdraw":
        pending = get_pending_withdrawal(user.id)
        if pending:
            await update.message.reply_text(
                pe(
                    "⏳ আপনার একটি withdraw request review-এর অপেক্ষায় আছে।\n"
                    f"Amount: <b>{pending['amount']:.2f} BDT</b>"
                ),
                parse_mode="HTML",
            )
            return
        context.user_data["state"] = "awaiting_withdraw_amount"
        await update.message.reply_text(
            pe(
                "💸 কত BDT withdraw করতে চান?\n"
                f"আপনার available balance: <b>{db_user['balance']:.2f} BDT</b>\n"
                "টাকার পরিমাণ লিখুন।"
            ),
            parse_mode="HTML",
        )

    elif action_text == "Support":
        supp_link = get_setting('support_link')
        keyboard = [
            [pbtn("Contact Support", icon="support", style="primary", url=supp_link)],
            [pbtn("Close", icon="close", style="danger", callback_data="close_msg")]
        ]
        await update.message.reply_text(pe("🗣️ <b>Contact us for any help:</b>"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif action_text == "Admin Panel" and is_admin(user.id):
        await send_admin_panel(update)


async def handle_deposit_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish a manual deposit with a screenshot and send it for review."""
    if not update.message or not update.message.photo:
        return

    user = update.effective_user
    set_current_user(user)
    if context.user_data.get("state") != "awaiting_deposit_screenshot":
        return

    if is_user_banned(user.id):
        await update.message.reply_text(
            pe("🚫 <b>আপনি এই বট থেকে ব্যান হয়ে গেছেন!</b>"),
            parse_mode="HTML",
        )
        return

    if not is_admin(user.id):
        is_joined, missing_channels = await check_force_join(user.id, context)
        if not is_joined:
            buttons = []
            for ch in missing_channels:
                join_url = force_join_button_url(ch)
                if join_url:
                    buttons.append([
                        pbtn("JOIN CHANNEL", icon="link", style="primary", url=join_url)
                    ])
            buttons.append([
                pbtn("Verify / Check Again", icon="refresh", style="success", callback_data="check_join")
            ])
            await update.message.reply_text(
                pe("⚠️ <b>বট ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন:</b>"),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML",
            )
            return

    method = context.user_data.get("dep_method", "Payment")
    amount = float(context.user_data.get("dep_amount", 0) or 0)
    dep_usdt = float(context.user_data.get("dep_usdt", 0) or 0)
    trx_id = str(context.user_data.get("dep_trx_id", "")).strip()
    screenshot_file_id = update.message.photo[-1].file_id

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Serialize the final check and insert so rapid submissions cannot
        # create more than one pending request for the same user.
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id FROM deposits WHERE user_id = ? AND status = 'pending' LIMIT 1",
            (user.id,),
        )
        if cursor.fetchone():
            conn.rollback()
            context.user_data.clear()
            await update.message.reply_text(
                pe(
                    "⏳ আপনার একটি deposit request ইতিমধ্যে pending আছে। "
                    "সেটি approve বা reject না হওয়া পর্যন্ত দ্বিতীয় request যাবে না।"
                ),
                parse_mode="HTML",
            )
            return

        cursor.execute(
            "SELECT id FROM deposits "
            "WHERE lower(trim(trx_id)) = lower(trim(?)) "
            "AND status IN ('pending', 'approved')",
            (trx_id,),
        )
        if cursor.fetchone():
            conn.rollback()
            context.user_data.clear()
            await update.message.reply_text(
                pe("❌ এই Transaction ID আগেই ব্যবহার করা হয়েছে।"),
                parse_mode="HTML",
            )
            return

        cursor.execute(
            "INSERT INTO deposits "
            "(user_id, amount, method, trx_id, screenshot_file_id, status) "
            "VALUES (?, ?, ?, ?, ?, 'pending')",
            (user.id, amount, method, trx_id, screenshot_file_id),
        )
        deposit_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        context.user_data.clear()
        await update.message.reply_text(
            pe("❌ এই Transaction ID আগেই ব্যবহার করা হয়েছে।"),
            parse_mode="HTML",
        )
        return
    finally:
        conn.close()

    context.user_data.clear()
    await update.message.reply_text(
        pe(
            "⏳ <b>আপনার payment request জমা হয়েছে!</b>\n"
            "TrxID এবং screenshot admin-এর কাছে পাঠানো হয়েছে। "
            "Approve হলে balance যোগ হবে।"
        ),
        parse_mode="HTML",
    )

    keyboard = InlineKeyboardMarkup([
        [
            pbtn(
                f"Approve {amount:.2f} BDT",
                icon="done",
                style="success",
                callback_data=f"appdep_{deposit_id}",
            )
        ],
        [pbtn("Reject", icon="close", style="danger", callback_data=f"rejdep_{deposit_id}")],
    ])
    usdt_info = f"\n💲 USDT Amount: <b>{dep_usdt:g} USDT</b>" if dep_usdt > 0 else ""
    admin_caption = (
        f"💠 <b>নতুন manual deposit request!</b>\n\n"
        f"👤 ইউজার: {user.first_name} (<code>{user.id}</code>)\n"
        f"💠 মাধ্যম: <b>{method}</b>{usdt_info}\n"
        f"💠 ব্যালেন্স পাবে: <b>{amount:.2f} BDT</b>\n"
        f"🧾 TrxID: <code>{trx_id}</code>\n\n"
        "📸 Screenshot সংযুক্ত আছে। Payment মিলিয়ে তারপর Approve করুন।"
    )

    notification_sent = await send_deposit_photo_notification(
        context,
        screenshot_file_id,
        admin_caption,
        reply_markup=keyboard,
    )
    if not notification_sent:
        for admin_id in get_all_admin_ids():
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=screenshot_file_id,
                    caption=pe(admin_caption),
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            except Exception as error:
                logging.error("Failed to send deposit screenshot to admin: %s", error)


# ==================== Callback Queries ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    set_current_user(user)

    if not is_admin(user.id) and data != "check_join":
        is_joined, missing_channels = await check_force_join(user.id, context)
        if not is_joined:
            buttons = []
            for ch in missing_channels:
                join_url = force_join_button_url(ch)
                if join_url:
                    buttons.append([
                        pbtn("JOIN CHANNEL", icon="link", style="primary", url=join_url)
                    ])
            buttons.append([
                pbtn("Verify / Check Again", icon="refresh", style="success", callback_data="check_join")
            ])
            prompt = pe("⚠️ <b>বট ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন:</b>")
            markup = InlineKeyboardMarkup(buttons)
            try:
                await query.edit_message_text(
                    prompt,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=prompt,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
            return

    if data == "close_msg":
        await query.message.delete()
        return

    if is_admin(user.id) and data == "admin_withdrawals":
        conn = get_db()
        rows = conn.execute(
            "SELECT id, user_id, amount FROM withdrawals "
            "WHERE status = 'pending' ORDER BY id DESC LIMIT 25"
        ).fetchall()
        conn.close()
        keyboard = [
            [pbtn(
                f"#{row['id']} · {row['amount']:.2f} BDT · User {row['user_id']}",
                icon="money",
                callback_data=f"withdraw_view_{row['id']}",
            )]
            for row in rows
        ]
        keyboard.append([
            pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")
        ])
        message = (
            "💸 <b>Pending Withdrawals</b>\n"
            "নিচের request বেছে নিয়ে approve বা reject করুন।"
            if rows else
            "✅ <b>কোনো pending withdrawal নেই।</b>"
        )
        await query.edit_message_text(
            pe(message),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data.startswith("withdraw_view_"):
        try:
            withdrawal_id = int(data.rsplit("_", 1)[1])
        except (TypeError, ValueError):
            await query.edit_message_text("Invalid withdrawal request.")
            return
        conn = get_db()
        row = conn.execute(
            "SELECT user_id, amount, payout_details, created_at "
            "FROM withdrawals WHERE id = ? AND status = 'pending'",
            (withdrawal_id,),
        ).fetchone()
        conn.close()
        if not row:
            await query.edit_message_text(
                pe("এই request আর pending নেই।"),
                reply_markup=InlineKeyboardMarkup([[
                    pbtn("Pending Withdrawals", icon="back", callback_data="admin_withdrawals")
                ]]),
                parse_mode="HTML",
            )
            return
        payout_details = html_lib.escape(str(row["payout_details"] or ""))
        await query.edit_message_text(
            "💸 <b>Withdraw request</b>\n\n"
                f"Request: <code>#{withdrawal_id}</code>\n"
                f"User: <code>{row['user_id']}</code>\n"
                f"Amount: <b>{row['amount']:.2f} BDT</b>\n"
                f"Payout details: <code>{payout_details}</code>\n"
                f"Requested: <code>{row['created_at']}</code>",
            reply_markup=InlineKeyboardMarkup([
                [pbtn(
                    "Approve",
                    icon="done",
                    style="success",
                    callback_data=f"withdraw_approve_{withdrawal_id}",
                )],
                [pbtn(
                    "Reject & Refund",
                    icon="close",
                    style="danger",
                    callback_data=f"withdraw_reject_{withdrawal_id}",
                )],
                [pbtn(
                    "Pending Withdrawals",
                    icon="back",
                    callback_data="admin_withdrawals",
                )],
            ]),
            parse_mode="HTML",
        )
        return

    if data.startswith(("withdraw_approve_", "withdraw_reject_")):
        if not is_admin(user.id):
            return
        try:
            withdrawal_id = int(data.rsplit("_", 1)[1])
        except (TypeError, ValueError):
            await query.edit_message_text("Invalid withdrawal request.")
            return

        approve = data.startswith("withdraw_approve_")
        result = review_withdrawal_request(
            withdrawal_id, user.id, approve
        )
        if result["status"] not in {"approved", "rejected"}:
            status_messages = {
                "not_found": "এই withdraw request পাওয়া যায়নি।",
                "already_processed": "এই request আগেই review করা হয়েছে।",
                "error": "Request review করা যায়নি; আবার চেষ্টা করুন।",
            }
            await query.edit_message_text(
                pe(status_messages.get(result["status"], "Request review ব্যর্থ।")),
                reply_markup=None,
                parse_mode="HTML",
            )
            return

        amount = result["amount"]
        target_user = result["user_id"]
        if approve:
            admin_status = (
                f"✅ Withdraw #{withdrawal_id} approved.\n"
                f"{amount:.2f} BDT payout details-এ manually পাঠান।"
            )
            user_status = (
                f"✅ আপনার withdraw request approve হয়েছে: {amount:.2f} BDT। "
                "Admin আপনার দেওয়া details-এ manual payout process করবেন।"
            )
        else:
            admin_status = (
                f"❌ Withdraw #{withdrawal_id} rejected. "
                f"{amount:.2f} BDT user balance-এ ফেরত গেছে।"
            )
            user_status = (
                f"❌ আপনার withdraw request reject হয়েছে। "
                f"{amount:.2f} BDT balance-এ ফেরত দেওয়া হয়েছে।"
            )
        await query.edit_message_text(
            pe(admin_status),
            reply_markup=None,
            parse_mode="HTML",
        )
        try:
            await context.bot.send_message(
                chat_id=target_user,
                text=pe(user_status),
                parse_mode="HTML",
            )
        except Exception as error:
            logging.error("Could not notify user about withdrawal review: %s", error)
        return

    if data.startswith(("purchase_copy_", "purchase_csv_")):
        parts = data.split("_", 2)
        delivery_type = parts[1]
        order_ref = parts[2] if len(parts) > 2 else ""
        conn = get_db()
        rows = conn.execute(
            "SELECT title, item_data FROM purchases "
            "WHERE user_id = ? AND order_ref = ? ORDER BY id",
            (user.id, order_ref),
        ).fetchall()
        conn.close()

        if not rows:
            await query.edit_message_text(
                pe("❌ এই ক্রয়ের ডাটা পাওয়া যায়নি।"),
                parse_mode="HTML",
            )
            return

        if delivery_type == "copy":
            for index, row in enumerate(rows, start=1):
                title = html_lib.escape(str(row["title"] or "Product"))
                value = html_lib.escape(str(row["item_data"] or ""))
                await context.bot.send_message(
                    chat_id=user.id,
                    text=(
                        f"<b>{title} — {index}</b>\n"
                        f"<code>{value}</code>"
                    ),
                    parse_mode="HTML",
                )
            await query.edit_message_text(
                pe("✅ প্রতিটি item-এর code-এ ট্যাপ করলে value কপি হবে।"),
                parse_mode="HTML",
            )
            return

        csv_text = io.StringIO(newline="")
        writer = csv.writer(csv_text)
        writer.writerow(["Product", "Item", "Value"])
        for index, row in enumerate(rows, start=1):
            writer.writerow([
                row["title"] or "Product",
                index,
                row["item_data"] or "",
            ])
        csv_payload = io.BytesIO(
            ("\ufeff" + csv_text.getvalue()).encode("utf-8")
        )
        await context.bot.send_document(
            chat_id=user.id,
            document=csv_payload,
            filename=f"purchase_{order_ref}.csv",
            caption=pe("✅ CSV ফাইলটি Google Sheets-এ খুলতে বা import করতে পারবেন।"),
            parse_mode="HTML",
        )
        await query.edit_message_text(
            pe("✅ আপনার product CSV ফাইল পাঠানো হয়েছে।"),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data in {"admin_backup_file", "admin_backup_file_legacy"}:
        try:
            backup = await asyncio.to_thread(build_full_backup)
            payload = json.dumps(
                backup, ensure_ascii=False, indent=2, default=str
            ).encode("utf-8")
            await context.bot.send_document(
                chat_id=user.id,
                document=io.BytesIO(payload),
                filename=f"gx_shop_full_backup_{datetime.now():%Y%m%d_%H%M%S}.json",
                caption=pe(
                    "✅ Full bot backup: users, balances, referrals, deposits, "
                    "products/stock, purchases, admins, channels ও সব settings। "
                    "কোনো environment credential ফাইলে রাখা হয়নি।"
                ),
                parse_mode="HTML",
            )
            await query.edit_message_text(
                pe("✅ <b>Full backup file আপনাকে পাঠানো হয়েছে।</b>"),
                reply_markup=InlineKeyboardMarkup([[
                    pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")
                ]]),
                parse_mode="HTML",
            )
        except Exception as error:
            logging.exception("Full backup file failed: %s", type(error).__name__)
            await query.edit_message_text(
                pe(
                    "❌ <b>Backup file তৈরি/পাঠানো যায়নি।</b>\n"
                    f"কারণ: <code>{type(error).__name__}</code>"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")
                ]]),
                parse_mode="HTML",
            )
        return

    if is_admin(user.id) and data == "admin_delete_all":
        await query.edit_message_text(
            pe(
                "🛑 <b>সব bot data মুছে ফেলবেন?</b>\n\n"
                "Users, balance/referral, deposits, purchases, products/stock, "
                "categories, payment settings, channels ও অতিরিক্ত admins মুছে "
                "যাবে। শুধু configured Owner admin থাকবে। কাজটি undo করা যাবে না।"
            ),
            reply_markup=InlineKeyboardMarkup([
                [pbtn("YES — Delete All Data", icon="delete", style="danger", callback_data="admin_delete_all_confirm")],
                [pbtn("Cancel", icon="close", callback_data="back_admin_panel")],
            ]),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "admin_delete_all_confirm":
        await query.edit_message_text(
            pe("⏳ <b>Bot data reset হচ্ছে...</b>"),
            parse_mode="HTML",
        )
        try:
            await asyncio.to_thread(reset_all_bot_data)
            await query.edit_message_text(
                pe(
                    "✅ Local bot data reset হয়েছে। শুধু configured Owner admin থাকবে।"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")
                ]]),
                parse_mode="HTML",
            )
        except Exception as error:
            logging.exception("Full bot data reset failed: %s", type(error).__name__)
            await query.edit_message_text(
                pe(
                    "❌ <b>Data reset সম্পন্ন হয়নি; সম্ভব হলে আগের data restore করা হয়েছে।</b>\n"
                    f"কারণ: <code>{html_lib.escape(str(error)[:300])}</code>"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")
                ]]),
                parse_mode="HTML",
            )
        return

    # Admin: Delete Product Categories Menu
    if is_admin(user.id) and data == "admin_del_prod_prompt":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = cursor.fetchall()
        conn.close()

        if not cats:
            await query.edit_message_text(pe("❌ <b>কোনো ক্যাটাগরি নেই!</b>"), reply_markup=InlineKeyboardMarkup([[pbtn("Back", icon="back", callback_data="admin_gx_control")]]), parse_mode="HTML")
            return

        keyboard = []
        row = []
        for c in cats:
            c_name = c['name']
            row.append(pbtn(c_name, icon=get_product_icon_key(c_name), style="danger", callback_data=f"delcat_sel_{c_name}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.append([pbtn("Back", icon="back", callback_data="admin_gx_control")])
        await query.edit_message_text(pe("🗑️ <b>প্রোডাক্ট ডিলিট করতে ক্যাটাগরি সিলেক্ট করুন:</b>"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    # Admin: Delete Product Items List by Category
    if is_admin(user.id) and data.startswith("delcat_sel_"):
        cat_name = data.replace("delcat_sel_", "")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, price FROM products WHERE category = ? GROUP BY title", (cat_name,))
        items = cursor.fetchall()
        conn.close()

        if not items:
            await query.edit_message_text(pe(f"❌ <b>{cat_name}</b> ক্যাটাগরিতে কোনো প্রোডাক্ট নেই!"), reply_markup=InlineKeyboardMarkup([[pbtn("Back", icon="back", callback_data="admin_del_prod_prompt")]]), parse_mode="HTML")
            return

        keyboard = []
        for i in items:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as stock FROM products WHERE title = ? AND category = ?", (i['title'], cat_name))
            stock_count = cursor.fetchone()['stock']
            conn.close()

            icon_key = get_product_icon_key(i['title'])
            keyboard.append([
                pbtn(
                    f"🗑 {i['title']} ({stock_count} Stock)",
                    icon=icon_key,
                    style="danger",
                    callback_data=f"delitem_prompt_{i['title']}"
                )
            ])

        keyboard.append([pbtn("Back", icon="back", callback_data="admin_del_prod_prompt")])
        await query.edit_message_text(pe(f"🗑️ <b>{cat_name}</b> ক্যাটাগরির প্রোডাক্টসমূহ:\nযেটি ডিলিট করতে চান তাতে ক্লিক করুন:"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    # Admin: Delete Product Confirmation Prompt
    if is_admin(user.id) and data.startswith("delitem_prompt_"):
        title = data.replace("delitem_prompt_", "")
        context.user_data['del_prod_title'] = title

        keyboard = [
            [
                pbtn("হ্যাঁ, ডিলিট করুন", icon="done", style="danger", callback_data="delitem_confirm"),
                pbtn("না/বাতিল", icon="close", style="primary", callback_data="admin_del_prod_prompt")
            ]
        ]
        await query.edit_message_text(pe(f"⚠️ আপনি কি নিশ্চিতভাবে <b>{title}</b> প্রোডাক্টটি স্টক থেকে ডিলিট করতে চান?"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    # Admin: Execute Delete Product
    if is_admin(user.id) and data == "delitem_confirm":
        title = context.user_data.get('del_prod_title')
        if not title:
            await query.edit_message_text(pe("❌ কিছু ভুল হয়েছে, আবার চেষ্টা করুন।"), reply_markup=InlineKeyboardMarkup([[pbtn("Back", icon="back", callback_data="admin_gx_control")]]), parse_mode="HTML")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE title = ?", (title,))
        conn.commit()
        conn.close()

        context.user_data.pop('del_prod_title', None)
        await query.edit_message_text(pe(f"✅ সফলভাবে <b>{title}</b> প্রোডাক্টটি স্টক থেকে ডিলিট করা হয়েছে!"), reply_markup=InlineKeyboardMarkup([[pbtn("Back to GX Control", icon="back", callback_data="admin_gx_control")]]), parse_mode="HTML")
        return

    # GX Control Sub-Menu Handler
    if is_admin(user.id) and data == "admin_gx_control":
        context.user_data.pop('state', None)
        ref_bonus = get_setting('referral_bonus') or "0"
        usdt_rate = get_setting('usdt_rate') or "120"
        
        keyboard = [
            [
                pbtn(f"Referral Bonus ({ref_bonus} BDT)", icon="gift", callback_data='admin_set_ref'),
                pbtn(f"USDT Rate ({usdt_rate}৳)", icon="binance", callback_data='admin_set_usdt_rate')
            ],
            [
                pbtn("Payment Set", icon="card", callback_data='admin_set_payment'),
                pbtn("Support Set", icon="support", callback_data='admin_set_supp')
            ],
            [
                pbtn("Balance Control", icon="balance_main", style="primary", callback_data='admin_balance_menu')
            ],
            [
                pbtn("Delete Product", icon="delete", style="danger", callback_data='admin_del_prod_prompt')
            ],
            [
                pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")
            ]
        ]
        await query.edit_message_text(
            pe("⚙️ <b>GX CONTROL PANEL</b>\nManage your advanced configurations below:"),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Balance Control Callbacks
    if is_admin(user.id) and data == "admin_balance_menu":
        context.user_data.pop('state', None)
        keyboard = [
            [
                pbtn("Add Balance", icon="balance_add", style="success", callback_data="admin_add_bal_prompt"),
                pbtn("Cut Balance", icon="balance_cut", style="danger", callback_data="admin_cut_bal_prompt")
            ],
            [
                pbtn("Back to GX Control", icon="back", callback_data="admin_gx_control")
            ]
        ]
        await query.edit_message_text(
            pe("💠 <b>Balance Management</b>\n\nইউজারের ব্যালেন্স যোগ বা কাটতে নিচের বাটনগুলোতে ক্লিক করুন:"),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    elif is_admin(user.id) and data == "admin_add_bal_prompt":
        context.user_data['state'] = 'admin_add_balance'
        await query.edit_message_text(
            pe("➕ <b>Add Balance</b>\n\nযে ইউজারের ব্যালেন্স যোগ করতে চান তার **User ID** এবং **Amount** এভাবে লিখে পাঠান:\n`User_ID Amount`\n\nউদাহরণ: `123456789 100`"),
            reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_balance_menu")]]),
            parse_mode="HTML"
        )
        return

    elif is_admin(user.id) and data == "admin_cut_bal_prompt":
        context.user_data['state'] = 'admin_cut_balance'
        await query.edit_message_text(
            pe("➖ <b>Cut Balance</b>\n\nযে ইউজারের ব্যালেন্স কাটতে চান তার **User ID** এবং **Amount** এভাবে লিখে পাঠান:\n`User_ID Amount`\n\nউদাহরণ: `123456789 50`"),
            reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_balance_menu")]]),
            parse_mode="HTML"
        )
        return

    # USDT Rate Set (Admin)
    if is_admin(user.id) and data == "admin_set_usdt_rate":
        context.user_data['state'] = 'awaiting_usdt_rate'
        curr_rate = get_setting('usdt_rate') or "120"
        await query.edit_message_text(
            pe(f"💲 <b>SET USDT CONVERSION RATE</b>\n\nবর্তমান রেট: <b>1$ = {curr_rate} BDT</b>\n\n১ ডলারের (1 USDT) নতুন BDT মূল্য টাইপ করে পাঠান (যেমন: 120, 125, 130):"),
            reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_gx_control")]]),
            parse_mode="HTML"
        )
        return

    # Broadcast Prompt
    if is_admin(user.id) and data == "admin_broadcast":
        context.user_data['state'] = 'awaiting_broadcast_msg'
        await query.edit_message_text(
            pe("📢 <b>BROADCAST MESSAGE</b>\n\n"
            "যে নোটিশ বা মেসেজটি বটের সকল মেম্বারদের কাছে পাঠাতে চান, তা এখন টাইপ করে বা ফরোয়ার্ড করে পাঠান:"),
            reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="back_admin_panel")]]),
            parse_mode="HTML"
        )
        return

    # View Leaderboard
    if data == "view_leaderboard":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.first_name, SUM(p.price) as total_spent 
            FROM purchases p 
            JOIN users u ON p.user_id = u.user_id 
            GROUP BY u.user_id 
            ORDER BY total_spent DESC LIMIT 10
        ''')
        top_buyers = cursor.fetchall()
        conn.close()

        if not top_buyers:
            lb_text = "🏆 <b>TOP BUYERS LEADERBOARD</b>\n\n<i>এখনও কেউ প্রোডাক্ট কেনেনি!</i>"
        else:
            lb_text = "🏆 <b>TOP 10 BUYERS LEADERBOARD</b>\n\n"
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for idx, row in enumerate(top_buyers):
                m = medals[idx] if idx < len(medals) else "🔹"
                lb_text += f"{m} <b>{row['first_name']}</b> — {row['total_spent']:.2f} BDT\n"

        keyboard = [
            [pbtn("Back", icon="back", callback_data="back_to_profile")],
            [pbtn("Close", icon="close", style="danger", callback_data="close_msg")]
        ]
        
        await query.edit_message_text(text=pe(lb_text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    # Back to Profile
    if data == "back_to_profile":
        db_user = get_or_create_user(
            user.id, user.first_name, username=getattr(user, "username", "") or ""
        )
        ref_income = db_user['ref_earnings'] if db_user['ref_earnings'] else 0.0
        
        profile_text = (
            f"👤 <b>আপনার প্রোফাইল:</b>\n\n"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"💠 <b>ব্যালেন্স:</b> {db_user['balance']:.2f} BDT\n"
            f"🎁 <b>রেফার থেকে আয়:</b> {ref_income:.2f} BDT"
        )
        keyboard = [
            [pbtn("হিস্ট্রি", icon="bag", callback_data='purchases')],
            [pbtn("Close", icon="close", style="danger", callback_data="close_msg")]
        ]
        
        await query.edit_message_text(text=pe(profile_text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    # Purchase History Callback
    if data == "purchases":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT title, price, date FROM purchases WHERE user_id = ? ORDER BY id DESC", (user.id,))
        records = cursor.fetchall()
        conn.close()

        keyboard = [
            [pbtn("Back", icon="back", callback_data="back_to_profile")],
            [pbtn("Close", icon="close", style="danger", callback_data="close_msg")]
        ]

        if not records:
            history_text = "🛍️ <b>আপনি এখনও কোনো প্রোডাক্ট কেনেননি!</b>"
        else:
            history_text = f"🛍️ <b>আপনার ক্রয়কৃত প্রোডাক্টের হিস্ট্রি (মোট: {len(records)} টি):</b>\n\n"
            for idx, r in enumerate(records, 1):
                history_text += f"{idx}. <b>{r['title']}</b> - {r['price']:.2f} BDT\n📅 <i>{r['date']}</i>\n\n"

        await query.edit_message_text(text=pe(history_text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    # Admin: User Search & Ban System
    if is_admin(user.id) and data == "admin_user_mgmt":
        context.user_data['state'] = 'awaiting_search_user_id'
        await query.edit_message_text(pe("👤 যে মেম্বারের ব্যালেন্স বা স্ট্যাটাস দেখতে চান, তার <b>Telegram User ID</b> পাঠান:"), reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="back_admin_panel")]]), parse_mode="HTML")
        return

    elif is_admin(user.id) and data.startswith("toggle_ban_"):
        target_id = int(data.split('_')[2])
        if target_id == SUPER_ADMIN_ID:
            await query.answer("অনারকে ব্যান করা যাবে না!", show_alert=True)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
        u = cursor.fetchone()

        if u:
            new_ban_state = 0 if u['is_banned'] == 1 else 1
            cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_ban_state, target_id))
            conn.commit()
            conn.close()

            status_msg = "ব্যান করা হয়েছে!" if new_ban_state == 1 else "আনব্যান করা হয়েছে!"
            await query.answer(f"User {target_id} কে {status_msg}", show_alert=True)
            
            context.user_data['state'] = 'awaiting_search_user_id'
            await query.edit_message_text(
                pe(f"✅ ইউজার <code>{target_id}</code>-কে সফলভাবে {status_msg}\n\nআরেকজনের তথ্য দেখতে চাইলে নতুন <b>Telegram User ID</b> পাঠান:"),
                reply_markup=InlineKeyboardMarkup([[pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")]]),
                parse_mode="HTML"
            )
            return

    if is_admin(user.id) and data == "admin_withdraw_min":
        context.user_data.pop("state", None)
        min_amount = get_min_withdraw_amount()
        await query.edit_message_text(
            pe(
                "💸 <b>MINIMUM WITHDRAW SETTINGS</b>\n\n"
                f"Current minimum: <b>{min_amount:.2f} BDT</b>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [pbtn("Set / Change Minimum", icon="note", callback_data="prompt_withdraw_min")],
                [pbtn("Back", icon="back", callback_data="back_admin_panel")],
            ]),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "prompt_withdraw_min":
        context.user_data["state"] = "awaiting_min_withdraw"
        await query.edit_message_text(
            pe("💸 নতুন <b>Minimum Withdraw Amount (BDT)</b> লিখুন:"),
            reply_markup=InlineKeyboardMarkup([[
                pbtn("Cancel", icon="close", style="danger", callback_data="admin_withdraw_min")
            ]]),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "admin_withdraw_notify":
        context.user_data.pop("state", None)
        enabled = withdrawal_notifications_enabled()
        target = get_setting("withdraw_notify_chat_id") or "Not Set"
        keyboard = [
            [pbtn("Set / Change Group", icon="group", callback_data="prompt_withdraw_group")],
        ]
        if target != "Not Set":
            keyboard.append([
                pbtn(
                    "Disable Alerts" if enabled else "Enable Alerts",
                    icon="stop" if enabled else "done",
                    style="danger" if enabled else "success",
                    callback_data="toggle_withdraw_notify",
                )
            ])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])
        await query.edit_message_text(
            pe(
                "💸 <b>WITHDRAW REQUEST GROUP</b>\n\n"
                f"Status: <b>{'ON' if enabled else 'OFF'}</b>\n"
                f"Target group: <code>{target}</code>\n\n"
                "Withdraw request-গুলো আলাদা এই group-এ approve/reject buttons-সহ যাবে।\n"
                "Bot-কে group-এ administrator করতে হবে।"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "prompt_withdraw_group":
        context.user_data["state"] = "awaiting_withdraw_notify_target"
        await query.edit_message_text(
            pe(
                "📢 Withdrawal request-এর target <b>group Chat ID</b> পাঠান:\n\n"
                "উদাহরণ: <code>-100123456789</code>\n"
                "Bot-এর administrator permission যাচাই করে সেভ করা হবে।"
            ),
            reply_markup=InlineKeyboardMarkup([[
                pbtn("Cancel", icon="close", style="danger", callback_data="admin_withdraw_notify")
            ]]),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "toggle_withdraw_notify":
        if not get_setting("withdraw_notify_chat_id").strip():
            await query.answer("আগে একটি withdrawal group সেট করুন।", show_alert=True)
            return
        new_status = (
            "OFF" if get_setting("withdraw_notify_enabled") == "ON" else "ON"
        )
        set_setting("withdraw_notify_enabled", new_status)
        await query.answer(f"Withdraw alerts {new_status} করা হয়েছে।", show_alert=True)
        await query.edit_message_text(
            pe(f"💸 <b>Withdraw alerts {new_status}</b>"),
            reply_markup=InlineKeyboardMarkup([[
                pbtn("Back to Withdraw Settings", icon="back", callback_data="admin_withdraw_notify")
            ]]),
            parse_mode="HTML",
        )
        return

    # Admin: Group Log Settings
    if is_admin(user.id) and data == "admin_deposit_notify":
        context.user_data.pop('state', None)
        notify_enabled = deposit_notifications_enabled()
        notify_target = get_setting("deposit_notify_chat_id") or "Not Set"
        notify_type = get_setting("deposit_notify_type") or "Not Set"
        keyboard = [
            [
                pbtn("Set Group", icon="group", callback_data="prompt_deposit_group"),
                pbtn("Set Channel", icon="megaphone", callback_data="prompt_deposit_channel"),
            ],
            [
                pbtn(
                    "Disable Alerts" if notify_enabled else "Enable Alerts",
                    icon="stop" if notify_enabled else "done",
                    style="danger" if notify_enabled else "success",
                    callback_data="toggle_deposit_notify",
                )
            ],
            [pbtn("Back", icon="back", callback_data="back_admin_panel")],
        ]
        msg = (
            "💠 <b>DEPOSIT ALERT SETTINGS</b>\n\n"
            f"Status: <b>{'ON' if notify_enabled else 'OFF'}</b>\n"
            f"Target type: <b>{notify_type}</b>\n"
            f"Target: <code>{notify_target}</code>\n\n"
            "ON থাকলে pending manual deposit request "
            "শুধু এই group/channel-এ যাবে; admin-এর private bot inbox-এ যাবে না।\n"
            "Bot-কে target group/channel-এ administrator হতে হবে।"
        )
        await query.edit_message_text(
            pe(msg),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data in {"prompt_deposit_group", "prompt_deposit_channel"}:
        context.user_data["state"] = "awaiting_deposit_notify_target"
        context.user_data["deposit_notify_type"] = (
            "group" if data == "prompt_deposit_group" else "channel"
        )
        target_label = "group Chat ID" if data == "prompt_deposit_group" else "channel @username বা Chat ID"
        await query.edit_message_text(
            pe(
                f"📢 target-এর <b>{target_label}</b> পাঠান:\n\n"
                "উদাহরণ: <code>-100123456789</code> অথবা <code>@my_channel</code>\n"
                "সেভ করার আগে bot-এর administrator permission যাচাই হবে।"
            ),
            reply_markup=InlineKeyboardMarkup(
                [[pbtn("Cancel", icon="close", style="danger", callback_data="admin_deposit_notify")]]
            ),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "toggle_deposit_notify":
        if not get_setting("deposit_notify_chat_id").strip():
            await query.answer("আগে একটি group বা channel সেট করুন।", show_alert=True)
            return
        new_status = "OFF" if get_setting("deposit_notify_enabled") == "ON" else "ON"
        set_setting("deposit_notify_enabled", new_status)
        await query.answer(
            f"Deposit alerts {new_status} করা হয়েছে।",
            show_alert=True,
        )
        await query.edit_message_text(
            pe(
                f"💠 <b>Deposit alerts {new_status}</b>\n\n"
                "Settings দেখতে আবার Deposit Alerts চাপুন।"
            ),
            reply_markup=InlineKeyboardMarkup(
                [[pbtn("Back to Admin Panel", icon="back", callback_data="back_admin_panel")]]
            ),
            parse_mode="HTML",
        )
        return

    if is_admin(user.id) and data == "admin_group_log":
        context.user_data.pop('state', None)
        log_group = get_setting('log_group_id') or "Not Set"
        keyboard = [
            [pbtn("Set / Change Group ID", icon="link", callback_data="prompt_set_group_id")],
            [pbtn("Back", icon="back", callback_data="back_admin_panel")]
        ]
        msg = (
            f"📢 <b>GROUP LOG SETTINGS</b>\n\n"
            f"বর্তমান Log Group ID: <code>{log_group}</code>\n\n"
            f"💡 <i>ইউজার ডিপোজিট বা কেনাকাটা করলে এই গ্রুপে অটো নোটিফিকেশন যাবে।</i>"
        )
        await query.edit_message_text(pe(msg), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif is_admin(user.id) and data == "prompt_set_group_id":
        context.user_data['state'] = 'awaiting_group_id'
        await query.edit_message_text(
            pe("📢 গ্রুপের <b>Chat ID</b> লিখে পাঠান (যেমন: <code>-100123456789</code>):"),
            reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_group_log")]]),
            parse_mode="HTML"
        )
        return

    # Check Force Join Callback
    if data == "check_join":
        with _force_join_cache_lock:
            _force_join_cache.pop(user.id, None)
        is_joined, missing_channels = await check_force_join(user.id, context)
        if is_joined:
            await query.message.delete()
            get_or_create_user(
                user.id, user.first_name,
                context.user_data.pop("pending_ref_id", 0),
                username=getattr(user, "username", "") or "",
            )
            await context.bot.send_message(
                chat_id=user.id,
                text=pe(f"👋 <b>Mail & ProxySell Bot</b> এ আপনাকে স্বাগতম, {user.first_name}!"),
                reply_markup=get_main_keyboard(user.id),
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ আপনি এখনও সব চ্যানেলে জয়েন করেননি!", show_alert=True)
            
            buttons = []
            for ch in missing_channels:
                join_url = force_join_button_url(ch)
                if join_url:
                    buttons.append([
                        pbtn("JOIN CHANNEL", icon="link", style="primary", url=join_url)
                    ])
            
            buttons.append([pbtn("Verify / Check Again", icon="refresh", style="success", callback_data="check_join")])
            
            try:
                await query.edit_message_text(
                    pe("⚠️ <b>বট ব্যবহার করতে নিচের চ্যানেলে জয়েন করুন:</b>"),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        return

    # Dynamic Deposit Method Selection Callback
    if data.startswith('depmethod_'):
        pending = get_pending_deposit(user.id)
        if pending:
            await query.answer(
                "আপনার আগের deposit request approve/reject হওয়া পর্যন্ত অপেক্ষা করুন।",
                show_alert=True,
            )
            return
        method_name = data.split('_')[1]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT min_deposit FROM payment_methods WHERE name = ?", (method_name,))
        res = cursor.fetchone()
        conn.close()

        min_limit = res['min_deposit'] if res else 10.0

        context.user_data['dep_method'] = method_name
        context.user_data['state'] = 'awaiting_deposit_amount'
        
        await query.message.delete()
        
        if method_name.lower() == 'binance':
            try:
                usdt_rate = float(get_setting('usdt_rate'))
            except ValueError:
                usdt_rate = 120.0
            prompt_text = f"💠 <b>{method_name}</b> বেছে নিয়েছেন।\n\nআপনি কত <b>USDT ($)</b> ডিপোজিট করতে চান? (সংখ্যায় টাইপ করুন, মিনিমাম: <b>{min_limit} USDT</b>):\n💡 <i>বর্তমান রেট: 1$ = {usdt_rate:.2f} BDT</i>"
        else:
            prompt_text = f"💠 <b>{method_name}</b> বেছে নিয়েছেন।\n\nআপনি কত টাকা ডিপোজিট করতে চান? (সংখ্যায় টাইপ করুন, মিনিমাম: <b>{min_limit:.2f} BDT</b>):"

        m = await context.bot.send_message(
            chat_id=user.id,
            text=pe(prompt_text),
            parse_mode="HTML"
        )
        context.user_data['last_msg_id'] = m.message_id
        return

    # Category Selection in Product Add
    if is_admin(user.id) and data.startswith('seladdcat_'):
        cat_selected = data.replace('seladdcat_', '')
        context.user_data['add_category'] = cat_selected
        context.user_data['state'] = 'add_prod_step3_price'
        await query.edit_message_text(pe(f"✅ Selected Category: <b>{cat_selected}</b>\n\n💰 এবার প্রতি পিসের <b>Price (টাকা)</b> টাইপ করে পাঠান:"), parse_mode="HTML")
        return

    # Category Management
    if is_admin(user.id) and data == 'admin_cat_mgmt':
        context.user_data.pop('state', None)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row['name'] for row in cursor.fetchall()]
        conn.close()

        keyboard = []
        for c in cats:
            keyboard.append([pbtn(f"Delete: {c}", icon="delete", style="danger", callback_data=f"del_cat_{c}")])

        keyboard.append([pbtn("Add Category", icon="new", style="success", callback_data="admin_add_cat_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "📁 <b>CATEGORY MANAGEMENT</b>\nএখান থেকে ক্যাটাগরি তৈরি বা ডিলিট করুন:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif is_admin(user.id) and data == 'admin_add_cat_prompt':
        context.user_data['state'] = 'awaiting_new_category'
        await query.edit_message_text(pe("📁 নতুন ক্যাটাগরির নাম লিখুন (যেমন: PROXY, VPN, GMAIL):"), reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_cat_mgmt")]]), parse_mode="HTML")
        return

    elif is_admin(user.id) and data.startswith('del_cat_'):
        cat_to_del = data.replace('del_cat_', '')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE name = ?", (cat_to_del,))
        conn.commit()
        
        cursor.execute("SELECT name FROM categories")
        cats = [row['name'] for row in cursor.fetchall()]
        conn.close()

        keyboard = []
        for c in cats:
            keyboard.append([pbtn(f"Delete: {c}", icon="delete", style="danger", callback_data=f"del_cat_{c}")])

        keyboard.append([pbtn("Add Category", icon="new", style="success", callback_data="admin_add_cat_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "📁 <b>CATEGORY MANAGEMENT</b>\nএখান থেকে ক্যাটাগরি তৈরি বা ডিলিট করুন:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        await query.answer(f"Category {cat_to_del} ডিলিট করা হয়েছে!", show_alert=False)
        return

    # Dynamic Payment Settings Menu (Admin Panel)
    if is_admin(user.id) and data == 'admin_set_payment':
        context.user_data.pop('state', None)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, number_or_address, min_deposit, icon_key FROM payment_methods")
        p_methods = cursor.fetchall()
        conn.close()

        keyboard = []
        msg_details = ""
        for p in p_methods:
            p_name = p['name']
            p_num = p['number_or_address']
            p_min = p['min_deposit']
            unit_txt = "USDT" if 'binance' in p_name.lower() else "BDT"
            
            msg_details += f"🔹 <b>{p_name}:</b> <code>{p_num}</code> (Min: {p_min} {unit_txt})\n"
            keyboard.append([pbtn(f"Delete {p_name}", icon="delete", style="danger", callback_data=f"del_pay_{p_name}")])

        keyboard.append([pbtn("Add / Update Payment Method", icon="new", style="success", callback_data='add_pay_prompt')])
        keyboard.append([pbtn("Back to GX Control", icon="back", callback_data='admin_gx_control')])

        msg = f"⚙️ <b>PAYMENT SETTINGS</b>\n\n{msg_details}\n💡 যেকোনো পেমেন্ট মেথড তৈরি করতে বা লিমিট আপডেট করতে নিচের বাটনে চাপ দিন."
        await query.edit_message_text(pe(msg), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif is_admin(user.id) and data == 'add_pay_prompt':
        context.user_data['state'] = 'add_pay_step1_name'
        await query.edit_message_text(pe("💳 পেমেন্ট মেথডের নাম লিখুন (যেমন: bKash, Nagad, Rocket, Upay, Binance):"), reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_set_payment")]]), parse_mode="HTML")
        return

    elif is_admin(user.id) and data.startswith('del_pay_'):
        pay_to_del = data.replace('del_pay_', '')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM payment_methods WHERE name = ?", (pay_to_del,))
        conn.commit()

        cursor.execute("SELECT name, number_or_address, min_deposit, icon_key FROM payment_methods")
        p_methods = cursor.fetchall()
        conn.close()

        keyboard = []
        msg_details = ""
        for p in p_methods:
            p_name = p['name']
            p_num = p['number_or_address']
            p_min = p['min_deposit']
            unit_txt = "USDT" if 'binance' in p_name.lower() else "BDT"
            
            msg_details += f"🔹 <b>{p_name}:</b> <code>{p_num}</code> (Min: {p_min} {unit_txt})\n"
            keyboard.append([pbtn(f"Delete {p_name}", icon="delete", style="danger", callback_data=f"del_pay_{p_name}")])

        keyboard.append([pbtn("Add / Update Payment Method", icon="new", style="success", callback_data='add_pay_prompt')])
        keyboard.append([pbtn("Back to GX Control", icon="back", callback_data='admin_gx_control')])

        msg = f"⚙️ <b>PAYMENT SETTINGS</b>\n\n{msg_details}\n💡 যেকোনো পেমেন্ট মেথড তৈরি করতে বা লিমিট আপডেট করতে নিচের বাটনে চাপ দিন."
        await query.edit_message_text(pe(msg), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        await query.answer(f"Payment Method {pay_to_del} ডিলিট করা হয়েছে!", show_alert=False)
        return

    elif is_admin(user.id) and data == 'admin_set_ref':
        context.user_data['state'] = 'awaiting_ref_bonus'
        await query.edit_message_text(
            pe(
                "🎁 নতুন ইউজার আপনার referral link দিয়ে join করলে "
                "referrer-কে একবারে কত fixed bonus (BDT) দেবেন লিখুন। "
                "0 দিলে bonus বন্ধ থাকবে।"
            ),
            reply_markup=InlineKeyboardMarkup([[
                pbtn("Cancel", icon="close", style="danger", callback_data="admin_gx_control")
            ]]),
            parse_mode="HTML",
        )
        return

    # Product Buy Category Navigation
    if data.startswith('buycat_'):
        cat_name = data.replace('buycat_', '')
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, price FROM products WHERE category = ? GROUP BY title", (cat_name,))
        items = cursor.fetchall()

        keyboard = []
        for i in items:
            cursor.execute("SELECT COUNT(*) as stock FROM products WHERE title = ? AND category = ?", (i['title'], cat_name))
            stock_count = cursor.fetchone()['stock']
            
            icon_key = get_product_icon_key(i['title'])
            
            keyboard.append([
                pbtn(
                    f"{i['title']} · {i['price']:.2f} BDT ({stock_count} Stock)",
                    icon=icon_key,
                    style="danger",
                    callback_data=f"itemselect_{i['id']}"
                )
            ])
        conn.close()

        keyboard.append([pbtn("Back", icon="back", callback_data="back_to_cats")])

        if not items:
            await query.edit_message_text(pe(f"❌ <b>{cat_name}</b> ক্যাটাগরিতে বর্তমানে কোনো স্টক নেই!"), reply_markup=InlineKeyboardMarkup([[pbtn("Back", icon="back", callback_data="back_to_cats")]]), parse_mode="HTML")
            return

        await query.edit_message_text(pe(f"🛍️ <b>{cat_name} ক্যাটাগরির প্রোডাক্টসমূহ:</b>"), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data == "back_to_cats":
        await render_categories_menu(query)
        return

    elif data.startswith('itemselect_'):
        p_id = int(data.split('_')[1])
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT category, title, price FROM products WHERE id = ?", (p_id,))
        res = cursor.fetchone()

        if not res:
            await query.answer("❌ প্রোডাক্টটি পাওয়া যায়নি!", show_alert=True)
            conn.close()
            return

        title = res['title']
        cat_name = res['category']
        price = res['price']

        cursor.execute("SELECT COUNT(*) as stock FROM products WHERE title = ? AND category = ?", (title, cat_name))
        stock_res = cursor.fetchone()
        stock = stock_res['stock'] if stock_res else 0

        conn.close()

        if stock == 0:
            await query.answer("❌ প্রোডাক্টটি আউট অফ স্টক!", show_alert=True)
            return

        context.user_data['buy_cat'] = cat_name
        context.user_data['buy_pid'] = p_id
        context.user_data['buy_qty'] = 1

        msg = (
            f"🏷️ <b>{title}</b>\n"
            f"💎 প্রাইস: {price:.2f} BDT\n"
            f"📦 স্টক: {stock}\n\n"
            f"<b>পরিমাণ:</b> 1\n"
            f"<b>মোট:</b> 💎 {price:.2f} BDT"
        )
        await query.edit_message_text(pe(msg), reply_markup=build_quantity_keyboard(1), parse_mode="HTML")
        return

    # Quantity Selection Buttons
    if data in ['qty_plus', 'qty_minus', 'qty_custom', 'qty_cancel', 'qty_confirm', 'qty_noop']:
        p_id = context.user_data.get('buy_pid')
        qty = context.user_data.get('buy_qty', 1)

        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT category, title, price FROM products WHERE id = ?", (p_id,))
        res = cursor.fetchone()

        if not res:
            await query.edit_message_text(pe("❌ প্রোডাক্টটি পাওয়া যায়নি!"), parse_mode="HTML")
            conn.close()
            return

        price = res['price']
        title = res['title']
        cat_name = res['category']

        cursor.execute("SELECT COUNT(*) as stock FROM products WHERE title = ? AND category = ?", (title, cat_name))
        stock_res = cursor.fetchone()
        stock = stock_res['stock'] if stock_res else 0
        conn.close()

        if stock == 0:
            await query.edit_message_text(pe("❌ এই প্রোডাক্টটি বর্তমানে স্টক আউট!"), parse_mode="HTML")
            return

        if data == 'qty_plus':
            if qty < stock:
                qty += 1
                context.user_data['buy_qty'] = qty
            else:
                await query.answer(f"স্টকে সর্বোচ্চ {stock} টি আছে!", show_alert=True)
                return

        elif data == 'qty_minus':
            if qty > 1:
                qty -= 1
                context.user_data['buy_qty'] = qty
            else:
                await query.answer("সর্বনিম্ন ১ টি নিতে হবে!", show_alert=True)
                return

        elif data == 'qty_custom':
            context.user_data['state'] = 'awaiting_custom_qty'
            await query.message.delete()
            m = await context.bot.send_message(chat_id=user.id, text=pe(f"🔢 কত পিস নিতে চান? সংখ্যা টাইপ করুন (সর্বোচ্চ স্টক: {stock}):"), parse_mode="HTML")
            context.user_data['last_msg_id'] = m.message_id
            return

        elif data == 'qty_cancel':
            context.user_data.clear()
            await query.edit_message_text(pe("❌ অর্ডার বাতিল করা হয়েছে।"), parse_mode="HTML")
            return

        elif data == 'qty_confirm':
            total_price = price * qty
            db_user = get_or_create_user(
                user.id, user.first_name,
                username=getattr(user, "username", "") or "",
            )

            purchase = complete_product_purchase(
                user.id, title, cat_name, qty, price
            )
            if purchase["status"] == "insufficient_balance":
                current_balance = purchase.get("balance", db_user["balance"])
                await query.edit_message_text(
                    pe(
                        f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই!\n\n"
                        f"প্রয়োজন: {total_price:.2f} BDT\n"
                        f"আপনার ব্যালেন্স: {current_balance:.2f} BDT"
                    ),
                    parse_mode="HTML",
                )
                return
            if purchase["status"] == "out_of_stock":
                await query.edit_message_text(pe("❌ পর্যাপ্ত স্টক নেই!"), parse_mode="HTML")
                return
            if purchase["status"] != "ok":
                await query.edit_message_text(
                    pe("❌ ক্রয় সম্পন্ন করা যায়নি। কিছুক্ষণ পর আবার চেষ্টা করুন।"),
                    parse_mode="HTML",
                )
                return

            total_price = purchase["total_price"]
            today = purchase["date"]

            await query.edit_message_text(
                pe(f"🎉 <b>ক্রয় সফল হয়েছে!</b>\n\n"
                f"📦 <b>প্রোডাক্ট:</b> {title}\n"
                f"🔢 <b>পরিমাণ:</b> {qty} পিস\n"
                f"💰 <b>মোট মূল্য:</b> {total_price:.2f} BDT\n\n"
                "ডাটা নেওয়ার পদ্ধতি বেছে নিন:"),
                reply_markup=InlineKeyboardMarkup([
                    [pbtn(
                        "Copy values",
                        icon="note",
                        callback_data=f"purchase_copy_{purchase['order_ref']}",
                    )],
                    [pbtn(
                        "CSV file",
                        icon="folder",
                        callback_data=f"purchase_csv_{purchase['order_ref']}",
                    )],
                ]),
                parse_mode="HTML"
            )

            log_group_id = get_setting('log_group_id')
            if log_group_id:
                try:
                    group_msg = (
                        f"🛒 <b>NEW PURCHASE NOTIFICATION!</b>\n\n"
                        f"👤 <b>Buyer:</b> {user.first_name} (<code>{user.id}</code>)\n"
                        f"📦 <b>Product:</b> {title}\n"
                        f"📁 <b>Category:</b> {cat_name}\n"
                        f"🔢 <b>Quantity:</b> {qty} Pcs\n"
                        f"💰 <b>Total Paid:</b> {total_price:.2f} BDT\n"
                        f"📅 <b>Time:</b> {today}"
                    )
                    await context.bot.send_message(chat_id=log_group_id, text=pe(group_msg), parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Failed to send log to group: {e}")

            context.user_data.clear()
            return

        total = price * qty
        msg = (
            f"🏷️ <b>{title}</b>\n"
            f"💎 প্রাইস: {price:.2f} BDT\n"
            f"📦 স্টক: {stock}\n\n"
            f"<b>পরিমাণ:</b> {qty}\n"
            f"<b>মোট:</b> 💎 {total:.2f} BDT"
        )
        await query.edit_message_text(pe(msg), reply_markup=build_quantity_keyboard(qty), parse_mode="HTML")
        return

    # Admin Management Callbacks
    if is_admin(user.id) and data == 'admin_mgmt':
        context.user_data.pop('state', None)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM admins")
        admins = [row['user_id'] for row in cursor.fetchall()]
        conn.close()

        keyboard = []
        for aid in admins:
            if aid == SUPER_ADMIN_ID:
                keyboard.append([pbtn(f"Owner: {aid}", icon="king", callback_data="noop")])
            else:
                keyboard.append([pbtn(f"Delete: {aid}", icon="delete", style="danger", callback_data=f"del_admin_{aid}")])

        keyboard.append([pbtn("Add Admin", icon="new", style="success", callback_data="admin_add_admin_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "👤 <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif is_admin(user.id) and data.startswith("del_admin_"):
        del_id = int(data.split('_')[2])
        if del_id == SUPER_ADMIN_ID:
            await query.answer("অনারকে ডিলিট করা সম্ভব নয়!", show_alert=True)
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (del_id,))
        conn.commit()
        
        cursor.execute("SELECT user_id FROM admins")
        admins = [row['user_id'] for row in cursor.fetchall()]
        conn.close()

        keyboard = []
        for aid in admins:
            if aid == SUPER_ADMIN_ID:
                keyboard.append([pbtn(f"Owner: {aid}", icon="king", callback_data="noop")])
            else:
                keyboard.append([pbtn(f"Delete: {aid}", icon="delete", style="danger", callback_data=f"del_admin_{aid}")])

        keyboard.append([pbtn("Add Admin", icon="new", style="success", callback_data="admin_add_admin_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "👤 <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        await query.answer(f"Admin {del_id} রিমুভ করা হয়েছে!", show_alert=False)
        return

    elif is_admin(user.id) and data == "admin_add_admin_prompt":
        context.user_data['state'] = 'awaiting_new_admin_id'
        await query.edit_message_text(pe("👑 নতুন অ্যাডমিনের <b>Telegram User ID</b> লিখুন:"), reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_mgmt")]]), parse_mode="HTML")
        return

    # Force Join Callbacks
    if is_admin(user.id) and data == 'admin_fj_sys':
        context.user_data.pop('state', None)
        status = get_setting('force_join_status')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM channels")
        channels = [row['username'] for row in cursor.fetchall()]
        conn.close()

        status_text = "STATUS: ON" if status == 'ON' else "STATUS: OFF"
        status_style = "success" if status == 'ON' else "danger"
        status_icon = "done" if status == 'ON' else "warn"
        keyboard = [
            [pbtn(status_text, icon=status_icon, style=status_style, callback_data="toggle_fj_status")]
        ]
        for ch in channels:
            keyboard.append([pbtn(f"Delete: {ch}", icon="delete", style="danger", callback_data=f"del_channel_{ch}")])

        keyboard.append([pbtn("Add Channel", icon="new", style="success", callback_data="admin_add_channel_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "🔗 <b>FORCE JOIN SYSTEM</b>\nManage channels below:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif is_admin(user.id) and data == "toggle_fj_status":
        curr = get_setting('force_join_status')
        new_st = 'OFF' if curr == 'ON' else 'ON'
        set_setting('force_join_status', new_st)
        with _force_join_cache_lock:
            _force_join_cache.clear()
        
        status = get_setting('force_join_status')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM channels")
        channels = [row['username'] for row in cursor.fetchall()]
        conn.close()

        status_text = "STATUS: ON" if status == 'ON' else "STATUS: OFF"
        status_style = "success" if status == 'ON' else "danger"
        status_icon = "done" if status == 'ON' else "warn"
        keyboard = [
            [pbtn(status_text, icon=status_icon, style=status_style, callback_data="toggle_fj_status")]
        ]
        for ch in channels:
            keyboard.append([pbtn(f"Delete: {ch}", icon="delete", style="danger", callback_data=f"del_channel_{ch}")])

        keyboard.append([pbtn("Add Channel", icon="new", style="success", callback_data="admin_add_channel_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "🔗 <b>FORCE JOIN SYSTEM</b>\nManage channels below:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        await query.answer(f"Force Join {new_st} করা হয়েছে!", show_alert=False)
        return

    elif is_admin(user.id) and data.startswith("del_channel_"):
        ch_name = data.replace('del_channel_', '')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channels WHERE username = ?", (ch_name,))
        conn.commit()
        with _force_join_cache_lock:
            _force_join_cache.clear()
        
        status = get_setting('force_join_status')
        cursor.execute("SELECT username FROM channels")
        channels = [row['username'] for row in cursor.fetchall()]
        conn.close()

        status_text = "STATUS: ON" if status == 'ON' else "STATUS: OFF"
        status_style = "success" if status == 'ON' else "danger"
        status_icon = "done" if status == 'ON' else "warn"
        keyboard = [
            [pbtn(status_text, icon=status_icon, style=status_style, callback_data="toggle_fj_status")]
        ]
        for ch in channels:
            keyboard.append([pbtn(f"Delete: {ch}", icon="delete", style="danger", callback_data=f"del_channel_{ch}")])

        keyboard.append([pbtn("Add Channel", icon="new", style="success", callback_data="admin_add_channel_prompt")])
        keyboard.append([pbtn("Back", icon="back", callback_data="back_admin_panel")])

        text = "🔗 <b>FORCE JOIN SYSTEM</b>\nManage channels below:"
        await query.edit_message_text(pe(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        await query.answer("চ্যানেল ডিলিট হয়েছে!", show_alert=False)
        return

    elif is_admin(user.id) and data == "admin_add_channel_prompt":
        context.user_data['state'] = 'awaiting_add_channel'
        await query.edit_message_text(
            pe(
                "🔗 Public channel: <code>@channelname</code> বা "
                "<code>https://t.me/channelname</code>\n\n"
                "Private channel হলে bot admin থাকা অবস্থায় "
                "<code>-1001234567890 | https://t.me/+invite</code> দিন। "
                "Invite link একা দিলে membership verify করা যায় না."
            ),
            reply_markup=InlineKeyboardMarkup([[
                pbtn("Cancel", icon="close", style="danger", callback_data="admin_fj_sys")
            ]]),
            parse_mode="HTML",
        )
        return

    elif is_admin(user.id) and data == "back_admin_panel":
        context.user_data.pop('state', None)
        await send_admin_panel(update)
        return

    elif is_admin(user.id) and data == 'admin_add_prod':
        context.user_data['state'] = 'add_prod_step1_name'
        await query.edit_message_text(pe("📦 <b>Step 1:</b> প্রোডাক্টের <b>Name / Title</b> টাইপ করে পাঠান:"), reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="back_admin_panel")]]), parse_mode="HTML")
        return

    elif is_admin(user.id) and data == 'admin_set_supp':
        context.user_data['state'] = 'awaiting_support_link'
        await query.edit_message_text(pe("💬 নতুন <b>Support Username / Link</b> পাঠান:"), reply_markup=InlineKeyboardMarkup([[pbtn("Cancel", icon="close", style="danger", callback_data="admin_gx_control")]]), parse_mode="HTML")
        return

    # Deposit Approval Callbacks
    if is_admin(user.id) and (data.startswith('appdep_') or data.startswith('rejdep_')):
        is_approve = data.startswith('appdep_')
        deposit_id = int(data.split('_')[1])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT user_id, amount, method, trx_id, status FROM deposits WHERE id = ?", (deposit_id,))
        dep = cursor.fetchone()

        if not dep:
            await query.answer("❌ ডিপোজিট রেকর্ড পাওয়া যায়নি!", show_alert=True)
            conn.rollback()
            conn.close()
            return

        if dep['status'] != 'pending':
            await query.answer("⚠️ এই ডিপোজিটটি ইতিমধ্যেই প্রসেস করা হয়েছে!", show_alert=True)
            conn.rollback()
            conn.close()
            return

        target_user = dep['user_id']
        amount = dep['amount']
        method = dep['method']
        trx_id = dep['trx_id']

        if is_approve:
            cursor.execute("UPDATE deposits SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?", (user.id, datetime.now(), deposit_id))
            conn.commit()

            update_balance(target_user, amount)

            cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (target_user,))
            user_info = cursor.fetchone()
            target_name = user_info['first_name'] if user_info else "User"

            conn.close()

            await query.answer("✅ Deposit approved!", show_alert=True)
            review_text = (
                f"✅ <b>Approved by {user.first_name}!</b>\n\n"
                f"👤 User: <code>{target_user}</code>\n"
                f"💰 Amount: {amount:.2f} BDT"
            )
            if query.message.photo:
                await query.edit_message_caption(
                    caption=pe(review_text),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(pe(review_text), parse_mode="HTML")

            try:
                await context.bot.send_message(chat_id=target_user, text=pe(f"🎉 <b>আপনার ডিপোজিট সফল হয়েছে!</b>\n💠 ব্যালেন্সে যোগ হয়েছে: {amount:.2f} BDT"), parse_mode="HTML")
            except Exception:
                pass

            group_msg = (
                f"💠 <b>NEW SUCCESSFUL DEPOSIT!</b>\n\n"
                f"👤 <b>User:</b> {target_name} (<code>{target_user}</code>)\n"
                f"💠 <b>Method:</b> {method}\n"
                f"💰 <b>Amount:</b> {amount:.2f} BDT\n"
                f"🧾 <b>TrxID:</b> <code>{trx_id}</code>\n"
                f"📅 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            if not await send_deposit_notification(context, group_msg):
                log_group_id = get_setting('log_group_id')
                if log_group_id:
                    try:
                        await context.bot.send_message(
                            chat_id=log_group_id,
                            text=pe(group_msg),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logging.error(f"Failed to send deposit log to group: {e}")

        else:
            cursor.execute("UPDATE deposits SET status = 'rejected', approved_by = ?, approved_at = ? WHERE id = ?", (user.id, datetime.now(), deposit_id))
            conn.commit()
            conn.close()

            await query.answer("❌ Deposit rejected!", show_alert=True)
            review_text = f"❌ <b>Rejected by {user.first_name}!</b>"
            if query.message.photo:
                await query.edit_message_caption(
                    caption=pe(review_text),
                    parse_mode="HTML",
                )
            else:
                await query.edit_message_text(pe(review_text), parse_mode="HTML")

            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text=pe("❌ SORRY DEAR আপনার ডিপোজিট রিজেক্ট করা হয়েছে, দয়া করে সব ঠিকঠাক ডিটেইলস দিন।"),
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Failed to send rejection message to user: {e}")

        return

# ==================== Render / UptimeRobot Health Server ====================
health_app = Flask(__name__)


@health_app.get("/")
def health_home():
    return jsonify({"status": "ok", "service": "gx-shop-bot"})


@health_app.get("/health")
def health_check():
    return jsonify({"status": "ok"})


def run_health_server():
    port = int(os.getenv("PORT", "8080"))
    health_app.run(host="0.0.0.0", port=port, use_reloader=False)


# ==================== Main Runner ====================

if __name__ == '__main__':
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env variable সেট করা হয়নি।")
    if SUPER_ADMIN_ID <= 0:
        raise RuntimeError("SUPER_ADMIN_ID env variable সেট করা হয়নি।")

    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_deposit_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🚀 Bot is running with local SQLite database.")
    app.run_polling(drop_pending_updates=True)
