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
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logging.info(f"🌐 HTTP Health сервер {port}-портда ишга тушди.")
        server.serve_forever()
    except Exception as e:
        logging.error(f"HTTP server error: {e}")

threading.Thread(target=start_http_health, daemon=True).start()

# ==================== ДАТАБАЗА ВА КЭШ ====================
DB_PATH = "bot_moderation.db"
_settings_cache = {
    "night_mode": "1",
    "night_start": "00:00",
    "night_end": "06:30",
    "night_warn_text": "",
    "lock_links": "1",
    "lock_voice": "0",
    "lock_stickers": "0",
    "lock_forwards": "0",
    "lock_arabic": "1",
    "lock_service": "1",
    "auto_react": "1",
    "share_btn": "1",
    "expert_btn": "1"
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
                PRIMARY KEY (user_id, chat_id)
            )
        """)
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
    if user_id == OWNER_ID:
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

def mute_user_24h(chat_id, user_id, user_mention, reason="3 тадан ортиқ расм/видео юборилди"):
    until_date = int(time.time()) + 86400  # 24 соат
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
        cur.execute("INSERT OR REPLACE INTO muted_users (user_id, chat_id, muted_until, reason) VALUES (?, ?, ?, ?)", (user_id, chat_id, until_date, reason))
        conn.commit()
        conn.close()
    except Exception:
        pass

    notice_text = f"""
⚠️ <b>ҚАТЪИЙ ОГОҲЛАНТИРИШ ВА ЖАЗО!</b>
━━━━━━━━━━━━━━━━━━━━
👤 Фойдаланувчи: {user_mention}
🚫 Сабаб: <b>3 тадан ортиқ расм ёки видео юборилди!</b>
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
    try:
        bot.restrict_chat_member(
            chat_id=chat_id,
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
                chat_id=chat_id,
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
        cur.execute("DELETE FROM muted_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

def check_night_mode_violation(message):
    if message.chat.type == 'private':
        return False
    # Админларга чеклов йўқ
    if is_admin(message.chat.id, message.from_user.id):
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

    return f"""🐝 <b>ASALARICHILIK.UZ — БОШҚАРУВ МАРКАЗИ</b>
━━━━━━━━━━━━━━━━━━━━
🟢 <b>Бот ҳолати:</b> ОНЛАЙН (Серверда узлуксиз ишламоқда)
🕒 <b>Тошкент вақти:</b> {current_time_str} (UTC+5)
⚡️ <b>Жорий режим:</b> <b>{active_now_text}</b>

🛡 <b>ГУРУҲ ҲИМОЯ ҲОЛАТИ:</b>
• 🌙 <b>Тунги режим:</b> <b>{night_status_icon}</b> ({start_str} дан {end_str} гача)
• 🔒 <b>Қулфлар (Чекловлар):</b> 🟢 <b>Фаол</b> (Расм, Видео, Спам)
• 📸 <b>3 талик медиа лимит:</b> 🟢 <b>Фаол</b> (4 та бўлса 24с МУТ)
• 🔇 <b>Ҳозир мутда:</b> <b>{active_mutes} та аъзо</b>
• 👥 <b>Гуруҳ:</b> {MAIN_GROUP}
━━━━━━━━━━━━━━━━━━━━
<i>Керакли бўлимни танланг:</i>"""

def build_main_menu_markup():
    markup = InlineKeyboardMarkup()
    is_on = get_setting("night_mode", "1") == "1"
    btn_night_text = f"🌙 Тунги Режим ({'🟢 Ёқилган' if is_on else '🔴 Ўчирилган'})"

    markup.row(InlineKeyboardButton("⚙️ Гуруҳ Созламалари", callback_data="open_group_settings"))
    markup.row(
        InlineKeyboardButton("🔒 Қулфлар (Чекловлар)", callback_data="open_locks_menu"),
        InlineKeyboardButton(btn_night_text, callback_data="open_night_menu")
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
Бот гуруҳ хавфсизлигини 100% таъминлайди.

Қуйидаги бўлимлардан кераклисини танланг:
• 🔒 <b>Қулфлар (Чекловлар):</b> Расм, видео, ҳавола, овоз ва стикерлар чеклови.
• 🌙 <b>Тунги режим:</b> Соат 00:00 дан 06:30 гача гуруҳни автоматик қулфлаш.
• 📸 <b>3 талик медиа лимит:</b> Спам тарзида расм ташлаганларга 24 соатлик мут.
• 🧹 <b>Сервис хабарлар:</b> Аъзолар кирди-чиқдисини автоматик тозалаш.
━━━━━━━━━━━━━━━━━━━━"""

def build_group_settings_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔒 Қулфлар ва Чекловлар бўлими", callback_data="open_locks_menu"))
    markup.row(InlineKeyboardButton("🌙 Тунги Режим Созламалари", callback_data="open_night_menu"))
    markup.row(InlineKeyboardButton("📸 3 талик Медиа Назорат Ҳолати", callback_data="info_media_limit"))
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

🟢 = Қулфланган (гуруҳда тақиқланади)
🔴 = Рухсат берилган (аъзолар ёза олади)
━━━━━━━━━━━━━━━━━━━━"""

def build_locks_menu_markup():
    markup = InlineKeyboardMarkup()

    l_links = "🟢" if get_setting("lock_links", "1") == "1" else "🔴"
    l_voice = "🟢" if get_setting("lock_voice", "0") == "1" else "🔴"
    l_stickers = "🟢" if get_setting("lock_stickers", "0") == "1" else "🔴"
    l_forwards = "🟢" if get_setting("lock_forwards", "0") == "1" else "🔴"
    l_arabic = "🟢" if get_setting("lock_arabic", "1") == "1" else "🔴"
    l_service = "🟢" if get_setting("lock_service", "1") == "1" else "🔴"
    l_night = "🟢" if get_setting("night_mode", "1") == "1" else "🔴"

    markup.row(InlineKeyboardButton("📸 Расмлар: 3 та лимит (24с МУТ)", callback_data="info_media_limit"))
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

# ==================== ХАБАР ҲАНДЛЕРЛАРИ ====================

# Сервис хабарлар
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def handle_service_messages(message):
    if get_setting("lock_service", "1") == "1":
        safe_delete_message(message.chat.id, message.message_id)

# Расм ва видеолар (3 талик лимит ва 24с мут)
@bot.message_handler(content_types=['photo', 'video'])
def handle_media_control(message):
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == 'private' or is_admin(chat_id, user_id):
        return

    now = time.time()
    user_mention = get_mention(message.from_user)

    # Альбом
    if message.media_group_id:
        mg_id = message.media_group_id
        _album_messages[mg_id].append((message.message_id, user_id))

        if len(_album_messages[mg_id]) > 3:
            for mid, _ in list(_album_messages[mg_id]):
                safe_delete_message(chat_id, mid)

            if len(_album_messages[mg_id]) == 4:
                mute_user_24h(chat_id, user_id, user_mention, reason="Альбомда 3 тадан ортиқ расм/видео")
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

        mute_user_24h(chat_id, user_id, user_mention, reason="Кетма-кет 3 тадан ортиқ расм/видео")
        _user_media_history[user_key].clear()
        return

# Овоз, стикер ва бошқа медиалар
@bot.message_handler(content_types=['voice', 'audio', 'document', 'sticker', 'animation', 'video_note', 'contact', 'location', 'poll'])
def handle_other_media(message):
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    if message.chat.type == 'private' or is_admin(chat_id, message.from_user.id):
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
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text or ""

    if is_admin(chat_id, user_id):
        return

    now = time.time()
    user_key = (chat_id, user_id)

    # Форвард хабар қулфи
    if getattr(message, 'forward_from', None) or getattr(message, 'forward_from_chat', None):
        if get_setting("lock_forwards", "0") == "1":
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

    # Реклама ва ҳаволалар
    if get_setting("lock_links", "1") == "1":
        if any(kw in text.lower() for kw in ["http://", "https://", "t.me/"]):
            if not any(allowed in text for allowed in ["t.me/Uz_Asalarichilik", "t.me/ASALARICHILIK_UZBEKISTAN", "t.me/JamshidjonDavronov"]):
                safe_delete_message(chat_id, message.message_id)
                warn_user(chat_id, user_id, message.from_user)
                return

def warn_user(chat_id, user_id, user_obj):
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
        mute_user_24h(chat_id, user_id, mention, reason="3 марта реклама/спам тарқатиш")
    else:
        msg = bot.send_message(
            chat_id,
            f"⚠️ {mention}, гуруҳда бегона реклама ва ҳавола тарқатиш тақиқланган!\nОгоҳлантириш: <b>{count}/3</b> (3 тадан сўнг 24 соатлик мут берилади)."
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

# ==================== CALLBACK QUERY ҲАНДЛЕРЛАРИ ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    data = call.data
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
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_main_menu_text(),
                reply_markup=build_main_menu_markup()
            )
        except Exception:
            pass
        return

    # 2. Гуруҳ созламалари
    if data == "open_group_settings":
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_group_settings_text(),
                reply_markup=build_group_settings_markup()
            )
        except Exception:
            pass
        return

    # 3. Қулфлар (Чекловлар) бўлими
    if data == "open_locks_menu":
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_locks_menu_text(),
                reply_markup=build_locks_menu_markup()
            )
        except Exception:
            pass
        return

    # Қулфларни ўчириб-ёқиш
    if data.startswith("toggle_lock_"):
        key = data.replace("toggle_", "")
        curr = get_setting(key, "0")
        new_val = "0" if curr == "1" else "1"
        set_setting(key, new_val)
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_locks_menu_text(),
                reply_markup=build_locks_menu_markup()
            )
        except Exception:
            pass
        return

    # 4. Тунги режим (2-расм)
    if data == "open_night_menu":
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_night_menu_text(),
                reply_markup=build_night_menu_markup()
            )
        except Exception:
            pass
        return

    # Ҳолатини ўчириб-ёқиш (🟢 -> 🔴)
    if data == "toggle_night_status":
        curr = get_setting("night_mode", "1")
        new_val = "0" if curr == "1" else "1"
        set_setting("night_mode", new_val)
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_night_menu_text(),
                reply_markup=build_night_menu_markup()
            )
        except Exception:
            pass
        return

    # Бошланиш вақти танлаш
    if data == "pick_night_start":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("22:00", callback_data="set_start_22:00"),
            InlineKeyboardButton("23:00", callback_data="set_start_23:00"),
            InlineKeyboardButton("00:00", callback_data="set_start_00:00"),
            InlineKeyboardButton("01:00", callback_data="set_start_01:00")
        )
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="🔓 <b>Тунги режим бошланиш соатини танланг:</b>",
                reply_markup=markup
            )
        except Exception:
            pass
        return

    if data.startswith("set_start_"):
        val = data.replace("set_start_", "")
        set_setting("night_start", val)
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_night_menu_text(),
                reply_markup=build_night_menu_markup()
            )
        except Exception:
            pass
        return

    # Тугаш вақти танлаш
    if data == "pick_night_end":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("05:00", callback_data="set_end_05:00"),
            InlineKeyboardButton("06:00", callback_data="set_end_06:00"),
            InlineKeyboardButton("06:30", callback_data="set_end_06:30"),
            InlineKeyboardButton("07:00", callback_data="set_end_07:00")
        )
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="🔓 <b>Тунги режим тугаш соатини танланг:</b>",
                reply_markup=markup
            )
        except Exception:
            pass
        return

    if data.startswith("set_end_"):
        val = data.replace("set_end_", "")
        set_setting("night_end", val)
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_night_menu_text(),
                reply_markup=build_night_menu_markup()
            )
        except Exception:
            pass
        return

    # Синов эълони юбориш
    if data == "send_night_test_now":
        test_text = get_night_warn_text()
        try:
            sent = bot.send_message(MAIN_GROUP, f"🧪 <b>[СИНОВ ЭЪЛОНИ]:</b>\n\n{test_text}")
            delete_later(MAIN_GROUP, sent.message_id, delay=30)
        except Exception:
            pass
        return

    # Огоҳлантириш матни
    if data == "edit_night_warn_prompt":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Стандарт матнга қайтариш (Сброс)", callback_data="reset_night_warn"))
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="✏️ <b>Тунги режим огоҳлантириш матни:</b>\n\nСтандарт матнга қайтариш учун пастдаги тугмани босинг:",
                reply_markup=markup
            )
        except Exception:
            pass
        return

    if data == "reset_night_warn":
        set_setting("night_warn_text", "")
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_night_menu_text(),
                reply_markup=build_night_menu_markup()
            )
        except Exception:
            pass
        return

    # Бошқа бўлимлар
    if data == "info_media_limit":
        try:
            bot.send_message(chat_id, "📸 <b>3 талик медиа лимит:</b>\nАъзолар 3 тадан кўп расм ёки видео юборса, барча ташланган расмлар ўчирилади ва 24 соатлик МУТ берилади.")
        except Exception:
            pass
        return

    if data == "open_stats":
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=build_main_menu_text(),
                reply_markup=build_main_menu_markup()
            )
        except Exception:
            pass
        return

    if data == "open_broadcast_menu":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu"))
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="📢 <b>Жўнатма юбориш:</b>\n\nКанал ва гуруҳга расм, видео, аудио ва хабар юбориш учун телефонингиздаги <b>Asalarichilik.Uz</b> Android иловасидан фойдаланинг!",
                reply_markup=markup
            )
        except Exception:
            pass
        return

# ==================== ИШГА ТУШИРИШ (POLLING ВА АВТО-ҚАЙТА ТИКЛАНИШ) ====================
def run_bot():
    logging.info("🐝 Asalarichilik Moderation Bot ishga tushmoqda...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            err_msg = str(e)
            if "409" in err_msg or "Conflict" in err_msg:
                logging.warning("409 Conflict: Boshqa bot instansi ishlayapti. 15 soniya kutiladi...")
                time.sleep(15)
            else:
                logging.error(f"Polling xatolik: {e}. 5 soniyadan so'ng qayta ishga tushadi...")
                time.sleep(5)

if __name__ == "__main__":
    run_bot()
