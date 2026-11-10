#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐝 Asalarichilik.Uz — Telegram Гуруҳ Назорат, Қулфлар & Хавфсизлик Боти
Муаллиф ва Бот эгаси: @JamshidjonDavronov (ID: 2047501151)
Бот: @Asalarichilikuztv_bot

1. 🏠 АСОСИЙ МЕНЮ: Барча аввалги созламалар ва жонли онлайн ҳолат.
2. 🔒 ҚУЛФЛАР (ЧЕКЛОВЛАР БЎЛИМИ):
   - Расмлар (3 талик лимит, 24с мут)
   - Видеолар (3 талик лимит, 24с мут)
   - Реклама ва ҳаволалар қулфи (ON/OFF)
   - Овозли хабарлар қулфи (ON/OFF)
   - Стикер ва GIF қулфи (ON/OFF)
   - Форвард хабарлар қулфи (ON/OFF)
   - Арабча/Форсча матнлар қулфи (ON/OFF)
   - Кирди-чиқди тозалаш (ON/OFF)
3. 🌙 ТУНГИ РЕЖИМ (2-расмдагидек 100% аниқ кўриниш ва тугмалар):
   - Ҳолати: 🟢 Ёқилган / 🔴 Ўчирилган (дарҳол ўзгаради)
   - Бошланиш ва Тугаш вақтлари (соат ва дақиқа танлаш)
   - 2-расмдаги огоҳлантириш матни
   - Синов эълонини гуруҳга юбориш
4. 🌐 RENDER.COM HTTP HEALTH CHECK: 100% муаммосиз ишлаш учун.
"""

import os
import sys
import time
import re
import logging
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = "8643717970:AAE27V6dfb-w2q_mpiqgqVsmucGPdlqY2eU"
OWNER_ID = 2047501151  # @JamshidjonDavronov
MAIN_CHANNEL = "@Uz_Asalarichilik"
MAIN_GROUP = "@Asalarichilik_Uzbekistan"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Тошкент вақти (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))

# ==================== RENDER HTTP HEALTH SERVER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - Asalarichilik Moderation Bot is active and running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_http_health():
    port_env = os.environ.get("PORT")
    port = int(port_env) if port_env and port_env.isdigit() else 10000
    if port == 8080:  # Sandbox container nginx uses 8080
        port = 10000
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logging.info(f"🌐 HTTP Health сервер {port}-портда ишга тушди.")
        server.serve_forever()
    except Exception as e:
        logging.warning(f"HTTP server notice: {e}")

threading.Thread(target=start_http_health, daemon=True).start()

# ==================== ДАТАБАЗА ВА КЭШ ====================
DB_PATH = "bot_moderation.db"
_settings_cache = {
    "night_mode": "1",
    "night_start": "00:00",
    "night_end": "06:30",
    "night_warn_text": "",
    "lock_photos": "1",
    "lock_videos": "1",
    "lock_links": "1",
    "lock_voice": "0",
    "lock_stickers": "0",
    "lock_forwards": "0",
    "lock_arabic": "1",
    "lock_service": "1",
    "auto_react": "1",
    "share_btn": "1",
    "expert_btn": "1",
    "weather_auto": "1",
    "weather_time": "07:30",
    "weather_target": "both",
    "weather_region": "all",
    "weather_period": "1day"
}

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS muted_users (
                user_id INTEGER,
                chat_id INTEGER,
                muted_until INTEGER,
                reason TEXT,
                user_name TEXT DEFAULT '',
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        try:
            cur.execute("ALTER TABLE muted_users ADD COLUMN user_name TEXT DEFAULT ''")
        except Exception:
            pass
        cur.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER,
                chat_id INTEGER,
                warn_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_stats (
                chat_id INTEGER PRIMARY KEY,
                deleted_media INTEGER DEFAULT 0,
                muted_count INTEGER DEFAULT 0,
                deleted_links INTEGER DEFAULT 0,
                deleted_night INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        for k, v in _settings_cache.items():
            cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

        # Кэшга ўқиб оламиз
        cur.execute("SELECT key, value FROM settings")
        for row in cur.fetchall():
            if row[0] and row[1] is not None:
                _settings_cache[row[0]] = str(row[1])

        conn.close()
    except Exception as e:
        logging.error(f"DB init error: {e}")

init_db()

def get_setting(key, default=""):
    return _settings_cache.get(key, default)

def set_setting(key, value):
    _settings_cache[key] = str(value)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB save error: {e}")

# ==================== ВАҚТ ҲИСОБЛАШ ====================
def parse_time_to_minutes(time_str):
    try:
        parts = time_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except Exception:
        return 0

def is_night_mode_now():
    if get_setting("night_mode", "1") != "1":
        return False

    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")

    start_min = parse_time_to_minutes(start_str)
    end_min = parse_time_to_minutes(end_str)

    now_dt = datetime.now(TASHKENT_TZ)
    now_min = now_dt.hour * 60 + now_dt.minute

    if start_min > end_min:  # 23:00 - 06:30
        return now_min >= start_min or now_min < end_min
    elif start_min < end_min:  # 00:00 - 06:30
        return start_min <= now_min < end_min
    else:
        return True

def get_remaining_night_time_str():
    end_str = get_setting("night_end", "06:30")
    end_min = parse_time_to_minutes(end_str)

    now_dt = datetime.now(TASHKENT_TZ)
    now_min = now_dt.hour * 60 + now_dt.minute

    if now_min < end_min:
        diff = end_min - now_min
    else:
        diff = (24 * 60 - now_min) + end_min

    rem_h = diff // 60
    rem_m = diff % 60
    return f"{rem_h:02d} соат {rem_m:02d} дақиқа"

def get_night_warn_text():
    custom = get_setting("night_warn_text", "").strip()
    if custom:
        return custom

    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")
    rem_time = get_remaining_night_time_str()

    return f"""❝ 🌙 Ҳурматли Фойдаланувчи!

Ҳозирда ушбу гуруҳ автоматик қулфланган (соат {start_str} дан {end_str} гача).

Сиз соат {end_str} дан кейин гуруҳга ёзишингиз ёки бирор маълумот жўнатишингиз мумкин. Ҳозирда ушбу гуруҳ автоматик қулфланганлиги сабабли юборилган хабарингиз ўчирилди.

⏳ Пожалуйста, подождите {rem_time} , пока блокировка группы не будет снята.

⏳ Ушбу огоҳлантириш 30 сониядан сўнг автоматик ўчириб ташланади. ❞"""

# ==================== АДМИН ВА ҲИМОЯ ====================
_user_media_history = defaultdict(list)
_album_messages = defaultdict(list)
_user_msg_times = defaultdict(list)
_admin_cache = {}
_night_warn_cache = {}

def is_admin(chat_id, user_id):
    if user_id in [OWNER_ID, 777000, 1087968824, 136817688]:
        return True
    now = time.time()
    cache_key = (chat_id, user_id)
    if cache_key in _admin_cache:
        val, ts = _admin_cache[cache_key]
        if now - ts < 120:
            return val
    try:
        member = bot.get_chat_member(chat_id, user_id)
        is_adm = member.status in ["administrator", "creator"]
        _admin_cache[cache_key] = (is_adm, now)
        return is_adm
    except Exception:
        return False

OFFICIAL_CHATS = {
    MAIN_CHANNEL,  # -1001261575171
    MAIN_GROUP,    # -1001548174542
    OWNER_ID       # 2047501151
}

OFFICIAL_USERNAMES = {
    "uz_asalarichilik",
    "asalarichilik_uzbekistan",
    "asalarichilikuztv_bot",
    "asalarichilikuz_bot",
    "jamshidjondavronov"
}

OFFICIAL_ALLOWED_LINKS = [
    "t.me/uz_asalarichilik",
    "t.me/asalarichilik_uzbekistan",
    "t.me/asalarichilikuztv_bot",
    "t.me/asalarichilikuz_bot",
    "t.me/jamshidjondavronov",
    "youtube.com/@asalarichilikuz",
    "youtube.com/@asalarichilik",
    "youtube.com/channel/",
    "youtu.be/"
]

def is_official_message(message):
    """
    Каналдан уланган гуруҳга келган барча хабарларни ва расмий канал/гуруҳ/бот постларини аниқлаш.
    Ушбу хабарларга ҳеч қачон чеклов, ўчириш ёки огоҳлантириш қўлланмайди.
    """
    if not message:
        return False

    # 1. Telegram Service / Automatic linked channel forward
    if getattr(message, 'is_automatic_forward', False):
        return True

    from_u = getattr(message, 'from_user', None)
    if from_u:
        # 777000: Telegram Channel proxy, 1087968824: GroupAnonymousBot, 136817688: Channel Bot
        if from_u.id in [777000, 1087968824, 136817688, OWNER_ID]:
            return True
        if from_u.username and from_u.username.lower() in OFFICIAL_USERNAMES:
            return True

    # 2. Sender chat (канал номидан пост келганда)
    sender_c = getattr(message, 'sender_chat', None)
    if sender_c:
        if sender_c.id in [MAIN_CHANNEL, MAIN_GROUP, message.chat.id]:
            return True
        if sender_c.username and sender_c.username.lower() in OFFICIAL_USERNAMES:
            return True

    # 3. Расмий канал ёки гуруҳдан форвард қилинган пост
    fwd_chat = getattr(message, 'forward_from_chat', None)
    if fwd_chat:
        if fwd_chat.id in [MAIN_CHANNEL, MAIN_GROUP]:
            return True
        if fwd_chat.username and fwd_chat.username.lower() in OFFICIAL_USERNAMES:
            return True

    return False

def has_foreign_links(message):
    """
    Хабарда бегона реклама, ҳавола ёки бошқа канал/гуруҳ борлигини кучайтирилган тарзда текширади.
    Гуруҳ ва каналнинг ўз ҳаволаларига тегмайди.
    """
    if is_official_message(message):
        return False

    text = (getattr(message, 'text', '') or '') + " " + (getattr(message, 'caption', '') or '')
    all_entities = (getattr(message, 'entities', None) or []) + (getattr(message, 'caption_entities', None) or [])

    urls_found = []

    # Регуляр ифода: ҳаволалар ва t.me силкалари
    raw_lower = text.lower()
    url_matches = re.findall(r'(https?://[^\s]+|t\.me/[^\s]+|telegram\.me/[^\s]+|www\.[^\s]+)', raw_lower)
    urls_found.extend(url_matches)

    # Канал/гуруҳ юзернеймлари: @kanal_nomi
    mention_matches = re.findall(r'@([a-zA-Z0-9_]{4,})', raw_lower)
    for m in mention_matches:
        urls_found.append(f"@{m.lower()}")

    # Telegram Entities (яширин форматланган ҳаволалар)
    for ent in all_entities:
        if ent.type == 'text_link' and getattr(ent, 'url', None):
            urls_found.append(ent.url.lower())
        elif ent.type == 'url':
            full_txt = message.text or message.caption or ""
            extracted = full_txt[ent.offset:ent.offset+ent.length].lower()
            urls_found.append(extracted)
        elif ent.type == 'mention':
            full_txt = message.text or message.caption or ""
            extracted = full_txt[ent.offset:ent.offset+ent.length].lower()
            urls_found.append(extracted)

    if not urls_found:
        return False

    # Ҳар бир ҳаволани расмий ҳаволалар оқ рўйхати билан текширамиз
    for item in urls_found:
        clean = item.strip().lower()

        is_own = False
        for allowed in OFFICIAL_ALLOWED_LINKS:
            if allowed in clean:
                is_own = True
                break

        if clean.startswith("@"):
            uname = clean[1:].strip()
            if uname in OFFICIAL_USERNAMES:
                is_own = True

        # Агар ўзимизнинг канал ёки гуруҳ бўлмаса — демак БЕГОНА реклама/канал!
        if not is_own:
            return True

    return False

def get_mention(user):
    name = user.first_name or "Фойдаланувчи"
    name = name.replace("<", "").replace(">", "")
    if user.username:
        return f'<a href="tg://user?id={user.id}">{name}</a> (@{user.username})'
    return f'<a href="tg://user?id={user.id}">{name}</a>'

def safe_delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def delete_later(chat_id, message_id, delay=30):
    def _worker():
        time.sleep(delay)
        safe_delete_message(chat_id, message_id)
    threading.Thread(target=_worker, daemon=True).start()

def mute_user_24h(chat_id, user_id, user_mention, user_name="", reason="3 тадан ортиқ расм/видео юборилди"):
    until_date = int(time.time()) + 86400  # 24 соат
    if not user_name:
        user_name = f"ID: {user_id}"

    try:
        bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=until_date,
            use_independent_chat_permissions=True
        )
    except Exception:
        try:
            bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                ),
                until_date=until_date
            )
        except Exception as e:
            logging.error(f"Mute error: {e}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO muted_users (user_id, chat_id, muted_until, reason, user_name)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, chat_id, until_date, reason, user_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Save mute db error: {e}")

    notice_text = f"""
⚠️ <b>ҚАТЪИЙ ОГОҲЛАНТИРИШ ВА ЖАЗО!</b>
━━━━━━━━━━━━━━━━━━━━
👤 Фойдаланувчи: {user_mention}
🚫 Сабаб: <b>{reason}!</b>
🔇 Жазо тури: <b>24 соатлик МУТ (1 кун ёзиш чеклови)</b>
⏳ Муддати: 1 сутка (24 соат)
━━━━━━━━━━━━━━━━━━━━
<i>Гуруҳ қоидаси: Реклама ёки кетма-кет 3 тадан ортиқ расм/видео ташлаш қатъиян ман этилади! Барча ташланган расмлар ўчирилди.</i>
""".strip()

    try:
        sent = bot.send_message(chat_id, notice_text)
        delete_later(chat_id, sent.message_id, delay=45)
    except Exception:
        pass

def unmute_user_fully(chat_id, user_id):
    targets = [chat_id, MAIN_GROUP, -1001548174542]
    for target in targets:
        try:
            bot.restrict_chat_member(
                chat_id=target,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                ),
                use_independent_chat_permissions=True
            )
        except Exception:
            try:
                bot.restrict_chat_member(
                    chat_id=target,
                    user_id=user_id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
            except Exception:
                pass

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM muted_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Delete mute db error: {e}")

def get_active_muted_users():
    now_ts = int(time.time())
    users = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, chat_id, muted_until, reason, user_name
            FROM muted_users
            WHERE muted_until > ?
            ORDER BY muted_until DESC
        """, (now_ts,))
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            users.append({
                "user_id": r[0],
                "chat_id": r[1],
                "muted_until": r[2],
                "reason": r[3] or "Қоидабузарлик",
                "user_name": r[4] or f"ID: {r[0]}"
            })
    except Exception as e:
        logging.error(f"get_active_muted_users error: {e}")
    return users

def build_muted_list_text():
    muted = get_active_muted_users()
    count = len(muted)
    now_ts = int(time.time())

    if count == 0:
        return """🔇 <b>МУТДАГИ АЪЗОЛАР РЎЙХАТИ</b>
━━━━━━━━━━━━━━━━━━━━
🎉 <b>Ҳозирда гуруҳда мутга тушган аъзолар йўқ!</b>
Барча аъзолар эркин хабар ёзишлари мумкин.
━━━━━━━━━━━━━━━━━━━━"""

    lines = [
        f"🔇 <b>МУТДАГИ АЪЗОЛАР РЎЙХАТИ ({count} та аъзо)</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "<i>Қуйидаги аъзолар гуруҳ қоидасини бузгани учун мутга тушган:</i>\n"
    ]

    for idx, u in enumerate(muted[:15], 1):
        rem_sec = max(0, u["muted_until"] - now_ts)
        rem_h = rem_sec // 3600
        rem_m = (rem_sec % 3600) // 60
        time_left = f"{rem_h} соат {rem_m} дақиқа" if rem_h > 0 else f"{rem_m} дақиқа"
        name = u["user_name"]
        lines.append(f"<b>{idx}. {name}</b> (ID: <code>{u['user_id']}</code>)")
        lines.append(f"   🚫 Сабаб: <i>{u['reason']}</i>")
        lines.append(f"   ⏳ Қолган вақт: <b>{time_left}</b>\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("<i>Фойдаланувчини мутдан чиқариш учун пастдаги тугмани босинг:</i>")
    return "\n".join(lines)

def build_muted_list_markup():
    muted = get_active_muted_users()
    markup = InlineKeyboardMarkup()

    for u in muted[:8]:
        u_name = u["user_name"]
        if len(u_name) > 18:
            u_name = u_name[:17] + ".."
        btn_label = f"🔓 Озод қилиш: {u_name}"
        markup.row(InlineKeyboardButton(btn_label, callback_data=f"unmute_uid_{u['user_id']}"))

    if len(muted) > 0:
        markup.row(InlineKeyboardButton(f"🔓 Барчасини мутдан озод қилиш ({len(muted)} та)", callback_data="unmute_all_users"))

    markup.row(
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu"),
        InlineKeyboardButton("🔄 Янгилаш", callback_data="open_muted_list")
    )
    return markup

def check_night_mode_violation(message):
    if message.chat.type == 'private':
        return False
    if is_official_message(message):
        return False
    user_id = message.from_user.id if message.from_user else 0
    if is_admin(message.chat.id, user_id):
        return False

    if is_night_mode_now():
        safe_delete_message(message.chat.id, message.message_id)

        now = time.time()
        user_key = (message.chat.id, message.from_user.id)
        last_warn = _night_warn_cache.get(user_key, 0)

        if now - last_warn > 120:
            _night_warn_cache[user_key] = now
            warn_msg = get_night_warn_text()
            try:
                sent = bot.send_message(message.chat.id, warn_msg)
                delete_later(message.chat.id, sent.message_id, delay=30)
            except Exception:
                pass
        return True
    return False

# ==================== 1. АСОСИЙ МЕНЮ (MAIN MENU) ====================
def build_main_menu_text():
    now_dt = datetime.now(TASHKENT_TZ)
    current_time_str = now_dt.strftime("%H:%M")
    is_on = get_setting("night_mode", "1") == "1"
    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")
    is_active_now = is_night_mode_now()

    night_status_icon = "🟢 ЁҚИЛГАН" if is_on else "🔴 ЎЧИРИЛГАН"
    active_now_text = "🌙 Ҳозир ТУНГИ РЕЖИМДА (Ёзиш чекланган)" if is_active_now else "☀️ Ҳозир КУНДУЗГИ РЕЖИМДА (Ёзиш мумкин)"

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM muted_users WHERE muted_until > ?", (int(time.time()),))
        active_mutes = cur.fetchone()[0]
        conn.close()
    except Exception:
        active_mutes = 0

    l_photos_state = "🟢 Фаол" if get_setting("lock_photos", "1") == "1" else "🔴 Ўчирилган"
    l_videos_state = "🟢 Фаол" if get_setting("lock_videos", "1") == "1" else "🔴 Ўчирилган"
    l_weather_state = "🟢 Фаол" if get_setting("weather_auto", "1") == "1" else "🔴 Ўчирилган"
    w_time_str = get_setting("weather_time", "07:30")

    return f"""🐝 <b>ASALARICHILIK.UZ — БОШҚАРУВ МАРКАЗИ</b>
━━━━━━━━━━━━━━━━━━━━
🟢 <b>Бот ҳолати:</b> ОНЛАЙН (Серверда узлуксиз ишламоқда)
🕒 <b>Тошкент вақти:</b> {current_time_str} (UTC+5)
⚡️ <b>Жорий режим:</b> <b>{active_now_text}</b>

🛡 <b>ГУРУҲ ҲИМОЯ ВА ХИЗМАТ ҲОЛАТИ:</b>
• 🌙 <b>Тунги режим:</b> <b>{night_status_icon}</b> ({start_str} дан {end_str} гача)
• ⛅️ <b>Об-ҳаво эълонлари:</b> <b>{l_weather_state}</b> (ҳар куни соат {w_time_str} да)
• 📸 <b>Расмлар лимити (3 талик):</b> {l_photos_state}
• 📹 <b>Видеолар лимити (3 талик):</b> {l_videos_state}
• 🔒 <b>Қулфлар (Чекловлар):</b> 🟢 <b>Фаол</b> (Ҳавола, Овоз, Стикер, Форвард)
• 🔇 <b>Ҳозир мутда:</b> <b>{active_mutes} та аъзо</b>
• 👥 <b>Гуруҳ:</b> {MAIN_GROUP}
━━━━━━━━━━━━━━━━━━━━
<i>Керакли бўлимни танланг:</i>"""

def build_main_menu_markup():
    markup = InlineKeyboardMarkup()
    is_on = get_setting("night_mode", "1") == "1"
    btn_night_text = f"🌙 Тунги Режим ({'🟢 Ёқилган' if is_on else '🔴 Ўчирилган'})"

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM muted_users WHERE muted_until > ?", (int(time.time()),))
        active_mutes = cur.fetchone()[0]
        conn.close()
    except Exception:
        active_mutes = 0

    markup.row(InlineKeyboardButton("⚙️ Гуруҳ Созламалари", callback_data="open_group_settings"))
    markup.row(
        InlineKeyboardButton("🔒 Қулфлар (Чекловлар)", callback_data="open_locks_menu"),
        InlineKeyboardButton(btn_night_text, callback_data="open_night_menu")
    )
    markup.row(
        InlineKeyboardButton("⛅️ Об-ҳаво маълумотлари", callback_data="open_weather_menu"),
        InlineKeyboardButton(f"🔇 Мутдагилар ({active_mutes} та)", callback_data="open_muted_list")
    )
    markup.row(
        InlineKeyboardButton("📢 Жўнатма юбориш", callback_data="open_broadcast_menu"),
        InlineKeyboardButton("📊 Статистика", callback_data="open_stats")
    )
    markup.row(
        InlineKeyboardButton("📢 Расмий Канал", url="https://t.me/Uz_Asalarichilik"),
        InlineKeyboardButton("👥 Расмий Гуруҳ", url="https://t.me/ASALARICHILIK_UZBEKISTAN")
    )
    markup.row(InlineKeyboardButton("🔄 Маълумотларни янгилаш", callback_data="refresh_main_menu"))
    return markup

# ==================== 2. ГУРУҲ СОЗЛАМАЛАРИ (GROUP SETTINGS) ====================
def build_group_settings_text():
    return f"""⚙️ <b>ГУРУҲ СОЗЛАМАЛАРИ (@Asalarichilik_Uzbekistan)</b>
━━━━━━━━━━━━━━━━━━━━
Бот гуруҳ хавфсизлигини ва хизматларни 100% таъминлайди.

Қуйидаги бўлимлардан кераклисини танланг:
• 🔒 <b>Қулфлар (Чекловлар):</b> Расм, видео, ҳавола, овоз ва стикерлар чеклови.
• 🌙 <b>Тунги режим:</b> Соат 00:00 дан 06:30 гача гуруҳни автоматик қулфлаш.
• ⛅️ <b>Об-ҳаво:</b> Кунлик автоматик об-ҳаво ва агро-тавсияларни юбориш созламалари.
• 📸 <b>3 талик медиа лимит:</b> Спам тарзида расм/видео ташлаганларга 24 соатлик мут.
• 🔇 <b>Мутдагилар:</b> Мутга тушган аъзоларни кўриш ва уларни мутдан озод қилиш.
• 🧹 <b>Сервис хабарлар:</b> Аъзолар кирди-чиқдисини автоматик тозалаш.
━━━━━━━━━━━━━━━━━━━━"""

def build_group_settings_markup():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM muted_users WHERE muted_until > ?", (int(time.time()),))
        active_mutes = cur.fetchone()[0]
        conn.close()
    except Exception:
        active_mutes = 0

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔒 Қулфлар ва Чекловлар бўлими", callback_data="open_locks_menu"))
    markup.row(
        InlineKeyboardButton("🌙 Тунги Режим", callback_data="open_night_menu"),
        InlineKeyboardButton("⛅️ Об-ҳаво созламалари", callback_data="open_weather_menu")
    )
    markup.row(InlineKeyboardButton(f"🔇 Мутдагилар рўйхати ({active_mutes} та)", callback_data="open_muted_list"))
    markup.row(
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu"),
        InlineKeyboardButton("🔄 Янгилаш", callback_data="open_group_settings")
    )
    return markup

# ==================== 3. ҚУЛФЛАР (LOCKS) БЎЛИМИ ====================
def build_locks_menu_text():
    return """🔒 <b>ГУРУҲ ҚУЛФЛАРИ ВА ЧЕКЛОВЛАРИ</b>
━━━━━━━━━━━━━━━━━━━━
Керакли қулф устига босиб уни ёқишингиз (🟢) ёки ўчиришингиз (🔴) мумкин.

🟢 = Қулфланган / Чеклов фаол (3 тадан ошса ёки ташланса жазоланади)
🔴 = Рухсат берилган / Чеклов ўчирилган
━━━━━━━━━━━━━━━━━━━━"""

def build_locks_menu_markup():
    markup = InlineKeyboardMarkup()

    l_photos = "🟢" if get_setting("lock_photos", "1") == "1" else "🔴"
    l_videos = "🟢" if get_setting("lock_videos", "1") == "1" else "🔴"
    l_links = "🟢" if get_setting("lock_links", "1") == "1" else "🔴"
    l_voice = "🟢" if get_setting("lock_voice", "0") == "1" else "🔴"
    l_stickers = "🟢" if get_setting("lock_stickers", "0") == "1" else "🔴"
    l_forwards = "🟢" if get_setting("lock_forwards", "0") == "1" else "🔴"
    l_arabic = "🟢" if get_setting("lock_arabic", "1") == "1" else "🔴"
    l_service = "🟢" if get_setting("lock_service", "1") == "1" else "🔴"
    l_night = "🟢" if get_setting("night_mode", "1") == "1" else "🔴"

    markup.row(
        InlineKeyboardButton(f"📸 Расмлар лимити (3 та): {l_photos}", callback_data="toggle_lock_photos"),
        InlineKeyboardButton(f"📹 Видеолар лимити (3 та): {l_videos}", callback_data="toggle_lock_videos")
    )
    markup.row(
        InlineKeyboardButton(f"🔗 Реклама/Ҳавола: {l_links}", callback_data="toggle_lock_links"),
        InlineKeyboardButton(f"🎙 Овозли хабар: {l_voice}", callback_data="toggle_lock_voice")
    )
    markup.row(
        InlineKeyboardButton(f"🎭 Стикер & GIF: {l_stickers}", callback_data="toggle_lock_stickers"),
        InlineKeyboardButton(f"⏩ Форвардлар: {l_forwards}", callback_data="toggle_lock_forwards")
    )
    markup.row(
        InlineKeyboardButton(f"🌐 Арабча ёзув: {l_arabic}", callback_data="toggle_lock_arabic"),
        InlineKeyboardButton(f"🧹 Кирди-чиқди: {l_service}", callback_data="toggle_lock_service")
    )
    markup.row(InlineKeyboardButton(f"🌙 Тунги Режим: {l_night}", callback_data="open_night_menu"))
    markup.row(
        InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data="open_group_settings"),
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu")
    )
    return markup

# ==================== 4. 2-РАСМДАГИ ТУНГИ РЕЖИМ МЕНЮСИ ====================
def build_night_menu_text():
    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")
    is_on = get_setting("night_mode", "1") == "1"
    now_dt = datetime.now(TASHKENT_TZ)
    current_time_str = now_dt.strftime("%H:%M")

    warn_text = get_night_warn_text()
    status_str = "🟢 Ёқилган" if is_on else "🔴 Ўчирилган"

    return f"""🌙 <b>ТУНГИ РЕЖИМ БОШҚАРУВИ</b>
━━━━━━━━━━━━━━━━━━━━
• Ҳозирги Тошкент вақти: <b>{current_time_str}</b>
• Ҳолати: <b>{status_str}</b>
• Қулфлаш вақти: <b>соат {start_str} дан {end_str} гача</b>

Тунги вақтда юборилган барча хабарлар бот томонидан автоматик ўчирилади (30 сониядан сўнг тозаланади).

💬 <b>Ҳозирги огоҳлантириш матни:</b>
{warn_text}"""

def build_night_menu_markup():
    is_on = get_setting("night_mode", "1") == "1"
    status_label = "Ҳолати / Status: 🟢 Ёқилган" if is_on else "Ҳолати / Status: 🔴 Ўчирилган"
    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")

    markup = InlineKeyboardMarkup()
    # 1-қатор: Ҳолати
    markup.row(InlineKeyboardButton(status_label, callback_data="toggle_night_status"))
    # 2-қатор: Бошланиш ва Тугаш
    markup.row(
        InlineKeyboardButton(f"🔓 Бошланиш: {start_str}", callback_data="pick_night_start"),
        InlineKeyboardButton(f"🔓 Тугаш: {end_str}", callback_data="pick_night_end")
    )
    # 3-қатор: Огоҳлантириш матни
    markup.row(InlineKeyboardButton("✏️ Огоҳлантириш матнини ўзгартириш", callback_data="edit_night_warn_prompt"))
    # 4-қатор: Синов эълони
    markup.row(InlineKeyboardButton("🚀 Ҳозироқ синов эълонини юбориш", callback_data="send_night_test_now"))
    # 5-қатор: Ортга
    markup.row(
        InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data="open_group_settings"),
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu")
    )
    return markup

# ==================== 5. ОБ-ҲАВО МАЪЛУМОТЛАРИ ВА СОЗЛАМАЛАРИ ====================

WEATHER_REGIONS_ORDER = ["tashkent", "fergana", "samarkand", "bukhara", "kashkadarya", "khorezm"]

WEATHER_REGIONS_CONFIG = {
    "tashkent": {
        "header": "📍 Тошкент шаҳри ва вилояти:",
        "name": "Тошкент шаҳри ва вилояти",
        "lat": 41.31,
        "lon": 69.24
    },
    "fergana": {
        "header": "📍 Фарғона водийси (Андижон, Наманган, Фарғона):",
        "name": "Фарғона водийси",
        "lat": 40.38,
        "lon": 71.78
    },
    "samarkand": {
        "header": "📍 Самарқанд ва Жиззах вилоятлари:",
        "name": "Самарқанд ва Жиззах",
        "lat": 39.65,
        "lon": 66.97
    },
    "bukhara": {
        "header": "📍 Бухоро ва Навоий вилоятлари:",
        "name": "Бухоро ва Навоий",
        "lat": 39.77,
        "lon": 64.42
    },
    "kashkadarya": {
        "header": "📍 Қашқадарё ва Сурхондарё вилоятлари:",
        "name": "Қашқадарё ва Сурхондарё",
        "lat": 38.86,
        "lon": 65.79
    },
    "khorezm": {
        "header": "📍 Хоразм вилояти ва Қорақалпоғистон:",
        "name": "Хоразм ва Қорақалпоғистон",
        "lat": 41.55,
        "lon": 60.63
    }
}

UZ_MONTHS = {
    1: "январ", 2: "феврал", 3: "март", 4: "апрел", 5: "май", 6: "июн",
    7: "июл", 8: "август", 9: "сентябр", 10: "октябр", 11: "ноябр", 12: "декабр"
}

UZ_WEEKDAYS = {
    0: "Душанба", 1: "Сешанба", 2: "Чоршанба", 3: "Пайшанба", 4: "Жума", 5: "Шанба", 6: "Якшанба"
}

YOUNG_BEEKEEPER_TIPS = [
    {
        "title": "👔 <b>Асаларичининг кийими ва гигиенаси:</b>",
        "body": "Арилар қора ранг, жунли матолар ва кескин ҳидларни (тер, спирт, парфюм, саримсоқ) ёқтирмайди ва чақишга интилади. Арихонага фақат тоза, оқ ёки оч рангдаги пахта матоли кийим ва тўрли қалпоқ кийиб киринг!"
    },
    {
        "title": "💨 <b>Тутатгич (дымарь)дан фойдаланиш санъати:</b>",
        "body": "Тутатгичга чирик тол ёки дарахт пўстлоғи, қуруқ тезак солинг. Ариларга қайноқ оловли тутун эмас, салқин ва оппоқ тутун берилади. Уяни очганда 1-2 марта енгил тутун пуркаб, 1 дақиқа кутинг — арилар ошқозонига асал тўлдириб, мулойим бўлиб қолади."
    },
    {
        "title": "💧 <b>Арихонада тоза сувдоннинг (поилка) аҳамияти:</b>",
        "body": "Асаларилар қуюқ асални эритиш ва наслни парваришлаш учун доимо сувга муҳтож. Арихонанинг қуёш тушадиган илиқ бурчагига тоза, бироз туз қўшилган (10 литр сувга 1 чой қошиқ ош тузи) илиқ сувдон қўйишни ҳеч қачон унутманг!"
    },
    {
        "title": "🍯 <b>Қишлов олдидан озиқа захирасини назорат қилиш:</b>",
        "body": "Ҳар бир соғлом оила қишловга киришда камида 16-20 кг сифатли асал захирасига эга бўлиши шарт. Захира кам бўлса ёки ҳарорат пасайганда арилар очликдан ҳалок бўлмаслиги учун рамкалар устига канди хамири ёки қуюқ сироп берилади."
    },
    {
        "title": "❄️ <b>Қишда ари уясини безовта қилмаслик қоидаси:</b>",
        "body": "Қиш фаслида уяни тақиллатиш, силкитиш ёки ортиқча очиш мутлақо тақиқланади! Шовқиндан қўрққан арилар қишки клубдан (тўдадан) уя тубига тўкилиб совуқда нобуд бўлади. Арилар ҳолатини резина найча орқали қулоқ солиб текшириш кифоя."
    },
    {
        "title": "🌬 <b>Уяларда шамоллатиш (вентиляция) қоидалари:</b>",
        "body": "Қишда ариларни совуқ эмас, балки уя ичидаги намлик ва димлик нобуд қилади. Уя тубида ва шифтида ҳаво алмашиш йўли бўлиши, ёстиқчалар қуруқ пахтадан бўлиши керак. Намлик тўпланса рамкалар моғорлайди ва арилар нозематозга чалинади."
    },
    {
        "title": "🐝 <b>Она арини (матка) эҳтиётлаш ва текшириш:</b>",
        "body": "Рамкани кўздан кечирганда доимо уянинг устида тутинг. Агар тасодифан она ари рамкадан сирғалиб кетса ҳам, тўғри уя ичига тушади. Рамкада янги қўйилган 1-2 кунлик тухумлар бўлса, она ари оила ичида соғ-омон эканлигини билдиради."
    },
    {
        "title": "🐜 <b>Варроа канасига қарши ўз вақтида ишлов бериш:</b>",
        "body": "Асал олингач ва куз бошида оилаларни Варроа канасига қарши дорилаш шарт. Бунинг учун тимол, шовул кислотаси ёки махсус тасдиқланган пластинкалар қўлланилади. Канаси кўп оила қишдан соғлом чиқа олмайди."
    },
    {
        "title": "🪵 <b>Мумпарда (вощина) ва янги рамкалар қўйиш:</b>",
        "body": "Ҳар йили уядаги эскирган қора рамкаларнинг 30-40 фоизини янгиларига алмаштиринг. Эски уя кўзлари кичрайиб кетгани сабабли ундан чиққан янги арилар ҳам майда ва нимжон бўлиб қолади. Янги рамка — соғлом авлод демакдир!"
    },
    {
        "title": "🌸 <b>Баҳорги биринчи тозаланиш парвози (облёт):</b>",
        "body": "Баҳор бошланиб ҳаво ҳарорати +12...+14°C га етганда арилар қиш бўйи ичакларида йиғилган чиқиндиларни ташқарига чиқариш учун ёппасига парвоз қилади. Шу куни арихона атрофи тозаланиши ва парвоз йўли очиқ бўлиши шарт."
    },
    {
        "title": "🧤 <b>Чақиш хавфини камайтириш ва тўғри ҳаракатланиш:</b>",
        "body": "Асаларилар олдида қўлни тез силтаманг ва арини уриб ўлдиришга уринманг. Ари ҳалок бўлаётганда хавф феромонини ажратади ва бошқа ариларни ҳам ҳужумга чорлайди. Агар сизни ари чақса, нишни сиқмасдан, пичоқ ёки тирноқ билан суриб чиқаринг!"
    },
    {
        "title": "🌱 <b>Асалли ўсимликлар (медоносы) экиш:</b>",
        "body": "Арихона атрофига фацелия, оқ беда, эспарцет, липа, ялпиз каби асал берувчи ўсимликларни экиш асал ҳосилини 20-30% га оширади ва ариларнинг узоққа учиб чарчашининг олдини олади."
    }
]

WMO_CODE_TEXTS = {
    0: ("☀️ Очиқ қуёшли", "🟢 Парвоз учун қулай"),
    1: ("🌤 Асосан очиқ", "🟢 Парвоз учун қулай"),
    2: ("⛅️ Қисман булутли", "🟢 Парвоз учун яхши"),
    3: ("☁️ Булутли", "🟡 Парвоз ўртача"),
    45: ("🌫 Туман", "🔴 Парвоз чекланган"),
    48: ("🌫 Қировли туман", "🔴 Парвоз ноқулай"),
    51: ("🌦 Бироз майда ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    53: ("🌧 Майда ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    55: ("🌧 Кучли майда ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    61: ("🌧 Бироз ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    63: ("🌧 Ёмғирли ҳаво", "🔴 Уяда қолиш тавсия этилади"),
    65: ("🌧 Кучли ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    71: ("🌨 Қор ёғиши", "🔴 Совуқ, уяда сақланг"),
    73: ("🌨 Ўртача қор", "🔴 Совуқ, уяда сақланг"),
    75: ("❄️ Кучли қор", "🔴 Совуқ, уяда сақланг"),
    80: ("🌦 Қисқа ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    81: ("🌧 Жала ёмғир", "🔴 Уяда қолиш тавсия этилади"),
    95: ("⛈ Момақалдироқ", "🔴 Хавфли, уяда сақланг")
}

_weather_cache = {}
_weather_cache_time = 0

def fetch_weather_for_region(reg_key):
    global _weather_cache, _weather_cache_time
    now = time.time()
    if reg_key in _weather_cache and (now - _weather_cache_time < 1800):
        return _weather_cache[reg_key]

    cfg = WEATHER_REGIONS_CONFIG.get(reg_key, WEATHER_REGIONS_CONFIG["tashkent"])
    url = f"https://api.open-meteo.com/v1/forecast?latitude={cfg['lat']}&longitude={cfg['lon']}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code,wind_speed_10m_max,precipitation_sum&forecast_days=10&timezone=Asia%2FTashkent"
    try:
        import urllib.request
        import json
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            cur_temp = round(data['current']['temperature_2m'], 1)
            cur_code = int(data['current']['weather_code'])
            cur_wind = round(data['current']['wind_speed_10m'], 1)
            cur_hum = int(data['current'].get('relative_humidity_2m', 50))

            daily_max = data['daily']['temperature_2m_max']
            daily_min = data['daily']['temperature_2m_min']
            daily_code = data['daily']['weather_code']
            daily_dates = data['daily']['time']
            daily_wind_max = data['daily'].get('wind_speed_10m_max', [cur_wind])
            daily_precip = data['daily'].get('precipitation_sum', [0.0] * len(daily_dates))

            max_w = round(daily_wind_max[0], 1) if daily_wind_max else cur_wind
            w_min = int(round(min(cur_wind, max_w)))
            w_max = int(round(max(cur_wind, max_w)))
            if w_min >= w_max:
                w_min = max(1, w_max - 3)
            wind_str = f"{w_min}-{w_max} м/с"

            result = {
                "header": cfg.get("header", f"📍 {cfg['name']}:"),
                "name": cfg["name"],
                "cur_temp": cur_temp,
                "cur_wind": cur_wind,
                "cur_hum": cur_hum,
                "cur_code": cur_code,
                "max_temp": round(daily_max[0], 1) if daily_max else cur_temp,
                "min_temp": round(daily_min[0], 1) if daily_min else cur_temp,
                "wind_str": wind_str,
                "days": []
            }
            for i in range(min(10, len(daily_dates))):
                result["days"].append({
                    "date": daily_dates[i],
                    "max": round(daily_max[i], 1),
                    "min": round(daily_min[i], 1),
                    "code": int(daily_code[i]),
                    "precip": round(daily_precip[i], 1) if i < len(daily_precip) else 0.0
                })
            _weather_cache[reg_key] = result
            _weather_cache_time = now
            return result
    except Exception as e:
        logging.warning(f"Weather fetch error for {reg_key}: {e}")
        fallback = {
            "header": cfg.get("header", f"📍 {cfg['name']}:"),
            "name": cfg["name"],
            "cur_temp": 13.0,
            "cur_wind": 4.5,
            "cur_hum": 55,
            "cur_code": 1,
            "max_temp": 14.0,
            "min_temp": 2.0,
            "wind_str": "4-8 м/с",
            "days": [
                {"date": "Бугун", "max": 14.0, "min": 2.0, "code": 1},
                {"date": "Эртага", "max": 13.5, "min": 2.0, "code": 2},
                {"date": "Индинга", "max": 12.0, "min": 1.0, "code": 3}
            ]
        }
        return fallback

def fmt_temp_c(t):
    val = round(t)
    return f"+{val}°C" if val > 0 else f"{val}°C"

def get_detailed_condition_text(code, month):
    # Ойларга қараб мослаштириш
    season = "кузги" if month in [9, 10, 11] else ("қишки" if month in [12, 1, 2] else "баҳорги")
    if code == 0:
        return f"☀️ Очиқ, илиқ {season} қуёш"
    elif code in [1, 2]:
        return f"🌤 Ўзгарувчан булутли, илиқ {season} ҳаво"
    elif code == 3:
        return "☁️ Булутли"
    elif code in [45, 48]:
        return "🌫 Туманли ҳаво"
    elif code in [51, 53, 55]:
        return "🌦 Майда ёмғир"
    elif code in [61, 63, 65]:
        return "🌧 Ёмғир ёғиши кутилади"
    elif code in [71, 73, 75]:
        return "❄️ Қор ёғиши кутилади"
    elif code in [80, 81, 82]:
        return "🌦 Қисқа ёмғир"
    elif code >= 95:
        return "⛈ Момақалдироқли ёмғир"
    return "🌤 Ўзгарувчан булутли"

def get_bee_flight_badge(temp, code):
    if code in [51, 53, 55, 61, 63, 65, 71, 73, 75, 80, 81, 82, 95]:
        return "🔴 Ёғингарчилик (Уяни очманг)"
    if temp < 7:
        return "🔴 Совуқ (Уяни очманг)"
    elif temp < 12:
        return "🟡 Салқин (Қисқа сувга парвоз)"
    elif temp < 16:
        return "🟡 Ўртача қулай (Салқин)"
    elif temp <= 28:
        return "🟢 Қулай (Фаол парвоз)"
    else:
        return "🟡 Иссиқ (Сув ва соя зарур)"

def get_bee_advice_for_temp(temp, code):
    if code in [51, 53, 55, 61, 63, 65, 71, 73, 75, 80, 81, 95]:
        return "🌧 Ёғингарчилик сабабли арилар уяда қолиши керак. Уяларга намлик тушмаслигини таъминланг."
    if temp >= 15:
        return "☀️ Ҳаво илиқ (+15°C+). Асаларилар фаол парвоз қилади, сувдонларни назорат қилинг."
    elif temp >= 10:
        return "⛅️ Ҳаво мўътадил (+10...+14°C). Оилалар клубка тўпланишга мойил. Уяларни ортиқча безовта қилманг."
    else:
        return "❄️ Ҳаво салқин/совуқ (+10°C дан паст). Арилар уяда жипс клуб шаклида. Шамоллатиш тешикларини ва уя иссиқлигини текширинг."

def get_daily_beekeeper_tip(now_dt=None):
    if not now_dt:
        now_dt = datetime.now(TASHKENT_TZ)
    idx = now_dt.timetuple().tm_yday % len(YOUNG_BEEKEEPER_TIPS)
    return YOUNG_BEEKEEPER_TIPS[idx]

def build_daily_weather_markup():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👍 1", callback_data="rx_like"),
        InlineKeyboardButton("👎", callback_data="rx_dislike"),
        InlineKeyboardButton("❤️", callback_data="rx_heart"),
        InlineKeyboardButton("👏", callback_data="rx_clap")
    )
    markup.row(
        InlineKeyboardButton("📢 Asalarichilik.Uz ↗️", url="https://t.me/Uz_Asalarichilik"),
        InlineKeyboardButton("👥 Расмий Гуруҳ ↗️", url="https://t.me/ASALARICHILIK_UZBEKISTAN")
    )
    return markup

def build_daily_weather_post_text():
    now_dt = datetime.now(TASHKENT_TZ)
    day = now_dt.day
    month_str = UZ_MONTHS.get(now_dt.month, "ноябр")
    weekday_str = UZ_WEEKDAYS.get(now_dt.weekday(), "Сешанба")

    tip = get_daily_beekeeper_tip(now_dt)

    lines = [
        "🟠 <b>Asalarichilik.Uz</b> 🇺🇿 🟡",
        "⛅️ <b>ОБ-ҲАВО МАЪЛУМОТИ — БАРЧА ВИЛОЯТЛАР (ЎЗБЕКИСТОН)</b>",
        f"🗓 <b>{day}-{month_str}, {weekday_str}</b> | Кунлик умумреспублика об-ҳаво баёни\n"
    ]

    for reg_key in WEATHER_REGIONS_ORDER:
        data = fetch_weather_for_region(reg_key)
        header = data.get("header", f"📍 {data['name']}:")
        t_max_str = fmt_temp_c(data["max_temp"])
        t_min_str = fmt_temp_c(data["min_temp"])
        cond_text = get_detailed_condition_text(data["cur_code"], now_dt.month)
        wind_str = data.get("wind_str", f"{round(data['cur_wind'])} м/с")
        flight_badge = get_bee_flight_badge(data["max_temp"], data["cur_code"])

        lines.append(f"<b>{header}</b>")
        lines.append(f"☀️ Кундузи: <b>{t_max_str}</b> | 🌙 Кечаси: <b>{t_min_str}</b>")
        lines.append(f"🌤 Ҳолат: {cond_text} | 💨 Шамол: {wind_str}")
        lines.append(f"🐝 Асаларичилик: <b>{flight_badge}</b>")
        lines.append("----------------------------------------")

    lines.append("\n💡 <b>ЯНГИ ВА ЁШ АСАЛАРИЧИЛАР УЧУН КУНЛИК ҚИЗИҚАРЛИ МАЪЛУМОТ ВА ТАВСИЯ:</b>")
    lines.append(tip["title"])
    lines.append(tip["body"])
    lines.append("----------------------------------------")
    lines.append("📌 <i>Ушбу об-ҳаво маълумоти гуруҳда доимий сақланади (ўчирилмайди).</i>")
    lines.append("🐝 @Asalarichilikuztv_bot — @JamshidjonDavronov")

    return "\n".join(lines)

def build_3days_weather_post_text():
    now_dt = datetime.now(TASHKENT_TZ)
    end_3d = now_dt + timedelta(days=2)
    start_str = f"{now_dt.day}-{UZ_MONTHS.get(now_dt.month, 'ноябр')}"
    end_str = f"{end_3d.day}-{UZ_MONTHS.get(end_3d.month, 'ноябр')}"
    weekday_str = UZ_WEEKDAYS.get(now_dt.weekday(), "Сешанба")

    lines = [
        "🟠 <b>Asalarichilik.Uz</b> 🇺🇿 🟡",
        "⛅️ <b>3 КУНЛИК ОБ-ҲАВО ВА АСАЛАРИЧИЛИК ТАҲЛИЛИ (ЎЗБЕКИСТОН)</b>",
        f"🗓 <b>{start_str} дан {end_str} гача</b> ({weekday_str}дан бошлаб)",
        "━━━━━━━━━━━━━━━━━━━━\n"
    ]

    day_labels = ["Бугун", "Эртага", "Индинга"]

    for reg_key in WEATHER_REGIONS_ORDER:
        data = fetch_weather_for_region(reg_key)
        header = data.get("header", f"📍 {data['name']}:")
        lines.append(f"<b>{header}</b>")

        days_data = data.get("days", [])
        for i in range(min(3, len(days_data))):
            d = days_data[i]
            t_max_s = fmt_temp_c(d["max"])
            t_min_s = fmt_temp_c(d["min"])
            cond_s, flight_s = WMO_CODE_TEXTS.get(d["code"], ("⛅️ Булутли", "🟡 Ўртача"))
            label = day_labels[i] if i < len(day_labels) else d.get("date", f"{i+1}-кун")
            badge = get_bee_flight_badge(d["max"], d["code"])
            lines.append(f"• <b>{label}:</b> {t_max_s} / {t_min_s} | {cond_s}")
            lines.append(f"   🐝 Асаларичилик: <b>{badge}</b>")
        lines.append("----------------------------------------")

    lines.append("\n💡 <b>ЁШ АСАЛАРИЧИЛАР УЧУН 3 КУНЛИК МУҲИМ ТАҲЛИЛ ВА РЕЖА:</b>")
    lines.append("1. 🐝 <b>Парвоз кунлари:</b> Кундузи ҳарорат +14...+17°C бўлган илиқ соатларда арилар сув ва тозаланиш учун қисқа парвоз қилади. Сувдонларни қуёшли илиқ жойга қўйинг.")
    lines.append("2. ❄️ <b>Совуқ ва ёғингарчилик кунлари:</b> Ҳарорат +10°C дан паст ва ёмғирли кунларда уяни мутлақо очманг ва силкитманг! Оилалар иссиқликни сақлаш учун клубга тўпланади.")
    lines.append("3. 🍯 <b>Озиқа назорати:</b> Озиқа захираси кам бўлган оилалар совуқда заифлашади. Рамкалар устига 0.5–1 кг канди хамири қўйиб озиқлантиринг.")
    lines.append("4. 🌬 <b>Вентиляция:</b> Намлик йиғилишига йўл қўйманг, устки ёстиқлар қуруқ пахтадан бўлиши шарт.")
    lines.append("----------------------------------------")
    lines.append("📌 <i>Ушбу 3 кунлик таҳлил гуруҳда доимий сақланади.</i>")
    lines.append("🐝 @Asalarichilikuztv_bot — @JamshidjonDavronov")

    return "\n".join(lines)

def build_10days_weather_post_text():
    now_dt = datetime.now(TASHKENT_TZ)
    end_10d = now_dt + timedelta(days=9)
    start_str = f"{now_dt.day}-{UZ_MONTHS.get(now_dt.month, 'ноябр')}"
    end_str = f"{end_10d.day}-{UZ_MONTHS.get(end_10d.month, 'ноябр')}"

    lines = [
        "🟠 <b>Asalarichilik.Uz</b> 🇺🇿 🟡",
        "📆 <b>10 КУНЛИК ОБ-ҲАВО ПРОГНОЗИ ВА СТРАТЕГИК ТАҲЛИЛ</b>",
        f"🗓 <b>{start_str} — {end_str}</b> | 10 кунлик агро-метеорологик таҳлил",
        "━━━━━━━━━━━━━━━━━━━━\n"
    ]

    lines.append("🗺 <b>ҲУДУДЛАР БЎЙИЧА 10 КУНЛИК КЎРСАТКИЧЛАР:</b>")
    for reg_key in WEATHER_REGIONS_ORDER:
        data = fetch_weather_for_region(reg_key)
        name = data.get("name", reg_key)
        days_data = data.get("days", [])
        if not days_data:
            continue
        max_temps = [d["max"] for d in days_data[:10]]
        min_temps = [d["min"] for d in days_data[:10]]
        codes = [d["code"] for d in days_data[:10]]

        avg_max = round(sum(max_temps) / len(max_temps), 1)
        lowest_min = min(min_temps)
        highest_max = max(max_temps)
        rain_days_count = sum(1 for c in codes if c in [51, 53, 55, 61, 63, 65, 71, 73, 75, 80, 81, 82, 95])

        lines.append(f"📍 <b>{name.upper()}:</b>")
        lines.append(f"• Кундузги: <b>+{highest_max}°C ... +{min(max_temps)}°C</b> (ўртача: +{avg_max}°C)")
        lines.append(f"• Энг совуқ тун: <b>{fmt_temp_c(lowest_min)}</b>")
        lines.append(f"• Ёғингарчилик кунлари: <b>{rain_days_count} кун</b>")
        strat_badge = "❄️ Қишки совуққа шайлик" if lowest_min <= 2 else "⛅️ Илиқ кузги қишлов"
        lines.append(f"• Стратегия: <i>{strat_badge}</i>\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <b>ЁШ ВА ЯНГИ АСАЛАРИЧИЛАР УЧУН 10 КУНЛИК СТРАТЕГИК ТАВСИЯЛАР:</b>")
    lines.append("1. 🍯 <b>Қишлов озиқа захираси:</b> Кейинги 10 кунда ҳарорат пасаяди. Ҳар бир уяда камида 16–20 кг озиқа борлигини назорат қилинг. Захира оз бўлса, кечиктирмай канди беринг.")
    lines.append("2. ❄️ <b>Клуб жипслиги ва тинчлик:</b> Ҳаво +8...+10°C га тушганда арилар тўлиқ шарсимон клуб ҳосил қилади. Клубни ҳеч қачон зарб билан урманг, шовқин қилманг — арилар уя тубига тўкилиб нобуд бўлади.")
    lines.append("3. 🌬 <b>Вентиляция ва намлик ҳимояси:</b> Қишда ариларни совуқ эмас, балки уя ичидаги рутубат ва димлик ҳалок қилади. Парвоз тешигини сичқон кирмайдиган қилиб торайтиринг, устки ёстиқлар қуруқ бўлишини таъминланг.")
    lines.append("4. 🐜 <b>Варроа канаси:</b> Агар даволаш ишлари якунланмаган бўлса, илиқ кунлардан бирида шошилинч Варроа канасига қарши ишлов беринг.")
    lines.append("----------------------------------------")
    lines.append("📌 <i>Ушбу 10 кунлик стратегик таҳлил гуруҳда доимий сақланади.</i>")
    lines.append("🐝 @Asalarichilikuztv_bot — @JamshidjonDavronov")

    return "\n".join(lines)

def get_current_weather_post_text(period=None):
    if not period:
        period = get_setting("weather_period", "1day")
    if period == "3days":
        return build_3days_weather_post_text()
    elif period == "10days":
        return build_10days_weather_post_text()
    else:
        return build_daily_weather_post_text()

def build_weather_preview_markup(period="1day"):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🚀 Гуруҳга юбориш", callback_data=f"send_w_{period}_group"),
        InlineKeyboardButton("📢 Каналга юбориш", callback_data=f"send_w_{period}_channel")
    )
    markup.row(
        InlineKeyboardButton("🌐 Гуруҳ + Каналга юбориш", callback_data=f"send_w_{period}_both")
    )
    markup.row(
        InlineKeyboardButton("◀️ Об-ҳаво бўлимига қайтиш", callback_data="open_weather_menu"),
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu")
    )
    return markup

def build_weather_menu_text():
    now_dt = datetime.now(TASHKENT_TZ)
    cur_hm = now_dt.strftime("%H:%M")
    is_auto = get_setting("weather_auto", "1") == "1"
    auto_status = "🟢 ЁҚИЛГАН" if is_auto else "🔴 ЎЧИРИЛГАН"
    w_time = get_setting("weather_time", "07:30")
    w_target = get_setting("weather_target", "both")
    target_str = "👥 Гуруҳ + 📢 Канал" if w_target == "both" else ("👥 Фақат Гуруҳ" if w_target == "group" else "📢 Фақат Канал")

    w_period = get_setting("weather_period", "1day")
    period_str = "1 кунлик (Кунлик баён)" if w_period == "1day" else ("3 кунлик таҳлил" if w_period == "3days" else "10 кунлик прогноз")

    tashkent_w = fetch_weather_for_region("tashkent")
    code = tashkent_w["cur_code"]
    cond_text, flight_status = WMO_CODE_TEXTS.get(code, ("⛅️ Булутли", "🟡 Ўртача"))
    bee_adv = get_bee_advice_for_temp(tashkent_w["cur_temp"], code)

    return f"""⛅️ <b>ОБ-ҲАВО МАЪЛУМОТЛАРИ ВА СОЗЛАМАЛАРИ</b>
━━━━━━━━━━━━━━━━━━━━
🕒 <b>Тошкент вақти:</b> {cur_hm} (UTC+5)
📍 <b>Тошкентда ҳозир:</b> <b>+{tashkent_w['cur_temp']}°C</b>, {cond_text}
💨 <b>Шамол:</b> {tashkent_w['cur_wind']} м/с | 💧 <b>Намлик:</b> {tashkent_w['cur_hum']}%
🐝 <b>Асаларилар парвози:</b> <b>{flight_status}</b>
💡 <b>Агро-тавсия:</b> <i>{bee_adv}</i>

⚙️ <b>АВТО-ЭЪЛОН СОЗЛАМАЛАРИ:</b>
• 📢 Ҳолати: <b>{auto_status}</b>
• 📊 Авто-эълон даври: <b>{period_str}</b>
• ⏰ Юбориш вақти: <b>Ҳар куни соат {w_time} да</b>
• 🎯 Юбориш манзили: <b>{target_str}</b>
━━━━━━━━━━━━━━━━━━━━
<i>Кўриш ёки юбориш учун бўлимни танланг:</i>"""

def build_weather_menu_markup():
    markup = InlineKeyboardMarkup()
    is_auto = get_setting("weather_auto", "1") == "1"
    auto_label = f"📢 Авто: {'🟢 Ёқилган' if is_auto else '🔴 Ўчирилган'}"
    w_time = get_setting("weather_time", "07:30")
    w_target = get_setting("weather_target", "both")
    target_label = f"🎯 Манзил: {'Гуруҳ+Канал' if w_target == 'both' else ('Фақат Гуруҳ' if w_target == 'group' else 'Фақат Канал')}"

    w_period = get_setting("weather_period", "1day")
    p_label = "1 кунлик" if w_period == "1day" else ("3 кунлик" if w_period == "3days" else "10 кунлик")

    # 1-қатор: 1 кунлик, 3 кунлик, 10 кунлик таҳлилларни кўриш
    markup.row(
        InlineKeyboardButton("🌤 1 кунлик баён", callback_data="view_wperiod_1day"),
        InlineKeyboardButton("📅 3 кунлик таҳлил", callback_data="view_wperiod_3days"),
        InlineKeyboardButton("📆 10 кунлик прогноз", callback_data="view_wperiod_10days")
    )

    # 2-қатор: Авто-эълон турини ўзгартириш
    markup.row(
        InlineKeyboardButton(f"📊 Авто-давр: {p_label} 🔄", callback_data="cycle_weather_period"),
        InlineKeyboardButton(f"⏰ Вақт: {w_time}", callback_data="pick_weather_time")
    )

    # 3-қатор: Авто-эълон ва Манзил
    markup.row(
        InlineKeyboardButton(auto_label, callback_data="toggle_weather_auto"),
        InlineKeyboardButton(target_label, callback_data="toggle_weather_target")
    )

    # 4-қатор: Тезкор юбориш тугмалари
    markup.row(
        InlineKeyboardButton("🚀 Гуруҳга юбориш", callback_data="send_weather_now_group"),
        InlineKeyboardButton("📢 Каналга юбориш", callback_data="send_weather_now_channel")
    )
    markup.row(
        InlineKeyboardButton("🌐 Гуруҳ + Каналга ҳозир юбориш", callback_data="send_weather_now_both")
    )

    # 5-қатор ва 6-қатор: Вилоятлар бўйича кўриш
    markup.row(
        InlineKeyboardButton("📍 Тошкент", callback_data="view_wreg_tashkent"),
        InlineKeyboardButton("📍 Фарғона водийси", callback_data="view_wreg_fergana")
    )
    markup.row(
        InlineKeyboardButton("📍 Самарқанд", callback_data="view_wreg_samarkand"),
        InlineKeyboardButton("📍 Бухоро / Навоий", callback_data="view_wreg_bukhara")
    )
    markup.row(
        InlineKeyboardButton("📍 Қашқадарё", callback_data="view_wreg_kashkadarya"),
        InlineKeyboardButton("📍 Хоразм", callback_data="view_wreg_khorezm")
    )

    # 7-қатор: Ортга ва Янгилаш
    markup.row(
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu"),
        InlineKeyboardButton("🔄 Янгилаш", callback_data="open_weather_menu")
    )
    return markup

def build_region_weather_text(reg_key):
    data = fetch_weather_for_region(reg_key)
    name = data["name"]
    t_cur = data["cur_temp"]
    t_max = data["max_temp"]
    t_min = data["min_temp"]
    w_spd = data["cur_wind"]
    hum = data["cur_hum"]
    code = data["cur_code"]
    cond_text, flight_status = WMO_CODE_TEXTS.get(code, ("⛅️ Булутли", "🟡 Ўртача"))
    advice = get_bee_advice_for_temp(t_cur, code)

    days_lines = []
    for d in data["days"]:
        d_code = d["code"]
        d_cond, _ = WMO_CODE_TEXTS.get(d_code, ("⛅️ Булутли", ""))
        days_lines.append(f"• <b>{d['date']}:</b> +{d['max']}°C / +{d['min']}°C — {d_cond}")

    days_block = "\n".join(days_lines)

    return f"""📍 <b>{name.upper()} — ОБ-ҲАВО ВА ТАВСИЯЛАР</b>
━━━━━━━━━━━━━━━━━━━━
🌡 <b>Ҳозирги ҳарорат:</b> +{t_cur}°C
📈 <b>Кундузги / Кечаси:</b> +{t_max}°C / +{t_min}°C
⛅️ <b>Ҳолат:</b> {cond_text}
💨 <b>Шамол:</b> {w_spd} м/с | 💧 <b>Намлик:</b> {hum}%
🐝 <b>Асаларилар парвози:</b> <b>{flight_status}</b>

📅 <b>КЕЙИНГИ КУНЛАР ПРОГНОЗИ:</b>
{days_block}

💡 <b>АСАЛАРИЧИ УЧУН АГРО-ТАВСИЯ:</b>
<i>{advice}</i>
━━━━━━━━━━━━━━━━━━━━"""

def build_region_weather_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("◀️ Об-ҳаво бўлимига қайтиш", callback_data="open_weather_menu"))
    markup.row(InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu"))
    return markup

def build_weather_time_markup():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("06:30", callback_data="set_wtime_06:30"),
        InlineKeyboardButton("07:00", callback_data="set_wtime_07:00"),
        InlineKeyboardButton("07:30", callback_data="set_wtime_07:30")
    )
    markup.row(
        InlineKeyboardButton("08:00", callback_data="set_wtime_08:00"),
        InlineKeyboardButton("08:30", callback_data="set_wtime_08:30"),
        InlineKeyboardButton("09:00", callback_data="set_wtime_09:00")
    )
    markup.row(InlineKeyboardButton("◀️ Ортга (Об-ҳаво)", callback_data="open_weather_menu"))
    return markup

def weather_scheduler_worker():
    """Ҳар куни белгиланган вақтда об-ҳавони гуруҳ/каналга автоматик юбориш."""
    last_sent_date = ""
    while True:
        try:
            now_dt = datetime.now(TASHKENT_TZ)
            today_str = now_dt.strftime("%Y-%m-%d")
            current_hm = now_dt.strftime("%H:%M")

            target_hm = get_setting("weather_time", "07:30")
            is_auto = get_setting("weather_auto", "1") == "1"

            if is_auto and current_hm == target_hm and last_sent_date != today_str:
                last_sent_date = today_str
                target = get_setting("weather_target", "both")
                post_text = get_current_weather_post_text()
                post_markup = build_daily_weather_markup()

                if target in ["both", "group"]:
                    try:
                        bot.send_message(MAIN_GROUP, post_text, reply_markup=post_markup)
                    except Exception as e:
                        logging.error(f"Auto weather to group error: {e}")

                if target in ["both", "channel"]:
                    try:
                        bot.send_message(MAIN_CHANNEL, post_text, reply_markup=post_markup)
                    except Exception as e:
                        logging.error(f"Auto weather to channel error: {e}")

                logging.info(f"⛅️ Автоматик кунлик об-ҳаво эълони юборилди ({today_str} {current_hm})")
        except Exception as e:
            logging.error(f"Weather scheduler error: {e}")
        time.sleep(30)

threading.Thread(target=weather_scheduler_worker, daemon=True).start()

# ==================== ХАБАР ҲАНДЛЕРЛАРИ ====================

# Сервис хабарлар
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def handle_service_messages(message):
    if get_setting("lock_service", "1") == "1":
        safe_delete_message(message.chat.id, message.message_id)

# Расм ва видеолар (3 талик лимит ва 24с мут)
@bot.message_handler(content_types=['photo', 'video'])
def handle_media_control(message):
    if is_official_message(message):
        return

    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0

    if message.chat.type == 'private' or is_admin(chat_id, user_id):
        return

    # Агар расм/видео остидаги матнда бегона ҳавола бўлса — дарҳол ўчириш ва огоҳлантириш:
    if get_setting("lock_links", "1") == "1" and has_foreign_links(message):
        safe_delete_message(chat_id, message.message_id)
        warn_user(chat_id, user_id, message.from_user)
        return

    is_photo = message.content_type == 'photo'
    is_video = message.content_type == 'video'

    # Текширамиз: чеклов ёқилганми ёки ўчирилганми
    if is_photo and get_setting("lock_photos", "1") != "1":
        return
    if is_video and get_setting("lock_videos", "1") != "1":
        return

    now = time.time()
    user_mention = get_mention(message.from_user)
    raw_name = message.from_user.first_name or f"User_{user_id}"
    if message.from_user.username:
        raw_name = f"{raw_name} (@{message.from_user.username})"

    media_type_label = "расм" if is_photo else "видео"

    # Альбом
    if message.media_group_id:
        mg_id = message.media_group_id
        _album_messages[mg_id].append((message.message_id, user_id))

        if len(_album_messages[mg_id]) > 3:
            for mid, _ in list(_album_messages[mg_id]):
                safe_delete_message(chat_id, mid)

            if len(_album_messages[mg_id]) == 4:
                mute_user_24h(chat_id, user_id, user_mention, user_name=raw_name, reason=f"Альбомда 3 тадан ортиқ {media_type_label}")
            return

    # Кетма-кет 60 сонияда
    user_key = (chat_id, user_id)
    _user_media_history[user_key] = [
        (mid, ts) for mid, ts in _user_media_history[user_key] if now - ts < 60
    ]
    _user_media_history[user_key].append((message.message_id, now))
    media_count = len(_user_media_history[user_key])

    if media_count > 3:
        for mid, _ in _user_media_history[user_key]:
            safe_delete_message(chat_id, mid)

        mute_user_24h(chat_id, user_id, user_mention, user_name=raw_name, reason=f"Кетма-кет 3 тадан ортиқ {media_type_label}")
        _user_media_history[user_key].clear()
        return

# Овоз, стикер ва бошқа медиалар
@bot.message_handler(content_types=['voice', 'audio', 'document', 'sticker', 'animation', 'video_note', 'contact', 'location', 'poll'])
def handle_other_media(message):
    if is_official_message(message):
        return

    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    if message.chat.type == 'private' or is_admin(chat_id, user_id):
        return

    # Агар файл ёки ҳужжат остидаги матнда бегона ҳавола бўлса:
    if get_setting("lock_links", "1") == "1" and has_foreign_links(message):
        safe_delete_message(chat_id, message.message_id)
        warn_user(chat_id, user_id, message.from_user)
        return

    # Овозли хабар қулфи
    if message.content_type in ['voice', 'audio', 'video_note'] and get_setting("lock_voice", "0") == "1":
        safe_delete_message(chat_id, message.message_id)
        return

    # Стикер ва GIF қулфи
    if message.content_type in ['sticker', 'animation'] and get_setting("lock_stickers", "0") == "1":
        safe_delete_message(chat_id, message.message_id)
        return

# Буйруқлар (Асосий Меню ва Созламалар)
@bot.message_handler(commands=['start', 'settings', 'menu', 'sozlamalar', 'help'])
def cmd_main_settings(message):
    text = build_main_menu_text()
    markup = build_main_menu_markup()
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['tungi', 'night', 'tungirejim'])
def cmd_night_shortcut(message):
    text = build_night_menu_text()
    markup = build_night_menu_markup()
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['qulflar', 'locks'])
def cmd_locks_shortcut(message):
    text = build_locks_menu_text()
    markup = build_locks_menu_markup()
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Гуруҳ матнли хабарлари
@bot.message_handler(func=lambda m: m.chat.type != 'private', content_types=['text'])
def handle_group_text(message):
    if is_official_message(message):
        return

    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    text = message.text or ""

    if is_admin(chat_id, user_id):
        return

    now = time.time()
    user_key = (chat_id, user_id)

    # Форвард хабар қулфи (бегона каналлардан форвард қилинганда)
    if getattr(message, 'forward_from', None) or getattr(message, 'forward_from_chat', None):
        if not is_official_message(message) and get_setting("lock_forwards", "0") == "1":
            safe_delete_message(chat_id, message.message_id)
            return

    # Арабча/Форсча матн қулфи
    if get_setting("lock_arabic", "1") == "1":
        if re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', text):
            safe_delete_message(chat_id, message.message_id)
            return

    # Anti-Flood (3 сонияда 5 та хабар)
    _user_msg_times[user_key] = [ts for ts in _user_msg_times[user_key] if now - ts < 3]
    _user_msg_times[user_key].append(now)
    if len(_user_msg_times[user_key]) > 5:
        safe_delete_message(chat_id, message.message_id)
        mute_user_24h(chat_id, user_id, get_mention(message.from_user), reason="Флуд (Тез-тез хабар ёзиш)")
        return

    # Реклама ва ҳаволалар (Кучайтирилган назорат — бегона канал ва ҳаволалар учун)
    if get_setting("lock_links", "1") == "1":
        if has_foreign_links(message):
            safe_delete_message(chat_id, message.message_id)
            warn_user(chat_id, user_id, message.from_user)
            return

def warn_user(chat_id, user_id, user_obj):
    # Telegram Channel proxy, botlar ёки расмий админ бўлса огоҳлантирилмайди
    if user_id in [777000, 1087968824, 136817688, OWNER_ID]:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT warn_count FROM warnings WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    row = cur.fetchone()
    count = (row[0] if row else 0) + 1
    cur.execute("INSERT OR REPLACE INTO warnings (user_id, chat_id, warn_count) VALUES (?, ?, ?)", (user_id, chat_id, count))
    conn.commit()
    conn.close()

    mention = get_mention(user_obj)
    if count >= 3:
        mute_user_24h(chat_id, user_id, mention, reason="3 марта бегона канал ва реклама тарқатиш")
        msg = bot.send_message(
            chat_id,
            f"🚫 {mention}, сизга 3 марта огоҳлантириш берилди!\n"
            f"Гуруҳда бегона реклама ва канал тарқатганингиз сабабли <b>24 соатлик МУТ</b> берилди."
        )
        delete_later(chat_id, msg.message_id, delay=35)
    else:
        msg = bot.send_message(
            chat_id,
            f"⚠️ {mention}, гуруҳда бегона реклама, канал ва ҳавола тарқатиш қатъиян тақиқланган!\n"
            f"Огоҳлантириш: <b>{count}/3</b> (3 тадан сўнг 24 соатлик мут берилади)."
        )
        delete_later(chat_id, msg.message_id, delay=35)

# Админ буйруқлари
@bot.message_handler(commands=['unmute', 'ochish'])
def cmd_unmute(message):
    chat_id = message.chat.id
    if not is_admin(chat_id, message.from_user.id):
        return

    target_user_id = None
    target_name = "Фойдаланувчи"

    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
        target_name = get_mention(message.reply_to_message.from_user)
    elif len(message.text.split()) > 1:
        try:
            target_user_id = int(message.text.split()[1])
            target_name = f"ID: {target_user_id}"
        except ValueError:
            pass

    if target_user_id:
        unmute_user_fully(chat_id, target_user_id)
        msg = bot.send_message(chat_id, f"✅ {target_name} мутдан муваффақиятли чиқарилди! Энди бемалол ёза олади.")
        delete_later(chat_id, msg.message_id, delay=30)

@bot.message_handler(commands=['mut', 'mute'])
def cmd_mute(message):
    chat_id = message.chat.id
    if not is_admin(chat_id, message.from_user.id):
        return
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        mute_user_24h(chat_id, target_user.id, get_mention(target_user), reason="Админ буйруғи билан")
        safe_delete_message(chat_id, message.message_id)

@bot.message_handler(commands=['del'])
def cmd_del(message):
    chat_id = message.chat.id
    if not is_admin(chat_id, message.from_user.id):
        return
    if message.reply_to_message:
        safe_delete_message(chat_id, message.reply_to_message.message_id)
        safe_delete_message(chat_id, message.message_id)

@bot.message_handler(commands=['stat', 'statistika'])
def cmd_stat(message):
    chat_id = message.chat.id
    if not is_admin(chat_id, message.from_user.id):
        return
    bot.reply_to(message, build_main_menu_text(), reply_markup=build_main_menu_markup())

def safe_edit_or_send(chat_id, message_id, text, markup):
    """Xabar matnini xavfsiz o'zgartirish yoki yangi qilib yuborish."""
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        err_str = str(e).lower()
        if "not modified" in err_str:
            return
        logging.warning(f"edit_message_text warning ({e}), yangi xabar yuboriladi.")
        try:
            bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e2:
            logging.error(f"send_message also failed: {e2}")

# ==================== CALLBACK QUERY ҲАНДЛЕРЛАРИ ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    if not call or not call.message:
        return

    data = call.data or ""
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # Реакциялар
    if data.startswith(("rx:", "rx_")):
        emoji_type = data.replace("rx:", "").replace("rx_", "")
        resp_msg = {
            "👍": "👍 Раҳмат! Сизга маъқул бўлганидан хурсандмиз.",
            "❤️": "❤️ Раҳмат! Асаларичиликка бўлган меҳрингиз учун ташаккур.",
            "🔥": "🔥 Ажойиб танлов! Эътиборингиз учун раҳмат.",
            "👏": "👏 Раҳмат! Қўллаб-қувватлаганингиз учун миннатдормиз.",
            "🐝": "🐝 Асаларичилик ривожи учун биргаликда олдинга!"
        }.get(emoji_type, f"✅ {emoji_type} Қабул қилинди!")
        try:
            bot.answer_callback_query(call.id, resp_msg, show_alert=False)
        except Exception:
            pass
        return

    # Ҳар қандай callback_query'га дарҳол жавоб берамиз
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # 1. Асосий меню
    if data in ["open_main_menu", "refresh_main_menu"]:
        safe_edit_or_send(chat_id, message_id, build_main_menu_text(), build_main_menu_markup())
        return

    # 2. Гуруҳ созламалари
    if data == "open_group_settings":
        safe_edit_or_send(chat_id, message_id, build_group_settings_text(), build_group_settings_markup())
        return

    # 3. Қулфлар (Чекловлар) бўлими
    if data == "open_locks_menu":
        safe_edit_or_send(chat_id, message_id, build_locks_menu_text(), build_locks_menu_markup())
        return

    # Қулфларни ўчириб-ёқиш
    if data.startswith("toggle_lock_"):
        key = data.replace("toggle_", "")
        curr = get_setting(key, "0")
        new_val = "0" if curr == "1" else "1"
        set_setting(key, new_val)
        safe_edit_or_send(chat_id, message_id, build_locks_menu_text(), build_locks_menu_markup())
        return

    # 4. Тунги режим (2-расм)
    if data == "open_night_menu":
        safe_edit_or_send(chat_id, message_id, build_night_menu_text(), build_night_menu_markup())
        return

    # Ҳолатини ўчириб-ёқиш (🟢 -> 🔴)
    if data == "toggle_night_status":
        curr = get_setting("night_mode", "1")
        new_val = "0" if curr == "1" else "1"
        set_setting("night_mode", new_val)
        safe_edit_or_send(chat_id, message_id, build_night_menu_text(), build_night_menu_markup())
        return

    # Бошланиш вақти танлаш
    if data == "pick_night_start":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("20:00", callback_data="set_start_20:00"),
            InlineKeyboardButton("21:00", callback_data="set_start_21:00"),
            InlineKeyboardButton("22:00", callback_data="set_start_22:00"),
            InlineKeyboardButton("23:00", callback_data="set_start_23:00")
        )
        markup.row(
            InlineKeyboardButton("00:00", callback_data="set_start_00:00"),
            InlineKeyboardButton("01:00", callback_data="set_start_01:00"),
            InlineKeyboardButton("02:00", callback_data="set_start_02:00")
        )
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        safe_edit_or_send(
            chat_id, message_id,
            "🔓 <b>Тунги режим бошланиш соатини танланг:</b>",
            markup
        )
        return

    if data.startswith("set_start_"):
        val = data.replace("set_start_", "")
        set_setting("night_start", val)
        safe_edit_or_send(chat_id, message_id, build_night_menu_text(), build_night_menu_markup())
        return

    # Тугаш вақти танлаш
    if data == "pick_night_end":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("04:00", callback_data="set_end_04:00"),
            InlineKeyboardButton("05:00", callback_data="set_end_05:00"),
            InlineKeyboardButton("05:30", callback_data="set_end_05:30"),
            InlineKeyboardButton("06:00", callback_data="set_end_06:00")
        )
        markup.row(
            InlineKeyboardButton("06:30", callback_data="set_end_06:30"),
            InlineKeyboardButton("07:00", callback_data="set_end_07:00"),
            InlineKeyboardButton("07:30", callback_data="set_end_07:30"),
            InlineKeyboardButton("08:00", callback_data="set_end_08:00")
        )
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        safe_edit_or_send(
            chat_id, message_id,
            "🔓 <b>Тунги режим тугаш соатини танланг:</b>",
            markup
        )
        return

    if data.startswith("set_end_"):
        val = data.replace("set_end_", "")
        set_setting("night_end", val)
        safe_edit_or_send(chat_id, message_id, build_night_menu_text(), build_night_menu_markup())
        return

    # Синов эълони юбориш
    if data == "send_night_test_now":
        test_text = get_night_warn_text()
        sent_in_group = False
        try:
            sent = bot.send_message(MAIN_GROUP, f"🧪 <b>[СИНОВ ЭЪЛОНИ]:</b>\n\n{test_text}")
            delete_later(MAIN_GROUP, sent.message_id, delay=30)
            sent_in_group = True
        except Exception as e:
            logging.error(f"Group send test error: {e}")

        try:
            sent_priv = bot.send_message(chat_id, f"🧪 <b>[СИНОВ ЭЪЛОНИ]:</b>\n\n{test_text}")
            delete_later(chat_id, sent_priv.message_id, delay=30)
        except Exception:
            pass

        alert_msg = "🚀 Гуруҳга синов эълони юборилди (30 сониядан сўнг ўчирилади)!" if sent_in_group else "🚀 Синов эълони юборилди!"
        try:
            bot.answer_callback_query(call.id, alert_msg, show_alert=True)
        except Exception:
            pass
        return

    # Огоҳлантириш матни
    if data == "edit_night_warn_prompt":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Стандарт матнга қайтариш (Сброс)", callback_data="reset_night_warn"))
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        safe_edit_or_send(
            chat_id, message_id,
            "✏️ <b>Тунги режим огоҳлантириш матни:</b>\n\nСтандарт матнга қайтариш учун пастдаги тугмани босинг:",
            markup
        )
        return

    if data == "reset_night_warn":
        set_setting("night_warn_text", "")
        safe_edit_or_send(chat_id, message_id, build_night_menu_text(), build_night_menu_markup())
        return

    # Бошқа бўлимлар
    if data == "info_media_limit":
        alert_info = (
            "📸 3 ТАЛИК МЕДИА ЛИМИТ:\n\n"
            "• Биттада (альбом) ёки кетма-кет 3 тадан кўп расм/видео юборилса:\n"
            "• Барча ташланган расмлар бир зумда ўчирилади!\n"
            "• Қоидабузарга автоматик 24 соатлик (1 кунлик) МУТ берилади."
        )
        try:
            bot.answer_callback_query(call.id, alert_info, show_alert=True)
        except Exception:
            try:
                bot.send_message(chat_id, alert_info)
            except Exception:
                pass
        return

    if data == "open_stats":
        safe_edit_or_send(chat_id, message_id, build_main_menu_text(), build_main_menu_markup())
        return

    if data == "open_broadcast_menu":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu"))
        safe_edit_or_send(
            chat_id, message_id,
            "📢 <b>Жўнатма юбориш:</b>\n\nКанал ва гуруҳга расм, видео, аудио ва хабар юбориш учун телефонингиздаги <b>Asalarichilik.Uz</b> Android иловасидан фойдаланинг!",
            markup
        )
        return

    # 5. Мутдагилар рўйхати (Muted users list)
    if data == "open_muted_list":
        safe_edit_or_send(chat_id, message_id, build_muted_list_text(), build_muted_list_markup())
        return

    if data.startswith("unmute_uid_"):
        uid = int(data.replace("unmute_uid_", ""))
        unmute_user_fully(MAIN_GROUP, uid)
        safe_edit_or_send(chat_id, message_id, build_muted_list_text(), build_muted_list_markup())
        try:
            bot.answer_callback_query(call.id, f"✅ Фойдаланувчи (ID: {uid}) мутдан озод қилинди!")
        except Exception:
            pass
        return

    if data == "unmute_all_users":
        muted = get_active_muted_users()
        total_count = len(muted)
        for u in muted:
            unmute_user_fully(MAIN_GROUP, u["user_id"])
        safe_edit_or_send(chat_id, message_id, build_muted_list_text(), build_muted_list_markup())
        try:
            bot.answer_callback_query(call.id, f"✅ Барча ({total_count} та) аъзо мутдан озод қилинди!", show_alert=True)
        except Exception:
            pass
        return

    # 6. Об-ҳаво маълумотлари ва созламалари
    if data == "open_weather_menu":
        safe_edit_or_send(chat_id, message_id, build_weather_menu_text(), build_weather_menu_markup())
        return

    if data == "toggle_weather_auto":
        curr = get_setting("weather_auto", "1")
        new_val = "0" if curr == "1" else "1"
        set_setting("weather_auto", new_val)
        safe_edit_or_send(chat_id, message_id, build_weather_menu_text(), build_weather_menu_markup())
        try:
            bot.answer_callback_query(call.id, f"Авто-эълон: {'🟢 Ёқилди' if new_val == '1' else '🔴 Ўчирилди'}")
        except Exception:
            pass
        return

    if data == "toggle_weather_target":
        curr = get_setting("weather_target", "both")
        next_map = {"both": "group", "group": "channel", "channel": "both"}
        new_val = next_map.get(curr, "both")
        set_setting("weather_target", new_val)
        safe_edit_or_send(chat_id, message_id, build_weather_menu_text(), build_weather_menu_markup())
        label = "Гуруҳ + Канал" if new_val == "both" else ("Фақат Гуруҳ" if new_val == "group" else "Фақат Канал")
        try:
            bot.answer_callback_query(call.id, f"Манзил: {label}")
        except Exception:
            pass
        return

    if data == "pick_weather_time":
        safe_edit_or_send(chat_id, message_id, "⏰ <b>Кунлик об-ҳаво эълони юборилиш вақтини танланг:</b>", build_weather_time_markup())
        return

    if data.startswith("set_wtime_"):
        val = data.replace("set_wtime_", "")
        set_setting("weather_time", val)
        safe_edit_or_send(chat_id, message_id, build_weather_menu_text(), build_weather_menu_markup())
        try:
            bot.answer_callback_query(call.id, f"Эълон вақти: {val} га созланди!")
        except Exception:
            pass
        return

    if data.startswith("view_wreg_"):
        reg_key = data.replace("view_wreg_", "")
        safe_edit_or_send(chat_id, message_id, build_region_weather_text(reg_key), build_region_weather_markup())
        return

    if data == "cycle_weather_period":
        curr = get_setting("weather_period", "1day")
        next_period = {"1day": "3days", "3days": "10days", "10days": "1day"}.get(curr, "1day")
        set_setting("weather_period", next_period)
        safe_edit_or_send(chat_id, message_id, build_weather_menu_text(), build_weather_menu_markup())
        p_label = "1 кунлик" if next_period == "1day" else ("3 кунлик" if next_period == "3days" else "10 кунлик")
        try:
            bot.answer_callback_query(call.id, f"Авто-эълон даври: {p_label} созланди!")
        except Exception:
            pass
        return

    if data == "view_wperiod_1day":
        safe_edit_or_send(chat_id, message_id, build_daily_weather_post_text(), build_weather_preview_markup("1day"))
        return

    if data == "view_wperiod_3days":
        safe_edit_or_send(chat_id, message_id, build_3days_weather_post_text(), build_weather_preview_markup("3days"))
        return

    if data == "view_wperiod_10days":
        safe_edit_or_send(chat_id, message_id, build_10days_weather_post_text(), build_weather_preview_markup("10days"))
        return

    # Муайян давр бўйича юборишлар
    if data.startswith("send_w_"):
        parts = data.split("_")  # ['send', 'w', '1day', 'group']
        if len(parts) >= 4:
            p_code = parts[2]
            dest = parts[3]
            txt = build_daily_weather_post_text() if p_code == "1day" else (build_3days_weather_post_text() if p_code == "3days" else build_10days_weather_post_text())
            mrk = build_daily_weather_markup()

            if dest in ["group", "both"]:
                try:
                    bot.send_message(MAIN_GROUP, txt, reply_markup=mrk)
                except Exception as e:
                    logging.error(f"Send {p_code} to group error: {e}")

            if dest in ["channel", "both"]:
                try:
                    bot.send_message(MAIN_CHANNEL, txt, reply_markup=mrk)
                except Exception as e:
                    logging.error(f"Send {p_code} to channel error: {e}")

            dest_str = "Гуруҳ ва Каналга" if dest == "both" else ("Гуруҳга" if dest == "group" else "Каналга")
            try:
                bot.answer_callback_query(call.id, f"🚀 {dest_str} муваффақиятли юборилди!", show_alert=True)
            except Exception:
                pass
            return

    if data == "send_weather_now_group":
        post_text = get_current_weather_post_text()
        post_markup = build_daily_weather_markup()
        sent_ok = False
        try:
            bot.send_message(MAIN_GROUP, post_text, reply_markup=post_markup)
            sent_ok = True
        except Exception as e:
            logging.error(f"Manual send weather to group error: {e}")

        alert_text = "🚀 Ўзбекистон об-ҳавоси ва таҳлил гуруҳга юборилди!" if sent_ok else "⚠️ Гуруҳга юборишда хатолик бўлди."
        try:
            bot.answer_callback_query(call.id, alert_text, show_alert=True)
        except Exception:
            pass
        return

    if data == "send_weather_now_channel":
        post_text = get_current_weather_post_text()
        post_markup = build_daily_weather_markup()
        sent_ok = False
        try:
            bot.send_message(MAIN_CHANNEL, post_text, reply_markup=post_markup)
            sent_ok = True
        except Exception as e:
            logging.error(f"Manual send weather to channel error: {e}")

        alert_text = "📢 Ўзбекистон об-ҳавоси ва таҳлил каналга юборилди!" if sent_ok else "⚠️ Каналга юборишда хатолик бўлди."
        try:
            bot.answer_callback_query(call.id, alert_text, show_alert=True)
        except Exception:
            pass
        return

    if data == "send_weather_now_both":
        post_text = get_current_weather_post_text()
        post_markup = build_daily_weather_markup()
        g_ok = False
        c_ok = False
        try:
            bot.send_message(MAIN_GROUP, post_text, reply_markup=post_markup)
            g_ok = True
        except Exception as e:
            logging.error(f"Send both to group error: {e}")

        try:
            bot.send_message(MAIN_CHANNEL, post_text, reply_markup=post_markup)
            c_ok = True
        except Exception as e:
            logging.error(f"Send both to channel error: {e}")

        alert_text = f"🌐 Об-ҳаво эълони юборилди! (Гуруҳ: {'✅' if g_ok else '❌'}, Канал: {'✅' if c_ok else '❌'})"
        try:
            bot.answer_callback_query(call.id, alert_text, show_alert=True)
        except Exception:
            pass
        return

@bot.message_handler(commands=['mutlar', 'mutes', 'unmutelist'])
def cmd_muted_list(message):
    text = build_muted_list_text()
    markup = build_muted_list_markup()
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['obhavo', 'weather', 'havo'])
def cmd_weather(message):
    text = build_weather_menu_text()
    markup = build_weather_menu_markup()
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['obhavo_1kun', 'obhavo_1', 'obhavo_post'])
def cmd_weather_1day(message):
    post_text = build_daily_weather_post_text()
    post_markup = build_daily_weather_markup()
    bot.send_message(message.chat.id, post_text, reply_markup=post_markup)

@bot.message_handler(commands=['obhavo_3kun', 'obhavo_3'])
def cmd_weather_3days(message):
    post_text = build_3days_weather_post_text()
    post_markup = build_daily_weather_markup()
    bot.send_message(message.chat.id, post_text, reply_markup=post_markup)

@bot.message_handler(commands=['obhavo_10kun', 'obhavo_10'])
def cmd_weather_10days(message):
    post_text = build_10days_weather_post_text()
    post_markup = build_daily_weather_markup()
    bot.send_message(message.chat.id, post_text, reply_markup=post_markup)

# ==================== ИШГА ТУШИРИШ (POLLING ВА АВТО-ҚАЙТА ТИКЛАНИШ) ====================
def run_bot():
    logging.info("🐝 Asalarichilik Moderation Bot ishga tushmoqda...")
    try:
        bot.delete_webhook(drop_pending_updates=False)
        logging.info("Webhook sozlamalari yangilandi.")
    except Exception as e:
        logging.warning(f"delete_webhook notice: {e}")

    while True:
        try:
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=20,
                skip_pending=False,
                allowed_updates=['message', 'callback_query', 'chat_member', 'my_chat_member']
            )
        except Exception as e:
            err_msg = str(e)
            if "409" in err_msg or "Conflict" in err_msg:
                logging.warning("409 Conflict: Boshqa bot instansi ishlayapti. 10 soniya kutiladi...")
                time.sleep(10)
            else:
                logging.error(f"Polling xatolik: {e}. 5 soniyadan so'ng qayta ishga tushadi...")
                time.sleep(5)

if __name__ == "__main__":
    run_bot()

