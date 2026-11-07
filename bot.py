#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐝 Asalarichilik.Uz — Telegram Гуруҳ Назорат & Хавфсизлик Боти
Муаллиф ва Бот эгаси: @JamshidjonDavronov (ID: 2047501151)
Бот: @Asalarichilikuztv_bot

Render.com ва Серверлар учун тўлиқ мослаштирилган:
1. 🌐 Render.com HTTP Health-Check сервери (Port Binding)
2. 🌙 ТУНГИ РЕЖИМ (Night Mode) тўлиқ интерактив менюси ва онлайн ҳолати
3. 📸 3 ТАДАН ОРТИҚ РАСМ ВА ВИДЕО НАЗОРАТИ (24 соатлик МУТ)
4. 🚫 Реклама ва спам линкларни дарҳол ўчириш
5. 🧹 Сервис хабарларини тозалаш
6. 👮‍♂️ Админ буйруқлари: /start, /settings, /menu, /tungi, /mut, /unmute, /stat, /del
7. 😊 Смайлик реакциялари (👍 ❤️ 🔥 👏 🐝)
"""

import os
import sys
import time
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

# ==================== RENDER.COM HTTP HEALTH CHECK ====================
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - Asalarichilik Moderation Bot is active and running on Render!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_render_http():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), RenderHealthServer)
        logging.info(f"🌐 Render HTTP сервери {port}-портда ишга тушди.")
        server.serve_forever()
    except Exception as e:
        logging.error(f"Render HTTP server xatolik: {e}")

threading.Thread(target=start_render_http, daemon=True).start()

# ==================== ДАТАБАЗА ====================
DB_PATH = "bot_moderation.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
    # 2-расмдаги стандарт вақтлар: 00:00 дан 06:30 гача
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_mode', '1')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_start', '00:00')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_end', '06:30')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_warn_text', '')")
    conn.commit()
    conn.close()

init_db()

def get_setting(key, default=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if (row and row[0] is not None) else default
    except Exception:
        return default

def set_setting(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ==================== ТУНГИ РЕЖИМ ВА ВАҚТ ҲИСОБ-КИТОБИ ====================
def parse_time_to_minutes(time_str):
    try:
        parts = time_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except Exception:
        return 0

def is_night_mode_now():
    """Тошкент вақти (UTC+5) билан тунги режим фаоллигини дақиқасигача аниқлаш"""
    enabled = get_setting("night_mode", "1") == "1"
    if not enabled:
        return False

    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")

    start_min = parse_time_to_minutes(start_str)
    end_min = parse_time_to_minutes(end_str)

    now_dt = datetime.now(TASHKENT_TZ)
    now_min = now_dt.hour * 60 + now_dt.minute

    if start_min > end_min:  # Масалан 23:00 дан 06:30 гача
        return now_min >= start_min or now_min < end_min
    elif start_min < end_min:  # Масалан 00:00 дан 06:30 гача
        return start_min <= now_min < end_min
    else:
        return True

def get_remaining_night_time_str():
    """Қулф очилгунча қолган вақтни ҳисоблаш (соат ва дақиқа)"""
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
    """2-расмдагидек аниқ огоҳлантириш матни"""
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

# ==================== КЭШ ВА АДМИН ТЕКШИРУВИ ====================
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
        cur.execute(
            "INSERT OR REPLACE INTO muted_users (user_id, chat_id, muted_until, reason) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, until_date, reason)
        )
        cur.execute(
            "INSERT INTO group_stats (chat_id, muted_count) VALUES (?, 1) ON CONFLICT(chat_id) DO UPDATE SET muted_count = muted_count + 1",
            (chat_id,)
        )
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

# ==================== ТУНГИ РЕЖИМДА ХАБАР ЎЧИРИШ ====================
def check_night_mode_violation(message):
    if message.chat.type == 'private':
        return False
    if is_admin(message.chat.id, message.from_user.id):
        return False

    if is_night_mode_now():
        safe_delete_message(message.chat.id, message.message_id)

        now = time.time()
        user_key = (message.chat.id, message.from_user.id)
        last_warn = _night_warn_cache.get(user_key, 0)

        # Бир аъзога 2 дақиқада максимум 1 марта огоҳлантириш чиқарилади
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

# ==================== АСОСИЙ МЕНЮ ВА 2-РАСМ ТУНГИ РЕЖИМ МЕНЮЛАРИ ====================
def build_main_menu_text():
    now_dt = datetime.now(TASHKENT_TZ)
    current_time_str = now_dt.strftime("%H:%M")
    is_on = get_setting("night_mode", "1") == "1"
    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")
    is_active_now = is_night_mode_now()

    night_status_icon = "🟢 ЁҚИЛГАН" if is_on else "🔴 ЎЧИРИЛГАН"
    active_now_text = "🌙 Ҳозир ТУНГИ РЕЖИМДА (Ёзиш чекланган)" if is_active_now else "☀️ Ҳозир КУНДУЗГИ РЕЖИМДА (Ёзиш мумкин)"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM muted_users WHERE muted_until > ?", (int(time.time()),))
    active_mutes = cur.fetchone()[0]
    cur.execute("SELECT deleted_media, muted_count, deleted_links FROM group_stats WHERE chat_id = (SELECT chat_id FROM group_stats LIMIT 1)")
    stat_row = cur.fetchone()
    conn.close()

    total_mutes = stat_row[1] if stat_row else 0

    return f"""🐝 <b>ASALARICHILIK.UZ — БОШҚАРУВ ПАНЕЛИ</b>
━━━━━━━━━━━━━━━━━━━━
🟢 <b>Бот ҳолати:</b> ОНЛАЙН (Серверда узлуксиз ишламоқда)
🕒 <b>Тошкент вақти:</b> {current_time_str} (UTC+5)
⚡️ <b>Жорий режим:</b> <b>{active_now_text}</b>

🛡 <b>ГУРУҲ ҲИМОЯ ВА ХАВФСИЗЛИК ҲОЛАТИ:</b>
• 🌙 <b>Тунги режим:</b> <b>{night_status_icon}</b> ({start_str} дан {end_str} гача)
• 📸 <b>Медиа назорат:</b> 🟢 <b>3 талик лимит</b> (4 та бўлса 24с МУТ)
• 🚫 <b>Спам ва ҳаволалар:</b> 🟢 <b>Авто-тозалаш</b>
• 🔇 <b>Ҳозир фаол мутда:</b> <b>{active_mutes} та аъзо</b> (Жами: {total_mutes})
• 👥 <b>Гуруҳ:</b> {MAIN_GROUP}
━━━━━━━━━━━━━━━━━━━━
<i>Керакли бўлимни бошқариш учун қуйидаги тугмалардан бирини босинг:</i>"""

def build_main_menu_markup():
    markup = InlineKeyboardMarkup()
    is_on = get_setting("night_mode", "1") == "1"
    btn_night_text = "🌙 Тунги Режим Созламалари (🟢 Ёқилган)" if is_on else "🌙 Тунги Режим Созламалари (🔴 Ўчирилган)"
    markup.row(InlineKeyboardButton(btn_night_text, callback_data="open_night_menu"))
    markup.row(InlineKeyboardButton("📸 3 талик Медиа Назорат (Фаол)", callback_data="info_media_limit"))
    markup.row(InlineKeyboardButton("📊 Гуруҳ Статистикаси", callback_data="open_stats"))
    markup.row(
        InlineKeyboardButton("📢 Расмий Канал", url="https://t.me/Uz_Asalarichilik"),
        InlineKeyboardButton("👥 Расмий Гуруҳ", url="https://t.me/ASALARICHILIK_UZBEKISTAN")
    )
    markup.row(InlineKeyboardButton("🔄 Маълумотларни янгилаш", callback_data="refresh_main_menu"))
    return markup

def build_night_menu_text():
    """2-расмдагидек кўриниш ва огоҳлантириш матни"""
    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")
    is_on = get_setting("night_mode", "1") == "1"
    now_dt = datetime.now(TASHKENT_TZ)
    current_time_str = now_dt.strftime("%H:%M")

    warn_text = get_night_warn_text()
    status_str = "🟢 Ёқилган" if is_on else "🔴 Ўчирилган"

    return f"""🌙 <b>ТУНГИ РЕЖИМ БОШҚАРУВИ</b>
━━━━━━━━━━━━━━━━━━━━
• Тошкент вақти: <b>{current_time_str}</b>
• Ҳолати: <b>{status_str}</b>
• Блокировка вақти: <b>соат {start_str} дан {end_str} гача</b>

Тунги вақтда юборилган барча хабарлар бот томонидан автоматик ўчирилади (30 сониядан сўнг тозаланади).

💬 <b>Ҳозирги огоҳлантириш матни:</b>
{warn_text}"""

def build_night_menu_markup():
    """2-расмдаги тугмалар билан 100% бир хил тузилиш"""
    is_on = get_setting("night_mode", "1") == "1"
    status_label = "Ҳолати / Status: 🟢 Ёқилган" if is_on else "Ҳолати / Status: 🔴 Ўчирилган"
    start_str = get_setting("night_start", "00:00")
    end_str = get_setting("night_end", "06:30")

    markup = InlineKeyboardMarkup()
    # 1-қатор: Ҳолати (босганда дарҳол ўчиб-ёнади)
    markup.row(InlineKeyboardButton(status_label, callback_data="toggle_night_status"))
    # 2-қатор: Бошланиш ва Тугаш вақтлари
    markup.row(
        InlineKeyboardButton(f"🔓 Бошланиш: {start_str}", callback_data="pick_night_start"),
        InlineKeyboardButton(f"🔓 Тугаш: {end_str}", callback_data="pick_night_end")
    )
    # 3-қатор: Огоҳлантириш матнини ўзгартириш
    markup.row(InlineKeyboardButton("✏️ Огоҳлантириш матнини ўзгартириш", callback_data="edit_night_warn_prompt"))
    # 4-қатор: Синов эълонини юбориш
    markup.row(InlineKeyboardButton("🚀 Ҳозироқ синов эълонини юбориш", callback_data="send_night_test_now"))
    # 5-қатор: Ортга қайтиш тугмалари
    markup.row(
        InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data="open_main_menu"),
        InlineKeyboardButton("◀️ Асосий Меню", callback_data="open_main_menu")
    )
    return markup

# ==================== ХАБАРЛАР ВА БУЙРУҚЛАР ҲАНДЛЕРЛАРИ ====================

# 1. Кирди-чиқди сервис хабарлари
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def handle_service_messages(message):
    safe_delete_message(message.chat.id, message.message_id)

# 2. Расм ва видеолар (3 талик қатъий назорат)
@bot.message_handler(content_types=['photo', 'video'])
def handle_media_control(message):
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == 'private':
        return

    if is_admin(chat_id, user_id):
        return

    now = time.time()
    user_mention = get_mention(message.from_user)

    # Альбом назорати:
    if message.media_group_id:
        mg_id = message.media_group_id
        _album_messages[mg_id].append((message.message_id, user_id))

        if len(_album_messages[mg_id]) > 3:
            for mid, _ in list(_album_messages[mg_id]):
                safe_delete_message(chat_id, mid)

            if len(_album_messages[mg_id]) == 4:
                mute_user_24h(chat_id, user_id, user_mention, reason="Альбомда 3 тадан ортиқ расм/видео")
            return

    # Кетма-кет 60 сонияда юбориш назорати:
    user_key = (chat_id, user_id)
    _user_media_history[user_key] = [
        (mid, ts) for mid, ts in _user_media_history[user_key] if now - ts < 60
    ]

    _user_media_history[user_key].append((message.message_id, now))
    media_count = len(_user_media_history[user_key])

    if media_count > 3:
        for mid, _ in _user_media_history[user_key]:
            safe_delete_message(chat_id, mid)

        mute_user_24h(chat_id, user_id, user_mention, reason="Кетма-кет 3 тадан ортиқ расм/видео юборилди")
        _user_media_history[user_key].clear()
        return

# 3. Бошқа барча медиа турлари (Тунги назорат)
@bot.message_handler(content_types=['voice', 'audio', 'document', 'sticker', 'animation', 'video_note', 'contact', 'location', 'poll'])
def handle_other_media(message):
    if check_night_mode_violation(message):
        return

# 4. Барча матнли хабарлар ва буйруқлар
@bot.message_handler(commands=['start', 'settings', 'menu', 'sozlamalar', 'help'])
def cmd_main_settings(message):
    user_id = message.from_user.id
    if message.chat.type != 'private' and not is_admin(message.chat.id, user_id):
        return

    text = build_main_menu_text()
    markup = build_main_menu_markup()
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(commands=['tungi', 'night', 'tungirejim'])
def cmd_night_shortcut(message):
    chat_id = message.chat.id
    if message.chat.type != 'private' and not is_admin(chat_id, message.from_user.id):
        return

    text = build_night_menu_text()
    markup = build_night_menu_markup()
    bot.send_message(chat_id, text, reply_markup=markup)

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

    # Anti-Flood (3 сонияда 5 та хабар)
    _user_msg_times[user_key] = [ts for ts in _user_msg_times[user_key] if now - ts < 3]
    _user_msg_times[user_key].append(now)
    if len(_user_msg_times[user_key]) > 5:
        safe_delete_message(chat_id, message.message_id)
        mute_user_24h(chat_id, user_id, get_mention(message.from_user), reason="Флуд (Тез-тез хабар ёзиш)")
        return

    # Реклама ва ҳаволалар
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

# ==================== АДМИН БУЙРУҚЛАРИ ====================
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
        msg = bot.send_message(chat_id, f"✅ {target_name} мутдан чиқарилди! Энди бемалол ёза олади.")
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

# ==================== CALLBACK QUERY ҲОДИСАЛАРИ ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id

    # 1. Пост реакциялари
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

    # Админ текшируви
    if user_id != OWNER_ID and not is_admin(chat_id, user_id):
        bot.answer_callback_query(call.id, "⛔️ Бу бўлим фақат бот эгаси ва админлар учун!", show_alert=True)
        return

    # 2. Асосий менюни очиш ёки янгилаш
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
        bot.answer_callback_query(call.id, "🔄 Асосий Меню янгиланди!")
        return

    # 3. Тунги режим бўлимини очиш (2-расм)
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
        bot.answer_callback_query(call.id, "🌙 Тунги Режим Созламалари")
        return

    # 4. Ҳолати (🟢 Ёқилган / 🔴 Ўчирилган) тугмаси босилганда
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

        alert_text = "🟢 Тунги режим муваффақиятли ЁҚИЛДИ!" if new_val == "1" else "🔴 Тунги режим ЎЧИРИЛДИ!"
        bot.answer_callback_query(call.id, alert_text, show_alert=True)
        return

    # 5. Бошланиш вақтини танлаш
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
                text="🔓 <b>Тунги режим бошланиш соатини танланг ёки босинг:</b>",
                reply_markup=markup
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)
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
        bot.answer_callback_query(call.id, f"✅ Бошланиш вақти: {val} қилиб созланди!", show_alert=True)
        return

    # 6. Тугаш вақтини танлаш
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
        bot.answer_callback_query(call.id)
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
        bot.answer_callback_query(call.id, f"✅ Тугаш вақти: {val} қилиб созланди!", show_alert=True)
        return

    # 7. Ҳозироқ синов эълонини юбориш (2-расмдагидек)
    if data == "send_night_test_now":
        test_text = get_night_warn_text()
        try:
            sent = bot.send_message(MAIN_GROUP, f"🧪 <b>[СИНОВ ЭЪЛОНИ]:</b>\n\n{test_text}")
            delete_later(MAIN_GROUP, sent.message_id, delay=30)
            bot.answer_callback_query(call.id, "✅ Синов эълони гуруҳга юборилди ва 30 сониядан сўнг автоматик ўчирилади!", show_alert=True)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Гуруҳга юборишда хатолик: {e}", show_alert=True)
        return

    # 8. Огоҳлантириш матнини ўзгартириш
    if data == "edit_night_warn_prompt":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Стандарт матнга қайтариш (Сброс)", callback_data="reset_night_warn"))
        markup.row(InlineKeyboardButton("◀️ Ортга (Тунги режим)", callback_data="open_night_menu"))
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="✏️ <b>Тунги режим огоҳлантириш матни:</b>\n\nМатнни ўзгартириш учун янги матнни ёзиб юборинг ёки стандарт матнга қайтариш тугмасини босинг:",
                reply_markup=markup
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)
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
        bot.answer_callback_query(call.id, "✅ Огоҳлантириш матни стандарт ҳолатга қайтарилди!", show_alert=True)
        return

    # 9. Бошқа бўлимлар
    if data == "info_media_limit":
        bot.answer_callback_query(call.id, "📸 3 тадан кўп расм/видео юборилса: барча расмлар ўчирилади ва 24 соатлик МУТ берилади!", show_alert=True)
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
        bot.answer_callback_query(call.id, "📊 Статистика янгиланди!")
        return

    bot.answer_callback_query(call.id, "✅ Қабул қилинди")

# ==================== ИШГА ТУШИРИШ ====================
def run_bot():
    logging.info("🐝 Asalarichilik Moderation Bot ishga tushmoqda...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            logging.error(f"Polling error: {e}. 5 soniyadan so'ng qayta ishga tushadi...")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
