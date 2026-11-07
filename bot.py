#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐝 Asalarichilik.Uz — Telegram Гуруҳ Назорат & Хавфсизлик Боти
Муаллиф ва Бот эгаси: @JamshidjonDavronov (ID: 2047501151)
Бот: @Asalarichilikuztv_bot

Асосий вазифалар:
1. 🌙 ТУНГИ РЕЖИМ (Night Mode):
   - Соат 23:00 дан 06:00 гача (Тошкент вақти билан UTC+5) гуруҳда хабар ёзиш чекланади.
   - Тунда ёзилган хабарлар автоматик ўчирилади ва огоҳлантириш берилади.
   - Админлар /tungi on, /tungi off ёки /tungi 22 07 буйруғи орқали бошқара олади.
2. 📸 КУЧАЙТИРИЛГАН МЕДИА НАЗОРАТ: 3 тадан ортиқ расм ёки видео юборилса:
   - Барча юборилган расм/видеолар бир зумда ўчирилади!
   - Фойдаланувчига 24 соатлик (1 кунлик) МУТ берилади.
3. 🚫 Спам ва бегона реклама ҳаволаларини дарҳол ўчириш.
4. 🧹 Кирди-чиқди (сервис) хабарларини тозалаш.
5. 👮‍♂️ Админ буйруқлари: /mut, /unmute, /warn, /del, /stat, /tungi.
6. 😊 Илова ва канал постларидаги смайлик реакциялари (👍 ❤️ 🔥 👏 🐝).
"""

import os
import sys
import time
import logging
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict

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
    # Тунги режимни бошланғич созлаш (default: ёқилган, 23:00 - 06:00)
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_mode', '1')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_start', '23')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('night_end', '6')")
    conn.commit()
    conn.close()

init_db()

# ==================== ТУНГИ РЕЖИМ СОЗЛАМАЛАРИ ====================
def get_setting(key, default=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else default
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

def is_night_mode_now():
    """Ҳозир тунги режим вақтими ёки йўқми текшириш (Тошкент вақти UTC+5 билан)"""
    enabled = get_setting("night_mode", "1") == "1"
    if not enabled:
        return False

    try:
        start_hour = int(get_setting("night_start", "23"))
        end_hour = int(get_setting("night_end", "6"))
    except ValueError:
        start_hour, end_hour = 23, 6

    now_dt = datetime.now(TASHKENT_TZ)
    current_hour = now_dt.hour

    if start_hour > end_hour:  # Масалан 23:00 дан 06:00 гача
        return current_hour >= start_hour or current_hour < end_hour
    else:
        return start_hour <= current_hour < end_hour

# ==================== КЭШ ВА ҲИМОЯ ====================
_user_media_history = defaultdict(list)
_album_messages = defaultdict(list)
_user_msg_times = defaultdict(list)
_admin_cache = {}
_night_warn_cache = {}  # (chat_id, user_id) -> last_warn_ts (тунги режимда спам бўлмаслиги учун)

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

def delete_later(chat_id, message_id, delay=45):
    def _worker():
        time.sleep(delay)
        safe_delete_message(chat_id, message_id)
    threading.Thread(target=_worker, daemon=True).start()

def mute_user_24h(chat_id, user_id, user_mention, reason="3 тадан ортиқ расм/видео юборилди"):
    """Фойдаланувчига 24 соатлик (1 кунлик) мут бериш"""
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

    # ДБга ёзиш
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
        delete_later(chat_id, sent.message_id, delay=50)
    except Exception:
        pass

def unmute_user_fully(chat_id, user_id):
    """Мутни олиб ташлаш"""
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

# ==================== ТУНГИ РЕЖИМДА ХАБАРНИ БЛОКЛАШ ====================
def check_night_mode_violation(message):
    """Тунги режимда хабар ёзилган бўлса, ўчириш ва огоҳлантириш бериш"""
    if message.chat.type == 'private':
        return False
    if is_admin(message.chat.id, message.from_user.id):
        return False

    if is_night_mode_now():
        safe_delete_message(message.chat.id, message.message_id)

        # 3 дақиқа ичида битта фойдаланувчига қайта-қайта хабар ёзиб спам қилмаслик
        now = time.time()
        user_key = (message.chat.id, message.from_user.id)
        last_warn = _night_warn_cache.get(user_key, 0)

        if now - last_warn > 180:
            _night_warn_cache[user_key] = now
            start_h = get_setting("night_start", "23")
            end_h = get_setting("night_end", "6")
            user_mention = get_mention(message.from_user)

            night_text = f"""
🌙 <b>ТУНГИ РЕЖИМ ФАОЛ!</b>
━━━━━━━━━━━━━━━━━━━━
👤 {user_mention}, гуруҳда соат <b>{start_h}:00 дан {end_h}:00 гача</b> (Тошкент вақти) тунги осойишталик режими амал қилмоқда.

Гуруҳ аъзоларининг тинчлигини бузмаслик мақсадида ҳозир хабар ёзиш вақтинча тўхтатилган.
Илтимос, эрталаб соат <b>{end_h}:00</b> дан кейин ёзинг! 🐝
""".strip()
            try:
                sent = bot.send_message(message.chat.id, night_text)
                delete_later(message.chat.id, sent.message_id, delay=35)
            except Exception:
                pass
        return True
    return False

# ==================== СЕРВИС ХАБАРЛАР (КИРДИ-ЧИҚДИ) ====================
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def handle_service_messages(message):
    safe_delete_message(message.chat.id, message.message_id)

    if message.content_type == 'new_chat_members':
        for member in message.new_chat_members:
            if member.is_bot:
                continue
            mention = get_mention(member)
            welcome_text = f"👋 Ассалому алайкум, {mention}! <b>Asalarichilik.Uz</b> гуруҳига хуш келибсиз!\n\n🐝 <i>Гуруҳда бир вақтда 3 тадан ортиқ расм/видео юбориш тақиқланади. Тунги режим: 23:00 дан 06:00 гача.</i>"
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("📢 Расмий Канал", url="https://t.me/Uz_Asalarichilik"),
                InlineKeyboardButton("👥 Қоидалар", url="https://t.me/Uz_Asalarichilik")
            )
            try:
                msg = bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
                delete_later(message.chat.id, msg.message_id, delay=60)
            except Exception:
                pass

# ==================== КУЧАЙТИРИЛГАН РАСМ ВА ВИДЕО НАЗОРАТИ ====================
@bot.message_handler(content_types=['photo', 'video'])
def handle_media_control(message):
    # 1. Аввал тунги режим текширилади:
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == 'private':
        bot.reply_to(message, "✅ Ҳурматли асаларичи, гуруҳ ёки каналга юбориш учун Asalarichilik иловасидан фойдаланинг.")
        return

    # Админлар ва бот эгасига чеклов йўқ
    if is_admin(chat_id, user_id):
        return

    now = time.time()
    user_mention = get_mention(message.from_user)

    # 1. АЛЬБОМ (Media Group) НАЗОРАТИ (Биттада 4, 5, 10 та расм/видео ташланса):
    if message.media_group_id:
        mg_id = message.media_group_id
        _album_messages[mg_id].append((message.message_id, user_id))

        if len(_album_messages[mg_id]) > 3:
            for mid, _ in list(_album_messages[mg_id]):
                safe_delete_message(chat_id, mid)

            if len(_album_messages[mg_id]) == 4:
                mute_user_24h(chat_id, user_id, user_mention, reason="Альбомда 3 тадан ортиқ расм/видео")
            return

    # 2. КЕТМА-КЕТ МЕДИА ЮБОРИШ НАЗОРАТИ (60 сония ичида):
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

# ==================== ОВОЗ, АУДИО, ФАЙЛ, СТИКЕР ТУНГИ НАЗОРАТИ ====================
@bot.message_handler(content_types=['voice', 'audio', 'document', 'sticker', 'animation'])
def handle_other_media(message):
    if check_night_mode_violation(message):
        return

# ==================== АНТИ-СПАМ ВА МАТН НАЗОРАТИ ====================
@bot.message_handler(func=lambda m: m.chat.type != 'private', content_types=['text'])
def handle_group_text(message):
    # Тунги режимни текшириш
    if check_night_mode_violation(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text or ""

    if is_admin(chat_id, user_id):
        return

    now = time.time()
    user_key = (chat_id, user_id)

    # 1. Anti-Flood (3 сония ичида 5 тадан кўп хабар)
    _user_msg_times[user_key] = [ts for ts in _user_msg_times[user_key] if now - ts < 3]
    _user_msg_times[user_key].append(now)
    if len(_user_msg_times[user_key]) > 5:
        safe_delete_message(chat_id, message.message_id)
        mute_user_24h(chat_id, user_id, get_mention(message.from_user), reason="Флуд (Тез-тез хабар ёзиш)")
        return

    # 2. Реклама ва линклар назорати
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

# ==================== ТУНГИ РЕЖИМ БУЙРУҚЛАРИ ====================
@bot.message_handler(commands=['tungi', 'night', 'tungirejim'])
def cmd_night_mode(message):
    chat_id = message.chat.id
    if message.chat.type != 'private' and not is_admin(chat_id, message.from_user.id):
        return

    parts = message.text.split()
    # /tungi on
    if len(parts) > 1 and parts[1].lower() in ["on", "yoq", "yoqish", "1", "start"]:
        set_setting("night_mode", "1")
        sh = get_setting("night_start", "23")
        eh = get_setting("night_end", "6")
        bot.reply_to(message, f"🌙 <b>Тунги режим ЁҚИЛДИ!</b>\n\n⏰ Вақти: соат <b>{sh}:00 дан {eh}:00 гача</b> (Тошкент вақти).\nУшбу вақт оралиғида оддий аъзолар хабар ёза олмайди.")
        return

    # /tungi off
    if len(parts) > 1 and parts[1].lower() in ["off", "ochir", "ochirish", "0", "stop"]:
        set_setting("night_mode", "0")
        bot.reply_to(message, "☀️ <b>Тунги режим ЎЧИРИЛДИ!</b>\nЭнди аъзолар 24 соат давомида эркин ёзишлари мумкин.")
        return

    # /tungi 22 07 (бошланиш ва тугаш соатини ўзгартириш)
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        sh, eh = int(parts[1]), int(parts[2])
        if 0 <= sh <= 23 and 0 <= eh <= 23:
            set_setting("night_start", str(sh))
            set_setting("night_end", str(eh))
            set_setting("night_mode", "1")
            bot.reply_to(message, f"✅ <b>Тунги режим вақти ўзгартирилди:</b>\n\n⏰ Янги вақт: <b>{sh}:00 дан {eh}:00 гача</b> (Тошкент вақти)")
            return

    # Ҳолатини кўрсатиш
    is_on = get_setting("night_mode", "1") == "1"
    sh = get_setting("night_start", "23")
    eh = get_setting("night_end", "6")
    now_dt = datetime.now(TASHKENT_TZ)
    current_time_str = now_dt.strftime("%H:%M")
    is_active_now = is_night_mode_now()

    status_icon = "🟢 ЁҚИЛГАН" if is_on else "🔴 ЎЧИРИЛГАН"
    active_now_text = "🌙 Ҳозир тунги режим ФАОЛ (ёзиш чекланган)" if is_active_now else "☀️ Ҳозир кундузги режим (ёзиш мумкин)"

    msg = f"""
🌙 <b>ТУНГИ РЕЖИМ БОШҚАРУВИ:</b>
━━━━━━━━━━━━━━━━━━━━
• Ҳолати: <b>{status_icon}</b>
• Вақти: <b>{sh}:00 дан {eh}:00 гача</b>
• Ҳозирги Тошкент вақти: <b>{current_time_str}</b>
• Жорий ҳолат: <b>{active_now_text}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Бошқариш буйруқлари:</b>
• <code>/tungi on</code> — Ёқиш
• <code>/tungi off</code> — Ўчириш
• <code>/tungi 22 7</code> — Вақтини 22:00 дан 07:00 гача ўзгартириш
""".strip()
    bot.reply_to(message, msg)

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
        msg = bot.send_message(chat_id, f"✅ {target_name} мутдан муваффақиятли чиқарилди! Энди бемалол ёза олади.")
        delete_later(chat_id, msg.message_id, delay=30)
    else:
        bot.reply_to(message, "Мутдан чиқариш учун фойдаланувчи хабарига reply қилиб /unmute деб ёзинг.")

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

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT deleted_media, muted_count, deleted_links FROM group_stats WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM muted_users WHERE chat_id = ? AND muted_until > ?", (chat_id, int(time.time())))
    active_mutes = cur.fetchone()[0]
    conn.close()

    m_count = row[1] if row else 0
    sh = get_setting("night_start", "23")
    eh = get_setting("night_end", "6")
    n_on = "Фаол 🟢" if get_setting("night_mode", "1") == "1" else "Ўчирилган 🔴"

    text = f"""
📊 <b>ГУРУҲ ҲИМОЯ ВА НАЗОРАТ СТАТИСТИКАСИ:</b>
━━━━━━━━━━━━━━━━━━━━
🌙 Тунги режим: <b>{n_on} ({sh}:00 - {eh}:00)</b>
🔇 Ҳозир фаол мутдагилар: <b>{active_mutes} та</b>
🛡 Жами мут берилганлар: <b>{m_count} марта</b>
📸 3 талик медиа лимит: <b>Фаол (24 соатлик мут)</b>
🔗 Реклама ва спам фильтри: <b>Фаол</b>
━━━━━━━━━━━━━━━━━━━━
<i>Бот фаол ишламоқда ва гуруҳ хавфсизлигини 100% таъминламоқда!</i>
""".strip()
    bot.reply_to(message, text)

# ==================== СМАЙЛИК РЕАКЦИЯЛАРИ ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
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

    if data == "toggle_night":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "Фақат эгаси учун!")
            return
        curr = get_setting("night_mode", "1")
        new_val = "0" if curr == "1" else "1"
        set_setting("night_mode", new_val)
        txt = "🌙 Тунги режим ЁҚИЛДИ" if new_val == "1" else "☀️ Тунги режим ЎЧИРИЛДИ"
        bot.answer_callback_query(call.id, txt, show_alert=True)
        return

    bot.answer_callback_query(call.id, "✅ Қабул қилинди")

# ==================== ШАХСИЙ ЧАТ /START (БОТ ЭГАСИ УЧУН) ====================
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    user_id = message.from_user.id
    if message.chat.type != 'private':
        return

    if user_id == OWNER_ID:
        sh = get_setting("night_start", "23")
        eh = get_setting("night_end", "6")
        n_status = "ЁҚИЛГАН 🟢" if get_setting("night_mode", "1") == "1" else "ЎЧИРИЛГАН 🔴"
        text = f"""
🐝 <b>Ассалому алайкум, Ҳурматли Жамшиджон! (@JamshidjonDavronov)</b>

Бот гуруҳни тўлиқ назорат қилмоқда:

🌙 <b>1. ТУНГИ РЕЖИМ ({n_status}):</b>
• Вақти: соат <b>{sh}:00 дан {eh}:00 гача</b> (Тошкент вақти)
• Тунда ёзилган хабарлар автоматик ўчирилади ва огоҳлантириш берилади.
• Бошқариш: <code>/tungi on</code> ёки <code>/tungi off</code> ёки <code>/tungi 22 7</code>

📸 <b>2. 3 ТАДАН ОРТИҚ РАСМ/ВИДЕО НАЗОРАТИ:</b>
• Биттада (альбом) ёки кетма-кет 3 тадан кўп расм/видео юборилса:
• Барча ташланган расмлар бир зумда ўчирилади!
• Фойдаланувчига автоматик <b>24 соатлик (1 кунлик) МУТ</b> берилади.

⚙️ <b>3. АДМИН БУЙРУҚЛАРИ (Гуруҳда):</b>
• <code>/unmute</code> — Мутдан чиқариш (хабарига reply қилиб)
• <code>/mut</code> — 24 соатга мут қилиш
• <code>/del</code> — Хабарни ўчириш
• <code>/stat</code> — Ҳимоя статистикасини кўриш
• <code>/tungi</code> — Тунги режимни кўриш ва созлаш
""".strip()
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🌙 Тунги режимни ёқиш/ўчириш", callback_data="toggle_night")
        )
        markup.row(
            InlineKeyboardButton("📢 Расмий Канал", url="https://t.me/Uz_Asalarichilik"),
            InlineKeyboardButton("👥 Расмий Гуруҳ", url="https://t.me/ASALARICHILIK_UZBEKISTAN")
        )
    else:
        text = """
🐝 <b>Asalarichilik.Uz Назорат Ботига хуш келибсиз!</b>

Бот @Asalarichilik_Uzbekistan гуруҳида хавфсизлик ва тозаликни таъминлайди:
• 🌙 Тунги режим: 23:00 дан 06:00 гача хабар ёзиш тақиқланади.
• 📸 3 тадан ортиқ расм/видео юборганларга 24 соатлик мут берилади.
• 🚫 Спам ва рекламалар тақиқланган.

📢 Расмий канал: @Uz_Asalarichilik
👥 Расмий гуруҳ: @Asalarichilik_Uzbekistan
""".strip()
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📢 Расмий Канал", url="https://t.me/Uz_Asalarichilik"),
            InlineKeyboardButton("👥 Расмий Гуруҳ", url="https://t.me/ASALARICHILIK_UZBEKISTAN")
        )
    bot.send_message(message.chat.id, text, reply_markup=markup)

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
