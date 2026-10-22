import os
import base64
import atexit
import requests
import time
import json
import hashlib
import shutil
import uuid
import threading
import random
import re
import html
import pyotp
import csv
import io
import zipfile
import copy
import math
import unicodedata
import signal
import zlib
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import Counter 
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urljoin, urlparse

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# ==========================================
# ==========================================
# PREMIUM LOADING EMOJIS
# ==========================================
GET_NUMBER_EMOJI_ID = "6224284210434154938"
APP_PHONE_EMOJI_ID = GET_NUMBER_EMOJI_ID
MESSAGE_SMS_EMOJI_ID = "6224339349224300713"
OTP_GROUP_EMOJI_ID = "6221761819090887073"
TWO_FA_BUTTON_EMOJI_ID = "6224513742076388019"
FORCE_JOIN_BUTTON_EMOJI_ID = "6224353952113108803"
REFERRAL_EMOJI_ID = "6224058651636672676"
GIFT_BOX_EMOJI_ID = "6222224537392522359"
LEGACY_GIFT_BOX_EMOJI_ID = "5420396762189831222"
WITHDRAWAL_EMOJI_ID = "6222028867272451005"
WITHDRAWAL_METHOD_EMOJI_IDS = {
    "bkash": "6224332172333949565",
    "nagad": "6224022445062365570",
    "rocket": "6224089523861595570",
    "roket": "6224089523861595570",
    "binance": "6222248761008070866",
    "binamce": "6222248761008070866",
    "upay": "5228781228685036863",
}
RELOAD_RESTART_RESET_LOADING_EMOJI_ID = "6224205341949698044"
LOADING_EMOJI_ID = RELOAD_RESTART_RESET_LOADING_EMOJI_ID
COUNTRY_LOADING_EMOJI_ID = RELOAD_RESTART_RESET_LOADING_EMOJI_ID
LANGUAGE_EMOJI_ID = "6224383737711305101"
RESTART_EMOJI_ID = RELOAD_RESTART_RESET_LOADING_EMOJI_ID
NUMBER_SUCCESS_EMOJI_ID = "6224038684333711964"
ALLOCATED_CHECK_EMOJI_ID = "6201914938424827608"
CROSS_CANCEL_EMOJI_ID = "6224003980997962148"
BACK_BUTTON_EMOJI_ID = "6220017972174398857"
MAIN_MENU_EMOJI_ID = "5278702045883292456"
PREMIUM_DIGIT_EMOJI_IDS = {
    "1": "6224428190622821133",
    "2": "6222155319699582400",
    "3": "6224377630267810997",
    "4": "6224380812838577611",
    "5": "6223976935588896776",
    "6": "6224374705395081252",
    "7": "6224064724720427998",
    "8": "6224427619392168915",
    "9": "6224369220721845258",
    "0": "6224183463386292700",
}
OTP_WORK_SERVICE_EMOJI_ID = TWO_FA_BUTTON_EMOJI_ID
WELCOME_HAND_EMOJI_ID = "6224462498821579450"
WELCOME_PERSON_EMOJI_ID = "6224447423486371495"
WELCOME_CHECK_EMOJI_ID = "6219797305344665322"
#
EMOJI_1 = LOADING_EMOJI_ID
EMOJI_2 = LOADING_EMOJI_ID
UPLOAD_EMOJI_ID = "6224124059693622546"
#
_loading_animation_lock = threading.RLock()
_loading_animation_events = {}


def _animate_fetching_message(chat_id, message_id, stop_event):
    """Animate the number-fetch status without blocking the provider request."""
    frames = ["⟳", "◐", "◑", "◒", "◓"]
    dots = ["", ".", "..", "..."]
    index = 0
    while not stop_event.wait(1.0):
        frame = frames[index % len(frames)]
        suffix = dots[index % len(dots)]
        try:
            edit_message(
                chat_id,
                message_id,
                f'<tg-emoji emoji-id="{COUNTRY_LOADING_EMOJI_ID}">{frame}</tg-emoji> '
                f"<b>Getting Number{suffix}</b>",
            )
        except Exception:
            pass
        index += 1


def _stop_fetching_animation(chat_id, message_id):
    if not message_id:
        return
    with _loading_animation_lock:
        stop_event = _loading_animation_events.pop((chat_id, message_id), None)
    if stop_event:
        stop_event.set()


def _finish_existing_fetching_animation(chat_id, message_id, started_at,
                                        minimum_duration=0.0):
    _stop_fetching_animation(chat_id, message_id)
    remaining = minimum_duration - (time.monotonic() - started_at)
    if remaining > 0:
        time.sleep(remaining)


def loading_html(text):
    """Prefix any loading message with the requested premium emoji."""
    return f'<tg-emoji emoji-id="{LOADING_EMOJI_ID}">⏳</tg-emoji> {text}'

def show_loading(chat_id, msg_id=None):
    if not msg_id:
        msg = send_message(chat_id, render_body_text(loading_html("<b>Fetching number...</b>")))
        msg_id = msg.get("result", {}).get("message_id")
    elif msg_id:
        try:
            edit_message(
                chat_id,
                msg_id,
                render_body_text(loading_html("<b>Fetching number...</b>")),
            )
        except Exception:
            pass
    return msg_id


def start_premium_reveal(chat_id, old_msg_id=None):
    """Do not show the old single-emoji reveal animation.

    The old flow sent a standalone custom emoji when the fetching text was
    unavailable.  That made users see one unexplained emoji, so the fetching
    message is now the only loading indicator.
    """
    return None, time.monotonic()


def finish_premium_reveal(chat_id, reveal_id, reveal_started_at,
                           minimum_duration=3.0):
    """Compatibility no-op for the removed single-emoji reveal."""
    return


def start_fetching_loading(chat_id):
    """Show the old Fetching number loading message as a real custom emoji."""
    text = "⏳ Fetching number..."
    result = api_call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "entities": [
            {
                "type": "custom_emoji",
                "offset": 0,
                "length": 1,
                "custom_emoji_id": LOADING_EMOJI_ID
            },
            {
                "type": "bold",
                "offset": 2,
                "length": 18
            }
        ],
        "disable_web_page_preview": True
    })
    if result and result.get("ok") and result.get("result"):
        loading_id = result.get("result", {}).get("message_id")
        if loading_id:
            stop_event = threading.Event()
            with _loading_animation_lock:
                _loading_animation_events[(chat_id, loading_id)] = stop_event
            threading.Thread(
                target=_animate_fetching_message,
                args=(chat_id, loading_id, stop_event),
                daemon=True,
            ).start()
        return loading_id, time.monotonic()

    # Keep the first loading stage visible even on clients/API versions that
    # reject the custom entity.
    fallback = api_call("sendMessage", {
        "chat_id": chat_id,
        "text": "Fetching number...",
        "disable_web_page_preview": True
    })
    loading_id = fallback.get("result", {}).get("message_id") if fallback else None
    if loading_id:
        stop_event = threading.Event()
        with _loading_animation_lock:
            _loading_animation_events[(chat_id, loading_id)] = stop_event
        threading.Thread(
            target=_animate_fetching_message,
            args=(chat_id, loading_id, stop_event),
            daemon=True,
        ).start()
    return (
        loading_id,
        time.monotonic()
    )


def finish_fetching_loading(chat_id, loading_id, started_at,
                            minimum_duration=0.0):
    """Remove Fetching number as soon as the requested work finishes."""
    try:
        remaining = minimum_duration - (time.monotonic() - started_at)
        if remaining > 0:
            time.sleep(remaining)
        if loading_id:
            _stop_fetching_animation(chat_id, loading_id)
            delete_message(chat_id, loading_id)
    except Exception:
        pass


def finish_combined_loading(chat_id, fetching_id, reveal_id,
                            reveal_started_at, minimum_duration=3.0):
    """Remove the fetching message after number selection finishes."""
    try:
        if fetching_id:
            _stop_fetching_animation(chat_id, fetching_id)
            delete_message(chat_id, fetching_id)
    except Exception:
        pass
# Configuration (Token & Owner ID)
# ==========================================
TOKEN = "8769195746:AAHDc94PpsqwLwXYlS56BlECW77nPGgADmk"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
FILE_URL = f"https://api.telegram.org/file/bot{TOKEN}/"
OWNER_ID = 8857400259
ALL_ADMIN_IDS = [8857400259, 8857400259]
BOT_USERNAME = "GX_SMS_BOT"
BOT_DATA_NAMESPACE = hashlib.sha256((TOKEN.partition(":")[0] or "unconfigured").encode("utf-8")).hexdigest()[:16]
# The bot ID (the part before ":") stays stable when Telegram rotates a token,
# so the storage namespace remains stable as long as the same bot is used.
# Prefer BOT_DATA_DIR pointing to a persistent-volume mount in production.
_BOT_DATA_DIR_CONFIGURED = bool(os.getenv("BOT_DATA_DIR", "").strip())
# Use a script-relative default so a launcher changing its working directory
# does not silently select a different empty database on the next restart.
# BOT_DATA_DIR should still point at a persistent-volume mount in production.
_BOT_CODE_DIR = os.path.dirname(os.path.abspath(__file__))
_BOT_SCRIPT_DATA_DIR = os.path.abspath(
    os.path.join(_BOT_CODE_DIR, "bot_data", BOT_DATA_NAMESPACE)
)
_BOT_CWD_DATA_DIR = os.path.abspath(
    os.path.join(os.getcwd(), "bot_data", BOT_DATA_NAMESPACE)
)
_BOT_DEFAULT_DATA_DIR = _BOT_SCRIPT_DATA_DIR


def _has_existing_bot_database(directory):
    """Detect this bot's JSON store and backups without creating directories."""
    try:
        names = os.listdir(directory)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise RuntimeError(
            f"Cannot inspect bot data directory {directory!r}: {exc}"
        ) from exc
    return any(
        name in {
            "users.json", "users.json.bak",
            "withdraw_requests.json", "withdraw_requests.json.bak",
            "activity_logs.json", "activity_logs.json.bak",
            "settings.json", "settings.json.bak",
            "runtime_state.json", "runtime_state.json.bak",
        }
        or (
            name.startswith("gx_")
            and (name.endswith(".json") or name.endswith(".json.bak"))
        )
        for name in names
    )


if _BOT_DATA_DIR_CONFIGURED:
    BOT_DATA_DIR = os.path.abspath(
        os.path.expanduser(os.getenv("BOT_DATA_DIR", "").strip())
    )
    # Never choose between two stores silently, even if both contain JSON:
    # a partly populated new directory can hide a fuller old one.
    _other_existing_dirs = [
        path for path in dict.fromkeys(
            (_BOT_DEFAULT_DATA_DIR, _BOT_SCRIPT_DATA_DIR, _BOT_CWD_DATA_DIR)
        )
        if path != BOT_DATA_DIR and _has_existing_bot_database(path)
    ]
    if _other_existing_dirs:
        raise RuntimeError(
            "BOT_DATA_DIR points to "
            + repr(BOT_DATA_DIR)
            + ", but another existing GX database was found at "
            + ", ".join(repr(path) for path in _other_existing_dirs)
            + ". Check which folder contains the latest data, then point "
            "BOT_DATA_DIR to that folder; startup stopped to prevent data loss."
        )
else:
    _existing_local_dirs = [
        path for path in dict.fromkeys(
            (_BOT_DEFAULT_DATA_DIR, _BOT_SCRIPT_DATA_DIR, _BOT_CWD_DATA_DIR)
        )
        if _has_existing_bot_database(path)
    ]
    if len(_existing_local_dirs) > 1:
        raise RuntimeError(
            "Multiple existing GX database directories were found: "
            + ", ".join(repr(path) for path in _existing_local_dirs)
            + ". Set BOT_DATA_DIR to the directory containing the latest data; "
            "the bot stopped rather than choosing or overwriting one."
        )
    BOT_DATA_DIR = (
        _existing_local_dirs[0]
        if _existing_local_dirs
        else _BOT_DEFAULT_DATA_DIR
    )
BOT_NAMESPACE = BOT_DATA_NAMESPACE
os.makedirs(BOT_DATA_DIR, mode=0o700, exist_ok=True)
try:
    os.chmod(BOT_DATA_DIR, 0o700)
except OSError:
    pass

# Multiple copies of a JSON-backed bot can each load their own stale in-memory
# snapshot and overwrite newer user balances/OTP totals.  Hold an OS lock for
# the lifetime of this process so only one bot instance writes this data dir.
_BOT_INSTANCE_LOCK_HANDLE = None
_BOT_INSTANCE_LOCK_PATH = os.path.join(BOT_DATA_DIR, ".gx_bot_instance.lock")
try:
    _BOT_INSTANCE_LOCK_HANDLE = open(_BOT_INSTANCE_LOCK_PATH, "a+", encoding="utf-8")
    if fcntl is not None:
        try:
            fcntl.flock(
                _BOT_INSTANCE_LOCK_HANDLE.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            _BOT_INSTANCE_LOCK_HANDLE.close()
            _BOT_INSTANCE_LOCK_HANDLE = None
            raise RuntimeError(
                "Another GX SMS Bot process is already using this data directory "
                f"({BOT_DATA_DIR}). Stop the duplicate process before starting."
            ) from exc
    _BOT_INSTANCE_LOCK_HANDLE.seek(0)
    _BOT_INSTANCE_LOCK_HANDLE.truncate()
    _BOT_INSTANCE_LOCK_HANDLE.write(f"pid={os.getpid()}\n")
    _BOT_INSTANCE_LOCK_HANDLE.flush()
except OSError as exc:
    raise RuntimeError(
        f"Cannot create the bot instance lock in {BOT_DATA_DIR!r}: {exc}"
    ) from exc
if fcntl is None:
    print(
        "⚠️ This platform does not provide fcntl; duplicate-process protection "
        "is unavailable."
    )


if ZoneInfo:
    try:
        DATA_TZ = ZoneInfo("Asia/Dhaka")
    except Exception:
        DATA_TZ = timezone.utc
else:
    DATA_TZ = timezone.utc


def data_now():
    return datetime.now(DATA_TZ)


def data_month_key():
    return data_now().strftime("%Y-%m")


def iso_now():
    return data_now().isoformat(timespec="seconds")

# ==========================================
# Premium Emoji Database
# ==========================================
# Premium_App.txt optionally overrides service icons; country flags are bundled below.
PREMIUM_APP_SOURCE_FILE = "Premium_App.txt"
_ALLOWED_PREMIUM_APPS = {
    "facebook": ("FACEBOOK", "Facebook"),
    "instagram": ("INSTAGRAM", "Instagram"),
    "whatsapp": ("WHATSAPP", "WhatsApp"),
    "telegram": ("TELEGRAM", "Telegram"),
    "imo": ("IMO", "Imo"),
    "tiktok": ("TIKTOK", "TikTok"),
}


def _read_emoji_source_lines(filename):
    path = os.path.join(_BOT_CODE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8-sig") as source:
            return source.read().splitlines()
    except OSError as exc:
        raise RuntimeError(
            f"Required emoji source file {filename!r} is missing or unreadable. "
            "Keep it beside the bot script."
        ) from exc


def _load_supplied_premium_apps():
    allowed = {
        re.sub(r"[^a-z0-9]", "", name): (key, label)
        for name, (key, label) in _ALLOWED_PREMIUM_APPS.items()
    }
    found = {}
    for line in _read_emoji_source_lines(PREMIUM_APP_SOURCE_FILE):
        prefix, separator, json_text = line.partition("{")
        if not separator:
            continue
        try:
            record = json.loads("{" + json_text)
        except (TypeError, ValueError):
            continue
        parts = prefix.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        normalized_name = re.sub(r"[^a-z0-9]", "", parts[1].casefold())
        target = allowed.get(normalized_name)
        char = record.get("emoji")
        emoji_id = str(record.get("id", "")).strip()
        if not target or not char or not emoji_id.isdigit():
            continue
        key, label = target
        found[key] = {"char": char, "id": emoji_id, "name": label}

    # TikTok uses the emoji explicitly supplied for this bot, even when an
    # optional Premium_App.txt contains an older icon.
    found["TIKTOK"] = {
        "char": "🎵",
        "id": "6199644833460528959",
        "name": "TikTok",
    }

    missing = [
        label for key, label in _ALLOWED_PREMIUM_APPS.values()
        if key not in found
    ]
    if missing:
        raise RuntimeError(
            "The supplied app emoji file is missing required services: "
            + ", ".join(missing)
        )
    return {
        key: found[key]
        for key, _label in _ALLOWED_PREMIUM_APPS.values()
    }


PEM = {
    "ok": '<tg-emoji emoji-id="6224038684333711964">✅</tg-emoji>',
    "no": f'<tg-emoji emoji-id="{CROSS_CANCEL_EMOJI_ID}">❌</tg-emoji>',
    "warn": '<tg-emoji emoji-id="6199310839623721543">⚠️</tg-emoji>',
    "admin": '<tg-emoji emoji-id="5353032893096567467">📊</tg-emoji>',
    "user": '<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji>',
    "file": '<tg-emoji emoji-id="5352721946054268944">📁</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5352597830089347330">🚀</tg-emoji>',
    "graph": '<tg-emoji emoji-id="5352877703043258544">📊</tg-emoji>',
    "money": '<tg-emoji emoji-id="5348469219761626211">💸</tg-emoji>',
    "gift": f'<tg-emoji emoji-id="{GIFT_BOX_EMOJI_ID}">🎁</tg-emoji>',
    "referral": f'<tg-emoji emoji-id="{REFERRAL_EMOJI_ID}">🎁</tg-emoji>',
    "msg": f'<tg-emoji emoji-id="{MESSAGE_SMS_EMOJI_ID}">💬</tg-emoji>',
    "gear": '<tg-emoji emoji-id="5420155432272438703">⚙️</tg-emoji>',
    "link": '<tg-emoji emoji-id="5420517437885943844">🔗</tg-emoji>',
    "trash": '<tg-emoji emoji-id="6224256529369932354">🗑</tg-emoji>',
    "upload": '<tg-emoji emoji-id="6224124059693622546">📤</tg-emoji>',
    "world": '<tg-emoji emoji-id="5336972142066047577">🌐</tg-emoji>',
    "lock": '<tg-emoji emoji-id="5353022963132174959">🔐</tg-emoji>',
    "phone": f'<tg-emoji emoji-id="{APP_PHONE_EMOJI_ID}">📱</tg-emoji>',
    "num": '<tg-emoji emoji-id="5352862640592949843">🔢</tg-emoji>',
    "pin": '<tg-emoji emoji-id="5352922460897452503">📍</tg-emoji>',
    "star": '<tg-emoji emoji-id="5352552689983067014">✨</tg-emoji>',
    "hi": f'<tg-emoji emoji-id="{WELCOME_HAND_EMOJI_ID}">👋</tg-emoji>'
}

GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "😒": "5334763399299506604",
    "🖥": "5334880948259427772", "🌐": "5334590977837403844", "🌟": "5337102391244263212",
    "🕓": "5336983442125001376", "⌛": RELOAD_RESTART_RESET_LOADING_EMOJI_ID,
    "⏳": RELOAD_RESTART_RESET_LOADING_EMOJI_ID, "💬": MESSAGE_SMS_EMOJI_ID,
    "🔐": "5337255927735163754", "🍏": "5337132498965010628", "❔": "5336850036145823599",
    "⚠️": "6199310839623721543", "🔥": "5337267511261960341", "💸": "5348469219761626211",
    "🥚": "5348390922507817684", "👨‍⚖": "5334763399299506604", "🐁": "5348494358205207761",
    "🧻": "5348486915026884464", "⚗": "5346311574221000149", "🛴": "5348075478634766440",
    "📊": "5353032893096567467", "🔢": "5352862640592949843", "👤": "5352861489541714456",
    "📁": "5352721946054268944", "🚀": "5352597830089347330", "💎": "5352838545826420397",
    "📍": "5352922460897452503", "👋": WELCOME_HAND_EMOJI_ID, "✅": "6224038684333711964",
    "1️⃣": "5352651766288652742", "2️⃣": "5355186458418257716", "3️⃣": "5352867219028091093",
    "4️⃣": "5352566657216714037", "5️⃣": "5353086880835474989", "6️⃣": "5354859211975071385",
    "7️⃣": "5352859127309707652", "8️⃣": "5352957533600389988", "9️⃣": "5353060913463204207",
    "🔤": "5352727417842606016", "📣": "5352980533150259581", "📤": "6224124059693622546",
    "✨": "5352552689983067014", "🔹": "5352638632278660622", "🎙": "5355102594886833928",
    "💴": "5352985330628730418", "📅": "5352585194295564660", "📴": "5352974971167611327",
    "✏️": "5395444784611480792", "📱": APP_PHONE_EMOJI_ID, "🔗": "5420517437885943844",
    "❌": CROSS_CANCEL_EMOJI_ID, "⚙️": "5420155432272438703", "🫂": "5420145051336485498",
    "➕": "5420323438508155202", "🗑": "6224256529369932354", "🎁": GIFT_BOX_EMOJI_ID,
    "➤": "5420618897898381296", "🏢": "5420156334215565595", "💳": "5190899075968441286",
    "📝": "6222073659486381042", "🛡": "5190447043545438788", "🤝": "5192805934073685937",
    "💰": "5190576863226933563", "👀": "5190645917711114179", "🕹": "5193100774988617665",
    "🟢": "5192812028632274956", "🧪": "5190781475468915802", "🎨": "5190751148704833975",
    "📂": "5257969839313526622", "🌍": "5780471598922337683", "📌": "5318986077455795572",
    "📢": "5789428375261023681", "🆔": "5352862640592949843", "📈": "5352877703043258544",
    "🔔": "5352980533150259581", "🏦": "5348469219761626211", "🧾": "6222073659486381042",
    "👨‍⚖️": "5334763399299506604", "🔍": "5463352748751753567",
    "🔑": "5197288647275071607"
}

DEFAULT_WELCOME_TEXT = (
    f'<tg-emoji emoji-id="{WELCOME_HAND_EMOJI_ID}">👋</tg-emoji> '
    'Hello! Welcome {user_name} '
    f'<tg-emoji emoji-id="{WELCOME_PERSON_EMOJI_ID}">🙂</tg-emoji>'
    f'<tg-emoji emoji-id="{WELCOME_CHECK_EMOJI_ID}">✅</tg-emoji>'
)
LEGACY_DEFAULT_START_TEXT = (
    "╔═══════════╗\n       📊 NUMBER BOT\n╚═══════════╝\n"
    "🚀 Welcome to Number & OTP Service\n━━━━━━━━━━━━\n"
    "✅ Choose an option below\nto continue using the bot.\n"
    "━━━━━━━━━━━━\n💎 Premium OTP Service"
)
DEFAULT_CUSTOM_MESSAGES = {
    "start": {"text": DEFAULT_WELCOME_TEXT, "buttons": []},
    "get_number": {"text": f"{PEM['pin']} Select a service:", "buttons": []},
    "select_country": {
        "text": (
            '<tg-emoji emoji-id="6224281577619201977">📌</tg-emoji> '
            'Select a country for {service}:'
        ),
        "buttons": [],
    },
    "traffic": {"text": f"{PEM['graph']} <b>Traffic Overview</b>\n\n{PEM['ok']} Available Numbers: {{avail}}\n{PEM['rocket']} Assigned Numbers: {{assigned}}", "buttons": []},
    "refer": {"text": f"➖➖➖➖➖➖➖\n« {PEM['referral']} REFER & EARN »\n➖➖➖➖➖➖➖\n{PEM['link']} YOUR LINK:\n<code>{{ref_link}}</code>\n➖➖➖➖➖➖➖\n{PEM['user']} TOTAL REFERS: <b>{{total_ref}}</b>\n➖➖➖➖➖➖➖\n{PEM['money']} PER REFER: <b>{{ref_reward}} TK</b>\n➖➖➖➖➖➖➖", "buttons": []},
    "withdrawal": {
        "text": (
            '<tg-emoji emoji-id="6224024626905753921">💳</tg-emoji> '
            'WITHDRAWAL <tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>\n'
            "━━━━━━━━━━━━━━━━━━\n\n"
            '<tg-emoji emoji-id="6221761819090887073">🔔</tg-emoji> '
            'Total OTP » {total_otp} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
            '<tg-emoji emoji-id="6224492894305133331">🫂</tg-emoji> '
            'Total Reffer » {total_ref} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
            '<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
            'Available Balance » {bal} ৳ <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
            '<tg-emoji emoji-id="6224119399654105709">📉</tg-emoji> '
            'Minimum Withdraw » {min_w} ৳ <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n\n'
            "━━━━━━━━━━━━━━━━━━\n"
            '<tg-emoji emoji-id="6224024626905753921">💳</tg-emoji> '
            'Choose Your Method <tg-emoji emoji-id="6233188575286927353">⬇️</tg-emoji>'
        ),
        "buttons": [],
    },
    "support": {"text": f"{PEM['msg']} Contact us for any help:", "buttons": []}
}

# Built-in premium flag emoji catalog bundled from the supplied list.
# Stored as compressed JSON so the bot remains a single self-contained file.
_DEFAULT_PREMIUM_FLAGS_B64 = (
    "eNp1XMtyG8mV/RWENnZHyBGVmZUv70iQAikCFJsAKUu7IllNVgtA0QVAMuXwYlaznE+YiVlMe9rtttwP98OvxfzQRMwPzLmV"
    "Zeajyo6GyTDDB1mZ9557zs1b/esnVjz5+a+fXN8VzZOfP/nff//X/8Lnd0+ePqk2Nf6HvWf4dV2sSvr9k9u7Yl1ttsWa/n6D"
    "/0lyy6zQkjGJX7iUSj35zdMnQpoY9Hf4fPkI+uzYgz6r1stifRMA5llurWLMMmUzxS0B7v2iv8i/+kX+IlgkoY2ON/RjE6Fq"
    "nTNjmVZMZVK6Zco+7B897DSEvcKjFyEgz7hhFrBaqixrATlLNvO/8fn7I+DB6xDwtmxiwCw3jGueZ0pKnnMCZDHcj/h8/wh3"
    "MfdwF+tqW96M5ttiW0aPzXM8uZJC0Bpx1rSZ8/5Te9S9AHVvhTVeF+vRvFjVRXToQNbCaKszqzlrYY/7sP7M94Iz31vf7qrl"
    "MgTkzCjBhci5kBm2ogWc9AG/8ICTEHBb3e6KER39ftFc7W7ijcWTY5FCqVxblRP2frIHn0V7sB/swX5xV6yKOJQEk0YLjkDK"
    "MtYe1P5+H+8zj7cf4jVXxU0dAUqumNFMyVwz7U5+f9YH/MoDzgLAslmFD2zxoAYLk4IhQFlm280c78V4v6UNfcTDXx/xxsW6"
    "iPaPc5uJXOcy4xIH1e7fwawf6H55B8HyDupVtUYQhc+bGymZMFwybTLRPu/Biz7gNx7wRR9wPTov73dXy+o63krOrGZ5ZqS2"
    "uSboyUEM/QXBP0Ljr4/Qk6aMnh1bybnJlMhMzoCbt+z2PHn2P0TP/jx49ueInOTRZSZZpnMlreFGtEdzdh7jfYvPd494+Osj"
    "3tmubLb16Ly6rqPc4UwieExmOB0UYZ6cxpgf8Pn6ERN/fcScF9V6OzqptttNmz+n5dtqEwWTBW0a8ByXQokWfTqO0f9IAfWI"
    "jr8m6NPddRXuKuO5wA6IPBeSGd5G1GWC+ecI87KHeVmtr0v8pDVv78qRO7tqXYaLZwJrzxlSgTHFHevPk1ryfVRL5kEtmdP3"
    "zIqi2Za+4uUoTRS7mZVICJxkS36LRQz6A30eQfHXR9BFg+i9KW7ahS/qq+I2PEvsC7dC5tLI3GhXVRbjPrbfmUWwM4td88ad"
    "4hhxV2+G6qDgmVHYC2EMcrqtrpfH/a33zH0ZMPfFHPve3FbrIWRKFWEZl5qhkLWHKrTqc7jPvb2DkMNv6qaJKyyTPJNaiVyg"
    "dLf7jHLWB/Q8sfciqjL1Ms49pjTtK4esME5YyAE4n3t7Qe7tNbcIt2odMyNSjkGvSGWs4to98gCkp4e9WQi5KmNRAepCHdAy"
    "M0zlGTPtI1vdB/yLB3wZAu6uksqnswzrRKE21q1PsT7ajx7tIkDbbbZNsYxFCv7Dc2geKyABdIuYDyhIH/t7iwQxfWAUgRyV"
    "lFHMt3wI4D6gV1F7oYp6X6KaVp9GihQhLiRJCSoBmW430WrRr6e/9/X0KCr4DRgmBGSZEdZQ+PBMy1ZEGZP1AX1k7x+EgOvb"
    "ZXFTbu7CBwftKWS4VSARI7pskX3Mv3nMV2HRXxbNLko/Bjrl2EcDmma83UmU1h7e5x7vMMK7rXarcIHQy7lSGXJPSK5bJpIZ"
    "6wP6k9l/HQFW78tofaCFHMXUSPxwIgfKoo/3B4/3PMRbR2eC88itslRJlTLOdtih/fORuB9E4v7dLrYxbX3HOaAso9Kp9oxR"
    "QPp4nmz2A7LZr5fV29QfMMjNDB+pkYUOcOB5/+QBPw4B10XV+A2EUII4lJTGkMlamXaFUOB9QC/r9vdCwA24pi0OR2Xzvryt"
    "34ZkhkKPRYIsoB0lAt6pMq4G8D337L8M8bebd8U6ph/oWm3p+SEejAuhgSPyhLsfEO5+U7yvllHK4Nl5SxhcWLejaiivvdDZ"
    "Pw3xduuyCtk7w2Fb6BuuUMmtY285cELedOwHpmN/t7wtEgsHoUisyOAykDjaxbjqI3qDvf8sRGze4ExGz4pNpAlIvyhEO1Qo"
    "4Nu6hSLbR/U1e/84Qt2tb6roXEBlAsZdWKW1ajfSpAfzISLIk6PQIKyu6psk2KHlLZMK7jWDBm+XKHTfcvhCOJ5FiGVT13Fb"
    "AZSdgcigVZR1hYEL00f8s0e8DBHvy9Fl2dyUcbmGu4Rvw4bKzgxzofqY/njGwfGMUf9RD0d7nzT/1H5ADUD+5FbAxxvmjkrI"
    "vn7zlWIRVIrxXXETUTBkNzwcIKWA62zzZ2C5vmUxnoZg1TIiYC6Q1hqG1aB4uTAyA2g+e8anEVqS28oYIUCWFjU2a+uXHDhw"
    "T5fjgC7H9bJeXSXtD5ZBmIHRBU5eO7WnbD8ofQidhCFUr+omdtWCPCbiSEkIycxpqZz3l+jTezwJAdexMkfscBKRwigEj8vt"
    "VPr8Njra8UEC93S0gFM5KFf1dVNsq+vHEBrVn5CJidhYZ/ACqEhQB6aTbmZg9R/8152EX1e/GdDoRHnK4BlyBRrtilI2EASe"
    "ksfnIepmW5D9jEQw/LEhVytRNqV0SsYkMf/7CPMoxGxqbEXSXAIvKZsbCe/pHl0ObLRXreNAtY5jCQwqFqBkpDwYDyt0JD8Q"
    "qF5njQOdNX64T2QWvINGPAkLMOsUOkp9H8/LonEgi8bvy+u7hDpJqEIMaovCbjpdJPuAnt3HAbuP/+ebbTm6+cnx2xpyYfRT"
    "/GweRuO62Gw/iuRS28vIwH5ZxkRbinPZb7n4aDoIoumgXK+K5k3kpeCsUZBQiokHXDbIge6nV3MHgZo7+LS6qnfbKhZg2Ncc"
    "yga6mJtOgCWIn0fW9zCwvofXuwIGMopLrAtSCVyPVboeZXpQn0fpfxik/+Htw/023kAyexzGFs4/4y5zRL+V4OvRPKhHh8vR"
    "vFi+TZaYY3ki07DiiixkxylZv13lNeIk0IiHv9wV2xoSZDma7Kp1GTdUNVViOCsom65JyVM9+3mUlYdBVh421bYp40RC+Egq"
    "74rLToWgyvUBvcE4DAzG4WZbp15XMpaDoQ1rK5MjfNPfUZ9J89ch4Dvwxroa/XT+joQimO6jaGtxUqa1qvipugAdeH7vDw4D"
    "f3C4vavq+yo2+zloX7EWmbleErcDFx2+5D0LSt6zoqnLAUpWubLwqpmwKKZK507V2j6sz6Rnz8P7k0+rqOFlhRHw+5DbSjNH"
    "d6IP5k/9WXDqz5pifV1GkptpeED8BkP9jzTPWT9AveeYBJ5jUlzViTMHC0kD+jTgIyeP+EC8+xo/mYVwqWZAVlI3h/yQEU52"
    "wm708XxMToKYnJR1c5sAQrrR0hiECHdRk9s+q3m8gwivWRXrh4iD8LwaShCMAZLvFKfoL9Ar7UmgtCd3iaGCGoBmhyam64cu"
    "B+XA/vlaMQlqxaS6gn7dFjFLSgkJx41CfGddC2sA0QfM5DxqmJdxwKBqozQimsEV2t218NT1fhFp1sk0xkvvA1sfDemF8MNO"
    "unYOEXAP0mfyJMjkCTiyXBVxJ1AIpQSYF1HDoIlcHOZ9SK+FJ6chZEK25Ewzi0TRmoxpJzUH4tBb58nLFO9n+9VmU+yiZhvk"
    "Gmwa5IaEnXQ1xw48udcuk1ch7EMcPtT3hNvVGaJHMed/ZGb7Ss3v5FGwk0dFtY39cw6FnUmjURIM61pYtt9L9uRwGZDDUb18"
    "GM1LaJZL0sIwVONq++CuMD+KLgsY7QEo0lKh7DRr3l+1P6yj0/Br1je7JrrAYxZegy4fSGl0xh/Z2Uf0aujoJEK8HZ3gv6Jy"
    "q1ROi8UCweftUaXO8veRZj0KNOvRbn1bNA+xobbgyQyRhdh3Dy3SZvWX0aXlcXBpeXxdprfq+H8LafLMGIlIbQ8rlQNfRpt4"
    "HGzi8fomqd1CMASRzqm5465AFO+jeS90fBCh1etyEyAiIY3J27YW3EmeuTKYFtcvIx46DnjoGIXraVtcV6GrevFJvKUZRJHO"
    "4QSguVzHUA1sqRdbxx9HX/HLuJRJRBGOBwQvVNc8En00XyqOD0O03gHBpFjNNILHCuVu8ZLLjn/75v/+418+w+c/8fkOny/w"
    "+Rofr5AmwU3zy2JZJh1iC+GGqAczZy79j2f9FfviexwUX2xuSTZ1lvTamYFD5ZJnOlPd/ehh/37U78LzYBeel82mfIg1IQol"
    "6Q1qBLglWj0QWL58HE/DNTZFuYzdGgqRUlDBxkrXuRe2D+cJ7zggvONtsXyIe/YIUCww15ntWuyG9R/2W/+wZ+Fl8H08OEOd"
    "E1QhTqItz6WLR96H83ryeaAnn9fNTTKIA3aEcqFb/9xkbU7qfvvEx8pJoKZPivfFm7tktAcZQ5dRKLzcQvY79ZKS0IfodE+C"
    "0z0p1w+xJQE9SoKCK+kWqNIO1IdIvZwE6uWkaqqrIvaMpCMFVR9qabroM6ke+hCdyElwIic1LM7TsB9zVtb3y/Inm7AxE2UQ"
    "ShCDz2VCCKm6VkeS9H+NCscvTsLv29Rv67C0kRCBOIRP4VSTXAgMNGK9bjgJdMPJ7h1KclzgFVgUPzkzmbuzsXZgh73nPQk8"
    "78lDc/vwPgkClF1kJV0bwwFJ3RVL1R8A8FV+GlT5aVH7XR3ofMUBDGOQacYgKDLR3aay/jd5iz29DL9p+zYxbEJlTFF6gQGc"
    "tLVqAM8P6kwD+pyWV8U6ti84flA+A6FgV7uOghrYCl+Up/MQcFNv7+pYQZFaQN5yomSnlsXACn3VmwZVb1pdJTNkVD7afjGI"
    "gBqpbijN9AG9Ypy+igAfYl0LcceI9iykkpvKyrnow/mMnR6HcOX13bZcb7ZlFYcUdHzOlWzVg7sXEjrrw3pani5C2O3dLp3G"
    "E3k7pIMSCnWbdXqJ9yG9AJsGAmy6+1W5uqp3zW1UkTlWZSHktdHatfpMWuK/igh6FhD0rLj2ap6G22C0QKbwCYIkUxc9rA/n"
    "k3M2CeFuitticx25N2bp0gUFM4OPEbkzHimBfBURyOxliLks3lVxM5IZA+6g4TFp2vhRWR/Oh8/sVQz3sKnSCBKSRiSUVdq1"
    "zewQos/p2WWEeFO9LeMWdkbdEkPmSPNuRIIPnIqXCLNphBh7GENOHxRMCxXMxY3qo/lQnC0itG08YiI4hyeCM6KGRFsxVerY"
    "vor8/uwohGs2d8VyOTRdQ4QOYAg3mefG3bfYgYV69Tr7OEKmZtkvd2XULNKGZiM53f12g2OcD6zW08/sPMTcNdU2TURUMjAP"
    "nIGhA+o6HgMH7hNxdpFiVslkA9c0LSFR2TR3FUgOrNIPcc2CIa5Z+at4XA5nJLGVuYTQtNr1E1RqhX4X6eBngQ6eVdeNcy9PR8/K"
    "mxLl7HHwNlYLDGYG2YltzqkD2/njgUj1LmkWuKRZvbyp3+Jb/pkWoTkKlUON4B/dkajuo/t++Wwcoq+LeFsQDFQsaUA6px5VK"
    "70HAsw7xNlphHdbJ7NCguHMuIJFoMEK14s0Awfn5ePsMEJE7ShvmzqaxxQ0I8ckdYSYdCTKBjC9GpnthZhNfZ0MT2Y0uiUsy"
    "6GaXS3i6fj6V5Funr0OAd9TUzLMK3IdBlwHZcpQ5rphZjtAyj7AZmGAPRR02xKxMlJeG+SWsCAnV9VT5/p19NCnwUOfwhTHf"
    "VPShzQHrzMatufc9ZwHAH3in56HgLsm7lMp6nIi4yWoxI322DQUv45k+Gkgw0/L+yIybSBPjbzBE3PqV7Rxw/ponuBPpyHa9"
    "q5sUvpkNM+EcCbtwalC0hMPPLA/5dPXIea70euySB07MxDttr2hped3jSnZB/Xq6DRQR6cVanlxu0suAzMy0/AF1P1xUw98YC"
    "d9ypwehpC3ZSQPwHA5TV2RgSOOa8l44LG95DidJHAJu1PzhEaR8NN225gaoK8jdj+9CAHjPMk1jJSiW3q6AWnjOh94WK+vTgN"
    "9dVo374rIniOkNQkOyCEohM5NJan8TZR3L4K8e7GK7bShFwYUlkXa112gpZX828jqnQVW76x403tRBgerMtgGmz2aPZVOEX4bab"
    "WzlyHiMmgOU1vUCJsRxUACSncXYPUAnDcjZ/MIrtyQJCjWo0XZoOjWzcPT0Yvr6919VUZhzo2FA5AIS0H3vS7Mdf+LPPuc7YVfhF"
    "+Sez9LNMYow3M34qzSyb1vo6A8m4R497tiRBnZb8O3PRVql0pq7juhYAeQvXw9exUit+n4EL9OQAVc0fQnp1s5QmR9QJ+OZ0E6"
    "npURTbahxJE5NNmLvGwfXPTBvDY8C7Th2V21rO7vowH31vCR0QcFUZPLjZHmpo/pufIs4MqzOr1rQXAiiFq1LozopiUGHtjL4bN"
    "FiNdsd7cJmQslKT4hC5HqLinTUvOnKHo+DqLn4yK5rmJKwdULGkrVSneawvZrq0/LWZCW4bwN+GN7N4JLK2+Sm+k841gqpJsGr3dtlPRW"
    "/ruIl84DXjqvV6kmZvT2BBhOGam4a0Sk9yTfRaR5HpDm+W6zoSztxGaV3KjCZXBBbyRk0MbODcmBtXpSOQ9I5fwdzj9eqmXIdRJYCC7pxHE6zPOXiFVezsNXM8L3xCDXoE0tDd8YRRegnQQeuOP3lDyfhXBrHFBTrWPFlmsoeJQ2hg0VXVGzfUwfo/NFiFmPFvWqbCdhz4B9Xd2X8ZtoJFgzhpPi2nUpbdrk+T4K2PleCL+7qUZ7TZHcVLccQv9AK4EHXGFnfVSvrufhSzokhKO84tTmQJhak6NKOacu0mb0d9FBnYcHVTZXaWWnwWyEEdyacBdOPB84KW8n5uE7OeXD9V25jC8c6HVLuhDTudJA7aYheR/Ts9N8Gr5+g7pUjKYl7Fa0UnIWOadLem3dpX/a8vg+Kh/zSfROz21xXzcxIt1j5khTIhfVzXQNHI4nlXlAKvMlbNqbKukDUINCZxp8Zbu2ghkIIi8N58cxYpm+bqpRNCFnUDth2pWrmrqP6JuZ86CZOaeBy3r4tR3YVJvRSCiy9R+TXAOH5Nlu/iIEXqWviGTSGHqnA7ZF2i6SkoX+Pcqf12H+1DuwshuxTa7b3L0Gxxm5TmlqJT9EhuXkPAVt2/3x9brhpGjgUbnurjfYwLH7FJrPU9D5LrqF4bmCcMyVzWGABHexlCruzyPMwxDzPnnzhAITZojBWCnbkVHe72r6wJyGgdlUo2mxfhNfwmAHwRwKO2poirzN8wH29E2JedCUSB6X3urQdCrStC9Kdm85DISlP5h5eDA7EDD9Gs30EKG1IzjIcZeMA5njJdc8kFzzd6iS8S2baC/riNjgUtsdTAeYfhuJrvFRCFdt3zs3GYsuxDcyEaUChcjdVauBWUCvM+eBzpw/NFTPqUYMzpBn5IZocNnQDKy7cEm544eopC+Ckr4oqnfxEWVW6hwSTMACKjdnZ1Mn80M0YLZ4HuJ9WvW8TM44ttPSq7E0Td7dDA7MuXs/vXgdYq7fk0Z6OureWx9ucaHSKxqrgbiVxjo9rwY2wp/dIji7xV1RJQdH998gZkGdHgjxznpkfURfkBZBQVpUq7r52RS+KeqiMhJNUDj0on2uu9Ju+qC+IC2CgrSokzFzq1EylDE0Y6i61szAQ3s6XrwI0VDeEnZX1KZQkN//uCBgA3BedyxOwxdK19Um0Qk0n4tMJ0oybkzfDuygz/fFefyCanThjxMR9JaiaodJ3OSUTad+f4gE4mIW49E7lGl4ZtbQ+AwCJxPdFBp2tI/qbx0WlyHq22K5C4dTaCgZzggyExame60jvSX4MTrii+CIL277KhuaXVMQMnq/xcmDrI/na+RFUCMv3tALivG7HWTXsIvEm9J0LmvgTU/PmnuHvX97RMtIh6uqSf8lEpQwgt5YpDsN3ZG86S/X891FwHcXzS6x1Xh8yCOqRTTt0g37DAF6+rgI6OPi/VXZpyRqaUJ3ZdQUF3mX26Y/jeZd1mXgsi6L9a7Yxl3N3NAULZhdUcerfeoBPL+ll8GWXkKxv9+V8dghTUTStD+9QttNMpq8j+hz8TLIxcuq3OLX+I0eCCxBrwZpYgxXh5Li+7doia+CJb4qV+U6EW5W84x6Jwqn49rMWV+5+Vx8HeTi6950LssyRlMDcD30ypHDE308X8heB4XsdbW6Kq7exUKdmv5G0wQ6uKNFPLzoiyt/xIfBER/umvq+ROVFuAcmmhgcdYzh6SUDKF0p/ub/AbEhPiA="
)
_BUNDLED_PREMIUM_FLAGS_B64 = (
    "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"
    "1H0Wk9I9"
)

_ACTIVE_PREMIUM_FLAGS_B64 = (
    "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"
)

_ACTIVE_PREMIUM_FLAGS_B64 += (
    "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"
)

DEFAULT_PREMIUM_FLAGS = json.loads(
    zlib.decompress(base64.b64decode(_ACTIVE_PREMIUM_FLAGS_B64)).decode("utf-8")
)

DEFAULT_PREMIUM_APPS = {
    "FACEBOOK": {"char": "📘", "id": "6199307176016618934", "name": "Facebook"},
    "WHATSAPP": {"char": "💬", "id": "6199388041660869050", "name": "WhatsApp"},
    "TELEGRAM": {"char": "✈️", "id": "6199643171308185348", "name": "Telegram"},
    "WHATSAPP BUSINESSES": {"char": "💼", "id": "5336814486701514414", "name": "WhatsApp Businesses"},
    "IMO": {"char": "💭", "id": "6219565965521199933", "name": "Imo"},
    "INSTAGRAM": {"char": "📸", "id": "6199309233305953911", "name": "Instagram"},
    "APPLE": {"char": "🍎", "id": "5294101883051353361", "name": "Apple"},
    "GOOGLE": {"char": "🔍", "id": "5335010201005231986", "name": "Google"},
    "MICROSOFT": {"char": "🪟", "id": "6196972500513989831", "name": "Microsoft"},
    "OTHER": {"char": "📶", "id": "5305517382138112561", "name": "Other"},
    "TEAMS": {"char": "🧑‍🤝‍🧑", "id": "5334590977837403844", "name": "Teams"},
    "TIKTOK": {"char": "🎵", "id": "6199644833460528959", "name": "TikTok"},
    "BKASH": {"char": "🏦", "id": "5348469219761626211", "name": "Bkash"},
    "ROCKET": {"char": "🚀", "id": "5346042941196507141", "name": "Rocket"},
    "BYBIT": {"char": "📈", "id": "5348372939479751825", "name": "Bybit"},
    "BINANCE": {"char": "💱", "id": "5348212415077064131", "name": "Binance"},
    "MELBET": {"char": "🌟", "id": "5337102391244263212", "name": "Melbet"},
    "SNAPCHAT": {"char": "👻", "id": "5359441366554255082", "name": "Snapchat"},
    "UBER": {"char": "🚗", "id": "5298715455316303708", "name": "Uber"},
    "PAYPAL": {"char": "💵", "id": "5776103539872896061", "name": "PayPal"},
    "DISCORD": {"char": "🎬", "id": "5116246243646898866", "name": "Discord"},
    "AMAZON": {"char": "🌟", "id": "4995019580536524226", "name": "Amazon"},
    "VIBER": {"char": "💜", "id": "5463060437572528782", "name": "Viber"},
    "LINKEDIN": {"char": "💼", "id": "6224222994265279792", "name": "Linkedin"},
    "LINE": {"char": "🔒", "id": "5399818044866327279", "name": "Line"},
    "WECHAT": {"char": "💜", "id": "5782757599560602950", "name": "Wechat"},
    "TWITTER": {"char": "🐦", "id": "5215726959056662534", "name": "Twitter"},
    "REDDIT": {"char": "👽", "id": "4992421103847604984", "name": "Reddit"},
    "PINTEREST": {"char": "📌", "id": "5346103513120258857", "name": "Pinterest"},
    "TWITCH": {"char": "🎮", "id": "5233333563306301418", "name": "Twitch"},
    "ZOOM": {"char": "📹", "id": "5881799193219043268", "name": "Zoom"},
    "SIGNAL": {"char": "💬", "id": "5293998404404272267", "name": "Signal"},
    "SLACK": {"char": "💻", "id": "4994972469040251302", "name": "Slack"},
    "SKYPE": {"char": "☎️", "id": "4992613535562334989", "name": "Skype"},
    "NETFLIX": {"char": "🎥", "id": "6255738712664050133", "name": "Netflix"},
    "SPOTIFY": {"char": "🎵", "id": "5411392711146095115", "name": "Spotify"},
    "AMAZON PRIME": {"char": "📺", "id": "6111801057061374810", "name": "Amazon Prime"},
    "HOICHOI": {"char": "🍿", "id": "6104822598493801746", "name": "Hoichoi"},
    "DARAZ": {"char": "📦", "id": "5336879280578138635", "name": "Daraz"},
    "FOODPANDA": {"char": "🐼", "id": "5336879280578138635", "name": "Foodpanda"},
    "PATHAO": {"char": "🛵", "id": "5336879280578138635", "name": "Pathao"},
    "ALIEXPRESS": {"char": "🛒", "id": "5336879280578138635", "name": "AliExpress"},
    "SHOPEE": {"char": "🛍️", "id": "5336879280578138635", "name": "Shopee"},
    "PAYONEER": {"char": "💳", "id": "5336879280578138635", "name": "Payoneer"},
    "WISE": {"char": "🦉", "id": "5336879280578138635", "name": "Wise"},
    "CHATGPT": {"char": "🤖", "id": "5296516998996445955", "name": "ChatGPT"},
    "NOTION": {"char": "📓", "id": "5336879280578138635", "name": "Notion"},
    "GITHUB": {"char": "🐙", "id": "5417836094098007862", "name": "GitHub"},
    "CANVA": {"char": "🖌️", "id": "5111661409008092227", "name": "Canva"},
    "FIGMA": {"char": "🎨", "id": "5336879280578138635", "name": "Figma"},
    "UPWORK": {"char": "💼", "id": "5336879280578138635", "name": "Upwork"},
    "FIVERR": {"char": "🟢", "id": "5336879280578138635", "name": "Fiverr"},
    "YAHOO": {"char": "🌐", "id": "5336879280578138635", "name": "Yahoo"},
    "DROPBOX": {"char": "☁️", "id": "5336879280578138635", "name": "Dropbox"},
    "COURSERA": {"char": "📚", "id": "5336879280578138635", "name": "Coursera"},
    "DUOLINGO": {"char": "🗣️", "id": "5336879280578138635", "name": "Duolingo"},
}
DEFAULT_PREMIUM_APPS = (
    _load_supplied_premium_apps()
    if os.path.isfile(os.path.join(_BOT_CODE_DIR, PREMIUM_APP_SOURCE_FILE))
    else DEFAULT_PREMIUM_APPS
)

LOCKED_PREMIUM_APP_KEYS = frozenset({
    "IMO", "FACEBOOK", "INSTAGRAM", "WHATSAPP", "TELEGRAM", "TIKTOK",
})

# Durable JSON storage using the GX-prefixed local database file names.
# Standard Free Number Bot-style filenames from the previous build are read as
# legacy files and migrated to these active GX files on the next write.
_LOCAL_COLLECTION_FILES = {
    "users": "gx_users.json",
    "withdrawals": "gx_withdrawals.json",
    "history": "gx_history.json",
    "settings": "gx_settings.json",
    "runtime_state": "gx_runtime_state.json",
}
_LEGACY_LOCAL_COLLECTION_FILES = {
    "users": "users.json",
    "withdrawals": "withdraw_requests.json",
    "history": "activity_logs.json",
    "settings": "settings.json",
    "runtime_state": "runtime_state.json",
}
_runtime_collections = {}
_runtime_store_lock = threading.RLock()
_runtime_collection_persist_lock_guard = threading.Lock()
_runtime_collection_persist_locks = {}


def _local_collection_persist_lock(collection_name):
    name = str(collection_name)
    with _runtime_collection_persist_lock_guard:
        return _runtime_collection_persist_locks.setdefault(
            name, threading.RLock()
        )

class _LocalIncrement:
    def __init__(self, amount):
        self.amount = amount

class _LocalServerTimestamp:
    pass

class _LocalSentinels:
    Increment = _LocalIncrement
    SERVER_TIMESTAMP = _LocalServerTimestamp()

postgres = _LocalSentinels()


def _postgres_value(value, previous=None):
    """Resolve Firestore-style sentinels into JSON-safe local values."""
    if isinstance(value, _LocalIncrement):
        if previous is None:
            previous = 0
        elif isinstance(previous, bool):
            previous = int(previous)
        elif isinstance(previous, str):
            previous_text = previous.strip()
            if not previous_text:
                previous = 0
            else:
                try:
                    previous = int(previous_text)
                except ValueError:
                    try:
                        previous = float(previous_text)
                    except ValueError as exc:
                        raise ValueError(
                            "Cannot increment a non-numeric value in the local database."
                        ) from exc
        try:
            result = previous + value.amount
        except TypeError as exc:
            raise ValueError(
                "Cannot increment a non-numeric value in the local database."
            ) from exc
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Local database increment produced a non-finite number.")
        return result
    if isinstance(value, _LocalServerTimestamp):
        return iso_now()
    if isinstance(value, dict):
        old = previous if isinstance(previous, dict) else {}
        return {
            str(key): _postgres_value(item, old.get(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_postgres_value(item) for item in value]
    return copy.deepcopy(value)


def _local_collection_path(collection_name):
    name = str(collection_name)
    filename = _LOCAL_COLLECTION_FILES.get(name)
    if filename is None:
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "collection"
        filename = f"gx_{safe_name}.json"
    return os.path.join(BOT_DATA_DIR, filename)


def _legacy_local_collection_path(collection_name):
    filename = _LEGACY_LOCAL_COLLECTION_FILES.get(str(collection_name))
    return os.path.join(BOT_DATA_DIR, filename) if filename else None


def _fsync_directory(directory):
    """Flush directory-entry updates where the platform supports it."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        directory_fd = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        # Some filesystems do not support fsync on directories.
        pass
    finally:
        os.close(directory_fd)


def _read_local_collection_file(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        # Older versions may store collections (especially activity logs) as
        # arrays. Convert each record to the document-id keyed shape used by
        # the local database, retaining every valid record.
        records = {}
        is_history_file = os.path.basename(path) in {
            "activity_logs.json",
            "gx_history.json",
        }
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise RuntimeError(
                    f"Local database file {os.path.basename(path)} contains "
                    f"a non-object record at array index {index - 1}."
                )
            candidate = next(
                (
                    item.get(field)
                    for field in ("event_id", "request_id", "user_id", "id")
                    if item.get(field) is not None
                    and str(item.get(field)).strip()
                ),
                None,
            )
            base_id = str(candidate).strip() if candidate is not None else f"LOCAL_{index}"
            document_id = base_id
            if document_id in records:
                document_id = f"{base_id}_{index}"
                suffix = 2
                while document_id in records:
                    document_id = f"{base_id}_{index}_{suffix}"
                    suffix += 1
            record = dict(item)
            if is_history_file:
                record["event_id"] = document_id
            records[document_id] = record
        data = records
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Local database file {os.path.basename(path)} must contain a JSON object."
        )
    return data


def _restore_local_collection_backup(path, backup_path):
    """Restore a verified backup without consuming or replacing the backup."""
    directory = os.path.dirname(path)
    temporary = f"{path}.{os.getpid()}.{threading.get_ident()}.recover.tmp"
    try:
        shutil.copyfile(backup_path, temporary)
        os.chmod(temporary, 0o600)
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(directory)
    finally:
        if os.path.exists(temporary):
            try:
                os.remove(temporary)
            except OSError:
                pass


def _load_local_collection(collection_name):
    name = str(collection_name)
    with _runtime_store_lock:
        if name in _runtime_collections:
            return _runtime_collections[name]
        path = _local_collection_path(name)
        load_path = path
        legacy_path = _legacy_local_collection_path(name)
        if (
            not os.path.exists(load_path)
            and not os.path.exists(f"{load_path}.bak")
            and legacy_path
            and (
                os.path.exists(legacy_path)
                or os.path.exists(f"{legacy_path}.bak")
            )
        ):
            load_path = legacy_path
        backup_path = f"{load_path}.bak"
        if os.path.exists(load_path):
            try:
                data = _read_local_collection_file(load_path)
            except Exception as exc:
                # A previous complete version is safer than starting with an
                # empty collection. Never overwrite the unreadable file unless
                # its backup has first been validated.
                if not os.path.exists(backup_path):
                    raise RuntimeError(
                        f"Local database file {os.path.basename(load_path)} could not be read, "
                        f"and no backup exists: {exc}"
                    ) from exc
                try:
                    data = _read_local_collection_file(backup_path)
                    _restore_local_collection_backup(load_path, backup_path)
                    print(
                        f"⚠️ Recovered {os.path.basename(load_path)} from its last-good backup."
                    )
                except Exception as backup_exc:
                    raise RuntimeError(
                        f"Local database file {os.path.basename(load_path)} and its backup "
                        f"could not be read: {exc}; {backup_exc}"
                    ) from backup_exc
        elif os.path.exists(backup_path):
            try:
                data = _read_local_collection_file(backup_path)
                _restore_local_collection_backup(load_path, backup_path)
                print(
                    f"⚠️ Restored missing {os.path.basename(load_path)} from its last-good backup."
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Local database file {os.path.basename(load_path)} is missing and its "
                    f"backup could not be read: {exc}"
                ) from exc
        else:
            data = {}
        _runtime_collections[name] = data
        return data


def _persist_local_collection(collection_name, data_snapshot=None):
    name = str(collection_name)
    with _local_collection_persist_lock(name):
        if data_snapshot is None:
            with _runtime_store_lock:
                data_snapshot = dict(_load_local_collection(name))
        path = _local_collection_path(name)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        temporary = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        backup_path = f"{path}.bak"
        backup_temporary = f"{backup_path}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                os.chmod(temporary, 0o600)
                json.dump(
                    data_snapshot,
                    handle,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
                handle.flush()
                os.fsync(handle.fileno())
            # Keep one previous complete snapshot. The backup itself is
            # replaced atomically, so a crash during backup creation leaves
            # the current primary untouched.
            if os.path.exists(path):
                try:
                    # Same-directory hard links make backups of large user
                    # collections nearly free and preserve the exact prior
                    # complete file. Fall back to a copy on unsupported hosts.
                    os.link(path, backup_temporary)
                except OSError:
                    with open(path, "rb") as source, open(backup_temporary, "wb") as target:
                        os.chmod(backup_temporary, 0o600)
                        shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                os.replace(backup_temporary, backup_path)
                _fsync_directory(os.path.dirname(path))
            elif not os.path.exists(backup_path):
                # On the first write after migrating from gx_*.json, keep the
                # old complete snapshot as the new-format file's first backup.
                legacy_path = _legacy_local_collection_path(name)
                legacy_source = next(
                    (
                        candidate for candidate in (
                            legacy_path,
                            f"{legacy_path}.bak" if legacy_path else None,
                        )
                        if candidate and os.path.isfile(candidate)
                    ),
                    None,
                )
                if legacy_source:
                    try:
                        os.link(legacy_source, backup_temporary)
                    except OSError:
                        with open(legacy_source, "rb") as source, open(
                            backup_temporary, "wb"
                        ) as target:
                            os.chmod(backup_temporary, 0o600)
                            shutil.copyfileobj(source, target)
                            target.flush()
                            os.fsync(target.fileno())
                    os.replace(backup_temporary, backup_path)
                    _fsync_directory(os.path.dirname(path))
            os.replace(temporary, path)
            _fsync_directory(os.path.dirname(path))
        finally:
            for leftover in (temporary, backup_temporary):
                if os.path.exists(leftover):
                    try:
                        os.remove(leftover)
                    except OSError:
                        pass


class _LocalDocument:
    def __init__(self, document_id, data=None, exists=True):
        self.id = str(document_id)
        self._data = copy.deepcopy(data) if isinstance(data, dict) else {}
        self.exists = bool(exists)

    def to_dict(self):
        return copy.deepcopy(self._data)


class _LocalDocumentReference:
    def __init__(self, database, collection_name, document_id):
        self.database = database
        self.collection_name = str(collection_name)
        self.document_id = str(document_id)

    def get(self):
        with _runtime_store_lock:
            collection = _load_local_collection(self.collection_name)
            data = collection.get(self.document_id)
            if data is None:
                return _LocalDocument(self.document_id, {}, exists=False)
            return _LocalDocument(self.document_id, data, exists=True)

    def set(self, data, merge=False):
        if not isinstance(data, dict):
            raise ValueError("Local database document data must be a dictionary.")
        persist_lock = _local_collection_persist_lock(self.collection_name)
        with persist_lock:
            with _runtime_store_lock:
                collection = _load_local_collection(self.collection_name)
                existing = copy.deepcopy(collection.get(self.document_id, {}))
                incoming = _postgres_value(data, existing)
                result = dict(existing) if merge and isinstance(existing, dict) else {}
                result.update(incoming)
                snapshot = dict(collection)
                snapshot[self.document_id] = copy.deepcopy(result)
            _persist_local_collection(self.collection_name, snapshot)
            with _runtime_store_lock:
                collection[self.document_id] = copy.deepcopy(result)

    def update(self, data):
        if not isinstance(data, dict):
            raise ValueError("Local database document update must be a dictionary.")
        persist_lock = _local_collection_persist_lock(self.collection_name)
        with persist_lock:
            with _runtime_store_lock:
                collection = _load_local_collection(self.collection_name)
                if self.document_id not in collection:
                    raise KeyError(f"Document does not exist: {self.collection_name}/{self.document_id}")
                existing = copy.deepcopy(collection[self.document_id])
                result = dict(existing)
                result.update(_postgres_value(data, existing))
                snapshot = dict(collection)
                snapshot[self.document_id] = copy.deepcopy(result)
            _persist_local_collection(self.collection_name, snapshot)
            with _runtime_store_lock:
                collection[self.document_id] = copy.deepcopy(result)

    def delete(self):
        persist_lock = _local_collection_persist_lock(self.collection_name)
        with persist_lock:
            with _runtime_store_lock:
                collection = _load_local_collection(self.collection_name)
                snapshot = dict(collection)
                snapshot.pop(self.document_id, None)
            _persist_local_collection(self.collection_name, snapshot)
            with _runtime_store_lock:
                collection.pop(self.document_id, None)


class _LocalCollection:
    def __init__(self, database, collection_name):
        self.database = database
        self.collection_name = str(collection_name)
        self._order_field = None
        self._descending = False
        self._limit = None

    def document(self, document_id):
        return _LocalDocumentReference(self.database, self.collection_name, document_id)

    def order_by(self, field, direction="ASCENDING"):
        self._order_field = str(field)
        self._descending = str(direction).upper() == "DESCENDING"
        return self

    def limit(self, count):
        self._limit = max(0, int(count))
        return self

    def select(self, _fields):
        return self

    def stream(self):
        with _runtime_store_lock:
            rows = list(_load_local_collection(self.collection_name).items())
        rows = [
            (document_id, copy.deepcopy(data))
            for document_id, data in rows
        ]
        if self._order_field:
            def sort_key(row):
                value = (row[1] or {}).get(self._order_field)
                if value is None:
                    return (0, "")
                if isinstance(value, (int, float)):
                    return (1, value)
                return (1, str(value))
            rows.sort(key=sort_key, reverse=self._descending)
        if self._limit is not None:
            rows = rows[:self._limit]
        return iter(_LocalDocument(document_id, data) for document_id, data in rows)


class _LocalDatabase:
    def __bool__(self):
        return True

    def collection(self, name):
        return _LocalCollection(self, name)

    def clear_collection(self, name):
        persist_lock = _local_collection_persist_lock(name)
        with persist_lock:
            with _runtime_store_lock:
                collection_name = str(name)
                _load_local_collection(collection_name)
            _persist_local_collection(collection_name, {})
            with _runtime_store_lock:
                _runtime_collections[collection_name] = {}

    def flush_all(self):
        with _runtime_store_lock:
            collection_names = list(_runtime_collections)
        for name in collection_names:
            with _local_collection_persist_lock(name):
                with _runtime_store_lock:
                    snapshot = dict(_load_local_collection(name))
                _persist_local_collection(name, snapshot)


db = _LocalDatabase()
print(f"✅ Local JSON database ready: {BOT_DATA_DIR}")
if not _BOT_DATA_DIR_CONFIGURED:
    print(
        "⚠️ BOT_DATA_DIR is not set. This default local folder may be erased by "
        "a redeploy/container replacement; configure it to a persistent-volume mount."
    )

_FRESH_INSTALL_MARKER = os.path.join(BOT_DATA_DIR, ".gx_fresh_install_complete")


def _initialize_fresh_local_database_once():
    """Start with empty local JSON collections once, then preserve later data."""
    if os.path.isfile(_FRESH_INSTALL_MARKER):
        return False

    database_filenames = set()
    for filename in (
        list(_LOCAL_COLLECTION_FILES.values())
        + list(_LEGACY_LOCAL_COLLECTION_FILES.values())
    ):
        database_filenames.add(filename)
        database_filenames.add(f"{filename}.bak")

    # Remove this bot's old collection files/backups, including legacy GX-
    # prefixed files, before the first clean boot. The marker is written last,
    # so an interrupted reset safely retries instead of starting half-reset.
    for filename in os.listdir(BOT_DATA_DIR):
        is_database_file = filename in database_filenames or (
            filename.startswith("gx_")
            and (filename.endswith(".json") or filename.endswith(".json.bak"))
        )
        if not is_database_file:
            continue
        path = os.path.join(BOT_DATA_DIR, filename)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)

    # Match the reference bot's file-backed local database: initialize each
    # known collection as a JSON object so all stores exist from first launch.
    for filename in _LOCAL_COLLECTION_FILES.values():
        path = os.path.join(BOT_DATA_DIR, filename)
        temporary = f"{path}.{os.getpid()}.fresh.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                os.chmod(temporary, 0o600)
                json.dump({}, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass

    marker_temporary = f"{_FRESH_INSTALL_MARKER}.{os.getpid()}.tmp"
    try:
        with open(marker_temporary, "w", encoding="utf-8") as handle:
            os.chmod(marker_temporary, 0o600)
            handle.write("Fresh local database initialized.\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(marker_temporary, _FRESH_INSTALL_MARKER)
        _fsync_directory(BOT_DATA_DIR)
    finally:
        if os.path.exists(marker_temporary):
            try:
                os.remove(marker_temporary)
            except OSError:
                pass

    _runtime_collections.clear()
    print(
        "🆕 Fresh local JSON database initialized once. "
        "Data will be preserved on subsequent restarts."
    )
    return True


_initialize_fresh_local_database_once()



bot_settings = {
    "admins": ALL_ADMIN_IDS.copy(),
    "panels": [], 
    "fw_groups": [], 
    "otp_link": "https://t.me/your_otp_group",
    "otp_forward_channel_button": True,
    "otp_forward_support_button": True,
    "withdraw_on": True,
    "join_notifications": {str(OWNER_ID): True},
    "min_withdraw": 30.0,
    "otp_reward": 0.1,
    "refer_reward": 0.5,
    "cooldown": 10,
    "num_req": 3,
    "num_share": 1, 
    "support_link": "https://t.me/your_support",
    "w_methods": ["bKash", "Nagad"],
    "w_group": "", 
    
    "fj_on": False,
    "fj_channels": [], 
    "stex_keys": [],
    "demo_on": False,
    "demo_interval": 2, 
    "voltx_keys": [],
    "zenex_keys": [],
    "fastx_keys": [],
    "search_countries": [],
    "voltx_search_countries": [],
    "zenex_search_countries": [],
    "fastx_search_countries": [],
    "fastx_auto": False,
    "stex_services": {},
    "voltx_services": {},
    "zenex_services": {},
    "fastx_services": {},
    "premium_flags": copy.deepcopy(DEFAULT_PREMIUM_FLAGS),
    "premium_apps": copy.deepcopy(DEFAULT_PREMIUM_APPS),
    "custom_messages": copy.deepcopy(DEFAULT_CUSTOM_MESSAGES)
}

# Local JSON files start from safe runtime defaults and retain saved admin settings.
DEFAULT_BOT_SETTINGS = copy.deepcopy(bot_settings)
DEFAULT_BOT_SETTINGS.setdefault("demo_on", False)
DEFAULT_BOT_SETTINGS.setdefault("demo_interval", 2)
# These are the values shown and changed from the GX Control panel.  They are
# exported as one explicit snapshot as well as part of the complete settings
# so older local backups can restore this section without losing any other setting.
GX_CONTROL_KEYS = (
    "withdraw_on", "support_link", "w_group", "min_withdraw",
    "otp_reward", "refer_reward", "cooldown", "num_req", "num_share",
    "w_methods",
)

def ensure_premium_apps():
    """Replace old/custom app emoji entries with the six approved services."""
    bot_settings["premium_apps"] = copy.deepcopy(DEFAULT_PREMIUM_APPS)


def ensure_premium_flags():
    """Discard stale/manual flags and use only the supplied TXT catalog."""
    bot_settings["premium_flags"] = copy.deepcopy(DEFAULT_PREMIUM_FLAGS)


FS_KEYS = [
    "admins", "panels", "fw_groups", "otp_link", "otp_forward_channel_button",
    "otp_forward_support_button", "withdraw_on", 
    "min_withdraw", "otp_reward", "refer_reward", "cooldown", 
    "num_req", "num_share", "support_link", "w_methods", "w_group", "stex_keys", "voltx_keys", "search_countries", "stex_services", "voltx_services",
    "fj_on", "fj_channels", "join_notifications", "voltx_auto", "stex_auto", "zenex_auto", "zenex_keys", "zenex_services", "zenex_search_countries", "fastx_keys", "fastx_services", "fastx_search_countries", "fastx_auto"
]

number_batches = {}
used_numbers_list = []
stex_assigned_numbers = {} 
voltx_assigned_numbers = {}
zenex_assigned_numbers = {}
fastx_assigned_numbers = {}
# Number allocation is shared by Telegram update workers and the provider
# listeners.  Keep the claim set in memory only: numbers are operational
# state, not user/financial data, so they must never be written to Sheets.
number_allocation_lock = threading.RLock()
claimed_numbers = set()
STEX_BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api"
VOLTX_BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
ZENEX_BASE_URL = "https://api.zenexnetwork.com"
FASTX_BASE_URL = re.sub(
    r"(/api|/api/v1)$", "", os.getenv("FASTXOTP_BASE_URL", "https://fastxotp.com").rstrip("/")
).rstrip("/")
total_uploaded_stats = 0
total_assigned_stats = 0
processed_otps = set() 
_processed_otp_order = []
_processed_otp_lock = threading.RLock()
_MAX_PROCESSED_OTP_IDS = 5000
recent_traffic = []
_live_range_cache = {"stex": {}, "voltx": {}, "zenex": {}, "fastx": {}}
_live_range_cache_lock = threading.RLock()
_live_range_cache_updated_at = 0.0


def _remember_processed_otp(unique_id):
    """Atomically remember an OTP and evict only the oldest IDs at capacity."""
    key = str(unique_id)
    with _processed_otp_lock:
        if key in processed_otps:
            return False
        processed_otps.add(key)
        _processed_otp_order.append(key)
        overflow = len(_processed_otp_order) - _MAX_PROCESSED_OTP_IDS
        if overflow > 0:
            expired = _processed_otp_order[:overflow]
            del _processed_otp_order[:overflow]
            for old_key in expired:
                processed_otps.discard(old_key)
        return True


def _has_processed_otp(unique_id):
    with _processed_otp_lock:
        return str(unique_id) in processed_otps


def _processed_otp_snapshot():
    with _processed_otp_lock:
        ordered = list(_processed_otp_order)
        known = set(ordered)
        ordered.extend(sorted(processed_otps - known))
        return ordered[-_MAX_PROCESSED_OTP_IDS:]


def _restore_processed_otp_ids(values):
    ordered = []
    seen = set()
    for value in values if isinstance(values, (list, tuple, set)) else []:
        key = str(value)
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    ordered = ordered[-_MAX_PROCESSED_OTP_IDS:]
    with _processed_otp_lock:
        processed_otps.clear()
        processed_otps.update(ordered)
        _processed_otp_order[:] = ordered
_number_picker_sessions = {}
_number_picker_sessions_lock = threading.RLock()
_number_picker_refreshing = {}
user_banned_cache = {}
_force_join_membership_cache = {}
_force_join_membership_cache_lock = threading.RLock()
_FORCE_JOIN_MEMBERSHIP_CACHE_TTL = 60.0
_FORCE_JOIN_NEGATIVE_CACHE_TTL = 5.0
local_users = {}
audit_history = []
data_month = data_month_key()

database_save_lock = threading.RLock()

# Active HTTP sessions for Auto Captcha Panels
panel_sessions = {}
PANEL_API_REFRESH_INTERVAL = 600.0
panel_api_cache = {}
panel_api_cache_lock = threading.RLock()
_panel_unmatched_otp_keys = set()

def normalize_panel_url(raw_url):
    """Normalize and validate a provider URL before saving it."""
    value = str(raw_url or "").strip()
    if not value:
        raise ValueError("URL cannot be empty.")
    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = "https://" + value
    parsed = urlparse(value)
    if (
        re.search(r"\s", value)
        or parsed.scheme.lower() not in ("http", "https")
        or not parsed.netloc
        or not parsed.hostname
    ):
        raise ValueError("Please send a valid HTTP/HTTPS URL.")
    return value


def panel_api_request_urls(panel):
    """Return the request URL candidates for an API provider.

    A Full API URL is used exactly as supplied (with optional {token}/{key}
    placeholders supported). A base URL keeps the older token/key fallbacks.
    """
    full_url = str(panel.get("full_api_url", "") or "").strip()
    base_url = str(panel.get("api_url", "") or "").strip()
    token = str(panel.get("token", "") or "").strip()

    if full_url:
        try:
            full_url = normalize_panel_url(full_url)
        except ValueError:
            return []
        return [full_url.replace("{token}", token).replace("{key}", token)]

    if not base_url:
        return []
    try:
        base_url = normalize_panel_url(base_url)
    except ValueError:
        return []

    if "{token}" in base_url or "{key}" in base_url:
        return [base_url.replace("{token}", token).replace("{key}", token)]
    if "token=" in base_url.lower() or "key=" in base_url.lower():
        return [base_url]

    separator = "&" if "?" in base_url else "?"
    return [
        f"{base_url}{separator}token={token}",
        f"{base_url}{separator}key={token}&start=0",
        f"{base_url}{separator}key={token}",
    ]


def _panel_number_value(value):
    """Return a real provider number, or None for unrelated numeric fields."""
    if value is None or isinstance(value, (dict, list, tuple)):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not 7 <= len(digits) <= 18:
        return None
    # Do not mistake timestamps, ids, counters, or an empty placeholder for a
    # phone number. Values are accepted only when they came from a number-like
    # provider field (the caller enforces that).
    if len(set(digits)) == 1:
        return None
    return digits


PANEL_NUMBER_KEYS = {
    "number", "num", "phone", "phone_number", "phonenumber",
    "msisdn", "mobile", "mobile_number", "mobilenumber",
    "telephone", "tel", "full_number", "national_number",
    "no_plus_number", "receiver", "recipient", "to_number",
}
PANEL_MESSAGE_KEYS = {
    "message", "msg", "sms", "sms_text", "smstext", "content",
    "text", "body", "otp_message",
}
PANEL_SERVICE_KEYS = {
    "service", "app", "application", "site", "platform", "sender",
}


def parse_panel_number_response(response_text, p_config=None):
    """Parse provider JSON into real numbers, including number-only APIs.

    Hadi-like APIs often return available numbers without an SMS message.
    The old parser deliberately required an OTP message, which made those
    providers look empty. This parser accepts only explicit phone-number
    fields; it never manufactures a number from a counter, timestamp, or
    arbitrary JSON value.
    """
    results = []
    seen = set()
    try:
        data = json.loads(response_text)
    except (TypeError, ValueError):
        return results

    def walk(node, inherited_service=""):
        if isinstance(node, dict):
            lower = {
                re.sub(r"[^a-z0-9_]", "_", str(key).lower()).strip("_"): value
                for key, value in node.items()
            }
            service = inherited_service
            for key in PANEL_SERVICE_KEYS:
                if lower.get(key) not in (None, ""):
                    service = str(lower[key]).strip()
                    break

            number = None
            for key in PANEL_NUMBER_KEYS:
                if key in lower:
                    number = _panel_number_value(lower[key])
                    if number:
                        break
            if number and number not in seen:
                message = ""
                for key in PANEL_MESSAGE_KEYS:
                    if lower.get(key) not in (None, ""):
                        message = str(lower[key]).strip()
                        break
                otp = extract_otp_code(message) if message else None
                item = {
                    "number": number,
                    "message": message,
                    "service": service,
                }
                if otp:
                    item["otp"] = otp
                seen.add(number)
                results.append(item)

            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value, service)
        elif isinstance(node, list):
            for value in node:
                if isinstance(value, (dict, list)):
                    walk(value, inherited_service)

    walk(data)
    return results


def fetch_api_panel_data(panel, timeout=15):
    """Fetch one API panel without inventing fallback data.

    Returns (otp_rows, number_rows, status_text). The first non-error response
    wins. A successful response with no recognized records is reported clearly
    so the admin can fix the provider's response/URL instead of seeing silence.
    """
    urls = panel_api_request_urls(panel)
    if not urls:
        return [], [], "Invalid API URL"
    headers = {
        "User-Agent": "GX-Number-Bot/1.0",
        "Accept": "application/json,text/plain,text/html;q=0.9,*/*;q=0.8",
    }
    last_status = "No response"
    for request_url in urls:
        try:
            response = requests.get(request_url, headers=headers, timeout=timeout)
            last_status = f"HTTP {response.status_code}"
            if not response.ok:
                continue
            raw_text = response.text or ""
            number_rows = parse_panel_number_response(raw_text, panel)
            otp_rows = parse_panel_response(raw_text, panel)
            if otp_rows:
                return otp_rows, number_rows, "OK"
            if number_rows:
                return [], number_rows, "OK"
            # A valid HTTP response is still useful feedback even when its
            # schema is unsupported; do not silently try to invent records.
            if raw_text.strip():
                return [], [], "HTTP 200: no number/message records recognized"
        except requests.RequestException as exc:
            last_status = f"Request error: {str(exc)[:80]}"
        except Exception as exc:
            last_status = f"Parse error: {str(exc)[:80]}"
    return [], [], last_status


# 🌟 sAjaxSource (AJAX/DataTable) এবং Fallback HTML Parser Helper Function
def fetch_cpt_panel_cdrs(p, session, check_url):
    res = session.get(check_url, timeout=15)
    html_text = res.text
    
    # সেশন শেষ হয়েছে বা লগইন পেজে রিডাইরেক্ট করেছে কি না তা চেক করা
    final_url = str(getattr(res, "url", "") or "").lower()
    login_redirect = bool(re.search(r"/(?:login|signin)(?:\.php)?(?:[/?#]|$)", final_url))
    login_markers = (
        "sign in to your account",
        "please sign in",
        "welcome back!",
    )
    if login_redirect or any(marker in html_text.lower() for marker in login_markers):
        raise Exception("Session expired")
        
    soup = BeautifulSoup(html_text, 'html.parser')
    s_ajax_source = ""
    for script in soup.find_all("script"):
        script_text = script.string or ""
        match = re.search(r'sAjaxSource":\s*"([^"]+)"', script_text)
        if match:
            s_ajax_source = match.group(1)
            break
            
    results = []
    
    n_col_name = p.get("num_col_name", "number").lower()
    m_col_name = p.get("msg_col_name", "message").lower()
    n_idx = int(p.get("num_col_idx", 1)) - 1 if p.get("num_col_idx") else 1
    m_idx = int(p.get("msg_col_idx", 2)) - 1 if p.get("msg_col_idx") else 2

    # ৫.১ যদি sAjaxSource AJAX লিংক পাওয়া যায়
    if s_ajax_source:
        baseUrl = p.get("login_url", "").split("/client")[0].split("/login")[0].strip()
        if not baseUrl.startswith("http"):
            baseUrl = "http://" + baseUrl
            
        full_ajax_url = ""
        if s_ajax_source.startswith("http"):
            full_ajax_url = s_ajax_source
        elif s_ajax_source.startswith("/"):
            full_ajax_url = f"{baseUrl}{s_ajax_source}"
        else:
            last_slash_idx = check_url.rfind("/")
            current_dir = check_url[:last_slash_idx]
            full_ajax_url = f"{current_dir}/{s_ajax_source}"

        if "iDisplayLength" not in full_ajax_url:
            # Respect the panel record setting and cap an unlimited request.
            # Fetching 10,000 rows every monitor cycle wastes bandwidth.
            try:
                record_limit = int(p.get("records", 0))
            except (TypeError, ValueError):
                record_limit = 0
            record_limit = 1000 if record_limit <= 0 else min(record_limit, 1000)
            query_params = (
                "sEcho=1&iColumns=7&iDisplayStart=0"
                f"&iDisplayLength={record_limit}"
                "&sSearch=&iSortingCols=1&iSortCol_0=0&sSortDir_0=desc"
            )
            divider = "&" if "?" in full_ajax_url else "?"
            full_ajax_url += f"{divider}{query_params}"

        ajax_headers = {
            "Referer": check_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        
        ajax_res = session.get(full_ajax_url, headers=ajax_headers, timeout=15)
        data_dict = ajax_res.json()
        rows = data_dict.get("aaData", [])
        for row_val in rows:
            if not isinstance(row_val, list):
                continue
                
            if len(row_val) < max(n_idx, m_idx) + 1:
                continue
                
            num_val = row_val[n_idx] if (0 <= n_idx < len(row_val)) else row_val[2]
            msg_val = row_val[m_idx] if (0 <= m_idx < len(row_val)) else row_val[4]
            
            clean_num = re.sub(r'\D', '', str(num_val))
            if clean_num and 5 <= len(clean_num) <= 18:
                otp = extract_otp_code(msg_val)
                if otp and len(msg_val) > 4:
                    results.append({"number": clean_num, "message": msg_val, "otp": otp})
                    
    else:
        # ৫.২ ডাইরেক্ট HTML টেবিল থেকে রিড করার ব্যাকআপ লজিক
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if not rows: continue
            
            final_n_idx = n_idx
            final_m_idx = m_idx
            
            header_cells = rows[0].find_all(['th', 'td'])
            for i, cell in enumerate(header_cells):
                c_text = cell.get_text(strip=True).lower()
                if n_col_name in c_text: final_n_idx = i
                if m_col_name in c_text: final_m_idx = i

            for row in rows:
                cols = row.find_all(['td', 'th'])
                if all(c.name == 'th' for c in cols): continue
                
                if len(cols) > max(final_n_idx, final_m_idx):
                    num_text = cols[final_n_idx].get_text(separator=" ", strip=True)
                    msg_text = cols[final_m_idx].get_text(separator=" ", strip=True)
                    
                    clean_num = re.sub(r'\D', '', num_text)
                    if clean_num and 5 <= len(clean_num) <= 18:
                        otp = extract_otp_code(msg_text)
                        if otp and len(msg_text) > 4:
                            results.append({"number": clean_num, "message": msg_text, "otp": otp})
                            
    return results, html_text

# Track active number sessions to expire them automatically
user_active_sessions = {}

assigned_number_rates = {}

database_save_lock = threading.RLock()


def _runtime_state_snapshot():
    with number_allocation_lock:
        number_state = {
            "number_batches": copy.deepcopy(number_batches),
            "used_numbers_list": copy.deepcopy(used_numbers_list),
            "stex_assigned_numbers": copy.deepcopy(stex_assigned_numbers),
            "voltx_assigned_numbers": copy.deepcopy(voltx_assigned_numbers),
            "zenex_assigned_numbers": copy.deepcopy(zenex_assigned_numbers),
            "fastx_assigned_numbers": copy.deepcopy(fastx_assigned_numbers),
            "assigned_number_rates": copy.deepcopy(assigned_number_rates),
        }
    number_state.update({
        "total_uploaded_stats": int(total_uploaded_stats or 0),
        "total_assigned_stats": int(total_assigned_stats or 0),
        "processed_otps": _processed_otp_snapshot(),
        "recent_traffic": copy.deepcopy(recent_traffic),
        "data_month": str(data_month),
    })
    return number_state


def load_db():
    """Restore bot settings, user records, withdrawals, history and stock locally."""
    global bot_settings, number_batches, used_numbers_list
    global total_uploaded_stats, total_assigned_stats, recent_traffic
    global stex_assigned_numbers, voltx_assigned_numbers, zenex_assigned_numbers
    global fastx_assigned_numbers
    global processed_otps, assigned_number_rates, data_month

    settings_doc = db.collection("settings").document("bot_settings").get()
    if settings_doc.exists:
        stored_settings = settings_doc.to_dict()
        if isinstance(stored_settings, dict):
            bot_settings = _fill_missing_settings(bot_settings, stored_settings)
            bot_settings = _deduplicate_bot_settings(bot_settings)
            bot_settings["admins"] = list(dict.fromkeys(
                [
                    int(item) if str(item).lstrip("-").isdigit() else item
                    for item in bot_settings.get("admins", [])
                ] + ALL_ADMIN_IDS
            ))
    ensure_premium_apps()
    ensure_premium_flags()
    bot_settings.setdefault("custom_messages", {}).pop("search_number", None)
    if not isinstance(bot_settings.get("panels"), list):
        bot_settings["panels"] = []
    for panel in bot_settings["panels"]:
        if not isinstance(panel, dict):
            continue
        panel.setdefault("type", "API Panel")
        panel.setdefault("status", "OFF")
        panel.setdefault("name", "Unnamed Provider")
        panel.setdefault("api_url", "")
        panel.setdefault("full_api_url", "")
        panel.setdefault("token", "")
        panel.setdefault("records", 0)

    state_doc = db.collection("runtime_state").document("state").get()
    if state_doc.exists:
        state = state_doc.to_dict()
        if isinstance(state, dict):
            if isinstance(state.get("number_batches"), dict):
                number_batches = copy.deepcopy(state["number_batches"])
            if isinstance(state.get("used_numbers_list"), list):
                used_numbers_list = copy.deepcopy(state["used_numbers_list"])
            for key in (
                "stex_assigned_numbers", "voltx_assigned_numbers",
                "zenex_assigned_numbers", "fastx_assigned_numbers",
                "assigned_number_rates",
            ):
                if isinstance(state.get(key), dict):
                    globals()[key] = copy.deepcopy(state[key])
            total_uploaded_stats = int(state.get("total_uploaded_stats", total_uploaded_stats) or 0)
            total_assigned_stats = int(state.get("total_assigned_stats", total_assigned_stats) or 0)
            if isinstance(state.get("processed_otps"), list):
                _restore_processed_otp_ids(state["processed_otps"])
            if isinstance(state.get("recent_traffic"), list):
                recent_traffic = copy.deepcopy(state["recent_traffic"])
            data_month = str(state.get("data_month") or data_month)

    local_users.clear()
    local_users.update({snapshot.id: snapshot.to_dict() for snapshot in db.collection("users").stream()})
    audit_history.clear()
    audit_history.extend(
        snapshot.to_dict()
        for snapshot in db.collection("history").order_by("timestamp", direction="DESCENDING").stream()
    )
    if "all_known_users" in globals():
        all_known_users.clear()
        all_known_users.update(local_users.keys())
    if "user_cache" in globals():
        user_cache.clear()
    if "pending_withdrawals" in globals():
        pending_withdrawals.clear()
        for snapshot in db.collection("withdrawals").stream():
            item = snapshot.to_dict()
            if str(item.get("status", "pending")).lower() == "pending":
                pending_withdrawals[snapshot.id] = item
    with number_allocation_lock:
        claimed_numbers.clear()
    return True


def save_local_db():
    """Persist durable stock/allocation metadata to its local JSON document."""
    db.collection("runtime_state").document("state").set(_runtime_state_snapshot())
    # Local document writes are persisted atomically by set/update/delete.
    # Rewriting every loaded collection here made a settings save rewrite the
    # full users and history files, delaying unrelated button responses.


_provider_state_save_executor = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="provider-state-save"
)
_provider_state_save_lock = threading.Lock()
_provider_state_save_requested = False
_provider_state_save_running = False


def _provider_state_save_worker():
    global _provider_state_save_requested, _provider_state_save_running
    while True:
        with _provider_state_save_lock:
            if not _provider_state_save_requested:
                _provider_state_save_running = False
                return
            _provider_state_save_requested = False
        try:
            with database_save_lock:
                save_local_db()
        except Exception as exc:
            print(f"⚠️ Deferred number-state save failed: {exc}")


def schedule_provider_state_save():
    """Persist allocation changes off the number-response path, coalescing bursts."""
    global _provider_state_save_requested, _provider_state_save_running
    with _provider_state_save_lock:
        _provider_state_save_requested = True
        if _provider_state_save_running:
            return
        _provider_state_save_running = True
    try:
        _provider_state_save_executor.submit(_provider_state_save_worker)
    except RuntimeError:
        with _provider_state_save_lock:
            _provider_state_save_running = False


def save_user_store():
    """Persist any compatibility-cache user/history records to local collections."""
    for user_id, user in list(local_users.items()):
        if isinstance(user, dict):
            db.collection("users").document(str(user_id)).set(user)
    for index, event in enumerate(list(audit_history)):
        if isinstance(event, dict):
            event_id = str(event.get("event_id") or f"LOCAL_{index + 1}")
            db.collection("history").document(event_id).set(event)
    save_local_db()


def _atomic_json_write(path, value):
    temporary = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with database_save_lock:
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                os.chmod(temporary, 0o600)
                json.dump(value, handle, indent=2, ensure_ascii=False, default=str)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                try:
                    os.remove(temporary)
                except OSError:
                    pass


def _sync_fs():
    db.flush_all()


def save_db(preserve_existing=True):
    """Save current bot configuration and runtime state to local JSON files."""
    global bot_settings
    del preserve_existing  # Kept for compatibility with existing handlers.
    with database_save_lock:
        if "_deduplicate_bot_settings" in globals():
            bot_settings = _deduplicate_bot_settings(bot_settings)
        db.collection("settings").document("bot_settings").set(copy.deepcopy(bot_settings))
        save_local_db()


def _durable_state_fingerprint():
    """Fingerprint mutable settings/runtime state for low-write autosaving."""
    state = {
        "bot_settings": copy.deepcopy(bot_settings),
        "runtime_state": _runtime_state_snapshot(),
    }
    encoded = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _periodic_local_autosave_worker(interval_seconds=5.0):
    """Checkpoint changed settings/runtime state like the reference bot.

    User, history and withdrawal document writes are already synchronous.
    This worker covers mutable in-memory settings and number/provider state
    even if a code path forgets to call save_db().
    """
    # Force one checkpoint after startup, then save only when durable state
    # changes. This also closes the small gap between startup load and worker
    # initialization.
    last_fingerprint = None

    while True:
        time.sleep(interval_seconds)
        try:
            current_fingerprint = _durable_state_fingerprint()
            if current_fingerprint == last_fingerprint:
                continue
            save_db()
            last_fingerprint = current_fingerprint
        except Exception as exc:
            # Keep retrying on the next interval; never replace unreadable
            # database data with an empty snapshot.
            print(f"⚠️ Periodic local database save failed: {exc}")


def _flush_database_before_exit():
    try:
        save_db()
    except Exception as exc:
        print(f"⚠️ Final local database save failed: {exc}")


def _handle_termination_signal(_signum, _frame):
    # Raising SystemExit runs the registered final flush before process exit.
    raise SystemExit(0)


atexit.register(_flush_database_before_exit)



# Local restore/export normalization helpers
def _fill_missing_settings(defaults, stored):
    """Apply stored settings while retaining only missing newer defaults."""
    result = copy.deepcopy(defaults) if isinstance(defaults, dict) else {}
    if not isinstance(stored, dict):
        return result
    for key, value in stored.items():
        if (
            isinstance(value, dict)
            and isinstance(result.get(key), dict)
        ):
            result[key] = _fill_missing_settings(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _migrate_legacy_premium_emoji_ids(value):
    """Replace prior bot emoji IDs in saved settings and custom messages."""
    emoji_id_updates = {
        "6204067726357439597": GET_NUMBER_EMOJI_ID,
        "6204158577800652231": MESSAGE_SMS_EMOJI_ID,
        "6206125170311046692": OTP_GROUP_EMOJI_ID,
        "6219728615932699381": TWO_FA_BUTTON_EMOJI_ID,
        "6204185859432914997": FORCE_JOIN_BUTTON_EMOJI_ID,
        "6204182376214438451": REFERRAL_EMOJI_ID,
        "6204048257270686236": WITHDRAWAL_EMOJI_ID,
        "6219750726424338797": RELOAD_RESTART_RESET_LOADING_EMOJI_ID,
        "6071096140168696563": LANGUAGE_EMOJI_ID,
        "6204067528788942134": NUMBER_SUCCESS_EMOJI_ID,
        "6219752491655899743": CROSS_CANCEL_EMOJI_ID,
        "5353001161878182134": UPLOAD_EMOJI_ID,
        "6219940207496536715": WELCOME_HAND_EMOJI_ID,
        "6203957577626164865": WELCOME_PERSON_EMOJI_ID,
        "5271604874419647061": OTP_GROUP_EMOJI_ID,
    }

    if isinstance(value, dict):
        migrated = {}
        for key, item in value.items():
            if key == "icon_custom_emoji_id":
                migrated[key] = emoji_id_updates.get(str(item), item)
            else:
                migrated[key] = _migrate_legacy_premium_emoji_ids(item)
        return migrated
    if isinstance(value, list):
        return [_migrate_legacy_premium_emoji_ids(item) for item in value]
    if isinstance(value, str):
        for old_id, new_id in emoji_id_updates.items():
            value = value.replace(old_id, str(new_id))
        return value
    return value


def _deduplicate_bot_settings(settings):
    """Remove repeated admin settings before runtime use or Sheets export."""
    if not isinstance(settings, dict):
        return {}
    result = copy.deepcopy(settings)

    def unique_values(values):
        output = []
        seen = set()
        for value in values if isinstance(values, list) else []:
            marker = json.dumps(
                value, ensure_ascii=False, sort_keys=True, default=str
            )
            if marker not in seen:
                seen.add(marker)
                output.append(value)
        return output

    for key in (
        "admins", "fj_channels", "stex_keys", "voltx_keys", "zenex_keys",
        "search_countries", "voltx_search_countries",
        "zenex_search_countries", "fastx_search_countries", "w_methods",
    ):
        if key in result:
            result[key] = unique_values(result.get(key))

    # Panels are user-created records, not a set. Do not deduplicate them by
    # name/URL: two providers can intentionally share those fields while using
    # different credentials, and collapsing them silently drops panel data.
    result["panels"] = [
        copy.deepcopy(panel)
        for panel in (
            result.get("panels", [])
            if isinstance(result.get("panels"), list) else []
        )
        if isinstance(panel, dict)
    ]

    for service_key in ("stex_services", "voltx_services", "zenex_services", "fastx_services"):
        services = result.get(service_key)
        if not isinstance(services, dict):
            continue
        for countries in services.values():
            if not isinstance(countries, dict):
                continue
            for country, ranges in list(countries.items()):
                countries[country] = unique_values(ranges)

    custom_messages = result.get("custom_messages")
    if isinstance(custom_messages, dict):
        for message in custom_messages.values():
            if isinstance(message, dict) and isinstance(message.get("buttons"), list):
                message["buttons"] = unique_values(message["buttons"])

        # Saved custom menu text can contain the old embedded emoji tags even
        # after the constants changed. Use the new referral icon in the stored
        # referral message and its old gift-style custom buttons.
        referral_message = custom_messages.get("refer")
        if isinstance(referral_message, dict):
            referral_tag = (
                f'<tg-emoji emoji-id="{GIFT_BOX_EMOJI_ID}">🎁</tg-emoji>'
            )
            referral_text = referral_message.get("text")
            if isinstance(referral_text, str):
                referral_text = re.sub(
                    r'<tg-emoji emoji-id="\d+">🎁</tg-emoji>',
                    referral_tag,
                    referral_text,
                )
                referral_message["text"] = referral_text
            for button in referral_message.get("buttons", []):
                if (
                    isinstance(button, dict)
                    and str(button.get("icon_custom_emoji_id", ""))
                    == LEGACY_GIFT_BOX_EMOJI_ID
                ):
                    button["icon_custom_emoji_id"] = GIFT_BOX_EMOJI_ID

    result = _migrate_legacy_premium_emoji_ids(result)
    return result


def _as_number(value, default=0):
    try:
        number = float(str(value).strip())
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return default


def _normalize_username(value):
    """Store Telegram usernames consistently as @username or an empty string."""
    value = str(value or "").strip()
    if not value:
        return ""
    return "@" + value.lstrip("@")


def _is_group_or_channel_record(row):
    """Reject group/channel records from user and financial Sheets tabs."""
    if not isinstance(row, dict):
        return True
    for field in ("user_id", "id", "chat_id", "group_id", "channel_id", "sender_chat_id"):
        value = row.get(field)
        if value is None or str(value).strip() == "":
            continue
        text = str(value).strip()
        if re.fullmatch(r"-\d+", text):
            return True
    chat_type = str(row.get("chat_type", row.get("type", "")) or "").lower()
    return chat_type in {"group", "supergroup", "channel"}


def _merge_record_values(existing, incoming):
    """Merge a record while keeping meaningful values from both copies."""
    result = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    if not isinstance(incoming, dict):
        return result
    for key, value in incoming.items():
        if (
            key == "otp_timestamps"
            and isinstance(result.get(key), list)
            and isinstance(value, list)
        ):
            # Backups overlap with live history. Merge the multiset by taking
            # the largest count per timestamp so overlap is retained once,
            # without dropping same-second OTP events.
            current_values = [str(item) for item in result[key]]
            incoming_values = [str(item) for item in value]
            current_counts = Counter(current_values)
            incoming_counts = Counter(incoming_values)
            merged_values = list(current_values)
            for timestamp, count in incoming_counts.items():
                if count > current_counts[timestamp]:
                    merged_values.extend(
                        [timestamp] * (count - current_counts[timestamp])
                    )
            result[key] = merged_values
            continue
        # A blank value from an old CSV/XLSX export must not erase a real value
        # already present. False and numeric zero are meaningful and do update.
        if key not in result or value not in (None, ""):
            result[key] = copy.deepcopy(value)
    return result


def _deduplicate_collection_rows(value, collection_name):
    """Return one canonical record per user/request/event identity.

    Imported spreadsheets are row based while the runtime store is document based. A
    restore can therefore contain duplicate rows with different generated
    document IDs. This function collapses those rows before they reach runtime
    and before the next Sheets rewrite.
    """
    if isinstance(value, dict):
        source = value.items()
    elif isinstance(value, list):
        source = enumerate(value)
    else:
        source = []

    result = {}
    for source_key, raw_row in source:
        if not isinstance(raw_row, dict):
            continue
        row = copy.deepcopy(raw_row)
        if collection_name == "users":
            if _is_group_or_channel_record(row):
                continue
            identity = str(
                row.get("user_id") or row.get("id") or source_key or ""
            ).strip()
            if not identity or not re.fullmatch(r"\d+", identity) or identity == "0":
                continue
            row["user_id"] = identity
        elif collection_name == "withdrawals":
            if _is_group_or_channel_record(row):
                continue
            identity = str(row.get("request_id") or "").strip()
            if not identity:
                identity = "RESTORED_" + hashlib.sha256(
                    _stable_json_key({
                        "user_id": row.get("user_id", ""),
                        "amount": row.get("amount", ""),
                        "method": row.get("method", ""),
                        "number": row.get("number", ""),
                        "timestamp": row.get("timestamp", ""),
                    }).encode("utf-8")
                ).hexdigest()[:20]
            row["request_id"] = identity
        else:
            if _is_group_or_channel_record(row):
                continue
            identity = str(row.get("event_id") or "").strip()
            if not identity:
                identity = "RESTORED_" + hashlib.sha256(
                    _stable_json_key({
                        "user_id": row.get("user_id", ""),
                        "event_type": row.get("event_type", ""),
                        "amount": row.get("amount", ""),
                        "status": row.get("status", ""),
                        "method": row.get("method", ""),
                        "request_id": row.get("request_id", ""),
                        "timestamp": row.get("timestamp", ""),
                        "message": row.get("message", ""),
                    }).encode("utf-8")
                ).hexdigest()[:20]
            row["event_id"] = identity

        if identity in result:
            result[identity] = _merge_record_values(result[identity], row)
        else:
            result[identity] = row
    return result


def _decode_otp_timestamps(value):
    """Decode OTP timestamp lists exported through CSV/XLSX cells."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "A user's otp_timestamps field is not valid JSON."
            ) from exc
    if not isinstance(value, list):
        raise ValueError("A user's otp_timestamps field must be a JSON array.")
    return [str(item) for item in value if item is not None and str(item).strip()]


def _normalize_user_otp_timestamps(users_by_id):
    """Validate timestamp history before a restore mutates any stored records."""
    if not isinstance(users_by_id, dict):
        raise ValueError("Backup user records are invalid.")
    normalized = copy.deepcopy(users_by_id)
    for user_id, user in normalized.items():
        if not isinstance(user, dict) or "otp_timestamps" not in user:
            continue
        try:
            user["otp_timestamps"] = _decode_otp_timestamps(
                user["otp_timestamps"]
            )
        except ValueError as exc:
            raise ValueError(
                f"User {user_id} has invalid OTP timestamp history: {exc}"
            ) from exc
    return normalized


def _restore_rows_to_runtime(rows_by_sheet):
    """Restore imported user, withdrawal and history records into local collections."""
    users = list(_deduplicate_collection_rows(
        rows_by_sheet.get("Users", []) or [], "users"
    ).values())
    withdrawals = list(_deduplicate_collection_rows(
        rows_by_sheet.get("Withdrawals", []) or [], "withdrawals"
    ).values())
    history = list(_deduplicate_collection_rows(
        rows_by_sheet.get("History", []) or [], "history"
    ).values())

    for collection_name in ("users", "withdrawals", "history"):
        db.clear_collection(collection_name)

    for row in users:
        uid = str(row.get("user_id") or row.get("id") or "").strip()
        if not uid:
            continue
        user = dict(row)
        user["user_id"] = _as_number(uid, uid)
        old_username_value = str(row.get("username", "") or "").strip()
        user["user_name"] = str(
            row.get("user_name")
            or row.get("full_name")
            or (
                old_username_value
                if old_username_value and not old_username_value.startswith("@")
                and " " in old_username_value
                else ""
            )
            or ""
        )[:120]
        username_candidate = (
            old_username_value
            if old_username_value and (
                old_username_value.startswith("@") or " " not in old_username_value
            )
            else ""
        )
        user["username"] = _normalize_username(username_candidate)[:120]
        user["balance"] = _as_number(row.get("balance"), 0.0)
        user["total_refers"] = _as_number(row.get("total_refers"), 0)
        user["total_otps"] = _as_number(row.get("total_otps"), 0)
        if "otp_timestamps" in row:
            user["otp_timestamps"] = _decode_otp_timestamps(
                row["otp_timestamps"]
            )
        user["otp"] = str(row.get("otp", "") or "")
        user["banned"] = str(row.get("banned", "")).lower() in ("1", "true", "yes")
        user["verified"] = str(row.get("verified", "")).lower() in ("1", "true", "yes")
        db.collection("users").document(uid).set(user)

    for index, row in enumerate(withdrawals):
        request_id = str(row.get("request_id") or f"RESTORED_{index + 1}")
        item = dict(row)
        item["request_id"] = request_id
        item["user_id"] = str(row.get("user_id", ""))
        item["amount"] = _as_number(row.get("amount"), 0.0)
        item["status"] = str(row.get("status", "pending") or "pending").lower()
        db.collection("withdrawals").document(request_id).set(item)

    for index, row in enumerate(history):
        event_id = str(row.get("event_id") or f"RESTORED_{index + 1}")
        item = dict(row)
        item["event_id"] = event_id
        item["amount"] = _as_number(row.get("amount"), row.get("amount", ""))
        db.collection("history").document(event_id).set(item)

    local_users.clear()
    for snapshot in db.collection("users").stream():
        local_users[snapshot.id] = snapshot.to_dict()
    audit_history.clear()
    audit_history.extend(
        snapshot.to_dict() for snapshot in db.collection("history").stream()
    )
    all_known_users.clear()
    all_known_users.update(local_users.keys())
    user_cache.clear()
    pending_withdrawals.clear()
    for snapshot in db.collection("withdrawals").stream():
        item = snapshot.to_dict()
        if str(item.get("status", "pending")).lower() == "pending":
            pending_withdrawals[snapshot.id] = item



def record_history(user_id, event_type, message="", amount=None, status=None,
                   method=None, request_id=None, balance_after=None,
                   payment_number=None):
    """Store only useful financial/user events; never store OTP text or service numbers."""
    entry = {
        "event_id": uuid.uuid4().hex[:18],
        "user_id": str(user_id),
        "event_type": str(event_type),
        "message": str(message or "")[:500],
        "amount": amount,
        "status": status,
        "method": method,
        "request_id": request_id,
        "balance_after": balance_after,
        "timestamp": iso_now(),
        "data_month": data_month_key()
    }
    if payment_number is not None:
        entry["payment_number"] = str(payment_number)[:80]

    try:
        if db:
            db.collection("history").document(entry["event_id"]).set(entry)
        else:
            audit_history.append(entry)
            if len(audit_history) > 10000:
                del audit_history[:-10000]
            save_user_store()
    except Exception:
        pass
    return entry


def _delete_collection_documents(collection_name):
    if not db:
        return
    try:
        for snapshot in db.collection(collection_name).stream():
            db.collection(collection_name).document(snapshot.id).delete()
    except Exception as exc:
        print(f"⚠️ Could not clear {collection_name}: {exc}")


def ensure_monthly_data_reset():
    """Advance the monthly marker without deleting durable customer records."""
    global data_month
    current_month = data_month_key()
    if data_month == current_month:
        return False

    # A former monthly rollover zeroed user balances/counters and deleted
    # history and withdrawals. That made an ordinary first restart of a new
    # month look like data loss. Preserve all customer and provider records;
    # only advance the marker so startup never interprets the rollover as a
    # reason to clear data.
    print(f"📅 Monthly marker advanced without deleting data: {data_month} -> {current_month}")
    data_month = current_month
    save_local_db()
    return True


load_db()
ensure_monthly_data_reset()
# Rewrite the state once on startup so legacy used-number/OTP caches are
# removed from older local state files as well.
save_db()

user_states = {}
temp_data = {}
system_settings_message_ids = {}
system_settings_reply_sessions = set()
system_settings_reply_actions = {}
user_cooldowns = {}
pending_withdrawals = {}
withdrawal_processing_lock = threading.Lock()
withdrawal_processing_ids = set()

# ==========================================
# Telegram API & Helpers
# ==========================================
_tg_http_local = threading.local()


def _telegram_http_session():
    """Reuse keep-alive connections without sharing one Session across threads."""
    session = getattr(_tg_http_local, "session", None)
    if session is None:
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=8,
            pool_maxsize=16,
            max_retries=0,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _tg_http_local.session = session
    return session


_callback_ack_executor = ThreadPoolExecutor(
    max_workers=16,
    thread_name_prefix="telegram-callback-ack",
)
_force_join_check_executor = ThreadPoolExecutor(
    max_workers=16,
    thread_name_prefix="telegram-force-join",
)
_provider_http_local = threading.local()
_provider_fetch_executor = ThreadPoolExecutor(
    max_workers=32, thread_name_prefix="number-provider"
)


def _provider_http_session():
    """Reuse one keep-alive HTTP session per provider worker thread."""
    session = getattr(_provider_http_local, "session", None)
    if session is None:
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=4,
            pool_maxsize=4,
            max_retries=0,
            pool_block=True,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _provider_http_local.session = session
    return session

def api_call(method, payload=None):
    url = f"{BASE_URL}/{method}"
    try:
        # getUpdates is a 50-second long poll; its HTTP read timeout must be
        # longer than Telegram's poll timeout or the bot reconnects needlessly.
        timeout = (5, 60) if method.startswith("getUpdates") else (3.05, 10)
        res = _telegram_http_session().post(url, json=payload, timeout=timeout)
        result = res.json()
        if method in {
            "sendMessage", "sendPhoto", "sendDocument", "sendVideo",
            "sendAudio", "sendVoice", "sendAnimation", "sendSticker",
            "sendLocation", "sendContact", "sendPoll", "sendMediaGroup",
            "copyMessage", "copyMessages",
        } and isinstance(payload, dict):
            _record_bot_delivery_result(payload.get("chat_id"), result)
        return result
    except Exception as e:
        return {}


# Use the same 30 messages/second limit for both broadcast paths.
_BROADCAST_RATE_PER_SECOND = 30
_BROADCAST_RATE_LOCK = threading.Lock()
_BROADCAST_NEXT_SEND_AT = 0.0
_BROADCAST_PAUSE_UNTIL = 0.0
_broadcast_http_local = threading.local()


def _broadcast_http_session():
    """Reuse a separate keep-alive Telegram session per broadcast worker."""
    session = getattr(_broadcast_http_local, "session", None)
    if session is None:
        session = requests.Session()
        _broadcast_http_local.session = session
    return session


def _broadcast_wait_for_slot():
    """Apply one shared per-bot send rate across both broadcast entry points."""
    global _BROADCAST_NEXT_SEND_AT
    interval = 1.0 / _BROADCAST_RATE_PER_SECOND
    with _BROADCAST_RATE_LOCK:
        now = time.monotonic()
        send_at = max(now, _BROADCAST_NEXT_SEND_AT, _BROADCAST_PAUSE_UNTIL)
        _BROADCAST_NEXT_SEND_AT = send_at + interval
    delay = send_at - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def _broadcast_note_rate_limit(retry_after):
    """Pause all broadcast workers when Telegram responds with HTTP 429."""
    global _BROADCAST_PAUSE_UNTIL
    try:
        retry_after = max(1.0, min(float(retry_after), 120.0))
    except (TypeError, ValueError):
        retry_after = 1.0
    with _BROADCAST_RATE_LOCK:
        _BROADCAST_PAUSE_UNTIL = max(
            _BROADCAST_PAUSE_UNTIL, time.monotonic() + retry_after
        )


def _broadcast_users(user_ids, method, payload_for_user):
    """Send one broadcast with bounded concurrency, shared pacing and retries."""
    recipients = list(dict.fromkeys(
        str(user_id) for user_id in user_ids if str(user_id).strip()
    ))
    if not recipients:
        return 0, 0, 0

    url = f"{BASE_URL}/{method}"

    def send_to_user(user_id):
        payload = payload_for_user(user_id)
        session = _broadcast_http_session()

        for attempt in range(3):
            _broadcast_wait_for_slot()
            try:
                response = session.post(url, json=payload, timeout=15)
            except requests.RequestException:
                if attempt < 2:
                    time.sleep(0.25 * (attempt + 1))
                    continue
                return False

            try:
                result = response.json()
            except ValueError:
                result = {}
            if not isinstance(result, dict):
                result = {}

            if result.get("ok"):
                _record_bot_delivery_result(user_id, result)
                return True

            if response.status_code == 429:
                parameters = result.get("parameters")
                retry_after = (
                    parameters.get("retry_after", 1)
                    if isinstance(parameters, dict)
                    else 1
                )
                _broadcast_note_rate_limit(retry_after)
                if attempt < 2:
                    continue
                return False

            if response.status_code == 403:
                _record_bot_delivery_result(user_id, result)
            if response.status_code >= 500 and attempt < 2:
                time.sleep(0.25 * (attempt + 1))
                continue
            return False

        return False

    worker_count = min(128, len(recipients))
    success = 0
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        # Bound queued futures so large user lists do not consume excessive RAM.
        chunk_size = worker_count * 8
        for offset in range(0, len(recipients), chunk_size):
            chunk = recipients[offset:offset + chunk_size]
            success += sum(1 for sent in executor.map(send_to_user, chunk) if sent)
    failed = len(recipients) - success
    return success, failed, len(recipients)


UI_TRANSLATIONS_BN = {
    "SELECT LANGUAGE": "ভাষা নির্বাচন করুন",
    "CHOOSE YOUR LANGUAGE": "আপনার ভাষা নির্বাচন করুন",
    "NAVIGATION MENU": "নেভিগেশন মেনু",
    "ENGLISH": "ইংরেজি",
    "BANGLA": "বাংলা",
    "GET NUMBER": "নম্বর নিন",
    "TRAFFIC": "ট্রাফিক",
    "2FA ONLINE": "২এফএ অনলাইন",
    "REFER": "রেফার",
    "WITHDRAWAL": "উত্তোলন",
    "SUPPORT": "সাপোর্ট",
    "CHANGE LANGUAGE": "ভাষা পরিবর্তন করুন",
    "RESTART BOT": "বট রিস্টার্ট করুন",
    "ADMIN PANEL": "অ্যাডমিন প্যানেল",
    "CLOSE": "বন্ধ করুন",
    "CANCEL": "বাতিল",
    "REFRESH": "রিফ্রেশ",
    "COPY LINK": "লিংক কপি করুন",
    "CONTACT SUPPORT": "সাপোর্টে যোগাযোগ করুন",
    "GENERATE 2FA CODE": "২এফএ কোড তৈরি করুন",
    "EXPLORE": "এক্সপ্লোর",
    "RANGE": "রেঞ্জ",
    "SELECT A SERVICE": "একটি সার্ভিস নির্বাচন করুন",
    "SELECT A COUNTRY": "একটি দেশ নির্বাচন করুন",
    "NO NUMBERS OR SERVICES AVAILABLE!": "কোনো নম্বর বা সার্ভিস পাওয়া যায়নি!",
    "NO RECENT TRAFFIC FOUND IN THE LAST 10 MINUTES...": "গত ১০ মিনিটে কোনো ট্রাফিক পাওয়া যায়নি...",
    "UPDATED": "আপডেট হয়েছে",
    "ENTER 3 TO 9 DIGITS": "৩ থেকে ৯ ডিজিট লিখুন",
    "FAST NUMBER LOOKUP SYSTEM": "দ্রুত নম্বর খোঁজার সিস্টেম",
    "CONTACT US FOR ANY HELP:": "যেকোনো সাহায্যের জন্য যোগাযোগ করুন:",
    "SELECT METHOD:": "মেথড নির্বাচন করুন:",
    "YOUR LINK:": "আপনার লিংক:",
    "TOTAL REFERS:": "মোট রেফার:",
    "PER REFER:": "প্রতি রেফারে:",
    "NUMBER BOT": "নম্বর বট",
    "WELCOME TO NUMBER & OTP SERVICE": "নম্বর ও ওটিপি সার্ভিসে স্বাগতম",
    "CHOOSE AN OPTION BELOW": "নিচের অপশনটি নির্বাচন করুন",
    "TO CONTINUE USING THE BOT": "বট ব্যবহার চালিয়ে যেতে",
    "PREMIUM OTP SERVICE": "প্রিমিয়াম ওটিপি সার্ভিস",
    "TRAFFIC OVERVIEW": "ট্রাফিকের বিবরণ",
    "AVAILABLE NUMBERS": "উপলভ্য নম্বর",
    "ASSIGNED NUMBERS": "বরাদ্দ করা নম্বর",
    "10 MINUTE LIVE TRAFFIC": "১০ মিনিটের লাইভ ট্রাফিক",
    "LOW": "কম",
    "MEDIUM": "মাঝারি",
    "HIGH": "বেশি",
    "SELECT A SERVICE:": "একটি সার্ভিস নির্বাচন করুন:",
    "SELECT A COUNTRY": "একটি দেশ নির্বাচন করুন",
    "ENTER 3 TO 9 DIGITS": "৩ থেকে ৯ ডিজিট লিখুন",
    "EXAMPLE:": "উদাহরণ:",
    "TOTAL OTP": "মোট ওটিপি",
    "BALANCE:": "ব্যালেন্স:",
    "MINIMUM:": "সর্বনিম্ন:",
    "WITHDRAWAL": "উত্তোলন",
    "REFER & EARN": "রেফার করুন ও আয় করুন",
    "TOTAL REFERS": "মোট রেফার",
    "PER REFER": "প্রতি রেফারে",
    "NO NUMBERS OR SERVICES AVAILABLE!": "কোনো নম্বর বা সার্ভিস পাওয়া যায়নি!",
    "NO RECENT TRAFFIC FOUND": "সাম্প্রতিক কোনো ট্রাফিক পাওয়া যায়নি",
    "UPDATED": "আপডেট হয়েছে",
    "JOIN CHANNEL": "চ্যানেলে যোগ দিন",
    "CHECK JOINED": "যোগ দেওয়া যাচাই করুন",
    "NUMBER MANAGEMENT": "নম্বর ম্যানেজমেন্ট",
    "DELETE MANAGEMENT": "ডিলিট ম্যানেজমেন্ট",
    "USED NUMBER": "ব্যবহৃত নম্বর",
    "UNUSED NUMBER": "অব্যবহৃত নম্বর",
    "DELETE FILE": "ফাইল ডিলিট",
    "DELETE DATA": "ডেটা ডিলিট",
    "BACK TO ADMIN PANEL": "অ্যাডমিন প্যানেলে ফিরুন",
    "MASTER PANEL": "মাস্টার প্যানেল",
    "GX CONTROL": "জিএক্স কন্ট্রোল",
    "TIMER SET": "টাইমার সেট",
    "MEMBER & ADMIN": "মেম্বার ও অ্যাডমিন",
    "RECOVER DATA": "ডেটা পুনরুদ্ধার",
}

def get_user_language(user_id):
    """Return the selected UI language; legacy users fall back to English."""
    # Negative Telegram IDs are groups/channels, not user profiles.
    if isinstance(user_id, int) and user_id < 0:
        return "EN"
    try:
        return get_user(user_id).get("language") or "EN"
    except Exception:
        return "EN"

def localize_ui_text(chat_id, text):
    if not text or get_user_language(chat_id) != "BN":
        return text
    result = str(text)
    for source, target in sorted(UI_TRANSLATIONS_BN.items(), key=lambda item: len(item[0]), reverse=True):
        result = re.sub(re.escape(source), target, result, flags=re.IGNORECASE)
    return result

def localize_markup(chat_id, reply_markup):
    if not reply_markup or get_user_language(chat_id) != "BN":
        return reply_markup
    markup = copy.deepcopy(reply_markup)
    for keyboard_key in ("keyboard", "inline_keyboard"):
        for row in markup.get(keyboard_key, []) if isinstance(markup, dict) else []:
            for button in row:
                if isinstance(button, dict) and "text" in button:
                    button["text"] = localize_ui_text(chat_id, button["text"])
    return markup

_BOLD_BUTTON_TRANSLATION = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
    "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
)
_NORMAL_BUTTON_TRANSLATION = str.maketrans(
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
    "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
)
_SMALL_CAPS_BUTTON_GLYPHS = (
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘQʀꜱᴛᴜᴠᴡXʏᴢ"
)
_SMALL_CAPS_BUTTON_TRANSLATION = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    _SMALL_CAPS_BUTTON_GLYPHS * 2,
)
_NORMAL_SMALL_CAPS_BUTTON_TRANSLATION = str.maketrans(
    _SMALL_CAPS_BUTTON_GLYPHS,
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
)
_LEGACY_NORMAL_BUTTON_TRANSLATION = str.maketrans(
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
    "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
)

def bold_button_text(text):
    """Use Unicode bold glyphs because Telegram does not parse HTML in buttons."""
    # Keep the original casing (e.g. Facebook) while making the label bold.
    return str(text).translate(_BOLD_BUTTON_TRANSLATION)

def normal_button_text(text):
    """Convert small-caps and bold button labels before command matching."""
    return (
        str(text)
        .translate(_NORMAL_SMALL_CAPS_BUTTON_TRANSLATION)
        .translate(_NORMAL_BUTTON_TRANSLATION)
        .translate(_LEGACY_NORMAL_BUTTON_TRANSLATION)
    )


def small_caps_button_text(text):
    """Keep each word's first letter uppercase and render the rest in small caps."""
    plain_text = normal_button_text(text)

    def style_word(match):
        word = match.group(0)
        return (
            word[0].upper()
            + word[1:].lower().translate(_SMALL_CAPS_BUTTON_TRANSLATION)
        )

    return re.sub(r"[A-Za-z]+", style_word, plain_text)

def _service_name_pattern():
    names = {
        str(value.get("name", key)).strip()
        for key, value in bot_settings.get("premium_apps", {}).items()
        if str(value.get("name", key)).strip()
    }
    names.update(str(key).replace("_", " ").strip() for key in bot_settings.get("premium_apps", {}))
    # Include detected SMS services, admin-added stock services, and every
    # configured withdrawal method. This keeps names such as Facebook, a
    # custom service, bKash, or Nagad bold in both messages and buttons.
    names.update(
        str(key).replace("_", " ").strip()
        for key in globals().get("SERVICE_SMS_KEYWORDS", {})
    )
    names.update(
        str(method).strip()
        for method in bot_settings.get("w_methods", [])
        if str(method).strip()
    )
    for batch in number_batches.values():
        if isinstance(batch, dict) and str(batch.get("service", "")).strip():
            names.add(str(batch["service"]).strip())
    for setting_key in ("stex_services", "voltx_services", "zenex_services", "fastx_services"):
        names.update(
            str(service).replace("_", " ").strip()
            for service in bot_settings.get(setting_key, {})
            if str(service).strip()
        )
    names = sorted((name for name in names if name), key=len, reverse=True)
    if not names:
        return None
    return re.compile(
        r"(?<![\w])(" + "|".join(re.escape(name) for name in names) + r")(?![\w])",
        flags=re.IGNORECASE,
    )

def bold_service_names(text):
    """Bold only known service names, leaving the surrounding text normal."""
    pattern = _service_name_pattern()
    if not pattern:
        return str(text)
    return pattern.sub(lambda match: bold_button_text(match.group(1)), str(text))


_NORMAL_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\u2300-\u23FF"
    "\u2600-\u27BF"
    "\u2B00-\u2BFF"
    "\u00A9\u00AE\u203C\u2049\u2122\u2139\u3030\u303D\u3297\u3299"
    "\uFE0E\uFE0F\u200D\u20E3"
    "\U0001F3FB-\U0001F3FF"
    "\U000E0020-\U000E007F"
    "]"
)
_NORMAL_EMOJI_RUN_RE = re.compile(
    r"[ \t]*(?:(?:" + _NORMAL_EMOJI_RE.pattern + r")+[ \t]*)+"
)


def strip_normal_emojis(text):
    """Remove regular emoji while preserving Telegram premium-emoji markup."""
    parts = re.split(
        r"(<tg-emoji\b[^>]*>.*?</tg-emoji>)",
        str(text or ""),
        flags=re.IGNORECASE | re.DOTALL,
    )
    for index, part in enumerate(parts):
        if not part.lower().startswith("<tg-emoji"):
            def replace_emoji_run(match):
                before = part[:match.start()].rstrip(" \t")
                after = part[match.end():].lstrip(" \t")
                has_before = (
                    bool(before) and not before.endswith(("\n", "\r"))
                ) or (
                    index > 0 and parts[index - 1].lower().endswith("</tg-emoji>")
                )
                has_after = (
                    bool(after) and not after.startswith(("\n", "\r"))
                ) or (
                    index + 1 < len(parts)
                    and parts[index + 1].lower().startswith("<tg-emoji")
                )
                return " " if has_before and has_after else ""

            parts[index] = _NORMAL_EMOJI_RUN_RE.sub(replace_emoji_run, part)
    return "".join(parts)


def normalize_body_formatting(text):
    """Keep body copy normal, except for the service names requested by the user."""
    if not text:
        return text
    normal_text = str(text).translate(_NORMAL_BUTTON_TRANSLATION).translate(_LEGACY_NORMAL_BUTTON_TRANSLATION)
    normal_text = re.sub(r"</?(?:b|strong|i|em)>", "", normal_text, flags=re.IGNORECASE)
    normal_text = strip_normal_emojis(normal_text)
    return bold_service_names(normal_text)

def bold_button_markup(reply_markup, chat_id=None):
    """Bold reply-keyboard labels and only known app names in inline buttons."""
    if not reply_markup:
        return reply_markup
    markup = localize_markup(chat_id, reply_markup) if chat_id is not None else copy.deepcopy(reply_markup)
    is_traffic_markup = any(
        str(button.get("callback_data", "")).startswith(("refresh_traffic", "exp_rng_"))
        for keyboard_key in ("keyboard", "inline_keyboard")
        for row in markup.get(keyboard_key, []) if isinstance(markup, dict)
        for button in row
        if isinstance(button, dict)
    )
    service_pattern = None if is_traffic_markup else _service_name_pattern()
    for keyboard_key in ("keyboard", "inline_keyboard"):
        for row in markup.get(keyboard_key, []) if isinstance(markup, dict) else []:
            for button in row:
                if isinstance(button, dict) and not is_traffic_markup:
                    icon_id = str(button.get("icon_custom_emoji_id", ""))
                    button_text = str(button.get("text", "")).strip().casefold()
                    callback_data = str(button.get("callback_data", "")).casefold()
                    is_back_button = (
                        bool(re.search(r"\bback\b", button_text))
                        or button_text.startswith("back_")
                        or callback_data.startswith("back_")
                        or "পেছনে" in button_text
                        or "পিছনে" in button_text
                        or "ফিরে" in button_text
                    )
                    is_close_button = (
                        bool(re.search(r"\b(cancel|close)\b", button_text))
                        or bool(re.search(r"\b(cancel|close)\b", callback_data))
                        or button_text in {"বন্ধ করুন", "বাতিল", "বাতিল করুন"}
                    )
                    if is_back_button:
                        button["icon_custom_emoji_id"] = BACK_BUTTON_EMOJI_ID
                    elif is_close_button:
                        button["text"] = "Close"
                        button["icon_custom_emoji_id"] = CROSS_CANCEL_EMOJI_ID
                    elif icon_id in {"5420130255174145507", "5267490665117275176"}:
                        button["icon_custom_emoji_id"] = CROSS_CANCEL_EMOJI_ID
                if isinstance(button, dict) and "text" in button:
                    button["text"] = strip_normal_emojis(button["text"])
                    if keyboard_key == "keyboard":
                        button["text"] = bold_button_text(button["text"])
                    else:
                        button_text = str(button["text"])
                        button["text"] = (
                            service_pattern.sub(
                                lambda match: bold_button_text(match.group(1)),
                                button_text,
                            )
                            if service_pattern else button_text
                        )
                    button["text"] = small_caps_button_text(button["text"])
    return markup


def _system_settings_button_key(text):
    normalized = normal_button_text(text).strip().casefold()
    if (
        re.search(r"\b(cancel|close)\b", normalized)
        or normalized in {"বন্ধ করুন", "বাতিল", "বাতিল করুন"}
    ):
        return "close"
    return normalized


def _system_settings_reply_markup(chat_id, reply_markup):
    """Convert admin inline callbacks into the reference bot's reply keyboards."""
    if (
        chat_id not in system_settings_reply_sessions
        or not isinstance(reply_markup, dict)
    ):
        return reply_markup

    # Match the working reference bot: use an ordinary resized reply keyboard.
    # In particular, do not add persistence/one-time flags that its menus omit.
    if isinstance(reply_markup.get("keyboard"), list):
        markup = copy.deepcopy(reply_markup)
        markup["resize_keyboard"] = True
        markup.pop("is_persistent", None)
        markup.pop("one_time_keyboard", None)
        return markup

    if not isinstance(reply_markup.get("inline_keyboard"), list):
        return reply_markup

    keyboard = []
    actions = {}
    unsupported_button_fields = {
        "callback_data", "url", "login_url", "web_app", "switch_inline_query",
        "switch_inline_query_current_chat", "switch_inline_query_chosen_chat",
        "callback_game", "pay",
    }
    for row in reply_markup["inline_keyboard"]:
        reply_row = []
        for button in row:
            if not isinstance(button, dict) or not button.get("text"):
                continue
            callback_data = button.get("callback_data")
            if callback_data is None:
                continue
            source_text = strip_normal_emojis(str(button["text"]))
            actions[_system_settings_button_key(source_text)] = str(callback_data)
            localized_text = strip_normal_emojis(
                localize_ui_text(chat_id, source_text)
            )
            actions[_system_settings_button_key(localized_text)] = str(callback_data)
            reply_row.append({
                key: copy.deepcopy(value)
                for key, value in button.items()
                if key not in unsupported_button_fields
            })
        if reply_row:
            keyboard.append(reply_row)

    if not keyboard:
        return reply_markup
    system_settings_reply_actions[chat_id] = actions
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
    }


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    body_text = normalize_body_formatting(localize_ui_text(chat_id, text))
    payload = {"chat_id": chat_id, "text": body_text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    reply_markup = _system_settings_reply_markup(chat_id, reply_markup)
    if reply_markup:
        payload["reply_markup"] = bold_button_markup(reply_markup, chat_id)
    result = api_call("sendMessage", payload)
    if (
        chat_id in system_settings_reply_sessions
        and isinstance(reply_markup, dict)
        and isinstance(reply_markup.get("keyboard"), list)
        and isinstance(result, dict)
        and result.get("ok")
    ):
        result_message_id = result.get("result", {}).get("message_id")
        if result_message_id:
            system_settings_message_ids[chat_id] = result_message_id
    return result


def get_configured_admin_ids():
    """Return hard-coded owner/admin IDs and admins restored from bot settings."""
    values = [OWNER_ID] + list(ALL_ADMIN_IDS)
    for value in bot_settings.get("admins", []) if isinstance(bot_settings, dict) else []:
        try:
            values.append(int(value))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(values))


_ADMIN_CALLBACK_EXACT = frozenset({
    "backup_all_data", "restore_all_data", "restore_confirm", "restore_cancel",
    "delete_all_data", "delete_all_data_yes", "local_db_status",
    "export_data", "user_management", "member_admin_management",
    "um_manage_balance", "um_ban_unban", "um_user_profile",
    "menu_design_list", "md_reset_defaults", "test_message_flow",
    "broadcast_msg",
    "upload_num", "delete_files", "show_used", "show_unused", "dl_used",
    "dl_unused", "lb_main", "back_to_admin", "back_to_number_management",
    "back_to_delete_management", "toggle_join_notify",
    "system_settings", "toggle_demo", "set_demo_interval", "stex_control", "toggle_stex_auto", "add_stex_key",
    "view_stex_keys", "stex_search_country", "add_search_country",
    "manage_stex_srv", "nx_add_srv", "voltx_control", "toggle_voltx_auto",
    "add_voltx_key", "view_voltx_keys", "voltx_search_country",
    "add_voltx_search_country", "manage_voltx_srv", "vx_add_srv",
    "zenex_control", "toggle_zenex_auto", "add_zenex_key", "view_zenex_keys",
    "fastx_control", "add_fastx_key", "view_fastx_keys",
    "zenex_search_country", "add_zenex_search_country", "manage_zenex_srv",
    "toggle_fastx_auto", "fastx_search_country", "add_fastx_search_country",
    "manage_fastx_srv",
    "zx_add_srv", "manage_fj", "toggle_fj", "add_fj", "manage_admins",
    "add_adm", "manage_otp_groups",
    "add_fw", "edit_otp_link",
    "manage_panels", "manage_api_panels", "manage_cpt_panels",
    "add_api_panel", "add_cpt_panel", "list_del_api", "list_del_cpt",
    "GX_control", "GX_toggle_w", "manage_w_methods", "add_wm",
    "panel_otp_rates", "cancel_GX_edit",
})

_ADMIN_CALLBACK_PREFIXES = (
    "md_edit_", "md_text_", "md_btns_", "md_addbtn_", "md_delbtn_",
    "del_b_", "lb_", "stex_", "del_nxa_", "del_sc_", "nx_",
    "voltx_", "del_vtx_", "del_vsc_", "vx_", "zenex_", "del_znx_", "fx_",
    "del_zsc_", "zx_", "del_fastx_key_", "del_fj_", "del_adm_", "manage_fw_",
    "add_fwbtn_", "del_fwbtn_", "del_fw_", "tog_pnl_", "conf_pnl_",
    "set_p_", "test_p_conn_", "do_del_pnl_", "GX_",
    "del_wm_", "panel_rate_", "um_bal_", "um_blocked_users_page_",
)


def is_admin_callback(data):
    """Identify callbacks that must never be handled by ordinary users."""
    return (
        data in _ADMIN_CALLBACK_EXACT
        or any(data.startswith(prefix) for prefix in _ADMIN_CALLBACK_PREFIXES)
    )


def send_photo(chat_id, photo_url_or_file_id, caption="", reply_markup=None, parse_mode="HTML"):
    body_caption = normalize_body_formatting(localize_ui_text(chat_id, caption))
    payload = {"chat_id": chat_id, "photo": photo_url_or_file_id, "caption": body_caption, "parse_mode": parse_mode}
    reply_markup = _system_settings_reply_markup(chat_id, reply_markup)
    if reply_markup: payload["reply_markup"] = bold_button_markup(reply_markup, chat_id)
    result = api_call("sendPhoto", payload)
    if (
        chat_id in system_settings_reply_sessions
        and isinstance(reply_markup, dict)
        and isinstance(reply_markup.get("keyboard"), list)
        and isinstance(result, dict)
        and result.get("ok")
    ):
        result_message_id = result.get("result", {}).get("message_id")
        if result_message_id:
            system_settings_message_ids[chat_id] = result_message_id
    return result

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    body_text = normalize_body_formatting(localize_ui_text(chat_id, text))
    payload = {"chat_id": chat_id, "message_id": message_id, "text": body_text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    reply_markup = _system_settings_reply_markup(chat_id, reply_markup)
    if (
        chat_id in system_settings_reply_sessions
        and isinstance(reply_markup, dict)
        and isinstance(reply_markup.get("keyboard"), list)
    ):
        # Telegram reply keyboards belong to a newly sent message. Send that
        # replacement without deleting the current keyboard first: removing
        # the active keyboard message creates a gap where Android Telegram can
        # raise the typing keyboard. The reference bot keeps prior menu
        # messages in chat and sends each next menu as a fresh message.
        result = send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        replacement_id = (
            result.get("result", {}).get("message_id")
            if isinstance(result, dict) and result.get("ok")
            else None
        )
        if replacement_id:
            system_settings_message_ids[chat_id] = replacement_id
            state_data = temp_data.get(chat_id)
            if isinstance(state_data, dict) and state_data.get("msg_id") == message_id:
                state_data["msg_id"] = replacement_id
        return result
    if reply_markup:
        payload["reply_markup"] = bold_button_markup(reply_markup, chat_id)
    result = api_call("editMessageText", payload)
    if (
        chat_id in system_settings_reply_sessions
        and isinstance(reply_markup, dict)
        and isinstance(reply_markup.get("keyboard"), list)
    ):
        system_settings_message_ids[chat_id] = message_id
    return result

def delete_message(chat_id, message_id):
    return api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def answer_callback(callback_id, text="", show_alert=False):
    if callback_id == "__reply_keyboard__":
        return
    text = strip_normal_emojis(text)
    api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text, "show_alert": show_alert})

def send_document(chat_id, filename, text_content):
    url = f"{BASE_URL}/sendDocument"
    files = {'document': (filename, text_content)}
    data = {'chat_id': chat_id}
    try:
        response = requests.post(url, data=data, files=files, timeout=60)
        if response.content:
            result = response.json()
        else:
            result = {"ok": response.ok, "description": response.text[:300]}
        _record_bot_delivery_result(chat_id, result)
        return result
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


PERSISTENT_COLLECTIONS = ("users", "history", "withdrawals")


def _export_database_collections():
    """Export the local user, withdrawal and history collections."""
    if not db:
        raise RuntimeError("Local database is unavailable.")
    return {
        collection_name: {
            snapshot.id: snapshot.to_dict()
            for snapshot in db.collection(collection_name).stream()
        }
        for collection_name in PERSISTENT_COLLECTIONS
    }




def build_full_backup():
    """Return a backup of durable local data and bot runtime state."""
    collections = _export_database_collections()
    runtime_state = {
        "bot_settings": copy.deepcopy(bot_settings),
        "number_batches": copy.deepcopy(number_batches),
        "used_numbers_list": copy.deepcopy(used_numbers_list),
        "stex_assigned_numbers": copy.deepcopy(stex_assigned_numbers),
        "voltx_assigned_numbers": copy.deepcopy(voltx_assigned_numbers),
        "zenex_assigned_numbers": copy.deepcopy(zenex_assigned_numbers),
        "fastx_assigned_numbers": copy.deepcopy(fastx_assigned_numbers),
        "assigned_number_rates": copy.deepcopy(assigned_number_rates),
        "total_uploaded_stats": total_uploaded_stats,
        "total_assigned_stats": total_assigned_stats,
        "processed_otps": _processed_otp_snapshot(),
        "recent_traffic": copy.deepcopy(recent_traffic),
    }
    return {
        "backup_format": "gx-number-bot-full-state",
        "backup_version": 5,
        "created_at": iso_now(),
        "data_month": data_month,
        "persistent_source": "local_json_database",
        "admin_panel": {
            "settings": copy.deepcopy(bot_settings),
            "runtime": copy.deepcopy(runtime_state),
        },
        "collections": collections,
        "runtime": runtime_state,
    }




def _stable_json_key(value):
    """Create a deterministic key for de-duplicating JSON-compatible values."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _unique_values(existing, incoming):
    """Append new list values without changing the existing order."""
    result = []
    seen = set()
    for value in list(existing or []) + list(incoming or []):
        key = _stable_json_key(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(copy.deepcopy(value))
    return result


def _merge_settings(existing, incoming):
    """Merge imported settings without deleting settings already in the bot."""
    if not isinstance(existing, dict):
        existing = {}
    if not isinstance(incoming, dict):
        return copy.deepcopy(existing)
    result = copy.deepcopy(existing)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_settings(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            result[key] = _unique_values(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _merge_number_batches(existing, incoming):
    """Merge number files and de-duplicate numbers inside each matching file."""
    result = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    if not isinstance(incoming, dict):
        return result
    for batch_id, imported_batch in incoming.items():
        batch_key = str(batch_id)
        if not isinstance(imported_batch, dict):
            continue
        current_batch = result.get(batch_key)
        if not isinstance(current_batch, dict):
            current_batch = {}
        merged_batch = _merge_settings(current_batch, imported_batch)
        old_numbers = current_batch.get("numbers", [])
        new_numbers = imported_batch.get("numbers", [])
        if isinstance(old_numbers, list) and isinstance(new_numbers, list):
            # Numbers are unique by their actual "num" value, not by the
            # complete object, because used_by/rate metadata can differ.
            merged_numbers = []
            number_indexes = {}
            for item in old_numbers + new_numbers:
                if not isinstance(item, dict):
                    key = _stable_json_key(item)
                    if key not in number_indexes:
                        number_indexes[key] = len(merged_numbers)
                        merged_numbers.append(copy.deepcopy(item))
                    continue
                number_key = str(item.get("num", "")).strip()
                key = f"num:{number_key}" if number_key else _stable_json_key(item)
                if key not in number_indexes:
                    number_indexes[key] = len(merged_numbers)
                    merged_numbers.append(copy.deepcopy(item))
                    continue
                index = number_indexes[key]
                old_item = merged_numbers[index]
                if isinstance(old_item, dict):
                    merged_numbers[index] = _merge_settings(old_item, item)
                    if isinstance(old_item.get("used_by"), list) and isinstance(
                        item.get("used_by"), list
                    ):
                        merged_numbers[index]["used_by"] = _unique_values(
                            old_item["used_by"], item["used_by"]
                        )
            merged_batch["numbers"] = merged_numbers
        result[batch_key] = merged_batch
    return result


def _deduplicate_number_batches(batches):
    """Keep one copy of a number even when it appears in different files."""
    if not isinstance(batches, dict):
        return {}
    result = copy.deepcopy(batches)
    seen_numbers = set()
    for batch in result.values():
        if not isinstance(batch, dict) or not isinstance(batch.get("numbers"), list):
            continue
        unique_numbers = []
        for item in batch["numbers"]:
            if isinstance(item, dict):
                number_key = str(item.get("num", "")).strip()
                if number_key:
                    if number_key in seen_numbers:
                        continue
                    seen_numbers.add(number_key)
            unique_numbers.append(item)
        batch["numbers"] = unique_numbers
    return result


def _merge_collection_maps(current, imported):
    """Merge records by document ID; imported values win on the same ID."""
    result = copy.deepcopy(current) if isinstance(current, dict) else {}
    if not isinstance(imported, dict):
        return result
    for document_id, value in imported.items():
        key = str(document_id)
        if not isinstance(value, dict):
            continue
        if isinstance(result.get(key), dict):
            result[key] = _merge_record_values(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def send_full_backup(chat_id):
    try:
        payload = json.dumps(
            build_full_backup(), ensure_ascii=False, indent=2, default=str
        ).encode("utf-8")
    except Exception as exc:
        send_message(
            chat_id,
            render_body_text(
                f"❌ <b>Backup stopped:</b> <code>{html.escape(str(exc))}</code>"
            ),
        )
        return False
    result = send_document(
        chat_id, f"bot_full_backup_{data_month_key()}.json", payload
    )
    if not result or not result.get("ok"):
        description = html.escape(
            str((result or {}).get("description", "Telegram upload failed"))
        )
        send_message(
            chat_id,
            render_body_text(
                f"❌ <b>Backup upload failed:</b> <code>{description}</code>"
            ),
        )
        return False
    send_message(
        chat_id,
        render_body_text(
            '<tg-emoji emoji-id="6201914938424827608">✅</tg-emoji> '
            '<b>Full backup created and sent.</b>\n'
            "The JSON contains the complete local Users, Withdrawals and History data, "
            "Admin Panel settings, number stock, provider configuration and runtime counters. "
            "Telegram tokens are never exported."
        ),
    )
    return True


def restore_full_backup(backup):
    """Merge a validated JSON, CSV or Excel backup into local bot data."""
    global data_month
    global bot_settings, number_batches, used_numbers_list
    global stex_assigned_numbers, voltx_assigned_numbers
    global zenex_assigned_numbers, fastx_assigned_numbers, assigned_number_rates
    global total_uploaded_stats, total_assigned_stats
    global processed_otps, recent_traffic
    if not isinstance(backup, dict):
        raise ValueError("Backup must contain valid bot data.")
    collections = copy.deepcopy(backup.get("collections", {}))
    if not isinstance(collections, dict):
        raise ValueError("Backup collections are invalid.")
    # Older/manual backups can carry user/history arrays or exported workbook tabs.
    legacy_tabs = (backup.get("google_sheets") or {}).get("tabs", {})
    if isinstance(legacy_tabs, dict):
        for old_name, new_name in (("Users", "users"), ("Withdrawals", "withdrawals"), ("History", "history")):
            if new_name not in collections and isinstance(legacy_tabs.get(old_name), list):
                collections[new_name] = legacy_tabs[old_name]
    for name in ("users", "history", "withdrawals"):
        if name not in collections and name in backup:
            collections[name] = backup[name]

    collections["users"] = _deduplicate_collection_rows(
        collections.get("users", {}), "users"
    )
    collections["users"] = _normalize_user_otp_timestamps(
        collections["users"]
    )
    collections["history"] = _deduplicate_collection_rows(
        collections.get("history", {}), "history"
    )
    collections["withdrawals"] = _deduplicate_collection_rows(
        collections.get("withdrawals", {}), "withdrawals"
    )

    # A restore is additive. Existing records remain, while a matching
    # document ID is treated as the same record and updated from the file.
    current_collections = {
        collection_name: _deduplicate_collection_rows(
            {
                snapshot.id: snapshot.to_dict()
                for snapshot in db.collection(collection_name).stream()
            },
            collection_name,
        )
        for collection_name in PERSISTENT_COLLECTIONS
    }
    for collection_name in PERSISTENT_COLLECTIONS:
        collections[collection_name] = _merge_collection_maps(
            current_collections.get(collection_name, {}),
            collections.get(collection_name, {}),
        )

    runtime_state = backup.get("runtime")
    is_full_state_backup = isinstance(runtime_state, dict)
    if is_full_state_backup:
        imported_settings = runtime_state.get("bot_settings")
        imported_batches = runtime_state.get("number_batches")
        if not isinstance(imported_settings, dict):
            raise ValueError("Full backup is missing bot settings.")
        if not isinstance(imported_batches, dict):
            raise ValueError("Full backup is missing number batches.")
        imported_runtime_maps = {
            "stex_assigned_numbers": runtime_state.get("stex_assigned_numbers", {}),
            "voltx_assigned_numbers": runtime_state.get("voltx_assigned_numbers", {}),
            "zenex_assigned_numbers": runtime_state.get("zenex_assigned_numbers", {}),
            "fastx_assigned_numbers": runtime_state.get("fastx_assigned_numbers", {}),
            "assigned_number_rates": runtime_state.get("assigned_number_rates", {}),
        }
        if any(not isinstance(value, dict) for value in imported_runtime_maps.values()):
            raise ValueError("Full backup contains invalid assignment data.")
        imported_used_numbers = runtime_state.get("used_numbers_list", [])
        imported_processed_otps = runtime_state.get("processed_otps", [])
        imported_recent_traffic = runtime_state.get("recent_traffic", [])
        if not isinstance(imported_used_numbers, list):
            raise ValueError("Full backup used_numbers_list is invalid.")
        if not isinstance(imported_processed_otps, list):
            raise ValueError("Full backup processed_otps is invalid.")
        if not isinstance(imported_recent_traffic, list):
            raise ValueError("Full backup recent_traffic is invalid.")

        # Merge settings/files so a restore never deletes data that exists only
        # in the current bot. Keep the configured owner as an emergency admin.
        bot_settings = _merge_settings(bot_settings, imported_settings)
        admins = bot_settings.get("admins", [])
        if not isinstance(admins, list):
            admins = []
        bot_settings["admins"] = list(dict.fromkeys(
            [int(item) if str(item).lstrip("-").isdigit() else item for item in admins]
            + ALL_ADMIN_IDS
        ))
        number_batches = _deduplicate_number_batches(
            _merge_number_batches(number_batches, imported_batches)
        )
        used_numbers_list = _unique_values(
            used_numbers_list, imported_used_numbers
        )
        stex_assigned_numbers = {
            **stex_assigned_numbers,
            **copy.deepcopy(imported_runtime_maps["stex_assigned_numbers"]),
        }
        voltx_assigned_numbers = {
            **voltx_assigned_numbers,
            **copy.deepcopy(imported_runtime_maps["voltx_assigned_numbers"]),
        }
        zenex_assigned_numbers = {
            **zenex_assigned_numbers,
            **copy.deepcopy(imported_runtime_maps["zenex_assigned_numbers"]),
        }
        fastx_assigned_numbers = {
            **fastx_assigned_numbers,
            **copy.deepcopy(imported_runtime_maps["fastx_assigned_numbers"]),
        }
        assigned_number_rates = {
            **assigned_number_rates,
            **copy.deepcopy(imported_runtime_maps["assigned_number_rates"]),
        }
        total_uploaded_stats = max(
            int(total_uploaded_stats or 0),
            int(runtime_state.get("total_uploaded_stats", 0) or 0),
        )
        total_assigned_stats = max(
            int(total_assigned_stats or 0),
            int(runtime_state.get("total_assigned_stats", 0) or 0),
        )
        _restore_processed_otp_ids(
            _unique_values(_processed_otp_snapshot(), imported_processed_otps)
        )
        recent_traffic = _unique_values(
            recent_traffic, imported_recent_traffic
        )

        # These objects contain Telegram message IDs/provider sessions and are
        # intentionally reset instead of reviving stale live sessions.
        user_active_sessions.clear()
        user_cooldowns.clear()
        user_states.clear()
        temp_data.clear()
        with number_allocation_lock:
            claimed_numbers.clear()
        panel_sessions.clear()
        panel_api_cache.clear()

    _restore_rows_to_runtime({
        "Users": list(collections["users"].values()),
        "Withdrawals": list(collections["withdrawals"].values()),
        "History": list(collections["history"].values()),
    })
    user_banned_cache.clear()
    user_states.clear()
    temp_data.clear()
    user_cooldowns.clear()
    data_month = str(backup.get("data_month") or data_month_key())
    if is_full_state_backup:
        # Save the merged runtime state. Existing settings are intentionally
        # retained; save_db updates only the current merged documents.
        save_db()
    save_local_db()
    return {
        "users": len(collections["users"]),
        "withdrawals": len(collections["withdrawals"]),
        "history": len(collections["history"]),
        "number_batches": len(number_batches),
        "full_state": is_full_state_backup,
    }


def delete_all_bot_data():
    """Reset operational data while keeping the owner able to open the bot."""
    global bot_settings, number_batches, total_uploaded_stats, total_assigned_stats
    global data_month, local_users, audit_history, all_known_users, claimed_numbers
    number_batches.clear()
    total_uploaded_stats = 0
    total_assigned_stats = 0
    used_numbers_list.clear()
    with number_allocation_lock:
        claimed_numbers.clear()
    stex_assigned_numbers.clear()
    voltx_assigned_numbers.clear()
    zenex_assigned_numbers.clear()
    fastx_assigned_numbers.clear()
    assigned_number_rates.clear()
    _restore_processed_otp_ids([])
    recent_traffic.clear()
    local_users.clear()
    audit_history.clear()
    all_known_users.clear()
    user_cache.clear()
    user_banned_cache.clear()
    pending_withdrawals.clear()
    user_active_sessions.clear()
    user_states.clear()
    temp_data.clear()
    user_cooldowns.clear()
    bot_settings = {
        "admins": ALL_ADMIN_IDS.copy(),
        "panels": [],
        "fw_groups": [],
        "otp_link": "https://t.me/your_otp_group",
        "otp_forward_channel_button": True,
        "otp_forward_support_button": True,
        "withdraw_on": True,
        "join_notifications": {str(OWNER_ID): True},
        "min_withdraw": 30.0,
        "otp_reward": 0.1,
        "refer_reward": 0.5,
        "cooldown": 10,
        "num_req": 3,
        "num_share": 1,
        "support_link": "https://t.me/your_support",
        "w_methods": ["bKash", "Nagad"],
        "w_group": "",
        "fj_on": False,
        "fj_channels": [],
        "stex_keys": [],
        "voltx_keys": [],
        "zenex_keys": [],
        "fastx_keys": [],
        "search_countries": [],
        "voltx_search_countries": [],
        "zenex_search_countries": [],
        "fastx_search_countries": [],
        "fastx_auto": False,
        "stex_services": {},
        "voltx_services": {},
        "zenex_services": {},
        "fastx_services": {},
        "premium_flags": copy.deepcopy(DEFAULT_PREMIUM_FLAGS),
        "premium_apps": copy.deepcopy(DEFAULT_PREMIUM_APPS),
        "custom_messages": copy.deepcopy(DEFAULT_CUSTOM_MESSAGES),
    }
    data_month = data_month_key()
    for collection_name in ("users", "history", "withdrawals", "settings", "runtime_state"):
        _clear_database_collection(collection_name)
    save_local_db()
    save_db()
    _save_users_list()


EXPORT_USER_FIELDS = [
    "user_name", "username", "user_id", "balance", "otp", "total_refers",
    "total_otps", "otp_timestamps", "banned", "verified", "language", "created_at",
    "updated_at", "referred_by", "ref_paid", "ref_bonus_last_otp",
    "referral_bonus_progress", "otp_bonus_notifications"
]
EXPORT_HISTORY_FIELDS = [
    "event_id", "timestamp", "user_id", "event_type", "amount", "status",
    "method", "request_id", "balance_after", "payment_number", "message"
]


def _export_value(value):
    if value is None:
        return ""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=isinstance(value, dict),
            default=str,
        )
    if isinstance(value, set):
        return json.dumps(sorted(value, key=str), ensure_ascii=False, default=str)
    return str(value)


def collect_export_rows():
    users = []
    history = []
    if db:
        try:
            for snapshot in db.collection("users").stream():
                row = snapshot.to_dict()
                if _is_group_or_channel_record(row):
                    continue
                row["user_id"] = row.get("user_id", snapshot.id)
                row["user_name"] = row.get("user_name", row.get("full_name", ""))
                row["username"] = _normalize_username(row.get("username", ""))
                for key in EXPORT_USER_FIELDS:
                    row.setdefault(key, "")
                users.append(row)
        except Exception:
            pass
        try:
            for snapshot in db.collection("history").order_by("timestamp", direction="DESCENDING").stream():
                row = snapshot.to_dict()
                for key in EXPORT_HISTORY_FIELDS:
                    row.setdefault(key, "")
                history.append(row)
        except Exception:
            pass
    else:
        for key, row in local_users.items():
            row = dict(row)
            if _is_group_or_channel_record(row):
                continue
            row["user_id"] = row.get("user_id", key)
            row["user_name"] = row.get("user_name", row.get("full_name", ""))
            row["username"] = _normalize_username(row.get("username", ""))
            for field in EXPORT_USER_FIELDS:
                row.setdefault(field, "")
            users.append(row)
        history = [
            dict(row)
            for row in audit_history
        ]

    users = list(_deduplicate_collection_rows(users, "users").values())
    history = list(_deduplicate_collection_rows(history, "history").values())
    users.sort(key=lambda row: str(row.get("user_id", "")))
    history.sort(key=lambda row: str(row.get("event_id", "")))
    return users, history


def _make_csv(headers, rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _export_value(row.get(key, "")) for key in headers})
    return output.getvalue().encode("utf-8-sig")


def _xlsx_cell(value, reference="A1"):
    text = xml_escape(_export_value(value))
    return f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>'


def _xlsx_sheet(headers, rows):
    all_rows = [headers] + [[row.get(key, "") for key in headers] for row in rows]
    body = []
    for row_number, row in enumerate(all_rows, 1):
        cells = ""
        for column_number, value in enumerate(row):
            number = column_number + 1
            letters = ""
            while number:
                number, remainder = divmod(number - 1, 26)
                letters = chr(65 + remainder) + letters
            cells += _xlsx_cell(value, f"{letters}{row_number}")
        body.append(f'<row r="{row_number}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>' + "".join(body) + '</sheetData></worksheet>'
    )


def make_xlsx(users, history, withdrawals=None):
    withdrawals = withdrawals or []
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Users" sheetId="1" r:id="rId1"/>'
        '<sheet name="Withdrawals" sheetId="2" r:id="rId2"/>'
        '<sheet name="History" sheetId="3" r:id="rId3"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", _xlsx_sheet(EXPORT_USER_FIELDS, users))
        archive.writestr(
            "xl/worksheets/sheet2.xml",
            _xlsx_sheet(
                ["request_id", "user_id", "amount", "method", "number",
                 "full_name", "status", "timestamp", "balance_after"],
                withdrawals,
            ),
        )
        archive.writestr(
            "xl/worksheets/sheet3.xml",
            _xlsx_sheet(EXPORT_HISTORY_FIELDS, history),
        )
    return output.getvalue()


def _xlsx_column_number(cell_reference):
    letters = re.match(r"([A-Z]+)", str(cell_reference or "").upper())
    if not letters:
        return 0
    number = 0
    for char in letters.group(1):
        number = number * 26 + ord(char) - ord("A") + 1
    return number - 1


def _xlsx_xml_text(node):
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _read_xlsx_sheets(raw_bytes):
    """Read ordinary XLSX backups without openpyxl."""
    namespace = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as archive:
        names = set(archive.namelist())
        shared_strings = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                _xlsx_xml_text(item)
                for item in root.findall("main:si", namespace)
            ]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationship_root = ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        relationships = {}
        for rel in relationship_root.findall("pkg:Relationship", namespace):
            target = rel.attrib.get("Target", "")
            if not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            relationships[rel.attrib.get("Id", "")] = target

        result = {}
        for sheet in workbook.findall("main:sheets/main:sheet", namespace):
            title = sheet.attrib.get("name", "Sheet")
            relation_id = sheet.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id",
                "",
            )
            target = relationships.get(relation_id)
            if not target or target not in names:
                continue
            root = ET.fromstring(archive.read(target))
            matrix = []
            for row in root.findall(".//main:sheetData/main:row", namespace):
                values = {}
                for cell in row.findall("main:c", namespace):
                    cell_type = cell.attrib.get("t", "")
                    value_node = cell.find("main:v", namespace)
                    if cell_type == "inlineStr":
                        value = _xlsx_xml_text(cell.find("main:is", namespace))
                    else:
                        value = _xlsx_xml_text(value_node)
                        if cell_type == "s" and value.isdigit():
                            index = int(value)
                            value = (
                                shared_strings[index]
                                if index < len(shared_strings) else ""
                            )
                    values[_xlsx_column_number(cell.attrib.get("r", ""))] = value
                if values:
                    width = max(values) + 1
                    matrix.append([values.get(index, "") for index in range(width)])
            if not matrix:
                result[title] = []
                continue
            headers = [str(value).strip() for value in matrix[0]]
            rows = []
            for values in matrix[1:]:
                if not any(str(value).strip() for value in values):
                    continue
                rows.append({
                    header: values[index] if index < len(values) else ""
                    for index, header in enumerate(headers) if header
                })
            result[title] = rows
    return result


def xlsx_to_backup(raw_bytes):
    sheets = _read_xlsx_sheets(raw_bytes)
    collections = {"users": {}, "withdrawals": {}, "history": {}}
    for title, rows in sheets.items():
        lowered = str(title).strip().lower()
        if lowered in ("users", "user", "user data"):
            target, id_field = "users", "user_id"
        elif lowered in ("withdrawals", "withdrawal", "withdraw history"):
            target, id_field = "withdrawals", "request_id"
        elif lowered in ("history", "events", "transactions"):
            target, id_field = "history", "event_id"
        elif rows and "request_id" in rows[0]:
            target, id_field = "withdrawals", "request_id"
        elif rows and "user_id" in rows[0]:
            target, id_field = "users", "user_id"
        else:
            continue
        for index, row in enumerate(rows):
            key = str(row.get(id_field) or f"RESTORED_{target}_{index + 1}")
            collections[target][key] = row
    if not any(collections.values()):
        raise ValueError("No Users, Withdrawals or History records were found in the workbook.")
    return {
        "backup_format": "xlsx-records",
        "backup_version": 2,
        "created_at": iso_now(),
        "collections": collections,
    }


def csv_to_backup(raw_bytes):
    text = raw_bytes.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("The CSV file contains no rows.")
    headers = set(rows[0])
    if "request_id" in headers:
        target, id_field = "withdrawals", "request_id"
    elif "event_type" in headers or "event_id" in headers:
        target, id_field = "history", "event_id"
    else:
        target, id_field = "users", "user_id"
    return {
        "backup_format": "csv-records",
        "backup_version": 2,
        "created_at": iso_now(),
        "collections": {
            "users": {
                str(row.get("user_id") or f"RESTORED_{index + 1}"): row
                for index, row in enumerate(rows)
            } if target == "users" else {},
            "withdrawals": {
                str(row.get("request_id") or f"RESTORED_{index + 1}"): row
                for index, row in enumerate(rows)
            } if target == "withdrawals" else {},
            "history": {
                str(row.get("event_id") or f"RESTORED_{index + 1}"): row
                for index, row in enumerate(rows)
            } if target == "history" else {},
        },
    }


def _pdf_safe(text):
    text = unicodedata.normalize("NFKD", _export_value(text))
    text = text.encode("ascii", "replace").decode("ascii")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(users, history):
    lines = [
        "BOT DATA EXPORT",
        f"Generated: {iso_now()}",
        f"Users: {len(users)} | History events: {len(history)}",
        "",
        "USERS"
    ]
    lines.append(" | ".join(EXPORT_USER_FIELDS))
    for row in users:
        lines.append(" | ".join(_export_value(row.get(key, "")) for key in EXPORT_USER_FIELDS))
    lines.extend(["", "HISTORY"])
    lines.append(" | ".join(EXPORT_HISTORY_FIELDS))
    for row in history:
        lines.append(" | ".join(_export_value(row.get(key, "")) for key in EXPORT_HISTORY_FIELDS))

    lines = [_pdf_safe(line[:150]) for line in lines]
    page_lines = [lines[i:i + 48] for i in range(0, len(lines), 48)] or [["No data"]]
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"
    ]
    page_ids = []
    for page in page_lines:
        stream_lines = ["BT", "/F1 7 Tf", "28 805 Td", "9 TL"]
        for line in page:
            stream_lines.append(f"({_pdf_safe(line)}) Tj")
            stream_lines.append("T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", "replace")
        content_id = len(objects) + 1
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode('latin-1')}\nendstream")
        page_id = len(objects) + 1
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>")
        page_ids.append(page_id)
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>"

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj.encode("latin-1", "replace"))
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)


def send_data_export(chat_id):
    users, history = collect_export_rows()
    withdrawals = []
    for snapshot in db.collection("withdrawals").order_by("timestamp", direction="DESCENDING").stream():
        row = snapshot.to_dict()
        row["request_id"] = row.get("request_id", snapshot.id)
        if not _is_group_or_channel_record(row):
            withdrawals.append(row)
    if not users and not history:
        send_message(chat_id, render_body_text("❌ No user/history data is available for export."))
        return
    month = data_month_key()
    send_document(chat_id, f"bot_data_{month}.csv", _make_csv(EXPORT_USER_FIELDS, users))
    send_document(chat_id, f"bot_history_{month}.csv", _make_csv(EXPORT_HISTORY_FIELDS, history))
    send_document(chat_id, f"bot_data_{month}.xlsx", make_xlsx(users, history, withdrawals))
    send_document(chat_id, f"bot_data_{month}.pdf", make_pdf(users, history))
    send_message(chat_id, render_body_text(
        f"{PEM['ok']} <b>Export complete.</b>\n"
        f"Users: {len(users)} | History events: {len(history)}\n"
        "CSV, Excel and PDF files were sent."
    ))

all_known_users = set()
bot_delivery_state_lock = threading.RLock()


def _record_bot_delivery_result(chat_id, result):
    """Remember users Telegram reports as blocking the bot; clear after delivery works."""
    user_id = str(chat_id or "").strip()
    if not user_id or user_id not in {str(uid) for uid in all_known_users}:
        return
    if not isinstance(result, dict):
        return

    if result.get("ok") is True:
        blocked = False
    else:
        description = str(result.get("description", "")).lower()
        try:
            error_code = int(result.get("error_code", 0))
        except (TypeError, ValueError):
            error_code = 0
        if error_code != 403 or "bot was blocked by the user" not in description:
            return
        blocked = True

    with bot_delivery_state_lock:
        user = local_users.get(user_id)
        if not isinstance(user, dict):
            try:
                snapshot = db.collection("users").document(user_id).get() if db else None
                if not snapshot or not snapshot.exists:
                    return
                user = snapshot.to_dict() or {}
            except Exception:
                return

        if bool(user.get("bot_blocked", False)) == blocked:
            return
        user["bot_blocked"] = blocked
        local_users[user_id] = user
        try:
            if db:
                db.collection("users").document(user_id).set(
                    {"bot_blocked": blocked}, merge=True
                )
        except Exception:
            pass


def get_blocked_user_ids():
    return sorted(
        str(user_id)
        for user_id in all_known_users
        if isinstance(local_users.get(str(user_id)), dict)
        and local_users[str(user_id)].get("bot_blocked") is True
    )

def sync_users_list():
    global all_known_users
    try:
        all_known_users.clear()
        if db:
            for doc in db.collection('users').select([]).stream():
                all_known_users.add(doc.id)
        else:
            all_known_users.update(str(uid) for uid in local_users.keys())
    except: pass

threading.Thread(target=sync_users_list, daemon=True).start()

def _save_users_list():
    # User IDs are already kept in the bot database; no extra local file.
    return

def register_user_local(uid):
    uid_str = str(uid)
    if uid_str not in all_known_users:
        # users_list.json can be stale after a restart, so avoid treating an
        # already-persisted user as a new joiner.
        already_persisted = uid_str in local_users
        if db and not already_persisted:
            try:
                already_persisted = db.collection("users").document(uid_str).get().exists
            except Exception:
                pass
        all_known_users.add(uid_str)
        threading.Thread(target=_save_users_list, daemon=True).start()
        return not already_persisted
    return False


def get_join_notification_status(admin_id):
    settings = bot_settings.setdefault("join_notifications", {})
    key = str(admin_id)
    if key not in settings:
        settings[key] = True
    value = settings[key]
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on", "enabled"}
    return bool(value)


def notify_admins_new_user(msg, user_id):
    """Notify each admin independently according to their own preference."""
    from_user = msg.get("from", {})
    full_name = " ".join(
        part for part in (from_user.get("first_name", ""), from_user.get("last_name", ""))
        if part
    ).strip() or "Unknown user"
    username = from_user.get("username")
    username_text = f"@{username}" if username else "No username"
    text = (
        "👤 <b>NEW USER JOINED</b>\n\n"
        f"Name: {html.escape(full_name)}\n"
        f"Username: {html.escape(username_text)}\n"
        f"User ID: <code>{user_id}</code>"
    )
    for admin_id in get_configured_admin_ids():
        if get_join_notification_status(admin_id):
            send_message(admin_id, render_body_text(text))

def broadcast_completion_message(success, failed, total):
    return render_body_text(
        '<tg-emoji emoji-id="5789428375261023681">📢</tg-emoji> '
        '<b>Broadcast Send To All Users Successfully</b>'
        '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="6224038684333711964">🌟</tg-emoji> '
        f'Success: {success} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="6224003980997962148">❌</tg-emoji> '
        f'Failed: {failed} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="6224334680594850487">👥</tg-emoji> '
        f'Total Sent: {total} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
    )


def broadcast_copymessage(from_chat_id, msg_id):
    success, failed, total = _broadcast_users(
        all_known_users,
        "copyMessage",
        lambda user_id: {
            "chat_id": user_id,
            "from_chat_id": from_chat_id,
            "message_id": msg_id,
        },
    )
    send_message(from_chat_id, broadcast_completion_message(success, failed, total))

def render_body_text(text):
    if not text: return str(text)
    parts = re.split(r'(<tg-emoji.*?</tg-emoji>)', str(text))
    for i in range(len(parts)):
        if not parts[i].startswith('<tg-emoji'):
            for normal_emj, prem_id in GLOBAL_BODY_EMOJIS.items():
                if normal_emj in parts[i]:
                    parts[i] = parts[i].replace(normal_emj, f'<tg-emoji emoji-id="{prem_id}">{normal_emj}</tg-emoji>')
    return "".join(parts)

def extract_premium_html(msg):
    text = msg.get("text", msg.get("caption", ""))
    entities = msg.get("entities", msg.get("caption_entities", []))
    if not entities: return text
    try:
        b_text = text.encode('utf-16-le')
        c_entities = [e for e in entities if e.get("type") == "custom_emoji"]
        c_entities.sort(key=lambda x: x["offset"], reverse=True)
        for ent in c_entities:
            offset = ent["offset"] * 2
            length = ent["length"] * 2
            eid = ent["custom_emoji_id"]
            emoji_char = b_text[offset:offset+length].decode('utf-16-le')
            html_tag = f'<tg-emoji emoji-id="{eid}">{emoji_char}</tg-emoji>'
            replacement = html_tag.encode('utf-16-le')
            b_text = b_text[:offset] + replacement + b_text[offset+length:]
        return b_text.decode('utf-16-le')
    except Exception as e:
        return text 

def _flag_calling_code(key, data=None):
    if isinstance(data, dict) and data.get("calling_code") is not None:
        return str(data.get("calling_code", "")).strip()
    return str(key or "").split(":", 1)[0].strip()


def get_flag_info_from_num(num):
    clean = num.replace("+", "").replace(" ", "")
    sorted_flags = sorted(
        bot_settings.get("premium_flags", {}).items(),
        key=lambda item: len(_flag_calling_code(item[0], item[1])),
        reverse=True,
    )
    for key, data in sorted_flags:
        code = _flag_calling_code(key, data)
        if not code.isdigit():
            continue
        if clean.startswith(code):
            return data["char"], data.get("iso", "XX"), data.get("id")
    return "🌍", "XX", None

def get_flag_and_code(num):
    char, iso, _ = get_flag_info_from_num(num)
    return char, iso

def get_flag_info_html(num_or_iso, return_full_name=False):
    if len(num_or_iso) == 2:
        for _key, data in bot_settings.get("premium_flags", {}).items():
            if data.get("iso") == num_or_iso:
                eid = data.get("id")
                char = data.get("char")
                name = data.get("name", num_or_iso)
                if return_full_name: return name
                if eid: return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
                return char
        if return_full_name: return num_or_iso
        return "🌍"
        
    char, _, eid = get_flag_info_from_num(num_or_iso)
    if return_full_name:
        for key, data in bot_settings.get("premium_flags", {}).items():
            clean = num_or_iso.replace("+", "").replace(" ", "")
            code = _flag_calling_code(key, data)
            if code.isdigit() and clean.startswith(code):
                return data.get("name", num_or_iso)
        return num_or_iso
        
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
    return char

def mask_number(num):
    """Show a compact country-prefix/GX/last-three group label."""
    value = str(num or "").strip()
    clean = re.sub(r"\D", "", value)
    if not clean:
        return value
    country_prefix = ""
    for raw_code in sorted(
        bot_settings.get("premium_flags", {}).items(),
        key=lambda item: len(re.sub(
            r"\D", "", _flag_calling_code(item[0], item[1])
        )),
        reverse=True,
    ):
        code = re.sub(r"\D", "", _flag_calling_code(raw_code[0], raw_code[1]))
        if code and clean.startswith(code):
            country_prefix = code
            break
    if not country_prefix:
        country_prefix = clean[:3] if len(clean) > 3 else clean
    last_three = clean[-3:] if len(clean) >= 3 else clean
    return f"{country_prefix}GX{last_three}"


def _same_number_request_context(number, service, provider=None):
    """Find the most specific known provider range for a forwarded OTP."""
    digits = _canonical_number(number)
    if not digits:
        return None
    valid_providers = {"stex", "voltx", "zenex", "fastx"}
    requested_provider = str(provider or "").strip().lower()
    if requested_provider not in valid_providers:
        requested_provider = "auto"
    service_name = (
        _canonical_traffic_service(service)
        or _canonical_allowed_service(service)
        or ""
    )

    # A number allocated through the bot already knows the exact range/provider.
    for session in list(user_active_sessions.values()):
        if not isinstance(session, dict):
            continue
        contexts = session.get("number_contexts", {})
        if not isinstance(contexts, dict):
            contexts = {}
        for active_number in session.get("nums", []):
            if _canonical_number(active_number) != digits:
                continue
            context = contexts.get(digits, {})
            if not isinstance(context, dict):
                context = {}
            query = _clean_range_prefix(
                context.get("range") or session.get("request_range")
            )
            context_provider = str(
                context.get("provider") or session.get("provider") or ""
            ).strip().lower()
            context_service = (
                _canonical_traffic_service(
                    context.get("service") or session.get("service")
                )
                or service_name
            )
            if query and digits.startswith(query):
                if requested_provider == "auto" or context_provider == requested_provider:
                    return {
                        "range": query,
                        "provider": context_provider if context_provider in valid_providers else requested_provider,
                        "service": context_service,
                    }

    try:
        _flag, iso = get_flag_and_code(digits)
        country_name = get_flag_info_html(iso, return_full_name=True) or ""
    except Exception:
        iso, country_name = "", ""

    candidates = []
    for item in recent_traffic if isinstance(recent_traffic, list) else []:
        if not isinstance(item, dict) or not _traffic_service_matches(
            item.get("service", ""), service_name or service
        ):
            continue
        item_provider = str(item.get("source") or item.get("panel") or "").lower()
        if requested_provider != "auto" and item_provider != requested_provider:
            continue
        if iso and item.get("iso") and str(item.get("iso")).upper() != str(iso).upper():
            continue
        prefix = _clean_range_prefix(item.get("real_range") or item.get("range"))
        if 4 <= len(prefix) <= 18 and digits.startswith(prefix):
            candidates.append((len(prefix), item_provider, prefix))

    provider_names = (
        [requested_provider]
        if requested_provider != "auto"
        else ["stex", "voltx", "zenex", "fastx"]
    )
    for provider_name in provider_names:
        service_map = bot_settings.get(f"{provider_name}_services", {})
        if isinstance(service_map, dict):
            for configured_service, countries in service_map.items():
                if not _traffic_service_matches(configured_service, service_name or service):
                    continue
                if not isinstance(countries, dict):
                    continue
                for configured_country, ranges in countries.items():
                    if iso and not _country_matches_iso(configured_country, iso):
                        continue
                    if not isinstance(ranges, (list, tuple, set)):
                        ranges = [ranges]
                    for value in ranges:
                        prefix = _clean_range_prefix(value)
                        if 4 <= len(prefix) <= 18 and digits.startswith(prefix):
                            candidates.append((len(prefix), provider_name, prefix))

        for range_value, live_provider in _live_ranges_for_service_country(
            service_name or service,
            country_name or None,
            provider_name,
        ):
            prefix = _clean_range_prefix(range_value)
            if 4 <= len(prefix) <= 18 and digits.startswith(prefix):
                candidates.append((len(prefix), live_provider, prefix))

    if candidates:
        _length, found_provider, query = max(candidates, key=lambda row: row[0])
        return {
            "range": query,
            "provider": found_provider if found_provider in valid_providers else requested_provider,
            "service": service_name,
        }

    # Keep a usable button on every forwarded OTP, including demo/test entries.
    # The provider will still enforce its own stock and range validation.
    query = digits[:min(7, len(digits))]
    return {
        "range": query,
        "provider": requested_provider,
        "service": service_name,
    }


def _same_number_callback_data(number, service, provider=None):
    context = _same_number_request_context(number, service, provider)
    if not context:
        return "same_num:auto:-:0000"
    provider_name = context.get("provider", "auto")
    if provider_name not in {"stex", "voltx", "zenex", "fastx"}:
        provider_name = "auto"
    service_name = context.get("service") or "-"
    query = _clean_range_prefix(context.get("range"))
    return f"same_num:{provider_name}:{service_name}:{query}"


def _usable_forward_button_url(value):
    url = str(value or "").strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    if (
        parsed.scheme.lower() not in ("http", "https")
        or not parsed.netloc
        or not parsed.hostname
        or "your_" in url.lower()
        or "example." in url.lower()
    ):
        return ""
    return url


def otp_forward_keyboard(otp, number, service, provider, custom_buttons=None,
                         include_code=True):
    """Build an OTP copy button when allowed, plus group-configured links."""
    keyboard = []
    if include_code:
        keyboard.append([{
            "text": str(otp),
            "copy_text": {"text": str(otp)},
            "style": "success",
        }])

    styles = ("danger", "success", "primary")
    custom_row = []
    for index, button in enumerate(custom_buttons or []):
        if not isinstance(button, dict) or not button.get("url"):
            continue
        icon_custom_emoji_id = button.get("icon_custom_emoji_id")
        if not icon_custom_emoji_id:
            normalized_label = re.sub(
                r"[^\w\s]",
                " ",
                str(button.get("text", "")).casefold(),
                flags=re.UNICODE,
            )
            normalized_label = " ".join(normalized_label.split())
            label_words = f" {normalized_label} "
            if " get number " in label_words or " নম্বর নিন " in label_words:
                icon_custom_emoji_id = GET_NUMBER_EMOJI_ID
            elif " channel " in label_words or " চ্যানেল " in label_words:
                icon_custom_emoji_id = OTP_GROUP_EMOJI_ID
            elif " support " in label_words or " সাপোর্ট " in label_words:
                icon_custom_emoji_id = MESSAGE_SMS_EMOJI_ID
        item = {
            "text": str(button.get("text", "Open")),
            "url": str(button["url"]),
            "style": styles[index % len(styles)],
        }
        if icon_custom_emoji_id:
            item["icon_custom_emoji_id"] = str(icon_custom_emoji_id)
        custom_row.append(item)
        if len(custom_row) == 2:
            # Keep configured labels unpadded: adding alignment spaces here
            # makes two-button rows wider than the OTP message on Telegram.
            keyboard.append(custom_row)
            custom_row = []
    if custom_row:
        keyboard.append(custom_row)
    return {"inline_keyboard": keyboard}


# Calibrated against the latest Telegram Android screenshot: 56 cells left a
# 34px gap to the full-width copy-button row, so use 60 for this layout.
OTP_FORWARD_BUBBLE_WIDTH_CELLS = 60


def _otp_forward_display_width(line):
    """Estimate Telegram-visible monospace cells, including emoji sequences."""
    width = 0
    regional_indicators = 0
    join_next_emoji = False
    for char in str(line or ""):
        codepoint = ord(char)
        category = unicodedata.category(char)
        if char == "\u200d":
            join_next_emoji = True
            continue
        if (
            category.startswith("M")
            or category == "Cf"
            or 0xFE00 <= codepoint <= 0xFE0F
            or 0x1F3FB <= codepoint <= 0x1F3FF
        ):
            continue
        if 0x1F1E6 <= codepoint <= 0x1F1FF:
            regional_indicators += 1
            if regional_indicators % 2 == 1:
                width += 2
            continue
        regional_indicators = 0
        if join_next_emoji and category == "So":
            join_next_emoji = False
            continue
        join_next_emoji = False
        width += 2 if (
            unicodedata.east_asian_width(char) in ("W", "F")
            or category in ("So", "Sk")
        ) else 1
    return width


def _otp_forward_keyboard_width(keyboard):
    """Estimate the widest inline-keyboard row in the same display cells."""
    widest_row = OTP_FORWARD_BUBBLE_WIDTH_CELLS
    rows = keyboard.get("inline_keyboard", []) if isinstance(keyboard, dict) else []
    for row in rows:
        if not isinstance(row, list) or not row:
            continue
        row_width = 0
        for button in row:
            if not isinstance(button, dict):
                continue
            label = html.unescape(
                re.sub(r"<[^>]+>", "", str(button.get("text", "")))
            )
            row_width += _otp_forward_display_width(label)
            # Account for the button's icon, link arrow, and client-side
            # horizontal padding so the caption reaches the full button row.
            if button.get("icon_custom_emoji_id") or button.get("copy_text"):
                row_width += 2
            if button.get("url"):
                row_width += 1
            row_width += 8
        row_width += max(0, len(row) - 1) * 2
        widest_row = max(widest_row, row_width)
    return widest_row


def _pad_otp_forward_bubble_width(text, target_width=OTP_FORWARD_BUBBLE_WIDTH_CELLS):
    """Pad an OTP caption to match the widest button row for that group."""
    source = str(text or "")
    if not source:
        return source
    visible_text = re.sub(
        r"<tg-emoji\b[^>]*>(.*?)</tg-emoji>",
        r"\1",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    visible_text = html.unescape(re.sub(r"<[^>]+>", "", visible_text))
    widest_line = max(
        (_otp_forward_display_width(line) for line in visible_text.splitlines()),
        default=0,
    )
    target_width = max(OTP_FORWARD_BUBBLE_WIDTH_CELLS, int(target_width or 0))
    padding = max(0, target_width - widest_line)
    full_width_padding = ("\u3164" * (padding // 2)) + ("\u2007" if padding % 2 else "")
    return source + full_width_padding


def _format_otp_forward_caption(text):
    """Limit OTP group language labels to French, English, or Arabic."""
    source = str(text or "").strip()
    language_marker = re.compile(
        r"(?P<marker><tg-emoji\b[^>]*>\s*💬\s*</tg-emoji>|💬)"
        r"(?P<spacing>\s*)(?P<language>[^\s<\n]+)",
        flags=re.IGNORECASE,
    )

    def allowed_language(match):
        detected = match.group("language").strip().casefold().lstrip("#")
        if detected in {"fr", "french", "français"}:
            label = "French"
        elif detected in {"ar", "arabic", "العربية"}:
            label = "Arabic"
        else:
            label = "English"
        return match.group("marker") + match.group("spacing") + label

    return language_marker.sub(allowed_language, source)


def send_otp_to_forward_groups(text, otp, number, service, provider="auto"):
    """Post the GX-masked number and requested public OTP copy button."""
    text = _format_otp_forward_caption(text)
    sent = 0
    for group in bot_settings.get("fw_groups", []):
        if not isinstance(group, dict) or not group.get("chat_id"):
            continue
        keyboard = otp_forward_keyboard(
            otp,
            number,
            service,
            provider,
            group.get("buttons", []),
            include_code=True,
        )
        group_text = _pad_otp_forward_bubble_width(
            text,
            target_width=_otp_forward_keyboard_width(keyboard),
        )
        result = send_message(
            group["chat_id"],
            group_text,
            reply_markup=keyboard if keyboard.get("inline_keyboard") else None,
        )
        if isinstance(result, dict) and result.get("ok"):
            sent += 1
        else:
            print("⚠️ OTP group notice was not delivered.")
    return sent


def _panel_otp_owner_ids(number):
    """Find exact owners across active sessions and every number provider."""
    canonical = _canonical_number(number)
    if not canonical:
        return []

    owners = {}
    for user_id, session_data in list(user_active_sessions.items()):
        if not isinstance(session_data, dict):
            continue
        session_numbers = session_data.get("nums", [])
        if isinstance(session_numbers, (list, tuple, set)) and any(
            _canonical_number(value) == canonical for value in session_numbers
        ):
            owners[str(user_id)] = user_id

    # The active session is the most current assignment; do not route an OTP
    # to a stale owner left in a provider map after the session changed.
    if owners:
        return list(owners.values())

    for assigned_numbers in (
        stex_assigned_numbers,
        voltx_assigned_numbers,
        zenex_assigned_numbers,
        fastx_assigned_numbers,
    ):
        for assigned_number, user_id in list(assigned_numbers.items()):
            if _canonical_number(assigned_number) == canonical:
                owners[str(user_id)] = user_id

    return list(owners.values())


def _assigned_provider_for_number(number):
    canonical = _canonical_number(number)
    if not canonical:
        return None
    for provider, assigned in (
        ("stex", stex_assigned_numbers),
        ("voltx", voltx_assigned_numbers),
        ("zenex", zenex_assigned_numbers),
        ("fastx", fastx_assigned_numbers),
    ):
        if any(_canonical_number(value) == canonical for value in assigned):
            return provider
    return None


def _handle_same_number_request(call):
    """Fetch the configured NUM/REQ quantity for the forwarded OTP's range."""
    callback_id = call.get("id")
    clicker = call.get("from", {}).get("id")
    if not clicker:
        answer_callback(callback_id, "❌ Could not identify the requesting user.", show_alert=True)
        return

    if is_user_banned(clicker):
        answer_callback(callback_id, "🚫 You are banned from using this bot.", show_alert=True)
        return

    parts = str(call.get("data", "")).split(":", 3)
    if len(parts) != 4:
        answer_callback(callback_id, "❌ This same-range button is invalid.", show_alert=True)
        return
    _prefix, provider, service_token, raw_query = parts
    provider = provider.lower()
    if provider not in {"stex", "voltx", "zenex", "fastx", "auto"}:
        answer_callback(callback_id, "❌ Invalid provider.", show_alert=True)
        return
    query = _clean_range_prefix(raw_query)
    if not (4 <= len(query) <= 18):
        answer_callback(callback_id, "❌ Invalid number range.", show_alert=True)
        return
    service = (
        _canonical_allowed_service(service_token)
        or _canonical_traffic_service(service_token)
        if service_token and service_token != "-"
        else None
    )

    cooldown = float(bot_settings.get("cooldown", 0) or 0)
    now = time.time()
    wait_left = cooldown - (now - user_cooldowns.get(clicker, 0))
    if wait_left > 0:
        answer_callback(
            callback_id,
            f"⌛ Please wait {max(1, int(wait_left + 0.99))}s.",
            show_alert=True,
        )
        return
    if not check_force_join(clicker):
        answer_callback(callback_id, "Join the required channel(s) first.", show_alert=True)
        try:
            send_force_join_msg(clicker)
        except Exception:
            pass
        return

    # Opening the bot once is required before Telegram permits a group-button
    # action to send the requested number privately.
    loading_result = send_message(
        clicker,
        render_body_text(
            f'<tg-emoji emoji-id="{COUNTRY_LOADING_EMOJI_ID}">⏳</tg-emoji> '
            "<b>Fetching same-range numbers…</b>"
        ),
    )
    if not isinstance(loading_result, dict) or not loading_result.get("ok"):
        answer_callback(
            callback_id,
            "Open the bot and press Start, then tap GET SAME NUMBER again.",
            show_alert=True,
        )
        return

    answer_callback(callback_id, "Fetching numbers from the same range…")
    user_cooldowns[clicker] = now
    register_user_local(clicker)
    loading_message_id = (
        loading_result.get("result", {}).get("message_id")
        if isinstance(loading_result.get("result"), dict) else None
    )
    if not loading_message_id:
        send_message(clicker, "❌ Could not start the number request. Please try again.")
        return

    count = requested_number_count()
    fetched, _source = fetch_numbers_fast(
        query,
        clicker,
        count,
        source_hint=provider if provider != "auto" else None,
        service=service,
        use_local=False,
        persist=False,
    )
    if not fetched:
        edit_message(
            clicker,
            loading_message_id,
            "❌ No numbers are available in this range right now. Please try again later.",
        )
        return

    expire_previous_number(
        clicker,
        background=True,
        skip_message_id=loading_message_id,
    )
    number_contexts = {}
    for number in fetched:
        canonical = _canonical_number(number)
        assigned_provider = _assigned_provider_for_number(number) or provider
        number_contexts[canonical] = {
            "range": query,
            "provider": assigned_provider,
            "service": service or "",
        }
    user_active_sessions[clicker] = {
        "msg_id": loading_message_id,
        "nums": fetched,
        "request_range": query,
        "provider": provider,
        "service": service or "",
        "number_contexts": number_contexts,
    }
    schedule_provider_state_save()

    keyboard = []
    for number in fetched:
        display_number = f"+{_canonical_number(number)}"
        _char, _iso, flag_emoji_id = get_flag_info_from_num(str(number))
        keyboard.append([{
            "text": display_number,
            "icon_custom_emoji_id": flag_emoji_id or "5780471598922337683",
            "copy_text": {"text": display_number},
            "style": "success",
        }])
    link_buttons = []
    if bot_settings.get("otp_forward_channel_button", True):
        channel_url = _usable_forward_button_url(bot_settings.get("otp_link"))
        if channel_url:
            link_buttons.append({
                "text": "CHANNEL",
                "icon_custom_emoji_id": OTP_GROUP_EMOJI_ID,
                "url": channel_url,
                "style": "primary",
            })
    if bot_settings.get("otp_forward_support_button", True):
        support_url = _usable_forward_button_url(bot_settings.get("support_link"))
        if support_url:
            link_buttons.append({
                "text": "SUPPORT",
                "icon_custom_emoji_id": MESSAGE_SMS_EMOJI_ID,
                "url": support_url,
                "style": "primary",
            })
    if link_buttons:
        keyboard.append(link_buttons)
    range_label = html.escape(query)
    result_text = render_body_text(
        f"{PEM['ok']} <b>{len(fetched)} number(s) fetched from the same range</b>\n"
        f"Range: <code>{range_label}</code>\n"
        "Wait for incoming OTPs in the bot."
    )
    edit_result = edit_message(
        clicker,
        loading_message_id,
        result_text,
        reply_markup={"inline_keyboard": keyboard},
    )
    if not isinstance(edit_result, dict) or not edit_result.get("ok"):
        fallback_result = send_message(
            clicker,
            result_text,
            reply_markup={"inline_keyboard": keyboard},
        )
        if isinstance(fallback_result, dict) and fallback_result.get("ok"):
            fallback_message = fallback_result.get("result", {})
            if isinstance(fallback_message, dict) and fallback_message.get("message_id"):
                user_active_sessions[clicker]["msg_id"] = fallback_message["message_id"]


LANG_MAP = {
    "#EN": "English", "#BN": "Bengali", "#AR": "Arabic", "#HI": "Hindi", 
    "#PA": "Punjabi", "#GU": "Gujarati", "#OR": "Odia", "#TA": "Tamil", 
    "#TE": "Telugu", "#KN": "Kannada", "#ML": "Malayalam", "#SI": "Sinhala", 
    "#TH": "Thai", "#LO": "Lao", "#BO": "Tibetan", "#MY": "Burmese", 
    "#AM": "Amharic", "#KM": "Khmer", "#KA": "Georgian", "#HY": "Armenian", 
    "#HE": "Hebrew", "#EL": "Greek", "#RU": "Russian", "#ZH": "Chinese", 
    "#JA": "Japanese", "#KO": "Korean", "#ID": "Indonesian", "#MS": "Malay", 
    "#VN": "Vietnamese", "#TL": "Filipino", "#ES": "Spanish", "#PT": "Portuguese", 
    "#FR": "French", "#DE": "German", "#IT": "Italian", "#PL": "Polish", 
    "#TR": "Turkish", "#NL": "Dutch", "#SV": "Swedish", "#DA": "Danish", 
    "#NO": "Norwegian", "#FI": "Finnish", "#CS": "Czech", "#SK": "Slovak", 
    "#HU": "Hungarian", "#RO": "Romanian", "#HR": "Croatian", "#BG": "Bulgarian", 
    "#UK": "Ukrainian", "#SW": "Swahili", "#AF": "Afrikaans"
}

# ==========================================
# ADVANCED SERVICE & LANGUAGE DETECTION
# ==========================================

SERVICE_SMS_KEYWORDS = {
    "whatsapp": ["whatsapp", "whatsa", "whatsap", "whats", "whatsapp business", "whatsapp me", "whatsapp code", "whatsap", "واتساب", "واتساپ", "واٹس ایپ", "व्हाट्सएप", "वाट्सएप", "वॉट्सऐप", "व्हाट्सप्प", "হোয়াটসঅ্যাপ", "হোটসঅ্যাপ", "ватсап", "уотсап", "вотсап", "ватс апп", "వాట్సాప్", "വാട്‌സ്ആപ്പ്", "வாட்ஸ்அப்", "ವಾಟ್ಸಾಪ್", "વોટ્સએપ", "ਵਟਸਐਪ", "ହ୍ଵାଟସ୍ ଆପ୍", "වට්ස්ඇප්", "วอตส์แอปป์", "วอทส์แอพ", "ဝက်စ်အက်ပ်", "វ៉តសាប់", "ວອດແອັບ", "ワッツアップ", "왓츠앱", "whatsapp的", "whatsapp验证码", "וואטסאפ", "γουάτσαπ", "ዋትስአፕ", "ვოთსაფი", "վոթսափ"],
    "facebook": ["facebook", "fb", "meta", "fbook", "fb code", "facebook code", "فيسبوك", "فيس بوك"],
    "instagram": ["instagram", "insta", "ig", "ig code", "instagram code", "انستغرام", "انستقرام"],
    "telegram": ["telegram", "tg", "tele", "telegram code", "tg code", "t.me", "تيليجرام", "تليجرام"],
    "tiktok": ["tiktok", "tik tok", "tikvideo", "tiktok code", "tik code", "تيك توك"],
    "snapchat": ["snapchat", "snap", "snap code", "سناب شات"],
    "twitter": ["twitter", "x.com", "x code", "twitter code", "تويتر"],
    "discord": ["discord", "discord code", "ديسكورد"],
    "viber": ["viber", "viber code", "فايبر"],
    "line": ["line", "line code", "line verification", "لاين"],
    "wechat": ["wechat", "we chat", "wechat code", "وي تشات"],
    "signal": ["signal", "signal code", "سيجنال"],
    "linkedin": ["linkedin", "linked in", "لينكد إن"],
    "imo": ["imo", "imo code", "imo verification", "ايمو"],
    "kakaotalk": ["kakao", "kakaotalk", "كاكاو"],
    "qq": ["qq", "tencent qq"],
    "vk": ["vk", "vkontakte"],
    "google": ["google", "gmail", "youtube", "g-", "google voice", "جوجل", "غوغل"],
    "microsoft": ["microsoft", "ms", "outlook", "live.com", "hotmail"],
    "apple": ["apple", "icloud", "itunes", "apple id"],
    "yahoo": ["yahoo", "yahoo code", "ymail"],
    "protonmail": ["proton", "protonmail"],
    "binance": ["binance", "bnb", "binances"],
    "coinbase": ["coinbase"],
    "okx": ["okx", "okex"],
    "kucoin": ["kucoin"],
    "bybit": ["bybit"],
    "huobi": ["huobi", "htx"],
    "mexc": ["mexc"],
    "trustwallet": ["trust wallet", "trustwallet"],
    "bkash": ["bkash", "b-kash", "bkash code"],
    "nagad": ["nagad", "nagad code"],
    "rocket": ["rocket", "dutch bangla"],
    "upay": ["upay", "upay code"],
    "paypal": ["paypal", "pay pal"],
    "paytm": ["paytm"],
    "cashapp": ["cash app", "cashapp"],
    "wise": ["wise", "transferwise"],
    "amazon": ["amazon", "amzn", "amazon code"],
    "ebay": ["ebay"],
    "aliexpress": ["aliexpress", "ali express"],
    "alibaba": ["alibaba"],
    "daraz": ["daraz", "daraz code"],
    "foodpanda": ["foodpanda", "food panda"],
    "uber": ["uber", "uber code", "uber verification", "uber eats"],
    "pathao": ["pathao", "pathao ride"],
    "netflix": ["netflix", "netflix code"],
    "spotify": ["spotify", "spotify code"],
    "steam": ["steam", "steam guard"],
    "epicgames": ["epic games", "epicgames"],
    "roblox": ["roblox", "roblox code"],
    "riotgames": ["riot", "riot games", "valorant", "league of legends"],
    "garena": ["garena", "free fire", "freefire"],
    "playstation": ["playstation", "psn"],
    "1xbet": ["1xbet", "1x bet"],
    "melbet": ["melbet", "melbet code"],
    "linebet": ["linebet"],
    "bet365": ["bet365"],
    "megapari": ["megapari"],
    "tinder": ["tinder", "tinder code"],
    "bumble": ["bumble"],
    "badoo": ["badoo"]
}

def detect_service(text):
    text_lower = str(text or "").casefold()
    matches = []
    for service_key, keywords in SERVICE_SMS_KEYWORDS.items():
        for keyword in keywords:
            keyword = str(keyword).strip().casefold()
            if not keyword:
                continue
            # Avoid matching short aliases such as "ms", "fb", or "ig" in
            # the middle of unrelated words. Prefer the most specific brand
            # mention when an SMS contains more than one service-like term.
            pattern = (
                r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
            )
            match = re.search(pattern, text_lower, flags=re.UNICODE)
            if match:
                matches.append((len(keyword), -match.start(), service_key.upper()))
    if matches:
        return max(matches)[2]
    return None


def _normalize_service_label(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _service_key_from_label(value):
    """Resolve a provider's service label without inspecting its SMS body."""
    normalized = _normalize_service_label(value)
    if not normalized:
        return None

    candidates = []
    for service_key, keywords in SERVICE_SMS_KEYWORDS.items():
        aliases = [service_key, *keywords]
        for alias in aliases:
            alias_normalized = _normalize_service_label(alias)
            if not alias_normalized:
                continue
            if normalized == alias_normalized or (
                len(alias_normalized) >= 3
                and normalized.startswith(alias_normalized)
            ):
                candidates.append((len(alias_normalized), service_key.upper()))
    return max(candidates)[1] if candidates else None


def _resolve_service_app(service_text, msg_text=""):
    raw_service = str(service_text or "").strip()
    raw_normalized = _normalize_service_label(raw_service)
    apps = bot_settings.get("premium_apps", {})

    # A provider's explicit service field is authoritative. Only inspect the
    # SMS body when the provider label is generic or otherwise unrecognized.
    service_key = _service_key_from_label(raw_service)
    if not service_key:
        service_key = detect_service(msg_text)

    # Prefer an exact premium-app entry (for example "Amazon Prime") before
    # falling back to a shorter canonical alias such as "Amazon".
    for app_name, data in apps.items():
        app_names = {
            _normalize_service_label(app_name),
            _normalize_service_label(data.get("name", "")),
        }
        if raw_normalized and raw_normalized in app_names:
            return data.get("name", app_name.title()), data

    canonical_name = _normalize_service_label(service_key)
    for app_name, data in apps.items():
        app_names = {
            _normalize_service_label(app_name),
            _normalize_service_label(data.get("name", "")),
        }
        if canonical_name and canonical_name in app_names:
            return data.get("name", app_name.title()), data

    if service_key:
        return service_key.title(), None
    return raw_service.title() if raw_service else "Unknown", None

def get_service_info_html(service_text, msg_text=""):
    full_name, data = _resolve_service_app(service_text, msg_text)
    if data:
        char = data.get("char", "📱")
        emoji_id = data.get("id")
        if emoji_id:
            return full_name, f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'
        return full_name, char
    return full_name, f'<tg-emoji emoji-id="{APP_PHONE_EMOJI_ID}">📱</tg-emoji>'

def get_service_icon_id(service_text, msg_text=""):
    """Return the premium icon ID belonging to a service button."""
    _app_full_name, app_data = _resolve_service_app(service_text, msg_text)
    if app_data:
        return app_data.get("id") or "5190645917711114179"
    return "5190645917711114179"

def detect_language(text):
    if not text: return "#EN"
    text_str = str(text)

    if any('\u0600' <= c <= '\u06ff' for c in text_str): return "#AR"
    if any('\u0980' <= c <= '\u09ff' for c in text_str): return "#BN"
    if any('\u0900' <= c <= '\u097f' for c in text_str): return "#HI"
    if any('\u0a00' <= c <= '\u0a7f' for c in text_str): return "#PA"
    if any('\u0a80' <= c <= '\u0aff' for c in text_str): return "#GU"
    if any('\u0b00' <= c <= '\u0b7f' for c in text_str): return "#OR"
    if any('\u0b80' <= c <= '\u0bff' for c in text_str): return "#TA"
    if any('\u0c00' <= c <= '\u0c7f' for c in text_str): return "#TE"
    if any('\u0c80' <= c <= '\u0cff' for c in text_str): return "#KN"
    if any('\u0d00' <= c <= '\u0d7f' for c in text_str): return "#ML"
    if any('\u0d80' <= c <= '\u0dff' for c in text_str): return "#SI"
    if any('\u0e00' <= c <= '\u0e7f' for c in text_str): return "#TH"
    if any('\u0e80' <= c <= '\u0eff' for c in text_str): return "#LO"
    if any('\u0f00' <= c <= '\u0fff' for c in text_str): return "#BO"
    if any('\u1000' <= c <= '\u109f' for c in text_str): return "#MY"
    if any('\u1200' <= c <= '\u137f' for c in text_str): return "#AM"
    if any('\u1780' <= c <= '\u17ff' for c in text_str): return "#KM"
    if any('\u10a0' <= c <= '\u10ff' for c in text_str): return "#KA"
    if any('\u0530' <= c <= '\u058f' for c in text_str): return "#HY"
    if any('\u0590' <= c <= '\u05ff' for c in text_str): return "#HE"
    if any('\u0370' <= c <= '\u03ff' for c in text_str): return "#EL"
    if any('\u0400' <= c <= '\u04ff' for c in text_str): return "#RU"
    if any('\u4e00' <= c <= '\u9fff' for c in text_str): return "#ZH"
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text_str): return "#JA"
    if any('\uac00' <= c <= '\ud7af' for c in text_str): return "#KO"

    text_lower = text_str.lower()
    
    if any(w in text_lower for w in ["kode verifikasi", "jangan bagikan", "rahasia"]): return "#ID"
    if any(w in text_lower for w in ["kod pengesahan", "jangan kongsi"]): return "#MS"
    if any(w in text_lower for w in ["mã của bạn", "không chia sẻ", "mã xác minh"]): return "#VN"
    if any(w in text_lower for w in ["ang iyong code", "huwag ibahagi"]): return "#TL"
    if any(w in text_lower for w in ["código", "tu código", "verificación", "no compartas"]): return "#ES"
    if any(w in text_lower for w in ["seu código", "código de verificação", "não compartilhe"]): return "#PT"
    if any(w in text_lower for w in ["code secret", "ne partagez pas", "votre code"]): return "#FR"
    if any(w in text_lower for w in ["dein code", "bestätigungscode", "nicht teilen"]): return "#DE"
    if any(w in text_lower for w in ["il tuo codice", "codice di verifica", "non condividere"]): return "#IT"
    if any(w in text_lower for w in ["twój kod", "nie udostępniaj", "kod weryfikacyjny"]): return "#PL"
    if any(w in text_lower for w in ["doğrulama kodu", "paylaşmayın", "onay kodu"]): return "#TR"
    if any(w in text_lower for w in ["jouw code", "verificatiecode", "niet delen"]): return "#NL"
    if any(w in text_lower for w in ["din kod", "verifieringskod", "dela inte"]): return "#SV"
    if any(w in text_lower for w in ["bekræftelseskode", "del ikke"]): return "#DA"
    if any(w in text_lower for w in ["bekreftelseskode", "ikke del"]): return "#NO"
    if any(w in text_lower for w in ["vahvistuskoodi", "älä jaa"]): return "#FI"
    if any(w in text_lower for w in ["váš kód", "ověřovací kód", "nesdílejte"]): return "#CS"
    if any(w in text_lower for w in ["overovací kód", "nezdieľajte"]): return "#SK"
    if any(w in text_lower for w in ["ellenőrző kód", "ne oszd meg"]): return "#HU"
    if any(w in text_lower for w in ["codul tău", "codul de verificare", "nu partaja"]): return "#RO"
    if any(w in text_lower for w in ["kontrolni kod", "kod za potvrdu", "ne delite"]): return "#HR"
    if any(w in text_lower for w in ["код за потвърждение", "не споделяйте"]): return "#BG"
    if any(w in text_lower for w in ["ваш код", "код підтвердження"]): return "#UK"
    if any(w in text_lower for w in ["msimbo wako", "usishiriki"]): return "#SW"
    if any(w in text_lower for w in ["verifikasiekode", "moenie deel nie"]): return "#AF"
    
    return "#EN"

def parse_chat_id(text):
    text = text.strip()
    if text.startswith("-100") or (text.startswith("-") and text[1:].isdigit()):
        return text
    if "t.me/" in text:
        parts = text.split("/")
        username = parts[-1]
        if username: return "@" + username if not username.startswith("@") else username
    if text.startswith("@"):
        return text
    return "@" + text

def is_admin(user_id):
    return user_id in get_configured_admin_ids()

def clear_force_join_membership_cache():
    with _force_join_membership_cache_lock:
        _force_join_membership_cache.clear()


def check_force_join(user_id, force_refresh=False):
    if not bot_settings["fj_on"] or not bot_settings["fj_channels"]:
        return True
    if is_admin(user_id):
        return True

    channels = tuple(str(channel) for channel in bot_settings["fj_channels"])
    cache_key = (str(user_id), channels)
    now = time.monotonic()
    if not force_refresh:
        with _force_join_membership_cache_lock:
            cached = _force_join_membership_cache.get(cache_key)
            if isinstance(cached, tuple):
                allowed, cached_until = cached
                if cached_until > now:
                    return allowed
            elif isinstance(cached, (int, float)) and cached > now:
                return True

    futures = [
        _force_join_check_executor.submit(
            api_call, "getChatMember", {"chat_id": channel, "user_id": user_id}
        )
        for channel in channels
    ]
    for channel, future in zip(channels, futures):
        try:
            result = future.result()
        except Exception:
            result = {}
        if not (
            result.get("ok")
            and result.get("result", {}).get("status") not in ("left", "kicked")
        ):
            with _force_join_membership_cache_lock:
                _force_join_membership_cache[cache_key] = (
                    False,
                    time.monotonic() + _FORCE_JOIN_NEGATIVE_CACHE_TTL,
                )
            return False

    with _force_join_membership_cache_lock:
        if len(_force_join_membership_cache) >= 5000:
            expired = [
                key
                for key, expiry in _force_join_membership_cache.items()
                if expiry <= now
            ]
            for key in expired:
                _force_join_membership_cache.pop(key, None)
            while len(_force_join_membership_cache) >= 5000:
                _force_join_membership_cache.pop(
                    next(iter(_force_join_membership_cache)), None
                )
        _force_join_membership_cache[cache_key] = (
            True,
            time.monotonic() + _FORCE_JOIN_MEMBERSHIP_CACHE_TTL,
        )
    return True

def send_force_join_msg(chat_id):
    kb = []
    for ch in bot_settings["fj_channels"]:
        url = f"https://t.me/{ch.replace('@', '')}" if ch.startswith("@") else ch
        kb.append([{"text": f"Join Channel", "icon_custom_emoji_id": FORCE_JOIN_BUTTON_EMOJI_ID, "url": url, "style": "primary"}])
    kb.append([{"text": "Check Joined", "icon_custom_emoji_id": FORCE_JOIN_BUTTON_EMOJI_ID, "callback_data": "check_fj", "style": "success"}])
    send_message(chat_id, render_body_text(f"{PEM['warn']} <b>Please join our channels to use the bot!</b>"), reply_markup={"inline_keyboard": kb})

def is_user_banned(user_id):
    if is_admin(user_id): return False
    if user_id in user_banned_cache and time.time() - user_banned_cache[user_id]['time'] < 60:
        return user_banned_cache[user_id]['banned']
    banned = False
    if db:
        try:
            doc = db.collection('users').document(str(user_id)).get()
            banned = doc.exists and doc.to_dict().get("banned", False)
        except: pass
    user_banned_cache[user_id] = {'banned': banned, 'time': time.time()}
    return banned

# ==========================================
# Captcha Auto Login & Parsing Core
# ==========================================
def extract_otp_code(text):
    clean_text = re.sub(r'[\u200B-\u200D\uFEFF]', '', str(text))

    multi_part = re.search(r'(\d{3}[-\s]+\d{3})|(\d{2}[-\s]+\d{2}[-\s]+\d{2})', clean_text)
    if multi_part:
        return multi_part.group(0).replace(" ", "")

    otp_keywords = ['code', 'is', 'otp', 'pin', 'verification', 'auth', 'কোড', 'رمز', 'your code']
    keywords_pattern = '|'.join(otp_keywords)
    keyword_match = re.search(rf'(?:{keywords_pattern})\s*(?:is|:|-|=)?\s*([a-z0-9]{{4,10}})', clean_text, re.I)
    if keyword_match and keyword_match.group(1).isdigit():
        return keyword_match.group(1)
        
    keyword_match_rev = re.search(rf'([a-z0-9]{{4,10}})\s*(?:is your|is the|কোড)', clean_text, re.I)
    if keyword_match_rev and keyword_match_rev.group(1).isdigit():
        return keyword_match_rev.group(1)

    g_match = re.search(r'G-(\d{6})', clean_text, re.IGNORECASE)
    if g_match: return g_match.group(1)

    digit_matches = re.findall(r'(?<!\d)\d{4,8}(?!\d)', clean_text)
    if digit_matches: return digit_matches[0]

    return None

def parse_panel_response(response_text, p_config=None):
    results = []
    p_type = p_config.get("type", "API Panel") if p_config else "API Panel"
    
    n_col_name = p_config.get("num_col_name", "number").lower() if p_config else "number"
    m_col_name = p_config.get("msg_col_name", "message").lower() if p_config else "message"
    n_idx = int(p_config.get("num_col_idx", 1)) - 1 if p_config and p_config.get("num_col_idx") else 1
    m_idx = int(p_config.get("msg_col_idx", 2)) - 1 if p_config and p_config.get("msg_col_idx") else 2

    if p_type == "Auto Captcha Panel":
        try:
            soup = BeautifulSoup(response_text, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if not rows: continue
                
                final_n_idx = n_idx
                final_m_idx = m_idx
                
                header_cells = rows[0].find_all(['th', 'td'])
                for i, cell in enumerate(header_cells):
                    c_text = cell.get_text(strip=True).lower()
                    if n_col_name in c_text: final_n_idx = i
                    if m_col_name in c_text: final_m_idx = i

                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    
                    if all(c.name == 'th' for c in cols): continue
                    
                    if len(cols) > max(final_n_idx, final_m_idx):
                        num_text = cols[final_n_idx].get_text(separator=" ", strip=True)
                        msg_text = cols[final_m_idx].get_text(separator=" ", strip=True)
                        
                        clean_num = re.sub(r'\D', '', num_text)
                        
                        if clean_num and 5 <= len(clean_num) <= 18:
                            otp = extract_otp_code(msg_text)
                            if otp and len(msg_text) > 4:
                                results.append({"number": clean_num, "message": msg_text, "otp": otp})
        except Exception as e:
            pass
    else:
        try:
            data = json.loads(response_text)
            temp_results = []
            
            def process_item(item):
                pot_nums_list = []
                pot_msg = None
                values = []
                
                if isinstance(item, dict):
                    lower_keys = {str(k).lower(): v for k, v in item.items()}
                    for k in [
                        "number", "num", "phone", "phone_number", "msisdn",
                        "mobile", "mobile_number", "telephone", "tel",
                        "full_number", "national_number", "no_plus_number",
                        "receiver", "recipient", "to_number",
                    ]:
                        if k in lower_keys:
                            clean_val = re.sub(r'\D', '', str(lower_keys[k]))
                            if 5 <= len(clean_val) <= 18:
                                if clean_val not in pot_nums_list: pot_nums_list.append(clean_val)
                    for k in [
                        "message", "msg", "sms", "sms_text", "content",
                        "text", "body", "otp_message",
                    ]:
                        if k in lower_keys:
                            val = str(lower_keys[k])
                            if len(val) > 4:
                                pot_msg = val
                                break
                    values = list(item.values())
                elif isinstance(item, list):
                    values = item

                for v in values:
                    if isinstance(v, (dict, list)) or v is None: continue
                    v_str = str(v).strip()
                    
                    clean_v = re.sub(r'\D', '', v_str)
                    if 7 <= len(clean_v) <= 18 and not re.search(r'[a-zA-Z]', v_str):
                        if not re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', v_str) and not re.search(r'\d{2}:\d{2}:\d{2}', v_str) and "." not in v_str:
                            if clean_v not in pot_nums_list:
                                pot_nums_list.append(clean_v)
                    
                    if len(v_str) > 4 and not v_str.isdigit():
                        if extract_otp_code(v_str):
                            if pot_msg is None or len(v_str) > len(pot_msg):
                                pot_msg = v_str
                                
                pot_num = None
                if pot_nums_list:
                    matched_user_num = None
                    for n in pot_nums_list:
                        if n in stex_assigned_numbers or any(n in str(key) for key in stex_assigned_numbers.keys()):
                            matched_user_num = n
                            break
                    
                    if matched_user_num:
                        pot_num = matched_user_num
                    elif len(pot_nums_list) >= 2:
                        pot_num = pot_nums_list[1]
                    else:
                        pot_num = pot_nums_list[0]
                            
                if pot_num and pot_msg:
                    otp = extract_otp_code(pot_msg)
                    if otp:
                        temp_results.append({"number": pot_num, "message": pot_msg, "otp": otp})
                        
            def traverse_json(node):
                if isinstance(node, list):
                    if len(node) > 0 and not isinstance(node[0], (dict, list)):
                        process_item(node)
                    for child in node:
                        if isinstance(child, (dict, list)):
                            traverse_json(child)
                elif isinstance(node, dict):
                    process_item(node)
                    for val in node.values():
                        if isinstance(val, (dict, list)):
                            traverse_json(val)

            traverse_json(data)
            
            seen = set()
            for r in temp_results:
                uid = f"{r['number']}_{r['otp']}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(r)
        except: pass
        
    # Some providers use a different key spelling (for example
    # phone_number/sms_text). Re-run through the strict explicit-field parser
    # as a fallback, but only keep rows that contain a real OTP.
    if not results:
        for item in parse_panel_number_response(response_text, p_config):
            if item.get("otp"):
                results.append({
                    "number": item["number"],
                    "message": item.get("message", ""),
                    "otp": item["otp"],
                })
    return results

def attempt_auto_login(p, idx):
    login_url = p.get("login_url", "").strip()
    if not login_url.startswith("http"):
        login_url = "http://" + login_url
        
    if not login_url.lower().endswith('/login') and not login_url.lower().endswith('.php'):
        login_url = f"{login_url.rstrip('/')}/login"
        
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    
    try:
        res = session.get(login_url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        all_text = res.text
        
        captcha_match = re.search(r'(\d+\s*[\+\-\*]\s*\d+)\s*[=\?:]', all_text)
        if not captcha_match:
            captcha_match = re.search(r'what is\s*(\d+\s*[\+\-\*]\s*\d+)', all_text, re.I)
        if not captcha_match:
            elements = soup.find_all(["label", "div", "span", "p", "strong"])
            for el in elements:
                txt = el.get_text(separator=" ", strip=True)
                if any(op in txt for op in ["+", "-", "*"]):
                    m = re.search(r'(\d+\s*[\+\-\*]\s*\d+)', txt)
                    if m:
                        captcha_match = m
                        break
                        
        captcha_text = captcha_match.group(1) if captcha_match else "0 + 0"
        answer = "0"
        m2 = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', captcha_text)
        if m2:
            a, op, b = int(m2.group(1)), m2.group(2), int(m2.group(3))
            if op == '+': answer = str(a + b)
            elif op == '-': answer = str(a - b)
            elif op == '*': answer = str(a * b)

        form = soup.find("form")
        if not form:
            p["login_status"] = "❌ No login form found"
            return False
            
        action = form.get("action")
        from urllib.parse import urljoin
        post_url = urljoin(login_url, action) if action else login_url

        form_data = {}
        for hidden in form.find_all("input", type="hidden"):
            name = hidden.get("name")
            if name: form_data[name] = hidden.get("value") or ""
        
        user_input = form.find("input", {"name": re.compile(r"user|email|id", re.I)}) or \
                     form.find("input", {"type": "text", "placeholder": re.compile(r"user|email", re.I)}) or \
                     form.find("input", {"type": "text"})
                     
        pass_input = form.find("input", {"name": re.compile(r"pass", re.I)}) or \
                     form.find("input", {"type": "password"})
                     
        captcha_input = form.find("input", {"placeholder": re.compile(r"answer|ans|code|verification|value|captcha", re.I)}) or \
                        form.find("input", {"name": re.compile(r"ans|captcha|ver|code", re.I)})
        
        user_field = user_input.get("name") if user_input else "username"
        pass_field = pass_input.get("name") if pass_input else "password"
        captcha_field = captcha_input.get("name") if captcha_input else "answer"

        form_data[user_field] = p.get("username", "")
        form_data[pass_field] = p.get("password", "")
        if captcha_field:
            form_data[captcha_field] = answer

        login_req = session.post(post_url, data=form_data, allow_redirects=True, timeout=15)
        
        msg_link = p.get("msg_link", "").strip()
        if not msg_link.startswith("http") and msg_link != "":
            msg_link = "http://" + msg_link
            
        check_url = msg_link if msg_link else f"{login_url.split('/login')[0]}/client/SMSCDRStats"
        
        check_res = session.get(check_url, timeout=10)
        
        if 'logout' in login_req.text.lower() or 'logout' in check_res.text.lower() or 'sms reports' in check_res.text.lower() or 'dashboard' in check_res.text.lower() or 'cdrs' in check_res.text.lower():
            panel_sessions[idx] = session
            p["login_status"] = "✅ Active & Fetching"
            return True
        else:
            p["login_status"] = f"❌ Login Failed (Math: {captcha_text} = {answer})"
            return False
            
    except Exception as e:
        p["login_status"] = f"❌ Error: {str(e)[:20]}"
        
    return False

def panel_monitor_thread():
    global processed_otps, recent_traffic, panel_sessions
    while True:
        try:
            for idx, p in enumerate(bot_settings.get("panels", [])):
                if p.get("status") == "ON":
                    panel_number_rows = []
                    panel_rate_changed = False

                    if p.get("type") == "Auto Captcha Panel":
                        sess = panel_sessions.get(idx)
                        
                        if not sess:
                            now = time.time()
                            if now - p.get("last_login_attempt", 0) < 30: 
                                continue 
                            p["last_login_attempt"] = now
                            
                            success = attempt_auto_login(p, idx)
                            save_db()
                            if not success:
                                continue 
                            sess = panel_sessions.get(idx)
                            
                        try:
                            msg_link = p.get("msg_link", "").strip()
                            if not msg_link:
                                login_url = p.get("login_url", "").strip()
                                if not login_url.startswith("http"):
                                    login_url = "http://" + login_url
                                msg_link = f"{login_url.split('/login')[0]}/client/SMSCDRStats"
                            parsed_data, res_text = fetch_cpt_panel_cdrs(p, sess, msg_link)
                            panel_number_rows = [
                                {
                                    "number": item.get("number", ""),
                                    "message": item.get("message", ""),
                                    "service": item.get("service", ""),
                                }
                                for item in parsed_data
                                if isinstance(item, dict)
                            ]
                            p["login_status"] = "✅ Active & Fetching"
                        except Exception as e:
                            p["login_status"] = (
                                f"❌ Panel fetch failed ({type(e).__name__}); retrying"
                            )
                            panel_sessions.pop(idx, None)
                            save_db()
                            continue

                    elif p.get("api_url") or p.get("full_api_url"): 
                        full_url = p.get("full_api_url", "").strip()
                        url = p.get("api_url", "").strip()
                        token = p.get("token", "").strip()
                        if not full_url and not url: continue
                        
                        urls_to_try = panel_api_request_urls(p)
                        if not urls_to_try:
                            continue

                        parsed_data = []
                        panel_number_rows = []
                        successful_response = False
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                        for try_url in urls_to_try:
                            try:
                                res = requests.get(try_url, headers=headers, timeout=10)
                                if not res.ok:
                                    p["login_status"] = f"❌ API HTTP {res.status_code}"
                                    continue
                                successful_response = True
                                parsed_data = parse_panel_response(res.text, p)
                                panel_number_rows = parse_panel_number_response(res.text, p)
                                if parsed_data or panel_number_rows:
                                    if not full_url and try_url != url and token:
                                        p["api_url"] = try_url.replace(token, "{token}")
                                        save_db()
                                    break
                            except Exception as e:
                                p["login_status"] = (
                                    f"❌ API request failed ({type(e).__name__})"
                                )
                                continue
                        if successful_response and not parsed_data:
                            p["login_status"] = (
                                "⚠️ Connected; no OTP rows were recognized"
                            )
                    else:
                        continue
                    
                    if p.get("type") != "Auto Captcha Panel":
                        limit = p.get("records", 0)
                        if limit > 0:
                            parsed_data = parsed_data[:limit]
                            panel_number_rows = panel_number_rows[:limit]

                    service_hints_by_number = {}
                    for row in panel_number_rows:
                        if not isinstance(row, dict):
                            continue
                        number = re.sub(r"\D", "", str(row.get("number", "")))
                        if number:
                            service_hints_by_number[number] = row.get("service", "")
                        if record_panel_rate_catalog(
                            p,
                            row.get("number", ""),
                            row.get("message", ""),
                            row.get("service", ""),
                        ):
                            panel_rate_changed = True

                    if not parsed_data:
                        if str(p.get("login_status", "")).startswith("✅"):
                            p["login_status"] = (
                                "⚠️ Connected; no OTP rows were recognized"
                            )
                        if panel_rate_changed:
                            save_db()
                        continue
                        
                    for item in parsed_data:
                        num = item["number"]
                        otp = item["otp"]
                        msg_text = item["message"]
                        number_key = re.sub(r"\D", "", str(num))
                        service_hint = service_hints_by_number.get(number_key, "")
                        if record_panel_rate_catalog(
                            p, num, msg_text, service_hint
                        ):
                            panel_rate_changed = True
                        panel_identity = str(
                            p.get("id") or p.get("name") or f"panel-{idx}"
                        ).strip().casefold()
                        canonical_num = _canonical_number(num)
                        unique_id = f"PANEL:{panel_identity}:{canonical_num}:{otp}"
                        if _has_processed_otp(unique_id):
                            continue

                        owners = _panel_otp_owner_ids(num)
                        if not owners:
                            p["login_status"] = (
                                "⚠️ OTP parsed; no assigned-number owner found"
                            )
                            if unique_id not in _panel_unmatched_otp_keys:
                                print(
                                    f"⚠️ Panel {idx + 1}: OTP parsed, but no exact assigned-number owner was found."
                                )
                                _panel_unmatched_otp_keys.add(unique_id)
                            continue
                        _panel_unmatched_otp_keys.discard(unique_id)

                        char, iso = get_flag_and_code(num)
                        panel_service = _panel_rate_service_key(
                            p, msg_text, service_hint
                        )
                        app_full_name, prem_app_html = get_service_info_html(
                            panel_service
                        )
                        display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                        masked = mask_number(display_num)
                        lang = detect_language(msg_text)
                        lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")

                        inbox_msg = render_body_text(
                            f"{get_flag_info_html(display_num)} {iso} | "
                            f"{prem_app_html} {display_num} | 💬 {lang_name}\n\n"
                            f"🔐 OTP: <code>{html.escape(str(otp))}</code>"
                        )
                        inbox_kb = [[{
                            "text": str(otp),
                            "icon_custom_emoji_id": "5353022963132174959",
                            "copy_text": {"text": str(otp)},
                            "style": "success",
                        }]]
                        reward = panel_otp_reward(
                            p, num, msg_text, service_hint
                        )
                        if reward > 0:
                            inbox_kb.append([{
                                "text": f"Added {reward} tk",
                                "icon_custom_emoji_id": GIFT_BOX_EMOJI_ID,
                                "callback_data": "ignore",
                                "style": "primary",
                            }])

                        delivered = False
                        for owner_id in owners:
                            result = send_message(
                                owner_id,
                                inbox_msg,
                                reply_markup={"inline_keyboard": inbox_kb},
                            )
                            if isinstance(result, dict) and result.get("ok"):
                                delivered = True
                                record_user_otp(owner_id, otp)
                                if reward > 0:
                                    update_balance(owner_id, reward)
                            else:
                                error = (
                                    result.get("description", "Telegram send failed")
                                    if isinstance(result, dict) else "Telegram send failed"
                                )
                                print(
                                    f"⚠️ Panel {idx + 1}: private OTP delivery failed "
                                    f"for assigned user {owner_id}: {str(error)[:120]}"
                                )

                        if not delivered:
                            p["login_status"] = (
                                "❌ OTP parsed; private Telegram delivery failed"
                            )
                            continue

                        _remember_processed_otp(unique_id)
                        p["login_status"] = "✅ OTP delivered to assigned user"
                        current_time = time.time()
                        recent_traffic = [
                            t for t in recent_traffic
                            if current_time - t.get("time", 0) <= 3600
                        ]
                        recent_traffic.append({
                            "service": app_full_name,
                            "iso": iso,
                            "flag": char,
                            "number": num,
                            "time": current_time,
                        })
                        save_local_db()

                        display_msg = render_body_text(
                            f"{get_flag_info_html(display_num)} {iso} | "
                            f"{prem_app_html} {masked} | 💬 {lang_name}"
                        )
                        send_otp_to_forward_groups(
                            display_msg, otp, num, panel_service, "auto"
                        )
                    if panel_rate_changed:
                        save_db()
        except Exception as e:
            print(
                f"⚠️ Panel monitor error ({type(e).__name__}); "
                "check the panel response and credentials."
            )
        time.sleep(5) 

# ==========================================
# PostgreSQL User Management
# ==========================================
user_cache = {}
user_data_lock = threading.RLock()
_USER_OPERATION_LOCKS = tuple(threading.RLock() for _ in range(64))
referral_lock = threading.Lock()


def _user_operation_lock(user_id):
    user_key = str(user_id).strip()
    return _USER_OPERATION_LOCKS[hash(user_key) % len(_USER_OPERATION_LOCKS)]


def _cache_user_record(user_id, user_key, data):
    with user_data_lock:
        user_cache[user_key] = data
    ban_cache_key = (
        int(user_key) if re.fullmatch(r"-?\d+", user_key) else user_key
    )
    user_banned_cache[ban_cache_key] = {
        "banned": bool(data.get("banned", False)),
        "time": time.time(),
    }


def get_user(user_id):
    with user_data_lock:
        cached = user_cache.get(str(user_id).strip())
    if cached is not None:
        return cached
    with _user_operation_lock(user_id):
        with user_data_lock:
            cached = user_cache.get(str(user_id).strip())
        if cached is not None:
            return cached
        return _get_user_unlocked(user_id)


def _get_user_unlocked(user_id):
    user_key = str(user_id).strip()
    with user_data_lock:
        cached = user_cache.get(user_key)
    if cached is not None:
        return cached
    if not db:
        with user_data_lock:
            data = local_users.get(user_key)
        if not data:
            data = {
                "user_id": user_id,
                "user_name": "",
                "username": "",
                "balance": 0.0,
                "otp": "",
                "total_refers": 0,
                "total_otps": 0,
                "banned": False,
                "verified": False,
                "language": None,
                "otp_bonus_notifications": True,
                "created_at": iso_now()
            }
            with user_data_lock:
                local_users[user_key] = data
            save_user_store()
        _cache_user_record(user_id, user_key, data)
        return data
    
    doc_ref = db.collection('users').document(str(user_id))
    doc = doc_ref.get()
    if doc.exists: 
        data = doc.to_dict()
        if "total_otps" not in data: data["total_otps"] = 0
        if "total_refers" not in data: data["total_refers"] = 0
        if "balance" not in data: data["balance"] = 0.0
        if "user_name" not in data: data["user_name"] = ""
        if "username" not in data: data["username"] = ""
        if "otp" not in data: data["otp"] = ""
        if "banned" not in data: data["banned"] = False
        if "verified" not in data: data["verified"] = False
        if "language" not in data: data["language"] = None
        _cache_user_record(user_id, user_key, data)
        return data
    else:
        new_user = {
            "user_id": user_id,
            "user_name": "",
            "username": "",
            "balance": 0.0,
            "otp": "",
            "total_refers": 0,
            "total_otps": 0,
            "banned": False,
            "verified": False,
            "language": None,
            "otp_bonus_notifications": True,
            "created_at": iso_now()
        }
        doc_ref.set(new_user)
        _cache_user_record(user_id, user_key, new_user)
        return new_user


def update_user_profile(user_id, user_name, username=None):
    """Save the user's display name and Telegram @username."""
    user_name = str(user_name or "").strip()[:120]
    normalized_username = (
        _normalize_username(username)[:120] if username is not None else None
    )
    if not user_name and normalized_username is None:
        return
    user = get_user(user_id)
    changed_fields = {}
    if user_name and user.get("user_name") != user_name:
        changed_fields["user_name"] = user_name
        user["user_name"] = user_name
    if normalized_username is not None and user.get("username", "") != normalized_username:
        changed_fields["username"] = normalized_username
        user["username"] = normalized_username
    if not changed_fields:
        return
    user["updated_at"] = iso_now()
    changed_fields["updated_at"] = user["updated_at"]
    try:
        if db:
            db.collection("users").document(str(user_id)).set(
                changed_fields,
                merge=True,
            )
        else:
            local_users[str(user_id)] = user
            save_user_store()
    except Exception:
        pass


def _parse_otp_timestamp(value):
    """Parse a stored OTP event time and normalize it to the bot's local zone."""
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
            str(value).strip().replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=DATA_TZ)
        return parsed.astimezone(DATA_TZ)
    except (TypeError, ValueError, OverflowError):
        return None


def _retained_otp_timestamps(values, now):
    """Keep only valid event timestamps from the rolling 30-day window."""
    if not isinstance(values, list):
        return []
    cutoff = now - timedelta(days=30)
    retained = []
    for value in values:
        parsed = _parse_otp_timestamp(value)
        if parsed is not None and parsed >= cutoff:
            retained.append(parsed.isoformat(timespec="seconds"))
    return retained


def get_otp_period_counts(now=None):
    """Count OTP deliveries for Dhaka today and the last rolling 7/30 days."""
    current = _parse_otp_timestamp(now if now is not None else data_now())
    if current is None:
        current = data_now()
    today_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_day_start = current - timedelta(days=7)
    thirty_day_start = current - timedelta(days=30)
    counts = {"today": 0, "7_days": 0, "30_days": 0}

    for snapshot in db.collection("users").stream():
        user = snapshot.to_dict()
        timestamps = user.get("otp_timestamps", []) if isinstance(user, dict) else []
        if not isinstance(timestamps, list):
            continue
        for value in timestamps:
            event_time = _parse_otp_timestamp(value)
            if event_time is None or event_time > current:
                continue
            if event_time >= today_start:
                counts["today"] += 1
            if event_time >= seven_day_start:
                counts["7_days"] += 1
            if event_time >= thirty_day_start:
                counts["30_days"] += 1
    return counts


def record_user_otp(user_id, otp):
    """Save the latest OTP for the user and keep the existing OTP counter."""
    with _user_operation_lock(user_id):
        otp = str(otp or "").strip()[:32]
        if not otp:
            return False
        user = get_user(user_id)
        now = data_now()
        updated_at = now.isoformat(timespec="seconds")
        otp_timestamps = _retained_otp_timestamps(
            user.get("otp_timestamps", []), now
        )
        otp_timestamps.append(updated_at)
        old_otp = user.get("otp", "")
        old_total_raw = user.get("total_otps", 0)
        old_total = max(0, int(_as_number(old_total_raw, 0)))
        old_updated_at = user.get("updated_at")
        had_otp_timestamps = "otp_timestamps" in user
        old_otp_timestamps = copy.deepcopy(user.get("otp_timestamps", []))
        try:
            if db:
                db.collection("users").document(str(user_id)).set(
                    {
                        "otp": otp,
                        "total_otps": postgres.Increment(1),
                        "otp_timestamps": otp_timestamps,
                        "updated_at": updated_at,
                    },
                    merge=True,
                )
            else:
                user["otp"] = otp
                user["total_otps"] = int(old_total or 0) + 1
                user["otp_timestamps"] = otp_timestamps
                user["updated_at"] = updated_at
                local_users[str(user_id)] = user
                save_user_store()
        except Exception as exc:
            user["otp"] = old_otp
            user["total_otps"] = old_total_raw
            if had_otp_timestamps:
                user["otp_timestamps"] = old_otp_timestamps
            else:
                user.pop("otp_timestamps", None)
            if old_updated_at is None:
                user.pop("updated_at", None)
            else:
                user["updated_at"] = old_updated_at
            print(f"⚠️ OTP counter save failed for {user_id}: {exc}")
            return False

        user["otp"] = otp
        user["total_otps"] = int(old_total or 0) + 1
        user["otp_timestamps"] = otp_timestamps
        user["updated_at"] = updated_at
        updated_total = user["total_otps"]

    # Referral bonuses are triggered only after this OTP record is saved.
    try:
        process_referral_otp_bonus(
            user_id,
            otp_count=updated_total,
            new_otp_event=True,
        )
    except Exception as exc:
        print(f"⚠️ Referral OTP bonus processing failed for {user_id}: {exc}")
    return True


def set_user_language(user_id, language):
    language = "BN" if str(language).upper() == "BN" else "EN"
    user = get_user(user_id)
    user["language"] = language
    if db:
        try:
            db.collection("users").document(str(user_id)).update({"language": language})
        except Exception:
            pass
    else:
        local_users[str(user_id)] = user
        save_user_store()
    return language

COMMAND_ALIASES = {
    "নম্বর নিন": "GET NUMBER",
    "ট্রাফিক": "TRAFFIC",
    "২এফএ অনলাইন": "2FA ONLINE",
    "রেফার": "REFER",
    "উত্তোলন": "WITHDRAWAL",
    "সাপোর্ট": "SUPPORT",
    "ভাষা পরিবর্তন করুন": "CHANGE LANGUAGE",
    "বট রিস্টার্ট করুন": "RESTART BOT",
    "ভাষা": "CHANGE LANGUAGE",
    "অ্যাডমিন প্যানেল": "ADMIN PANEL",
    "নম্বর ম্যানেজমেন্ট": "NUMBER MANAGEMENT",
    "ডিলিট ম্যানেজমেন্ট": "DELETE MANAGEMENT",
    "ব্যবহৃত নম্বর": "USED NUMBER",
    "অব্যবহৃত নম্বর": "UNUSED NUMBER",
    "ফাইল ডিলিট": "DELETE FILE",
    "ডেটা ডিলিট": "DELETE DATA",
    "অ্যাডমিন প্যানেলে ফিরুন": "BACK TO ADMIN PANEL",
    "মাস্টার প্যানেল": "MASTER PANEL",
    "জিএক্স কন্ট্রোল": "GX CONTROL",
}

def canonical_command(text):
    normalized = str(text or "").strip()
    return COMMAND_ALIASES.get(normalized, normalized.upper())


def _parse_admin_slash_command(text):
    """Return a lowercase Telegram slash command and its optional argument."""
    parts = str(text or "").strip().split(maxsplit=1)
    if not parts or not parts[0].startswith("/"):
        return "", ""
    command = parts[0].split("@", 1)[0].casefold()
    argument = parts[1].strip() if len(parts) > 1 else ""
    return command, argument


def update_balance(user_id, amount, reason="balance_adjustment"):
    with _user_operation_lock(user_id):
        return _update_balance_unlocked(user_id, amount, reason)


def format_balance(value):
    """Display taka amounts to two decimals instead of exposing float noise."""
    try:
        amount = float(value)
        if not math.isfinite(amount):
            return "0.00"
        return f"{amount:.2f}"
    except (TypeError, ValueError, OverflowError):
        return "0.00"


def withdrawal_method_emoji_id(method):
    method_key = re.sub(r"[^a-z]", "", str(method or "").casefold())
    return WITHDRAWAL_METHOD_EMOJI_IDS.get(method_key, WITHDRAWAL_EMOJI_ID)


def _premium_digit_text(value):
    """Render digits with the supplied premium emoji IDs and keycap fallbacks."""
    fallbacks = {
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣",
        "8": "8️⃣",
        "9": "9️⃣",
        "0": "0️⃣",
    }
    rendered = []
    for character in str(value):
        emoji_id = PREMIUM_DIGIT_EMOJI_IDS.get(character)
        if emoji_id:
            rendered.append(
                f'<tg-emoji emoji-id="{emoji_id}">{fallbacks[character]}</tg-emoji>'
            )
        else:
            rendered.append(html.escape(character))
    return "".join(rendered)


def withdrawal_method_emoji_html(method):
    emoji_id = withdrawal_method_emoji_id(method)
    return f'<tg-emoji emoji-id="{emoji_id}">💳</tg-emoji>' if emoji_id else ""


def _pending_withdrawal_serials():
    """Return transient #1, #2… labels for currently pending requests."""
    with withdrawal_processing_lock:
        return {
            request_id: index
            for index, request_id in enumerate(pending_withdrawals, start=1)
        }


def _withdrawal_admin_request_text(req_id, req_data, serial):
    user_id = req_data.get("user_id", "User")
    full_name = html.escape(str(req_data.get("full_name", user_id)))
    amount = html.escape(str(req_data.get("amount", 0)))
    number = str(req_data.get("number", "Unknown"))
    safe_number = html.escape(number)
    method = str(req_data.get("method", "Unknown"))
    safe_method = html.escape(method)
    method_icon = withdrawal_method_emoji_html(method)
    method_prefix = f"{method_icon} " if method_icon else ""
    display_id = f"#{_premium_digit_text(serial)}"
    return (
        f"🎙 <b>NEW WITHDRAWAL REQUEST {display_id}</b>\n\n"
        f"👤 <b>USER:</b> <a href='tg://user?id={html.escape(str(user_id))}'>{full_name}</a>\n"
        f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
        f"<b>WITHDRAWAL:</b> {amount} TK\n"
        f'<tg-emoji emoji-id="6224284210434154938">📱</tg-emoji> '
        f"<b>NUMBER:</b> <code>{safe_number}</code>\n"
        f"{method_prefix}<b>METHOD:</b> {safe_method}\n\n"
        f'<tg-emoji emoji-id="6222105571093389816">🧾</tg-emoji> '
        f"<b>REQ ID:</b> <code>{display_id}</code>\n"
        "👨‍⚖️ <b>PROCESSED BY ADMIN</b>"
    )


def _withdrawal_admin_request_keyboard(req_id, serial):
    display_id = f"#{serial}"
    return {
        "inline_keyboard": [[
            {
                "text": f"✅ APPROVE {display_id}",
                "icon_custom_emoji_id": "6224188445548356446",
                "callback_data": f"wapp_{req_id}",
                "style": "success",
            },
            {
                "text": f"❌ REJECT {display_id}",
                "icon_custom_emoji_id": "6224003980997962148",
                "callback_data": f"wrej_{req_id}",
                "style": "danger",
            },
        ]]
    }


def _renumber_pending_withdrawal_messages():
    """Refresh group cards after add/resolve so active labels always start at #1."""
    with withdrawal_processing_lock:
        snapshot = [
            (request_id, copy.deepcopy(data), index)
            for index, (request_id, data) in enumerate(
                pending_withdrawals.items(), start=1
            )
        ]
        for request_id, _, serial in snapshot:
            current = pending_withdrawals.get(request_id)
            if isinstance(current, dict):
                current["display_serial"] = serial

    for request_id, req_data, serial in snapshot:
        admin_chat_id = req_data.get("admin_chat_id")
        admin_message_id = req_data.get("admin_message_id")
        if not admin_chat_id or not admin_message_id:
            continue
        try:
            result = edit_message(
                admin_chat_id,
                admin_message_id,
                render_body_text(
                    _withdrawal_admin_request_text(request_id, req_data, serial)
                ),
                reply_markup=_withdrawal_admin_request_keyboard(
                    request_id, serial
                ),
            )
            if not isinstance(result, dict) or not result.get("ok"):
                description = (
                    result.get("description", "unknown error")
                    if isinstance(result, dict)
                    else "no Telegram API response"
                )
                print(
                    f"⚠️ Could not renumber withdrawal {request_id}: "
                    f"{description}"
                )
        except Exception as exc:
            print(f"⚠️ Could not renumber withdrawal {request_id}: {exc}")


def _update_balance_unlocked(user_id, amount, reason="balance_adjustment"):
    user = get_user(user_id)
    if db:
        try:
            latest = db.collection("users").document(str(user_id)).get()
            if latest.exists:
                latest_user = latest.to_dict()
                if isinstance(latest_user, dict):
                    user = latest_user
                    user_cache[str(user_id).strip()] = user
        except Exception as exc:
            print(f"⚠️ Could not read current balance for {user_id}: {exc}")
            return False
    try:
        amount = round(float(amount), 2)
        old_balance = round(float(user.get("balance", 0.0) or 0.0), 2)
    except (TypeError, ValueError, OverflowError) as exc:
        print(f"⚠️ Rejected invalid balance update for {user_id}: {exc}")
        return False
    new_balance = round(old_balance + amount, 2)
    if not math.isfinite(amount) or not math.isfinite(new_balance):
        print(f"⚠️ Rejected non-finite balance update for {user_id}: {amount}")
        return False
    updated_at = iso_now()
    try:
        if db:
            doc_ref = db.collection('users').document(str(user_id))
            doc_ref.set({
                "user_id": user_id,
                "balance": new_balance,
                "updated_at": updated_at
            }, merge=True)
        else:
            user["balance"] = new_balance
            user["updated_at"] = updated_at
            local_users[str(user_id)] = user
            save_user_store()
    except Exception as exc:
        user["balance"] = old_balance
        print(f"⚠️ Balance update failed for {user_id}: {exc}")
        return False

    user["balance"] = new_balance
    user["updated_at"] = updated_at
    try:
        record_history(
            user_id,
            reason,
            message=f"Balance changed by {amount:.2f} TK",
            amount=amount,
            balance_after=new_balance
        )
    except Exception as exc:
        print(f"⚠️ Balance history write failed for {user_id}: {exc}")
    return True

def _referral_is_paid(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "paid"}
    return bool(value)


REFERRAL_OTP_MILESTONE = 15
REFERRAL_OTP_BONUS_PER_OTP = 0.10


def _otp_bonus_notifications_enabled(user):
    value = user.get("otp_bonus_notifications", True)
    if isinstance(value, str):
        return value.strip().casefold() not in {"0", "false", "no", "off"}
    return bool(value)


def _persist_user_fields(user_id, user, fields):
    """Persist a small set of user fields without rewriting other records."""
    user_key = str(user_id).strip()
    updates = dict(fields)
    updates["updated_at"] = iso_now()
    try:
        if db:
            db.collection("users").document(user_key).set(updates, merge=True)
        else:
            user.update(updates)
            local_users[user_key] = user
            save_user_store()
    except Exception as exc:
        print(f"⚠️ Could not save user settings for {user_key}: {exc}")
        return False

    user.update(updates)
    with user_data_lock:
        user_cache[user_key] = user
    local_users[user_key] = user
    return True


def set_otp_bonus_notifications(user_id, enabled):
    """Set only this account's referral OTP bonus message preference."""
    with _user_operation_lock(user_id):
        user = get_user(user_id)
        return _persist_user_fields(
            user_id,
            user,
            {"otp_bonus_notifications": bool(enabled)},
        )


def _fresh_user_for_referral_credit(user_id):
    """Read the inviter's latest balance and referral progress before crediting."""
    user_key = str(user_id).strip()
    if db:
        document = db.collection("users").document(user_key).get()
        if document.exists:
            user = document.to_dict()
            if not isinstance(user, dict):
                user = {}
            _cache_user_record(user_id, user_key, user)
            local_users[user_key] = user
            return user
    return get_user(user_id)


def _referral_progress_for(inviter, referred_id):
    all_progress = inviter.get("referral_bonus_progress", {})
    if not isinstance(all_progress, dict):
        return {}
    state = all_progress.get(str(referred_id), {})
    return state if isinstance(state, dict) else {}


def _save_referral_progress_seed(inviter_id, referred_id, last_otp):
    """Mark a legacy paid referral as qualified without paying it a second time."""
    inviter_key = str(inviter_id).strip()
    referred_key = str(referred_id).strip()
    with _user_operation_lock(inviter_id):
        inviter = _fresh_user_for_referral_credit(inviter_id)
        progress = copy.deepcopy(inviter.get("referral_bonus_progress", {}))
        if not isinstance(progress, dict):
            progress = {}
        current = progress.get(referred_key, {})
        if isinstance(current, dict) and current.get("milestone_paid"):
            return {
                "ok": True,
                "milestone_paid": True,
                "last_otp": max(
                    REFERRAL_OTP_MILESTONE,
                    int(_as_number(current.get("last_otp"), REFERRAL_OTP_MILESTONE)),
                ),
            }

        seeded_last_otp = max(REFERRAL_OTP_MILESTONE, int(last_otp))
        progress[referred_key] = {
            "milestone_paid": True,
            "last_otp": seeded_last_otp,
        }
        updates = {
            "user_id": inviter_id,
            "referral_bonus_progress": progress,
            "updated_at": iso_now(),
        }
        try:
            if db:
                db.collection("users").document(inviter_key).set(
                    updates,
                    merge=True,
                )
            else:
                inviter.update(updates)
                local_users[inviter_key] = inviter
                save_user_store()
        except Exception as exc:
            print(f"⚠️ Could not initialize referral progress: {exc}")
            return {"ok": False, "last_otp": 0}

        inviter.update(updates)
        with user_data_lock:
            user_cache[inviter_key] = inviter
        local_users[inviter_key] = inviter
        return {
            "ok": True,
            "milestone_paid": True,
            "last_otp": seeded_last_otp,
        }


def _apply_referral_bonus_credit(
    inviter_id,
    referred_id,
    bonus_kind,
    amount,
    last_otp,
):
    """Atomically store inviter balance and referral cursor in one user record."""
    inviter_key = str(inviter_id).strip()
    referred_key = str(referred_id).strip()
    with _user_operation_lock(inviter_id):
        inviter = _fresh_user_for_referral_credit(inviter_id)
        progress = copy.deepcopy(inviter.get("referral_bonus_progress", {}))
        if not isinstance(progress, dict):
            progress = {}
        state = progress.get(referred_key, {})
        if not isinstance(state, dict):
            state = {}
        state = copy.deepcopy(state)

        if bonus_kind == "milestone":
            if state.get("milestone_paid"):
                return {
                    "ok": True,
                    "applied": False,
                    "last_otp": max(
                        REFERRAL_OTP_MILESTONE,
                        int(_as_number(state.get("last_otp"), REFERRAL_OTP_MILESTONE)),
                    ),
                    "amount": 0.0,
                }
            target_otp = max(REFERRAL_OTP_MILESTONE, int(last_otp))
            state["milestone_paid"] = True
            state["last_otp"] = target_otp
            total_refers = int(_as_number(inviter.get("total_refers"), 0)) + 1
        elif bonus_kind == "per_otp":
            if not state.get("milestone_paid"):
                return {"ok": False, "applied": False, "last_otp": 0, "amount": 0.0}
            previous_otp = max(
                REFERRAL_OTP_MILESTONE,
                int(_as_number(state.get("last_otp"), REFERRAL_OTP_MILESTONE)),
            )
            target_otp = int(last_otp)
            if target_otp <= previous_otp:
                return {
                    "ok": True,
                    "applied": False,
                    "last_otp": previous_otp,
                    "amount": 0.0,
                }
            amount = round(
                (target_otp - previous_otp) * REFERRAL_OTP_BONUS_PER_OTP,
                2,
            )
            state["last_otp"] = target_otp
            total_refers = None
        else:
            return {"ok": False, "applied": False, "last_otp": 0, "amount": 0.0}

        try:
            amount = round(float(amount), 2)
            old_balance = round(float(inviter.get("balance", 0.0) or 0.0), 2)
        except (TypeError, ValueError, OverflowError):
            return {"ok": False, "applied": False, "last_otp": 0, "amount": 0.0}
        balance_after = round(old_balance + amount, 2)
        if (
            not math.isfinite(amount)
            or not math.isfinite(balance_after)
            or amount < 0
        ):
            return {"ok": False, "applied": False, "last_otp": 0, "amount": 0.0}

        state["updated_at"] = iso_now()
        progress[referred_key] = state
        updates = {
            "user_id": inviter_id,
            "balance": balance_after,
            "referral_bonus_progress": progress,
            "updated_at": iso_now(),
        }
        if total_refers is not None:
            updates["total_refers"] = total_refers
        try:
            if db:
                db.collection("users").document(inviter_key).set(
                    updates,
                    merge=True,
                )
            else:
                inviter.update(updates)
                local_users[inviter_key] = inviter
                save_user_store()
        except Exception as exc:
            print(f"⚠️ Referral bonus credit failed for {inviter_key}: {exc}")
            return {"ok": False, "applied": False, "last_otp": 0, "amount": 0.0}

        inviter.update(updates)
        with user_data_lock:
            user_cache[inviter_key] = inviter
        local_users[inviter_key] = inviter
        record_history(
            inviter_id,
            "referral_reward" if bonus_kind == "milestone" else "referral_otp_bonus",
            message=(
                "Referral reached 15 successful OTPs"
                if bonus_kind == "milestone"
                else f"Referral OTP bonus through OTP #{target_otp}"
            ),
            amount=amount,
            balance_after=balance_after,
            request_id=(
                f"REF-{referred_key}-15"
                if bonus_kind == "milestone"
                else f"REF-{referred_key}-OTP-{target_otp}"
            ),
        )
        return {
            "ok": True,
            "applied": True,
            "last_otp": target_otp,
            "amount": amount,
        }


def _send_referral_bonus_notification(inviter_id, kind, amount, otp_count=None):
    inviter = get_user(inviter_id)
    if not _otp_bonus_notifications_enabled(inviter):
        return
    if kind == "milestone":
        text = (
            "🎉 <b>রেফারেল বোনাস পেয়েছেন!</b>\n"
            "আপনার রেফার করা ব্যবহারকারী ১৫টি সফল OTP পেয়েছে।\n"
            f"৳{format_balance(amount)} আপনার ব্যালেন্সে যোগ হয়েছে।"
        )
    else:
        text = (
            "🎁 <b>Referral OTP bonus</b>\n"
            f"{otp_count}টি নতুন OTP-এর জন্য "
            f"৳{format_balance(amount)} আপনার ব্যালেন্সে যোগ হয়েছে।"
        )
    send_message(inviter_id, render_body_text(text))


def process_referral_otp_bonus(
    referred_user_id,
    otp_count=None,
    new_otp_event=False,
):
    """Pay the milestone at OTP 15, then 0.10 TK for each later OTP."""
    notifications = []
    processed_any = False
    try:
        referred_key = str(referred_user_id).strip()
        with referral_lock:
            with _user_operation_lock(referred_user_id):
                referred_user = get_user(referred_user_id)
                inviter_value = referred_user.get("referred_by")
                if not inviter_value:
                    return False
                try:
                    inviter_id = int(inviter_value)
                    referred_numeric_id = int(referred_user_id)
                except (TypeError, ValueError):
                    return False
                if inviter_id == referred_numeric_id:
                    return False

                current_otp_count = max(
                    0,
                    int(_as_number(referred_user.get("total_otps"), 0)),
                )
                try:
                    event_otp_count = (
                        max(0, int(otp_count))
                        if otp_count is not None else current_otp_count
                    )
                except (TypeError, ValueError, OverflowError):
                    event_otp_count = current_otp_count
                current_otp_count = max(current_otp_count, event_otp_count)

                inviter = _fresh_user_for_referral_credit(inviter_id)
                progress = _referral_progress_for(inviter, referred_key)
                ledger_milestone_paid = bool(progress.get("milestone_paid"))
                referred_milestone_paid = _referral_is_paid(
                    referred_user.get("ref_paid")
                )

                if not ledger_milestone_paid and not referred_milestone_paid:
                    if current_otp_count < REFERRAL_OTP_MILESTONE:
                        return False
                    reward = float(bot_settings.get("refer_reward", 0.5))
                    if not math.isfinite(reward) or reward < 0:
                        reward = 0.5
                    baseline_otp = (
                        current_otp_count
                        if not new_otp_event
                        else max(
                            REFERRAL_OTP_MILESTONE,
                            event_otp_count - 1,
                        )
                    )
                    result = _apply_referral_bonus_credit(
                        inviter_id,
                        referred_key,
                        "milestone",
                        reward,
                        baseline_otp,
                    )
                    if not result.get("ok"):
                        return False
                    last_paid_otp = result["last_otp"]
                    _persist_user_fields(
                        referred_user_id,
                        referred_user,
                        {
                            "ref_paid": True,
                            "ref_bonus_last_otp": last_paid_otp,
                        },
                    )
                    if result.get("applied"):
                        notifications.append(
                            (inviter_id, "milestone", result["amount"], None)
                        )
                        processed_any = True
                else:
                    if not ledger_milestone_paid:
                        # Old builds paid ref_paid users immediately. Seed their
                        # cursor at today's OTP count so old OTPs aren't paid again.
                        baseline_otp = (
                            current_otp_count
                            if not new_otp_event
                            else max(
                                REFERRAL_OTP_MILESTONE,
                                event_otp_count - 1,
                            )
                        )
                        result = _save_referral_progress_seed(
                            inviter_id,
                            referred_key,
                            baseline_otp,
                        )
                        if not result.get("ok"):
                            return False
                        last_paid_otp = result["last_otp"]
                    else:
                        last_paid_otp = max(
                            REFERRAL_OTP_MILESTONE,
                            int(_as_number(
                                progress.get("last_otp"),
                                REFERRAL_OTP_MILESTONE,
                            )),
                        )

                    if not referred_milestone_paid or (
                        int(_as_number(
                            referred_user.get("ref_bonus_last_otp"),
                            -1,
                        )) != last_paid_otp
                    ):
                        _persist_user_fields(
                            referred_user_id,
                            referred_user,
                            {
                                "ref_paid": True,
                                "ref_bonus_last_otp": last_paid_otp,
                            },
                        )

                if current_otp_count > last_paid_otp:
                    result = _apply_referral_bonus_credit(
                        inviter_id,
                        referred_key,
                        "per_otp",
                        0.0,
                        current_otp_count,
                    )
                    if result.get("ok") and result.get("applied"):
                        last_paid_otp = result["last_otp"]
                        _persist_user_fields(
                            referred_user_id,
                            referred_user,
                            {
                                "ref_paid": True,
                                "ref_bonus_last_otp": last_paid_otp,
                            },
                        )
                        notifications.append(
                            (
                                inviter_id,
                                "per_otp",
                                result["amount"],
                                current_otp_count - REFERRAL_OTP_MILESTONE,
                            )
                        )
                        processed_any = True

        # Send notices outside the user/referral locks. Turning notices off
        # never stops the balance credits.
        for notice in notifications:
            try:
                _send_referral_bonus_notification(*notice)
            except Exception as exc:
                print(f"⚠️ Could not send referral bonus notice: {exc}")
        return processed_any
    except Exception as exc:
        print(f"⚠️ Referral OTP bonus processing error: {exc}")
        return False


def add_referral(new_user_id):
    """Check an existing referral without paying before the 15-OTP milestone."""
    return process_referral_otp_bonus(new_user_id)

# ==========================================
# UI Keyboards & Menu Builders
# ==========================================
def get_cancel_kb():
    return {"inline_keyboard": [[{"text": "Close", "icon_custom_emoji_id": CROSS_CANCEL_EMOJI_ID, "callback_data": "cancel_state", "style": "danger"}]]}

def language_selector_markup():
    return {"inline_keyboard": [
        [{"text": "ENGLISH", "icon_custom_emoji_id": LANGUAGE_EMOJI_ID, "callback_data": "set_lang_EN", "style": "primary"}],
        [{"text": "BANGLA", "icon_custom_emoji_id": LANGUAGE_EMOJI_ID, "callback_data": "set_lang_BN", "style": "success"}],
    ]}

def send_language_selector(chat_id):
    text = "🌐 <b>SELECT LANGUAGE</b>\n\nCHOOSE YOUR LANGUAGE / আপনার ভাষা নির্বাচন করুন"
    send_message(chat_id, render_body_text(text), reply_markup=language_selector_markup())

def send_start_ui(chat_id):
    end_admin_reply_session(chat_id)
    c_msg = bot_settings["custom_messages"].get("start", {})
    user = get_user(chat_id)
    user_name = (
        user.get("user_name")
        or user.get("full_name")
        or user.get("username")
        or "User"
    )
    start_text = c_msg.get("text", DEFAULT_WELCOME_TEXT)
    if start_text == LEGACY_DEFAULT_START_TEXT:
        start_text = DEFAULT_WELCOME_TEXT
    escaped_user_name = html.escape(str(user_name), quote=True)
    start_text = str(start_text).replace("{user_name}", escaped_user_name)
    start_text = re.sub(
        r"\bUser\b",
        lambda _match: escaped_user_name,
        start_text,
        flags=re.IGNORECASE,
    )
    txt = render_body_text(start_text)
    kb = []
    for button in c_msg.get("buttons", []):
        button_copy = button.copy()
        button_copy.setdefault("style", "primary")
        kb.append([button_copy])
    if kb:
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})
        send_message(chat_id, render_body_text(f"{PEM['gear']} NAVIGATION MENU:"), reply_markup=main_menu(chat_id))
    else:
        send_message(chat_id, txt, reply_markup=main_menu(chat_id))


def end_admin_reply_session(chat_id):
    system_settings_reply_sessions.discard(chat_id)
    system_settings_reply_actions.pop(chat_id, None)
    system_settings_message_ids.pop(chat_id, None)


def main_menu(user_id):
    # The general navigation keyboard ends the admin-submenu reply session.
    end_admin_reply_session(user_id)
    kb = [
        [
            {"text": "GET NUMBER", "icon_custom_emoji_id": GET_NUMBER_EMOJI_ID, "style": "primary"},
            {"text": "TRAFFIC", "icon_custom_emoji_id": "5352877703043258544", "style": "danger"},
        ],
        [
            {"text": "2FA SET", "icon_custom_emoji_id": TWO_FA_BUTTON_EMOJI_ID, "style": "primary"},
        ],
        [
            {"text": "REFER", "icon_custom_emoji_id": REFERRAL_EMOJI_ID, "style": "primary"},
            {"text": "WITHDRAWAL", "icon_custom_emoji_id": WITHDRAWAL_EMOJI_ID, "style": "danger"},
        ],
    ]
    if is_admin(user_id):
        kb.append([{"text": "ADMIN PANEL", "icon_custom_emoji_id": "5420155432272438703", "style": "danger"}])
    else:
        kb.append([{"text": "SUPPORT", "icon_custom_emoji_id": "5420145051336485498", "style": "danger"}])
    return {"keyboard": kb, "resize_keyboard": True}

def get_admin_text():
    otp_counts = get_otp_period_counts()
    try:
        # Count persisted documents directly; the background known-user cache
        # can be half-filled while it is refreshing after startup.
        users_count = (
            sum(1 for _ in db.collection("users").stream())
            if db else len(all_known_users)
        )
    except Exception:
        users_count = len(all_known_users)
    total_files = len(number_batches)
    available_nums = sum(
        len(batch.get("numbers", []))
        for batch in number_batches.values()
        if isinstance(batch, dict) and isinstance(batch.get("numbers", []), list)
    )
    try:
        total_numbers = max(int(total_uploaded_stats or 0), available_nums)
    except (TypeError, ValueError):
        total_numbers = available_nums
    try:
        assigned_numbers = int(total_assigned_stats or 0)
    except (TypeError, ValueError):
        assigned_numbers = 0

    stock_capacity = max(total_numbers, available_nums)
    stock_bar_width = max(20, min(40, len(str(max(0, stock_capacity))) * 5))
    filled_cells = (
        min(
            stock_bar_width,
            max(0, round(stock_bar_width * available_nums / stock_capacity)),
        )
        if stock_capacity else 0
    )
    stock_bar = "█" * filled_cells + "░" * (stock_bar_width - filled_cells)

    txt = f"""
<tg-emoji emoji-id="6221892119808714203">👆</tg-emoji> <b>ADMIN CONTROL PANEL</b> <tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>
◈━━━━━━━━━━━━━━━━━━◈

<tg-emoji emoji-id="6221761819090887073">🔔</tg-emoji><b>OTP RECEIVED</b>
Today OTP » {otp_counts['today']} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>
Last 7 days » {otp_counts['7_days']} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>
Last 30 days » {otp_counts['30_days']} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>

<tg-emoji emoji-id="6224280929079141302">🚫</tg-emoji> <b>DATABASE OVERVIEW</b> <tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>
┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅
<tg-emoji emoji-id="6224334680594850487">👥</tg-emoji> All Users       » {users_count} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>
<tg-emoji emoji-id="6201908796621598047">📞</tg-emoji> Numbers         » {total_numbers} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>
<tg-emoji emoji-id="6201761423408768085">✔️</tg-emoji> Assigned        » {assigned_numbers} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>
<tg-emoji emoji-id="6201914938424827608">🌟</tg-emoji> Available       » {available_nums} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>
<tg-emoji emoji-id="6224124059693622546">📤</tg-emoji> Uploaded Files  » {total_files} <tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>

<tg-emoji emoji-id="6201696285934757140">👍</tg-emoji> <b>STOCK LEVEL</b> <tg-emoji emoji-id="6199217359660525540">📈</tg-emoji>
┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅
[{stock_bar}] {available_nums} free<tg-emoji emoji-id="6226356085477875334">🌀</tg-emoji>
◈━━━━━━━━━━━━━━━━━━◈
"""
    return render_body_text(txt)

def get_local_db_status_text():
    counts = {
        "Users": sum(1 for _ in db.collection("users").stream()),
        "Withdrawals": sum(1 for _ in db.collection("withdrawals").stream()),
        "History": sum(1 for _ in db.collection("history").stream()),
    }
    files = ", ".join(_LOCAL_COLLECTION_FILES.values())
    return (
        "💾 <b>LOCAL DATABASE</b>\n\n"
        "Status: <b>READY</b>\n"
        f"Directory: <code>{html.escape(BOT_DATA_DIR)}</code>\n"
        f"Users: {counts['Users']} | Withdrawals: {counts['Withdrawals']} | History: {counts['History']}\n"
        f"Files: <code>{html.escape(files)}</code>\n\n"
        "Records are written to local JSON files; External spreadsheet sync is disabled."
    )


def admin_panel_keyboard(admin_id=None):
    return {
        "keyboard": [
            [{"text": "System Management", "icon_custom_emoji_id": "5420155432272438703", "style": "primary"}],
            [{"text": "Broadcast", "icon_custom_emoji_id": MESSAGE_SMS_EMOJI_ID, "style": "success"},
             {"text": "Upload Number", "icon_custom_emoji_id": UPLOAD_EMOJI_ID, "style": "success"}],
            [{"text": "Delete Management", "icon_custom_emoji_id": "6224256529369932354", "style": "danger"},
             {"text": "Number Management", "icon_custom_emoji_id": "6224284210434154938", "style": "danger"}],
            [{"text": "Master Panel", "icon_custom_emoji_id": "6224162624204972282", "style": "success"},
             {"text": "BOT MANAGEMENT", "icon_custom_emoji_id": "6203810466406342809", "style": "success"}],
            [{"text": "Back to Main Menu", "icon_custom_emoji_id": "5267490665117275176", "style": "danger"}],
        ],
        "resize_keyboard": True,
    }


def number_management_keyboard():
    return {
        "keyboard": [
            [{"text": "Used Number", "icon_custom_emoji_id": "6224038684333711964", "style": "success"},
             {"text": "Unused Number", "icon_custom_emoji_id": "5352597830089347330", "style": "success"}],
            [{"text": "Back to Admin Panel", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "style": "primary"}],
        ],
        "resize_keyboard": True,
    }


def delete_management_keyboard():
    return {
        "keyboard": [
            [{"text": "Delete File", "icon_custom_emoji_id": "6224256529369932354", "style": "danger"},
             {"text": "Delete Data", "icon_custom_emoji_id": "6224256529369932354", "style": "danger"}],
            [{"text": "Back to Admin Panel", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "style": "primary"}],
        ],
        "resize_keyboard": True,
    }


ADMIN_REPLY_COMMANDS = (
    "SYSTEM MANAGEMENT",
    "SYSTEM CONFIG",
    "LOCAL DATABASE",
    "BROADCAST",
    "UPLOAD NUMBER",
    "DELETE MANAGEMENT",
    "DELETE FILE",
    "DELETE FILES",
    "DELETE DATA",
    "NUMBER MANAGEMENT",
    "USED NUMBER",
    "UNUSED NUMBER",
    "MASTER PANEL",
    "BOT MANAGEMENT",
    "GX CONTROL",
    "BACK TO ADMIN PANEL",
    "BACK TO MAIN MENU",
)

ADMIN_SLASH_COMMANDS = frozenset({"/localdb", "/withdraw", "/numshare"})
BONUS_ALERT_COMMAND = "/bonusalert"
OTP_BONUS_NOTIFICATION_COMMANDS = frozenset({
    "/otpbonus_on",
    "/otpbonus_off",
})


def system_settings_keyboard(admin_id=None):
    demo_status = "ON" if bot_settings.get("demo_on", False) else "OFF"
    demo_interval = bot_settings.get("demo_interval", 2)
    demo_icon = "6224038684333711964" if bot_settings.get("demo_on", False) else "5420130255174145507"
    notification_status = (
        "ON" if admin_id is None or get_join_notification_status(admin_id) else "OFF"
    )
    inline_keyboard = [
        [{"text": "RANKING BOARD", "icon_custom_emoji_id": "6224240114004927438", "callback_data": "lb_main", "style": "primary"}],
        [{"text": f"JOIN ALERTS: {notification_status}", "icon_custom_emoji_id": "5352980533150259581", "callback_data": "toggle_join_notify", "style": "success" if notification_status == "ON" else "primary"},
         {"text": f"Demo SMS: {demo_status}", "icon_custom_emoji_id": MESSAGE_SMS_EMOJI_ID, "callback_data": "toggle_demo", "style": "success" if demo_status == "ON" else "primary"}],
        [{"text": "TIMER SET", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "set_demo_interval", "style": "primary"},
         {"text": "SYSTEM BACKUP", "icon_custom_emoji_id": UPLOAD_EMOJI_ID, "callback_data": "backup_all_data", "style": "primary"}],
        [{"text": "RECOVER DATA", "icon_custom_emoji_id": "6223982811104159288", "callback_data": "restore_all_data", "style": "success"},
         {"text": "MEMBER & ADMIN", "icon_custom_emoji_id": "6131927071946970439", "callback_data": "member_admin_management", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
    ]
    return {
        "inline_keyboard": inline_keyboard,
    }


def system_settings_reply_action(chat_id, text):
    """Map System Settings reply-button labels to their former callback actions."""
    normalized = _system_settings_button_key(text)
    menu_action = system_settings_reply_actions.get(chat_id, {}).get(normalized)
    if menu_action:
        return menu_action

    actions = {
        "▰ MASTER PANEL ▰": "manage_panels",
        "⚡▰ MASTER PANEL ▰⚡": "manage_panels",
        "RANKING BOARD": "lb_main",
        "🔥 RANKING BOARD": "lb_main",
        "TIMER SET": "set_demo_interval",
        "MEMBER & ADMIN": "member_admin_management",
        "SYSTEM BACKUP": "backup_all_data",
        "RECOVER DATA": "restore_all_data",
        "MANAGE ADMINS": "manage_admins",
        "MANAGE USERS": "user_management",
        "BOT MANAGEMENT": "GX_control",
        "Panel Management": "manage_panels",
        "Leaderboard": "lb_main",
        "Backup Data": "backup_all_data",
        "Restore": "restore_all_data",
        "Admin Management": "manage_admins",
        "User Management": "user_management",
        "GX Control": "GX_control",
        "GX CONTROL": "GX_control",
        "Back": "back_to_admin",
    }
    for label, callback_data in actions.items():
        localized_label = normal_button_text(localize_ui_text(chat_id, label)).strip().casefold()
        if normalized == localized_label:
            return callback_data

    for label in (
        "JOIN ALERTS: ON",
        "JOIN ALERTS: OFF",
        "Join Notification: ON",
        "Join Notification: OFF",
    ):
        localized_label = normal_button_text(localize_ui_text(chat_id, label)).strip().casefold()
        if normalized == localized_label:
            return "toggle_join_notify"

    for label in (
        "Demo SMS: ON",
        "Demo SMS: OFF",
        "🎭 Demo SMS: ON",
        "🎭 Demo SMS: OFF",
    ):
        localized_label = normal_button_text(localize_ui_text(chat_id, label)).strip().casefold()
        if normalized == localized_label:
            return "toggle_demo"

    interval_prefix = normal_button_text(localize_ui_text(chat_id, "⏱ ")).strip()
    if (
        normalized.startswith(interval_prefix.casefold())
        and re.fullmatch(r"⏱\s*\d+\s*s", normalized, flags=re.IGNORECASE)
    ) or re.fullmatch(r"\d+\s*s", normalized, flags=re.IGNORECASE):
        return "set_demo_interval"
    return None


def send_system_settings(chat_id, replace_message_id=None, text=None):
    """Send System Settings as an inline menu with directly routed callbacks."""
    system_settings_reply_sessions.add(chat_id)
    system_settings_reply_actions.pop(chat_id, None)

    result = send_message(
        chat_id,
        text or render_body_text(
            '<tg-emoji emoji-id="5370935802844946281">⚙️</tg-emoji> '
            '<b>SYSTEM MANAGEMENT</b> '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
        ),
        reply_markup=system_settings_keyboard(chat_id),
    )
    result_message_id = (
        result.get("result", {}).get("message_id")
        if isinstance(result, dict) and result.get("ok")
        else None
    )
    if result_message_id:
        system_settings_message_ids[chat_id] = result_message_id
        if replace_message_id and int(replace_message_id) != int(result_message_id):
            delete_message(chat_id, replace_message_id)
    else:
        system_settings_message_ids.pop(chat_id, None)
    return result


def send_admin_panel(chat_id, text=None):
    # Keep every submenu reached from the admin panel on a ReplyKeyboardMarkup.
    system_settings_reply_sessions.add(chat_id)
    system_settings_reply_actions.pop(chat_id, None)
    system_settings_message_ids.pop(chat_id, None)
    return send_message(
        chat_id,
        text or get_admin_text(),
        reply_markup=admin_panel_keyboard(chat_id),
    )


def handle_admin_reply_action(chat_id, command):
    """Route persistent admin reply-keyboard buttons to their existing actions."""
    if not is_admin(chat_id):
        send_message(chat_id, render_body_text("🚫 Admin only."))
        return True

    if command in {"SYSTEM MANAGEMENT", "SYSTEM CONFIG"}:
        send_system_settings(chat_id)
    elif command == "NUMBER MANAGEMENT":
        send_message(
            chat_id,
            render_body_text("<b>NUMBER MANAGEMENT</b>"),
            reply_markup=number_management_keyboard(),
        )
    elif command == "DELETE MANAGEMENT":
        send_message(
            chat_id,
            render_body_text("<b>DELETE MANAGEMENT</b>"),
            reply_markup=delete_management_keyboard(),
        )
    elif command in {"MASTER PANEL", "BOT MANAGEMENT", "GX CONTROL"}:
        callback_data = (
            "manage_panels" if command == "MASTER PANEL" else "GX_control"
        )
        message_id = system_settings_message_ids.get(chat_id)
        if not message_id:
            send_admin_panel(chat_id)
            message_id = system_settings_message_ids.get(chat_id)
        if message_id:
            handle_callback({
                "from": {"id": chat_id},
                "message": {
                    "chat": {"id": chat_id, "type": "private"},
                    "message_id": message_id,
                },
                "data": callback_data,
                "id": "__reply_keyboard__",
            })
    elif command == "BACK TO ADMIN PANEL":
        send_admin_panel(chat_id)
    elif command == "LOCAL DATABASE":
        try:
            status_text = get_local_db_status_text()
        except Exception as exc:
            status_text = (
                "❌ <b>Could not read the local database status.</b>\n"
                f"<code>{html.escape(str(exc))}</code>"
            )
        send_message(
            chat_id,
            render_body_text(status_text),
            reply_markup={"inline_keyboard": [[
                {"text": "Back to Admin Panel",
                 "icon_custom_emoji_id": "5267490665117275176",
                 "callback_data": "back_to_admin", "style": "primary"}
            ]]},
        )
    elif command == "BROADCAST":
        user_states[chat_id] = "wait_for_broadcast"
        send_message(
            chat_id,
            render_body_text(
                "📢 <b>Broadcast Mode</b>\n\n"
                "Send the message you want to broadcast (Text, Photo, Video, File etc)."
            ),
            reply_markup={"inline_keyboard": [[
                {"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176",
                 "callback_data": "back_to_admin", "style": "danger"}
            ]]},
        )
    elif command == "UPLOAD NUMBER":
        user_states[chat_id] = "wait_for_txt"
        send_message(
            chat_id,
            render_body_text(
                '<tg-emoji emoji-id="6224124059693622546">📤</tg-emoji> '
                'Upload Your numbers .txt file '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
            ),
            reply_markup={"inline_keyboard": [[
                {"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                 "callback_data": "back_to_admin", "style": "danger"}
            ]]},
        )
    elif command in {"DELETE FILE", "DELETE FILES"}:
        keyboard = [
            [
                {"text": f"{batch.get('filename', batch_id)} ({len(batch.get('numbers', []))})",
                 "icon_custom_emoji_id": "6224256529369932354",
                 "callback_data": f"del_b_{batch_id}", "style": "danger"}
            ]
            for batch_id, batch in number_batches.items()
        ]
        keyboard.append([{
            "text": "Back",
            "icon_custom_emoji_id": "5267490665117275176",
            "callback_data": "back_to_delete_management",
            "style": "primary",
        }])
        message = (
            '<tg-emoji emoji-id="6224501578729005740">📁</tg-emoji> '
            'Chose a file to delete '
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
            if number_batches else f"{PEM['no']} No files found."
        )
        send_message(
            chat_id,
            render_body_text(message),
            reply_markup={"inline_keyboard": keyboard},
        )
    elif command == "DELETE DATA":
        send_message(
            chat_id,
            render_body_text(
                '<tg-emoji emoji-id="6224387933894354612">🚨</tg-emoji> '
                '<b>DELETE ALL BOT DATA</b> '
                '<tg-emoji emoji-id="6224003980997962148">❌</tg-emoji>\n\n'
                "This will remove users, balances, history, withdrawals, number stock, "
                "API keys and custom settings from the local JSON database.\n"
                "The owner account and safe default settings will remain so the bot can start again."
            ),
            reply_markup={"inline_keyboard": [
                [{"text": "YES, DELETE EVERYTHING",
                  "icon_custom_emoji_id": "6224256529369932354",
                  "callback_data": "delete_all_data_yes", "style": "danger"}],
                [{"text": "NO, GO BACK",
                  "icon_custom_emoji_id": "5267490665117274959",
                  "callback_data": "back_to_delete_management", "style": "primary"}],
            ]},
        )
    elif command == "USED NUMBER":
        send_message(
            chat_id,
            render_body_text(
                '<tg-emoji emoji-id="6224284210434154938">🍏</tg-emoji> '
                f'Total Used Numbers '
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                f'{len(used_numbers_list)}'
            ),
            reply_markup={"inline_keyboard": [
                [{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622",
                  "callback_data": "dl_used", "style": "primary"}],
                [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                  "callback_data": "back_to_number_management", "style": "danger"}],
            ]},
        )
    elif command == "UNUSED NUMBER":
        unused_count = sum(len(batch["numbers"]) for batch in number_batches.values())
        send_message(
            chat_id,
            render_body_text(
                '<tg-emoji emoji-id="6224284210434154938">🍏</tg-emoji> '
                f'Total Fresh Numbers '
                '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                f'{unused_count}'
            ),
            reply_markup={"inline_keyboard": [
                [{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622",
                  "callback_data": "dl_unused", "style": "primary"}],
                [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                  "callback_data": "back_to_number_management", "style": "danger"}],
            ]},
        )
    elif command == "BACK TO MAIN MENU":
        user_states.pop(chat_id, None)
        temp_data.pop(chat_id, None)
        send_message(
            chat_id,
            render_body_text(
                f'<tg-emoji emoji-id="{MAIN_MENU_EMOJI_ID}">⚙️</tg-emoji> '
                "<b>Main Menu</b>"
            ),
            reply_markup=main_menu(chat_id),
        )
    else:
        return False
    return True

def get_user_management_text():
    blocked = len(get_blocked_user_ids())
    total = max(0, len(all_known_users) - blocked)
    active = total
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        '<tg-emoji emoji-id="6222063592083039576">🔍</tg-emoji> '
        '<b>USER OBSERVING</b> '
        '<tg-emoji emoji-id="6224387079195861802">🛜</tg-emoji>\n'
        '━━━━━━━━━━━━━━━━━━\n'
        f'<tg-emoji emoji-id="6224334680594850487">👥</tg-emoji> Total Users » {total} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="6201668351467463489">✅</tg-emoji> '
        f'Active Users » {active} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="6222232264038686862">✅</tg-emoji> '
        f'Blocked Users » {blocked} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="6224020344823357132">✅</tg-emoji> '
        'Banned Users » Hidden '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '<tg-emoji emoji-id="5197288647275071607">🛡</tg-emoji> '
        'Verified Users » Hidden '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '━━━━━━━━━━━━━━━━━━\n'
        f'<tg-emoji emoji-id="6224250585135194803">😓</tg-emoji> '
        f'Last Updated: {now_str} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
    )


def get_blocked_users_page(page=0):
    blocked_ids = get_blocked_user_ids()
    page_size = 40
    page_count = max(1, (len(blocked_ids) + page_size - 1) // page_size)
    page = max(0, min(int(page), page_count - 1))
    start = page * page_size

    if blocked_ids:
        id_lines = "\n".join(
            f"<code>{html.escape(user_id)}</code>"
            for user_id in blocked_ids[start:start + page_size]
        )
        text = (
            f"<b>BLOCKED USERS ({len(blocked_ids)})</b>\n"
            f"Page {page + 1}/{page_count}\n\n{id_lines}"
        )
    else:
        text = "<b>BLOCKED USERS (0)</b>\n\nNo blocked user IDs recorded."

    keyboard = []
    if page_count > 1:
        navigation = []
        if page > 0:
            navigation.append({
                "text": "Previous",
                "callback_data": f"um_blocked_users_page_{page - 1}",
                "style": "primary",
            })
        if page + 1 < page_count:
            navigation.append({
                "text": "Next",
                "callback_data": f"um_blocked_users_page_{page + 1}",
                "style": "primary",
            })
        if navigation:
            keyboard.append(navigation)
    keyboard.append([{
        "text": "Back",
        "icon_custom_emoji_id": "5267490665117275176",
        "callback_data": "user_management",
        "style": "primary",
    }])
    return render_body_text(text), {"inline_keyboard": keyboard}

def user_management_keyboard():
    return {"inline_keyboard": [
        [{"text": "Manage Balance", "icon_custom_emoji_id": "6224387014771352176", "callback_data": "um_manage_balance", "style": "primary"},
         {"text": "User Profile", "icon_custom_emoji_id": "6222105571093389816", "callback_data": "um_user_profile", "style": "primary"}],
        [{"text": "Ban/Unban User", "icon_custom_emoji_id": "6224387933894354612", "callback_data": "um_ban_unban", "style": "danger"},
         {"text": "Blocked Users", "icon_custom_emoji_id": "6224003980997962148", "callback_data": "um_blocked_users_page_0", "style": "danger"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "member_admin_management", "style": "primary"}]
    ]}

def member_admin_management_keyboard():
    return {"inline_keyboard": [
        [{"text": "MANAGE USERS", "icon_custom_emoji_id": "5193063022226086560", "callback_data": "user_management", "style": "primary"},
         {"text": "MANAGE ADMINS", "icon_custom_emoji_id": "6221892119808714203", "callback_data": "manage_admins", "style": "primary"}],
        [{"text": "Back to System Management", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "callback_data": "system_settings", "style": "danger"}],
    ]}

def menu_design_list_keyboard():
    return {"inline_keyboard": [
        [{"text": "Edit GET NUMBER", "icon_custom_emoji_id": GET_NUMBER_EMOJI_ID, "callback_data": "md_edit_get_number", "style": "success"}],
        [{"text": "Edit Select Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "md_edit_select_country", "style": "primary"}],
        [{"text": "Edit TRAFFIC", "icon_custom_emoji_id": "5353032893096567467", "callback_data": "md_edit_traffic", "style": "primary"},
         {"text": "Edit Refer", "icon_custom_emoji_id": REFERRAL_EMOJI_ID, "callback_data": "md_edit_refer", "style": "primary"}],
        [{"text": "Edit WITHDRAWAL", "icon_custom_emoji_id": "5352585194295564660", "callback_data": "md_edit_withdrawal", "style": "danger"},
         {"text": "Edit SUPPORT", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "md_edit_support", "style": "danger"}],
        [{"text": "Reset Defaults", "icon_custom_emoji_id": RELOAD_RESTART_RESET_LOADING_EMOJI_ID, "callback_data": "md_reset_defaults", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def menu_edit_options_keyboard(menu_key):
    return {"inline_keyboard": [
        [{"text": "Edit Body (Text)", "icon_custom_emoji_id": "5395444784611480792", "callback_data": f"md_text_{menu_key}", "style": "primary"}],
        [{"text": "Edit Inline Buttons", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"md_btns_{menu_key}", "style": "success"}],
        [{"text": "Back to Menus", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "menu_design_list", "style": "danger"}]
    ]}

def menu_buttons_list_keyboard(menu_key):
    kb = []
    btns = bot_settings["custom_messages"].get(menu_key, {}).get("buttons", [])
    for idx, btn in enumerate(btns):
        kb.append([{"text": f"Del: {btn['text']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"md_delbtn_{menu_key}_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Inline Button", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"md_addbtn_{menu_key}", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_edit_{menu_key}", "style": "primary"}])
    return {"inline_keyboard": kb}

def fj_settings_keyboard():
    status_text = 'ON' if bot_settings['fj_on'] else 'OFF'
    status_icon = "6224038684333711964" if bot_settings['fj_on'] else "5318840353510408444"
    kb = [[{"text": f"STATUS: {status_text}", "icon_custom_emoji_id": status_icon, "callback_data": "toggle_fj", "style": "primary"}]]
    for idx, ch in enumerate(bot_settings["fj_channels"]):
        kb.append([{"text": f"Delete: {ch}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_fj_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Channel", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_fj", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
    return {"inline_keyboard": kb}

def get_admin_management_text():
    return render_body_text(
        '<tg-emoji emoji-id="6201961792223060752">💀</tg-emoji> '
        '<b>ADMIN MANAGEMENT</b> '
        '<tg-emoji emoji-id="6201914938424827608">🌟</tg-emoji>\n'
        'Manage your bot admins below '
        '<tg-emoji emoji-id="6233188575286927353">⬇️</tg-emoji>'
    )


def admin_settings_keyboard():
    kb = []
    for idx, adm in enumerate(bot_settings["admins"]):
        text_btn = f"Owner: {adm}" if adm == OWNER_ID else f"Delete: {adm}"
        icon_id = "5353032893096567467" if adm == OWNER_ID else "5420130255174145507"
        cb_data = "ignore" if adm == OWNER_ID else f"del_adm_{idx}"
        kb.append([{"text": text_btn, "icon_custom_emoji_id": icon_id, "callback_data": cb_data, "style": "danger" if adm != OWNER_ID else "primary"}])
    kb.append([{"text": "Add Admin", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_adm", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "member_admin_management", "style": "primary"}])
    return {"inline_keyboard": kb}

def otp_groups_list_keyboard():
    kb = [[{"text": "Edit Channel Button Link", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "edit_otp_link", "style": "primary"}]]
    for idx, fg in enumerate(bot_settings["fw_groups"]):
        kb.append([{"text": f"Group: {fg['chat_id']}", "icon_custom_emoji_id": "5193063022226086560", "callback_data": f"manage_fw_{idx}", "style": "primary"}])
    kb.append([{"text": "Add Forward Group", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_fw", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}])
    return {"inline_keyboard": kb}

def stex_control_keyboard():
    auto_status = "ON" if bot_settings.get("stex_auto", False) else "OFF"
    auto_emoji = "6224038684333711964" if auto_status == "ON" else "5420130255174145507"
    return {"inline_keyboard": [
        [{"text": "Add StexSMS Key", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_stex_key", "style": "success"},
         {"text": "View/Del Keys", "icon_custom_emoji_id": "6224256529369932354", "callback_data": "view_stex_keys", "style": "danger"}],
        [{"text": "Manage StexSMS Services", "icon_custom_emoji_id": "6222073659486381042", "callback_data": "manage_stex_srv", "style": "success"}],
        [{"text": f"Auto Range: {auto_status}", "icon_custom_emoji_id": auto_emoji, "callback_data": "toggle_stex_auto", "style": "success" if auto_status == "ON" else "primary"},
         {"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "stex_search_country", "style": "primary"}],
        [{"text": "Back to Panels", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "callback_data": "manage_panels", "style": "primary"}]
    ]}

def zenex_control_keyboard():
    auto_status = "ON" if bot_settings.get("zenex_auto", False) else "OFF"
    auto_emoji = "6224038684333711964" if auto_status == "ON" else "5420130255174145507"
    return {"inline_keyboard": [
        [{"text": "Add Zenex Key", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_zenex_key", "style": "success"},
         {"text": "View/Del Keys", "icon_custom_emoji_id": "6224256529369932354", "callback_data": "view_zenex_keys", "style": "danger"}],
        [{"text": "Manage Zenex Services", "icon_custom_emoji_id": "6222073659486381042", "callback_data": "manage_zenex_srv", "style": "success"}],
        [{"text": f"Auto Range: {auto_status}", "icon_custom_emoji_id": auto_emoji, "callback_data": "toggle_zenex_auto", "style": "success" if auto_status == "ON" else "primary"},
         {"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "zenex_search_country", "style": "primary"}],
        [{"text": "Back to Panels", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "callback_data": "manage_panels", "style": "primary"}]
    ]}

def voltx_control_keyboard():
    auto_status = "ON" if bot_settings.get("voltx_auto", False) else "OFF"
    auto_emoji = "6224038684333711964" if auto_status == "ON" else "5420130255174145507"
    return {"inline_keyboard": [
        [{"text": "Add Voltx Key", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_voltx_key", "style": "success"},
         {"text": "View/Del Keys", "icon_custom_emoji_id": "6224256529369932354", "callback_data": "view_voltx_keys", "style": "danger"}],
        [{"text": "Manage Voltx Services", "icon_custom_emoji_id": "6222073659486381042", "callback_data": "manage_voltx_srv", "style": "success"}],
        [{"text": f"Auto Range: {auto_status}", "icon_custom_emoji_id": auto_emoji, "callback_data": "toggle_voltx_auto", "style": "success" if auto_status == "ON" else "primary"},
         {"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "voltx_search_country", "style": "primary"}],
        [{"text": "Back to Panels", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "callback_data": "manage_panels", "style": "primary"}]
    ]}

def fastx_control_keyboard():
    auto_status = "ON" if bot_settings.get("fastx_auto", False) else "OFF"
    auto_emoji = "6224038684333711964" if auto_status == "ON" else "5420130255174145507"
    return {"inline_keyboard": [
        [{"text": "Add FastX Key", "icon_custom_emoji_id": "5420323438508155202",
          "callback_data": "add_fastx_key", "style": "success"},
         {"text": "View/Delete Keys", "icon_custom_emoji_id": "6224256529369932354",
          "callback_data": "view_fastx_keys", "style": "danger"}],
        [{"text": "Manage FastX Services", "icon_custom_emoji_id": "6222073659486381042",
          "callback_data": "manage_fastx_srv", "style": "success"}],
        [{"text": f"Auto Range: {auto_status}", "icon_custom_emoji_id": auto_emoji,
          "callback_data": "toggle_fastx_auto", "style": "success" if auto_status == "ON" else "primary"},
         {"text": "Search Country", "icon_custom_emoji_id": "5336972142066047577",
          "callback_data": "fastx_search_country", "style": "primary"}],
        [{"text": "Back to Panels", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
          "callback_data": "manage_panels", "style": "primary"}],
    ]}


def service_control_panel_text(service_name, key_count, emoji_id, emoji_char):
    safe_name = html.escape(str(service_name))
    service_icon = f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>'
    return (
        f'{service_icon} {safe_name} Control Panel '
        '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
        '◈━━━━━━━━━━━━━━━━━━◈\n'
        f'{service_icon}Total API Keys'
        '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>'
        f'{key_count} '
        '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
        f'Manage your {safe_name} API Keys below '
        '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>\n'
        '◈━━━━━━━━━━━━━━━━━━◈'
    )


def grouped_keyboard_rows(buttons, row_size=4):
    return [
        buttons[index:index + row_size]
        for index in range(0, len(buttons), row_size)
    ]


def fastx_search_country_keyboard():
    buttons = []
    for index, country_code in enumerate(bot_settings.get("fastx_search_countries", [])):
        buttons.append({
            "text": f"Delete {country_code}",
            "icon_custom_emoji_id": "5420130255174145507",
            "callback_data": f"fx_del_sc_{index}",
            "style": "danger",
        })
    keyboard = grouped_keyboard_rows(buttons, 4)
    keyboard.append([{
        "text": "Add Country Code",
        "icon_custom_emoji_id": "5420323438508155202",
        "callback_data": "add_fastx_search_country",
        "style": "success",
    }])
    keyboard.append([{
        "text": "Back",
        "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
        "callback_data": "fastx_control",
        "style": "primary",
    }])
    return {"inline_keyboard": keyboard}


def fastx_services_keyboard():
    services = bot_settings.get("fastx_services", {})
    services = services if isinstance(services, dict) else {}
    keyboard = []
    for index, service_name in enumerate(services):
        countries = services.get(service_name, {})
        country_count = len(countries) if isinstance(countries, dict) else 0
        keyboard.append([{
            "text": f"{service_name} ({country_count} countries)",
            "icon_custom_emoji_id": "5257969839313526622",
            "callback_data": f"fx_srv_{index}",
            "style": "primary",
        }])
    keyboard.append([{
        "text": "Add New Service",
        "icon_custom_emoji_id": "5420323438508155202",
        "callback_data": "fx_add_srv",
        "style": "success",
    }])
    keyboard.append([{
        "text": "Back",
        "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
        "callback_data": "fastx_control",
        "style": "primary",
    }])
    return {"inline_keyboard": keyboard}


def fastx_service_countries_keyboard(service_index):
    services = bot_settings.get("fastx_services", {})
    if not isinstance(services, dict):
        return {"inline_keyboard": [[{
            "text": "Back",
            "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
            "callback_data": "manage_fastx_srv",
            "style": "primary",
        }]]}
    service_names = list(services)
    if not 0 <= service_index < len(service_names):
        return fastx_services_keyboard()
    service_name = service_names[service_index]
    countries = services.get(service_name, {})
    countries = countries if isinstance(countries, dict) else {}
    keyboard = []
    for country_index, country_name in enumerate(countries):
        ranges = countries.get(country_name, [])
        keyboard.append([{
            "text": f"{country_name} ({len(ranges) if isinstance(ranges, list) else 0} ranges)",
            "icon_custom_emoji_id": "5780471598922337683",
            "callback_data": f"fx_cnt_{service_index}_{country_index}",
            "style": "primary",
        }])
    keyboard.extend([
        [{
            "text": "Add Country",
            "icon_custom_emoji_id": "5420323438508155202",
            "callback_data": f"fx_add_cnt_{service_index}",
            "style": "success",
        }],
        [{
            "text": "Delete Service",
            "icon_custom_emoji_id": "6224256529369932354",
            "callback_data": f"fx_del_srv_{service_index}",
            "style": "danger",
        }],
        [{
            "text": "Back",
            "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
            "callback_data": "manage_fastx_srv",
            "style": "primary",
        }],
    ])
    return {"inline_keyboard": keyboard}


def fastx_service_ranges_keyboard(service_index, country_index):
    services = bot_settings.get("fastx_services", {})
    if not isinstance(services, dict):
        return fastx_services_keyboard()
    service_names = list(services)
    if not 0 <= service_index < len(service_names):
        return fastx_services_keyboard()
    service_name = service_names[service_index]
    countries = services.get(service_name, {})
    if not isinstance(countries, dict):
        return fastx_service_countries_keyboard(service_index)
    country_names = list(countries)
    if not 0 <= country_index < len(country_names):
        return fastx_service_countries_keyboard(service_index)
    ranges = countries.get(country_names[country_index], [])
    ranges = ranges if isinstance(ranges, list) else [ranges]
    keyboard = []
    row = []
    for range_index, range_value in enumerate(ranges):
        row.append({
            "text": f"Delete {range_value}",
            "icon_custom_emoji_id": "5420130255174145507",
            "callback_data": f"fx_dr_{service_index}_{country_index}_{range_index}",
            "style": "danger",
        })
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.extend([
        [{
            "text": "Add Range",
            "icon_custom_emoji_id": "5420323438508155202",
            "callback_data": f"fx_addr_{service_index}_{country_index}",
            "style": "success",
        }],
        [{
            "text": "Delete Entire Country",
            "icon_custom_emoji_id": "6224256529369932354",
            "callback_data": f"fx_del_cnt_{service_index}_{country_index}",
            "style": "danger",
        }],
        [{
            "text": "Back",
            "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
            "callback_data": f"fx_srv_{service_index}",
            "style": "primary",
        }],
    ])
    return {"inline_keyboard": keyboard}

def specific_fw_group_keyboard(idx):
    group = bot_settings["fw_groups"][idx]
    kb = []
    for b_idx, btn in enumerate(group.get("buttons", [])):
        kb.append([{"text": f"Del: {btn['text']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_fwbtn_{idx}_{b_idx}", "style": "danger"}])
    
    kb.append([{"text": "Add Inline Button", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"add_fwbtn_{idx}", "style": "success"}])
    kb.append([{"text": "Delete Entire Group", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"del_fw_{idx}", "style": "danger"}])
    kb.append([{"text": "Back to Groups", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "primary"}])
    return {"inline_keyboard": kb}

def _panel_rate_service_key(panel, message="", service_hint=""):
    """Identify a managed-panel service consistently for UI and OTP payout."""
    candidates = [
        detect_service(service_hint),
        detect_service(message),
        service_hint,
        panel.get("name", "Panel"),
    ]
    for candidate in candidates:
        value = re.sub(r"\s+", " ", str(candidate or "")).strip()
        if not value:
            continue
        detected = detect_service(value)
        return str(detected or value).upper()
    return "PANEL"


def _panel_casefold_key(mapping, wanted):
    """Find a mapping key without depending on old settings' capitalization."""
    if not isinstance(mapping, dict):
        return None
    wanted = str(wanted or "").strip().casefold()
    for key in mapping:
        if str(key).strip().casefold() == wanted:
            return key
    return None


def _panel_service_country_map(panel, field, service):
    catalog = panel.get(field, {}) if isinstance(panel, dict) else {}
    service_key = _panel_casefold_key(catalog, service)
    if service_key is None:
        return None, {}
    countries = catalog.get(service_key, {})
    return service_key, countries if isinstance(countries, dict) else {}


def _panel_rate_service_keys(panel):
    services = set()
    for field in ("otp_rate_catalog", "otp_rates"):
        catalog = panel.get(field, {})
        if isinstance(catalog, dict):
            services.update(
                str(service).strip().upper()
                for service, countries in catalog.items()
                if str(service).strip() and isinstance(countries, dict)
            )
    services.add(_panel_rate_service_key(panel))
    return sorted(services, key=str.casefold)


def _panel_rate_country_keys(panel, service):
    keys = set()
    for field in ("otp_rate_catalog", "otp_rates"):
        _service_key, countries = _panel_service_country_map(
            panel, field, service
        )
        if isinstance(countries, dict):
            keys.update(
                str(country).strip().upper()
                for country in countries
                if str(country).strip()
            )
    return sorted(keys)


def _panel_rate_country_label(country):
    value = str(country or "").strip().upper()
    try:
        return str(get_flag_info_html(value, return_full_name=True) or value)
    except Exception:
        return value


def _resolve_panel_rate_country(value):
    """Resolve a country name, ISO code, or configured calling code to ISO."""
    raw = re.sub(r"\s+", " ", str(value or "")).strip()
    if not raw:
        return None, None
    folded = raw.casefold()
    digits = re.sub(r"\D", "", raw)
    for flag_key, flag_data in bot_settings.get("premium_flags", {}).items():
        if not isinstance(flag_data, dict):
            continue
        calling_code = _flag_calling_code(flag_key, flag_data)
        iso = str(flag_data.get("iso", "")).strip().upper()
        name = str(flag_data.get("name", "")).strip()
        clean_code = re.sub(r"\D", "", str(calling_code))
        if (
            folded in {str(calling_code).casefold(), iso.casefold(), name.casefold()}
            or (digits and digits == clean_code)
        ):
            if iso:
                return iso, name or iso
    return None, None


def record_panel_rate_catalog(panel, number, message="", service_hint=""):
    """Remember service/country pairs exposed by a managed panel."""
    _flag, iso = get_flag_and_code(str(number or ""))
    iso = str(iso or "").strip().upper()
    if not iso or iso == "XX":
        return False
    service = _panel_rate_service_key(panel, message, service_hint)
    catalog = panel.get("otp_rate_catalog")
    if not isinstance(catalog, dict):
        catalog = {}
        panel["otp_rate_catalog"] = catalog
    countries = catalog.get(service)
    if not isinstance(countries, dict):
        countries = {}
        catalog[service] = countries
    label = _panel_rate_country_label(iso)
    if countries.get(iso) == label:
        return False
    countries[iso] = label
    return True


def panel_otp_reward(panel, number, message="", service_hint=""):
    """Return this panel's service/country override or the normal OTP reward."""
    service = _panel_rate_service_key(panel, message, service_hint)
    _flag, iso = get_flag_and_code(str(number or ""))
    _service_key, countries = _panel_service_country_map(
        panel, "otp_rates", service
    )
    country_key = _panel_casefold_key(countries, iso)
    if country_key is not None:
        try:
            reward = float(countries[country_key])
            return reward if math.isfinite(reward) and reward >= 0 else float(bot_settings.get("otp_reward", 0.0))
        except (TypeError, ValueError):
            pass
    return float(bot_settings.get("otp_reward", 0.0))


def panel_otp_rates_keyboard():
    buttons = []
    for idx, panel in enumerate(bot_settings.get("panels", [])):
        if not isinstance(panel, dict):
            continue
        name = str(panel.get("name", f"Panel {idx + 1}")).strip() or f"Panel {idx + 1}"
        panel_type = str(panel.get("type", "API Panel"))
        buttons.append([{
            "text": f"{name} · {panel_type}",
            "icon_custom_emoji_id": "5420155432272438703",
            "callback_data": f"panel_rate_panel_{idx}",
            "style": "primary",
        }])
    buttons.append([{
        "text": "Back",
        "icon_custom_emoji_id": "5267490665117275176",
        "callback_data": "GX_control",
        "style": "primary",
    }])
    return {"inline_keyboard": buttons}


def panel_rate_services_keyboard(panel_idx):
    panel = bot_settings["panels"][panel_idx]
    buttons = []
    for service_idx, service in enumerate(_panel_rate_service_keys(panel)):
        _service_key, countries = _panel_service_country_map(
            panel, "otp_rate_catalog", service
        )
        label, _icon = get_service_info_html(service, service)
        buttons.append([{
            "text": f"{label} ({len(countries) if isinstance(countries, dict) else 0} countries)",
            "icon_custom_emoji_id": get_service_icon_id(service, service),
            "callback_data": f"panel_rate_service_{panel_idx}_{service_idx}",
            "style": "success",
        }])
    buttons.extend([
        [{
            "text": "Back to Panels",
            "icon_custom_emoji_id": "5267490665117275176",
            "callback_data": "panel_otp_rates",
            "style": "primary",
        }],
        [{
            "text": "Back to OTP Rate",
            "icon_custom_emoji_id": "5267490665117275176",
            "callback_data": "GX_control",
            "style": "danger",
        }],
    ])
    return {"inline_keyboard": buttons}


def panel_rate_countries_keyboard(panel_idx, service):
    panel = bot_settings["panels"][panel_idx]
    service = str(service).strip().upper()
    _service_key, service_rates = _panel_service_country_map(
        panel, "otp_rates", service
    )
    buttons = []
    for country in _panel_rate_country_keys(panel, service):
        country_key = _panel_casefold_key(service_rates, country)
        if country_key is not None:
            rate_label = f"{service_rates[country_key]} TK/OTP"
        else:
            rate_label = f"Default {bot_settings.get('otp_reward', 0.0)} TK"
        emoji_id, _emoji = _picker_country_emoji(country)
        buttons.append([{
            "text": f"{_panel_rate_country_label(country)} · {rate_label}",
            "icon_custom_emoji_id": emoji_id,
            "callback_data": f"panel_rate_edit_{panel_idx}_{_panel_rate_service_keys(panel).index(service)}_{country}",
            "style": "success",
        }])
    buttons.extend([
        [{
            "text": "Add Country",
            "icon_custom_emoji_id": "5420323438508155202",
            "callback_data": f"panel_rate_add_{panel_idx}_{_panel_rate_service_keys(panel).index(service)}",
            "style": "primary",
        }],
        [{
            "text": "Back to Services",
            "icon_custom_emoji_id": "5267490665117275176",
            "callback_data": f"panel_rate_panel_{panel_idx}",
            "style": "primary",
        }],
        [{
            "text": "Back to OTP Rate",
            "icon_custom_emoji_id": "5267490665117275176",
            "callback_data": "GX_control",
            "style": "danger",
        }],
    ])
    return {"inline_keyboard": buttons}


def GX_control_keyboard():
    sup_status = "ON" if bot_settings.get("support_link") else "OFF"
    grp_status = "On" if bot_settings.get("w_group") else "Off"
    return {"inline_keyboard": [
        [{"text": f"Minimum Withdraw: {bot_settings['min_withdraw']}", "icon_custom_emoji_id": "6224119399654105709", "callback_data": "GX_min_w", "style": "success"},
         {"text": f"OTP Reward: {bot_settings['otp_reward']}", "icon_custom_emoji_id": "6224387014771352176", "callback_data": "GX_otp_r", "style": "primary"}],
        [{"text": f"REFER REWARD: {bot_settings['refer_reward']}", "icon_custom_emoji_id": REFERRAL_EMOJI_ID, "callback_data": "GX_ref_r", "style": "success"},
         {"text": f"COOLDOWN: {bot_settings['cooldown']}s", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "GX_cool", "style": "primary"}],
        [{"text": "OTP GROUP", "icon_custom_emoji_id": OTP_GROUP_EMOJI_ID, "callback_data": "manage_otp_groups", "style": "primary"}],
        [{"text": f"Number Per Request: {bot_settings['num_req']}", "icon_custom_emoji_id": "6224284210434154938", "callback_data": "GX_num_req", "style": "success"}],
        [{"text": f"SUPPORT LINK: {sup_status}", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "GX_sup_link", "style": "success" if sup_status == "ON" else "primary"},
         {"text": "Withdraw Methods", "icon_custom_emoji_id": "6224024626905753921", "callback_data": "manage_w_methods", "style": "primary"}],
        [{"text": f"Withdraw Group: {grp_status}", "icon_custom_emoji_id": "6224158062949705345", "callback_data": "GX_w_group", "style": "success"},
         {"text": "FORCE JOIN", "icon_custom_emoji_id": FORCE_JOIN_BUTTON_EMOJI_ID, "callback_data": "manage_fj", "style": "primary"}],
        [
         {"text": "BACK", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
    ]}

def get_withdrawal_methods_text():
    return render_body_text(
        '<tg-emoji emoji-id="6224024626905753921">💳</tg-emoji>'
        'Manage your withdrawal methods below '
        '<tg-emoji emoji-id="6233188575286927353">⬇️</tg-emoji>'
    )


def w_methods_keyboard():
    kb = []
    for idx, m in enumerate(bot_settings["w_methods"]):
        kb.append([{"text": f"Delete: {m}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_wm_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Method", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_wm", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "GX_control", "style": "primary"}])
    return {"inline_keyboard": kb}

def count_configured_auto_api_providers():
    """Count configured STEX, Voltx, Zenex and FastX provider groups once each."""
    provider_key_fields = (
        "stex_keys",
        "voltx_keys",
        "zenex_keys",
        "fastx_keys",
    )
    configured_count = 0
    for field in provider_key_fields:
        keys = bot_settings.get(field, [])
        if isinstance(keys, str):
            keys = [keys]
        elif not isinstance(keys, (list, tuple, set)):
            keys = [keys] if keys else []
        configured = any(
            str(key).strip()
            for key in keys
            if key is not None
        )
        if field == "fastx_keys" and not configured:
            configured = bool(os.getenv("FASTXOTP_API_KEY", "").strip())
        configured_count += int(configured)
    return configured_count


def api_panel_config_text(panel):
    """Render every API provider's details with the same branded layout."""
    panel_name = html.escape(str(panel.get("name", "API Panel")))
    api_url = html.escape(str(panel.get("api_url", "") or ""))
    token = html.escape(str(panel.get("token", "") or ""))
    full_api_url = html.escape(
        str(panel.get("full_api_url", "") or panel.get("api_url", "") or "")
    )
    if str(panel.get("status", "")).upper() == "ON":
        status_text = (
            'Monitoring '
            '<tg-emoji emoji-id="6221992261266187100">🟢</tg-emoji>'
        )
    else:
        status_text = (
            'Stopped '
            '<tg-emoji emoji-id="6224003980997962148">❌</tg-emoji>'
        )
    return (
        '<tg-emoji emoji-id="6199741311310896893">☄️</tg-emoji>'
        f'Configure {panel_name} '
        '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
        '◈━━━━━━━━━━━━━━━━━━━━◈\n'
        'Type<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji> API Panel\n'
        'Status<tg-emoji emoji-id="6221840949568350303">🛜</tg-emoji> '
        f'{status_text}\n'
        'API URL<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji>\n'
        f'{api_url}\n'
        'Token<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>\n'
        f'{token}\n'
        '<tg-emoji emoji-id="6224158062949705345">🔗</tg-emoji>'
        'Full API URL '
        '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>\n'
        '◈━━━━━━━━━━━━━━━━━━◈\n'
        f'{full_api_url} '
        '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
        '◈━━━━━━━━━━━━━━━━━━━━◈'
    )


def typed_panels_list_keyboard(p_type):
    kb = []
    add_cb = "add_api_panel" if p_type == "API Panel" else "add_cpt_panel"
    kb.append([{
        "text": "Add New Provider",
        "icon_custom_emoji_id": "5420323438508155202",
        "callback_data": add_cb,
        "style": "success",
    }])
    for idx, p in enumerate(bot_settings["panels"]):
        if p.get("type", "API Panel") != p_type: continue
        action_text = f"Turn OFF {p['name']}" if p['status'] == 'ON' else f"Turn ON {p['name']}"
        action_icon = "5318840353510408444" if p['status'] == 'ON' else "5192812028632274956"
        icon_id = "5420155432272438703" 
        kb.append([
            {"text": action_text, "icon_custom_emoji_id": action_icon, "callback_data": f"tog_pnl_{idx}", "style": "success" if p['status'] == 'ON' else "primary"},
            {"text": f"{p['name']}", "icon_custom_emoji_id": icon_id, "callback_data": f"conf_pnl_{idx}", "style": "primary"}
        ])
    kb.append([{"text": "Delete Provider", "icon_custom_emoji_id": "6199310839623721543", "callback_data": f"list_del_{'api' if p_type=='API Panel' else 'cpt'}", "style": "danger"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_panels", "style": "primary"}])
    return {"inline_keyboard": kb}

def panel_config_keyboard(idx):
    p = bot_settings["panels"][idx]
    
    kb = []
    action_text = "Turn OFF" if p['status'] == 'ON' else "Turn ON"
    action_icon = "5318840353510408444" if p['status'] == 'ON' else "5192812028632274956"
    kb.append([{"text": action_text, "icon_custom_emoji_id": action_icon, "callback_data": f"tog_pnl_{idx}", "style": "success" if p['status'] == 'ON' else "primary"}])
    
    if p["type"] != "Auto Captcha Panel":
        rec_count_text = "All (Unlimited)" if p.get('records', 0) == 0 else str(p.get('records'))
        kb.append([{"text": "Set API URL", "icon_custom_emoji_id": "5420517437885943844", "callback_data": f"set_p_api_{idx}", "style": "primary"}])
        kb.append([{"text": "Set Token", "icon_custom_emoji_id": "5353022963132174959", "callback_data": f"set_p_tok_{idx}", "style": "primary"}])
        kb.append([{"text": "🌐 Full API (URL+Token)", "icon_custom_emoji_id": "5420517437885943844", "callback_data": f"set_p_fapi_{idx}", "style": "primary"}])
        kb.append([{"text": f"Set Records Count: {rec_count_text}", "icon_custom_emoji_id": "6222073659486381042", "callback_data": f"set_p_rec_{idx}", "style": "primary"}])
        
    kb.append([{"text": "Test Connection", "icon_custom_emoji_id": "6224038684333711964", "callback_data": f"test_p_conn_{idx}", "style": "success"}])
        
    back_data = "manage_api_panels" if p.get("type", "API Panel") == "API Panel" else "manage_cpt_panels"
    kb.append([{"text": "Back to Providers", "icon_custom_emoji_id": "5267490665117275176", "callback_data": back_data, "style": "danger"}])
    return {"inline_keyboard": kb}

def build_traffic_ui(page=0):
    global recent_traffic
    current_time = time.time()
    fresh_events = []
    for event in recent_traffic:
        if not isinstance(event, dict):
            continue
        try:
            event_age = current_time - float(event.get("time", 0))
        except (TypeError, ValueError):
            continue
        if 0 <= event_age <= 600:
            fresh_events.append(event)
    recent_traffic = fresh_events

    traffic_service_key_cache = {}

    def traffic_service_key(value):
        source = str(value or "")
        if source in traffic_service_key_cache:
            return traffic_service_key_cache[source]
        raw = html.unescape(re.sub(r"<[^>]*>", "", source)).strip()
        if not raw:
            traffic_service_key_cache[source] = None
            return None
        canonical = _canonical_traffic_service(raw)
        if canonical:
            traffic_service_key_cache[source] = canonical
            return canonical
        traffic_service_key_cache[source] = None
        return None

    # Only inspect provider service/range caches here. Building the full
    # number-picker catalog also scans every local number batch, which Traffic
    # does not use and can make this screen slow when stock is large.
    stats = {service: {} for service in _ALLOWED_SERVICE_ALIASES}
    with _live_range_cache_lock:
        live_service_sources = [
            tuple(services.items())
            for services in _live_range_cache.values()
            if isinstance(services, dict)
        ]
    configured_service_sources = []
    for provider in ("stex", "voltx", "zenex", "fastx"):
        services = bot_settings.get(f"{provider}_services", {})
        if isinstance(services, dict):
            configured_service_sources.append(tuple(services.items()))

    for service_source in live_service_sources + configured_service_sources:
        for service, countries in service_source:
            if not isinstance(countries, dict):
                continue
            has_usable_range = False
            for country, ranges in countries.items():
                if not str(country or "").strip():
                    continue
                range_values = (
                    ranges if isinstance(ranges, (list, tuple, set))
                    else (ranges,)
                )
                if any(str(range_value or "").strip() for range_value in range_values):
                    has_usable_range = True
                    break
            if has_usable_range:
                service_key = traffic_service_key(service)
                if service_key:
                    stats.setdefault(service_key, {})

    for event in recent_traffic:
        srv = traffic_service_key(event.get("service", ""))
        if srv not in stats:
            continue
        iso = event.get("iso") or "XX"
        flag = event.get("flag") or "🌍"
        if iso not in stats[srv]:
            stats[srv][iso] = {"count": 0, "flag": flag}
        stats[srv][iso]["count"] += 1
        
    kb = []
    srv_totals = [
        (srv, sum(country["count"] for country in countries.values()), countries)
        for srv, countries in stats.items()
    ]
    service_order = {
        service: index for index, service in enumerate(_ALLOWED_SERVICE_ALIASES)
    }
    srv_totals.sort(
        key=lambda item: (
            -item[1],
            service_order.get(item[0], len(service_order)),
            item[0].casefold(),
        )
    )

    traffic_short_name_emoji = '<tg-emoji emoji-id="6219857271678050615">📶</tg-emoji>'
    traffic_percent_separator = '<tg-emoji emoji-id="6222178456688405100">🔹</tg-emoji>'
    traffic_rows = []

    for srv, total, countries in srv_totals:
        if not total:
            continue
        app_full_name, prem_app_html = get_service_info_html(srv)
        c_list = sorted(
            countries.items(),
            key=lambda x: (-x[1]["count"], str(x[0]).upper()),
        )[:7]
        for iso, c_data in c_list:
            prem_flag_html = get_flag_info_html(iso)
            count = c_data["count"]

            if count < 20:
                status_text = "LOW"
                status_emoji = '<tg-emoji emoji-id="5408846744727334338">🔴</tg-emoji>'
            elif count < 30:
                status_text = "MEDIUM"
                status_emoji = '<tg-emoji emoji-id="6219543855029560639">🟡</tg-emoji>'
            else:
                status_text = "HIGH"
                status_emoji = '<tg-emoji emoji-id="6219522483272294334">🟢</tg-emoji>'

            percentage = count * 100 // total if total else 0
            filled_cells = min(4, max(1, percentage * 4 // 100))
            progress_bar = (
                f"<code>[{'█' * filled_cells}"
                f"{'░' * (4 - filled_cells)}]</code>"
            )
            row_text = (
                f"{prem_flag_html} <b>{str(iso).upper()}</b> "
                f"{traffic_short_name_emoji} {progress_bar} "
                f"{percentage}% {traffic_percent_separator} "
                f"{status_text} {status_emoji}\n"
            )
            traffic_rows.append(
                (srv, total, prem_app_html, app_full_name.upper(), row_text)
            )

    rows_per_page = 8
    page_count = max(1, math.ceil(len(traffic_rows) / rows_per_page))
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 0
    page = max(0, min(page, page_count - 1))
    page_rows = traffic_rows[
        page * rows_per_page:(page + 1) * rows_per_page
    ]

    txt = (
        '<tg-emoji emoji-id="6219576393701794683">📡</tg-emoji> '
        '<b>10 Minute LIVE Traffic</b> '
        '<tg-emoji emoji-id="6219661940860396418">🛡️</tg-emoji>\n'
        '━━━━━━━━━━━━━━━━━━\n'
    )
    if not traffic_rows:
        txt += "<i>No traffic activity in the last 10 minutes.</i>\n"
    else:
        previous_service = None
        for srv, total, prem_app_html, app_name, row_text in page_rows:
            if srv != previous_service:
                if previous_service is not None:
                    txt += "━━━━━━━━━━━━━━━━━━\n"
                txt += f"{prem_app_html} {app_name} {total}\n"
                previous_service = srv
            txt += row_text

    service_short_names = {
        "FACEBOOK": "FB",
        "INSTAGRAM": "IG",
        "PAYPAL": "PP",
        "IMO": "IMO",
        "WHATSAPP": "WA",
        "WHATSAPPBUSINESS": "WA",
        "TELEGRAM": "TG",
        "MICROSOFT": "MS",
    }
    service_buttons = []
    for srv, _, countries in srv_totals:
        if not countries:
            continue
        app_full_name, _ = get_service_info_html(srv, srv)
        plain_service_name = html.unescape(
            re.sub(r"<[^>]*>", "", str(app_full_name or srv))
        ).strip()
        service_key = re.sub(r"[^A-Z0-9]", "", plain_service_name.upper())
        short_name = service_short_names.get(service_key)
        if not short_name:
            words = re.findall(r"[A-Z0-9]+", plain_service_name.upper())
            short_name = (
                "".join(word[0] for word in words[:4])
                if len(words) > 1
                else (words[0][:3] if words else str(srv).upper()[:3])
            )
        app_icon_id = get_service_icon_id(srv, srv)
        service_buttons.append({
            "text": short_name,
            "icon_custom_emoji_id": app_icon_id,
            "callback_data": f"exp_rng_{srv}",
            "style": "success",
        })
        if len(service_buttons) == 4:
            kb.append(service_buttons)
            service_buttons = []
    if service_buttons:
        kb.append(service_buttons)
            
    txt = render_body_text(txt)
    if page_count > 1:
        kb.append([
            {
                "text": "‹ Prev",
                "callback_data": f"traffic_page_{max(0, page - 1)}",
                "style": "primary",
            },
            {
                "text": f"{page + 1}/{page_count}",
                "callback_data": f"traffic_page_{page}",
                "style": "primary",
            },
            {
                "text": "Next ›",
                "callback_data": f"traffic_page_{min(page + 1, page_count - 1)}",
                "style": "primary",
            },
        ])
    kb.append([{"text": "Refresh", "icon_custom_emoji_id": "6224477342228565523", "callback_data": f"refresh_traffic_{page}", "style": "primary"}])
    kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
    
    traffic_markup = {"inline_keyboard": kb}
    traffic_target_width = _otp_forward_keyboard_width(traffic_markup) + 1
    txt = _pad_otp_forward_bubble_width(
        txt.rstrip("\n"),
        target_width=traffic_target_width,
    )
    visible_text = re.sub(
        r"<tg-emoji\b[^>]*>(.*?)</tg-emoji>",
        r"\1",
        txt,
        flags=re.IGNORECASE | re.DOTALL,
    )
    visible_text = html.unescape(re.sub(r"<[^>]+>", "", visible_text))
    measured_width = max(
        (_otp_forward_display_width(line) for line in visible_text.splitlines()),
        default=0,
    )
    if measured_width < traffic_target_width:
        txt += "\u2007" * (traffic_target_width - measured_width)
    return txt, traffic_markup


_ALLOWED_SERVICE_ALIASES = {
    "FACEBOOK": {"FACEBOOK", "FB", "META"},
    "INSTAGRAM": {"INSTAGRAM", "INSTA", "IG"},
    "IMO": {"IMO"},
    "TELEGRAM": {"TELEGRAM", "TG"},
    "WHATSAPP": {"WHATSAPP", "WHATSAPPBUSINESS", "WHATSAPPBIZ"},
    "TIKTOK": {"TIKTOK", "TT"},
}
_ALLOWED_SERVICE_LOOKUP = {
    alias: canonical
    for canonical, aliases in _ALLOWED_SERVICE_ALIASES.items()
    for alias in aliases
}


def _canonical_allowed_service(service):
    """Return one of the six customer-facing services, or None."""
    _is_local_stock, service = _split_service_selection(service)
    normalized = re.sub(r"[^A-Z0-9]", "", str(service or "").upper())
    return _ALLOWED_SERVICE_LOOKUP.get(normalized)


_LOCAL_STOCK_SERVICE_PREFIX = "L:"


def _split_service_selection(service):
    """Separate the local-upload menu variant from its canonical service."""
    service = str(service or "")
    if service.startswith(_LOCAL_STOCK_SERVICE_PREFIX):
        return True, service[len(_LOCAL_STOCK_SERVICE_PREFIX):]
    return False, service


def _local_stock_service_key(service):
    canonical = _canonical_allowed_service(service) or str(service or "").upper()
    return f"{_LOCAL_STOCK_SERVICE_PREFIX}{canonical}"


def _canonical_traffic_service(service):
    """Normalize provider labels such as 'Facebook SMS' to a displayed service."""
    raw = html.unescape(re.sub(r"<[^>]*>", "", str(service or ""))).strip()
    canonical = _canonical_allowed_service(raw)
    if canonical:
        return canonical
    normalized = re.sub(r"[^A-Z0-9]", "", raw.upper())
    for alias, service_name in sorted(
        _ALLOWED_SERVICE_LOOKUP.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if normalized.startswith(alias):
            return service_name
    return None


def _traffic_service_matches(value, target):
    """Compare API/provider labels against the customer-facing service name."""
    target_service = _canonical_traffic_service(target) or _canonical_allowed_service(target)
    value_service = _canonical_traffic_service(value) or _canonical_allowed_service(value)
    if target_service and value_service:
        return target_service == value_service
    return _traffic_name_key(value) == _traffic_name_key(target)


def _has_local_stock_for_service(service):
    canonical = _canonical_allowed_service(service) or re.sub(
        r"\s+", " ", str(service or "")
    ).strip().upper()
    if not canonical:
        return False
    with number_allocation_lock:
        return any(
            _traffic_service_matches(batch.get("service", ""), canonical)
            and any(
                isinstance(item, dict)
                and not item.get("to_remove")
                and _canonical_number(item.get("num"))
                and _canonical_number(item.get("num")) not in claimed_numbers
                for item in batch.get("numbers", [])
            )
            for batch in number_batches.values()
            if isinstance(batch, dict)
        )


def _service_selection_label(service):
    """Return the service's display name without source-based numbering."""
    _is_local, base_service = _split_service_selection(service)
    canonical = _canonical_allowed_service(base_service) or base_service
    service_name, _emoji = get_service_info_html(canonical, canonical)
    if not re.search(r"[A-Z0-9]", str(service_name or ""), re.IGNORECASE):
        service_name = str(canonical or base_service or "").strip()
    return service_name


def _clean_range_prefix(value):
    """Normalize provider range IDs and masked number prefixes for comparisons."""
    return re.sub(r"\D", "", str(value or ""))


def _range_is_allowed(query, allowed_ranges):
    query_prefix = _clean_range_prefix(query)
    if not query_prefix:
        return False
    for configured_range in allowed_ranges or []:
        allowed_prefix = _clean_range_prefix(configured_range)
        if allowed_prefix and (
            query_prefix.startswith(allowed_prefix)
            or allowed_prefix.startswith(query_prefix)
        ):
            return True
    return False


def _live_ranges_for_service_country(service, country=None, provider=None):
    """Return cached (range, provider) pairs for a service and optional country."""
    with _live_range_cache_lock:
        cache = copy.deepcopy(_live_range_cache)
    result = []
    wanted_country = str(country or "").strip().casefold()
    for provider_name, services in cache.items():
        if provider and provider_name != provider:
            continue
        if not isinstance(services, dict):
            continue
        for cached_service, countries in services.items():
            if not _traffic_service_matches(cached_service, service):
                continue
            if not isinstance(countries, dict):
                continue
            for cached_country, ranges in countries.items():
                if wanted_country and str(cached_country).strip().casefold() != wanted_country:
                    continue
                for range_value in ranges if isinstance(ranges, list) else []:
                    if _clean_range_prefix(range_value):
                        result.append((str(range_value), provider_name))
    return result


def _live_range_services():
    with _live_range_cache_lock:
        cache = copy.deepcopy(_live_range_cache)
    return {
        service
        for services in cache.values()
        if isinstance(services, dict)
        for service in services
    }


def _live_range_countries(service):
    with _live_range_cache_lock:
        cache = copy.deepcopy(_live_range_cache)
    countries = set()
    for services in cache.values():
        if not isinstance(services, dict):
            continue
        for cached_service, service_countries in services.items():
            if _traffic_service_matches(cached_service, service) and isinstance(service_countries, dict):
                countries.update(service_countries.keys())
    return countries


def _live_service_range_is_allowed(query, service, provider):
    return any(
        _range_is_allowed(query, [range_value])
        for range_value, _provider_name in _live_ranges_for_service_country(
            service, provider=provider
        )
    )


def _parse_live_range_payload(provider, payload):
    """Adapt supported liveaccess payloads into service -> country -> ranges."""
    if isinstance(payload, dict):
        data = payload.get("data")
        if provider == "zenex":
            if isinstance(data, dict) and "active_ranges" in data:
                rows = data.get("active_ranges", [])
            elif "active_ranges" in payload:
                rows = payload.get("active_ranges", [])
            else:
                return None
        else:
            if isinstance(data, dict) and "services" in data:
                rows = data.get("services", [])
            elif "services" in payload:
                rows = payload.get("services", [])
            else:
                return None
    elif isinstance(payload, list):
        rows = payload
    else:
        return None

    if not isinstance(rows, list):
        return None
    parsed = {}

    def add_range(service_value, range_value):
        service_name = _canonical_traffic_service(service_value)
        range_text = str(range_value or "").strip()
        digits = _clean_range_prefix(range_text)
        if not service_name or not (3 <= len(digits) <= 18):
            return
        try:
            _flag, iso = get_flag_and_code(digits)
            country_name = str(get_flag_info_html(iso, return_full_name=True) or "").strip()
        except Exception:
            return
        if not country_name:
            return
        country_name = country_name.title()
        countries = parsed.setdefault(service_name, {})
        ranges = countries.setdefault(country_name, [])
        if range_text not in ranges:
            ranges.append(range_text)

    for row in rows:
        if not isinstance(row, dict):
            continue
        service_name = row.get("sid") or row.get("service") or row.get("app") or row.get("application")
        ranges = row.get("ranges")
        if isinstance(ranges, list):
            for range_item in ranges:
                if isinstance(range_item, dict):
                    range_item = range_item.get("range") or range_item.get("rid") or range_item.get("number")
                add_range(service_name, range_item)
        else:
            add_range(service_name, row.get("range") or row.get("rid") or row.get("number"))
    return parsed


def _fetch_live_ranges_for_provider(provider):
    keys_by_provider = {
        "stex": ("stex_keys", STEX_BASE_URL, "mauthapi", "/liveaccess"),
        "voltx": ("voltx_keys", VOLTX_BASE_URL, "mauthapi", "/liveaccess"),
        "zenex": ("zenex_keys", ZENEX_BASE_URL, "mapikey", "/v1/active-ranges"),
        "fastx": ("fastx_keys", FASTX_BASE_URL, "X-API-Key", "/api/liveaccess"),
    }
    config = keys_by_provider.get(provider)
    if not config:
        return None
    key_name, base_url, header_name, endpoint = config
    keys = bot_settings.get(key_name, [])
    if isinstance(keys, str):
        keys = [keys]
    api_key = next((str(key).strip() for key in keys or [] if str(key).strip()), "")
    if provider == "fastx" and not api_key:
        api_key = os.getenv("FASTXOTP_API_KEY", "").strip()
    if not api_key:
        return None
    if provider == "voltx" and not bot_settings.get("voltx_on", True):
        return None

    try:
        response = requests.get(
            base_url.rstrip("/") + endpoint,
            headers={header_name: api_key, "User-Agent": "GX-Number-Bot/1.0"},
            timeout=(1.5, 3.5),
        )
        response.raise_for_status()
        payload = response.json()
        return _parse_live_range_payload(provider, payload)
    except Exception:
        return None


def _sync_fastx_auto_ranges(ranges=None):
    """Copy new FastX live service ranges into saved service/search settings."""
    if not bot_settings.get("fastx_auto", False):
        return False
    if ranges is None:
        with _live_range_cache_lock:
            ranges = copy.deepcopy(_live_range_cache.get("fastx", {}))
    if not isinstance(ranges, dict):
        return False

    services = bot_settings.setdefault("fastx_services", {})
    if not isinstance(services, dict):
        services = {}
        bot_settings["fastx_services"] = services
    search_countries = bot_settings.setdefault("fastx_search_countries", [])
    if not isinstance(search_countries, list):
        search_countries = []
        bot_settings["fastx_search_countries"] = search_countries

    changed = False
    for service_name, countries in ranges.items():
        service_name = _canonical_traffic_service(service_name) or str(service_name).strip().upper()
        if not service_name or not isinstance(countries, dict):
            continue
        configured_countries = services.setdefault(service_name, {})
        if not isinstance(configured_countries, dict):
            configured_countries = {}
            services[service_name] = configured_countries
            changed = True
        for country_name, range_values in countries.items():
            if not isinstance(range_values, (list, tuple, set)):
                range_values = [range_values]
            configured_ranges = configured_countries.setdefault(str(country_name), [])
            if not isinstance(configured_ranges, list):
                configured_ranges = [configured_ranges]
                configured_countries[str(country_name)] = configured_ranges
                changed = True
            for range_value in range_values:
                range_text = str(range_value or "").strip()
                prefix = _clean_range_prefix(range_text)
                if not prefix:
                    continue
                if range_text not in configured_ranges:
                    configured_ranges.append(range_text)
                    changed = True
                if prefix not in search_countries:
                    search_countries.append(prefix)
                    changed = True
    if changed:
        save_db()
    return changed


def _refresh_fastx_live_ranges_now():
    """Refresh FastX on demand after Auto Range is enabled."""
    global _live_range_cache_updated_at
    ranges = _fetch_live_ranges_for_provider("fastx")
    if ranges is None:
        return False
    with _live_range_cache_lock:
        _live_range_cache["fastx"] = ranges
        _live_range_cache_updated_at = time.time()
    _sync_fastx_auto_ranges(ranges)
    return True


def live_range_refresh_thread():
    """Refresh live provider ranges in the background without slowing button clicks."""
    global _live_range_cache_updated_at
    while True:
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    provider: executor.submit(_fetch_live_ranges_for_provider, provider)
                    for provider in ("stex", "voltx", "zenex", "fastx")
                }
                refreshed = {
                    provider: future.result()
                    for provider, future in futures.items()
                }
            with _live_range_cache_lock:
                for provider, ranges in refreshed.items():
                    # Preserve the last good cache if the provider is
                    # unreachable; a valid empty response may clear its cache.
                    if ranges is not None:
                        _live_range_cache[provider] = ranges
                _live_range_cache_updated_at = time.time()
            if refreshed.get("fastx") is not None:
                _sync_fastx_auto_ranges(refreshed["fastx"])
        except Exception:
            pass
        time.sleep(200)


def _refresh_live_range_cache_now():
    """Refresh all provider ranges concurrently for the first picker open."""
    global _live_range_cache_updated_at
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            provider: executor.submit(_fetch_live_ranges_for_provider, provider)
            for provider in ("stex", "voltx", "zenex", "fastx")
        }
        refreshed = {}
        for provider, future in futures.items():
            try:
                refreshed[provider] = future.result()
            except Exception:
                refreshed[provider] = None
    with _live_range_cache_lock:
        for provider, ranges in refreshed.items():
            if ranges is not None:
                _live_range_cache[provider] = ranges
        _live_range_cache_updated_at = time.time()
    if refreshed.get("fastx") is not None:
        _sync_fastx_auto_ranges(refreshed["fastx"])


def _picker_country_label(country):
    raw = str(country or "").strip()
    if not raw:
        return ""
    for flag_data in bot_settings.get("premium_flags", {}).values():
        iso = str(flag_data.get("iso", "")).strip()
        name = str(flag_data.get("name", "")).strip()
        if raw.casefold() == iso.casefold() or raw.casefold() == name.casefold():
            return name.title() or raw
    try:
        full_name = get_flag_info_html(raw, return_full_name=True)
        if full_name and full_name != raw:
            return str(full_name).title()
    except Exception:
        pass
    return raw.title()


def _format_number_picker_otp_rate(rate):
    try:
        rate_number = float(rate)
        if math.isfinite(rate_number):
            return f"{rate_number:g}"
    except (TypeError, ValueError):
        pass
    try:
        default_rate = float(bot_settings.get("otp_reward", 0.0))
        if math.isfinite(default_rate):
            return f"{default_rate:g}"
    except (TypeError, ValueError):
        pass
    return "0"


def _managed_panel_country_otp_rate(service, country):
    """Return the first configured managed-panel service/country override."""
    canonical_service = _canonical_allowed_service(service) or service
    country_label = _picker_country_label(country).casefold()
    country_iso, _country_name = _resolve_panel_rate_country(country)
    country_keys = {str(country or "").strip().upper()}
    if country_iso:
        country_keys.add(str(country_iso).strip().upper())

    for panel in bot_settings.get("panels", []):
        if not isinstance(panel, dict):
            continue
        rates = panel.get("otp_rates", {})
        if not isinstance(rates, dict):
            continue
        for configured_service, countries in rates.items():
            if not isinstance(countries, dict) or not _traffic_service_matches(
                configured_service, canonical_service
            ):
                continue
            for configured_country, rate in countries.items():
                same_country = (
                    str(configured_country).strip().upper() in country_keys
                    or _panel_rate_country_label(configured_country).casefold()
                    == country_label
                )
                if not same_country:
                    continue
                try:
                    rate_number = float(rate)
                    if math.isfinite(rate_number) and rate_number >= 0:
                        return rate_number
                except (TypeError, ValueError):
                    continue
    return None


def _number_picker_country_otp_rate(selection_service, country):
    """Prefer service/country panel override, then upload and global rates."""
    is_local_stock, base_service = _split_service_selection(selection_service)
    default_rate = bot_settings.get("otp_reward", 0.0)
    canonical_service = _canonical_allowed_service(base_service) or base_service
    panel_rate = _managed_panel_country_otp_rate(canonical_service, country)
    if panel_rate is not None:
        return panel_rate

    if is_local_stock:
        country_label = _picker_country_label(country).casefold()
        with number_allocation_lock:
            for batch in number_batches.values():
                if not isinstance(batch, dict):
                    continue
                if not _traffic_service_matches(
                    batch.get("service", ""), canonical_service
                ):
                    continue
                if _picker_country_label(
                    batch.get("country", "")
                ).casefold() != country_label:
                    continue
                has_available_number = any(
                    isinstance(item, dict)
                    and not item.get("to_remove")
                    and _canonical_number(item.get("num"))
                    and _canonical_number(item.get("num")) not in claimed_numbers
                    for item in batch.get("numbers", [])
                )
                if has_available_number and "rate" in batch:
                    try:
                        batch_rate = float(batch["rate"])
                        if math.isfinite(batch_rate):
                            return batch_rate
                    except (TypeError, ValueError):
                        pass

    return default_rate


def _picker_country_emoji(country):
    target = str(country or "").strip().casefold()
    for flag_data in bot_settings.get("premium_flags", {}).values():
        iso = str(flag_data.get("iso", "")).strip().casefold()
        name = str(flag_data.get("name", "")).strip().casefold()
        if target in (iso, name):
            emoji_id = flag_data.get("id")
            char = flag_data.get("char", "🌍")
            return emoji_id, (
                f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'
                if emoji_id else char
            )
    return "5780471598922337683", "🌍"


def _build_number_picker_catalog():
    """Build app/country/range options from cached APIs and local stock."""
    with _live_range_cache_lock:
        live_cache = copy.deepcopy(_live_range_cache)
    catalog = {}

    def add_country(service_value, country_value):
        is_local_stock, base_service = _split_service_selection(service_value)
        service = _canonical_allowed_service(base_service)
        if not service:
            return None
        country = _picker_country_label(country_value)
        # A masked provider label such as "******" is not a usable service name.
        if not service or not re.search(r"[A-Z0-9]", service) or not country:
            return None
        catalog_service = (
            _local_stock_service_key(service) if is_local_stock else service
        )
        return catalog.setdefault(catalog_service, {}).setdefault(
            country, {"ranges": [], "local_countries": []}
        )

    def add_range(service_value, country_value, range_value, provider):
        range_text = str(range_value or "").strip()
        if not range_text:
            return
        entry = add_country(service_value, country_value)
        if entry is None:
            return
        item = {"range": range_text, "source": provider}
        if item not in entry["ranges"]:
            entry["ranges"].append(item)

    for provider, services in live_cache.items():
        if not isinstance(services, dict):
            continue
        for service, countries in services.items():
            if not isinstance(countries, dict):
                continue
            for country, ranges in countries.items():
                for range_value in ranges if isinstance(ranges, list) else []:
                    add_range(service, country, range_value, provider)

    for provider in ("stex", "voltx", "zenex", "fastx"):
        for service, countries in bot_settings.get(f"{provider}_services", {}).items():
            if not isinstance(countries, dict):
                continue
            for country, ranges in countries.items():
                if not isinstance(ranges, (list, tuple, set)):
                    ranges = [ranges]
                for range_value in ranges:
                    add_range(service, country, range_value, provider)

    with number_allocation_lock:
        for batch in number_batches.values():
            if not isinstance(batch, dict):
                continue
            service = batch.get("service", "")
            country = batch.get("country", "")
            numbers = batch.get("numbers", [])
            if not isinstance(numbers, list):
                continue
            has_available = any(
                isinstance(item, dict)
                and _canonical_number(item.get("num"))
                and not item.get("to_remove")
                and _canonical_number(item.get("num")) not in claimed_numbers
                for item in numbers
            )
            if not has_available:
                continue
            entry = add_country(_local_stock_service_key(service), country)
            if entry is not None and country not in entry["local_countries"]:
                entry["local_countries"].append(country)

    return catalog


def _save_number_picker_session(chat_id, catalog):
    service_range_counts = {}
    for name, countries in catalog.items():
        _is_local_stock, base_service = _split_service_selection(name)
        canonical = _canonical_allowed_service(base_service) or base_service
        service_range_counts[canonical] = service_range_counts.get(canonical, 0) + sum(
            len(country_data.get("ranges", []))
            for country_data in countries.values()
        )
    app_names = sorted(
        catalog,
        key=lambda name: (
            -service_range_counts.get(
                _canonical_allowed_service(_split_service_selection(name)[1])
                or _split_service_selection(name)[1],
                0,
            ),
            str(
                _canonical_allowed_service(_split_service_selection(name)[1])
                or _split_service_selection(name)[1]
            ).lower(),
            _split_service_selection(name)[0],
        )
    )
    session = {
        "catalog": catalog,
        "apps": app_names,
        "local_service_buttons": [
            {
                "text": _service_selection_label(service),
                "icon_custom_emoji_id": get_service_icon_id(
                    _split_service_selection(service)[1],
                    _split_service_selection(service)[1],
                ),
                "callback_data": f"np_app_{index}",
                "style": "primary",
            }
            for index, service in enumerate(app_names, 1)
            if _split_service_selection(service)[0]
        ],
        "country_options": {},
        "selected_app": None,
        "selected_country_id": None,
        "created_at": time.time(),
    }
    with _number_picker_sessions_lock:
        _number_picker_sessions[chat_id] = session
    return session


def _split_number_picker_services(services):
    """Keep provider-backed and uploaded local-stock services in separate groups."""
    provider_services = []
    local_services = []
    for index, service in enumerate(services, 1):
        is_local, _base_service = _split_service_selection(service)
        target = local_services if is_local else provider_services
        target.append((index, service))
    return provider_services, local_services


def _render_number_picker_apps(chat_id, message_id, session):
    buttons = []
    row = []
    buttons.append([{
        "text": "OTP WORK SERVICE",
        "icon_custom_emoji_id": OTP_WORK_SERVICE_EMOJI_ID,
        "callback_data": "np_local_services",
        "style": "primary",
    }])
    shown_provider_services = 0
    for index, service in enumerate(session.get("apps", []), 1):
        is_local_stock, base_service = _split_service_selection(service)
        if is_local_stock:
            continue
        if shown_provider_services >= 6:
            break
        service_name = _service_selection_label(service)
        row.append({
            "text": service_name,
            "icon_custom_emoji_id": get_service_icon_id(base_service, base_service),
            "callback_data": f"np_app_{index}",
            "style": "primary",
        })
        shown_provider_services += 1
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([{
        "text": "Close",
        "icon_custom_emoji_id": "5420130255174145507",
        "callback_data": "close_msg",
        "style": "danger",
    }])
    text = (
        f"{PEM['phone']} <b>SELECT APP TO GET NUMBER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    markup = {"inline_keyboard": buttons}
    if message_id:
        return edit_message(chat_id, message_id, text, reply_markup=markup)
    return send_message(chat_id, text, reply_markup=markup)


def _render_number_picker_local_services(chat_id, message_id, session):
    """Show up to six allowed uploaded/local services."""
    session["view"] = "local"
    local_service_buttons = session.get("local_service_buttons")
    if local_service_buttons is None:
        _provider_services, local_services = _split_number_picker_services(
            session.get("apps", [])
        )
        local_service_buttons = []
        for index, service in local_services:
            _is_local_stock, base_service = _split_service_selection(service)
            local_service_buttons.append({
                "text": _service_selection_label(service),
                "icon_custom_emoji_id": get_service_icon_id(base_service, base_service),
                "callback_data": f"np_app_{index}",
                "style": "primary",
            })
    local_service_buttons = local_service_buttons[:6]
    buttons = [
        local_service_buttons[offset:offset + 2]
        for offset in range(0, len(local_service_buttons), 2)
    ]

    if not buttons:
        return edit_message(
            chat_id,
            message_id,
            "❌ No local stock is available right now.",
            reply_markup={"inline_keyboard": [[
                {
                    "text": "Back",
                    "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
                    "callback_data": "np_back_apps",
                    "style": "primary",
                },
                {
                    "text": "Close",
                    "icon_custom_emoji_id": CROSS_CANCEL_EMOJI_ID,
                    "callback_data": "close_msg",
                    "style": "danger",
                },
            ]]},
        )

    buttons.append([{
        "text": "Back",
        "icon_custom_emoji_id": "5267490665117275176",
        "callback_data": "np_back_apps",
        "style": "danger",
    }])
    text = "🧩 <b>OTP WORK SERVICE</b>\nSelect a local service:"
    return edit_message(
        chat_id,
        message_id,
        text,
        reply_markup={"inline_keyboard": buttons},
    )


def _refresh_number_picker_after_cache_miss(chat_id):
    """Refresh provider ranges off the button handler, then update loading menus."""
    try:
        _refresh_live_range_cache_now()
        catalog = _build_number_picker_catalog()
    except Exception:
        catalog = {}

    with _number_picker_sessions_lock:
        message_ids = list(dict.fromkeys(
            _number_picker_refreshing.pop(chat_id, [])
        ))

    if not message_ids:
        return

    if not catalog:
        session = _save_number_picker_session(chat_id, {})
        for message_id in message_ids:
            try:
                _render_number_picker_apps(chat_id, message_id, session)
            except Exception:
                pass
        return

    session = _save_number_picker_session(chat_id, catalog)
    for message_id in message_ids:
        try:
            _render_number_picker_apps(chat_id, message_id, session)
        except Exception:
            pass


def show_number_app_selection(chat_id, message_id=None):
    """Show the second bot's app picker, using cached ranges for fast opens."""
    catalog = _build_number_picker_catalog()
    with _live_range_cache_lock:
        cache_age = time.time() - _live_range_cache_updated_at

    status_message_id = message_id
    if not catalog:
        status_text = loading_html("<b>Loading ranges...</b>")
        if status_message_id:
            edit_message(chat_id, status_message_id, status_text)
        else:
            response = send_message(chat_id, status_text)
            status_message_id = (
                response.get("result", {}).get("message_id")
                if isinstance(response, dict) else None
            )
        with _number_picker_sessions_lock:
            waiting_messages = _number_picker_refreshing.get(chat_id)
            if waiting_messages is None:
                _number_picker_refreshing[chat_id] = [status_message_id]
                start_refresh = True
            else:
                waiting_messages.append(status_message_id)
                start_refresh = False
        if start_refresh:
            threading.Thread(
                target=_refresh_number_picker_after_cache_miss,
                args=(chat_id,),
                daemon=True,
            ).start()
        return

    session = _save_number_picker_session(chat_id, catalog)
    _render_number_picker_apps(chat_id, status_message_id, session)
    if cache_age >= 300:
        threading.Thread(
            target=_refresh_live_range_cache_now,
            daemon=True,
        ).start()


def _show_number_picker_countries(chat_id, message_id, app_index):
    with _number_picker_sessions_lock:
        session = _number_picker_sessions.get(chat_id)
    try:
        index = int(app_index) - 1
        service = session["apps"][index] if session else None
    except (ValueError, IndexError, TypeError):
        service = None
    if not service:
        edit_message(chat_id, message_id, "⚠️ Session expired. Please tap GET NUMBER again.")
        return

    country_map = session["catalog"].get(service, {})
    # Preserve the provider's cached order like the second file's sel_app
    # handler. Traffic-ranking every country scans the full recent-traffic
    # history and can make a simple app-button click noticeably slow.
    countries = list(country_map.keys())
    option_ids = {}
    buttons = []
    row = []
    for option_id, country in enumerate(countries, 1):
        emoji_id, _emoji = _picker_country_emoji(country)
        otp_rate = _format_number_picker_otp_rate(
            _number_picker_country_otp_rate(service, country)
        )
        option_ids[str(option_id)] = {
            "app_index": int(app_index),
            "service": service,
            "country": country,
            "entry": country_map[country],
        }
        row.append({
            "text": f"{country} /{otp_rate} TK",
            "icon_custom_emoji_id": emoji_id,
            "callback_data": f"np_cty_{option_id}",
            "style": "danger",
        })
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{
        "text": "« Back",
        "icon_custom_emoji_id": "5267490665117275176",
        "callback_data": "np_back_apps",
        "style": "primary",
    }])
    with _number_picker_sessions_lock:
        session["selected_app"] = int(app_index)
        session["country_options"] = option_ids
        session["selected_country_id"] = None
    service_name = _service_selection_label(service)
    text = (
        '<tg-emoji emoji-id="6224281577619201977">📌</tg-emoji> '
        f'<b>Select Country for {service_name}:</b>'
    )
    edit_message(chat_id, message_id, text, reply_markup={"inline_keyboard": buttons})


def _process_number_picker_country(call, country_id):
    chat_id = call["message"]["chat"]["id"]
    message_id = call["message"]["message_id"]
    with _number_picker_sessions_lock:
        session = _number_picker_sessions.get(chat_id)
        option = (
            session.get("country_options", {}).get(str(country_id))
            if session else None
        )
        if option:
            session["selected_country_id"] = str(country_id)

    if not option:
        answer_callback(call.get("id"), "⚠️ Session expired. Tap GET NUMBER again.", show_alert=True)
        return

    cooldown = float(bot_settings.get("cooldown", 0) or 0)
    now = time.time()
    wait_left = cooldown - (now - user_cooldowns.get(chat_id, 0))
    if wait_left > 0:
        answer_callback(
            call.get("id"),
            f"⌛ Please wait {max(1, int(wait_left + 0.99))}s.",
            show_alert=True,
        )
        return

    user_cooldowns[chat_id] = now
    selection_service = option["service"]
    _is_local_stock, service = _split_service_selection(selection_service)
    service = _canonical_allowed_service(service) or service
    country = option["country"]
    entry = option["entry"]
    app_index = option["app_index"]
    # Clear Telegram's button spinner before the message edit or stock lookup.
    answer_callback(call.get("id"))
    loading_text = (
        f'<tg-emoji emoji-id="{COUNTRY_LOADING_EMOJI_ID}">⏳</tg-emoji> '
        "<b>Getting Number</b>"
    )
    loading_started_at = time.monotonic()
    loading_result = edit_message(chat_id, message_id, loading_text)
    if not loading_result or not loading_result.get("ok"):
        edit_message(chat_id, message_id, loading_html("<b>Getting Number</b>"))
    expire_previous_number(
        chat_id,
        background=True,
        skip_message_id=message_id,
    )

    count = requested_number_count()
    fetched_nums = []
    number_contexts = {}
    for local_country in entry.get("local_countries", []):
        remaining = count - len(fetched_nums)
        if remaining <= 0:
            break
        fetched_nums.extend(_reserve_local_numbers(
            "",
            chat_id,
            remaining,
            service=service,
            country=local_country,
            persist=False,
        ))

    candidates = entry.get("ranges", [])
    if len(fetched_nums) < count and candidates:
        selected = random.choice(candidates)
        extra, _source = fetch_numbers_fast(
            selected["range"],
            chat_id,
            count - len(fetched_nums),
            source_hint=selected["source"],
            service=service,
            country=country,
            use_local=False,
            persist=False,
        )
        fetched_nums.extend(extra)
        for fetched_number in extra:
            number_contexts[_canonical_number(fetched_number)] = {
                "range": _clean_range_prefix(selected.get("range")),
                "provider": selected.get("source", "auto"),
                "service": service,
            }

    _finish_existing_fetching_animation(chat_id, message_id, loading_started_at)
    if not fetched_nums:
        edit_message(chat_id, message_id, "❌ Number out of stock! Please try again.")
        return

    first_number = str(fetched_nums[0])
    _flag, country_iso, _flag_id = get_flag_info_from_num(first_number)
    assigned_country = get_flag_info_html(country_iso, return_full_name=True) or country
    country_emoji = get_flag_info_html(country_iso) or "🌍"
    allocated_check = (
        f'<tg-emoji emoji-id="{ALLOCATED_CHECK_EMOJI_ID}">✅</tg-emoji>'
    )
    assign_text = (
        f"{country_emoji} <b>{assigned_country} Allocated</b> {allocated_check}\n"
        f"{'━' * 27}\n"
        '<tg-emoji emoji-id="6224205341949698044">⏳</tg-emoji> <b>Waiting for OTP.......</b>'
    )

    keyboard = []
    for number in fetched_nums:
        display_number = f"+{_canonical_number(number)}"
        _char, _iso, flag_emoji_id = get_flag_info_from_num(str(number))
        button_width = 24
        padding = max(0, button_width - len(display_number))
        # The flag/copy indicators take space on the left of the label.
        # Offset the padded number slightly left so the digits themselves
        # sit centered in the full-width number button.
        left_spaces = max(0, (padding // 2) - min(3, padding // 2))
        left_padding = "\u00A0" * left_spaces
        right_padding = "\u00A0" * (padding - left_spaces)
        keyboard.append([{
            "text": f"{left_padding}{display_number}{right_padding}",
            "icon_custom_emoji_id": flag_emoji_id or "5780471598922337683",
            "copy_text": {"text": display_number},
            "style": "success",
        }])
    keyboard.append([
        {
            "text": "Country",
            "icon_custom_emoji_id": LANGUAGE_EMOJI_ID,
            "callback_data": "np_back_country",
            "style": "primary",
        },
        {
            "text": "Change Number",
            "icon_custom_emoji_id": "5267295703666824255",
            "callback_data": "np_repeat",
            "style": "danger",
        },
    ])
    keyboard.append([
        {
            "text": "OTP Group",
            "icon_custom_emoji_id": OTP_GROUP_EMOJI_ID,
            "url": bot_settings.get("otp_link", "https://t.me/OTP_RCV_GRP"),
            "style": "primary",
        },
    ])
    edit_message(
        chat_id,
        message_id,
        assign_text,
        reply_markup={"inline_keyboard": keyboard},
    )
    user_active_sessions[chat_id] = {
        "msg_id": message_id,
        "nums": fetched_nums,
        "number_contexts": number_contexts,
    }
    schedule_provider_state_save()
    with _number_picker_sessions_lock:
        current = _number_picker_sessions.get(chat_id)
        if current:
            current["selected_app"] = app_index
            current["selected_country_id"] = str(country_id)


def _service_range_is_allowed(query, service, service_ranges):
    if not service or not isinstance(service_ranges, dict):
        return False
    for configured_service, countries in service_ranges.items():
        if not _traffic_service_matches(configured_service, service):
            continue
        if not isinstance(countries, dict):
            continue
        for ranges in countries.values():
            if not isinstance(ranges, (list, tuple, set)):
                ranges = [ranges]
            if _range_is_allowed(query, ranges):
                return True
    return False


def _country_matches_iso(country_name, iso):
    country = str(country_name or "").strip().casefold()
    iso = str(iso or "").strip().upper()
    if not country or not iso:
        return False
    if country == iso.casefold():
        return True
    for flag_key, flag_data in bot_settings.get("premium_flags", {}).items():
        if str(flag_data.get("iso", "")).upper() == iso:
            return country == str(flag_data.get("name", "")).strip().casefold()
    try:
        return country == str(get_flag_info_html(iso, return_full_name=True) or "").strip().casefold()
    except Exception:
        return False


# ==========================================
# OPTIMIZED NUMBER FETCHING FUNCTIONS
# ==========================================

def requested_number_count():
    """Return a safe, bounded number count from the admin setting."""
    try:
        # The admin value is the hard upper limit for one request.  Keep a
        # generous safety ceiling to prevent an accidental huge API fan-out,
        # while never returning more than this configured value.
        return max(1, min(50, int(bot_settings.get("num_req", 1))))
    except (TypeError, ValueError):
        return 1


def fetch_stex_number(api_key, query):
    try:
        headers = {"mauthapi": api_key}
        rid = str(query).strip().replace("+", "")
        res = _provider_http_session().post(f"{STEX_BASE_URL}/getnum", json={"rid": rid}, headers=headers, timeout=(0.8, 2.2))
        res.raise_for_status()
        data = res.json()
        if data.get("meta", {}).get("code") == 200 and data.get("data"):
            num_str = str(data["data"].get("no_plus_number", "")).replace("+", "")
            if not num_str:
                num_str = str(data["data"].get("national_number", "")).replace("+", "")
            if num_str:
                return num_str
    except:
        pass
    return None

def fetch_voltx_number(api_key, query):
    try:
        headers = {"mauthapi": api_key}
        rid = str(query).strip().replace("+", "")
        res = _provider_http_session().post(f"{VOLTX_BASE_URL}/getnum", json={"rid": rid}, headers=headers, timeout=(0.8, 2.2))
        res.raise_for_status()
        data = res.json()
        if data.get("meta", {}).get("code") == 200 and data.get("data"):
            num_str = str(data["data"].get("no_plus_number", "")).replace("+", "")
            if not num_str:
                num_str = str(data["data"].get("national_number", "")).replace("+", "")
            if num_str:
                return num_str
    except:
        pass
    return None

def fetch_zenex_number(api_key, query):
    try:
        headers = {"mapikey": api_key}
        res = _provider_http_session().post(f"{ZENEX_BASE_URL}/v1/getnum", json={"range": query, "is_national": False, "remove_plus": False}, headers=headers, timeout=(0.8, 2.2))
        res.raise_for_status()
        data = res.json()
        if data.get("meta", {}).get("code") == 200 and data.get("data"):
            num_str = str(data["data"].get("full_number", "")).replace("+", "")
            if not num_str:
                num_str = str(data["data"].get("number", "")).replace("+", "")
            if num_str:
                return num_str
    except:
        pass
    return None

def fetch_fastx_number(api_key, query):
    try:
        headers = {"X-API-Key": api_key}
        payload = {"range": str(query).strip().replace("+", ""), "is_national": False}
        res = _provider_http_session().post(
            f"{FASTX_BASE_URL}/api/getnum",
            json=payload,
            headers=headers,
            timeout=(0.8, 2.2),
        )
        res.raise_for_status()
        response_data = res.json()
        if isinstance(response_data, dict):
            data = response_data.get("data")
            if not isinstance(data, dict):
                data = response_data
            number = (
                data.get("full_number")
                or data.get("no_plus_number")
                or data.get("copy")
                or data.get("number")
            )
            normalized = _canonical_number(number)
            if normalized:
                return normalized
    except Exception:
        pass
    return None

def _canonical_number(value):
    """Normalize provider/local values for duplicate and ownership checks."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if 7 <= len(digits) <= 18 else ""


def _number_is_claimed(value):
    canonical = _canonical_number(value)
    if not canonical:
        return True
    with number_allocation_lock:
        return canonical in claimed_numbers


def _claim_provider_number(source, number, owner_id):
    """Atomically claim a real provider number exactly once in this process."""
    canonical = _canonical_number(number)
    if not canonical:
        return None
    with number_allocation_lock:
        if canonical in claimed_numbers:
            return None
        claimed_numbers.add(canonical)
        if source == "stex":
            stex_assigned_numbers[canonical] = owner_id
        elif source == "voltx":
            voltx_assigned_numbers[canonical] = owner_id
        elif source == "zenex":
            zenex_assigned_numbers[canonical] = owner_id
        else:
            fastx_assigned_numbers[canonical] = owner_id
    return canonical


def _reserve_local_numbers(
    query,
    chat_id,
    req_count,
    service=None,
    country=None,
    persist=True,
):
    """Reserve local stock fairly: one number per batch before a second one.

    A batch is the local equivalent of a provider/panel.  This prevents one
    uploaded panel/file from consuming the complete request while other
    configured sources are never used.
    """
    global total_assigned_stats
    query_digits = re.sub(r"\D", "", str(query or ""))
    try:
        limit = max(1, int(req_count))
    except (TypeError, ValueError):
        limit = 1

    selected = []
    with number_allocation_lock:
        candidates = {}
        for batch_id, batch in number_batches.items():
            if service is not None and not _traffic_service_matches(
                batch.get("service", ""), service
            ):
                continue
            if country is not None and str(batch.get("country", "")) != str(country):
                continue
            rows = []
            for index, item in enumerate(batch.get("numbers", [])):
                if not isinstance(item, dict):
                    continue
                raw = item.get("num", "")
                canonical = _canonical_number(raw)
                if not canonical or (query_digits and not canonical.startswith(query_digits)):
                    continue
                if chat_id is not None and chat_id in item.get("used_by", []):
                    continue
                if canonical in claimed_numbers:
                    continue
                rows.append((index, item, canonical))
            if rows:
                # Keep file order stable; fairness, not randomness, is the
                # important part here and makes debugging allocations possible.
                candidates[batch_id] = rows

        # Round-robin across batches.  If only two panels have stock and the
        # admin requested three numbers, the third comes from the first
        # panel that still has a real available number.
        while candidates and len(selected) < limit:
            progressed = False
            for batch_id in list(candidates):
                rows = candidates.get(batch_id, [])
                if not rows:
                    candidates.pop(batch_id, None)
                    continue
                _index, item, canonical = rows.pop(0)
                if canonical in claimed_numbers:
                    continue
                claimed_numbers.add(canonical)
                if chat_id is not None:
                    used_by = item.setdefault("used_by", [])
                    if chat_id not in used_by:
                        used_by.append(chat_id)
                item["shares"] = int(item.get("shares", 0) or 0) + 1
                item["to_remove"] = True  # one number belongs to one user
                used_numbers_list.append(item.get("num", canonical))
                batch = number_batches[batch_id]
                assigned_rate = _managed_panel_country_otp_rate(
                    batch.get("service", ""), batch.get("country", "")
                )
                if assigned_rate is None:
                    assigned_rate = batch.get(
                        "rate", bot_settings.get("otp_reward", 0.0)
                    )
                assigned_number_rates[item.get("num", canonical)] = float(
                    assigned_rate
                )
                selected.append(item.get("num", canonical))
                total_assigned_stats += 1
                progressed = True
                if len(selected) >= limit:
                    break
            if not progressed:
                break

        for batch_id in list(number_batches):
            number_batches[batch_id]["numbers"] = [
                item for item in number_batches[batch_id].get("numbers", [])
                if not item.get("to_remove")
            ]

    if selected and persist:
        with database_save_lock:
            save_local_db()
    return selected


def fetch_numbers_fast(
    query,
    chat_id=None,
    req_count=1,
    source_hint=None,
    service=None,
    country=None,
    use_local=True,
    persist=True,
):
    """Fetch no more than the admin request count using fair source rotation.

    First round: one real number from every eligible provider/panel.
    Remaining slots: use the provider that has produced the best real result
    so far, falling back to the next provider when it is empty.  A number is
    atomically claimed before it is returned, so concurrent users cannot see
    the same number.
    """
    try:
        req_count = max(1, min(50, int(req_count)))
    except (TypeError, ValueError):
        req_count = 1

    fetched_nums = (
        _reserve_local_numbers(
            query,
            chat_id,
            req_count,
            service=service,
            country=country,
            persist=persist,
        )
        if use_local else []
    )
    if len(fetched_nums) >= req_count:
        return fetched_nums[:req_count], "local"

    stex_allowed = bot_settings.get("search_countries", [])
    voltx_allowed = bot_settings.get("voltx_search_countries", [])
    zenex_allowed = bot_settings.get("zenex_search_countries", [])
    is_stex_allowed = (
        _range_is_allowed(query, stex_allowed)
        or _service_range_is_allowed(query, service, bot_settings.get("stex_services", {}))
        or _live_service_range_is_allowed(query, service, "stex")
    )
    is_voltx_allowed = (
        _range_is_allowed(query, voltx_allowed)
        or _service_range_is_allowed(query, service, bot_settings.get("voltx_services", {}))
        or _live_service_range_is_allowed(query, service, "voltx")
    )
    is_zenex_allowed = (
        _range_is_allowed(query, zenex_allowed)
        or _service_range_is_allowed(query, service, bot_settings.get("zenex_services", {}))
        or _live_service_range_is_allowed(query, service, "zenex")
    )
    is_fastx_allowed = (
        _range_is_allowed(query, bot_settings.get("fastx_search_countries", []))
        or _service_range_is_allowed(query, service, bot_settings.get("fastx_services", {}))
        or _live_service_range_is_allowed(query, service, "fastx")
    )

    fastx_keys = bot_settings.get("fastx_keys", [])
    if isinstance(fastx_keys, str):
        fastx_keys = [fastx_keys]
    if not fastx_keys and os.getenv("FASTXOTP_API_KEY", "").strip():
        fastx_keys = [os.getenv("FASTXOTP_API_KEY", "").strip()]
    provider_defs = {
        "stex": (is_stex_allowed, bot_settings.get("stex_keys", []), fetch_stex_number),
        "voltx": (is_voltx_allowed, bot_settings.get("voltx_keys", []), fetch_voltx_number),
        "zenex": (is_zenex_allowed, bot_settings.get("zenex_keys", []), fetch_zenex_number),
        "fastx": (is_fastx_allowed, fastx_keys, fetch_fastx_number),
    }
    if source_hint in provider_defs:
        provider_defs = {
            source_hint: provider_defs[source_hint]
        }

    groups = {}
    for source, (allowed, keys, fetcher) in provider_defs.items():
        if allowed:
            usable_keys = [str(key).strip() for key in list(keys)[:2] if str(key).strip()]
            if usable_keys:
                groups[source] = {
                    "keys": usable_keys,
                    "fetcher": fetcher,
                    "cursor": 0,
                    "successes": 0,
                    "attempts": 0,
                }

    source_state_lock = threading.Lock()

    def call_source(source):
        group = groups[source]
        with source_state_lock:
            key = group["keys"][group["cursor"] % len(group["keys"])]
            group["cursor"] += 1
            group["attempts"] += 1
        try:
            return group["fetcher"](key, query)
        except Exception:
            return None

    def accept(source, number):
        claimed = _claim_provider_number(source, number, chat_id)
        if not claimed or claimed in {_canonical_number(item) for item in fetched_nums}:
            return False
        fetched_nums.append(claimed)
        groups[source]["successes"] += 1
        return True

    # Every active source gets one chance in the first round.  This is the
    # piece that was missing when three auto ranges were enabled.
    source_order = list(groups)
    parallel_single_source = (
        source_hint in groups and len(groups) == 1 and len(fetched_nums) < req_count
    )
    if parallel_single_source:
        source = source_hint
        needed = req_count - len(fetched_nums)
        futures = [
            _provider_fetch_executor.submit(call_source, source)
            for _ in range(needed)
        ]
        for future in futures:
            try:
                accept(source, future.result(timeout=7))
            except Exception:
                continue
    elif source_order:
        futures = {
            source: _provider_fetch_executor.submit(call_source, source)
            for source in source_order
        }
        for source in source_order:
            try:
                accept(source, futures[source].result(timeout=7))
            except Exception:
                continue

    # Fill only the remaining requested slots.  Prefer sources that already
    # returned a real number; ties retain admin/provider order.
    attempts = 0
    # The first round has already tried every provider once. Don't retry a
    # single-number request; repeated calls made the country picker feel slow.
    max_attempts = (
        0 if parallel_single_source
        else max(0, (req_count - 1) * max(1, len(groups)))
    )
    while groups and len(fetched_nums) < req_count and attempts < max_attempts:
        ranked = sorted(
            groups,
            key=lambda source: (
                -groups[source]["successes"],
                groups[source]["attempts"],
                source_order.index(source),
            ),
        )
        got_one = False
        for source in ranked:
            if len(fetched_nums) >= req_count or attempts >= max_attempts:
                break
            attempts += 1
            if accept(source, call_source(source)):
                got_one = True
                break
        if not got_one and attempts >= max_attempts:
            break

    if fetched_nums and persist:
        with database_save_lock:
            save_local_db()
    if fetched_nums:
        return fetched_nums[:req_count], "api"
    return [], None

# ==========================================
# Message Handler
# ==========================================
def handle_message(msg):
    global total_uploaded_stats
    chat_id = msg["chat"]["id"]
    chat_type = msg["chat"].get("type", "private")
    
    if chat_type != "private":
        return
        
    text = normal_button_text(msg.get("text", ""))
    command = canonical_command(text)
    admin_slash_command, admin_slash_argument = _parse_admin_slash_command(text)
    from_user = msg.get("from", {})
    full_name = " ".join(
        part for part in (
            from_user.get("first_name", ""),
            from_user.get("last_name", ""),
        ) if part
    ).strip()
    if not full_name:
        full_name = from_user.get("username", "") or str(chat_id)
    update_user_profile(chat_id, full_name, from_user.get("username", ""))
    is_new_user = register_user_local(chat_id)
    if is_new_user:
        notify_admins_new_user(msg, chat_id)

    if is_user_banned(chat_id):
        send_message(chat_id, render_body_text("🚫 <b>You are banned from using this bot!</b>\nIf you think this is a mistake, please contact support."))
        return

    system_settings_action = system_settings_reply_action(chat_id, text)
    if (
        user_states.get(chat_id) == "wait_for_restore_confirm"
        and _system_settings_button_key(text) in {
            "yes, restore",
            "✅ yes, restore",
            "yes restore",
        }
    ):
        # The system-settings reply keyboard can outlive its in-memory label
        # map (for example after a process restart). Keep the restore action
        # recognizable while a backup confirmation is pending.
        system_settings_action = "restore_confirm"

    if command in {"CLOSE", "CANCEL"} and not system_settings_action:
        user_states.pop(chat_id, None)
        temp_data.pop(chat_id, None)
        if is_admin(chat_id) and chat_id in system_settings_reply_sessions:
            send_system_settings(chat_id)
        else:
            send_message(
                chat_id,
                render_body_text(f"{PEM['no']} Cancelled."),
                reply_markup=main_menu(chat_id),
            )
        return

    message_parts = text.strip().split(maxsplit=1)
    if message_parts and message_parts[0].split("@", 1)[0].casefold() == "/back":
        if is_admin(chat_id):
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            send_admin_panel(chat_id)
        else:
            send_message(chat_id, render_body_text("🚫 Admin only."))
        return
    
    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            inviter = int(parts[1])
            if inviter != chat_id:
                referred_user = get_user(chat_id)
                if not referred_user.get("referred_by") and not _referral_is_paid(referred_user.get("ref_paid")):
                    referred_user["referred_by"] = inviter
                    referred_user["ref_paid"] = False
                    if db:
                        db.collection("users").document(str(chat_id)).update({
                            "referred_by": inviter,
                            "ref_paid": False,
                            "updated_at": iso_now(),
                        })
                    else:
                        local_users[str(chat_id)] = referred_user
                        save_user_store()
                        
    # Users without a saved language use English by default; existing
    # language preferences continue to be respected by the localization layer.

    # Restart only resets temporary UI flow. Persistent users, settings,
    # balances, uploaded numbers and admin data remain untouched.
    if command == "RESTART BOT":
        user_states.pop(chat_id, None)
        temp_data.pop(chat_id, None)
        user_cooldowns.pop(chat_id, None)
        expire_previous_number(chat_id)
        send_start_ui(chat_id)
        return

    if not check_force_join(chat_id):
        send_force_join_msg(chat_id)
        return
        
    MAIN_MENU_CMDS = [
        "GET NUMBER", "TRAFFIC", "REFER", "WITHDRAWAL", "SUPPORT",
        "CHANGE LANGUAGE", "RESTART BOT", "ADMIN PANEL", "2FA ONLINE", "2FA SET",
        *ADMIN_REPLY_COMMANDS,
    ]
    
    is_main_cmd = False
    if (
        command in MAIN_MENU_CMDS
        or system_settings_action
        or admin_slash_command in ADMIN_SLASH_COMMANDS
        or admin_slash_command == BONUS_ALERT_COMMAND
        or admin_slash_command in OTP_BONUS_NOTIFICATION_COMMANDS
        or text.startswith("/start")
    ):
        preserve_restore_confirmation = (
            system_settings_action == "restore_confirm"
            and user_states.get(chat_id) == "wait_for_restore_confirm"
        )
        if not preserve_restore_confirmation:
            if chat_id in user_states:
                del user_states[chat_id]
            if chat_id in temp_data:
                del temp_data[chat_id]
        is_main_cmd = True

    if command == "CHANGE LANGUAGE":
        send_language_selector(chat_id)
        return

    if command in ADMIN_REPLY_COMMANDS:
        handle_admin_reply_action(chat_id, command)
        return

    if admin_slash_command == BONUS_ALERT_COMMAND:
        requested = admin_slash_argument.casefold()
        if requested in {"", "status"}:
            notifications_on = _otp_bonus_notifications_enabled(get_user(chat_id))
            status = "ON" if notifications_on else "OFF"
            send_message(
                chat_id,
                render_body_text(
                    f"🎁 Bonus alert is <b>{status}</b>.\n"
                    "Use <code>/bonusalert on</code> or "
                    "<code>/bonusalert off</code> to change it."
                ),
            )
            return

        if requested not in {"on", "off"}:
            send_message(
                chat_id,
                render_body_text(
                    "Use <code>/bonusalert</code> to check the status, or "
                    "<code>/bonusalert on</code> / <code>/bonusalert off</code>."
                ),
            )
            return

        notifications_on = requested == "on"
        if not set_otp_bonus_notifications(chat_id, notifications_on):
            send_message(
                chat_id,
                render_body_text(
                    "❌ Could not save your OTP bonus notification setting. "
                    "Please try again."
                ),
            )
            return
        status = "ON" if notifications_on else "OFF"
        explanation = (
            "বোনাস যোগ হলে এখন থেকে নোটিফিকেশন পাবেন।"
            if notifications_on
            else "বোনাস ব্যালেন্সে যোগ হবে—শুধু নোটিফিকেশন বন্ধ থাকবে।"
        )
        send_message(
            chat_id,
            render_body_text(
                f"✅ OTP bonus notification <b>{status}</b> করা হয়েছে।\n"
                f"{explanation}"
            ),
        )
        return

    if admin_slash_command in OTP_BONUS_NOTIFICATION_COMMANDS:
        notifications_on = admin_slash_command == "/otpbonus_on"
        if not set_otp_bonus_notifications(chat_id, notifications_on):
            send_message(
                chat_id,
                render_body_text(
                    "❌ Could not save your OTP bonus notification setting. "
                    "Please try again."
                ),
            )
            return
        status = "ON" if notifications_on else "OFF"
        explanation = (
            "বোনাস যোগ হলে এখন থেকে নোটিফিকেশন পাবেন।"
            if notifications_on
            else "বোনাস ব্যালেন্সে যোগ হবে—শুধু নোটিফিকেশন বন্ধ থাকবে।"
        )
        send_message(
            chat_id,
            render_body_text(
                f"✅ OTP bonus notification <b>{status}</b> করা হয়েছে।\n"
                f"{explanation}"
            ),
        )
        return

    if admin_slash_command in ADMIN_SLASH_COMMANDS:
        if not is_admin(chat_id):
            send_message(chat_id, render_body_text("🚫 Admin only."))
            return

        # Admin utility commands work from any menu and keep the next admin
        # screen on the same reply-keyboard flow as the hidden menu buttons.
        system_settings_reply_sessions.add(chat_id)

        if admin_slash_command == "/localdb":
            handle_admin_reply_action(chat_id, "LOCAL DATABASE")
            return

        if admin_slash_command == "/withdraw":
            requested = admin_slash_argument.casefold()
            if requested in ("", "toggle"):
                bot_settings["withdraw_on"] = not bool(
                    bot_settings.get("withdraw_on", False)
                )
            elif requested in ("on", "enable", "enabled"):
                bot_settings["withdraw_on"] = True
            elif requested in ("off", "disable", "disabled"):
                bot_settings["withdraw_on"] = False
            else:
                send_message(
                    chat_id,
                    render_body_text("Use <code>/withdraw</code>, "
                                     "<code>/withdraw on</code>, or "
                                     "<code>/withdraw off</code>."),
                )
                return
            save_db()
            status = "ON" if bot_settings["withdraw_on"] else "OFF"
            send_message(
                chat_id,
                render_body_text(f"✅ Withdraw is now <b>{status}</b>."),
                reply_markup=GX_control_keyboard(),
            )
            return

        if admin_slash_command == "/numshare":
            if admin_slash_argument:
                # Keep the existing single-use safeguard used by the old
                # NUM/SHARE button's set_GX handler.
                bot_settings["num_share"] = 1
                save_db()
                user_states.pop(chat_id, None)
                temp_data.pop(chat_id, None)
                send_message(
                    chat_id,
                    render_body_text(
                        "✅ Num/share command saved. The effective value stays "
                        "<b>1</b> because numbers cannot be reused."
                    ),
                    reply_markup=GX_control_keyboard(),
                )
            else:
                user_states[chat_id] = "set_GX"
                temp_data[chat_id] = {
                    "msg_id": system_settings_message_ids.get(chat_id),
                    "key": "num_share",
                }
                send_message(
                    chat_id,
                    render_body_text(
                        "📝 Send the Num/Share value. For safety, the effective "
                        "value remains 1 so a number is never reused."
                    ),
                )
            return

    if system_settings_action:
        if not is_admin(chat_id):
            send_message(chat_id, render_body_text("🚫 Admin only."))
            return
        settings_message_id = system_settings_message_ids.get(chat_id)
        if not settings_message_id:
            send_system_settings(chat_id)
            settings_message_id = system_settings_message_ids.get(chat_id)
        if settings_message_id:
            handle_callback({
                "from": {"id": chat_id},
                "message": {
                    "chat": {"id": chat_id, "type": "private"},
                    "message_id": settings_message_id,
                },
                "data": system_settings_action,
                "id": "__reply_keyboard__",
            })
        return
    
    if chat_id in user_states and not is_main_cmd:
        state = user_states[chat_id]

        if state == "wait_for_demo_interval":
            settings_msg_id = temp_data.get(chat_id, {}).get("msg_id")
            raw_seconds = str(text or "").strip()
            if not raw_seconds.isdecimal():
                edit_message(
                    chat_id, settings_msg_id,
                    render_body_text("❌ Send a whole number from 1 to 10000."),
                    reply_markup=get_cancel_kb(),
                )
                return
            interval_seconds = int(raw_seconds)
            if not 1 <= interval_seconds <= 10000:
                edit_message(
                    chat_id, settings_msg_id,
                    render_body_text("❌ Choose a number from 1 to 10000."),
                    reply_markup=get_cancel_kb(),
                )
                return
            bot_settings["demo_interval"] = interval_seconds
            save_db()
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            delete_message(chat_id, msg["message_id"])
            send_system_settings(
                chat_id,
                replace_message_id=settings_msg_id,
                text=render_body_text(
                    '<tg-emoji emoji-id="6222241944894971888">➡️</tg-emoji> '
                    f'<b>Demo SMS Timer Set at {interval_seconds} Second</b> '
                    '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
                ),
            )
            return

        if state == "wait_for_restore_json":
            if "document" not in msg:
                send_message(
                    chat_id,
                    render_body_text("📥 Please upload an .xlsx, .json or .csv backup file."),
                    reply_markup=get_cancel_kb(),
                )
                return
            document = msg["document"]
            filename = document.get("file_name", "backup.json")
            extension = os.path.splitext(filename.lower())[1]
            if extension not in (".json", ".xlsx", ".csv"):
                send_message(
                    chat_id,
                    render_body_text("❌ Only .xlsx, .json or .csv files are accepted."),
                    reply_markup=get_cancel_kb(),
                )
                return
            try:
                file_info = requests.get(
                    f"{BASE_URL}/getFile",
                    params={"file_id": document["file_id"]},
                    timeout=20,
                ).json()
                file_path = file_info.get("result", {}).get("file_path")
                if not file_path:
                    raise ValueError("Telegram did not return a file path.")
                raw_backup = requests.get(f"{FILE_URL}{file_path}", timeout=30).content
                if extension == ".json":
                    backup = json.loads(raw_backup.decode("utf-8"))
                elif extension == ".xlsx":
                    backup = xlsx_to_backup(raw_backup)
                else:
                    backup = csv_to_backup(raw_backup)
                if not isinstance(backup, dict) or not isinstance(
                    backup.get("collections"), dict
                ):
                    raise ValueError("This does not look like a valid bot backup.")
                temp_data.setdefault(chat_id, {})["restore_backup"] = backup
                temp_data[chat_id]["restore_is_full"] = isinstance(
                    backup.get("runtime"), dict
                )
                user_states[chat_id] = "wait_for_restore_confirm"
                restore_msg_id = temp_data[chat_id].get("msg_id")
                if temp_data[chat_id]["restore_is_full"]:
                    restore_scope = (
                        "The uploaded full JSON will be added to the current Users, "
                        "Withdrawals, History, number stock, settings and provider "
                        "configuration. Duplicate records will be kept only once."
                    )
                else:
                    restore_scope = (
                        "This is a legacy spreadsheet/CSV backup. Its Users, Withdrawals and "
                        "History records will be added, with duplicate IDs merged."
                    )
                confirmation = (
                    "⚠️ <b>CONFIRM DATA MERGE</b>\n\n"
                    f"{restore_scope}\nCurrent data will not be deleted.\n\n"
                    "Continue?"
                )
                edit_message(
                    chat_id,
                    restore_msg_id,
                    render_body_text(confirmation),
                    reply_markup={"inline_keyboard": [
                        [{"text": "YES, RESTORE", "icon_custom_emoji_id": "6224038684333711964",
                          "callback_data": "restore_confirm", "style": "danger"}],
                        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                          "callback_data": "restore_cancel", "style": "primary"}],
                    ]},
                )
            except Exception as exc:
                send_message(
                    chat_id,
                    render_body_text(f"❌ Backup could not be read: <code>{html.escape(str(exc))}</code>"),
                    reply_markup=get_cancel_kb(),
                )
            return

        elif state == "wait_for_restore_confirm":
            send_message(chat_id, render_body_text("Use the confirmation buttons above or press Back."))
            return

        # 🌟 Auto Captcha Panel Setup Flow
        elif state == "wait_for_cpanel_url" and text:
            temp_data[chat_id]["p_data"]["login_url"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_user"
            send_message(chat_id, render_body_text(
                '<tg-emoji emoji-id="6222105571093389816">👤</tg-emoji>'
                'Entar Your panel Account Username '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_user" and text:
            temp_data[chat_id]["p_data"]["username"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_pass"
            send_message(chat_id, render_body_text("3️⃣ <b>Password</b>\n➡️ Panel এর Password দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_pass" and text:
            temp_data[chat_id]["p_data"]["password"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_msg_link"
            send_message(chat_id, render_body_text(
                '<tg-emoji emoji-id="6224158062949705345">🔗</tg-emoji>'
                'Enter the '
                '<tg-emoji emoji-id="6222241944894971888">➡️</tg-emoji>'
                'SMS/OTP'
                '<tg-emoji emoji-id="6224414378007995368">⬅️</tg-emoji>'
                'JSON URL '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_link" and text:
            temp_data[chat_id]["p_data"]["msg_link"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_num_col_name"
            send_message(chat_id, render_body_text(
                '<tg-emoji emoji-id="6224099054394025076">📱</tg-emoji>'
                'Entar Number Column name '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_num_col_name" and text:
            temp_data[chat_id]["p_data"]["num_col_name"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_num_col_idx"
            send_message(chat_id, render_body_text(
                '<tg-emoji emoji-id="6224099054394025076">📱</tg-emoji>'
                'Entar Num'
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>'
                'Column Serial Number'
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_num_col_idx" and text:
            if text.isdigit():
                temp_data[chat_id]["p_data"]["num_col_idx"] = int(text)
                user_states[chat_id] = "wait_for_cpanel_msg_col_name"
                send_message(chat_id, render_body_text(
                    '<tg-emoji emoji-id="6224339349224300713">💬</tg-emoji>'
                    'Entar Massage Column Name '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
                ), reply_markup=get_cancel_kb())
            else:
                 send_message(chat_id, render_body_text("❌ Please enter a valid number serial!"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_col_name" and text:
            temp_data[chat_id]["p_data"]["msg_col_name"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_msg_col_idx"
            send_message(chat_id, render_body_text(
                '<tg-emoji emoji-id="6224339349224300713">💬</tg-emoji>'
                'Entar MSG'
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>'
                'Column Serial Number '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_col_idx" and text:
            if text.isdigit():
                temp_data[chat_id]["p_data"]["msg_col_idx"] = int(text)
                temp_data[chat_id]["p_data"]["login_status"] = "⏳ Pending Auto-Login..."
                
                # Save the panel configuration
                bot_settings["panels"].append(temp_data[chat_id]["p_data"])
                save_db()
                
                send_message(
                    chat_id,
                    render_body_text(
                        '<tg-emoji emoji-id="6226356085477875334">🌀</tg-emoji>'
                        'Auto CPA'
                        '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>'
                        'PNL Added Successfull '
                        '<tg-emoji emoji-id="6201914938424827608">🌟</tg-emoji>'
                    ),
                    reply_markup=main_menu(chat_id),
                )
                
                msg_id = temp_data[chat_id]["msg_id"]
                handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_cpt_panels", "id": "internal"})
                
                del user_states[chat_id]
                del temp_data[chat_id]
            else:
                 send_message(chat_id, render_body_text("❌ Please enter a valid number serial!"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_um_bal_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID! Please send a numeric User ID."), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            if db:
                doc = db.collection('users').document(str(target_uid)).get()
                if not doc.exists:
                    send_message(chat_id, render_body_text("❌ User not found in database!"), reply_markup=get_cancel_kb())
                    return
                current_bal = doc.to_dict().get('balance', 0.0)
                temp_data[chat_id]["target_uid"] = target_uid
                user_states[chat_id] = "wait_for_um_bal_amt"
                balance_action = temp_data[chat_id].get("balance_action", "add")
                action_label = "ADD" if balance_action == "add" else "REMOVE"
                send_message(
                    chat_id,
                    render_body_text(
                        f"✅ User found!\n💰 Current Balance: {current_bal} ৳\n\n"
                        f"📝 Send the amount to {action_label} (positive amount only):"
                    ),
                    reply_markup=get_cancel_kb(),
                )
            return

        elif state == "wait_for_um_bal_amt" and text:
            try:
                amt = float(text.strip())
                if not math.isfinite(amt) or amt <= 0:
                    raise ValueError("Amount must be a positive finite number.")
            except (TypeError, ValueError):
                send_message(
                    chat_id,
                    render_body_text("❌ Send a valid amount greater than zero."),
                    reply_markup=get_cancel_kb(),
                )
                return

            target_uid = temp_data[chat_id]["target_uid"]
            balance_action = temp_data[chat_id].get("balance_action", "add")
            delta = amt if balance_action == "add" else -amt
            reason = "admin_add_balance" if balance_action == "add" else "admin_remove_balance"

            if balance_action == "remove":
                # Serialize only this user's check and debit; unrelated users
                # should not wait on the balance database write.
                with _user_operation_lock(target_uid):
                    current_balance = float(get_user(target_uid).get("balance", 0.0))
                    if amt > current_balance:
                        send_message(
                            chat_id,
                            render_body_text(
                                f"❌ Amount exceeds the user's current balance "
                                f"({current_balance:g} ৳). Send a smaller amount."
                            ),
                            reply_markup=get_cancel_kb(),
                        )
                        return
                    updated = update_balance(target_uid, delta, reason=reason)
            else:
                updated = update_balance(target_uid, delta, reason=reason)

            if not updated:
                send_message(
                    chat_id,
                    render_body_text("❌ Balance could not be saved. Please retry."),
                    reply_markup=get_cancel_kb(),
                )
                return

            action_label = "added to" if balance_action == "add" else "removed from"
            change_text = f"+{amt:g}" if balance_action == "add" else f"-{amt:g}"
            send_message(
                chat_id,
                render_body_text(
                    f"{PEM['ok']} {amt:g} ৳ {action_label} user {target_uid}'s balance."
                ),
                reply_markup=main_menu(chat_id),
            )
            send_message(
                target_uid,
                render_body_text(
                    f"🔔 Your balance was {action_label} by "
                    f"<b>{amt:g} ৳</b> by an Admin "
                    f"(<code>{change_text} ৳</code>)."
                ),
            )
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_for_um_ban_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID!"), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            if db:
                doc_ref = db.collection('users').document(str(target_uid))
                doc = doc_ref.get()
                if not doc.exists:
                    send_message(chat_id, render_body_text("❌ User not found in database!"), reply_markup=get_cancel_kb())
                    return
                current_status = doc.to_dict().get("banned", False)
                new_status = not current_status
                doc_ref.update({"banned": new_status})
                
                user_banned_cache[target_uid] = {'banned': new_status, 'time': time.time()}
                
                status_text = "BANNED 🚫" if new_status else "UNBANNED ✅"
                send_message(chat_id, render_body_text(f"✅ User {target_uid} has been {status_text}!"), reply_markup=main_menu(chat_id))
                del user_states[chat_id]
                del temp_data[chat_id]
            return

        elif state == "wait_for_um_prof_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID!"), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            if db:
                doc = db.collection('users').document(str(target_uid)).get()
                if not doc.exists:
                    send_message(chat_id, render_body_text("❌ User not found in database!"), reply_markup=get_cancel_kb())
                    return
                data = doc.to_dict()
                is_verified = True if data.get('total_otps', 0) > 0 else data.get('verified', False)
                prof_text = f"""➖➖➖➖➖➖➖➖
👤 <b>USER PROFILE</b>
➖➖➖➖➖➖➖➖
🆔 ID: <code>{target_uid}</code>
💰 Balance: {format_balance(data.get('balance', 0.0))} ৳
🤝 Total Refers: {data.get('total_refers', 0)}
🔐 Total OTPs: {data.get('total_otps', 0)}
✅ Verified: {is_verified}
🚫 Banned: {data.get('banned', False)}
➖➖➖➖➖➖➖➖"""
                kb = {"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "user_management", "style": "primary"}]]}
                send_message(chat_id, render_body_text(prof_text), reply_markup=kb)
                del user_states[chat_id]
                del temp_data[chat_id]
            return

        elif state == "wait_for_menu_text" and text:
            try:
                menu_key = temp_data[chat_id]["menu_key"]
                formatted_html_text = extract_premium_html(msg)
                
                bot_settings["custom_messages"][menu_key]["text"] = formatted_html_text
                save_db()
                
                delete_message(chat_id, msg["message_id"])
                
                preview_text = render_body_text(formatted_html_text)
                success_text = f"{PEM['ok']} <b>Message Body Updated successfully!</b>\n\n🎨 <b>Editing: {menu_key.upper()}</b>\n\nPreview of current Text:\n{preview_text}"
                edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(success_text), reply_markup=menu_edit_options_keyboard(menu_key))
            except Exception as e:
                send_message(chat_id, f"❌ Error saving text: {e}")
            finally:
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            return
            
        elif state == "wait_for_menu_btn" and text:
            try:
                menu_key = temp_data[chat_id]["menu_key"]
                if "-" in text:
                    parts = text.split("-", 1)
                    btn_text = parts[0].strip()
                    btn_url = parts[1].strip()
                    
                    emoji_id = None
                    emoji_char = ""
                    for ent in msg.get("entities", []):
                        if ent.get("type") == "custom_emoji":
                            emoji_id = ent.get("custom_emoji_id")
                            offset = ent.get("offset", 0)
                            length = ent.get("length", 0)
                            b_text = text.encode('utf-16-le')
                            emoji_char = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                            break
                            
                    if emoji_char:
                        btn_text = btn_text.replace(emoji_char, "").strip()
                        
                    btn_data = {"text": btn_text, "url": btn_url, "style": "primary"}
                    if emoji_id:
                        btn_data["icon_custom_emoji_id"] = emoji_id
                        
                    bot_settings["custom_messages"][menu_key]["buttons"].append(btn_data)
                    save_db()
                    delete_message(chat_id, msg["message_id"])
                    edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"{PEM['gear']} <b>Edit Inline Buttons: {menu_key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(menu_key))
                else:
                    send_message(chat_id, render_body_text(f"{PEM['no']} Invalid format. Use <code>Button Text - https://link.com</code>"))
            except Exception as e:
                 pass
            finally:
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            return

        elif state == "wait_for_test_service" and text:
            temp_data[chat_id]["service"] = text.strip()
            user_states[chat_id] = "wait_for_test_number"
            send_message(chat_id, render_body_text("📝 Send the Number (e.g. +8801712345678):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_number" and text:
            temp_data[chat_id]["number"] = text.strip()
            user_states[chat_id] = "wait_for_test_otp"
            send_message(chat_id, render_body_text("📝 Send the OTP (e.g. 556677):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_otp" and text:
            temp_data[chat_id]["otp"] = text.strip()
            user_states[chat_id] = "wait_for_test_lang"
            send_message(chat_id, render_body_text("📝 Send the Language (e.g. EN, AR):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_lang" and text:
            lang = text.strip().upper()
            if not lang.startswith("#"):
                lang = "#" + lang
                
            srv = temp_data[chat_id]["service"]
            num = temp_data[chat_id]["number"]
            otp = temp_data[chat_id]["otp"]
            
            masked = mask_number(num)
            prem_flag_html = get_flag_info_html(num)
            char, iso = get_flag_and_code(num)
            app_full_name, prem_app_html = get_service_info_html(srv)
            
            lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")
            msg_text = render_body_text(f"{prem_flag_html} {iso} | {prem_app_html} {masked} | 💬 {lang_name}")
            
            send_otp_to_forward_groups(msg_text, otp, num, srv, "auto")
                
            send_message(chat_id, render_body_text(f"{PEM['ok']} Test message formatted and sent to all Forward Groups!"), reply_markup=main_menu(chat_id))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_broadcast":
            msg_id = msg["message_id"]
            send_message(chat_id, render_body_text(f"{PEM['ok']} Broadcast started..."))
            threading.Thread(target=broadcast_copymessage, args=(chat_id, msg_id)).start()
            del user_states[chat_id]
            return

        elif state == "wait_for_txt" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text(f"{PEM['no']} Please upload a .txt file only."))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_content = requests.get(f"{FILE_URL}{file_path}").text
            
            temp_data[chat_id] = {"numbers": file_content.splitlines(), "filename": doc["file_name"]}
            user_states[chat_id] = "wait_for_service"
            send_message(
                chat_id,
                render_body_text(
                    f"{PEM['ok']} File received.\n\n"
                    '<tg-emoji emoji-id="6224038684333711964">🌟</tg-emoji> '
                    'Entar Service Name '
                    '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
                ),
                reply_markup=get_cancel_kb(),
            )
            return

        elif state == "wait_for_service" and text:
            temp_data[chat_id]["service"] = text.upper()
            user_states[chat_id] = "wait_for_country"
            send_message(
                chat_id,
                render_body_text(
                    f"{PEM['ok']} Service set.\n\n"
                    '<tg-emoji emoji-id="6224038684333711964">🌟</tg-emoji> '
                    'Entar Country Name '
                    '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
                ),
                reply_markup=get_cancel_kb(),
            )
            return

        elif state == "wait_for_country" and text:
            country = text.upper()
            temp_data[chat_id]["country"] = country
            user_states[chat_id] = "wait_for_file_rate"
            send_message(
                chat_id,
                render_body_text(
                    f"{PEM['ok']} Country set.\n\n"
                    '<tg-emoji emoji-id="6221761819090887073">🔔</tg-emoji> '
                    'Entar Otp Rate '
                    '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
                ),
                reply_markup=get_cancel_kb(),
            )
            return

        elif state == "wait_for_file_rate" and text:
            try:
                rate = float(text.strip())
            except ValueError:
                send_message(chat_id, render_body_text("❌ Invalid rate! Please enter a number (e.g. 5.0):"), reply_markup=get_cancel_kb())
                return
                
            country = temp_data[chat_id]["country"]
            service = temp_data[chat_id]["service"]
            raw_numbers = temp_data[chat_id]["numbers"]
            
            clean_nums = []
            for num in raw_numbers:
                num = num.strip()
                if num:
                    if not num.startswith('+'): num = '+' + num
                    clean_nums.append(num)
            
            batch_id = str(uuid.uuid4())[:8]
            number_batches[batch_id] = {
                "filename": temp_data[chat_id]["filename"], 
                "service": service, 
                "country": country, 
                "rate": rate,
                "numbers": [{"num": n, "shares": 0, "used_by": []} for n in clean_nums]
            }
            total_uploaded_stats += len(clean_nums)
            save_db()
            
            app_full_name, prem_app_html = get_service_info_html(service)
            prem_flag_html = get_flag_info_html(clean_nums[0]) if clean_nums else f"{PEM['world']} "
            if clean_nums and country.strip().casefold() == "madagascar":
                prem_flag_html = (
                    '<tg-emoji emoji-id="5913782968563800236">🇲🇬</tg-emoji>'
                )

            broadcast_txt = (
                "《 NEW NUMBERS ADDED 》\n"
                "◈━━━━━━━━━━━━━━━━━━◈\n"
                f"{prem_flag_html} {country} {prem_app_html} {service}\n"
                "◈━━━━━━━━━━━━━━━━━━◈\n"
                '<tg-emoji emoji-id="6224284210434154938">🍏</tg-emoji> '
                f'Total Added: <b>{len(clean_nums)}</b>\n'
                '<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                f'Reward: <b>{rate} TK</b>\n'
                "◈━━━━━━━━━━━━━━━━━━◈\n"
                '<tg-emoji emoji-id="6222241944894971888">➡️</tg-emoji> '
                'Use /start to get your numbers '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
            )
            broadcast_txt = render_body_text(broadcast_txt)
            
            send_message(
                chat_id,
                render_body_text(
                    '<tg-emoji emoji-id="6224284210434154938">🍏</tg-emoji> '
                    'Your Number Has been Added Successful '
                    '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
                    'Starting Bradcust...'
                    '<tg-emoji emoji-id="6224477342228565523">♾️</tg-emoji>'
                ),
            )
            
            def simple_broadcast(txt):
                success, failed, total = _broadcast_users(
                    all_known_users,
                    "sendMessage",
                    lambda user_id: {
                        "chat_id": user_id,
                        "text": txt,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
                send_message(
                    chat_id,
                    broadcast_completion_message(success, failed, total),
                )

            threading.Thread(
                target=simple_broadcast,
                args=(broadcast_txt,),
                daemon=True,
            ).start()
            
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_stex_key" and text:
            key_value = text.strip()
            if key_value and key_value not in bot_settings["stex_keys"]:
                bot_settings["stex_keys"].append(key_value)
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"✅ StexSMS API Key Added! Total Keys: {len(bot_settings.get('stex_keys', []))}"), reply_markup=stex_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_voltx_key" and text:
            key_value = text.strip()
            if key_value and key_value not in bot_settings["voltx_keys"]:
                bot_settings["voltx_keys"].append(key_value)
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"✅ Voltx API Key Added! Total Keys: {len(bot_settings.get('voltx_keys', []))}"), reply_markup=voltx_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_sc" and text:
            code = text.strip().replace("+", "")
            if "search_countries" not in bot_settings: bot_settings["search_countries"] = []
            if code and code not in bot_settings["search_countries"]:
                bot_settings["search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            country_buttons = []
            for idx, c in enumerate(bot_settings.get("search_countries", [])):
                country_buttons.append({"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_sc_{idx}", "style": "danger"})
            kb = grouped_keyboard_rows(country_buttons, 4)
            kb.append([{"text": "➕ Add Country Code", "callback_data": "add_search_country", "style": "success"}])
            kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "primary"}])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(
                '<tg-emoji emoji-id="6224383737711305101">🚫</tg-emoji> '
                'Allowed Country Code List '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ), reply_markup={"inline_keyboard": kb})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_vsc" and text:
            code = text.strip().replace("+", "")
            if "voltx_search_countries" not in bot_settings: bot_settings["voltx_search_countries"] = []
            if code and code not in bot_settings["voltx_search_countries"]:
                bot_settings["voltx_search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "voltx_search_country", "id": "internal"})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_nx_srv_name" and text:
            srv = text.strip().upper()
            if "stex_services" not in bot_settings: bot_settings["stex_services"] = {}
            if srv not in bot_settings["stex_services"]: bot_settings["stex_services"][srv] = {}
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "manage_stex_srv", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_nx_cnt_name" and text:
            cnt = text.strip()
            srv = temp_data[chat_id]["srv"]
            if cnt not in bot_settings["stex_services"][srv]: bot_settings["stex_services"][srv][cnt] = []
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"nx_srv_{srv}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_nx_addr" and text:
            srv, cnt = temp_data[chat_id]["srv"], temp_data[chat_id]["cnt"]
            new_range = text.strip().replace("+", "")
            
            if new_range not in bot_settings["stex_services"][srv][cnt]:
                bot_settings["stex_services"][srv][cnt].append(new_range)
                
                if "search_countries" not in bot_settings:
                    bot_settings["search_countries"] = []
                if new_range not in bot_settings["search_countries"]:
                    bot_settings["search_countries"].append(new_range)
                    
                save_db()
                
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"nx_cnt_{srv}_{cnt}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_vx_srv_name" and text:
            srv = text.strip().upper()
            if "voltx_services" not in bot_settings: bot_settings["voltx_services"] = {}
            if srv not in bot_settings["voltx_services"]: bot_settings["voltx_services"][srv] = {}
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "manage_voltx_srv", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_vx_cnt_name" and text:
            cnt = text.strip()
            srv = temp_data[chat_id]["srv"]
            if cnt not in bot_settings["voltx_services"][srv]: bot_settings["voltx_services"][srv][cnt] = []
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"vx_srv_{srv}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_vx_addr" and text:
            srv, cnt = temp_data[chat_id]["srv"], temp_data[chat_id]["cnt"]
            new_range = text.strip().replace("+", "")
            
            if new_range not in bot_settings["voltx_services"][srv][cnt]:
                bot_settings["voltx_services"][srv][cnt].append(new_range)
                
                if "voltx_search_countries" not in bot_settings:
                    bot_settings["voltx_search_countries"] = []
                if new_range not in bot_settings["voltx_search_countries"]:
                    bot_settings["voltx_search_countries"].append(new_range)
                    
                save_db()
                
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"vx_cnt_{srv}_{cnt}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_for_add_zenex_key" and text:
            key_value = text.strip()
            if key_value and key_value not in bot_settings["zenex_keys"]:
                bot_settings["zenex_keys"].append(key_value)
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"✅ Zenex API Key Added! Total Keys: {len(bot_settings.get('zenex_keys', []))}"), reply_markup=zenex_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fastx_key" and text:
            key_value = text.strip()
            keys = bot_settings.setdefault("fastx_keys", [])
            if isinstance(keys, str):
                keys = [keys]
                bot_settings["fastx_keys"] = keys
            if key_value and key_value not in keys:
                keys.append(key_value)
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(
                chat_id,
                temp_data[chat_id]["msg_id"],
                render_body_text(f"✅ FastX API key saved. Total keys: {len(keys)}"),
                reply_markup=fastx_control_keyboard(),
            )
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fx_sc" and text:
            raw_code = text.strip()
            code = raw_code.replace("+", "")
            if not re.fullmatch(r"\+?\d{1,18}", raw_code):
                send_message(chat_id, render_body_text("❌ Send a valid numeric country/range code, such as 880."))
                return
            countries = bot_settings.setdefault("fastx_search_countries", [])
            if not isinstance(countries, list):
                countries = []
                bot_settings["fastx_search_countries"] = countries
            if code not in countries:
                countries.append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            state_data = temp_data.get(chat_id, {})
            handle_callback({
                "message": {"chat": {"id": chat_id}, "message_id": state_data.get("msg_id")},
                "data": "fastx_search_country",
                "id": "internal",
            })
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_fx_srv_name" and text:
            service_name = text.strip().upper()
            if not service_name or len(service_name) > 48:
                send_message(chat_id, render_body_text("❌ Enter a service name of 1–48 characters."))
                return
            services = bot_settings.setdefault("fastx_services", {})
            if not isinstance(services, dict):
                services = {}
                bot_settings["fastx_services"] = services
            services.setdefault(service_name, {})
            save_db()
            delete_message(chat_id, msg["message_id"])
            state_data = temp_data.get(chat_id, {})
            handle_callback({
                "message": {"chat": {"id": chat_id}, "message_id": state_data.get("msg_id")},
                "data": "manage_fastx_srv",
                "id": "internal",
            })
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_fx_cnt_name" and text:
            state_data = temp_data.get(chat_id, {})
            services = bot_settings.get("fastx_services", {})
            service_names = list(services) if isinstance(services, dict) else []
            service_index = state_data.get("service_index", -1)
            if not isinstance(service_index, int) or not 0 <= service_index < len(service_names):
                user_states.pop(chat_id, None)
                temp_data.pop(chat_id, None)
                send_message(chat_id, render_body_text("❌ FastX service is no longer available."))
                return
            country_name = text.strip().upper()
            if not country_name or len(country_name) > 48:
                send_message(chat_id, render_body_text("❌ Enter a country name of 1–48 characters."))
                return
            service_name = service_names[service_index]
            countries = services.setdefault(service_name, {})
            if not isinstance(countries, dict):
                countries = {}
                services[service_name] = countries
            countries.setdefault(country_name, [])
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({
                "message": {"chat": {"id": chat_id}, "message_id": state_data.get("msg_id")},
                "data": f"fx_srv_{service_index}",
                "id": "internal",
            })
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_fx_addr" and text:
            state_data = temp_data.get(chat_id, {})
            services = bot_settings.get("fastx_services", {})
            service_names = list(services) if isinstance(services, dict) else []
            service_index = state_data.get("service_index", -1)
            country_index = state_data.get("country_index", -1)
            if not isinstance(service_index, int) or not 0 <= service_index < len(service_names):
                user_states.pop(chat_id, None)
                temp_data.pop(chat_id, None)
                send_message(chat_id, render_body_text("❌ FastX service is no longer available."))
                return
            service_name = service_names[service_index]
            countries = services.get(service_name, {})
            country_names = list(countries) if isinstance(countries, dict) else []
            if not isinstance(country_index, int) or not 0 <= country_index < len(country_names):
                user_states.pop(chat_id, None)
                temp_data.pop(chat_id, None)
                send_message(chat_id, render_body_text("❌ FastX country is no longer available."))
                return
            range_text = re.sub(r"[\s+\-]", "", text.strip())
            digits = _clean_range_prefix(range_text)
            if not re.fullmatch(r"[0-9Xx]+", range_text) or not (3 <= len(digits) <= 18):
                send_message(chat_id, render_body_text("❌ Send a valid range, such as 88017 or 88017XXX."))
                return
            country_name = country_names[country_index]
            ranges = countries.setdefault(country_name, [])
            if not isinstance(ranges, list):
                ranges = [ranges]
                countries[country_name] = ranges
            if range_text not in ranges:
                ranges.append(range_text)
            search_countries = bot_settings.setdefault("fastx_search_countries", [])
            if not isinstance(search_countries, list):
                search_countries = []
                bot_settings["fastx_search_countries"] = search_countries
            if digits not in search_countries:
                search_countries.append(digits)
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({
                "message": {"chat": {"id": chat_id}, "message_id": state_data.get("msg_id")},
                "data": f"fx_cnt_{service_index}_{country_index}",
                "id": "internal",
            })
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_for_add_zsc" and text:
            code = text.strip().replace("+", "")
            if "zenex_search_countries" not in bot_settings: bot_settings["zenex_search_countries"] = []
            if code and code not in bot_settings["zenex_search_countries"]:
                bot_settings["zenex_search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "zenex_search_country", "id": "internal"})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_zx_srv_name" and text:
            srv = text.strip().upper()
            if "zenex_services" not in bot_settings: bot_settings["zenex_services"] = {}
            if srv not in bot_settings["zenex_services"]: bot_settings["zenex_services"][srv] = {}
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": "manage_zenex_srv", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_zx_cnt_name" and text:
            cnt = text.strip()
            srv = temp_data[chat_id]["srv"]
            if cnt not in bot_settings["zenex_services"][srv]: bot_settings["zenex_services"][srv][cnt] = []
            save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"zx_srv_{srv}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_zx_addr" and text:
            srv, cnt = temp_data[chat_id]["srv"], temp_data[chat_id]["cnt"]
            new_range = text.strip().replace("+", "")
            if new_range not in bot_settings["zenex_services"][srv][cnt]:
                bot_settings["zenex_services"][srv][cnt].append(new_range)
                if "zenex_search_countries" not in bot_settings: bot_settings["zenex_search_countries"] = []
                if new_range not in bot_settings["zenex_search_countries"]: bot_settings["zenex_search_countries"].append(new_range)
                save_db()
            delete_message(chat_id, msg["message_id"])
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": temp_data[chat_id]["msg_id"]}, "data": f"zx_cnt_{srv}_{cnt}", "id": "internal"})
            del user_states[chat_id]
            return

        elif state == "wait_for_add_wm" and text:
            method = text.strip()
            if method and method not in bot_settings["w_methods"]:
                bot_settings["w_methods"].append(method)
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], get_withdrawal_methods_text(), reply_markup=w_methods_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fj" and text:
            channel_id = parse_chat_id(text)
            if channel_id not in bot_settings["fj_channels"]:
                bot_settings["fj_channels"].append(channel_id)
            clear_force_join_membership_cache()
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🔗 <b>FORCE JOIN SYSTEM</b>\nManage channels below:\n<i>(Note: For private links, use numeric IDs like -100...)</i>"), reply_markup=fj_settings_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_add_adm" and text:
            if text.isdigit():
                admin_id = int(text)
                if admin_id not in bot_settings["admins"]:
                    bot_settings["admins"].append(admin_id)
                save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], get_admin_management_text(), reply_markup=admin_settings_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fw_id" and text:
            group_id = text.strip()
            if group_id and not any(
                str(group.get("chat_id", "")).strip() == group_id
                for group in bot_settings["fw_groups"]
                if isinstance(group, dict)
            ):
                bot_settings["fw_groups"].append(
                    {"chat_id": group_id, "buttons": []}
                )
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_add_fw_btn" and text:
            fw_idx = temp_data[chat_id]["fw_idx"]
            if "-" in text:
                parts = text.split("-", 1)
                btn_text = parts[0].strip()
                btn_url = parts[1].strip()
                
                emoji_id = None
                emoji_char = ""
                for ent in msg.get("entities", []):
                    if ent.get("type") == "custom_emoji":
                        emoji_id = ent.get("custom_emoji_id")
                        offset = ent.get("offset", 0)
                        length = ent.get("length", 0)
                        b_text = text.encode('utf-16-le')
                        emoji_char = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                        break
                
                if emoji_char:
                    btn_text = btn_text.replace(emoji_char, "").strip()
                    
                btn_data = {"text": btn_text, "url": btn_url}
                if emoji_id:
                    btn_data["icon_custom_emoji_id"] = emoji_id
                    
                bot_settings["fw_groups"][fw_idx]["buttons"].append(btn_data)
                save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"🛡 <b>Manage Group:</b> {bot_settings['fw_groups'][fw_idx]['chat_id']}"), reply_markup=specific_fw_group_keyboard(fw_idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_otp_link" and text:
            bot_settings["otp_link"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_panel_name" and text:
            p_name = text.strip()
            t_key = temp_data[chat_id].get("add_type", "api")
            msg_id = temp_data[chat_id]["msg_id"]
            delete_message(chat_id, msg["message_id"])
            
            if t_key == "logc":
                user_states[chat_id] = "wait_for_cpanel_url"
                temp_data[chat_id] = {"msg_id": msg_id, "p_data": {
                    "name": p_name, "type": "Auto Captcha Panel", "status": "ON", "records": 0, "login_status": "⏳ Pending First Login"
                }}
                edit_message(chat_id, msg_id, render_body_text(
                    '<tg-emoji emoji-id="6224158062949705345">🔗</tg-emoji>'
                    'Entar Panel Login Interface Url '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
                ), reply_markup=get_cancel_kb())
                return
            else:
                bot_settings["panels"].append({
                    "name": p_name, "type": "API Panel", "status": "OFF", "api_url": "", "token": "", "records": 0
                })
                save_db()
                handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_api_panels", "id": "internal"})
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
                return

        elif state == "wait_for_panel_otp_rate" and text:
            rate_data = temp_data.get(chat_id, {})
            panel_idx = rate_data.get("panel_idx")
            service = str(rate_data.get("service", "")).strip().upper()
            country = str(rate_data.get("country", "")).strip().upper()
            try:
                rate = float(text.strip())
                if not math.isfinite(rate) or rate < 0:
                    raise ValueError("Rate must be a finite non-negative number")
            except (TypeError, ValueError):
                delete_message(chat_id, msg["message_id"])
                edit_message(
                    chat_id,
                    rate_data.get("msg_id"),
                    render_body_text(
                        "❌ Invalid rate. Send a finite number greater than or equal to 0 "
                        "(for example, 5.0):"
                    ),
                    reply_markup={"inline_keyboard": [[{
                        "text": "Cancel",
                        "icon_custom_emoji_id": "5267490665117275176",
                        "callback_data": "panel_rate_cancel",
                        "style": "danger",
                    }]]},
                )
                return
            if not isinstance(panel_idx, int) or not 0 <= panel_idx < len(bot_settings.get("panels", [])):
                user_states.pop(chat_id, None)
                temp_data.pop(chat_id, None)
                delete_message(chat_id, msg["message_id"])
                edit_message(
                    chat_id,
                    rate_data.get("msg_id"),
                    render_body_text("❌ This panel no longer exists."),
                    reply_markup=panel_otp_rates_keyboard(),
                )
                return
            panel = bot_settings["panels"][panel_idx]
            rates = panel.get("otp_rates")
            if not isinstance(rates, dict):
                rates = {}
                panel["otp_rates"] = rates
            service_key = _panel_casefold_key(rates, service)
            if service_key is None:
                service_key = service
            country_rates = rates.get(service_key)
            if not isinstance(country_rates, dict):
                country_rates = {}
                rates[service_key] = country_rates
            country_key = _panel_casefold_key(country_rates, country)
            if country_key is None:
                country_key = country
            country_rates[country_key] = rate
            try:
                save_db()
            except Exception as exc:
                print(f"⚠️ Failed to save panel OTP rate: {exc}")
                delete_message(chat_id, msg["message_id"])
                edit_message(
                    chat_id,
                    rate_data.get("msg_id"),
                    render_body_text(
                        "❌ Rate could not be saved. Please try again."
                    ),
                    reply_markup={"inline_keyboard": [[{
                        "text": "Try Again",
                        "icon_custom_emoji_id": "5420155432272438703",
                        "callback_data": (
                            f"panel_rate_edit_{panel_idx}_"
                            f"{_panel_rate_service_keys(panel).index(service)}_"
                            f"{country}"
                        ),
                        "style": "primary",
                    }], [{
                        "text": "Cancel",
                        "icon_custom_emoji_id": "5267490665117275176",
                        "callback_data": "panel_rate_cancel",
                        "style": "danger",
                    }]]},
                )
                return
            delete_message(chat_id, msg["message_id"])
            panel = bot_settings["panels"][panel_idx]
            edit_message(
                chat_id,
                rate_data.get("msg_id"),
                render_body_text(
                    f"💰 <b>{html.escape(service)} · {_panel_rate_country_label(country)}</b>\n"
                    f"Rate saved: <b>{rate:g} TK/OTP</b>\n\n"
                    "Choose another country or go back."
                ),
                reply_markup=panel_rate_countries_keyboard(panel_idx, service),
            )
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_for_panel_rate_country" and text:
            rate_data = temp_data.get(chat_id, {})
            panel_idx = rate_data.get("panel_idx")
            service = str(rate_data.get("service", "")).strip().upper()
            iso, country_name = _resolve_panel_rate_country(text)
            if not iso:
                edit_message(
                    chat_id,
                    rate_data.get("msg_id"),
                    render_body_text(
                        "❌ Country not recognized. Send its name, ISO code, or calling code "
                        "from the configured country list."
                    ),
                    reply_markup={"inline_keyboard": [[{
                        "text": "Cancel",
                        "icon_custom_emoji_id": "5267490665117275176",
                        "callback_data": "panel_rate_cancel",
                        "style": "danger",
                    }]]},
                )
                return
            if not isinstance(panel_idx, int) or not 0 <= panel_idx < len(bot_settings.get("panels", [])):
                user_states.pop(chat_id, None)
                temp_data.pop(chat_id, None)
                delete_message(chat_id, msg["message_id"])
                edit_message(
                    chat_id,
                    rate_data.get("msg_id"),
                    render_body_text("❌ This panel no longer exists."),
                    reply_markup=panel_otp_rates_keyboard(),
                )
                return
            panel = bot_settings["panels"][panel_idx]
            catalog = panel.get("otp_rate_catalog")
            if not isinstance(catalog, dict):
                catalog = {}
                panel["otp_rate_catalog"] = catalog
            service_countries = catalog.get(service)
            if not isinstance(service_countries, dict):
                service_countries = {}
                catalog[service] = service_countries
            service_countries[iso] = country_name
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(
                chat_id,
                rate_data["msg_id"],
                render_body_text(
                    f"🌍 <b>{html.escape(service)}</b>\n"
                    f"Country added: <b>{html.escape(country_name)}</b>\n\n"
                    "Tap the country to set its OTP rate."
                ),
                reply_markup=panel_rate_countries_keyboard(panel_idx, service),
            )
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            return

        elif state == "wait_for_p_api" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["api_url"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = api_panel_config_text(p)
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_tok" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["token"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = api_panel_config_text(p)
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_fapi" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["full_api_url"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = api_panel_config_text(p)
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_rec" and text:
            if text.isdigit():
                idx = temp_data[chat_id]["p_idx"]
                bot_settings["panels"][idx]["records"] = int(text)
                save_db()
                delete_message(chat_id, msg["message_id"])
                p = bot_settings["panels"][idx]
                
                ui_text = api_panel_config_text(p)
                edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            else:
                send_message(chat_id, render_body_text("❌ Please enter a valid number! Try again."), reply_markup=get_cancel_kb())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "set_GX":
            msg_id = temp_data[chat_id]["msg_id"]
            key = temp_data[chat_id]["key"]
            try:
                if key in ["min_withdraw", "otp_reward", "refer_reward"]: 
                    value = float(text)
                    if not math.isfinite(value):
                        raise ValueError("Value must be finite")
                    if key == "min_withdraw" and value <= 0:
                        raise ValueError("Minimum withdrawal must be positive")
                    if key in ["otp_reward", "refer_reward"] and value < 0:
                        raise ValueError("Reward cannot be negative")
                    bot_settings[key] = value
                elif key == "num_req":
                    bot_settings[key] = max(1, min(50, int(text)))
                elif key == "num_share":
                    # A number is never reusable by another user.  Keep the
                    # legacy field for compatibility, but lock its effective
                    # value to one so the admin UI cannot re-enable sharing.
                    bot_settings[key] = 1
                elif key == "cooldown":
                    bot_settings[key] = max(0, min(3600, int(text)))
                else: 
                    bot_settings[key] = text
                save_db()
                delete_message(chat_id, msg["message_id"])
                edit_message(
                    chat_id, msg_id,
                    render_body_text(
                        '<tg-emoji emoji-id="6203810466406342809">😵</tg-emoji> '
                        '<b>BOT MANAGEMENT</b> '
                        '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
                    ),
                    reply_markup=GX_control_keyboard(),
                )
            except:
                delete_message(chat_id, msg["message_id"])
                edit_message(
                    chat_id, msg_id,
                    render_body_text(
                        '<tg-emoji emoji-id="6203810466406342809">😵</tg-emoji> '
                        '<b>BOT MANAGEMENT</b> '
                        '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n\n'
                        '❌ Invalid value!'
                    ),
                    reply_markup=GX_control_keyboard(),
                )
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_withdraw_amount" and text:
            try:
                amount = float(text.strip())
                bal = temp_data[chat_id]["balance"]
                min_w = bot_settings['min_withdraw']
                min_w_display = format_balance(min_w).rstrip("0").rstrip(".")
                if not math.isfinite(amount) or amount <= 0:
                    raise ValueError("Amount must be a positive finite number")
                if not math.isfinite(float(min_w)) or min_w <= 0:
                    raise ValueError("Invalid withdrawal configuration")
                
                if amount < min_w:
                    send_message(
                        chat_id,
                        render_body_text(
                            f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                            f'Minimum withdrawal: {min_w_display} ৳ '
                            f'<tg-emoji emoji-id="6224139770683990463">🪙</tg-emoji>\n'
                            f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                            f'Balance » {format_balance(bal)} ৳\n\n'
                            f'<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji> '
                            "Enter Amount again:"
                        ),
                        reply_markup=get_cancel_kb(),
                    )
                    return
                if amount > bal:
                    send_message(
                        chat_id,
                        render_body_text(
                            "❌ You don't have enough balance!\n"
                            f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                            f'Balance » {format_balance(bal)} ৳\n\n'
                            f'<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji> '
                            "Enter Amount again:"
                        ),
                        reply_markup=get_cancel_kb(),
                    )
                    return
                    
                temp_data[chat_id]["amount"] = amount
                user_states[chat_id] = "wait_for_withdraw_number"
                method = temp_data[chat_id]["method"]
                method_icon = withdrawal_method_emoji_html(method)
                method_prefix = f"{method_icon} " if method_icon else ""
                send_message(
                    chat_id,
                    render_body_text(
                        f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                        f'Amount » {format_balance(amount)} ৳\n\n'
                        f'<tg-emoji emoji-id="6224284210434154938">📱</tg-emoji> '
                        f'Enter Number » {method_prefix}<b>{html.escape(str(method))}</b> '
                        "account number:"
                    ),
                    reply_markup=get_cancel_kb(),
                )
            except ValueError:
                send_message(
                    chat_id,
                    render_body_text(
                        "❌ Invalid amount!\n\n"
                        '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji> '
                        "Please send a valid amount:"
                    ),
                    reply_markup=get_cancel_kb(),
                )
            return
            
        elif state == "wait_for_2fa_key" and text:
            msg_id_to_edit = temp_data.get(chat_id, {}).get("msg_id")
            delete_message(chat_id, msg.get("message_id"))

            if not msg_id_to_edit:
                send_message(chat_id, render_body_text("❌ Error: Message not found. Try again."))
                del user_states[chat_id]
                return

            try:
                secret = text.strip().replace(" ", "")
                totp = pyotp.TOTP(secret)
                code = totp.now()
                remaining_time = 30 - (int(time.time()) % 30)
                
                success_txt = (
                    '<tg-emoji emoji-id="5197288647275071607">🛡</tg-emoji> '
                    '2FA VERIFICATION '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    '━━━━━━━━━━━━━━━━━━\n\n'
                    '<tg-emoji emoji-id="6224216474504929238">🔐</tg-emoji> '
                    'Your Code'
                    '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                    f'<code>{code}</code> '
                    '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n\n'
                    '<tg-emoji emoji-id="6224109272121222524">✔️</tg-emoji> '
                    'Expires In'
                    '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                    f'{remaining_time}s '
                    '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n\n'
                    '━━━━━━━━━━━━━━━━━━\n'
                    '<tg-emoji emoji-id="6224513742076388019">🛡</tg-emoji> '
                    'Keep your code private '
                    '<tg-emoji emoji-id="6224020344823357132">✅</tg-emoji>'
                )
                kb = [
                    [{"text": "Copy Code", "icon_custom_emoji_id": "6226463631458968746", "copy_text": {"text": code}, "style": "success"}],
                    [{"text": "Refresh Code", "icon_custom_emoji_id": "6226356085477875334", "callback_data": "ref_2fa", "style": "primary"},
                     {"text": "Get New Code", "icon_custom_emoji_id": "6224099054394025076", "callback_data": "gen_2fa", "style": "danger"}],
                    [{"text": "Close", "icon_custom_emoji_id": "6224003980997962148", "callback_data": "close_msg", "style": "danger"}],
                ]
                
                edit_message(chat_id, msg_id_to_edit, render_body_text(success_txt), reply_markup={"inline_keyboard": kb})
                del user_states[chat_id]
                temp_data[chat_id] = {"msg_id": msg_id_to_edit, "twofa_secret": secret}
            except Exception:
                error_txt = "━━━━━━━━━━━━━━━\n《 🔑 <b>ENTER 2FA KEY</b> 》\n━━━━━━━━━━━━━━━\n📝 <b>SEND YOUR 2FA SECRET KEY</b>\n━━━━━━━━━━━━━━━\n❌ <b>Invalid Secret Key! Try again.</b>\n━━━━━━━━━━━━━━━"
                cancel_kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_2fa", "style": "danger"}]]}
                edit_message(chat_id, msg_id_to_edit, render_body_text(error_txt), reply_markup=cancel_kb)
            return

        elif state == "wait_for_withdraw_number":
            method = temp_data[chat_id]["method"]
            amount = temp_data[chat_id]["amount"]
            number = text
            req_id = f"W_{str(uuid.uuid4())[:6].upper()}"
            
            first_name = msg.get("from", {}).get("first_name", "User")
            last_name = msg.get("from", {}).get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            
            if not update_balance(chat_id, -amount, reason="withdrawal_debit"):
                send_message(
                    chat_id,
                    render_body_text("❌ Could not process the withdrawal right now. Please try again."),
                    reply_markup=get_cancel_kb(),
                )
                return
            req_data = {
                "user_id": chat_id,
                "amount": amount,
                "method": method,
                "number": number,
                "full_name": full_name,
                "status": "pending",
            }
            with withdrawal_processing_lock:
                pending_withdrawals[req_id] = req_data
                display_serial = len(pending_withdrawals)
            
            if db:
                try:
                    db.collection('withdrawals').document(req_id).set({
                        "user_id": str(chat_id),
                        "amount": amount,
                        "method": method,
                        "number": str(number)[:80],
                        "full_name": full_name[:120],
                        "status": "pending",
                        "timestamp": postgres.SERVER_TIMESTAMP,
                        "request_message": f"Withdrawal request: {amount} TK via {method}"
                    })
                except: 
                    pass
            record_history(
                chat_id,
                "withdrawal_request",
                message=f"Withdrawal request: {amount} TK via {method}",
                amount=amount,
                status="pending",
                method=method,
                request_id=req_id,
                payment_number=number
            )
                    
            if bot_settings["w_group"]:
                serials = _pending_withdrawal_serials()
                display_serial = serials.get(req_id, display_serial)
                admin_chat_id = bot_settings["w_group"]
                admin_result = send_message(
                    admin_chat_id,
                    render_body_text(
                        _withdrawal_admin_request_text(
                            req_id, req_data, display_serial
                        )
                    ),
                    reply_markup=_withdrawal_admin_request_keyboard(
                        req_id, display_serial
                    ),
                )
                if (
                    isinstance(admin_result, dict)
                    and admin_result.get("ok")
                ):
                    admin_message_id = admin_result.get("result", {}).get(
                        "message_id"
                    )
                    with withdrawal_processing_lock:
                        current_request = pending_withdrawals.get(req_id)
                        if isinstance(current_request, dict):
                            current_request["admin_chat_id"] = admin_chat_id
                            current_request["admin_message_id"] = admin_message_id
                    if db and admin_message_id:
                        try:
                            db.collection("withdrawals").document(req_id).update({
                                "admin_chat_id": admin_chat_id,
                                "admin_message_id": admin_message_id,
                            })
                        except Exception as exc:
                            print(
                                f"⚠️ Could not save admin message reference "
                                f"for withdrawal {req_id}: {exc}"
                            )
                    _renumber_pending_withdrawal_messages()
                else:
                    description = (
                        admin_result.get("description", "unknown error")
                        if isinstance(admin_result, dict)
                        else "no Telegram API response"
                    )
                    print(
                        f"⚠️ Could not send withdrawal request {req_id} "
                        f"to {admin_chat_id}: {description}"
                    )
            
            kb = {"inline_keyboard": [[{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}]]}
            method_icon = withdrawal_method_emoji_html(method)
            method_prefix = f"{method_icon} " if method_icon else ""
            success_text = (
                '<tg-emoji emoji-id="6222028867272451005">🙋</tg-emoji> '
                "Your withdrawal Request Sent successful "
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n\n'
                f"{method_prefix}<b>Method » {html.escape(str(method))}</b>\n"
                f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                f"Amount » {amount} ৳\n"
                f'<tg-emoji emoji-id="6224284210434154938">📱</tg-emoji> '
                f"Number » <code>{html.escape(str(number))}</code>\n"
                f'<tg-emoji emoji-id="6222105571093389816">🧾</tg-emoji> '
                f"ID » {req_id}"
            )
            
            send_message(chat_id, render_body_text(success_text), reply_markup=kb)
                
            del user_states[chat_id]
            del temp_data[chat_id]
            return

    # --- Regular Commands ---
    if text.startswith("/start"):
        get_user(chat_id)
        add_referral(chat_id)
                    
        send_start_ui(chat_id)
            
    elif command == "TRAFFIC":
        txt, markup = build_traffic_ui()
        send_message(chat_id, txt, reply_markup=markup)
        
    elif command == "REFER":
        u_data = get_user(chat_id)
        bot_username = str(BOT_USERNAME or "GX_SMS_BOT").lstrip("@")
        ref_link = f"https://t.me/{bot_username}?start={chat_id}"
        c_msg = bot_settings["custom_messages"].get("refer", {})

        # Render the ten supplied premium emojis in the order requested.
        referral_emoji_ids = (
            "6131890186767831988",
            "6131890186767831988",
            "6224334680594850487",
            "6224381843630728008",
            "6224255644606670093",
            "6219554021217148948",
            "6224381843630728008",
            "6224255644606670093",
            "6224158062949705345",
            "6226463631458968746",
        )

        def referral_emoji(index, fallback):
            return (
                f'<tg-emoji emoji-id="{referral_emoji_ids[index - 1]}">'
                f"{fallback}</tg-emoji>"
            )

        reward_text = format_balance(bot_settings.get("refer_reward", 0.5))
        raw_txt = (
            f"{referral_emoji(1, '🎁')} <b>Refer &amp; Earn</b> "
            f"{referral_emoji(2, '🎁')}\n"
            "━━━━━━━━━━━━━━\n\n"
            f"{referral_emoji(3, '👥')} Total Referrals "
            f"{referral_emoji(4, '🛜')} "
            f"<b>{int(_as_number(u_data.get('total_refers'), 0))}</b> "
            f"{referral_emoji(5, '✅')}\n"
            f"{referral_emoji(6, '📣')} Per Referral "
            f"{referral_emoji(7, '🛜')} <b>৳{reward_text}</b> "
            f"{referral_emoji(8, '✅')}\n\n"
            f"{referral_emoji(9, '🔗')} Referral Link\n"
            f"<code>{html.escape(ref_link)}</code> "
            f"{referral_emoji(10, '👈')}\n"
            "━━━━━━━━━━━━━━"
        )
        txt = render_body_text(raw_txt)

        share_text = "এই referral link-টি বন্ধুদের কাছে পাঠান।"
        share_url = (
            "https://t.me/share/url?"
            f"url={quote(ref_link, safe='')}&text={quote(share_text, safe='')}"
        )
        kb = [[
            {
                "text": "COPY LINK",
                "icon_custom_emoji_id": "6222073659486381042",
                "copy_text": {"text": ref_link},
                "style": "success",
            },
            {
                "text": "SHARE LINK",
                "icon_custom_emoji_id": "5420517437885943844",
                "url": share_url,
                "style": "primary",
            },
        ]]
        for b in c_msg.get("buttons", []): 
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        kb.append([{"text": "CLOSE", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif command == "WITHDRAWAL":
        if not bot_settings["withdraw_on"]:
            send_message(chat_id, render_body_text(f"{PEM['no']} Withdrawals are currently disabled."))
            return
        
        u_data = get_user(chat_id)
        bal = u_data.get('balance', 0.0)
        
        c_msg = bot_settings["custom_messages"].get("withdrawal", {})
        raw_txt = c_msg.get("text", "Withdrawal")
        if not raw_txt or (
            "SELECT METHOD:" in raw_txt and "Total Otp:" in raw_txt
        ):
            raw_txt = DEFAULT_CUSTOM_MESSAGES["withdrawal"]["text"]
        raw_txt = (
            raw_txt.replace("{bal}", format_balance(bal))
            .replace("{total_otp}", str(u_data.get('total_otps', 0)))
            .replace("{total_ref}", str(u_data.get('total_refers', 0)))
            .replace("{min_w}", format_balance(bot_settings['min_withdraw']))
        )
        txt = render_body_text(raw_txt)
        
        kb = []
        method_row = []
        for m in bot_settings["w_methods"]:
            method = m.strip()
            if not method:
                continue
            method_button = {
                "text": method,
                "callback_data": f"sel_wm_{method}",
                "style": "primary",
            }
            method_icon_id = withdrawal_method_emoji_id(method)
            if method_icon_id:
                method_button["icon_custom_emoji_id"] = method_icon_id
            method_row.append(method_button)
            if len(method_row) == 2:
                kb.append(method_row)
                method_row = []
        if method_row:
            kb.append(method_row)
        kb.append([{"text": "CANCEL", "callback_data": "close_msg", "style": "danger"}])
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif command == "ADMIN PANEL" and is_admin(chat_id):
        send_admin_panel(chat_id)

    elif command == "GET NUMBER":
        show_number_app_selection(chat_id)

    elif command in ("2FA ONLINE", "2FA SET") or text in ("🔐 2FA ONLINE", "🔐 2FA SET"):
        txt = (
            '<tg-emoji emoji-id="6224513742076388019">🛡</tg-emoji> '
            '2FA VERIFICATION '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
            '◈━━━━━━━━━━━━━━━━━━◈\n'
            '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
            'Get your time-based security code instantly '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
            '◈━━━━━━━━━━━━━━━━━━◈'
        )
        kb = [
            [{"text": "Get New Code", "icon_custom_emoji_id": "6224099054394025076", "callback_data": "gen_2fa", "style": "success"}],
            [{"text": "Close", "icon_custom_emoji_id": "6224003980997962148", "callback_data": "close_msg", "style": "danger"}],
        ]
        send_message(chat_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif command == "SUPPORT":
        c_msg = bot_settings["custom_messages"].get("support", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['msg']} Support"))
        if not txt.strip(): txt = render_body_text(f"{PEM['msg']} Support")
        kb = []
        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
            
        sup_link = bot_settings.get("support_link", "")
        if sup_link:
            kb.insert(0, [{"text": "Contact Support", "icon_custom_emoji_id": MESSAGE_SMS_EMOJI_ID, "url": sup_link, "style": "success"}])
            
        kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb} if kb else None)

def expire_previous_number(chat_id, background=False, skip_message_id=None):
    prev_data = user_active_sessions.pop(chat_id, None)
    if not prev_data:
        return

    prev_msg_id = prev_data["msg_id"]
    nums = prev_data["nums"]

    for num in nums:
        if num in stex_assigned_numbers: del stex_assigned_numbers[num]
        if num in voltx_assigned_numbers: del voltx_assigned_numbers[num]
        if num in zenex_assigned_numbers: del zenex_assigned_numbers[num]
        if num in fastx_assigned_numbers: del fastx_assigned_numbers[num]

    def finish_expiration():
        save_db()
        if prev_msg_id == skip_message_id:
            return
        kb = [[{"text": "Number Expired", "icon_custom_emoji_id": "5336997731481193790", "callback_data": "ignore", "style": "danger"}]]
        try:
            edit_message(chat_id, prev_msg_id, "NEW NUMBER\n", reply_markup={"inline_keyboard": kb})
        except:
            pass

    if background:
        threading.Thread(target=finish_expiration, daemon=True).start()
    else:
        finish_expiration()


def _traffic_name_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _service_traffic_count(service):
    current_time = time.time()
    return sum(
        1 for item in recent_traffic
        if _traffic_service_matches(item.get("service"), service)
        and current_time - item.get("time", 0) <= 3600
    )


def _country_traffic_count(country):
    target = str(country or "").strip().upper()
    current_time = time.time()
    total = 0
    for item in recent_traffic:
        if current_time - item.get("time", 0) > 3600:
            continue
        iso = str(item.get("iso", "") or "").upper()
        full_name = str(
            get_flag_info_html(iso, return_full_name=True) or ""
        ).upper()
        if target == iso or target == full_name or target in full_name or full_name in target:
            total += 1
    return total


def _top_traffic_countries(service, countries, limit=None):
    """Rank available countries by live traffic, optionally limiting the list."""
    unique_countries = list(dict.fromkeys(str(country) for country in countries))
    service_key = _traffic_name_key(service)
    current_time = time.time()
    ranked = []
    for index, country in enumerate(unique_countries):
        service_count = sum(
            1 for item in recent_traffic
            if _traffic_service_matches(item.get("service"), service)
            and current_time - item.get("time", 0) <= 3600
            and (
                str(item.get("iso", "")).upper() == country.upper()
                or str(get_flag_info_html(
                    str(item.get("iso", "")), return_full_name=True
                ) or "").upper() == country.upper()
            )
        )
        ranked.append((
            service_count,
            _country_traffic_count(country),
            country.lower(),
            index,
            country,
        ))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
    return [item[-1] for item in (ranked[:limit] if limit else ranked)]


def _two_column_rows(buttons):
    """Arrange inline buttons two per row for compact mobile layouts."""
    rows = []
    current = []
    for button in buttons:
        current.append(button)
        if len(current) == 2:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    return rows


def _equal_service_button_labels(buttons, minimum_width=16):
    """Give service buttons a consistent, slightly roomier visual width."""
    if not buttons:
        return buttons
    longest = max(
        len(re.sub(r"<[^>]+>", "", str(button.get("text", ""))))
        for button in buttons
        if isinstance(button, dict)
    )
    target_width = max(minimum_width, longest)
    padded = []
    for button in buttons:
        if not isinstance(button, dict):
            continue
        item = button.copy()
        label = str(item.get("text", "")).strip()
        # Non-breaking spaces keep Telegram from collapsing the alignment
        # padding while keeping the service name itself unchanged.
        item["text"] = f"\u00a0{label.center(target_width)}\u00a0"
        padded.append(item)
    return padded


def _stretch_service_prompt(text, buttons):
    """Make the service prompt visually span the two-column service row."""
    if not text or not buttons:
        return text
    label_width = max(
        len(re.sub(r"<[^>]+>", "", str(button.get("text", ""))))
        for button in buttons
        if isinstance(button, dict)
    )
    visible_text = re.sub(r"<[^>]+>", "", str(text))
    # Add a little extra room for Telegram's inline-button icon spacing so
    # the prompt bubble reaches the right edge of the service row.
    target_width = (label_width * 2) + 9
    extra_spaces = max(0, target_width - len(visible_text))
    padding = "\u00a0" * extra_spaces
    return f"{text}{padding}"


def _compact_number_label(number):
    """Show the complete number while keeping one consistent label format."""
    value = str(number or "").strip()
    clean = re.sub(r"[^\d]", "", value)
    return f"+{clean}" if clean else value


# ==========================================
# Callback Query Handler
# ==========================================
def _callback_ack_requires_handler(data):
    """Keep callbacks that need validation or a custom alert on their old path."""
    data = str(data or "")
    return (
        data.startswith(("wapp_", "wrej_"))
        or data.startswith("test_p_conn_")
        or data.startswith("c_n_")
        or data.startswith("g_c_")
        or data.startswith("np_cty_")
        or data.startswith("same_num:")
        or data == "toggle_join_notify"
        or data in ("np_repeat", "set_demo_interval")
    )


def handle_callback(call):
    global total_assigned_stats
    chat_id = call["message"]["chat"]["id"]
    chat_type = call["message"]["chat"].get("type", "private")
    data = call.get("data", "")

    if (
        not call.get("_early_ack_scheduled")
        and not _callback_ack_requires_handler(data)
    ):
        try:
            _callback_ack_executor.submit(answer_callback, call["id"])
        except Exception:
            pass

    if chat_type != "private" and not (
        data.startswith("wapp_")
        or data.startswith("wrej_")
        or data.startswith("same_num:")
    ):
        return

    msg_id = call["message"]["message_id"]

    if data.startswith("same_num:"):
        _handle_same_number_request(call)
        return

    if chat_type == "private":
        if is_user_banned(chat_id):
            answer_callback(call["id"], "🚫 You are banned from using this bot!", show_alert=True)
            return

        if data in ("set_lang_EN", "set_lang_BN"):
            language = set_user_language(chat_id, data.rsplit("_", 1)[-1])
            answer_callback(call["id"], "Language saved!" if language == "EN" else "ভাষা সেভ হয়েছে!")
            delete_message(chat_id, msg_id)
            if not check_force_join(chat_id):
                send_force_join_msg(chat_id)
            else:
                send_start_ui(chat_id)
            return

        if not check_force_join(chat_id) and data != "check_fj":
            send_force_join_msg(chat_id)
            return

    if data == "check_fj":
        if check_force_join(chat_id, force_refresh=True):
            delete_message(chat_id, msg_id)
            send_message(chat_id, render_body_text(f"{PEM['ok']} Thanks for joining! You can now use the bot."), reply_markup=main_menu(chat_id))
            
            add_referral(chat_id)
        else:
            answer_callback(call["id"], "❌ You haven't joined all channels yet!", show_alert=True)
        return

    if is_admin_callback(data) and not is_admin(chat_id):
        answer_callback(call["id"], "🚫 Admin only.", show_alert=True)
        return

    if data == "backup_all_data":
        answer_callback(call["id"], "Preparing backup…")
        send_full_backup(chat_id)
        return

    if data == "restore_all_data":
        user_states[chat_id] = "wait_for_restore_json"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6222241944894971888">➡️</tg-emoji> '
                '<b>RESTORE ALL DATA</b> '
                '<tg-emoji emoji-id="6224477342228565523">♾️</tg-emoji>\n\n'
                "Upload an Excel .xlsx file, or a bot .json/.csv backup now.\n"
                "After upload, the bot will show a final confirmation before replacing "
                "the current Users, Withdrawals and History data."
            ),
            reply_markup={"inline_keyboard": [[
                {"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                 "callback_data": "restore_cancel", "style": "primary"}
            ]]}
        )
        return

    if data == "restore_confirm":
        restore_backup = temp_data.get(chat_id, {}).get("restore_backup")
        if not restore_backup:
            answer_callback(call["id"], "❌ Backup session expired. Upload it again.", show_alert=True)
            return
        try:
            restore_summary = restore_full_backup(restore_backup)
            save_db()
            user_states.pop(chat_id, None)
            temp_data.pop(chat_id, None)
            answer_callback(call["id"], "✅ Data merge completed.", show_alert=True)
            if restore_summary.get("full_state"):
                restore_details = (
                    f"Users: {restore_summary['users']}\n"
                    f"Withdrawals: {restore_summary['withdrawals']}\n"
                    f"History: {restore_summary['history']}\n"
                    f"Number files: {restore_summary['number_batches']}\n"
                    "Local JSON save: ✅"
                )
            else:
                restore_details = (
                    f"Users restored: {restore_summary['users']}\n"
                    f"Withdrawals: {restore_summary['withdrawals']}\n"
                    f"History: {restore_summary['history']}\n"
                    "Local JSON save: ✅"
                )
            delete_message(chat_id, msg_id)
            send_admin_panel(
                chat_id,
                render_body_text(
                    f"{PEM['ok']} <b>Restore completed successfully.</b>\n"
                    f"{restore_details}"
                ),
            )
        except Exception as exc:
            answer_callback(call["id"], "❌ Restore failed.", show_alert=True)
            delete_message(chat_id, msg_id)
            send_admin_panel(
                chat_id,
                render_body_text(f"❌ Restore failed: <code>{html.escape(str(exc))}</code>"),
            )
        return

    if data == "restore_cancel":
        user_states.pop(chat_id, None)
        temp_data.pop(chat_id, None)
        answer_callback(call["id"], "Restore cancelled.")
        send_system_settings(chat_id, replace_message_id=msg_id)
        return

    if data == "delete_all_data":
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224387933894354612">🚨</tg-emoji> '
                '<b>DELETE ALL BOT DATA</b> '
                '<tg-emoji emoji-id="6224003980997962148">❌</tg-emoji>\n\n'
                "This will remove users, balances, history, withdrawals, number stock, "
                "API keys and custom settings from the local JSON database.\n"
                "The owner account and safe default settings will remain so the bot can start again."
            ),
            reply_markup={"inline_keyboard": [
                [{"text": "YES, DELETE EVERYTHING", "icon_custom_emoji_id": "6224256529369932354",
                  "callback_data": "delete_all_data_yes", "style": "danger"}],
                [{"text": "NO, GO BACK", "icon_custom_emoji_id": "5267490665117274959",
                  "callback_data": "back_to_admin", "style": "primary"}],
            ]}
        )
        return

    if data == "delete_all_data_yes":
        delete_all_bot_data()
        save_db()
        answer_callback(call["id"], "✅ All bot data deleted.", show_alert=True)
        delete_message(chat_id, msg_id)
        send_admin_panel(chat_id)
        return

    if data == "local_db_status":
        edit_message(
            chat_id,
            msg_id,
            render_body_text(get_local_db_status_text()),
            reply_markup={"inline_keyboard": [[
                {"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                 "callback_data": "back_to_admin", "style": "primary"}
            ]]},
        )
        return



    if data == "export_data":
        if not is_admin(chat_id):
            answer_callback(call["id"], "🚫 Admin only.", show_alert=True)
            return
        edit_message(chat_id, msg_id, render_body_text(
            loading_html("Preparing clean user-data export...")
        ))
        send_data_export(chat_id)
        delete_message(chat_id, msg_id)
        send_admin_panel(chat_id)
        return

    if data == "close_msg":
        answer_callback(call["id"])
        user_states.pop(chat_id, None)
        temp_data.pop(chat_id, None)
        if chat_id in system_settings_reply_sessions:
            send_system_settings(chat_id, replace_message_id=msg_id)
        else:
            delete_message(chat_id, msg_id)

    elif data == "ignore":
        # Informational/status buttons use this callback so Telegram clears
        # the loading state instead of leaving a dead callback spinning.
        answer_callback(call["id"])
        
    elif data == "cancel_state":
        answer_callback(call["id"])
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        if chat_id in system_settings_reply_sessions:
            send_system_settings(chat_id, replace_message_id=msg_id)
        else:
            delete_message(chat_id, msg_id)

    elif data == "cancel_2fa":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        txt = (
            '<tg-emoji emoji-id="6224513742076388019">🛡</tg-emoji> '
            '2FA VERIFICATION '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
            '◈━━━━━━━━━━━━━━━━━━◈\n'
            '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
            'Get your time-based security code instantly '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
            '◈━━━━━━━━━━━━━━━━━━◈'
        )
        kb = [
            [{"text": "Get New Code", "icon_custom_emoji_id": "6224099054394025076", "callback_data": "gen_2fa", "style": "success"}],
            [{"text": "Close", "icon_custom_emoji_id": "6224003980997962148", "callback_data": "close_msg", "style": "danger"}],
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data == "gen_2fa":
        user_states[chat_id] = "wait_for_2fa_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        txt = "━━━━━━━━━━━━━━━\n《 🔑 <b>ENTER 2FA KEY</b> 》\n━━━━━━━━━━━━━━━\n📝 <b>SEND YOUR 2FA SECRET KEY</b>\n━━━━━━━━━━━━━━━"
        kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_2fa", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup=kb)
        answer_callback(call["id"])

    elif data == "ref_2fa":
        secret = temp_data.get(chat_id, {}).get("twofa_secret", "")
        try:
            if not secret:
                raise ValueError("2FA session expired")
            totp = pyotp.TOTP(secret)
            code = totp.now()
            remaining_time = 30 - (int(time.time()) % 30)
            
            success_txt = (
                '<tg-emoji emoji-id="5197288647275071607">🛡</tg-emoji> '
                '2FA VERIFICATION '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                '━━━━━━━━━━━━━━━━━━\n\n'
                '<tg-emoji emoji-id="6224216474504929238">🔐</tg-emoji> '
                'Your Code'
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                f'<code>{code}</code> '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n\n'
                '<tg-emoji emoji-id="6224109272121222524">✔️</tg-emoji> '
                'Expires In'
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                f'{remaining_time}s '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n\n'
                '━━━━━━━━━━━━━━━━━━\n'
                '<tg-emoji emoji-id="6224513742076388019">🛡</tg-emoji> '
                'Keep your code private '
                '<tg-emoji emoji-id="6224020344823357132">✅</tg-emoji>'
            )
            kb = [
                [{"text": "Copy Code", "icon_custom_emoji_id": "6226463631458968746", "copy_text": {"text": code}, "style": "success"}],
                [{"text": "Refresh Code", "icon_custom_emoji_id": "6226356085477875334", "callback_data": "ref_2fa", "style": "primary"},
                 {"text": "Get New Code", "icon_custom_emoji_id": "6224099054394025076", "callback_data": "gen_2fa", "style": "danger"}],
                [{"text": "Close", "icon_custom_emoji_id": "6224003980997962148", "callback_data": "close_msg", "style": "danger"}],
            ]
            
            edit_message(chat_id, msg_id, render_body_text(success_txt), reply_markup={"inline_keyboard": kb})
        except:
            answer_callback(call["id"], "❌ Error refreshing code!", show_alert=True)

    elif data == "cancel_GX_edit":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6203810466406342809">😵</tg-emoji> '
                '<b>BOT MANAGEMENT</b> '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ),
            reply_markup=GX_control_keyboard(),
        )
        
    elif data == "panel_otp_rates":
        if not bot_settings.get("panels"):
            edit_message(
                chat_id,
                msg_id,
                render_body_text("📊 <b>PANEL OTP RATES</b>\n\nNo Panel Management providers are configured yet."),
                reply_markup=panel_otp_rates_keyboard(),
            )
        else:
            edit_message(
                chat_id,
                msg_id,
                render_body_text(
                    "📊 <b>PANEL OTP RATES</b>\n\n"
                    "Choose a managed panel. These rates are separate from the normal "
                    "Stex/Voltx/Zenex and global OTP reward rates."
                ),
                reply_markup=panel_otp_rates_keyboard(),
            )

    elif data.startswith("panel_rate_panel_"):
        try:
            panel_idx = int(data.rsplit("_", 1)[-1])
            if not 0 <= panel_idx < len(bot_settings.get("panels", [])):
                raise IndexError
            panel = bot_settings["panels"][panel_idx]
            name = html.escape(str(panel.get("name", f"Panel {panel_idx + 1}")))
            edit_message(
                chat_id,
                msg_id,
                render_body_text(
                    f"📱 <b>{name} · SERVICES</b>\n\n"
                    "Select the service to manage its country rates. The service is "
                    "taken from the panel name or detected OTP records."
                ),
                reply_markup=panel_rate_services_keyboard(panel_idx),
            )
        except (ValueError, IndexError, TypeError):
            answer_callback(call["id"], "❌ Panel no longer exists.", show_alert=True)

    elif data.startswith("panel_rate_service_"):
        try:
            parts = data.split("_")
            panel_idx, service_idx = int(parts[-2]), int(parts[-1])
            if not 0 <= panel_idx < len(bot_settings.get("panels", [])):
                raise IndexError
            panel = bot_settings["panels"][panel_idx]
            services = _panel_rate_service_keys(panel)
            service = services[service_idx]
            catalog = panel.get("otp_rate_catalog", {})
            country_count = (
                len(catalog.get(service, {}))
                if isinstance(catalog, dict)
                and isinstance(catalog.get(service, {}), dict)
                else 0
            )
            edit_message(
                chat_id,
                msg_id,
                render_body_text(
                    f"🌍 <b>{html.escape(service)} · COUNTRIES</b>\n\n"
                    f"Known countries: <b>{country_count}</b>\n"
                    "Countries are learned from this panel's phone-number records and OTPs. "
                    "Use Add Country if you want to configure one before it appears."
                ),
                reply_markup=panel_rate_countries_keyboard(panel_idx, service),
            )
        except (ValueError, IndexError, TypeError):
            answer_callback(call["id"], "❌ Panel or service no longer exists.", show_alert=True)

    elif data.startswith("panel_rate_edit_"):
        try:
            parts = data.split("_")
            panel_idx, service_idx = int(parts[3]), int(parts[4])
            country = parts[5].strip().upper()
            if not 0 <= panel_idx < len(bot_settings.get("panels", [])):
                raise IndexError
            panel = bot_settings["panels"][panel_idx]
            service = _panel_rate_service_keys(panel)[service_idx]
            if country not in _panel_rate_country_keys(panel, service):
                raise IndexError
            user_states[chat_id] = "wait_for_panel_otp_rate"
            temp_data[chat_id] = {
                "msg_id": msg_id,
                "panel_idx": panel_idx,
                "service": service,
                "country": country,
            }
            edit_message(
                chat_id,
                msg_id,
                render_body_text(
                    "💰 <b>Set OTP rate</b>\n\n"
                    f"Panel: <b>{html.escape(str(panel.get('name', 'Panel')))}</b>\n"
                    f"Service: <b>{html.escape(service)}</b>\n"
                    f"Country: <b>{html.escape(_panel_rate_country_label(country))}</b>\n\n"
                    "Send the reward in TK per OTP (0 is allowed). "
                    "This override applies only to this managed panel/service/country."
                ),
                reply_markup={"inline_keyboard": [[{
                    "text": "Cancel",
                    "icon_custom_emoji_id": "5267490665117275176",
                    "callback_data": "panel_rate_cancel",
                    "style": "danger",
                }]]},
            )
            answer_callback(call["id"])
        except (ValueError, IndexError, TypeError):
            answer_callback(call["id"], "❌ Panel, service, or country no longer exists.", show_alert=True)

    elif data.startswith("panel_rate_add_"):
        try:
            parts = data.split("_")
            panel_idx, service_idx = int(parts[-2]), int(parts[-1])
            if not 0 <= panel_idx < len(bot_settings.get("panels", [])):
                raise IndexError
            panel = bot_settings["panels"][panel_idx]
            service = _panel_rate_service_keys(panel)[service_idx]
            user_states[chat_id] = "wait_for_panel_rate_country"
            temp_data[chat_id] = {
                "msg_id": msg_id,
                "panel_idx": panel_idx,
                "service": service,
            }
            edit_message(
                chat_id,
                msg_id,
                render_body_text(
                    f"🌍 <b>Add a country for {html.escape(service)}</b>\n\n"
                    "Send a country name, ISO code, or calling code from the configured "
                    "country list. The country will be saved only for this managed panel."
                ),
                reply_markup={"inline_keyboard": [[{
                    "text": "Cancel",
                    "icon_custom_emoji_id": "5267490665117275176",
                    "callback_data": "panel_rate_cancel",
                    "style": "danger",
                }]]},
            )
        except (ValueError, IndexError, TypeError):
            answer_callback(call["id"], "❌ Panel or service no longer exists.", show_alert=True)

    elif data == "panel_rate_cancel":
        rate_data = temp_data.pop(chat_id, {})
        user_states.pop(chat_id, None)
        panel_idx = rate_data.get("panel_idx")
        service = rate_data.get("service")
        if (
            isinstance(panel_idx, int)
            and 0 <= panel_idx < len(bot_settings.get("panels", []))
            and service
            and str(service).upper() in _panel_rate_service_keys(bot_settings["panels"][panel_idx])
        ):
            panel = bot_settings["panels"][panel_idx]
            service = str(service).upper()
            edit_message(
                chat_id,
                msg_id,
                render_body_text(f"🌍 <b>{html.escape(service)} · COUNTRIES</b>"),
                reply_markup=panel_rate_countries_keyboard(panel_idx, service),
            )
        else:
            edit_message(
                chat_id,
                msg_id,
                render_body_text("📊 <b>PANEL OTP RATES</b>"),
                reply_markup=panel_otp_rates_keyboard(),
            )
        
    elif data.startswith("traffic_page_"):
        try:
            page = int(data.rsplit("_", 1)[-1])
        except (TypeError, ValueError):
            page = 0
        answer_callback(call["id"])
        txt, markup = build_traffic_ui(page=page)
        edit_message(chat_id, msg_id, txt, reply_markup=markup)

    elif data == "refresh_traffic" or data.startswith("refresh_traffic_"):
        try:
            page = int(data.rsplit("_", 1)[-1]) if data != "refresh_traffic" else 0
        except (TypeError, ValueError):
            page = 0
        txt, markup = build_traffic_ui(page=page)
        edit_message(chat_id, msg_id, txt, reply_markup=markup)
        answer_callback(call["id"], "✅ Traffic Refreshed!", show_alert=False)

    elif data.startswith("exp_rng_"):
        srv_query = data.replace("exp_rng_", "")
        
        country_stats = {}
        current_time = time.time()
        for t in recent_traffic:
            if current_time - t.get("time", 0) <= 3600:
                if _traffic_service_matches(t.get("service", ""), srv_query):
                    iso = str(t.get("iso", "XX")).upper()
                    flag = t.get("flag", "🌍")
                    if iso not in country_stats:
                        country_stats[iso] = {"count": 0, "flag": flag}
                    country_stats[iso]["count"] += 1
        
        if not country_stats:
            answer_callback(call["id"], "❌ No recent traffic found for this service!", show_alert=True)
            return
            
        kb = []
        for iso, c_data in sorted(country_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            count = c_data["count"]
            c_name = iso
            emoji_id = "5780471598922337683"
            for _key, fdata in bot_settings.get("premium_flags", {}).items():
                if fdata.get("iso") == iso:
                    c_name = fdata.get("name", iso)
                    if "id" in fdata: emoji_id = fdata["id"]
                    break
            
            btn_text = f"{c_name} ({iso}) - {count} OTP"
            kb.append([{"text": btn_text, "icon_custom_emoji_id": emoji_id, "callback_data": f"exp_c_{srv_query}_{iso}", "style": "primary"}])
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "refresh_traffic", "style": "danger"}])
        
        app_full_name, prem_app_html = get_service_info_html(srv_query)
        edit_message(chat_id, msg_id, render_body_text(f"📊 <b>Explore Service: {prem_app_html} {app_full_name}</b>\n\nSelect a country to view available ranges:"), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data.startswith("exp_c_"):
        parts = data.split("_")
        srv_query = parts[2]
        iso_query = parts[3]
        
        nums = []
        current_time = time.time()
        for t in recent_traffic:
            if current_time - t.get("time", 0) <= 3600:
                if (
                    _traffic_service_matches(t.get("service", ""), srv_query)
                    and str(t.get("iso", "")).upper() == iso_query.upper()
                ):
                    raw_value = t.get("real_range") or t.get("number", "")
                    digits = _clean_range_prefix(raw_value)
                    if digits:
                        nums.append((digits, bool(t.get("real_range"))))

        known_ranges = set()
        for provider_key in ("stex_services", "voltx_services", "zenex_services", "fastx_services"):
            services = bot_settings.get(provider_key, {})
            if not isinstance(services, dict):
                continue
            for configured_service, countries in services.items():
                if not _traffic_service_matches(configured_service, srv_query):
                    continue
                if not isinstance(countries, dict):
                    continue
                for configured_country, ranges in countries.items():
                    if not _country_matches_iso(configured_country, iso_query):
                        continue
                    if not isinstance(ranges, (list, tuple, set)):
                        ranges = [ranges]
                    for configured_range in ranges:
                        if isinstance(configured_range, dict):
                            configured_range = (
                                configured_range.get("range")
                                or configured_range.get("rid")
                                or configured_range.get("number")
                            )
                        clean_range = _clean_range_prefix(configured_range)
                        if 4 <= len(clean_range) <= 18:
                            known_ranges.add(clean_range)

        sorted_known = sorted(known_ranges, key=len, reverse=True)
        
        r_counts = Counter()
        for num, is_explicit_range in nums:
            matched = False
            for r in sorted_known:
                if num.startswith(r):
                    r_counts[r] += 1
                    matched = True
                    break
            if not matched:
                # A panel's live-access range is already an exact request ID.
                # For OTP records with a full number, use a stable prefix.
                fallback_range = num[:9] if is_explicit_range else num[:7]
                if len(fallback_range) >= 4:
                    r_counts[fallback_range] += 1

        # Keep configured ranges selectable even when a panel reports live
        # traffic but its matching OTP row has expired from this process.
        for configured_range in sorted_known:
            r_counts.setdefault(configured_range, 0)

        if not r_counts:
            answer_callback(call["id"], "❌ No ranges found for this service and country!", show_alert=True)
            return
                    
        r_list = sorted(
            r_counts.items(),
            key=lambda item: (-item[1], -len(item[0]), item[0]),
        )[:12]
        
        kb = []
        temp_row = []
        for r, count in r_list:
            clean_r = str(r).replace("X", "").replace("x", "")
            temp_row.append({"text": f"{clean_r} ({count})", "icon_custom_emoji_id": "5352862640592949843", "callback_data": f"c_n_s_{clean_r}_{srv_query}", "style": "primary"})
            if len(temp_row) == 2:
                kb.append(temp_row)
                temp_row = []
        if temp_row:
            kb.append(temp_row)
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"exp_rng_{srv_query}", "style": "danger"}])
        
        app_full_name, prem_app_html = get_service_info_html(srv_query)
        prem_flag_html = get_flag_info_html(iso_query)
        
        edit_message(chat_id, msg_id, render_body_text(f"📊 <b>Ranges for {prem_app_html} {app_full_name} - {prem_flag_html} {iso_query}</b>\n\nClick on any range to copy it."), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data == "member_admin_management":
        edit_message(
            chat_id,
            msg_id,
            render_body_text("<b>MEMBER &amp; ADMIN MANAGEMENT</b>"),
            reply_markup=member_admin_management_keyboard(),
        )

    elif data == "user_management":
        edit_message(chat_id, msg_id, get_user_management_text(), reply_markup=user_management_keyboard())

    elif data.startswith("um_blocked_users_page_"):
        try:
            page = int(data.rsplit("_", 1)[-1])
        except (TypeError, ValueError):
            page = 0
        text, keyboard = get_blocked_users_page(page)
        edit_message(chat_id, msg_id, text, reply_markup=keyboard)

    elif data == "um_manage_balance":
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>'
                '<b>Balance Management</b> '
                '<tg-emoji emoji-id="6224139770683990463">🪙</tg-emoji>'
            ),
            reply_markup={"inline_keyboard": [
                [
                    {"text": "Add Balance", "icon_custom_emoji_id": "5420323438508155202",
                     "callback_data": "um_bal_add", "style": "success"},
                    {"text": "Remove Balance", "icon_custom_emoji_id": "5420130255174145507",
                     "callback_data": "um_bal_remove", "style": "danger"},
                ],
                [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                  "callback_data": "user_management", "style": "primary"}],
            ]},
        )

    elif data in ("um_bal_add", "um_bal_remove"):
        balance_action = "add" if data == "um_bal_add" else "remove"
        user_states[chat_id] = "wait_for_um_bal_uid"
        temp_data[chat_id] = {"msg_id": msg_id, "balance_action": balance_action}
        action_label = "ADD" if balance_action == "add" else "REMOVE"
        edit_message(
            chat_id,
            msg_id,
            render_body_text(f"📝 Send the User ID to {action_label} balance:"),
            reply_markup=get_cancel_kb(),
        )
        
    elif data == "um_ban_unban":
        user_states[chat_id] = "wait_for_um_ban_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to Ban or Unban:"), reply_markup=get_cancel_kb())

    elif data == "um_user_profile":
        user_states[chat_id] = "wait_for_um_prof_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to View Profile:"), reply_markup=get_cancel_kb())

    elif data == "menu_design_list":
        edit_message(chat_id, msg_id, render_body_text(f"🎨 <b>Menu Design Editor</b>\n\nSelect a menu block to edit its Body Text and Inline Buttons. You can use Premium Emojis too!"), reply_markup=menu_design_list_keyboard())

    elif data == "md_reset_defaults":
        bot_settings["custom_messages"] = DEFAULT_CUSTOM_MESSAGES.copy()
        save_db()
        answer_callback(call["id"], "✅ Resetted to Premium Defaults!", show_alert=True)

    elif data.startswith("md_edit_"):
        answer_callback(call["id"])
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        key = data.replace("md_edit_", "")
        cm_text = render_body_text(bot_settings["custom_messages"].get(key, {}).get("text", "..."))
        try:
            edit_message(chat_id, msg_id, render_body_text(f"🎨 <b>Editing: {key.upper()}</b>\n\nPreview of current Text:\n{cm_text}"), reply_markup=menu_edit_options_keyboard(key))
        except: pass

    elif data.startswith("md_text_"):
        key = data.replace("md_text_", "")
        user_states[chat_id] = "wait_for_menu_text"
        temp_data[chat_id] = {"msg_id": msg_id, "menu_key": key}
        edit_message(chat_id, msg_id, render_body_text(f"📝 <b>Edit Body: {key.upper()}</b>\n\nSend the new text. You can use Premium Emojis directly here.\n(Use standard HTML like <b>bold</b>, <i>italic</i> for formatting)"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_edit_{key}", "style": "danger"}]]})

    elif data.startswith("md_btns_"):
        answer_callback(call["id"]) 
        if chat_id in user_states: del user_states[chat_id] 
        if chat_id in temp_data: del temp_data[chat_id]
        key = data.replace("md_btns_", "")
        try:
            edit_message(chat_id, msg_id, render_body_text(f"⚙️ <b>Edit Inline Buttons: {key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(key))
        except: pass

    elif data.startswith("md_addbtn_"):
        key = data.replace("md_addbtn_", "")
        user_states[chat_id] = "wait_for_menu_btn"
        temp_data[chat_id] = {"msg_id": msg_id, "menu_key": key}
        edit_message(chat_id, msg_id, render_body_text(f"➕ <b>Add Button: {key.upper()}</b>\n\nSend custom button in this format:\n<code>Button Text - https://link.com</code>\n\n<i>(Only normal Emojis supported here!)</i>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_btns_{key}", "style": "danger"}]]})

    elif data.startswith("md_delbtn_"):
        parts = data.split("_")
        key = parts[2]
        b_idx = int(parts[3])
        if b_idx < len(bot_settings["custom_messages"][key]["buttons"]):
            del bot_settings["custom_messages"][key]["buttons"][b_idx]
            save_db()
            answer_callback(call["id"], "✅ Button Deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"⚙️ <b>Edit Inline Buttons: {key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(key))

    elif data.startswith("sel_wm_"):
        method = data.replace("sel_wm_", "")
        bal = get_user(chat_id).get('balance', 0.0)
        min_w = bot_settings['min_withdraw']
        
        if bal < min_w:
            answer_callback(call["id"])
            send_message(
                chat_id,
                render_body_text(
                    '<tg-emoji emoji-id="6221743402271121752">❌</tg-emoji> '
                    "Insufficient Balance! Minimum balance required."
                ),
            )
            return
            
        temp_data[chat_id] = {"method": method, "balance": bal}
        user_states[chat_id] = "wait_for_withdraw_amount"
        method_icon = withdrawal_method_emoji_html(method)
        method_prefix = f"{method_icon} " if method_icon else ""
        min_w_display = format_balance(min_w).rstrip("0").rstrip(".")
        amount_prompt = (
            f"{method_prefix}Method » <b>{html.escape(str(method))}</b>\n"
            '<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
            f"Available Balance » {format_balance(bal)} ৳\n"
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji> '
            f"Enter Amount » Minimum: {min_w_display} ৳ "
            '<tg-emoji emoji-id="6224139770683990463">🪙</tg-emoji>'
        )
        answer_callback(call["id"])
        send_message(
            chat_id,
            render_body_text(amount_prompt),
            reply_markup=get_cancel_kb(),
        )

    elif data == "test_message_flow":
        user_states[chat_id] = "wait_for_test_service"
        temp_data[chat_id] = {}
        edit_message(chat_id, msg_id, render_body_text("🧪 <b>Test Mode</b>\n\n📝 Send the Service Name (e.g., IG):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]]})

    elif data == "broadcast_msg":
        user_states[chat_id] = "wait_for_broadcast"
        edit_message(chat_id, msg_id, render_body_text("📢 <b>Broadcast Mode</b>\n\nSend the message you want to broadcast (Text, Photo, Video, File etc)."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]})

    elif data == "upload_num":
        user_states[chat_id] = "wait_for_txt"
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224124059693622546">📤</tg-emoji> '
                'Upload Your numbers .txt file '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
            ),
            reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]},
        )

    elif data == "delete_files":
        kb = []
        for b_id, b_data in number_batches.items():
            kb.append([{"text": f"{b_data['filename']} ({len(b_data['numbers'])})", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"del_b_{b_id}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "primary"}])
        txt = (
            '<tg-emoji emoji-id="6224501578729005740">📁</tg-emoji> '
            'Chose a file to delete '
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
            if len(kb) > 1 else f"{PEM['no']} No files found."
        )
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_b_"):
        b_id = data.split("del_b_")[1]
        if b_id in number_batches:
            del number_batches[b_id]
            save_db()
            answer_callback(call["id"], "✅ File deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "delete_files", "id": call["id"]})

    elif data == "show_used":
        kb = {"inline_keyboard": [[{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_used", "style": "primary"}], [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]}
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224284210434154938">🍏</tg-emoji> '
                f'Total Used Numbers '
                '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                f'{len(used_numbers_list)}'
            ),
            reply_markup=kb,
        )

    elif data == "show_unused":
        unused_count = sum(len(b["numbers"]) for b in number_batches.values())
        kb = {"inline_keyboard": [[{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_unused", "style": "primary"}], [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]}
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224284210434154938">🍏</tg-emoji> '
                f'Total Fresh Numbers '
                '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                f'{unused_count}'
            ),
            reply_markup=kb,
        )

    elif data == "dl_used":
        if not used_numbers_list:
            answer_callback(call["id"], "❌ No used numbers found!", show_alert=True)
            return
        content = "\n".join(used_numbers_list).encode('utf-8')
        send_document(chat_id, "used_numbers.txt", content)
        answer_callback(call["id"])

    elif data == "dl_unused":
        unused_list = [n["num"] for b in number_batches.values() for n in b["numbers"]]
        if not unused_list:
            answer_callback(call["id"], "❌ No unused numbers found!", show_alert=True)
            return
        content = "\n".join(unused_list).encode('utf-8')
        send_document(chat_id, "unused_numbers.txt", content)
        answer_callback(call["id"])

    elif data == "lb_main":
        txt = (
            "━━━━━━━━━━━━━━━━━━\n"
            '《 <tg-emoji emoji-id="6224240114004927438">📊</tg-emoji> '
            '<b>RANKING BOARD</b> '
            '<tg-emoji emoji-id="5337267511261960341">🔥</tg-emoji> 》\n'
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>Select a category to view the top performers or history.</i>\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        kb = [
            [{"text": "Top Referrers", "icon_custom_emoji_id": REFERRAL_EMOJI_ID, "callback_data": "lb_top_refs", "style": "primary"}],
            [{"text": "Top OTP Receivers", "icon_custom_emoji_id": UPLOAD_EMOJI_ID, "callback_data": "lb_top_otps", "style": "success"},
             {"text": "Withdrawal History", "icon_custom_emoji_id": "6224024626905753921", "callback_data": "lb_w_history", "style": "success"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("lb_"):
        sub = data.replace("lb_", "")
        history_page = 0
        if sub.startswith("w_history_page_"):
            try:
                history_page = max(0, int(sub.rsplit("_", 1)[1]))
            except (TypeError, ValueError):
                history_page = 0
            sub = "w_history"
        edit_message(chat_id, msg_id, render_body_text(
            loading_html("<i>Fetching Data...</i>")
        ))
        
        def get_p_num(n): return _premium_digit_text(n)

        def get_top_users(field, limit):
            """Rank positive counts numerically, including legacy string values."""
            ranked = []
            for snapshot in db.collection("users").stream():
                data = snapshot.to_dict() or {}
                value = _as_number(data.get(field), 0)
                if value > 0:
                    ranked.append((value, snapshot, data))
            ranked.sort(
                key=lambda item: (item[0], str(item[1].id)),
                reverse=True,
            )
            return ranked[:limit]
        
        try:
            if sub == "top_refs":
                title, field, limit, icon = "TOP 5 REFERRERS", "total_refers", 5, PEM.get('user', '👥')
                users = get_top_users(field, limit)
                res_txt = ""
                count = 1
                for value, u, d in users:
                    p = "└" if count == len(users) else "├"
                    user_id = html.escape(str(u.id), quote=True)
                    res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={user_id}'><b>{user_id}</b></a> ➔ <b>{value}</b>\n"
                    count += 1
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "top_otps":
                title, field, limit, icon = "TOP 5 OTP RECEIVERS", "total_otps", 5, PEM.get('msg', '📩')
                users = get_top_users(field, limit)
                res_txt = ""
                count = 1
                for value, u, d in users:
                    p = "└" if count == len(users) else "├"
                    user_id = html.escape(str(u.id), quote=True)
                    res_txt += f"{p} {get_p_num(count)} <a href='tg://user?id={user_id}'><b>{user_id}</b></a> ➔ <b>{value}</b>\n"
                    count += 1
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "w_history":
                page_size = 10
                all_withdrawals = [
                    snapshot for snapshot in (
                    db.collection('withdrawals')
                    .order_by('timestamp', direction="DESCENDING")
                    .stream()
                    )
                    if str(
                        (snapshot.to_dict() or {}).get("status", "pending")
                    ).strip().casefold() in ("pending", "")
                ]
                page_count = max(1, (len(all_withdrawals) + page_size - 1) // page_size)
                history_page = min(history_page, page_count - 1)
                title = (
                    "WITHDRAWAL HISTORY ⌛ · PAGE "
                    f"{_premium_digit_text(history_page + 1)}/"
                    f"{_premium_digit_text(page_count)}"
                )
                icon = "🙋"
                page_start = history_page * page_size
                ws = all_withdrawals[page_start:page_start + page_size]
                res_txt = ""
                kb = []
                active_serials = _pending_withdrawal_serials()
                for page_index, w in enumerate(ws, start=page_start + 1):
                    d = w.to_dict()
                    s = str(d.get('status', 'Pending')).strip().lower()
                    stat_icon = PEM.get('ok','✅') if s in ["approved","success"] else PEM.get('no','❌') if s=="rejected" else "⏳"
                    uid = d.get('user_id','User')
                    req_id = str(d.get("request_id") or w.id)
                    display_serial = active_serials.get(req_id, page_index)
                    display_request_id = f"#{display_serial}"
                    display_request_id_html = f"#{_premium_digit_text(display_serial)}"
                    method = html.escape(str(d.get("method", "Unknown")))
                    payment_number = html.escape(str(d.get("number", "Unknown")))
                    amount_text = html.escape(str(d.get("amount", 0)))
                    p = "└" if page_index == page_start + len(ws) else "├"
                    res_txt += (
                        f"{p} {get_p_num(page_index)} "
                        f"<a href='tg://user?id={html.escape(str(uid))}'>{html.escape(str(uid))}</a> "
                        f"➔ <b>{amount_text}৳</b> · "
                        f"{method} · <code>{payment_number}</code> {stat_icon} "
                        f"{display_request_id_html}\n"
                    )
                    if s in ("pending", "") and re.fullmatch(r"[A-Za-z0-9_-]{1,50}", req_id):
                        digit_icon = PREMIUM_DIGIT_EMOJI_IDS.get(
                            str(display_serial)[0],
                            PREMIUM_DIGIT_EMOJI_IDS["1"],
                        )
                        kb.append([{
                            "text": f"ID: {display_request_id}",
                            "icon_custom_emoji_id": digit_icon,
                            "callback_data": "ignore",
                            "style": "primary",
                        }])
                        kb.append([
                            {"text": f"✅ Approve {display_request_id}", "icon_custom_emoji_id": "6224188445548356446", "callback_data": f"wapp_{req_id}_hist_{history_page}", "style": "success"},
                            {"text": f"❌ Reject {display_request_id}", "icon_custom_emoji_id": "6224003980997962148", "callback_data": f"wrej_{req_id}_hist_{history_page}", "style": "danger"},
                        ])
                if not res_txt: res_txt = "└ <i>No history found.</i>\n"
                page_navigation = []
                if history_page > 0:
                    page_navigation.append({
                        "text": "⬅️ Previous",
                        "callback_data": f"lb_w_history_page_{history_page - 1}",
                        "style": "primary",
                    })
                if history_page + 1 < page_count:
                    page_navigation.append({
                        "text": "Next ➡️",
                        "callback_data": f"lb_w_history_page_{history_page + 1}",
                        "style": "primary",
                    })
                if page_navigation:
                    kb.append(page_navigation)

            final_msg = f"━━━━━━━━━━━━━━━\n{icon} <b>{title}</b>\n━━━━━━━━━━━━━━━\n{res_txt}━━━━━━━━━━━━━━━"
            if sub != "w_history":
                kb = []
            kb.append([
                {"text": "Refresh", "icon_custom_emoji_id": "6224477342228565523", "callback_data": (
                    f"lb_w_history_page_{history_page}" if sub == "w_history" and history_page > 0
                    else "lb_w_history" if sub == "w_history" else data
                ), "style": "success"},
                {"text": "Close", "icon_custom_emoji_id": CROSS_CANCEL_EMOJI_ID, "callback_data": (
                    "system_settings" if sub == "w_history" else "lb_main"
                ), "style": "danger"},
            ])
            edit_message(chat_id, msg_id, render_body_text(final_msg), reply_markup={"inline_keyboard": kb})

        except Exception as e:
            edit_message(chat_id, msg_id, render_body_text(f"❌ Error: {e}"), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]})

    elif data == "back_to_number_management":
        answer_callback(call["id"])
        send_message(
            chat_id,
            render_body_text("<b>NUMBER MANAGEMENT</b>"),
            reply_markup=number_management_keyboard(),
        )

    elif data == "back_to_delete_management":
        answer_callback(call["id"])
        send_message(
            chat_id,
            render_body_text("<b>DELETE MANAGEMENT</b>"),
            reply_markup=delete_management_keyboard(),
        )

    elif data == "back_to_admin":
        if chat_id in user_states: del user_states[chat_id]
        temp_data.pop(chat_id, None)
        answer_callback(call["id"])
        # Keep the current reply-keyboard message until its replacement is
        # sent. Deleting it first makes Telegram briefly fall back to Gboard.
        send_admin_panel(chat_id)

    elif data == "toggle_join_notify":
        if not is_admin(chat_id):
            answer_callback(call["id"], "🚫 Admin only.", show_alert=True)
            return
        settings = bot_settings.setdefault("join_notifications", {})
        admin_key = str(chat_id)
        settings[admin_key] = not get_join_notification_status(chat_id)
        save_db()
        # Update the existing inline menu in place; no notification message or
        # popup is sent, and the label/color immediately reflects the setting.
        answer_callback(call["id"])
        edit_message(
            chat_id,
            msg_id,
            render_body_text(
                '<tg-emoji emoji-id="5370935802844946281">⚙️</tg-emoji> '
                '<b>SYSTEM MANAGEMENT</b> '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ),
            reply_markup=system_settings_keyboard(chat_id),
        )
        
    elif data == "system_settings":
        send_system_settings(chat_id, replace_message_id=msg_id)

    elif data == "fastx_control":
        fastx_keys = bot_settings.get("fastx_keys", [])
        if isinstance(fastx_keys, str):
            fastx_keys = [fastx_keys]
        effective_count = len([key for key in fastx_keys if str(key).strip()])
        if not effective_count and os.getenv("FASTXOTP_API_KEY", "").strip():
            effective_count = 1
        edit_message(
            chat_id, msg_id,
            render_body_text(service_control_panel_text(
                "FastX", effective_count, "6199291250277885056", "⚡"
            )),
            reply_markup=fastx_control_keyboard(),
        )

    elif data == "toggle_fastx_auto":
        bot_settings["fastx_auto"] = not bot_settings.get("fastx_auto", False)
        save_db()
        if bot_settings["fastx_auto"]:
            threading.Thread(
                target=_refresh_fastx_live_ranges_now,
                daemon=True,
            ).start()
        status = "ON" if bot_settings["fastx_auto"] else "OFF"
        answer_callback(call["id"], f"✅ FastX Auto Range is now {status}.")
        fastx_keys = bot_settings.get("fastx_keys", [])
        if isinstance(fastx_keys, str):
            fastx_keys = [fastx_keys]
        effective_count = len([key for key in fastx_keys if str(key).strip()])
        if not effective_count and os.getenv("FASTXOTP_API_KEY", "").strip():
            effective_count = 1
        edit_message(
            chat_id, msg_id,
            render_body_text(service_control_panel_text(
                "FastX", effective_count, "6199291250277885056", "⚡"
            )),
            reply_markup=fastx_control_keyboard(),
        )

    elif data == "fastx_search_country":
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224383737711305101">🚫</tg-emoji> '
                'Allowed Country Code List '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ),
            reply_markup=fastx_search_country_keyboard(),
        )

    elif data == "add_fastx_search_country":
        user_states[chat_id] = "wait_for_add_fx_sc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(
            chat_id, msg_id,
            render_body_text("📝 Send a numeric country/range code (for example, 880):"),
            reply_markup={"inline_keyboard": [[{
                "text": "Cancel",
                "icon_custom_emoji_id": CROSS_CANCEL_EMOJI_ID,
                "callback_data": "fastx_search_country",
                "style": "danger",
            }]]},
        )

    elif data.startswith("fx_del_sc_"):
        try:
            index = int(data.rsplit("_", 1)[1])
        except ValueError:
            index = -1
        countries = bot_settings.get("fastx_search_countries", [])
        if isinstance(countries, list) and 0 <= index < len(countries):
            del countries[index]
            save_db()
            answer_callback(call["id"], "✅ FastX country code deleted.")
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6224383737711305101">🚫</tg-emoji> '
                'Allowed Country Code List '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ),
            reply_markup=fastx_search_country_keyboard(),
        )

    elif data == "manage_fastx_srv":
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6199291250277885056">⚡</tg-emoji> '
                'Manage Your FastX Service Below '
                '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
            ),
            reply_markup=fastx_services_keyboard(),
        )

    elif data == "fx_add_srv":
        user_states[chat_id] = "wait_fx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(
            chat_id, msg_id,
            render_body_text("📝 Enter the FastX service name (for example, TELEGRAM):"),
            reply_markup=get_cancel_kb(),
        )

    elif data.startswith("fx_srv_"):
        try:
            service_index = int(data.rsplit("_", 1)[1])
        except ValueError:
            service_index = -1
        services = bot_settings.get("fastx_services", {})
        service_names = list(services) if isinstance(services, dict) else []
        if not 0 <= service_index < len(service_names):
            answer_callback(call["id"], "❌ FastX service not found.", show_alert=True)
            return
        service_name = service_names[service_index]
        countries = services.get(service_name, {})
        country_count = len(countries) if isinstance(countries, dict) else 0
        edit_message(
            chat_id, msg_id,
            render_body_text(
                f"📂 <b>FastX Service: {html.escape(str(service_name))}</b>\n"
                f"Configured countries: {country_count}"
            ),
            reply_markup=fastx_service_countries_keyboard(service_index),
        )

    elif data.startswith("fx_add_cnt_"):
        try:
            service_index = int(data.rsplit("_", 1)[1])
        except ValueError:
            service_index = -1
        services = bot_settings.get("fastx_services", {})
        service_names = list(services) if isinstance(services, dict) else []
        if not 0 <= service_index < len(service_names):
            answer_callback(call["id"], "❌ FastX service not found.", show_alert=True)
            return
        user_states[chat_id] = "wait_fx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "service_index": service_index}
        edit_message(
            chat_id, msg_id,
            render_body_text(
                f"🌍 Enter a country name for "
                f"<b>{html.escape(str(service_names[service_index]))}</b>:"
            ),
            reply_markup=get_cancel_kb(),
        )

    elif data.startswith("fx_cnt_"):
        try:
            _, _, service_value, country_value = data.split("_", 3)
            service_index = int(service_value)
            country_index = int(country_value)
        except ValueError:
            answer_callback(call["id"], "❌ Invalid FastX country.", show_alert=True)
            return
        services = bot_settings.get("fastx_services", {})
        service_names = list(services) if isinstance(services, dict) else []
        if not 0 <= service_index < len(service_names):
            answer_callback(call["id"], "❌ FastX service not found.", show_alert=True)
            return
        service_name = service_names[service_index]
        countries = services.get(service_name, {})
        country_names = list(countries) if isinstance(countries, dict) else []
        if not 0 <= country_index < len(country_names):
            answer_callback(call["id"], "❌ FastX country not found.", show_alert=True)
            return
        country_name = country_names[country_index]
        ranges = countries.get(country_name, [])
        range_count = len(ranges) if isinstance(ranges, list) else 1
        edit_message(
            chat_id, msg_id,
            render_body_text(
                f"📍 <b>{html.escape(str(service_name))} · "
                f"{html.escape(str(country_name))}</b>\n"
                f"Total ranges: {range_count}\n"
                "Tap a range to delete it or add another."
            ),
            reply_markup=fastx_service_ranges_keyboard(service_index, country_index),
        )

    elif data.startswith("fx_addr_"):
        try:
            _, _, service_value, country_value = data.split("_", 3)
            service_index = int(service_value)
            country_index = int(country_value)
        except ValueError:
            answer_callback(call["id"], "❌ Invalid FastX country.", show_alert=True)
            return
        user_states[chat_id] = "wait_fx_addr"
        temp_data[chat_id] = {
            "msg_id": msg_id,
            "service_index": service_index,
            "country_index": country_index,
        }
        edit_message(
            chat_id, msg_id,
            render_body_text("📝 Send a FastX range (for example, 88017 or 88017XXX):"),
            reply_markup=get_cancel_kb(),
        )

    elif data.startswith("fx_dr_"):
        try:
            _, _, service_value, country_value, range_value = data.split("_", 4)
            service_index = int(service_value)
            country_index = int(country_value)
            range_index = int(range_value)
        except ValueError:
            answer_callback(call["id"], "❌ Invalid FastX range.", show_alert=True)
            return
        services = bot_settings.get("fastx_services", {})
        service_names = list(services) if isinstance(services, dict) else []
        if 0 <= service_index < len(service_names):
            countries = services.get(service_names[service_index], {})
            country_names = list(countries) if isinstance(countries, dict) else []
            if 0 <= country_index < len(country_names):
                ranges = countries.get(country_names[country_index], [])
                if not isinstance(ranges, list):
                    ranges = [ranges]
                if 0 <= range_index < len(ranges):
                    removed_range = ranges.pop(range_index)
                    countries[country_names[country_index]] = ranges
                    save_db()
                    answer_callback(call["id"], f"✅ Range {removed_range} deleted.")
        handle_callback({
            "message": {"chat": {"id": chat_id}, "message_id": msg_id},
            "data": f"fx_cnt_{service_index}_{country_index}",
            "id": call["id"],
        })

    elif data.startswith("fx_del_srv_"):
        try:
            service_index = int(data.rsplit("_", 1)[1])
        except ValueError:
            service_index = -1
        services = bot_settings.get("fastx_services", {})
        service_names = list(services) if isinstance(services, dict) else []
        if 0 <= service_index < len(service_names):
            removed_service = service_names[service_index]
            del services[removed_service]
            save_db()
            answer_callback(call["id"], "✅ FastX service deleted.")
        handle_callback({
            "message": {"chat": {"id": chat_id}, "message_id": msg_id},
            "data": "manage_fastx_srv",
            "id": call["id"],
        })

    elif data.startswith("fx_del_cnt_"):
        try:
            _, _, _, service_value, country_value = data.split("_", 4)
            service_index = int(service_value)
            country_index = int(country_value)
        except ValueError:
            answer_callback(call["id"], "❌ Invalid FastX country.", show_alert=True)
            return
        services = bot_settings.get("fastx_services", {})
        service_names = list(services) if isinstance(services, dict) else []
        if 0 <= service_index < len(service_names):
            countries = services.get(service_names[service_index], {})
            country_names = list(countries) if isinstance(countries, dict) else []
            if 0 <= country_index < len(country_names):
                del countries[country_names[country_index]]
                save_db()
                answer_callback(call["id"], "✅ FastX country deleted.")
        handle_callback({
            "message": {"chat": {"id": chat_id}, "message_id": msg_id},
            "data": f"fx_srv_{service_index}",
            "id": call["id"],
        })

    elif data == "add_fastx_key":
        user_states[chat_id] = "wait_for_add_fastx_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(
            chat_id, msg_id,
            render_body_text("📝 Send the FastXOTP API key:"),
            reply_markup={"inline_keyboard": [[
                {"text": "Cancel", "icon_custom_emoji_id": CROSS_CANCEL_EMOJI_ID,
                 "callback_data": "fastx_control", "style": "danger"}
            ]]},
        )

    elif data == "view_fastx_keys":
        keys = bot_settings.get("fastx_keys", [])
        if isinstance(keys, str):
            keys = [keys]
        kb = []
        for idx, key in enumerate(keys):
            safe_name = str(key)[:10] + ("…" if len(str(key)) > 10 else "")
            kb.append([{
                "text": f"Delete {safe_name}",
                "icon_custom_emoji_id": CROSS_CANCEL_EMOJI_ID,
                "callback_data": f"del_fastx_key_{idx}",
                "style": "danger",
            }])
        if not kb:
            kb.append([{
                "text": "No saved keys",
                "icon_custom_emoji_id": "5420130255174145507",
                "callback_data": "ignore",
                "style": "primary",
            }])
        kb.append([{
            "text": "Back",
            "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID,
            "callback_data": "fastx_control",
            "style": "primary",
        }])
        edit_message(
            chat_id, msg_id,
            render_body_text("🗑 <b>FastX API Keys</b>\nTap a key to remove it:"),
            reply_markup={"inline_keyboard": kb},
        )

    elif data.startswith("del_fastx_key_"):
        try:
            idx = int(data.rsplit("_", 1)[1])
        except ValueError:
            idx = -1
        keys = bot_settings.get("fastx_keys", [])
        if isinstance(keys, str):
            keys = [keys]
        if 0 <= idx < len(keys):
            del keys[idx]
            bot_settings["fastx_keys"] = keys
            save_db()
            answer_callback(call["id"], "✅ FastX key deleted.", show_alert=True)
            handle_callback({
                "message": {"chat": {"id": chat_id}, "message_id": msg_id},
                "data": "view_fastx_keys",
                "id": call["id"],
            })

    elif data == "toggle_demo":
        if not is_admin(chat_id):
            answer_callback(call["id"], "🚫 Admin only.", show_alert=True)
            return
        bot_settings["demo_on"] = not bot_settings.get("demo_on", False)
        save_db()
        status = "ON ✅" if bot_settings["demo_on"] else "OFF ❌"
        answer_callback(call["id"], f"Demo SMS Forwarder: {status}", show_alert=True)
        send_system_settings(chat_id, replace_message_id=msg_id)

    elif data == "set_demo_interval":
        if not is_admin(chat_id):
            answer_callback(call["id"], "🚫 Admin only.", show_alert=True)
            return
        user_states[chat_id] = "wait_for_demo_interval"
        temp_data[chat_id] = {"msg_id": msg_id}
        answer_callback(call["id"], "Send the interval in seconds.")
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6222241944894971888">➡️</tg-emoji> '
                '<b>Set Demo SMS Time</b> '
                '<tg-emoji emoji-id="6226733922340842081">⏳</tg-emoji>\n'
                '<tg-emoji emoji-id="6222073659486381042">📝</tg-emoji> '
                'Send Any Number Start 1 to 10000 '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>'
            ),
            reply_markup=get_cancel_kb(),
        )

    elif data == "stex_control":
        edit_message(chat_id, msg_id, render_body_text(service_control_panel_text(
            "StexSMS", len(bot_settings.get("stex_keys", [])),
            "6226471972285458398", "⚡"
        )), reply_markup=stex_control_keyboard())
    
    elif data == "toggle_stex_auto":
        bot_settings["stex_auto"] = not bot_settings.get("stex_auto", False)
        save_db()
        edit_message(chat_id, msg_id, render_body_text(service_control_panel_text(
            "StexSMS", len(bot_settings.get("stex_keys", [])),
            "6226471972285458398", "⚡"
        )), reply_markup=stex_control_keyboard())
        answer_callback(call["id"], f"✅ Stex Auto Range is now {'ON' if bot_settings['stex_auto'] else 'OFF'}!", show_alert=False)

    elif data == "add_stex_key":
        user_states[chat_id] = "wait_for_add_stex_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new StexSMS API Key (e.g. nxa_...):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "danger"}]]})

    elif data == "view_stex_keys":
        kb = []
        for idx, key in enumerate(bot_settings.get("stex_keys", [])):
            safe_name = key[:10] + "..." if len(key)>10 else key
            kb.append([{"text": f"Delete {safe_name}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_nxa_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🗑 <b>Select StexSMS Key to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_nxa_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("stex_keys", [])):
            del bot_settings["stex_keys"][idx]
            save_db()
            answer_callback(call["id"], "✅ StexSMS Key Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "view_stex_keys", "id": call["id"]})

    elif data == "stex_search_country":
        country_buttons = []
        for idx, c in enumerate(bot_settings.get("search_countries", [])):
            country_buttons.append({"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_sc_{idx}", "style": "danger"})
        kb = grouped_keyboard_rows(country_buttons, 4)
        kb.append([{"text": "Add Country Code", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_search_country", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6224383737711305101">🚫</tg-emoji> '
            'Allowed Country Code List '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
        ), reply_markup={"inline_keyboard": kb})

    elif data == "add_search_country":
        user_states[chat_id] = "wait_for_add_sc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Country Code (e.g. 880 or 92):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_search_country", "style": "danger"}]]})

    elif data.startswith("del_sc_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("search_countries", [])):
            del bot_settings["search_countries"][idx]
            save_db()
            answer_callback(call["id"], "✅ Country Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "stex_search_country", "id": call["id"]})

    elif data == "manage_stex_srv":
        kb = []
        srvs = bot_settings.get("stex_services", {})
        apps_db = bot_settings.get("premium_apps", {})
        for srv in srvs:
            emoji_id = "5257969839313526622"
            for app_key, app_data in apps_db.items():
                if srv.upper() == app_key or srv.upper() in app_key or app_key in srv.upper():
                    if "id" in app_data:
                        emoji_id = app_data["id"]
                        break
            kb.append([{"text": f"{srv}", "icon_custom_emoji_id": emoji_id, "callback_data": f"nx_srv_{srv}", "style": "primary"}])
        kb.append([{"text": "Add New Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "nx_add_srv", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "stex_control", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6226471972285458398">⚡</tg-emoji> '
            'Manage Your Stex Service Below '
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
        ), reply_markup={"inline_keyboard": kb})

    elif data == "nx_add_srv":
        user_states[chat_id] = "wait_nx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter Service Name (e.g. TELEGRAM):"), reply_markup=get_cancel_kb())

    elif data.startswith("nx_srv_"):
        srv = data.replace("nx_srv_", "")
        kb = []
        countries = bot_settings["stex_services"].get(srv, {})
        flags_db = bot_settings.get("premium_flags", {})
        for c in countries:
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                iso = flag_data.get("iso", "").upper()
                name = flag_data.get("name", "").upper()
                if c.upper() == iso or c.upper() == name or c.upper() in name or name in c.upper():
                    if "id" in flag_data:
                        emoji_id = flag_data["id"]
                        break
            kb.append([{"text": f"{c} ({len(countries[c])} Ranges)", "icon_custom_emoji_id": emoji_id, "callback_data": f"nx_cnt_{srv}_{c}", "style": "primary"}])
        kb.append([{"text": "Add Country", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"nx_add_cnt_{srv}", "style": "success"}])
        kb.append([{"text": "Delete Service", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"nx_del_srv_{srv}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_stex_srv", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📂 <b>Service: {srv}</b>\nManage countries for this service:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("nx_add_cnt_"):
        srv = data.replace("nx_add_cnt_", "")
        user_states[chat_id] = "wait_nx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv}
        edit_message(chat_id, msg_id, render_body_text(f"🌍 Enter Country Name for <b>{srv}</b> (e.g. BD, INDIA):"), reply_markup=get_cancel_kb())

    elif data.startswith("nx_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        ranges = bot_settings["stex_services"][srv].get(cnt, [])
        
        kb = []
        row = []
        for r in ranges:
            row.append({"text": f"Delete {r}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"nx_dr_{srv}_{cnt}_{r}", "style": "danger"})
            if len(row) == 2:
                kb.append(row)
                row = []
        if row: kb.append(row)
        
        kb.append([{"text": "Add Range", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"nx_addr_{srv}_{cnt}", "style": "success"}])
        kb.append([{"text": "Delete Entire Country", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"nx_del_cnt_{srv}_{cnt}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"nx_srv_{srv}", "style": "primary"}])
        
        txt = f"📍 <b>Service: {srv} | Country: {cnt}</b>\n\n<b>Total Ranges:</b> {len(ranges)}\n<i>Click on a range below to delete it, or add a new one.</i>"
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("nx_addr_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        user_states[chat_id] = "wait_nx_addr"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv, "cnt": cnt}
        edit_message(chat_id, msg_id, render_body_text(f"📝 Send the new Range for <b>{cnt}</b> (e.g. 88017):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"nx_cnt_{srv}_{cnt}", "style": "danger"}]]})

    elif data.startswith("nx_dr_"):
        parts = data.split("_")
        srv, cnt, rng = parts[2], parts[3], parts[4]
        if rng in bot_settings["stex_services"].get(srv, {}).get(cnt, []):
            bot_settings["stex_services"][srv][cnt].remove(rng)
            save_db()
            answer_callback(call["id"], f"✅ Range {rng} deleted!", show_alert=True)
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"nx_cnt_{srv}_{cnt}", "id": call["id"]})

    elif data.startswith("nx_del_srv_"):
        srv = data.replace("nx_del_srv_", "")
        if srv in bot_settings["stex_services"]: del bot_settings["stex_services"][srv]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_stex_srv", "id": call["id"]})

    elif data.startswith("nx_del_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[3], parts[4]
        if cnt in bot_settings["stex_services"].get(srv, {}): del bot_settings["stex_services"][srv][cnt]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"nx_srv_{srv}", "id": call["id"]})

    elif data == "voltx_control":
        edit_message(chat_id, msg_id, render_body_text(service_control_panel_text(
            "Voltx", len(bot_settings.get("voltx_keys", [])),
            "6226471972285458398", "⚡"
        )), reply_markup=voltx_control_keyboard())

    elif data == "toggle_voltx_auto":
        bot_settings["voltx_auto"] = not bot_settings.get("voltx_auto", False)
        save_db()
        edit_message(chat_id, msg_id, render_body_text(service_control_panel_text(
            "Voltx", len(bot_settings.get("voltx_keys", [])),
            "6226471972285458398", "⚡"
        )), reply_markup=voltx_control_keyboard())
        answer_callback(call["id"], f"✅ Voltx Auto Range is now {'ON' if bot_settings['voltx_auto'] else 'OFF'}!", show_alert=False)

    elif data == "add_voltx_key":
        user_states[chat_id] = "wait_for_add_voltx_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new Voltx API Key:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "danger"}]]})

    elif data == "view_voltx_keys":
        kb = []
        for idx, key in enumerate(bot_settings.get("voltx_keys", [])):
            safe_name = key[:10] + "..." if len(key)>10 else key
            kb.append([{"text": f"Delete {safe_name}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_vtx_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🗑 <b>Select Voltx Key to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_vtx_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("voltx_keys", [])):
            del bot_settings["voltx_keys"][idx]
            save_db()
            answer_callback(call["id"], "✅ Voltx Key Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "view_voltx_keys", "id": call["id"]})

    elif data == "voltx_search_country":
        country_buttons = []
        for idx, c in enumerate(bot_settings.get("voltx_search_countries", [])):
            country_buttons.append({"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_vsc_{idx}", "style": "danger"})
        kb = grouped_keyboard_rows(country_buttons, 4)
        kb.append([{"text": "Add Country Code", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_voltx_search_country", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6224383737711305101">🚫</tg-emoji> '
            'Allowed Country Code List '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
        ), reply_markup={"inline_keyboard": kb})

    elif data == "add_voltx_search_country":
        user_states[chat_id] = "wait_for_add_vsc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Voltx Range Code (e.g. 26134):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_search_country", "style": "danger"}]]})

    elif data.startswith("del_vsc_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("voltx_search_countries", [])):
            del bot_settings["voltx_search_countries"][idx]
            save_db()
            answer_callback(call["id"], "✅ Voltx Range Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "voltx_search_country", "id": call["id"]})

    elif data == "manage_voltx_srv":
        kb = []
        srvs = bot_settings.get("voltx_services", {})
        apps_db = bot_settings.get("premium_apps", {})
        for srv in srvs:
            emoji_id = "5257969839313526622"
            for app_key, app_data in apps_db.items():
                if srv.upper() == app_key or srv.upper() in app_key or app_key in srv.upper():
                    if "id" in app_data: emoji_id = app_data["id"]; break
            kb.append([{"text": f"{srv}", "icon_custom_emoji_id": emoji_id, "callback_data": f"vx_srv_{srv}", "style": "primary"}])
        kb.append([{"text": "Add New Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "vx_add_srv", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "voltx_control", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6226471972285458398">⚡</tg-emoji> '
            'Manage Your Voltx Service Below '
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
        ), reply_markup={"inline_keyboard": kb})

    elif data == "vx_add_srv":
        user_states[chat_id] = "wait_vx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter Service Name (e.g. TELEGRAM):"), reply_markup=get_cancel_kb())

    elif data.startswith("vx_srv_"):
        srv = data.replace("vx_srv_", "")
        kb = []
        countries = bot_settings["voltx_services"].get(srv, {})
        flags_db = bot_settings.get("premium_flags", {})
        for c in countries:
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                iso = flag_data.get("iso", "").upper()
                name = flag_data.get("name", "").upper()
                if c.upper() == iso or c.upper() == name or c.upper() in name or name in c.upper():
                    if "id" in flag_data: emoji_id = flag_data["id"]; break
            kb.append([{"text": f"{c} ({len(countries[c])} Ranges)", "icon_custom_emoji_id": emoji_id, "callback_data": f"vx_cnt_{srv}_{c}", "style": "primary"}])
        kb.append([{"text": "Add Country", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"vx_add_cnt_{srv}", "style": "success"}])
        kb.append([{"text": "Delete Service", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"vx_del_srv_{srv}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_voltx_srv", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📂 <b>Service: {srv}</b>\nManage countries for this service:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("vx_add_cnt_"):
        srv = data.replace("vx_add_cnt_", "")
        user_states[chat_id] = "wait_vx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv}
        edit_message(chat_id, msg_id, render_body_text(f"🌍 Enter Country Name for <b>{srv}</b> (e.g. BD, INDIA):"), reply_markup=get_cancel_kb())

    elif data.startswith("vx_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        ranges = bot_settings["voltx_services"][srv].get(cnt, [])
        kb = []
        row = []
        for r in ranges:
            row.append({"text": f"Delete {r}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"vx_dr_{srv}_{cnt}_{r}", "style": "danger"})
            if len(row) == 2:
                kb.append(row)
                row = []
        if row: kb.append(row)
        kb.append([{"text": "Add Range", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"vx_addr_{srv}_{cnt}", "style": "success"}])
        kb.append([{"text": "Delete Entire Country", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"vx_del_cnt_{srv}_{cnt}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"vx_srv_{srv}", "style": "primary"}])
        txt = f"📍 <b>Service: {srv} | Country: {cnt}</b>\n\n<b>Total Ranges:</b> {len(ranges)}\n<i>Click on a range below to delete it, or add a new one.</i>"
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("vx_addr_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        user_states[chat_id] = "wait_vx_addr"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv, "cnt": cnt}
        edit_message(chat_id, msg_id, render_body_text(f"📝 Send the new Range for <b>{cnt}</b> (e.g. 26134):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"vx_cnt_{srv}_{cnt}", "style": "danger"}]]})

    elif data.startswith("vx_dr_"):
        parts = data.split("_")
        srv, cnt, rng = parts[2], parts[3], parts[4]
        if rng in bot_settings["voltx_services"].get(srv, {}).get(cnt, []):
            bot_settings["voltx_services"][srv][cnt].remove(rng)
            save_db()
            answer_callback(call["id"], f"✅ Range {rng} deleted!", show_alert=True)
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"vx_cnt_{srv}_{cnt}", "id": call["id"]})

    elif data.startswith("vx_del_srv_"):
        srv = data.replace("vx_del_srv_", "")
        if srv in bot_settings["voltx_services"]: del bot_settings["voltx_services"][srv]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_voltx_srv", "id": call["id"]})

    elif data.startswith("vx_del_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[3], parts[4]
        if cnt in bot_settings["voltx_services"].get(srv, {}): del bot_settings["voltx_services"][srv][cnt]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"vx_srv_{srv}", "id": call["id"]})

    elif data == "zenex_control":
        edit_message(chat_id, msg_id, render_body_text(service_control_panel_text(
            "Zenex", len(bot_settings.get("zenex_keys", [])),
            "6199291250277885056", "💠"
        )), reply_markup=zenex_control_keyboard())

    elif data == "toggle_zenex_auto":
        bot_settings["zenex_auto"] = not bot_settings.get("zenex_auto", False)
        save_db()
        edit_message(chat_id, msg_id, render_body_text(service_control_panel_text(
            "Zenex", len(bot_settings.get("zenex_keys", [])),
            "6199291250277885056", "💠"
        )), reply_markup=zenex_control_keyboard())
        answer_callback(call["id"], f"✅ Zenex Auto Range is now {'ON' if bot_settings['zenex_auto'] else 'OFF'}!", show_alert=False)

    elif data == "add_zenex_key":
        user_states[chat_id] = "wait_for_add_zenex_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new Zenex API Key:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "zenex_control", "style": "danger"}]]})

    elif data == "view_zenex_keys":
        kb = []
        for idx, key in enumerate(bot_settings.get("zenex_keys", [])):
            safe_name = key[:10] + "..." if len(key)>10 else key
            kb.append([{"text": f"Delete {safe_name}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_znx_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "zenex_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("🗑 <b>Select Zenex Key to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_znx_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("zenex_keys", [])):
            del bot_settings["zenex_keys"][idx]
            save_db()
            answer_callback(call["id"], "✅ Zenex Key Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "view_zenex_keys", "id": call["id"]})

    elif data == "zenex_search_country":
        country_buttons = []
        for idx, c in enumerate(bot_settings.get("zenex_search_countries", [])):
            country_buttons.append({"text": f"Delete {c}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_zsc_{idx}", "style": "danger"})
        kb = grouped_keyboard_rows(country_buttons, 4)
        kb.append([{"text": "Add Country Code", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_zenex_search_country", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "zenex_control", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6224383737711305101">🚫</tg-emoji> '
            'Allowed Country Code List '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
        ), reply_markup={"inline_keyboard": kb})

    elif data == "add_zenex_search_country":
        user_states[chat_id] = "wait_for_add_zsc"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Zenex Range Code (e.g. 447):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "zenex_search_country", "style": "danger"}]]})

    elif data.startswith("del_zsc_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings.get("zenex_search_countries", [])):
            del bot_settings["zenex_search_countries"][idx]
            save_db()
            answer_callback(call["id"], "✅ Zenex Range Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "zenex_search_country", "id": call["id"]})

    elif data == "manage_zenex_srv":
        kb = []
        for srv in bot_settings.get("zenex_services", {}):
            kb.append([{"text": f"{srv}", "icon_custom_emoji_id": "5257969839313526622", "callback_data": f"zx_srv_{srv}", "style": "primary"}])
        kb.append([{"text": "Add New Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "zx_add_srv", "style": "success"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "zenex_control", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6199291250277885056">💠</tg-emoji> '
            'Manage Your Zenex Service Below '
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
        ), reply_markup={"inline_keyboard": kb})

    elif data == "zx_add_srv":
        user_states[chat_id] = "wait_zx_srv_name"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter Service Name (e.g. TELEGRAM):"), reply_markup=get_cancel_kb())

    elif data.startswith("zx_srv_"):
        srv = data.replace("zx_srv_", "")
        kb = []
        for c in bot_settings.get("zenex_services", {}).get(srv, {}):
            kb.append([{"text": f"{c} ({len(bot_settings['zenex_services'][srv][c])} Ranges)", "icon_custom_emoji_id": "5780471598922337683", "callback_data": f"zx_cnt_{srv}_{c}", "style": "primary"}])
        kb.append([{"text": "Add Country", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"zx_add_cnt_{srv}", "style": "success"}])
        kb.append([{"text": "Delete Service", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"zx_del_srv_{srv}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_zenex_srv", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📂 <b>Service: {srv}</b>\nManage countries for this service:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("zx_add_cnt_"):
        srv = data.replace("zx_add_cnt_", "")
        user_states[chat_id] = "wait_zx_cnt_name"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv}
        edit_message(chat_id, msg_id, render_body_text(f"🌍 Enter Country Name for <b>{srv}</b> (e.g. UK, USA):"), reply_markup=get_cancel_kb())

    elif data.startswith("zx_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        ranges = bot_settings["zenex_services"][srv].get(cnt, [])
        kb, row = [], []
        for r in ranges:
            row.append({"text": f"Delete {r}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"zx_dr_{srv}_{cnt}_{r}", "style": "danger"})
            if len(row) == 2: kb.append(row); row = []
        if row: kb.append(row)
        kb.append([{"text": "Add Range", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"zx_addr_{srv}_{cnt}", "style": "success"}])
        kb.append([{"text": "Delete Entire Country", "icon_custom_emoji_id": "6224256529369932354", "callback_data": f"zx_del_cnt_{srv}_{cnt}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"zx_srv_{srv}", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"📍 <b>Service: {srv} | Country: {cnt}</b>\n\n<b>Total Ranges:</b> {len(ranges)}"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("zx_addr_"):
        parts = data.split("_")
        srv, cnt = parts[2], parts[3]
        user_states[chat_id] = "wait_zx_addr"
        temp_data[chat_id] = {"msg_id": msg_id, "srv": srv, "cnt": cnt}
        edit_message(chat_id, msg_id, render_body_text(f"📝 Send the new Range for <b>{cnt}</b> (e.g. 4473845XXX):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"zx_cnt_{srv}_{cnt}", "style": "danger"}]]})

    elif data.startswith("zx_dr_"):
        parts = data.split("_")
        srv, cnt, rng = parts[2], parts[3], parts[4]
        if rng in bot_settings["zenex_services"].get(srv, {}).get(cnt, []):
            bot_settings["zenex_services"][srv][cnt].remove(rng)
            save_db()
            answer_callback(call["id"], f"✅ Range {rng} deleted!", show_alert=True)
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"zx_cnt_{srv}_{cnt}", "id": call["id"]})

    elif data.startswith("zx_del_srv_"):
        srv = data.replace("zx_del_srv_", "")
        if srv in bot_settings["zenex_services"]: del bot_settings["zenex_services"][srv]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "manage_zenex_srv", "id": call["id"]})

    elif data.startswith("zx_del_cnt_"):
        parts = data.split("_")
        srv, cnt = parts[3], parts[4]
        if cnt in bot_settings["zenex_services"].get(srv, {}): del bot_settings["zenex_services"][srv][cnt]
        save_db()
        handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"zx_srv_{srv}", "id": call["id"]})

    elif data == "manage_fj":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "toggle_fj":
        bot_settings["fj_on"] = not bot_settings["fj_on"]
        clear_force_join_membership_cache()
        save_db()
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "add_fj":
        user_states[chat_id] = "wait_for_add_fj"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send Channel Username or Invite Link:\n<i>(Note: For private channels, use the numeric ID like -100...)</i>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_fj", "style": "danger"}]]})

    elif data.startswith("del_fj_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fj_channels"]):
            del bot_settings["fj_channels"][idx]
            clear_force_join_membership_cache()
            save_db()
            answer_callback(call["id"], "✅ Channel deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "manage_admins":
        edit_message(chat_id, msg_id, get_admin_management_text(), reply_markup=admin_settings_keyboard())

    elif data == "add_adm":
        user_states[chat_id] = "wait_for_add_adm"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID of the new Admin:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_admins", "style": "danger"}]]})

    elif data.startswith("del_adm_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["admins"]):
            del bot_settings["admins"][idx]
            save_db()
            answer_callback(call["id"], "✅ Admin deleted!", show_alert=True)
            edit_message(chat_id, msg_id, get_admin_management_text(), reply_markup=admin_settings_keyboard())

    elif data == "manage_otp_groups":
        edit_message(chat_id, msg_id, render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())

    elif data == "add_fw":
        user_states[chat_id] = "wait_for_add_fw_id"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Group ID/Username to forward messages to:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "danger"}]]})

    elif data.startswith("manage_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            grp_id = bot_settings["fw_groups"][idx]["chat_id"]
            edit_message(chat_id, msg_id, render_body_text(f"🛡 <b>Manage Group:</b> {grp_id}"), reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("add_fwbtn_"):
        idx = int(data.split("_")[2])
        user_states[chat_id] = "wait_for_add_fw_btn"
        temp_data[chat_id] = {"msg_id": msg_id, "fw_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send a custom button as:\n<code>Button Text - https://link.com</code>\nPut one emoji at the start of the button text; a premium custom emoji will become the button icon. Add GET NUMBER, CHANNEL, or SUPPORT as separate buttons if needed."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_fw_{idx}", "style": "danger"}]]})

    elif data.startswith("del_fwbtn_"):
        parts = data.split("_")
        idx, b_idx = int(parts[2]), int(parts[3])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            if 0 <= b_idx < len(bot_settings["fw_groups"][idx]["buttons"]):
                del bot_settings["fw_groups"][idx]["buttons"][b_idx]
                save_db()
                answer_callback(call["id"], "✅ Button deleted!", show_alert=True)
                edit_message(chat_id, msg_id, render_body_text(f"🛡 <b>Manage Group:</b> {bot_settings['fw_groups'][idx]['chat_id']}"), reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("del_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            del bot_settings["fw_groups"][idx]
            save_db()
            answer_callback(call["id"], "✅ Group deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())

    elif data == "edit_otp_link":
        user_states[chat_id] = "wait_for_otp_link"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new OTP Group Link:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "danger"}]]})

    elif data == "manage_panels":
        api_count = len([p for p in bot_settings["panels"] if p.get("type") == "API Panel"])
        cpt_count = len([p for p in bot_settings["panels"] if p.get("type", "API Panel") == "Auto Captcha Panel"])
        auto_api_count = count_configured_auto_api_providers()
        active_api = any(
            p.get("type") == "API Panel" and str(p.get("status", "")).upper() == "ON"
            for p in bot_settings.get("panels", [])
            if isinstance(p, dict)
        )
        active_captcha = any(
            p.get("type", "API Panel") == "Auto Captcha Panel"
            and str(p.get("status", "")).upper() == "ON"
            for p in bot_settings.get("panels", [])
            if isinstance(p, dict)
        )
        text = (
            '<tg-emoji emoji-id="6224162624204972282">⚡</tg-emoji>'
            '<b>MASTER PANEL</b>'
            '<tg-emoji emoji-id="6224162624204972282">⚡</tg-emoji>\n'
            '-----------------------------------\n'
            '<b>API</b> '
            '<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji> '
            f'{api_count} '
            '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
            '<b>Auto Captcha</b> '
            '<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji> '
            f'{cpt_count} '
            '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
            '<b>Auto Api Panel</b> '
            '<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji> '
            f'{auto_api_count} '
            '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
            'Choose a panel to manage '
            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>'
        )
        kb = {"inline_keyboard": [
            [{"text": "Auto Captcha Panel", "icon_custom_emoji_id": "6197397212650020943", "callback_data": "manage_cpt_panels", "style": "success" if active_captcha else "primary"}],
            [{"text": "Stex SMS", "icon_custom_emoji_id": "6226471972285458398", "callback_data": "stex_control", "style": "success" if bot_settings.get("stex_auto", False) else "primary"},
             {"text": "Voltx SMS", "icon_custom_emoji_id": "6226471972285458398", "callback_data": "voltx_control", "style": "success" if bot_settings.get("voltx_auto", False) else "primary"}],
            [{"text": "Zenex", "icon_custom_emoji_id": "6199291250277885056", "callback_data": "zenex_control", "style": "success" if bot_settings.get("zenex_auto", False) else "primary"},
             {"text": "API", "icon_custom_emoji_id": "6199741311310896893", "callback_data": "manage_api_panels", "style": "success" if active_api else "primary"},
             {"text": "FastX", "icon_custom_emoji_id": "6199291250277885056", "callback_data": "fastx_control", "style": "success" if bot_settings.get("fastx_auto", False) else "primary"}],
             [{"text": "Back", "icon_custom_emoji_id": BACK_BUTTON_EMOJI_ID, "callback_data": "back_to_admin", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, render_body_text(text), reply_markup=kb)

    elif data in ["manage_api_panels", "manage_cpt_panels"]:
        p_type = "API Panel" if data == "manage_api_panels" else "Auto Captcha Panel"
        p_list = [p for p in bot_settings["panels"] if p.get("type", "API Panel") == p_type]
        icon = f"{PEM['world']} API" if p_type == 'API Panel' else f"{PEM['lock']} Auto Captcha"

        if p_type == "Auto Captcha Panel":
            text = (
                '<tg-emoji emoji-id="6221992261266187100">🟢</tg-emoji>'
                f'Active Monitors'
                '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji>'
                f'{len(p_list)} '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
                '<tg-emoji emoji-id="6221992261266187100">🟢</tg-emoji>'
                'Available Providers'
                '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji>'
                '<tg-emoji emoji-id="6233188575286927353">⬇️</tg-emoji>\n'
            )
        else:
            text = (
                '<tg-emoji emoji-id="6199741311310896893">☄️</tg-emoji>'
                'API Panels Management'
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                '◈━━━━━━━━━━━━━━━━━━◈\n'
                '<tg-emoji emoji-id="6224162624204972282">⚡</tg-emoji>'
                'Active Monitors'
                '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji>'
                f'{len(p_list)} '
                '<tg-emoji emoji-id="6224188445548356446">✅</tg-emoji>\n'
                '◈━━━━━━━━━━━━━━━━━━◈\n'
                '<tg-emoji emoji-id="5192812028632274956">🟢</tg-emoji> '
                'Available Providers '
                '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>\n'
                '◈━━━━━━━━━━━━━━━━━━◈\n'
            )
        for p in p_list:
            if p_type == "API Panel":
                if p.get("status") == "ON":
                    status_text = (
                        '<tg-emoji emoji-id="6224038684333711964">✅</tg-emoji> '
                        'Monitoring'
                    )
                else:
                    status_text = (
                        '<tg-emoji emoji-id="6224003980997962148">❌</tg-emoji> '
                        'Stopped'
                    )
                configured = bool(p.get("api_url") or p.get("full_api_url"))
                if configured:
                    config_text = (
                        '<tg-emoji emoji-id="6224038684333711964">✅</tg-emoji> '
                        'Configured'
                    )
                    final_status_icon = (
                        '<tg-emoji emoji-id="6224038684333711964">✅</tg-emoji>'
                    )
                else:
                    config_text = (
                        '<tg-emoji emoji-id="6224003980997962148">❌</tg-emoji> '
                        'Not Configured'
                    )
                    final_status_icon = (
                        '<tg-emoji emoji-id="6199732519512842394">❌</tg-emoji>'
                    )
                text += (
                    '<tg-emoji emoji-id="6199741311310896893">☄️</tg-emoji>'
                    f'{html.escape(str(p.get("name", "API Panel")))}'
                    '<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                    f'{status_text} | {config_text} {final_status_icon}\n'
                    '◈━━━━━━━━━━━━━━━━━━◈\n'
                )
                continue
            status = "Monitoring" if p['status'] == 'ON' else "Stopped"
            login_state = p.get('login_status', '')
            if p['type'] == 'Auto Captcha Panel':
                conf = f" {login_state}" if login_state else f"{PEM['ok']} Configured"
            else:
                conf = f"{PEM['ok']} Configured" if p.get('api_url') else f"{PEM['no']} Not Configured"
            text += f"• {p['name']}: {PEM['ok'] if p['status']=='ON' else PEM['no']} {status} | {conf}\n"
        edit_message(chat_id, msg_id, render_body_text(text), reply_markup=typed_panels_list_keyboard(p_type))

    elif data in ["add_api_panel", "add_cpt_panel"]:
        user_states[chat_id] = "wait_for_panel_name"
        p_type = "api" if data == "add_api_panel" else "logc"
        temp_data[chat_id] = {"msg_id": msg_id, "add_type": p_type}
        edit_message(chat_id, msg_id, render_body_text(
            '<tg-emoji emoji-id="6222073659486381042">📝</tg-emoji>'
            ' Entar New Provider Name '
            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_{'api' if p_type=='api' else 'cpt'}_panels", "style": "danger"}]]})

    elif data.startswith("add_ptype_"):
        pass

    elif data in ["list_del_api", "list_del_cpt"]:
        p_type = "API Panel" if data == "list_del_api" else "Auto Captcha Panel"
        kb = []
        for idx, p in enumerate(bot_settings["panels"]):
            if p.get("type", "API Panel") == p_type:
                kb.append([{"text": f"Delete {p['name']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"do_del_pnl_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_{'api' if p_type=='API Panel' else 'cpt'}_panels", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['trash']} <b>Select a Provider to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("do_del_pnl_"):
        idx = int(data.split("_")[3])
        if 0 <= idx < len(bot_settings["panels"]):
            p_type = bot_settings["panels"][idx].get("type", "API Panel")
            del bot_settings["panels"][idx]
            save_db()
            answer_callback(call["id"], "✅ Provider Deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": f"manage_{'api' if p_type=='API Panel' else 'cpt'}_panels", "id": "internal"})

    elif data.startswith("tog_pnl_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["panels"]):
            p = bot_settings["panels"][idx]
            
            p["status"] = "ON" if p["status"] == "OFF" else "OFF"
            save_db()
            
            if p["type"] == "Auto Captcha Panel":
                raw_login_status = str(p.get("login_status", "Unknown"))
                if "Pending Auto-Login" in raw_login_status or "Pending First Login" in raw_login_status:
                    login_status = "Pending"
                else:
                    login_status = re.sub(r"^(?:⏳|✅|❌)\s*", "", raw_login_status)
                status_display = (
                    '<tg-emoji emoji-id="5192812028632274956">🟢</tg-emoji> '
                    'Monitoring <tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
                    if p["status"] == "ON"
                    else 'Stopped <tg-emoji emoji-id="6221743402271121752">❌</tg-emoji>'
                )
                text = (
                    '<tg-emoji emoji-id="6224099054394025076">📱</tg-emoji> '
                    f'Configure {html.escape(str(p.get("name", "B")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    '◈━━━━━━━━━━━━━━━━━━◈\n'
                    'Type<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                    f'{html.escape(str(p.get("type", "Auto Captcha Panel")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    f'Status<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>{status_display}\n'
                    'Login Status<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                    f'{html.escape(login_status)} '
                    '<tg-emoji emoji-id="6224477342228565523">♾️</tg-emoji>\n'
                    'Auto<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji>'
                    'Login... '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    'Login URL <tg-emoji emoji-id="6221840949568350303">🛜</tg-emoji>\n'
                    f'{html.escape(str(p.get("login_url", "None")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    'User Name<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji>\n'
                    f'{html.escape(str(p.get("username", "None")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    '◈━━━━━━━━━━━━━━━━━━◈'
                )
            else:
                text = api_panel_config_text(p)
            edit_message(chat_id, msg_id, render_body_text(text), reply_markup=panel_config_keyboard(idx))

    elif data.startswith("conf_pnl_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["panels"]):
            p = bot_settings["panels"][idx]
            if p["type"] == "Auto Captcha Panel":
                raw_login_status = str(p.get("login_status", "Unknown"))
                if "Pending Auto-Login" in raw_login_status or "Pending First Login" in raw_login_status:
                    login_status = "Pending"
                else:
                    login_status = re.sub(r"^(?:⏳|✅|❌)\s*", "", raw_login_status)
                status_display = (
                    '<tg-emoji emoji-id="5192812028632274956">🟢</tg-emoji> '
                    'Monitoring <tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
                    if p["status"] == "ON"
                    else 'Stopped <tg-emoji emoji-id="6221743402271121752">❌</tg-emoji>'
                )
                text = (
                    '<tg-emoji emoji-id="6221860118007391816">🕹</tg-emoji> '
                    f'Configure {html.escape(str(p.get("name", "B")))} '
                    '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>\n'
                    '◈━━━━━━━━━━━━━━━━━━◈\n'
                    'Type<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                    f'{html.escape(str(p.get("type", "Auto Captcha Panel")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    f'Status<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>'
                    f'{status_display}\n'
                    'Login Status<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji> '
                    f'{html.escape(login_status)} '
                    '<tg-emoji emoji-id="6224477342228565523">♾️</tg-emoji>\n'
                    'Auto<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji>'
                    'Login... '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    'Login URL<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji>\n'
                    f'{html.escape(str(p.get("login_url", "None")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    'User Name<tg-emoji emoji-id="6224381843630728008">🛜</tg-emoji>\n'
                    f'{html.escape(str(p.get("username", "None")))} '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    'Num CLMN<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                    f'{html.escape(str(p.get("num_col_name", "None")))} '
                    f'(Idx: {html.escape(str(p.get("num_col_idx", "None")))}) '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    'Msg CLMN<tg-emoji emoji-id="6222231598318755961">🛜</tg-emoji> '
                    f'{html.escape(str(p.get("msg_col_name", "None")))} '
                    f'(Idx: {html.escape(str(p.get("msg_col_idx", "None")))}) '
                    '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n'
                    '◈━━━━━━━━━━━━━━━━━━◈'
                )
            else:
                text = api_panel_config_text(p)
            edit_message(chat_id, msg_id, render_body_text(text), reply_markup=panel_config_keyboard(idx))

    elif data.startswith("set_p_api_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_api"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the API URL for this provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_tok_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_tok"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Token for this provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_fapi_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_fapi"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the FULL API URL (Example: http://api.com/get?key=YOUR_TOKEN&start=0):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_rec_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_rec"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the number of records to fetch (e.g. 10).\nType <code>0</code> for Unlimited:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("test_p_conn_"):
        idx = int(data.split("_")[3])
        p = bot_settings["panels"][idx]
        wait_msg = send_message(chat_id, render_body_text("⏳ Testing connection. Please wait..."))
        wait_msg_id = wait_msg.get("result", {}).get("message_id") if wait_msg else None
        answer_callback(call["id"])
        
        try:
            parsed = []
            raw_text = ""
            
            if p["type"] == "Auto Captcha Panel":
                sess = panel_sessions.get(idx)
                if not sess:
                    success = attempt_auto_login(p, idx)
                    if not success:
                        if wait_msg_id: delete_message(chat_id, wait_msg_id)
                        send_message(chat_id, render_body_text(f"❌ <b>Auto Login Failed!</b>\nReason: {html.escape(str(p.get('login_status', 'Unknown')))}"))
                        return
                    sess = panel_sessions.get(idx)
                    
                login_url = p.get("login_url", "").strip()
                if not login_url.startswith("http"): login_url = "http://" + login_url
                msg_link = p.get("msg_link", "").strip()
                if not msg_link.startswith("http") and msg_link != "": msg_link = "http://" + msg_link
                check_url = msg_link if msg_link else f"{login_url.split('/login')[0]}/client/SMSCDRStats"
                
                # 🌟 test connection supports sAjaxSource & HTML table parser
                parsed, raw_text = fetch_cpt_panel_cdrs(p, sess, check_url)
                
            else:
                full_url = p.get("full_api_url", "").strip()
                url = p.get("api_url", "").strip()
                token = p.get("token", "").strip()
                if not full_url and not url:
                    if wait_msg_id: delete_message(chat_id, wait_msg_id)
                    send_message(chat_id, render_body_text("❌ Please Set API URL or Full API URL first!"))
                    return
                
                urls_to_try = []
                if full_url:
                    urls_to_try.append(full_url)
                else:
                    if "{token}" in url or "{key}" in url:
                        urls_to_try.append(url.replace("{token}", token).replace("{key}", token))
                    elif "token=" in url or "key=" in url:
                        urls_to_try.append(url)
                    else:
                        sep = '&' if '?' in url else '?'
                        urls_to_try.append(f"{url}{sep}token={token}")
                        urls_to_try.append(f"{url}{sep}key={token}&start=0")
                        urls_to_try.append(f"{url}{sep}key={token}")
                    
                parsed = []
                raw_text = ""
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                for try_url in urls_to_try:
                    try:
                        res = requests.get(try_url, headers=headers, timeout=10)
                        raw_text = res.text
                        parsed = parse_panel_response(raw_text, p)
                        if parsed:
                            if not full_url and try_url != url and token:
                                p["api_url"] = try_url.replace(token, "{token}")
                                save_db()
                            break
                    except: pass
                 
            if wait_msg_id: delete_message(chat_id, wait_msg_id)
                 
            if parsed:
                if p.get("type") == "API Panel":
                    txt = (
                        '<tg-emoji emoji-id="6224038684333711964">✅</tg-emoji> '
                        'Connection Successful!\n'
                        '◈━━━━━━━━━━━━━━━━━◈\n'
                        'Parsed Data Sample (Max 3):\n\n'
                    )
                    for i, sample in enumerate(parsed[:3]):
                        num = html.escape(str(sample.get("number", "")))
                        full_msg = html.escape(str(sample.get("message", "")))
                        otp = html.escape(str(sample.get("otp", "")))
                        panel_name = html.escape(str(p.get("name", "Unknown")))
                        txt += (
                            f'{i + 1}'
                            '<tg-emoji emoji-id="6223988965792294118">📥</tg-emoji>\n'
                            '◈━━◈\n'
                            '<tg-emoji emoji-id="6224284210434154938">📱</tg-emoji> '
                            f'{panel_name}\n'
                            '<tg-emoji emoji-id="6224284210434154938">📱</tg-emoji> '
                            'Number'
                            '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                            f'<code>{num}</code> '
                            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n\n'
                            '<tg-emoji emoji-id="6222073659486381042">📝</tg-emoji> '
                            'Full Msg'
                            '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                            f'<code>{full_msg}</code> '
                            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n\n'
                            '<tg-emoji emoji-id="6221761819090887073">🔔</tg-emoji> '
                            'OTP'
                            '<tg-emoji emoji-id="6224279404365750242">🛜</tg-emoji> '
                            f'<code>{otp}</code> '
                            '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>\n\n'
                        )
                    txt += '◈━━━━━━━━━━━━━━━━━━━━◈'
                else:
                    txt = f"✅ <b>Connection Successful!</b>\n\n🎯 <b>Parsed Data Sample (Max 3):</b>\n\n"
                    for i, sample in enumerate(parsed[:3]):
                        num = sample['number']
                        msg = sample['message']
                        otp = sample['otp']
                        detected_app = detect_service(msg)
                        app_name = detected_app if detected_app else p.get("name", "Unknown")
                        app_full_name, prem_app_html = get_service_info_html(app_name, msg)
                        txt += f"<b>{i+1}.</b> {prem_app_html} <b>{app_full_name}</b>\n"
                        txt += f"📱 Number: <code>{num}</code>\n"
                        txt += f"📝 Full Msg: <code>{html.escape(msg)}</code>\n"
                        txt += f"🔐 OTP: <code>{otp}</code>\n"
                        txt += "➖" * 12 + "\n"
                send_message(chat_id, render_body_text(txt))
            else:
                if p["type"] == "Auto Captcha Panel":
                    try:
                        soup = BeautifulSoup(raw_text, 'html.parser')
                        tables = soup.find_all('table')
                        if tables:
                            full_table_data = "🔍 FULL TABLE DATA (A-Z)\n" + "="*50 + "\n\n"
                            for t_idx, table in enumerate(tables):
                                full_table_data += f"--- Table {t_idx+1} ---\n"
                                rows = table.find_all('tr')
                                for r_idx, row in enumerate(rows):
                                    cols = row.find_all(['th', 'td'])
                                    col_texts = [f"[{c_idx+1}] {c.get_text(separator=' ', strip=True)}" for c_idx, c in enumerate(cols)]
                                    full_table_data += f"Row {r_idx+1}: {' | '.join(col_texts)}\n"
                                full_table_data += "\n" + "="*50 + "\n"
                            
                            send_document(chat_id, f"Full_Panel_Data_{idx}.txt", full_table_data.encode('utf-8'))
                            fail_txt = f"⚠️ <b>Connected, but couldn't parse OTP data!</b>\n\n<i>আমি ওই লিংকের সম্পূর্ণ (A-Z) ডাটা একটি Text File এ পাঠিয়েছি। ফাইলটি ওপেন করে সঠিক Column Number (যেমন: [1], [3]) চেক করে প্যানেলে আপডেট করে নাও।</i>"
                            send_message(chat_id, render_body_text(fail_txt))
                        else:
                            send_message(chat_id, render_body_text(f"⚠️ <b>Connected, but no HTML Table found!</b>\nMake sure the message link is correct."))
                    except Exception as e:
                        send_message(chat_id, render_body_text(f"❌ <b>Error parsing HTML:</b> {html.escape(str(e))}"))
                else:
                    safe_html = html.escape(str(raw_text)[:300])
                    send_message(chat_id, render_body_text(f"⚠️ <b>Connected, but couldn't find/parse OTP data.</b>\n\n<i>Make sure your API config is correct.</i>\n\nRaw HTML/Data (excerpt):\n<code>{safe_html}...</code>"))
        except Exception as e:
            if wait_msg_id: delete_message(chat_id, wait_msg_id)
            send_message(chat_id, render_body_text(f"❌ <b>Connection Failed!</b>\nError: {html.escape(str(e))}"))

    elif data == "GX_control":
        if chat_id in user_states: del user_states[chat_id]
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6203810466406342809">😵</tg-emoji> '
                '<b>BOT MANAGEMENT</b> '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ),
            reply_markup=GX_control_keyboard(),
        )

    elif data == "GX_toggle_w":
        bot_settings["withdraw_on"] = not bot_settings["withdraw_on"]
        save_db()
        edit_message(
            chat_id, msg_id,
            render_body_text(
                '<tg-emoji emoji-id="6203810466406342809">😵</tg-emoji> '
                '<b>BOT MANAGEMENT</b> '
                '<tg-emoji emoji-id="6224255644606670093">✅</tg-emoji>'
            ),
            reply_markup=GX_control_keyboard(),
        )

    elif data == "manage_w_methods":
        edit_message(chat_id, msg_id, get_withdrawal_methods_text(), reply_markup=w_methods_keyboard())

    elif data == "add_wm":
        user_states[chat_id] = "wait_for_add_wm"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the name of the new Withdrawal Method:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_w_methods", "style": "danger"}]]})

    elif data.startswith("del_wm_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["w_methods"]):
            del bot_settings["w_methods"][idx]
            save_db()
            answer_callback(call["id"], "✅ Method deleted!", show_alert=True)
            edit_message(chat_id, msg_id, get_withdrawal_methods_text(), reply_markup=w_methods_keyboard())

    elif data.startswith("GX_"):
        key = data.replace("GX_", "")
        key_map = {"min_w": "min_withdraw", "otp_r": "otp_reward", "ref_r": "refer_reward", "cool": "cooldown", "num_req": "num_req", "num_share": "num_share", "sup_link": "support_link", "w_group": "w_group"}
        if key in key_map:
            temp_data[chat_id] = {"msg_id": msg_id, "key": key_map[key]}
            user_states[chat_id] = "set_GX"
            cancel_kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_GX_edit", "style": "danger"}]]}
            edit_message(chat_id, msg_id, render_body_text(f"📝 Please send the new value for <code>{key_map[key]}</code>:"), reply_markup=cancel_kb)
            answer_callback(call["id"])

    elif data == "np_back_apps":
        answer_callback(call.get("id"))
        show_number_app_selection(chat_id, msg_id)
        return

    elif data == "np_local_services":
        with _number_picker_sessions_lock:
            picker_session = _number_picker_sessions.get(chat_id)
        if picker_session:
            _render_number_picker_local_services(chat_id, msg_id, picker_session)
        else:
            show_number_app_selection(chat_id, msg_id)
        return

    elif data.startswith("np_app_"):
        answer_callback(call.get("id"))
        _show_number_picker_countries(
            chat_id, msg_id, data.rsplit("_", 1)[-1]
        )
        return

    elif data == "np_back_country":
        answer_callback(call.get("id"))
        with _number_picker_sessions_lock:
            picker_session = _number_picker_sessions.get(chat_id)
            selected_app = picker_session.get("selected_app") if picker_session else None
        if selected_app:
            _show_number_picker_countries(chat_id, msg_id, selected_app)
        else:
            show_number_app_selection(chat_id, msg_id)
        return

    elif data.startswith("np_cty_"):
        _process_number_picker_country(call, data.rsplit("_", 1)[-1])
        return

    elif data == "np_repeat":
        with _number_picker_sessions_lock:
            picker_session = _number_picker_sessions.get(chat_id)
            selected_country_id = (
                picker_session.get("selected_country_id")
                if picker_session else None
            )
        if selected_country_id:
            _process_number_picker_country(call, selected_country_id)
        else:
            answer_callback(call.get("id"), "⚠️ Select a country first.", show_alert=True)
        return

    elif data == "back_to_services":
        local_services = {
            canonical
            for batch in number_batches.values()
            if isinstance(batch, dict)
            for canonical in [_canonical_allowed_service(batch.get("service", ""))]
            if canonical and _has_local_stock_for_service(canonical)
        }
        provider_services = {
            canonical
            for service_map in (
                bot_settings.get("stex_services", {}),
                bot_settings.get("voltx_services", {}),
                bot_settings.get("zenex_services", {}),
            )
            for service in service_map
            for canonical in [_canonical_allowed_service(service)]
            if canonical
        }
        all_services = local_services.union(provider_services)
        
        if not all_services:
            answer_callback(call["id"], "❌ No numbers or services available!", show_alert=True)
            return
            
        c_msg = bot_settings["custom_messages"].get("get_number", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['pin']} Select Service"))
        
        kb = []
        service_buttons = []
        for s in sorted(
            all_services,
            key=lambda value: (
                -_service_traffic_count(value),
                str(value).lower(),
            ),
        ):
            selections = []
            if s in provider_services:
                selections.append((s, _service_selection_label(s)))
            if s in local_services:
                local_key = _local_stock_service_key(s)
                selections.append((local_key, _service_selection_label(local_key)))
            for selection_key, service_name in selections:
                service_buttons.append(
                    {
                        "text": service_name,
                        "icon_custom_emoji_id": get_service_icon_id(s, s),
                        "callback_data": f"g_s_{selection_key}",
                        "style": "primary",
                    }
                )
        service_buttons = _equal_service_button_labels(service_buttons)
        txt = _stretch_service_prompt(txt, service_buttons)
        kb.extend(_two_column_rows(service_buttons))
        
        for b in c_msg.get("buttons", []): 
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        kb.append([{"text": "Close", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "close_msg", "style": "danger"}])
        
        edit_message(chat_id, msg_id, txt, reply_markup={"inline_keyboard": kb})

    elif data.startswith("g_s_"):
        selection_service = data.split("g_s_", 1)[1]
        is_local_stock, base_service = _split_service_selection(selection_service)
        service = _canonical_allowed_service(base_service)
        if not service:
            answer_callback(call["id"], "❌ This service is unavailable.", show_alert=True)
            return
        if is_local_stock:
            all_countries = {
                batch.get("country")
                for batch in number_batches.values()
                if isinstance(batch, dict)
                and _traffic_service_matches(batch.get("service", ""), service)
                and batch.get("country")
                and batch.get("numbers")
            }
        else:
            stex_cnts = set(bot_settings.get("stex_services", {}).get(service, {}).keys())
            voltx_cnts = set(bot_settings.get("voltx_services", {}).get(service, {}).keys())
            zenex_cnts = set(bot_settings.get("zenex_services", {}).get(service, {}).keys())
            live_cnts = _live_range_countries(service)
            all_countries = stex_cnts.union(voltx_cnts, zenex_cnts, live_cnts)
        all_countries = _top_traffic_countries(service, all_countries)
        
        c_msg = bot_settings["custom_messages"].get("select_country", {})
        service_label = _service_selection_label(selection_service)
        raw_txt = c_msg.get(
            "text",
            '<tg-emoji emoji-id="6224281577619201977">📌</tg-emoji> '
            'Select a country for {service}:',
        ).replace("{service}", service_label)
        if 'emoji-id="6224281577619201977"' not in raw_txt:
            raw_txt = raw_txt.replace(
                "📌",
                '<tg-emoji emoji-id="6224281577619201977">📌</tg-emoji>',
                1,
            )
        txt = render_body_text(raw_txt)
        
        flags_db = bot_settings.get("premium_flags", {})
        kb = []
        country_buttons = []
        for c in all_countries:
            emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                iso = flag_data.get("iso", "").upper()
                name = flag_data.get("name", "").upper()
                if c.upper() == iso or c.upper() == name or c.upper() in name or name in c.upper():
                    if "id" in flag_data:
                        emoji_id = flag_data["id"]
                        break
            
            otp_price = _format_number_picker_otp_rate(
                _number_picker_country_otp_rate(selection_service, c)
            )
                    
            country_buttons.append(
                {
                    "text": f"{c} /{otp_price} TK",
                    "icon_custom_emoji_id": emoji_id,
                    "callback_data": f"g_c_{selection_service}_{c}",
                    "style": "success",
                }
            )
        kb.extend(_two_column_rows(country_buttons))
        
        for b in c_msg.get("buttons", []): 
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_services", "style": "danger"}])
        edit_message(chat_id, msg_id, txt, reply_markup={"inline_keyboard": kb})

    elif data.startswith("g_c_") or data.startswith("c_n_"):
        now = time.time()
        if now - user_cooldowns.get(chat_id, 0) < bot_settings["cooldown"]:
            answer_callback(call["id"], f"⌛ Please wait {int(bot_settings['cooldown'] - (now - user_cooldowns.get(chat_id, 0)))}s.", show_alert=True)
            return
        
        user_cooldowns[chat_id] = now
        expire_previous_number(chat_id)

        if data.startswith("c_n_s_"):
            is_stex_req = data.endswith("_stx")
            is_voltx_req = data.endswith("_vtx")
            is_zenex_req = data.endswith("_znx")
            clean_data = data[:-4] if (is_stex_req or is_voltx_req or is_zenex_req) else data
            parts_s = clean_data.split("_", 4)
            
            query = parts_s[3] if len(parts_s) > 3 else ""
            service_from_cb = parts_s[4] if len(parts_s) > 4 else None
            if service_from_cb and not _canonical_allowed_service(service_from_cb):
                answer_callback(call["id"], "❌ This service is unavailable.", show_alert=True)
                return
            
            allowed_countries = bot_settings.get("search_countries", [])
            voltx_allowed = bot_settings.get("voltx_search_countries", [])
            zenex_allowed = bot_settings.get("zenex_search_countries", [])
            
            is_stex_allowed = _range_is_allowed(query, allowed_countries) or _service_range_is_allowed(
                query, service_from_cb, bot_settings.get("stex_services", {})
            ) or _live_service_range_is_allowed(query, service_from_cb, "stex")
            is_voltx_allowed = _range_is_allowed(query, voltx_allowed) or _service_range_is_allowed(
                query, service_from_cb, bot_settings.get("voltx_services", {})
            ) or _live_service_range_is_allowed(query, service_from_cb, "voltx")
            is_zenex_allowed = _range_is_allowed(query, zenex_allowed) or _service_range_is_allowed(
                query, service_from_cb, bot_settings.get("zenex_services", {})
            ) or _live_service_range_is_allowed(query, service_from_cb, "zenex")
            
            if not is_stex_allowed and not is_voltx_allowed and not is_zenex_allowed:
                answer_callback(call["id"], "❌ This country code is not allowed for search!", show_alert=True)
                return
                
            # Match the second bot: keep this selected-country message and
            # edit it in place to show the animated premium loading emoji.
            # Acknowledge the tap before making the provider request.
            answer_callback(call.get("id"))
            loading_text = (
                f'<tg-emoji emoji-id="{COUNTRY_LOADING_EMOJI_ID}">⏳</tg-emoji> '
                "<b>Getting Number</b>"
            )
            loading_started_at = time.monotonic()
            loading_result = edit_message(chat_id, msg_id, loading_text)
            if not loading_result or not loading_result.get("ok"):
                edit_message(chat_id, msg_id, "⏳ <b>Getting Number</b>")
            
            fetched_nums, source = fetch_numbers_fast(
                query,
                chat_id,
                requested_number_count(),
                source_hint=(
                    "stex" if is_stex_req
                    else "voltx" if is_voltx_req
                    else "zenex" if is_zenex_req
                    else None
                ),
                service=service_from_cb,
                persist=False,
            )
            _finish_existing_fetching_animation(chat_id, msg_id, loading_started_at)
            if not fetched_nums:
                edit_message(chat_id, msg_id, "❌ Number out of stock!")
                return

            kb = []
            if service_from_cb:
                app_full_name, _ = get_service_info_html(
                    _canonical_allowed_service(service_from_cb) or service_from_cb
                )
                emoji_id_srv = MESSAGE_SMS_EMOJI_ID
                for app_key, app_data in bot_settings.get("premium_apps", {}).items():
                    if service_from_cb.upper() == app_key or service_from_cb.upper() in app_key or app_key in service_from_cb.upper():
                        if "id" in app_data: emoji_id_srv = app_data["id"]; break
                kb.append([{"text": f"{app_full_name}", "icon_custom_emoji_id": emoji_id_srv, "callback_data": "ignore", "style": "primary"}])

            flags_db = bot_settings.get("premium_flags", {})
            country_emoji_html = ""
            display_nums = []
            for num in fetched_nums:
                char_flag, iso = get_flag_and_code(num)
                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                display_nums.append(display_num)
                flag_emoji_id = "5780471598922337683"
                for flag_code, flag_data in flags_db.items():
                    if iso == flag_data.get("iso"):
                        if "id" in flag_data: 
                            flag_emoji_id = flag_data["id"]
                            country_emoji_html = f'<tg-emoji emoji-id="{flag_emoji_id}">{flag_data["char"]}</tg-emoji>'
                        break
                if not country_emoji_html: country_emoji_html = char_flag
                kb.append([{
                    "text": _compact_number_label(display_num),
                    "icon_custom_emoji_id": flag_emoji_id,
                    "copy_text": {"text": display_num},
                    "style": "success",
                }])
            
            vtx_ext = (
                "_stx" if is_stex_req
                else "_vtx" if is_voltx_req
                else "_znx" if is_zenex_req
                else ""
            )
            srv_ext = f"_{service_from_cb}" if service_from_cb else ""
            action_row = [{
                "text": "Change Number",
                "icon_custom_emoji_id": "5465368548702446780",
                "callback_data": f"c_n_s_{query}{srv_ext}{vtx_ext}",
                "style": "danger",
            }]
            if service_from_cb:
                action_row.append({
                    "text": "Change Country",
                    "icon_custom_emoji_id": "5305517382138112561",
                    "callback_data": f"g_s_{service_from_cb}",
                    "style": "danger",
                })
            kb.append(action_row)
            kb.append([{"text": "OTP Group", "icon_custom_emoji_id": OTP_GROUP_EMOJI_ID, "url": bot_settings["otp_link"], "style": "primary"}])
            
            success_mark = f'<tg-emoji emoji-id="{NUMBER_SUCCESS_EMOJI_ID}">✅</tg-emoji>'
            text_numbers = render_body_text(
                f"{success_mark} <b>NUMBER GENERATED SUCCESSFULLY</b>"
            )
            edit_message(
                chat_id, msg_id, text_numbers, reply_markup={"inline_keyboard": kb}
            )
            request_provider = (
                "stex" if is_stex_req
                else "voltx" if is_voltx_req
                else "zenex" if is_zenex_req
                else "auto"
            )
            number_contexts = {}
            for number in fetched_nums:
                canonical = _canonical_number(number)
                number_contexts[canonical] = {
                    "range": _clean_range_prefix(query),
                    "provider": _assigned_provider_for_number(number) or request_provider,
                    "service": service_from_cb or "",
                }
            user_active_sessions[chat_id] = {
                "msg_id": msg_id,
                "nums": fetched_nums,
                "request_range": _clean_range_prefix(query),
                "provider": request_provider,
                "service": service_from_cb or "",
                "number_contexts": number_contexts,
            }
            schedule_provider_state_save()
            return

        parts = data.split("_")
        selection_service = parts[2]
        is_local_stock, base_service = _split_service_selection(selection_service)
        service = _canonical_allowed_service(base_service)
        country = parts[3]
        if not service:
            answer_callback(call["id"], "❌ This service is unavailable.", show_alert=True)
            return

        has_local_stock = any(
            is_local_stock
            and _traffic_service_matches(b_data.get("service", ""), service)
            and b_data.get("country") == country
            and any(
                chat_id not in item.get("used_by", [])
                and not _number_is_claimed(item.get("num"))
                for item in b_data.get("numbers", [])
                if isinstance(item, dict)
            )
            for b_data in number_batches.values()
        )

        if not has_local_stock:
            if is_local_stock:
                answer_callback(
                    call["id"],
                    "❌ Uploaded stock is out of stock. Please choose another country.",
                    show_alert=True,
                )
                edit_message(chat_id, msg_id, "❌ Uploaded stock is out of stock.")
                return
            stex_srv_data = bot_settings.get("stex_services", {}).get(service, {}).get(country)
            voltx_srv_data = bot_settings.get("voltx_services", {}).get(service, {}).get(country)
            zenex_srv_data = bot_settings.get("zenex_services", {}).get(service, {}).get(country)
            
            target_range = None
            is_stex = False
            is_voltx = False
            is_zenex = False

            live_candidates = _live_ranges_for_service_country(service, country)
            if live_candidates:
                target_range, source_provider = random.choice(live_candidates)
                is_stex = source_provider == "stex"
                is_voltx = source_provider == "voltx"
                is_zenex = source_provider == "zenex"
            elif stex_srv_data and len(stex_srv_data) > 0:
                target_range = random.choice(stex_srv_data)
                is_stex = True
            elif voltx_srv_data and len(voltx_srv_data) > 0:
                target_range = random.choice(voltx_srv_data)
                is_voltx = True
            elif zenex_srv_data and len(zenex_srv_data) > 0:
                target_range = random.choice(zenex_srv_data)
                is_zenex = True
                
            if target_range:
                user_cooldowns[chat_id] = 0
                vtx_flag = (
                    "_stx" if is_stex
                    else "_vtx" if is_voltx
                    else "_znx" if is_zenex
                    else ""
                )
                handle_callback({"message": call["message"], "data": f"c_n_s_{target_range}_{service}{vtx_flag}", "id": call["id"]})
                return
            else:
                answer_callback(call["id"], "❌ Number out of stock or range missing!", show_alert=True)
                if data.startswith("c_n_"):
                    edit_message(chat_id, msg_id, "❌ Number out of stock or range missing!")
                return

        # Keep the selected-country message and show the same loading state
        # as the second bot until local stock has been reserved.
        # Acknowledge first so Telegram stops showing the pressed-button spinner.
        answer_callback(call.get("id"))
        loading_text = (
            f'<tg-emoji emoji-id="{COUNTRY_LOADING_EMOJI_ID}">⏳</tg-emoji> '
            "<b>Getting Number</b>"
        )
        loading_started_at = time.monotonic()
        loading_result = edit_message(chat_id, msg_id, loading_text)
        if not loading_result or not loading_result.get("ok"):
            edit_message(chat_id, msg_id, "⏳ <b>Getting Number</b>")

        fetched_nums = _reserve_local_numbers(
            query="",
            chat_id=chat_id,
            req_count=requested_number_count(),
            service=service,
            country=country,
            persist=False,
        )
        _finish_existing_fetching_animation(chat_id, msg_id, loading_started_at)

        if not fetched_nums:
            edit_message(
                chat_id, msg_id,
                "❌ You have already taken all numbers or stock is empty!"
            )
            return

        app_full_name, _ = get_service_info_html(
            service
        )
        app_full_name = _service_selection_label(selection_service)
        emoji_id = MESSAGE_SMS_EMOJI_ID
        apps_db = bot_settings.get("premium_apps", {})
        for app_key, app_data in apps_db.items():
            if service.upper() == app_key or service.upper() in app_key or app_key in service.upper():
                if "id" in app_data:
                    emoji_id = app_data["id"]
                    break
        kb = [[{"text": f"{app_full_name}", "icon_custom_emoji_id": emoji_id, "callback_data": "ignore", "style": "primary"}]]
        
        flags_db = bot_settings.get("premium_flags", {})
        country_emoji_html = ""
        display_nums = []
        for num in fetched_nums:
            char_flag, iso = get_flag_and_code(num)
            display_num = f"+{num}" if not num.startswith("+") else num
            display_nums.append(display_num)
            
            flag_emoji_id = "5780471598922337683"
            for flag_code, flag_data in flags_db.items():
                if iso == flag_data.get("iso"):
                    if "id" in flag_data: 
                        flag_emoji_id = flag_data["id"]
                        country_emoji_html = f'<tg-emoji emoji-id="{flag_emoji_id}">{flag_data["char"]}</tg-emoji>'
                    break
            
            if not country_emoji_html: country_emoji_html = char_flag
            kb.append([{
                "text": _compact_number_label(display_num),
                "icon_custom_emoji_id": flag_emoji_id,
                "copy_text": {"text": display_num},
                "style": "success",
            }])
            
        kb.append([
            {
                "text": "Change Number",
                "icon_custom_emoji_id": "5465368548702446780",
                "callback_data": f"c_n_{selection_service}_{country}",
                "style": "danger",
            },
            {
                "text": "Change Country",
                "icon_custom_emoji_id": "5305517382138112561",
                "callback_data": f"g_s_{selection_service}",
                "style": "danger",
            },
        ])

        c_btns = bot_settings["custom_messages"].get("get_number", {}).get("buttons", [])
        for c_b in c_btns: 
            b_copy = c_b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
            
        kb.append([{"text": "OTP Group", "icon_custom_emoji_id": OTP_GROUP_EMOJI_ID, "url": bot_settings["otp_link"], "style": "primary"}])
        
        success_mark = f'<tg-emoji emoji-id="{NUMBER_SUCCESS_EMOJI_ID}">✅</tg-emoji>'
        text_numbers = render_body_text(
            f"{success_mark} <b>NUMBER GENERATED SUCCESSFULLY</b>"
        )
        edit_message(
            chat_id, msg_id, text_numbers, reply_markup={"inline_keyboard": kb}
        )
        user_active_sessions[chat_id] = {
            "msg_id": msg_id,
            "nums": fetched_nums
        }
        schedule_provider_state_save()

    elif data.startswith("wapp_") or data.startswith("wrej_"):
        user_id_clicked = call.get("from", {}).get("id")
        if not is_admin(user_id_clicked):
            answer_callback(call["id"], "🚫 Only Bot Admins can process withdrawals!", show_alert=True)
            return
            
        action = "APPROVE" if data.startswith("wapp_") else "REJECT"
        history_page_match = re.fullmatch(
            r"w(?:app|rej)_(.+)_hist_(\d+)",
            data,
        )
        history_return_page = (
            int(history_page_match.group(2))
            if history_page_match else None
        )
        req_id = (
            history_page_match.group(1)
            if history_page_match
            else data[len("wapp_"):] if action == "APPROVE"
            else data[len("wrej_"):]
        )
        req_data = None
        with withdrawal_processing_lock:
            req_data = pending_withdrawals.get(req_id)

        # Recover a still-pending request from durable storage if a stale
        # in-memory map is the reason the button appeared to do nothing.
        if not isinstance(req_data, dict) and db:
            try:
                snapshot = db.collection("withdrawals").document(req_id).get()
                if snapshot.exists:
                    stored_request = snapshot.to_dict()
                    if (
                        isinstance(stored_request, dict)
                        and str(stored_request.get("status", "pending")).casefold()
                        == "pending"
                    ):
                        req_data = stored_request
                        with withdrawal_processing_lock:
                            pending_withdrawals.setdefault(req_id, req_data)
            except Exception as exc:
                print(f"⚠️ Could not reload withdrawal {req_id}: {exc}")
        
        with withdrawal_processing_lock:
            if req_data and req_id in withdrawal_processing_ids:
                answer_callback(call["id"], "⏳ This request is already being processed.", show_alert=True)
                return
            if req_data:
                withdrawal_processing_ids.add(req_id)
        if not req_data:
            answer_callback(call["id"], "❌ Request already processed!", show_alert=True)
            return

        if str(req_data.get("status", "pending")).casefold() != "pending":
            answer_callback(call["id"], "❌ Request already processed!", show_alert=True)
            with withdrawal_processing_lock:
                withdrawal_processing_ids.discard(req_id)
            return

        finalized = False
        callback_answered = False
        display_request_id = f"#{_pending_withdrawal_serials().get(req_id, 1)}"
        try:
            u_id = req_data.get("user_id")
            amt = req_data.get("amount", 0)
            num = str(req_data.get("number", ""))
            full_name = req_data.get("full_name", u_id)
            serial = _pending_withdrawal_serials().get(req_id, 1)
            display_request_id = f"#{serial}"
            answer_callback(
                call["id"],
                f"⏳ Processing withdrawal {display_request_id}…",
                show_alert=False,
            )
            callback_answered = True

            status_text = "Approve" if action == "APPROVE" else "Rejected"
            emoji_icon_id = (
                "6224188445548356446"
                if action == "APPROVE"
                else "6224003980997962148"
            )
            status_method = req_data.get("method", "")
            status_method_key = re.sub(
                r"[^a-z]", "", str(status_method).casefold()
            )
            status_method_label = (
                "Bkash" if status_method_key == "bkash"
                else str(status_method)
            )

            if action == "REJECT":
                refund_ok = update_balance(
                    u_id, amt, reason=f"withdrawal_refund:{req_id}"
                )
                if not refund_ok:
                    send_message(
                        chat_id,
                        render_body_text(
                            f"❌ Refund failed for withdrawal {display_request_id}; "
                            "the request is still pending."
                        ),
                    )
                    return

            status_heading_icon = "6224024626905753921"
            user_icon = "6224428190622821133"
            amount_icon = "6222105571093389816"
            number_icon = "6224387014771352176"
            method_icon = "6224284210434154938"
            method_value_icon = withdrawal_method_emoji_id(status_method)
            new_text = (
                f'<tg-emoji emoji-id="{status_heading_icon}">💳</tg-emoji> '
                f"<b>Withdrawal {status_text}</b> "
                f'<tg-emoji emoji-id="{emoji_icon_id}">'
                f'{"✅" if action == "APPROVE" else "❌"}</tg-emoji>\n'
                f"{_premium_digit_text('1')} <b>ID:</b> "
                f"#{_premium_digit_text(serial)}\n"
                f'<tg-emoji emoji-id="{user_icon}">👤</tg-emoji> '
                f"<b>User :</b> <a href='tg://user?id={html.escape(str(u_id))}'>"
                f"{html.escape(str(full_name))}</a>\n"
                f'<tg-emoji emoji-id="{amount_icon}">💰</tg-emoji> '
                f"<b>Withdrawal:</b> {html.escape(str(amt))} TK\n"
                f'<tg-emoji emoji-id="{number_icon}">📱</tg-emoji> '
                f"<b>Number :</b> <code>{html.escape(num)}</code>\n"
                f'<tg-emoji emoji-id="{method_icon}">💳</tg-emoji> '
                f"<b>Method:</b> "
                f'<tg-emoji emoji-id="{method_value_icon}">💳</tg-emoji> '
                f"{html.escape(status_method_label)}"
            )
            kb = {"inline_keyboard": [[{
                "text": status_text,
                "icon_custom_emoji_id": emoji_icon_id,
                "callback_data": "ignore",
                "style": "success" if action == "APPROVE" else "danger",
            }]]}
            if history_return_page is None:
                edit_result = edit_message(
                    chat_id, msg_id, render_body_text(new_text), reply_markup=kb
                )
                if not isinstance(edit_result, dict) or not edit_result.get("ok"):
                    print(
                        f"⚠️ Could not update withdrawal card {req_id}: "
                        f"{edit_result.get('description', 'unknown error') if isinstance(edit_result, dict) else 'no Telegram API response'}"
                    )

            status = "approved" if action == "APPROVE" else "rejected"
            if db:
                try:
                    db.collection("withdrawals").document(req_id).update({
                        "status": status,
                        "processed_by": str(user_id_clicked),
                        "display_id_at_resolution": display_request_id,
                    })
                except Exception as exc:
                    print(f"⚠️ Could not save withdrawal status {req_id}: {exc}")
            record_history(
                u_id,
                "withdrawal_status",
                message=f"Withdrawal {status}: {amt} TK via {status_method}",
                amount=amt,
                status=status,
                method=status_method,
                request_id=req_id,
                payment_number=req_data.get("number", ""),
            )

            if action == "REJECT":
                send_message(
                    u_id,
                    render_body_text(
                        f"❌ Your <tg-emoji emoji-id=\"6224387014771352176\">💰</tg-emoji> "
                        f"{amt} TK withdrawal request was rejected. Balance refunded."
                    ),
                )
            else:
                send_message(
                    u_id,
                    render_body_text(
                        f"{PEM['ok']} Your "
                        f'<tg-emoji emoji-id="6224387014771352176">💰</tg-emoji> '
                        f"{amt} TK withdrawal request has been paid successfully."
                    ),
                )

            with withdrawal_processing_lock:
                pending_withdrawals.pop(req_id, None)
                withdrawal_processing_ids.discard(req_id)
            finalized = True
            _renumber_pending_withdrawal_messages()
            if history_return_page is not None:
                handle_callback({
                    **call,
                    "data": f"lb_w_history_page_{history_return_page}",
                    "_early_ack_scheduled": True,
                })
        except Exception as exc:
            print(f"⚠️ Could not process withdrawal {req_id}: {exc}")
            if not callback_answered:
                answer_callback(
                    call["id"],
                    "❌ Withdrawal processing failed. Check the request and try again.",
                    show_alert=True,
                )
            else:
                send_message(
                    chat_id,
                    render_body_text(
                        f"⚠️ Could not finish withdrawal {display_request_id}; "
                        "please check its status before retrying."
                    ),
                )
        finally:
            with withdrawal_processing_lock:
                withdrawal_processing_ids.discard(req_id)
                if finalized:
                    pending_withdrawals.pop(req_id, None)

# ==========================================
# Polling Loop
# ==========================================
def poll_otp_with_status(number_id, num_str, owner_id, api_key):
    headers = {"X-API-Key": api_key}
    for _ in range(150):
        try:
            res = requests.get(f"{STEX_BASE_URL}/api/v1/numbers/{number_id}/sms", headers=headers, timeout=10)
            data = res.json()
            if data.get("success") and data.get("otp"):
                otp = str(data["otp"])
                msg_text = data.get("message", f"Your code is {otp}")
                
                extracted_otp = extract_otp_code(msg_text)
                if extracted_otp and len(extracted_otp) > len(otp):
                    otp = extracted_otp
                    
                app_name = data.get("service", "StexSMS Service")
                detected_app = detect_service(msg_text)
                if detected_app:
                    app_name = detected_app
                
                unique_id = f"POLL_{number_id}_{otp}"
                if _remember_processed_otp(unique_id):
                    
                    char, iso = get_flag_and_code(num_str)
                    app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                    
                    global recent_traffic
                    current_time = time.time()
                    recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                    recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num_str, "time": current_time})
                    save_local_db()
                    
                    display_num = f"+{num_str}" if not str(num_str).startswith("+") else str(num_str)
                    masked = mask_number(display_num)
                    lang = detect_language(msg_text)
                    lang_name = (
                        LANG_MAP.get(lang, "English")
                        if "LANG_MAP" in globals()
                        else lang.replace("#", "")
                    )
                    display_msg = render_body_text(
                        f"{get_flag_info_html(display_num)} {iso} | "
                        f"{prem_app_html} {masked} | 💬 {lang_name}"
                    )
                    
                    send_otp_to_forward_groups(
                        display_msg, otp, num_str, app_name, "stex"
                    )
                    
                    inbox_msg = render_body_text(f"╔═══════════════╗\n║ {prem_app_html} {get_flag_info_html(display_num)} {display_num} {lang}\n╚═══════════════╝")
                    inbox_kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                    
                    reward = float(assigned_number_rates.get(num_str, bot_settings.get("otp_reward", 0.0)))
                    if reward > 0:
                        update_balance(owner_id, reward)
                        inbox_kb.append([{"text": f"Added {reward} tk", "icon_custom_emoji_id": GIFT_BOX_EMOJI_ID, "callback_data": "ignore", "style": "primary"}])
                    
                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})
                    
                    record_user_otp(owner_id, otp)
                break
        except: pass
        time.sleep(4)
# ==========================================
# AUTO DEMO SMS FORWARDER (same token, same groups)
# ==========================================
DEMO_LANGS = ["#EN", "#BN", "#AR", "#HI", "#FR", "#ID", "#ES"]
_demo_sent_keys = set()
_demo_service_cycle = []
_demo_service_cycle_lock = threading.Lock()


def _demo_service_key(value):
    """Normalize real traffic labels the same way as the traffic screen."""
    raw = html.unescape(re.sub(r"<[^>]*>", "", str(value or ""))).strip()
    if not raw:
        return None
    canonical = _canonical_traffic_service(raw)
    if canonical:
        return canonical
    display_name, _emoji = get_service_info_html(raw, raw)
    display_name = html.unescape(
        re.sub(r"<[^>]*>", "", str(display_name or ""))
    ).strip()
    if not re.search(r"[A-Z0-9]", display_name, re.IGNORECASE):
        display_name = raw
    display_name = re.sub(r"\s+", " ", display_name).strip()
    return display_name.upper() if re.search(
        r"[A-Z0-9]", display_name, re.IGNORECASE
    ) else None


def _next_demo_service(service_names):
    """Cycle through every eligible service before repeating one."""
    global _demo_service_cycle
    active = set(service_names)
    with _demo_service_cycle_lock:
        remaining = [
            service for service in _demo_service_cycle if service in active
        ]
        queued = set(remaining)
        remaining.extend(
            service for service in sorted(active) if service not in queued
        )
        if not remaining:
            remaining = sorted(active)
        selected = remaining.pop(0)
        _demo_service_cycle = remaining
        return selected


def generate_unique_demo_otp():
    """Generate demo OTPs only for services/countries currently rated MEDIUM/HIGH."""
    current_time = time.time()
    traffic_snapshot = [
        dict(item) for item in list(recent_traffic)
        if isinstance(item, dict)
    ]
    service_country_hits = {}

    # Match the live Traffic screen's 10-minute window and per-country
    # thresholds: LOW < 20, MEDIUM 20-29, HIGH >= 30.
    for item in traffic_snapshot:
        try:
            age = current_time - float(item.get("time", 0))
        except (TypeError, ValueError):
            continue
        if not 0 <= age <= 600:
            continue
        service = _demo_service_key(item.get("service", ""))
        iso = str(item.get("iso", "") or "").strip().upper()
        if not service or len(iso) != 2:
            continue
        country_counts = service_country_hits.setdefault(service, {})
        country_counts[iso] = country_counts.get(iso, 0) + 1

    # A service qualifies when at least one country is MEDIUM or HIGH and has
    # a usable phone prefix. Never substitute a random low-traffic service.
    prefix_by_iso = {}
    for flag_key, flag_data in bot_settings.get("premium_flags", {}).items():
        if not isinstance(flag_data, dict):
            continue
        iso = str(flag_data.get("iso", "") or "").strip().upper()
        prefix = re.sub(
            r"\D", "", _flag_calling_code(flag_key, flag_data)
        )
        if len(iso) == 2 and prefix:
            prefix_by_iso.setdefault(iso, prefix)

    eligible_countries = {}
    for service, country_counts in service_country_hits.items():
        eligible = {
            iso: count for iso, count in country_counts.items()
            if count >= 20 and iso in prefix_by_iso
        }
        if eligible:
            eligible_countries[service] = eligible

    if not eligible_countries:
        return None

    service = _next_demo_service(eligible_countries)
    iso_hits = eligible_countries[service]
    chosen_iso = random.choices(
        list(iso_hits), weights=list(iso_hits.values()), k=1
    )[0]
    country_code = prefix_by_iso[chosen_iso]

    # Keep the existing unique number, OTP and language generation behavior.
    for _ in range(200):
        rest_len = random.choice([7, 8, 9])
        rest = "".join([str(random.randint(0, 9)) for _ in range(rest_len)])
        number = f"{country_code}{rest}"

        otp_len = random.choice([5, 6])
        otp = "".join([str(random.randint(0, 9)) for _ in range(otp_len)])

        lang = random.choice(DEMO_LANGS)

        unique_key = f"{number}_{otp}_{service}"
        if unique_key not in _demo_sent_keys:
            _demo_sent_keys.add(unique_key)
            if len(_demo_sent_keys) > 5000:
                _demo_sent_keys.clear()
            return number, otp, service, lang

    return None


def send_demo_otp_to_groups():
    """Tomar asol global_sms_listener er hubohu format e demo OTP pathay"""
    generated = generate_unique_demo_otp()
    if generated is None:
        return None
    number, otp, service, lang = generated

    char, iso = get_flag_and_code(number)
    app_full_name, prem_app_html = get_service_info_html(service, service)

    display_num = f"+{number}" if not str(number).startswith("+") else str(number)
    masked = mask_number(display_num)
    lang_name = LANG_MAP.get(lang, "English") if "LANG_MAP" in globals() else lang.replace("#", "")

    display_msg = render_body_text(
        f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {masked} | 💬 {lang_name}"
    )

    send_otp_to_forward_groups(
        display_msg, otp, number, service, "auto"
    )

    return service, number, otp


def demo_forwarder_thread():
    """Admin panel theke ON korle proti N second e demo OTP pathay"""
    print("🎭 Demo SMS Forwarder thread started (standby)")
    while True:
        try:
            if bot_settings.get("demo_on", False):
                interval = max(1, int(bot_settings.get("demo_interval", 2)))
                send_demo_otp_to_groups()
                time.sleep(interval)
            else:
                time.sleep(1)
        except Exception as exc:
            print(f"⚠️ Demo forwarder error: {exc}")
            time.sleep(2)


def stex_console_listener():
    global recent_traffic, bot_settings
    seen_console_hits = set()
    last_auto_update = time.time()
    
    while True:
        try:
            stex_keys = bot_settings.get("stex_keys", [])
            if stex_keys:
                api_key = stex_keys[0]
                headers = {"mauthapi": api_key}
                res = requests.get(f"{STEX_BASE_URL}/console", headers=headers, timeout=10)
                data = res.json()
                
                if data.get("meta", {}).get("code") == 200 and data.get("data", {}).get("hits"):
                    current_time = time.time()
                    new_hits = False
                    
                    for hit in data["data"]["hits"]:
                        range_str = str(hit.get("range", "")).replace("X", "")
                        if len(range_str) > 9:
                            range_str = range_str[:9]
                        sid = str(hit.get("sid", "Unknown"))
                        msg = str(hit.get("message", ""))
                        hit_time = hit.get("time", current_time * 1000) / 1000.0
                        
                        unique_hit = f"STEX_{range_str}_{sid}_{hit.get('time', 0)}"
                        if unique_hit not in seen_console_hits and range_str:
                            seen_console_hits.add(unique_hit)
                            if len(seen_console_hits) > 2000: seen_console_hits.clear()
                            
                            char, iso = get_flag_and_code(range_str)
                            app_full_name, _ = get_service_info_html(sid, msg)
                            
                            recent_traffic.append({
                                "service": app_full_name,
                                "iso": iso,
                                "flag": char,
                                "number": f"{range_str}XXX", 
                                "time": hit_time,
                                "real_range": range_str
                            })
                            new_hits = True
                            
                    if new_hits:
                        recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                        save_local_db()
                        
                    if bot_settings.get("stex_auto", False) and current_time - last_auto_update > 120:
                        last_auto_update = current_time
                        changed = False
                        
                        if "stex_services" not in bot_settings: bot_settings["stex_services"] = {}
                        if "search_countries" not in bot_settings: bot_settings["search_countries"] = []
                        
                        srv_counts = Counter(t["service"].upper() for t in recent_traffic if "real_range" in t)
                        top_srvs = [s for s, c in srv_counts.most_common(6)]
                        
                        for srv in top_srvs:
                            if srv not in bot_settings["stex_services"]:
                                bot_settings["stex_services"][srv] = {}
                                changed = True
                                
                            iso_counts = Counter(t["iso"] for t in recent_traffic if t.get("service", "").upper() == srv and "real_range" in t)
                            top_isos = [i for i, c in iso_counts.most_common(3)]
                            
                            for iso in top_isos:
                                full_country_name = get_flag_info_html(iso, return_full_name=True).title()
                                if full_country_name not in bot_settings["stex_services"][srv]:
                                    bot_settings["stex_services"][srv][full_country_name] = []
                                    changed = True
                                    
                                rng_counts = Counter(t["real_range"] for t in recent_traffic if t.get("service", "").upper() == srv and t.get("iso") == iso and "real_range" in t)
                                top_rngs = [r for r, c in rng_counts.most_common(2)]
                                
                                for rng in top_rngs:
                                    if rng not in bot_settings["stex_services"][srv][full_country_name]:
                                        bot_settings["stex_services"][srv][full_country_name].append(rng)
                                        changed = True
                                        
                                    country_code = rng[:3]
                                    if country_code not in bot_settings["search_countries"]:
                                        bot_settings["search_countries"].append(country_code)
                                        changed = True

                        services_to_remove = []
                        for srv, countries in list(bot_settings["stex_services"].items()):
                            srv_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and "real_range" in t and current_time - t.get("time", 0) <= 120)
                            if srv_hit < 1:
                                services_to_remove.append(srv)
                                continue
                            
                            countries_to_remove = []
                            for country, ranges in list(countries.items()):
                                c_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and get_flag_info_html(t.get("iso"), return_full_name=True).title() == country and "real_range" in t and current_time - t.get("time", 0) <= 120)
                                if c_hit < 1:
                                    countries_to_remove.append(country)
                                    continue
                                
                                ranges_to_remove = []
                                for rng in ranges:
                                    r_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and t.get("real_range") == rng and current_time - t.get("time", 0) <= 120)
                                    if r_hit < 1: 
                                        ranges_to_remove.append(rng)
                                
                                for r in ranges_to_remove:
                                    ranges.remove(r)
                                    changed = True
                                    
                            for c in countries_to_remove:
                                del bot_settings["stex_services"][srv][c]
                                changed = True
                                
                        for s in services_to_remove:
                            del bot_settings["stex_services"][s]
                            changed = True
                            
                        if changed:
                            save_db()
                            
        except Exception as e:
            pass
        time.sleep(10)

def voltx_console_listener():
    global recent_traffic, bot_settings
    seen_console_hits = set()
    last_auto_update = time.time()
    
    while True:
        try:
            if not bot_settings.get("voltx_on", True):
                time.sleep(5)
                continue
            voltx_keys = bot_settings.get("voltx_keys", [])
            if voltx_keys:
                api_key = voltx_keys[0]
                headers = {"mauthapi": api_key}
                res = requests.get(f"{VOLTX_BASE_URL}/console", headers=headers, timeout=10)
                data = res.json()
                
                if data.get("meta", {}).get("code") == 200 and data.get("data", {}).get("hits"):
                    current_time = time.time()
                    new_hits = False
                    
                    for hit in data["data"]["hits"]:
                        range_str = str(hit.get("range", "")).replace("X", "")
                        if len(range_str) > 9:
                            range_str = range_str[:9]
                        sid = str(hit.get("sid", "Unknown"))
                        msg = str(hit.get("message", ""))
                        hit_time = hit.get("time", current_time * 1000) / 1000.0
                        
                        unique_hit = f"{range_str}_{sid}_{hit.get('time', 0)}"
                        if unique_hit not in seen_console_hits and range_str:
                            seen_console_hits.add(unique_hit)
                            if len(seen_console_hits) > 2000: seen_console_hits.clear()
                            
                            char, iso = get_flag_and_code(range_str)
                            app_full_name, _ = get_service_info_html(sid, msg)
                            
                            recent_traffic.append({
                                "service": app_full_name,
                                "iso": iso,
                                "flag": char,
                                "number": f"{range_str}XXX", 
                                "time": hit_time,
                                "real_range": range_str
                            })
                            new_hits = True
                            
                    if new_hits:
                        recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                        save_local_db()
                        
                    if bot_settings.get("voltx_auto", False) and current_time - last_auto_update > 120:
                        last_auto_update = current_time
                        changed = False
                        
                        if "voltx_services" not in bot_settings: bot_settings["voltx_services"] = {}
                        if "voltx_search_countries" not in bot_settings: bot_settings["voltx_search_countries"] = []
                        
                        srv_counts = Counter(t["service"].upper() for t in recent_traffic if "real_range" in t)
                        top_srvs = [s for s, c in srv_counts.most_common(6)]
                        
                        for srv in top_srvs:
                            if srv not in bot_settings["voltx_services"]:
                                bot_settings["voltx_services"][srv] = {}
                                changed = True
                                
                            iso_counts = Counter(t["iso"] for t in recent_traffic if t.get("service", "").upper() == srv and "real_range" in t)
                            top_isos = [i for i, c in iso_counts.most_common(3)]
                            
                            for iso in top_isos:
                                full_country_name = get_flag_info_html(iso, return_full_name=True).title()
                                if full_country_name not in bot_settings["voltx_services"][srv]:
                                    bot_settings["voltx_services"][srv][full_country_name] = []
                                    changed = True
                                    
                                rng_counts = Counter(t["real_range"] for t in recent_traffic if t.get("service", "").upper() == srv and t.get("iso") == iso and "real_range" in t)
                                top_rngs = [r for r, c in rng_counts.most_common(2)]
                                
                                for rng in top_rngs:
                                    if rng not in bot_settings["voltx_services"][srv][full_country_name]:
                                        bot_settings["voltx_services"][srv][full_country_name].append(rng)
                                        changed = True
                                        
                                    country_code = rng[:3]
                                    if country_code not in bot_settings["voltx_search_countries"]:
                                        bot_settings["voltx_search_countries"].append(country_code)
                                        changed = True

                        services_to_remove = []
                        for srv, countries in list(bot_settings["voltx_services"].items()):
                            srv_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and "real_range" in t and current_time - t.get("time", 0) <= 120)
                            if srv_hit < 1:
                                services_to_remove.append(srv)
                                continue
                            
                            countries_to_remove = []
                            for country, ranges in list(countries.items()):
                                c_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and get_flag_info_html(t.get("iso"), return_full_name=True).title() == country and "real_range" in t and current_time - t.get("time", 0) <= 120)
                                if c_hit < 1:
                                    countries_to_remove.append(country)
                                    continue
                                
                                ranges_to_remove = []
                                for rng in ranges:
                                    r_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and t.get("real_range") == rng and current_time - t.get("time", 0) <= 120)
                                    if r_hit < 1: 
                                        ranges_to_remove.append(rng)
                                
                                for r in ranges_to_remove:
                                    ranges.remove(r)
                                    changed = True
                                    
                            for c in countries_to_remove:
                                del bot_settings["voltx_services"][srv][c]
                                changed = True
                                
                        for s in services_to_remove:
                            del bot_settings["voltx_services"][s]
                            changed = True
                            
                        if changed:
                            save_db()
                            
        except Exception as e:
            pass
        time.sleep(10)

def voltx_sms_listener():
    global processed_otps, recent_traffic, voltx_assigned_numbers
    while True:
        try:
            voltx_keys = bot_settings.get("voltx_keys", [])
            for api_key in voltx_keys:
                try:
                    headers = {"mauthapi": api_key}
                    res = requests.get(f"{VOLTX_BASE_URL}/success-otp", headers=headers, timeout=10)
                    resp_data = res.json()
                    
                    if resp_data.get("meta", {}).get("code") == 200 and "data" in resp_data and "otps" in resp_data["data"]:
                        for item in resp_data["data"]["otps"]:
                            num = str(item.get("number", "")).replace("+", "")
                            msg_text = str(item.get("message", ""))
                            otp = extract_otp_code(msg_text) or "CODE"
                            otp_id = str(item.get("otp_id", otp))
                            
                            app_name = "Voltx Service"
                            detected_app = detect_service(msg_text)
                            if detected_app: app_name = detected_app
                                
                            unique_id = f"VOLTX_{num}_{otp_id}"
                            
                            if num and _remember_processed_otp(unique_id):
                                
                                char, iso = get_flag_and_code(num)
                                app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                                current_time = time.time()
                                
                                recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                                recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                                save_local_db()
                                
                                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                                masked = mask_number(display_num)
                                lang = detect_language(msg_text)
                                
                                lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")
                                display_msg = render_body_text(f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {masked} | 💬 {lang_name}")
                                
                                send_otp_to_forward_groups(
                                    display_msg, otp, num, app_full_name, "voltx"
                                )
                                    
                                owner_id = None
                                clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                
                                for uid, session_data in user_active_sessions.items():
                                    for act_num in session_data.get("nums", []):
                                        act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                            owner_id = uid
                                            break
                                    if owner_id: break
                                    
                                if not owner_id:
                                    for vtx_n, n_owner in voltx_assigned_numbers.items():
                                        clean_vtx = str(vtx_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if clean_vtx == clean_api_num or (len(clean_vtx) >= 8 and clean_vtx.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_vtx[-8:])):
                                            owner_id = n_owner
                                            break
                                        
                                if owner_id:
                                    lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")
                                    inbox_msg = render_body_text(f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {display_num} | 💬 {lang_name}")
                                    inbox_kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                                    
                                    reward = float(assigned_number_rates.get(num, bot_settings.get("otp_reward", 0.0)))
                                    if reward > 0:
                                        update_balance(owner_id, reward)
                                        inbox_kb.append([{"text": f"Added {reward} tk", "icon_custom_emoji_id": GIFT_BOX_EMOJI_ID, "callback_data": "ignore", "style": "primary"}])
                                    
                                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})
                                    
                                    record_user_otp(owner_id, otp)
                except: pass
        except: pass
        time.sleep(5)

def zenex_sms_listener():
    global processed_otps, recent_traffic, zenex_assigned_numbers
    while True:
        try:
            zenex_keys = bot_settings.get("zenex_keys", [])
            for api_key in zenex_keys:
                try:
                    headers = {"mapikey": api_key}
                    res = requests.get(f"{ZENEX_BASE_URL}/v1/numsuccess/info", headers=headers, timeout=10)
                    resp_data = res.json()
                    
                    if resp_data.get("meta", {}).get("code") == 200 and "data" in resp_data and "otps" in resp_data["data"]:
                        for item in resp_data["data"]["otps"]:
                            num = str(item.get("number", "")).replace("+", "")
                            msg_text = str(item.get("otp", ""))
                            otp = extract_otp_code(msg_text) or "CODE"
                            otp_id = str(item.get("nid", otp))
                            
                            app_name = "Zenex Service"
                            detected_app = detect_service(msg_text)
                            if detected_app: app_name = detected_app
                                
                            unique_id = f"ZENEX_{num}_{otp_id}"
                            
                            if num and _remember_processed_otp(unique_id):
                                
                                char, iso = get_flag_and_code(num)
                                app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                                current_time = time.time()
                                
                                recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                                recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                                save_local_db()
                                
                                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                                masked = mask_number(display_num)
                                lang = detect_language(msg_text)
                                
                                lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")
                                display_msg = render_body_text(f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {masked} | 💬 {lang_name}")
                                
                                send_otp_to_forward_groups(
                                    display_msg, otp, num, app_full_name, "zenex"
                                )
                                    
                                owner_id = None
                                clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                
                                for uid, session_data in user_active_sessions.items():
                                    for act_num in session_data.get("nums", []):
                                        act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                            owner_id = uid
                                            break
                                    if owner_id: break
                                    
                                if not owner_id:
                                    for znx_n, n_owner in zenex_assigned_numbers.items():
                                        clean_znx = str(znx_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if clean_znx == clean_api_num or (len(clean_znx) >= 8 and clean_znx.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_znx[-8:])):
                                            owner_id = n_owner
                                            break
                                        
                                if owner_id:
                                    inbox_msg = render_body_text(f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {display_num} | 💬 {lang_name}")
                                    inbox_kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                                    
                                    reward = float(assigned_number_rates.get(num, bot_settings.get("otp_reward", 0.0)))
                                    if reward > 0:
                                        update_balance(owner_id, reward)
                                        inbox_kb.append([{"text": f"Added {reward} tk", "icon_custom_emoji_id": GIFT_BOX_EMOJI_ID, "callback_data": "ignore", "style": "primary"}])
                                    
                                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})
                                    
                                    record_user_otp(owner_id, otp)
                except: pass
        except: pass
        time.sleep(5)

def fastx_sms_listener():
    """Poll FastX OTPs and deliver each new code through the existing inbox flow."""
    global processed_otps, recent_traffic
    while True:
        try:
            keys = bot_settings.get("fastx_keys", [])
            if isinstance(keys, str):
                keys = [keys]
            keys = [str(key).strip() for key in keys if str(key).strip()]
            if not keys and os.getenv("FASTXOTP_API_KEY", "").strip():
                keys = [os.getenv("FASTXOTP_API_KEY", "").strip()]

            for api_key in keys[:3]:
                try:
                    response = requests.get(
                        f"{FASTX_BASE_URL}/api/otps",
                        headers={"X-API-Key": api_key},
                        timeout=(1.5, 4.0),
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if isinstance(payload, list):
                        otps = payload
                    elif isinstance(payload, dict):
                        data = payload.get("data")
                        if isinstance(data, dict):
                            otps = data.get("otps") or data.get("active") or []
                        elif isinstance(data, list):
                            otps = data
                        else:
                            otps = payload.get("otps") or payload.get("active") or []
                    else:
                        otps = []

                    for item in otps if isinstance(otps, list) else []:
                        if not isinstance(item, dict):
                            continue
                        number = _canonical_number(item.get("number", ""))
                        if not number:
                            continue
                        sms_text = str(item.get("message") or item.get("sms") or "").strip()
                        raw_otp = str(item.get("otp") or "").strip()
                        if raw_otp.isdigit() and 3 <= len(raw_otp) <= 8:
                            otp = raw_otp
                            sms_text = sms_text or f"OTP: {otp}"
                        else:
                            sms_text = sms_text or raw_otp
                            otp = extract_otp_code(sms_text)
                        if not otp or otp == "N/A":
                            continue

                        otp_id = str(
                            item.get("otp_id") or item.get("nid") or item.get("id")
                            or f"{number}_{otp}"
                        )
                        unique_id = f"FASTX_{number}_{otp_id}"
                        if not _remember_processed_otp(unique_id):
                            continue

                        service = (
                            item.get("service") or item.get("sid") or item.get("app")
                            or detect_service(sms_text) or "FastX Service"
                        )
                        app_name, premium_app = get_service_info_html(service, sms_text)
                        current_time = time.time()
                        char, iso = get_flag_and_code(number)
                        recent_traffic = [
                            traffic for traffic in recent_traffic
                            if current_time - traffic.get("time", 0) <= 3600
                        ]
                        recent_traffic.append({
                            "service": app_name,
                            "iso": iso,
                            "flag": char,
                            "number": number,
                            "time": current_time,
                            "panel": "fastx",
                        })
                        save_local_db()

                        display_number = f"+{number}"
                        lang = detect_language(sms_text)
                        lang_name = LANG_MAP.get(lang, "English") if "LANG_MAP" in globals() else lang.replace("#", "")
                        masked = mask_number(display_number)
                        group_text = render_body_text(
                            f"{get_flag_info_html(display_number)} {iso} | "
                            f"{premium_app} {masked} | 💬 {lang_name}"
                        )
                        send_otp_to_forward_groups(
                            group_text, otp, number, app_name, "fastx"
                        )

                        owner_id = None
                        for user_id, session in list(user_active_sessions.items()):
                            for active_number in session.get("nums", []):
                                if _canonical_number(active_number) == number:
                                    owner_id = user_id
                                    break
                            if owner_id:
                                break
                        if not owner_id:
                            for assigned_number, assigned_owner in list(fastx_assigned_numbers.items()):
                                if _canonical_number(assigned_number) == number:
                                    owner_id = assigned_owner
                                    break
                        if owner_id:
                            inbox_text = render_body_text(
                                f"{get_flag_info_html(display_number)} {iso} | "
                                f"{premium_app} {display_number} | 💬 {lang_name}"
                            )
                            inbox_keyboard = [[{
                                "text": str(otp),
                                "icon_custom_emoji_id": "5353022963132174959",
                                "copy_text": {"text": str(otp)},
                                "style": "success",
                            }]]
                            reward = float(
                                assigned_number_rates.get(
                                    number, bot_settings.get("otp_reward", 0.0)
                                )
                            )
                            if reward > 0:
                                update_balance(owner_id, reward)
                                inbox_keyboard.append([{
                                    "text": f"Added {reward} tk",
                                    "icon_custom_emoji_id": GIFT_BOX_EMOJI_ID,
                                    "callback_data": "ignore",
                                    "style": "primary",
                                }])
                            send_message(
                                owner_id,
                                inbox_text,
                                reply_markup={"inline_keyboard": inbox_keyboard},
                            )
                            record_user_otp(owner_id, str(otp))
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(5)


def global_sms_listener():
    global processed_otps, recent_traffic, stex_assigned_numbers
    while True:
        try:
            stex_keys = bot_settings.get("stex_keys", [])
            for api_key in stex_keys:
                try:
                    headers = {"mauthapi": api_key}
                    res = requests.get(f"{STEX_BASE_URL}/success-otp", headers=headers, timeout=10)
                    resp_data = res.json()
                    
                    if resp_data.get("meta", {}).get("code") == 200 and "data" in resp_data and "otps" in resp_data["data"]:
                        for item in resp_data["data"]["otps"]:
                            num = str(item.get("number", "")).replace("+", "")
                            msg_text = str(item.get("message", ""))
                            otp = extract_otp_code(msg_text) or "CODE"
                            otp_id = str(item.get("otp_id", otp))
                            
                            app_name = "Stex Service"
                            detected_app = detect_service(msg_text)
                            if detected_app: app_name = detected_app
                                
                            unique_id = f"STEX_{num}_{otp_id}"
                            
                            if num and _remember_processed_otp(unique_id):
                                
                                char, iso = get_flag_and_code(num)
                                app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                                current_time = time.time()
                                
                                recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                                recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                                save_local_db()
                                
                                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                                masked = mask_number(display_num)
                                lang = detect_language(msg_text)
                                
                                lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")
                                display_msg = render_body_text(f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {masked} | 💬 {lang_name}")
                                
                                send_otp_to_forward_groups(
                                    display_msg, otp, num, app_full_name, "stex"
                                )
                                    
                                owner_id = None
                                clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                
                                for uid, session_data in user_active_sessions.items():
                                    for act_num in session_data.get("nums", []):
                                        act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if act_clean == clean_api_num or (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:])):
                                            owner_id = uid
                                            break
                                    if owner_id: break
                                    
                                if not owner_id:
                                    for stex_n, n_owner in stex_assigned_numbers.items():
                                        clean_stex = str(stex_n).replace("+", "").replace(" ", "").replace("-", "").strip()
                                        if clean_stex == clean_api_num or (len(clean_stex) >= 8 and clean_stex.endswith(clean_api_num[-8:])) or (len(clean_api_num) >= 8 and clean_api_num.endswith(clean_stex[-8:])):
                                            owner_id = n_owner
                                            break
                                        
                                if owner_id:
                                    lang_name = LANG_MAP.get(lang, "English") if 'LANG_MAP' in globals() else lang.replace("#", "")
                                    inbox_msg = render_body_text(f"{get_flag_info_html(display_num)} {iso} | {prem_app_html} {display_num} | 💬 {lang_name}")
                                    inbox_kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                                    
                                    reward = float(assigned_number_rates.get(num, bot_settings.get("otp_reward", 0.0)))
                                    if reward > 0:
                                        update_balance(owner_id, reward)
                                        inbox_kb.append([{"text": f"Added {reward} tk", "icon_custom_emoji_id": GIFT_BOX_EMOJI_ID, "callback_data": "ignore", "style": "primary"}])
                                    
                                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})
                                    
                                    record_user_otp(owner_id, otp)
                except: pass
        except: pass
        time.sleep(5)

def zenex_console_listener():
    global recent_traffic, bot_settings
    last_auto_update = time.time()
    zenex_last_hits = {} 
    
    while True:
        try:
            zenex_keys = bot_settings.get("zenex_keys", [])
            if zenex_keys:
                api_key = zenex_keys[0]
                headers = {"mapikey": api_key}
                res = requests.get(f"{ZENEX_BASE_URL}/v1/active-ranges", headers=headers, timeout=10)
                data = res.json()
                
                if data.get("success") and "data" in data and "active_ranges" in data["data"]:
                    current_time = time.time()
                    new_hits_added = False
                    
                    for hit in data["data"]["active_ranges"]:
                        range_str = str(hit.get("range", "")).replace("X", "").replace("x", "")
                        sid = str(hit.get("service", "Unknown")).upper()
                        hits_count = int(hit.get("hits", 1))
                        
                        if range_str:
                            char, iso = get_flag_and_code(range_str)
                            app_full_name, _ = get_service_info_html(sid, "")
                            
                            range_key = f"{range_str}_{app_full_name}"
                            prev_hits = zenex_last_hits.get(range_key, 0)
                            
                            if hits_count > prev_hits:
                                new_hits = hits_count - prev_hits
                            else:
                                new_hits = hits_count
                                
                            zenex_last_hits[range_key] = hits_count
                            if new_hits > 150: new_hits = 150
                            
                            for _ in range(new_hits):
                                recent_traffic.append({
                                    "service": app_full_name,
                                    "iso": iso,
                                    "flag": char,
                                    "number": f"{range_str}XXX", 
                                    "time": current_time,
                                    "real_range": range_str,
                                    "source": "zenex"
                                })
                                new_hits_added = True
                            
                    if new_hits_added:
                        recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                        save_local_db()
                        
                    if bot_settings.get("zenex_auto", False) and current_time - last_auto_update > 120:
                        last_auto_update = current_time
                        changed = False
                        
                        if "zenex_services" not in bot_settings: bot_settings["zenex_services"] = {}
                        if "zenex_search_countries" not in bot_settings: bot_settings["zenex_search_countries"] = []
                        
                        srv_counts = Counter(t["service"].upper() for t in recent_traffic if t.get("source") == "zenex" and "real_range" in t)
                        top_srvs = [s for s, c in srv_counts.most_common(6)]
                        
                        for srv in top_srvs:
                            if srv not in bot_settings["zenex_services"]:
                                bot_settings["zenex_services"][srv] = {}
                                changed = True
                                
                            iso_counts = Counter(t["iso"] for t in recent_traffic if t.get("service", "").upper() == srv and t.get("source") == "zenex" and "real_range" in t)
                            top_isos = [i for i, c in iso_counts.most_common(3)]
                            
                            for iso in top_isos:
                                full_country_name = get_flag_info_html(iso, return_full_name=True).title()
                                if full_country_name not in bot_settings["zenex_services"][srv]:
                                    bot_settings["zenex_services"][srv][full_country_name] = []
                                    changed = True
                                    
                                rng_counts = Counter(t["real_range"] for t in recent_traffic if t.get("service", "").upper() == srv and t.get("iso") == iso and t.get("source") == "zenex" and "real_range" in t)
                                top_rngs = [r for r, c in rng_counts.most_common(2)]
                                
                                for rng in top_rngs:
                                    if rng not in bot_settings["zenex_services"][srv][full_country_name]:
                                        bot_settings["zenex_services"][srv][full_country_name].append(rng)
                                        changed = True
                                        
                                    country_code = rng[:3]
                                    if country_code not in bot_settings["zenex_search_countries"]:
                                        bot_settings["zenex_search_countries"].append(country_code)
                                        changed = True

                        services_to_remove = []
                        for srv, countries in list(bot_settings["zenex_services"].items()):
                            srv_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and t.get("source") == "zenex" and "real_range" in t and current_time - t.get("time", 0) <= 120)
                            if srv_hit < 1:
                                services_to_remove.append(srv)
                                continue
                            
                            countries_to_remove = []
                            for country, ranges in list(countries.items()):
                                c_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and get_flag_info_html(t.get("iso"), return_full_name=True).title() == country and t.get("source") == "zenex" and "real_range" in t and current_time - t.get("time", 0) <= 120)
                                if c_hit < 1:
                                    countries_to_remove.append(country)
                                    continue
                                
                                ranges_to_remove = []
                                for rng in ranges:
                                    r_hit = sum(1 for t in recent_traffic if t.get("service", "").upper() == srv.upper() and t.get("real_range") == rng and t.get("source") == "zenex" and current_time - t.get("time", 0) <= 120)
                                    if r_hit < 1: 
                                        ranges_to_remove.append(rng)
                                
                                for r in ranges_to_remove:
                                    ranges.remove(r)
                                    changed = True
                                    
                            for c in countries_to_remove:
                                del bot_settings["zenex_services"][srv][c]
                                changed = True
                                
                        for s in services_to_remove:
                            del bot_settings["zenex_services"][s]
                            changed = True
                            
                        if changed:
                            save_db()
                            
        except Exception as e:
            pass
        time.sleep(10)


def start_health_server():
    """Keep Render/UptimeRobot health checks green without a web framework."""
    port = 10000

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/health", "/healthz"):
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps({
                "ok": True,
                "service": "gx-number-bot",
                "database": "local_json",
                "persistent_storage": (
                    "BOT_DATA_DIR set; volume durability not verified"
                    if _BOT_DATA_DIR_CONFIGURED
                    else "Unconfigured local filesystem (may be ephemeral)"
                ),
                "bot_namespace": BOT_NAMESPACE,
                "process_id": os.getpid(),
                "storage_path": BOT_DATA_DIR,
                "database_files": {
                    filename: (
                        os.path.getsize(os.path.join(BOT_DATA_DIR, filename))
                        if os.path.isfile(os.path.join(BOT_DATA_DIR, filename))
                        else 0
                    )
                    for filename in _LOCAL_COLLECTION_FILES.values()
                },
                "time": datetime.utcnow().isoformat() + "Z"
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"🌐 Health server listening on port {port}")
        threading.Thread(target=server.serve_forever, daemon=True).start()
    except Exception as exc:
        print(f"⚠️ Health server could not start: {exc}")


def monthly_reset_thread():
    while True:
        try:
            ensure_monthly_data_reset()
        except Exception as exc:
            print(f"⚠️ Monthly reset check failed: {exc}")
        time.sleep(60)


def register_admin_commands():
    """Register public bonus toggles and utilities for admins."""
    public_commands = [
        {"command": "start", "description": "Open the user menu"},
        {
            "command": "bonusalert",
            "description": "Check or set bonus alerts (on/off)",
        },
        {
            "command": "otpbonus_on",
            "description": "Turn referral OTP bonus notifications on",
        },
        {
            "command": "otpbonus_off",
            "description": "Turn referral OTP bonus notifications off",
        },
    ]
    # All-private-chat scope is more specific than default and is therefore
    # shown consistently in normal users' command menus, even when a chat has
    # its own language or command-scope settings.
    for public_scope in ({"type": "all_private_chats"}, {"type": "default"}):
        existing_public = api_call("getMyCommands", {"scope": public_scope})
        public_command_map = {}
        if isinstance(existing_public, dict) and existing_public.get("ok"):
            for item in existing_public.get("result", []):
                if isinstance(item, dict) and item.get("command"):
                    command_name = str(item["command"]).casefold()
                    if command_name != "start":
                        public_command_map[command_name] = item
        for item in public_commands:
            public_command_map[item["command"]] = item
        start_command = public_command_map.pop(
            "start",
            {"command": "start", "description": "Open the user menu"},
        )
        # Telegram command identifiers must remain plain lowercase ASCII;
        # style every visible description to match the bot's button font.
        commands_to_set = [start_command, *public_command_map.values()]
        for command_item in commands_to_set:
            if isinstance(command_item.get("description"), str):
                command_item["description"] = small_caps_button_text(
                    command_item["description"]
                )
        public_result = api_call(
            "setMyCommands",
            {
                "scope": public_scope,
                "commands": commands_to_set,
            },
        )
        if not isinstance(public_result, dict) or not public_result.get("ok"):
            description = (
                public_result.get("description", "unknown error")
                if isinstance(public_result, dict)
                else "no Telegram API response"
            )
            print(
                "⚠️ Could not register public OTP bonus commands "
                f"for {public_scope['type']}: {description}"
            )

    command_scope_defaults = [
        {"command": "start", "description": "Start or reopen the bot menu"},
    ]
    admin_commands = [
        {"command": "localdb", "description": "Show local database status"},
        {"command": "withdraw", "description": "Toggle or set withdrawals on/off"},
        {"command": "numshare", "description": "Set the Num/Share value"},
        {
            "command": "bonusalert",
            "description": "Check or set bonus alerts (on/off)",
        },
    ]
    for admin_id in get_configured_admin_ids():
        scope = {"type": "chat", "chat_id": int(admin_id)}
        existing = api_call("getMyCommands", {"scope": scope})
        command_map = {}
        if isinstance(existing, dict) and existing.get("ok"):
            for item in existing.get("result", []):
                if isinstance(item, dict) and item.get("command"):
                    command_map[str(item["command"]).casefold()] = item
        for command_name in ("back", "otpbonus_on", "otpbonus_off"):
            command_map.pop(command_name, None)
        for item in command_scope_defaults:
            command_map.setdefault(item["command"], item)
        for item in admin_commands:
            command_map[item["command"]] = item
        start_command = command_map.pop("start", {
            "command": "start",
            "description": "Start or reopen the bot menu",
        })
        commands_to_set = [start_command, *command_map.values()]
        for command_item in commands_to_set:
            if isinstance(command_item.get("description"), str):
                command_item["description"] = small_caps_button_text(
                    command_item["description"]
                )

        result = api_call(
            "setMyCommands",
            {"scope": scope, "commands": commands_to_set},
        )
        if not isinstance(result, dict) or not result.get("ok"):
            description = (
                result.get("description", "unknown error")
                if isinstance(result, dict)
                else "no Telegram API response"
            )
            print(f"⚠️ Could not register admin commands for {admin_id}: {description}")


def main():
    global BOT_USERNAME
    if not TOKEN:
        print("❌ BOT_TOKEN is missing. Add it as a deployment secret.")
        return
    try:
        load_db()
        ensure_monthly_data_reset()
        save_db()
    except Exception as exc:
        print(f"❌ Local database could not be loaded safely: {exc}")
        return
    print(f"✅ Loaded local JSON data from {BOT_DATA_DIR}")
    try:
        signal.signal(signal.SIGTERM, _handle_termination_signal)
    except (ValueError, OSError):
        pass
    threading.Thread(
        target=_periodic_local_autosave_worker,
        name="local-database-autosave",
        daemon=True,
    ).start()
    start_health_server()
    threading.Thread(target=monthly_reset_thread, daemon=True).start()
    threading.Thread(target=live_range_refresh_thread, daemon=True).start()
    res = api_call("getMe")
    if res.get("ok"): BOT_USERNAME = res["result"]["username"]
    print(f"🤖 Bot is starting... @{BOT_USERNAME}")
    threading.Thread(
        target=register_admin_commands,
        name="telegram-admin-command-registration",
        daemon=True,
    ).start()

    threading.Thread(target=global_sms_listener, daemon=True).start()
    threading.Thread(target=stex_console_listener, daemon=True).start()
    threading.Thread(target=fastx_sms_listener, daemon=True).start()
    threading.Thread(target=demo_forwarder_thread, daemon=True).start()
    print("🎭 Demo SMS Forwarder Started!")
    threading.Thread(target=voltx_sms_listener, daemon=True).start()
    threading.Thread(target=voltx_console_listener, daemon=True).start()
    threading.Thread(target=zenex_sms_listener, daemon=True).start()
    threading.Thread(target=zenex_console_listener, daemon=True).start()
    print("📡 Background APIs & Global SMS Listener Started!")

    # These handlers often wait on Telegram/local database I/O. Keep bounded,
    # separate user/admin pools so slow operations do not queue other buttons.
    message_executor = ThreadPoolExecutor(
        max_workers=32,
        thread_name_prefix="telegram-message",
    )
    admin_message_executor = ThreadPoolExecutor(
        max_workers=8,
        thread_name_prefix="telegram-admin-message",
    )
    callback_executor = ThreadPoolExecutor(
        max_workers=24,
        thread_name_prefix="telegram-button",
    )
    admin_callback_executor = ThreadPoolExecutor(
        max_workers=8,
        thread_name_prefix="telegram-admin-button",
    )

    offset = None
    while True:
        try:
            update_method = "getUpdates?timeout=50"
            if offset is not None:
                update_method += f"&offset={offset}"
            updates = api_call(update_method)
            if updates.get("ok") and "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        message = update["message"]
                        sender_id = message.get("from", {}).get(
                            "id", message.get("chat", {}).get("id")
                        )
                        target_executor = (
                            admin_message_executor
                            if sender_id is not None and is_admin(sender_id)
                            else message_executor
                        )
                        target_executor.submit(handle_message, message)
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        if not _callback_ack_requires_handler(
                            callback.get("data", "")
                        ):
                            try:
                                _callback_ack_executor.submit(
                                    answer_callback, callback["id"]
                                )
                            except Exception:
                                pass
                            else:
                                callback["_early_ack_scheduled"] = True
                        callback_actor_id = callback.get("from", {}).get("id")
                        target_executor = (
                            admin_callback_executor
                            if callback_actor_id is not None
                            and is_admin(callback_actor_id)
                            else callback_executor
                        )
                        target_executor.submit(handle_callback, callback)
            elif updates.get("ok") is False:
                print(f"⚠️ Telegram polling error: {updates.get('description', 'unknown error')}")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Telegram polling exception: {e}")
            time.sleep(2)




if __name__ == "__main__":
    main()
