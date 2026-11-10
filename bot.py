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
    "weather_region": "all"
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

WEATHER_REGIONS_CONFIG = {
    "tashkent": {"name": "Тошкент ва вилояти", "lat": 41.31, "lon": 69.24},
    "fergana": {"name": "Фарғона водийси", "lat": 40.38, "lon": 71.78},
    "samarkand": {"name": "Самарқанд ва Жиззах", "lat": 39.65, "lon": 66.97},
    "bukhara": {"name": "Бухоро ва Навоий", "lat": 39.77, "lon": 64.42},
    "kashkadarya": {"name": "Қашқадарё ва Сурхондарё", "lat": 38.86, "lon": 65.79},
    "khorezm": {"name": "Хоразм ва Қорақалпоғистон", "lat": 41.55, "lon": 60.63}
}

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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={cfg['lat']}&longitude={cfg['lon']}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code,wind_speed_10m_max&timezone=Asia%2FTashkent"
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

            result = {
                "name": cfg["name"],
                "cur_temp": cur_temp,
                "cur_wind": cur_wind,
                "cur_hum": cur_hum,
                "cur_code": cur_code,
                "max_temp": round(daily_max[0], 1) if daily_max else cur_temp,
                "min_temp": round(daily_min[0], 1) if daily_min else cur_temp,
                "days": []
            }
            for i in range(min(4, len(daily_dates))):
                result["days"].append({
                    "date": daily_dates[i],
                    "max": round(daily_max[i], 1),
                    "min": round(daily_min[i], 1),
                    "code": int(daily_code[i])
                })
            _weather_cache[reg_key] = result
            _weather_cache_time = now
            return result
    except Exception as e:
        logging.warning(f"Weather fetch error for {reg_key}: {e}")
        fallback = {
            "name": cfg["name"],
            "cur_temp": 14.5,
            "cur_wind": 3.2,
            "cur_hum": 55,
            "cur_code": 1,
            "max_temp": 16.0,
            "min_temp": 6.0,
            "days": [
                {"date": "Бугун", "max": 16.0, "min": 6.0, "code": 1},
                {"date": "Эртага", "max": 14.5, "min": 5.0, "code": 2},
                {"date": "Индинга", "max": 13.0, "min": 4.0, "code": 3}
            ]
        }
        return fallback

def get_bee_advice_for_temp(temp, code):
    if code in [51, 53, 55, 61, 63, 65, 71, 73, 75, 80, 81, 95]:
        return "🌧 Ёғингарчилик сабабли арилар уяда қолиши керак. Уяларга намлик тушмаслигини таъминланг."
    if temp >= 15:
        return "☀️ Ҳаво илиқ (+15°C+). Асаларилар фаол парвоз қилади, сувдонларни назорат қилинг."
    elif temp >= 10:
        return "⛅️ Ҳаво мўътадил (+10...+14°C). Оилалар клубка тўпланишга мойил. Уяларни ортиқча безовта қилманг."
    else:
        return "❄️ Ҳаво салқин/совуқ (+10°C дан паст). Арилар уяда жипс клуб шаклида. Шамоллатиш тешикларини ва уя иссиқлигини текширинг."

def build_daily_weather_post_text():
    now_dt = datetime.now(TASHKENT_TZ)
    date_str = now_dt.strftime("%d-%m-%Y")

    lines = [
        f"⛅️ <b>АСАЛАРИЧИЛИК ВА КУНЛИК ОБ-ҲАВО МАЪЛУМОТИ</b>",
        f"📅 <b>Сана:</b> {date_str} | Тошкент вақти",
        "━━━━━━━━━━━━━━━━━━━━"
    ]

    for reg_key in ["tashkent", "fergana", "samarkand", "bukhara", "kashkadarya", "khorezm"]:
        data = fetch_weather_for_region(reg_key)
        name = data["name"]
        t_cur = data["cur_temp"]
        t_max = data["max_temp"]
        t_min = data["min_temp"]
        w_spd = data["cur_wind"]
        code = data["cur_code"]

        cond_text, flight_status = WMO_CODE_TEXTS.get(code, ("⛅️ Булутли", "🟡 Парвоз ўртача"))
        lines.append(f"📍 <b>{name.upper()}:</b>")
        lines.append(f"• Ҳарорат: <b>+{t_max}°C</b> / <b>+{t_min}°C</b> (ҳозир: +{t_cur}°C)")
        lines.append(f"• Ҳолат: {cond_text} | Шамол: {w_spd} м/с")
        lines.append(f"• Асаларилар парвози: <b>{flight_status}</b>\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🐝 <b>МУҲИМ АСАЛАРИЧИЛИК ТАВСИЯСИ:</b>")
    lines.append("<i>Ҳаво ҳарорати ва ёғингарчиликка қараб уяларни қишловга тўғри тайёрланг. Шамоллатиш тешикларини назорат қилинг ва намлик тўпланишига йўл қўйманг. Зарур бўлса канди ёки озиқа билан таъминланг.</i>")
    lines.append("\n📢 Канал: @Uz_Asalarichilik | 👥 Гуруҳ: @Asalarichilik_Uzbekistan")

    return "\n".join(lines)

def build_weather_menu_text():
    now_dt = datetime.now(TASHKENT_TZ)
    cur_hm = now_dt.strftime("%H:%M")
    is_auto = get_setting("weather_auto", "1") == "1"
    auto_status = "🟢 ЁҚИЛГАН" if is_auto else "🔴 ЎЧИРИЛГАН"
    w_time = get_setting("weather_time", "07:30")
    w_target = get_setting("weather_target", "both")
    target_str = "👥 Гуруҳ + 📢 Канал" if w_target == "both" else ("👥 Фақат Гуруҳ" if w_target == "group" else "📢 Фақат Канал")

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
• ⏰ Юбориш вақти: <b>Ҳар куни соат {w_time} да</b>
• 🎯 Юбориш манзили: <b>{target_str}</b>
━━━━━━━━━━━━━━━━━━━━
<i>Керакли амални ёки вилоятни танланг:</i>"""

def build_weather_menu_markup():
    markup = InlineKeyboardMarkup()
    is_auto = get_setting("weather_auto", "1") == "1"
    auto_label = f"📢 Авто-эълон: {'🟢 Ёқилган' if is_auto else '🔴 Ўчирилган'}"
    w_time = get_setting("weather_time", "07:30")
    w_target = get_setting("weather_target", "both")
    target_label = f"🎯 Манзил: {'Гуруҳ+Канал' if w_target == 'both' else ('Фақат Гуруҳ' if w_target == 'group' else 'Фақат Канал')}"

    # 1-қатор: Авто-эълон ва Вақти
    markup.row(
        InlineKeyboardButton(auto_label, callback_data="toggle_weather_auto"),
        InlineKeyboardButton(f"⏰ Вақт: {w_time}", callback_data="pick_weather_time")
    )
    # 2-қатор: Манзил танлаш
    markup.row(InlineKeyboardButton(target_label, callback_data="toggle_weather_target"))

    # 3-қатор: Тезкор юбориш тугмалари
    markup.row(
        InlineKeyboardButton("🚀 Гуруҳга ҳозир юбориш", callback_data="send_weather_now_group"),
        InlineKeyboardButton("📢 Каналга ҳозир юбориш", callback_data="send_weather_now_channel")
    )

    # 4-қатор ва 5-қатор: Вилоятлар бўйича кўриш
    markup.row(
        InlineKeyboardButton("📍 Тошкент", callback_data="view_wreg_tashkent"),
        InlineKeyboardButton("📍 Фарғона водийси", callback_data="view_wreg_fergana")
    )
    markup.row(
        InlineKeyboardButton("📍 Самарқанд", callback_data="view_wreg_samarkand"),
        InlineKeyboardButton("📍 Бухоро / Навоий", callback_data="view_wreg_bukhara")
    )
    markup.row(
        InlineKeyboardButton("📍 Сурхондарё", callback_data="view_wreg_kashkadarya"),
        InlineKeyboardButton("📍 Хоразм", callback_data="view_wreg_khorezm")
    )

    # 6-қатор: Ортга ва Янгилаш
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
                post_text = build_daily_weather_post_text()

                if target in ["both", "group"]:
                    try:
                        bot.send_message(MAIN_GROUP, post_text)
                    except Exception as e:
                        logging.error(f"Auto weather to group error: {e}")

                if target in ["both", "channel"]:
                    try:
                        bot.send_message(MAIN_CHANNEL, post_text)
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
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == 'private' or is_admin(chat_id, user_id):
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

    if data == "send_weather_now_group":
        post_text = build_daily_weather_post_text()
        sent_ok = False
        try:
            bot.send_message(MAIN_GROUP, post_text)
            sent_ok = True
        except Exception as e:
            logging.error(f"Manual send weather to group error: {e}")

        alert_text = "🚀 Об-ҳаво эълони гуруҳга муваффақиятли юборилди!" if sent_ok else "⚠️ Гуруҳга юборишда хатолик бўлди (Бот гуруҳда админ эканлигини текширинг)."
        try:
            bot.answer_callback_query(call.id, alert_text, show_alert=True)
        except Exception:
            pass
        return

    if data == "send_weather_now_channel":
        post_text = build_daily_weather_post_text()
        sent_ok = False
        try:
            bot.send_message(MAIN_CHANNEL, post_text)
            sent_ok = True
        except Exception as e:
            logging.error(f"Manual send weather to channel error: {e}")

        alert_text = "📢 Об-ҳаво эълони каналга муваффақиятли юборилди!" if sent_ok else "⚠️ Каналга юборишда хатолик бўлди (Бот каналда админ эканлигини текширинг)."
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

