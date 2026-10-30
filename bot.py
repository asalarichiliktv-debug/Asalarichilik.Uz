# ========================================================
# 🐝 Asalarichilik.Uz🇺🇿 - Telegram Гуруҳ Бошқарув & Хавфсизлик Боти
# Муаллиф ва Бот эгаси: @JamshidjonDavronov
# Версия: 5.1 (Мукаммал Кўптиллик, Реклама-Рассылка, Ақлли Об-ҳаво ва Авто-тозалаш)
# ========================================================

import os
import sys
import re
import json
import time
import urllib.parse
import threading
from datetime import datetime, timedelta, timezone
import sqlite3
import logging
import html
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types, apihelper
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)


def get_full_chat_permissions():
    """Гуруҳда барча турдаги хабарлар (видео, расм, овоз, файллар) юборишга тўлиқ рухсат бериш"""
    return types.ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )


def lift_user_mute(chat_id, user_id):
    """Гуруҳда аъзодан мутни (ёзиш чекловини) 100% ишончли олиб ташлаш ва эркин ёзишга рухсат бериш"""
    # 1-усул: Telegram Bot API мустақил рухсатлари билан (use_independent_chat_permissions=True)
    try:
        bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            ),
            use_independent_chat_permissions=True
        )
        return True
    except Exception as e1:
        logging.warning(f"lift_user_mute method 1 failed: {e1}")

    # 2-усул: Стандарт ChatPermissions (use_independent_chat_permissions сиз)
    try:
        bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        return True
    except Exception as e2:
        logging.warning(f"lift_user_mute method 2 failed: {e2}")

    # 3-усул: Энг содда рухсат (фақат can_send_messages=True)
    try:
        bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=types.ChatPermissions(can_send_messages=True)
        )
        return True
    except Exception as e3:
        logging.warning(f"lift_user_mute method 3 failed: {e3}")

    # 4-усул: Гуруҳнинг ўз дефолт рухсатлари бўйича очиш
    try:
        c = bot.get_chat(chat_id)
        if hasattr(c, 'permissions') and c.permissions:
            bot.restrict_chat_member(chat_id, user_id, permissions=c.permissions)
            return True
    except Exception as e4:
        logging.error(f"lift_user_mute method 4 failed: {e4}")

    return False

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 1. Токен ва Эгаси маълумотлари
TOKEN = os.getenv("BOT_TOKEN", "8832904946:AAFCC2nob7serGzN4ZQ2GCbrLer-qVUjqjM")
OWNER_ID = int(os.getenv("ADMIN_ID", "2047501151"))  # Бот асосий эгаси ID рақами
OWNER_USERNAME = "@JamshidjonDavronov"
BOT_USERNAME = "Asalarichiliktv_bot"
BOT_NAME = "Asalarichilik.Uz"

# API Timeouts
apihelper.CONNECT_TIMEOUT = 15
apihelper.READ_TIMEOUT = 15

def configure_network():
    """
    PythonAnywhere ва бошқа хостингларда Telegram Bot API га энг мукаммал уланишни
    автоматик танлайди (Direct, US proxy, EU proxy ёки Env proxy).
    """
    import urllib.request
    candidates = []
    
    # 1. Агар тизим муҳитида (os.environ) тайёр прокси бўлса
    env_p = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("https_proxy") or os.getenv("http_proxy")
    if env_p:
        candidates.append(("Тизим (Env) проксиси", env_p))
        
    # 2. PythonAnywhere US ва EU проксилари
    candidates.append(("PythonAnywhere US прокси", "http://proxy.server:3128"))
    candidates.append(("PythonAnywhere EU прокси", "http://proxy.eu.pythonanywhere.com:3128"))
    
    # 3. Тўғридан-тўғри интернет (Direct)
    candidates.append(("Тўғридан-тўғри интернет (Direct)", None))
    
    is_pa = (
        "PYTHONANYWHERE_DOMAIN" in os.environ or
        "pythonanywhere" in os.path.expanduser("~").lower()
    )
    if not is_pa:
        # Агар PythonAnywhere бўлмаса, Direct уланиш биринчи навбатда текширилади
        candidates.insert(0, ("Тўғридан-тўғри интернет (Direct)", None))

    api_url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    
    for label, p_addr in candidates:
        try:
            if p_addr:
                handler = urllib.request.ProxyHandler({'http': p_addr, 'https': p_addr})
                opener = urllib.request.build_opener(handler)
            else:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                
            req = urllib.request.Request(api_url, headers={'User-Agent': 'TeleBot/5.0'})
            with opener.open(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get("ok"):
                        if p_addr:
                            apihelper.proxy = {'http': p_addr, 'https': p_addr}
                            logging.info(f"🌐 {label} орқали муваффақиятли уланди: {p_addr}")
                        else:
                            apihelper.proxy = None
                            logging.info("🌐 Тўғридан-тўғри интернет (Direct) орқали уланди.")
                        return True
        except Exception as e:
            logging.debug(f"{label} текширилди: {e}")
            continue

    if is_pa:
        logging.warning("⚠️ Барча проксилар вақтинчалик банд (503). Стандарт PythonAnywhere проксиси фаоллаштирилди, бот автоматик уланишни давом эттиради.")
        apihelper.proxy = {'http': 'http://proxy.server:3128', 'https': 'http://proxy.server:3128'}
    else:
        apihelper.proxy = None
    return False

# Ишга туширишда тармоқни текшириш
configure_network()

bot = TeleBot(TOKEN, parse_mode="HTML", num_threads=8)

# Фойдаланувчиларнинг маълумот киритиш ҳолатлари (State tracking)
USER_STATES = {}

def setup_bot_commands():
    try:
        # 1. Гуруҳлардан барча / буйруқларини бутунлай тозалаш (Группаларда / босилганда ҳеч қандай меню чиқмайди)
        bot.delete_my_commands(scope=types.BotCommandScopeAllGroupChats())
        bot.delete_my_commands(scope=types.BotCommandScopeAllChatAdministrators())
        bot.delete_my_commands(scope=types.BotCommandScopeDefault())
        bot.set_my_commands([], scope=types.BotCommandScopeAllGroupChats())
        bot.set_my_commands([], scope=types.BotCommandScopeAllChatAdministrators())
        bot.set_my_commands([], scope=types.BotCommandScopeDefault())

        # 2. Фақат личка учун /start буйруғи
        bot.set_my_commands([
            types.BotCommand("start", "🏠 Асосий меню")
        ], scope=types.BotCommandScopeAllPrivateChats())
    except Exception as e:
        logging.warning(f"Командаларни созлашда огоҳлантириш: {e}")

# 2. SQLite Маълумотлар Базаси
class RowDict(dict):
    def __init__(self, items, cols):
        super().__init__(items)
        self._cols = cols

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._cols[key])
        return super().__getitem__(key)

def row_dict_factory(cursor, row):
    cols = [col[0] for col in cursor.description]
    items = {cols[i]: row[i] for i in range(len(cols))}
    return RowDict(items, cols)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CANONICAL_DB_PATH = os.path.join(BASE_DIR, "asalarichilik.db")
SETTINGS_BACKUP_PATH = os.path.join(BASE_DIR, "asalarichilik_settings_backup.json")

# Мустаҳкам база йўли: қаердан ишга туширилмасин (~, консоль, Always-On, cron) доим ягона базага уланади
candidate_db_locations = [
    CANONICAL_DB_PATH,
    os.path.abspath("asalarichilik.db"),
    os.path.join(os.path.expanduser("~"), "asalarichilik.db"),
    "/home/JamshidjonDavronov/asalarichilik.db",
    "/home/JamshidjonDavronov/AsalarichilikBot/asalarichilik.db"
]

best_db_path = CANONICAL_DB_PATH
best_db_size = -1

for loc in candidate_db_locations:
    try:
        if os.path.exists(loc) and os.path.isfile(loc):
            sz = os.path.getsize(loc)
            if sz > best_db_size:
                best_db_size = sz
                best_db_path = loc
    except Exception:
        pass

if best_db_path != CANONICAL_DB_PATH and os.path.exists(best_db_path) and best_db_size > 0:
    try:
        import shutil
        if not os.path.exists(CANONICAL_DB_PATH) or os.path.getsize(CANONICAL_DB_PATH) < best_db_size:
            shutil.copy2(best_db_path, CANONICAL_DB_PATH)
            logging.info(f"🔄 Маълумотлар базаси {best_db_path} дан {CANONICAL_DB_PATH} га кўчирилди!")
    except Exception as me:
        logging.warning(f"DB migration notice: {me}")

DB_PATH = CANONICAL_DB_PATH
_raw_conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
_raw_conn.execute("PRAGMA journal_mode=WAL;")
_raw_conn.execute("PRAGMA busy_timeout=15000;")
_raw_conn.row_factory = row_dict_factory

_db_local = threading.local()
_db_lock = threading.RLock()

class ThreadLocalCursor:
    """Кўп оқимли (multithreaded) муҳитда SQLite курсорларини хавфсиз бошқарувчи прокси"""
    def _cur(self):
        if not hasattr(_db_local, "cursor") or _db_local.cursor is None:
            _db_local.cursor = _raw_conn.cursor()
        return _db_local.cursor

    def execute(self, *args, **kwargs):
        with _db_lock:
            return self._cur().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        with _db_lock:
            return self._cur().executemany(*args, **kwargs)

    def fetchone(self):
        with _db_lock:
            return self._cur().fetchone()

    def fetchall(self):
        with _db_lock:
            return self._cur().fetchall()

    def fetchmany(self, *args, **kwargs):
        with _db_lock:
            return self._cur().fetchmany(*args, **kwargs)

    @property
    def lastrowid(self):
        with _db_lock:
            return self._cur().lastrowid

    @property
    def rowcount(self):
        with _db_lock:
            return self._cur().rowcount

    @property
    def description(self):
        with _db_lock:
            return self._cur().description

    def __iter__(self):
        with _db_lock:
            return iter(self._cur().fetchall())

    def __getattr__(self, name):
        with _db_lock:
            return getattr(self._cur(), name)

class ThreadSafeConn:
    """Кўп оқимли тизимда SQLite уланишини хавфсиз сақловчи прокси"""
    def commit(self):
        with _db_lock:
            return _raw_conn.commit()

    def rollback(self):
        with _db_lock:
            return _raw_conn.rollback()

    def cursor(self):
        return ThreadLocalCursor()

    def execute(self, *args, **kwargs):
        with _db_lock:
            return _raw_conn.execute(*args, **kwargs)

    def __getattr__(self, name):
        with _db_lock:
            return getattr(_raw_conn, name)

conn = ThreadSafeConn()
cursor = ThreadLocalCursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    language TEXT DEFAULT 'uz_kr'
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS groups (
    chat_id INTEGER PRIMARY KEY,
    title TEXT,
    added_by INTEGER DEFAULT 0,
    is_authorized INTEGER DEFAULT 0,
    lang TEXT DEFAULT 'uz_kr',
    lock_links INTEGER DEFAULT 1,
    lock_forwards INTEGER DEFAULT 1,
    lock_spam INTEGER DEFAULT 1,
    clean_joins INTEGER DEFAULT 1,
    lock_badwords INTEGER DEFAULT 1,
    lock_stickers INTEGER DEFAULT 0,
    lock_arabic INTEGER DEFAULT 1,
    lock_media INTEGER DEFAULT 0,
    lock_files INTEGER DEFAULT 0,
    lock_voice INTEGER DEFAULT 0,
    autolock_enabled INTEGER DEFAULT 0,
    welcome_enabled INTEGER DEFAULT 1,
    forcesub_enabled INTEGER DEFAULT 0,
    forcesub_channel TEXT DEFAULT '@uz_asalarichilik',
    forcesub_only_new INTEGER DEFAULT 1,
    forcesub_action TEXT DEFAULT 'kick',
    forcesub_timer_min INTEGER DEFAULT 0,
    approval_enabled INTEGER DEFAULT 0,
    limit_enabled INTEGER DEFAULT 1,
    limit_max INTEGER DEFAULT 3,
    limit_photos INTEGER DEFAULT 1,
    limit_videos INTEGER DEFAULT 1,
    limit_hours INTEGER DEFAULT 24,
    limit_notice_del INTEGER DEFAULT 2,
    autolock_start_time TEXT DEFAULT '23:00',
    autolock_end_time TEXT DEFAULT '06:30',
    autolock_delete_media INTEGER DEFAULT 1,
    autolock_msg_delete_minutes INTEGER DEFAULT 60,
    autolock_prewarn_msg TEXT DEFAULT '',
    autolock_start_msg TEXT DEFAULT '',
    autolock_end_msg TEXT DEFAULT '',
    timezone_offset INTEGER DEFAULT 5,
    timezone_city TEXT DEFAULT 'Тошкент (UTC+5)',
    weather_enabled INTEGER DEFAULT 1,
    weather_city TEXT DEFAULT 'Тошкент',
    weather_time TEXT DEFAULT '08:00',
    weather_forecast_type TEXT DEFAULT '10_days',
    weather_schedule TEXT DEFAULT 'daily',
    weather_repeat_days TEXT DEFAULT '1,2,3,4,5,6,7',
    weather_delete_hours INTEGER DEFAULT 2,
    weather_delete_minutes INTEGER DEFAULT 0,
    weather_delete_min INTEGER DEFAULT 120,
    forcesub_delete_sec INTEGER DEFAULT 30,
    rules_text TEXT DEFAULT ''
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS channels (
    chat_id INTEGER PRIMARY KEY,
    title TEXT,
    username TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS controller_posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER DEFAULT 0,
    target_name TEXT DEFAULT '',
    message_text TEXT DEFAULT '',
    media_type TEXT DEFAULT 'text',
    media_file_id TEXT DEFAULT '',
    reactions_json TEXT DEFAULT '[]',
    url_buttons_json TEXT DEFAULT '[]',
    has_comments INTEGER DEFAULT 0,
    native_comments INTEGER DEFAULT 0,
    is_silent INTEGER DEFAULT 0,
    delete_timer_hours INTEGER DEFAULT 0,
    scheduled_time TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    sent_chat_id INTEGER DEFAULT 0,
    sent_message_id INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS auto_delete_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    message_id INTEGER,
    delete_at TIMESTAMP
)''')

try:
    cursor.execute("ALTER TABLE controller_posts ADD COLUMN comments_url TEXT DEFAULT ''")
    conn.commit()
except Exception:
    pass

cursor.execute('''
CREATE TABLE IF NOT EXISTS post_comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    user_id INTEGER,
    full_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    comment_text TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()

# Дефолт каналларни базага текшириб қўшиш
try:
    cursor.execute(
        "INSERT OR IGNORE INTO channels (chat_id, title, username) VALUES (?, ?, ?)",
        (-1002035122486, "Asalarilar", "@asalarichilik")
    )
    cursor.execute(
        "INSERT OR IGNORE INTO channels (chat_id, title, username) VALUES (?, ?, ?)",
        (-1001849204910, "🍯🐝Asalarichilik.Uz🇺🇿 Kanali: 💎🍯🐝", "@Uz_Asalarichilik")
    )
    conn.commit()
except Exception:
    pass

cursor.execute('''
CREATE TABLE IF NOT EXISTS broadcast_posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_text TEXT,
    media_type TEXT,
    media_file_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS feed_reactions (
    content_type TEXT,
    content_id TEXT,
    user_id INTEGER,
    emoji TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(content_type, content_id, user_id)
)''')
conn.commit()

cursor.execute('''
CREATE TABLE IF NOT EXISTS post_reactions (
    post_id INTEGER,
    chat_id INTEGER,
    user_id INTEGER,
    emoji TEXT,
    PRIMARY KEY(post_id, chat_id, user_id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_bee_ad_limits (
    chat_id INTEGER,
    user_id INTEGER,
    count INTEGER DEFAULT 0,
    ad_date TEXT,
    warn_count INTEGER DEFAULT 0,
    last_warn_ts INTEGER DEFAULT 0,
    PRIMARY KEY(chat_id, user_id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_media_limits (
    chat_id INTEGER,
    user_id INTEGER,
    count INTEGER DEFAULT 0,
    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(chat_id, user_id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS new_members (
    chat_id INTEGER,
    user_id INTEGER,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(chat_id, user_id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS forcesub_verified (
    chat_id INTEGER,
    user_id INTEGER,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(chat_id, user_id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS global_quiz_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER DEFAULT 1,
    send_time TEXT DEFAULT '10:00',
    repeat_days TEXT DEFAULT '1,2,3,4,5,6,7',
    delete_hours INTEGER DEFAULT 0,
    auto_pin INTEGER DEFAULT 1,
    target_scope TEXT DEFAULT 'both',
    category_filter TEXT DEFAULT 'all',
    last_sent_date TEXT DEFAULT '',
    current_index INTEGER DEFAULT 0
)''')
cursor.execute("INSERT OR IGNORE INTO global_quiz_config (id, enabled, send_time, repeat_days, delete_hours, auto_pin, target_scope, category_filter, last_sent_date, current_index) VALUES (1, 1, '10:00', '1,2,3,4,5,6,7', 0, 1, 'both', 'all', '', 0)")
conn.commit()

cursor.execute('''
CREATE TABLE IF NOT EXISTS custom_bee_quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_kr TEXT,
    question_lat TEXT,
    question_ru TEXT,
    options_json TEXT,
    correct_id INTEGER DEFAULT 0,
    explanation_kr TEXT,
    explanation_lat TEXT,
    explanation_ru TEXT,
    category TEXT DEFAULT 'junior',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()

cursor.execute('''
CREATE TABLE IF NOT EXISTS whitelist (
    chat_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(chat_id, user_id)
)''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS blacklist (
    chat_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(chat_id, user_id)
)''')

# Auto-migration for new columns
try:
    cursor.execute("PRAGMA table_info(groups)")
    cols = [r[1] for r in cursor.fetchall()]
    new_cols = {
        "lang": "TEXT DEFAULT 'uz_kr'",
        "is_authorized": "INTEGER DEFAULT 1",
        "forcesub_enabled": "INTEGER DEFAULT 0",
        "forcesub_channel": "TEXT DEFAULT '@asalarichilik'",
        "forcesub_only_new": "INTEGER DEFAULT 1",
        "forcesub_action": "TEXT DEFAULT 'kick'",
        "forcesub_timer_min": "INTEGER DEFAULT 0",
        "approval_enabled": "INTEGER DEFAULT 0",
        "limit_enabled": "INTEGER DEFAULT 1",
        "limit_max": "INTEGER DEFAULT 3",
        "limit_photos": "INTEGER DEFAULT 1",
        "limit_videos": "INTEGER DEFAULT 1",
        "limit_hours": "INTEGER DEFAULT 24",
        "limit_notice_del": "INTEGER DEFAULT 60",
        "limit_warn_msg": "TEXT DEFAULT ''",
        "limit_repeat_mute": "INTEGER DEFAULT 1",
        "lock_links": "INTEGER DEFAULT 1",
        "lock_forwards": "INTEGER DEFAULT 1",
        "lock_spam": "INTEGER DEFAULT 1",
        "clean_joins": "INTEGER DEFAULT 1",
        "lock_badwords": "INTEGER DEFAULT 1",
        "lock_stickers": "INTEGER DEFAULT 0",
        "lock_arabic": "INTEGER DEFAULT 1",
        "lock_media": "INTEGER DEFAULT 0",
        "lock_files": "INTEGER DEFAULT 0",
        "lock_voice": "INTEGER DEFAULT 0",
        "autolock_enabled": "INTEGER DEFAULT 0",
        "welcome_enabled": "INTEGER DEFAULT 1",
        "autolock_start_time": "TEXT DEFAULT '23:00'",
        "autolock_end_time": "TEXT DEFAULT '06:30'",
        "autolock_delete_media": "INTEGER DEFAULT 1",
        "autolock_msg_delete_minutes": "INTEGER DEFAULT 60",
        "autolock_prewarn_msg": "TEXT DEFAULT ''",
        "autolock_start_msg": "TEXT DEFAULT ''",
        "autolock_end_msg": "TEXT DEFAULT ''",
        "timezone_offset": "INTEGER DEFAULT 5",
        "timezone_city": "TEXT DEFAULT 'Тошкент (UTC+5)'",
        "weather_enabled": "INTEGER DEFAULT 1",
        "weather_city": "TEXT DEFAULT 'Тошкент'",
        "weather_time": "TEXT DEFAULT '08:00'",
        "weather_delete_hours": "INTEGER DEFAULT 2",
        "weather_delete_minutes": "INTEGER DEFAULT 0"
    }
    for col_name, col_def in new_cols.items():
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE groups ADD COLUMN {col_name} {col_def}")
    # Normalize channel names to @uz_asalarichilik
    cursor.execute("UPDATE groups SET forcesub_channel = '@uz_asalarichilik' WHERE forcesub_channel LIKE '%asalarichilik%' OR forcesub_channel IS NULL OR forcesub_channel = ''")
    conn.commit()
except Exception as e:
    logging.error(f"Migration error: {e}")

# Bot System Settings Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS bot_system_settings (
    key TEXT PRIMARY KEY,
    value TEXT
)''')

default_sys_settings = {
    "official_channel": "@uz_asalarichilik",
    "official_group": "@asalarichilik_uzbekistan",
    "youtube_url": "https://youtube.com/@asalarichilikuztv?feature=shared",
    "news_script": "uz_kr",
    "quiz_script": "uz_kr"
}
for sk, sv in default_sys_settings.items():
    cursor.execute("INSERT OR IGNORE INTO bot_system_settings (key, value) VALUES (?, ?)", (sk, sv))
conn.commit()

try:
    cursor.execute("PRAGMA table_info(global_quiz_config)")
    q_cols = [r[1] for r in cursor.fetchall()]
    if "script" not in q_cols:
        cursor.execute("ALTER TABLE global_quiz_config ADD COLUMN script TEXT DEFAULT 'uz_kr'")
    conn.commit()
except Exception as e:
    logging.error(f"global_quiz_config migration error: {e}")


try:
    cursor.execute("PRAGMA table_info(user_bee_ad_limits)")
    u_cols = [r[1] for r in cursor.fetchall()]
    if "warn_count" not in u_cols:
        cursor.execute("ALTER TABLE user_bee_ad_limits ADD COLUMN warn_count INTEGER DEFAULT 0")
    if "last_warn_ts" not in u_cols:
        cursor.execute("ALTER TABLE user_bee_ad_limits ADD COLUMN last_warn_ts INTEGER DEFAULT 0")
    conn.commit()
except Exception as e:
    logging.error(f"user_bee_ad_limits migration error: {e}")

try:
    cursor.execute("PRAGMA table_info(groups)")
    g_cols = [r[1] for r in cursor.fetchall()]
    if "limit_warn_msg" not in g_cols:
        cursor.execute("ALTER TABLE groups ADD COLUMN limit_warn_msg TEXT DEFAULT ''")
    if "limit_repeat_mute" not in g_cols:
        cursor.execute("ALTER TABLE groups ADD COLUMN limit_repeat_mute INTEGER DEFAULT 1")
    conn.commit()
except Exception as e:
    logging.error(f"groups extra migration error: {e}")

# ==================== ЗАХИРА ВА ДОИМИЙЛИК (BACKUP & PERSISTENCE) ====================
def backup_settings_to_file():
    """Гуруҳлар ва каналлар созламаларини JSON захира файлига сақлайди"""
    try:
        with _db_lock:
            cur = _raw_conn.cursor()
            cur.execute("SELECT * FROM groups")
            groups_data = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM channels")
            channels_data = [dict(r) for r in cur.fetchall()]
            data = {
                "groups": groups_data,
                "channels": channels_data,
                "saved_at": time.time()
            }
            with open(SETTINGS_BACKUP_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as be:
        logging.warning(f"Backup settings notice: {be}")

def restore_settings_from_backup():
    """База бўшаб қолса ёки қайта ишга тушганда JSON захира файлидан тиклайди"""
    if not os.path.exists(SETTINGS_BACKUP_PATH):
        return
    try:
        with open(SETTINGS_BACKUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups_data = data.get("groups", [])
        channels_data = data.get("channels", [])
        with _db_lock:
            cur = _raw_conn.cursor()
            for g in groups_data:
                cols = [k for k in g.keys() if k != "rowid"]
                vals = [g[k] for k in cols]
                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join(cols)
                cur.execute(f"INSERT OR REPLACE INTO groups ({col_names}) VALUES ({placeholders})", vals)
            for c in channels_data:
                cur.execute(
                    "INSERT OR REPLACE INTO channels (chat_id, title, username) VALUES (?, ?, ?)",
                    (c.get("chat_id"), c.get("title"), c.get("username"))
                )
            _raw_conn.commit()
            logging.info("✅ Гуруҳ созламалари JSON захира файлидан муваффақиятли тикланди!")
    except Exception as re:
        logging.warning(f"Restore settings notice: {re}")

def ensure_main_group_seeded():
    """
    Асосий гуруҳ (-1001275726275) ва канал (-1001849204910) базада ҳар доим сақланишини кафолатлайди.
    Бот ҳар қандай вазиятда тўхтаб қолса ҳам созламалар ва гуруҳ йўқолмайди!
    """
    MAIN_GROUP_ID = -1001275726275
    MAIN_GROUP_TITLE = "🐝 Asalarichilik.Uz (Асосий гуруҳ)"
    MAIN_CHANNEL_ID = -1001849204910
    MAIN_CHANNEL_TITLE = "🍯🐝Asalarichilik.Uz🇺🇿 Kanali: 💎🍯🐝"
    MAIN_CHANNEL_USER = "@Uz_Asalarichilik"

    try:
        restore_settings_from_backup()
        with _db_lock:
            cur = _raw_conn.cursor()
            cur.execute("SELECT chat_id, title, is_authorized FROM groups WHERE chat_id = ?", (MAIN_GROUP_ID,))
            g_row = cur.fetchone()
            if not g_row:
                cur.execute('''
                    INSERT INTO groups (
                        chat_id, title, added_by, is_authorized, lang,
                        lock_links, lock_forwards, lock_spam, clean_joins, lock_badwords,
                        lock_stickers, lock_arabic, lock_media, lock_files, lock_voice,
                        autolock_enabled, welcome_enabled, forcesub_enabled, approval_enabled,
                        limit_enabled, limit_max, limit_photos, limit_videos, limit_hours, limit_notice_del,
                        autolock_start_time, autolock_end_time, autolock_delete_media, autolock_msg_delete_minutes,
                        timezone_offset, timezone_city, weather_enabled, weather_city, weather_time, weather_forecast_type
                    ) VALUES (
                        ?, ?, ?, 1, 'uz_kr',
                        1, 1, 1, 1, 1,
                        0, 1, 0, 0, 0,
                        0, 1, 0, 0,
                        1, 3, 1, 1, 24, 2,
                        '23:00', '06:30', 1, 60,
                        5, 'Тошкент (UTC+5)', 1, 'Тошкент', '08:00', '10_days'
                    )
                ''', (MAIN_GROUP_ID, MAIN_GROUP_TITLE, OWNER_ID))
                _raw_conn.commit()
                logging.info(f"✅ Асосий гуруҳ {MAIN_GROUP_TITLE} ({MAIN_GROUP_ID}) базага тикланди ва созланди!")
            else:
                if not g_row.get("is_authorized"):
                    cur.execute("UPDATE groups SET is_authorized = 1 WHERE chat_id = ?", (MAIN_GROUP_ID,))
                    _raw_conn.commit()

            cur.execute("SELECT chat_id FROM channels WHERE chat_id = ?", (MAIN_CHANNEL_ID,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO channels (chat_id, title, username) VALUES (?, ?, ?)",
                    (MAIN_CHANNEL_ID, MAIN_CHANNEL_TITLE, MAIN_CHANNEL_USER)
                )
                _raw_conn.commit()
        backup_settings_to_file()
    except Exception as e:
        logging.warning(f"ensure_main_group_seeded notice: {e}")

# Ишга тушганда дарҳол асосий гуруҳ ва канални тиклаб қўйиш
ensure_main_group_seeded()

# 3. Ёрдамчи Функциялар
def delete_msg_safe(chat_id, msg_id):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def safe_edit_or_send(chat_id, message_id, text, markup=None):
    if message_id:
        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup,
                disable_web_page_preview=True
            )
            return
        except Exception:
            pass
    try:
        bot.send_message(
            chat_id,
            text,
            reply_markup=markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"safe_edit_or_send error: {e}")

def register_group(chat_id, title, added_by=0):
    cursor.execute("SELECT chat_id FROM groups WHERE chat_id = ?", (chat_id,))
    if not cursor.fetchone():
        auth = 1 if (added_by == OWNER_ID or chat_id == -1001275726275) else 0
        cursor.execute(
            "INSERT INTO groups (chat_id, title, added_by, is_authorized) VALUES (?, ?, ?, ?)",
            (chat_id, title, added_by, auth)
        )
        conn.commit()
    else:
        cursor.execute("UPDATE groups SET title = ? WHERE chat_id = ?", (title, chat_id))
        conn.commit()
    backup_settings_to_file()

def register_channel(chat_id, title, username=None):
    cursor.execute(
        "INSERT OR REPLACE INTO channels (chat_id, title, username) VALUES (?, ?, ?)",
        (chat_id, title, username)
    )
    conn.commit()
    backup_settings_to_file()

def get_group(group_id):
    cursor.execute("SELECT * FROM groups WHERE chat_id = ?", (group_id,))
    row = cursor.fetchone()
    if not row and int(group_id) == -1001275726275:
        ensure_main_group_seeded()
        cursor.execute("SELECT * FROM groups WHERE chat_id = ?", (group_id,))
        row = cursor.fetchone()
    return row

def is_admin(chat_id, user_id):
    # Telegram хизмат ҳисоблари ва бот эгаси
    if user_id == OWNER_ID:
        return True
    if user_id in [777000, 1087968824]:
        return True
    if user_id <= 0:
        return False
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['creator', 'administrator']
    except Exception:
        return False

def check_bot_admin_status(group_id):
    try:
        m = bot.get_chat_member(group_id, bot.get_me().id)
        return m.status in ['creator', 'administrator']
    except Exception:
        return False

def get_system_setting(key, default=""):
    try:
        cursor.execute("SELECT value FROM bot_system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row and row["value"]:
            return row["value"]
    except Exception:
        pass
    return default

def set_system_setting(key, value):
    try:
        cursor.execute("INSERT OR REPLACE INTO bot_system_settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    except Exception as e:
        logging.error(f"Error saving system setting {key}: {e}")

def get_official_channel():
    return clean_channel_username(get_system_setting("official_channel", "@uz_asalarichilik"))

def get_official_group():
    return get_system_setting("official_group", "@asalarichilik_uzbekistan")

def get_official_youtube():
    return get_system_setting("youtube_url", "https://youtube.com/@asalarichilikuztv?feature=shared")

def clean_channel_username(chan_str):
    if not chan_str:
        return get_system_setting("official_channel", "@uz_asalarichilik")
    s = str(chan_str).strip()
    s = re.sub(r'https?://t\.me/', '', s)
    s = re.sub(r'^t\.me/', '', s)
    s = s.strip('/ \t\n\r')
    if not s.startswith('@') and not s.startswith('-100') and not s.isdigit():
        s = f"@{s}"
    if s.lower() in ['@asalarichilik', 'asalarichilik', '@asalarichilik_uz', 'asalarichilik_uz']:
        return "@uz_asalarichilik"
    return s

def check_bot_channel_admin(channel):
    """Каналда бот администратор эканлигини текшириш"""
    try:
        clean_c = clean_channel_username(channel)
        m = bot.get_chat_member(clean_c, bot.get_me().id)
        return m.status in ['creator', 'administrator']
    except Exception as e:
        logging.warning(f"check_bot_channel_admin error for {channel}: {e}")
        return False

def check_bot_group_admin(group_id):
    """Гуруҳда бот администратор эканлигини текшириш"""
    return check_bot_admin_status(group_id)

def check_user_channels_subscription(channels_str, user_id):
    """
    Текшириш: фойдаланувчи барча кўрсатилган каналларга аъзоми?
    Қайтаради: (is_all_sub, missing_channels_list)
    """
    if not channels_str:
        return True, []
    
    raw_list = [c.strip() for c in re.split(r'[,;\s]+', str(channels_str)) if c.strip()]
    if not raw_list:
        return True, []
        
    missing = []
    for raw_c in raw_list:
        clean_c = clean_channel_username(raw_c)
        try:
            cm = bot.get_chat_member(clean_c, user_id)
            if cm.status not in ['creator', 'administrator', 'member', 'restricted']:
                missing.append(clean_c)
        except Exception as e:
            logging.warning(f"get_chat_member error for channel {clean_c}, user {user_id}: {e}")
            missing.append(clean_c)
            
    return (len(missing) == 0), missing

def is_group_authorized(chat_id):
    return True

def is_user_allowed_to_manage_group(group_id, user_id):
    """Гуруҳни созлаш ва қулфларни бошқаришга рухсати борлигини текшириш"""
    if user_id == OWNER_ID:
        return True
    try:
        return is_admin(group_id, user_id)
    except Exception:
        return False

def is_user_admin_anywhere(user_id):
    """Фойдаланувчи бот эгаси ёки бирорта гуруҳ админи эканлигини текшириш"""
    if user_id == OWNER_ID:
        return True
    try:
        cursor.execute("SELECT chat_id FROM groups")
        rows = cursor.fetchall()
        for r in rows:
            gid = r["chat_id"]
            if is_admin(gid, user_id):
                return True
    except Exception:
        pass
    return False

def get_user_lang(user_id):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row["language"]:
        return row["language"]
    return "uz_kr"

# Вақт ва санани ҳисоблаш (UTC+Offset)
def get_now(offset_hours=5):
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    return utc_now + timedelta(hours=offset_hours)

def get_now_formatted(offset_hours=5):
    dt = get_now(offset_hours)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

UZ_MONTHS = ["январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]
UZ_MONTHS_LAT = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# 4. Профессионал Саломлашув матнлари (Огоҳлантириш билан!)
WELCOME_UZ_KR = """Салом, {first_name} 🙋‍♂️

🔰 Telegramнинг энг зўр воситаси билан танишинг.
🔰 Кучли гуруҳ бошқарувчиси.
🔰 Назорат учун энг яхши бот.

Асосий хусусиятлар:
✅ Тез буйруқ жавоблари
✅ Катта гуруҳларда силлиқ ишлаш
✅ Узилишсиз ва доимий онлайн
✅ Гуруҳ хавфсизлиги ва ҳимояси:
✅ Спамдан ҳимоя
✅ Сўз ва ибораларни илғор фильтрлаш
✅ Фойдаланувчи киришини аниқ бошқариш
✅ Расм ва видео лимитлари (Бир кунда 3 тадан кўп юборса 4-чисида 1 кунлик МУТЕ!)
✅ Илғор қулфлаш ва чеклаш тизими
✅ 1, 3 ва 10 кунлик аниқ об-ҳаво маълумотлари

👑 <b>Бот эгаси:</b> @JamshidjonDavronov

⚠️ <b>МУҲИМ ЭСЛАТМА:</b>
Агар ботни ўз гуруҳингизга қўшмоқчи бўлсангиз, аввал бот эгаси @JamshidjonDavronov билан боғланинг ва унинг розилигини олиб, сўнгра ботни гуруҳингизга админ қилиб фойдаланинг! (Эгаси розилигисиз бот бегона гуруҳларда ишламайди).

— 🛡 Asalarichilik.Uz🇺🇿 —"""

WELCOME_UZ_LAT = """Salom, {first_name} 🙋‍♂️

🔰 Telegramning eng zo'r vositasi bilan tanishing.
🔰 Kuchli guruh boshqaruvchisi.
🔰 Nazorat uchun eng yaxshi bot.

Asosiy xususiyatlar:
✅ Tez buyruq javoblari
✅ Katta guruhlarda silliq ishlash
✅ Uzilishsiz va doimiy onlayn
✅ Guruh xavfsizligi va himoyasi:
✅ Spamdan himoya
✅ So'z va iboralarni ilg'or filtrlash
✅ Foydalanuvchi kirishini aniq boshqarish
✅ Rasm va video limitlari (Bir kunda 3 tadan ko'p yuborsa 4-chisida 1 kunlik MUTE!)
✅ Ilg'or qulflash va cheklash tizimi
✅ 1, 3 va 10 kunlik aniq ob-havo ma'lumotlari

👑 <b>Bot egasi:</b> @JamshidjonDavronov

⚠️ <b>MUHIM ESLATMA:</b>
Agar botni o'z guruhingizga qo'shmoqchi bo'lsangiz, avval bot egasi @JamshidjonDavronov bilan bog'laning va uning roziligini olib, so'ngra botni guruhingizga admin qilib foydalaning! (Egasi roziligisiz bot begona guruhlarda ishlamaydi).

— 🛡 Asalarichilik.Uz🇺🇿 —"""

WELCOME_RU = """Здравствуйте, {first_name} 🙋‍♂️

🔰 Познакомьтесь с лучшим инструментом Telegram.
🔰 Мощный групповой менеджер.
🔰 Лучший бот для полного контроля и безопасности.

Основные возможности:
✅ Мгновенные ответы на команды
✅ Плавная работа в больших группах
✅ Надежный онлайн 24/7 без перебоев
✅ Безопасность и защита групп:
✅ Полная защита от спама и рекламных ссылок
✅ Умная фильтрация нецензурных слов
✅ Точный контроль входа пользователей
✅ Лимиты фото и видео (до 3 в день, на 4-й — МУТ на 24 часа!)
✅ Продвинутая система замков и ограничений
✅ Точный прогноз погоды на 1, 3 и 10 дней

👑 <b>Владелец бота:</b> @JamshidjonDavronov

⚠️ <b>ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:</b>
Если вы хотите добавить бота в свою группу, сначала свяжитесь с владельцем бота @JamshidjonDavronov и только с его согласия назначайте бота администратором и используйте его! (Без одобрения владельца бот не будет работать в группе).

— 🛡 Asalarichilik.Uz🇺🇿 —"""

WELCOME_EN = """Hello, {first_name} 🙋‍♂️

🔰 Meet the best Telegram group management tool.
🔰 Powerful group administrator.
🔰 The best bot for complete control & security.

Main features:
✅ Ultra fast command responses
✅ Smooth operation in huge groups
✅ 24/7 continuous online uptime
✅ Group safety and security:
✅ Anti-spam & link protection
✅ Advanced word & phrase filtering
✅ Strict user entry & member control
✅ Photo & video limits (max 3/day, 4th = 24h MUTE!)
✅ Advanced locking and restriction system
✅ 1, 3 and 10 days accurate weather forecasts

👑 <b>Bot Owner:</b> @JamshidjonDavronov

⚠️ <b>IMPORTANT NOTICE:</b>
If you wish to add this bot to your group, please contact the bot owner @JamshidjonDavronov first and only use it as an admin with his prior permission! (The bot will not operate in groups without owner approval).

— 🛡 Asalarichilik.Uz🇺🇿 —"""

def get_welcome_text(first_name, lang="uz_kr"):
    tpl = {"ru": WELCOME_RU, "en": WELCOME_EN, "uz_lat": WELCOME_UZ_LAT}.get(lang, WELCOME_UZ_KR)
    return tpl.format(first_name=first_name, owner=OWNER_USERNAME, bot_name=BOT_NAME)

# 5. Клавиатуралар ва Менюлар (Кўптиллик)
def get_main_menu_btn_label(lang="uz_kr"):
    if lang == "ru":
        return "🏠 Главное меню"
    elif lang == "en":
        return "🏠 Main Menu"
    elif lang == "uz_lat":
        return "🏠 Asosiy Menyu"
    return "🏠 Асосий Меню"

def get_main_reply_keyboard(lang="uz_kr", user_id=None):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    is_owner = (user_id == OWNER_ID)
    if lang == "ru":
        markup.row(KeyboardButton("🏠 Главное меню"))
        markup.row(KeyboardButton("Настройки группы 🎛"), KeyboardButton("Сменить язык 🌐"))
        markup.row(KeyboardButton("Инструкция бота 📖"), KeyboardButton("🩺 Врач Asalarichilik.Uz🇺🇿 🐝"))
        markup.row(KeyboardButton("📰 Новости (/news)"), KeyboardButton("🐝 Викторина & Опрос 📊"))
        if is_owner:
            markup.row(KeyboardButton("📢 Рассылка рекламы 📨"), KeyboardButton("👑 Управление группами 👥"))
            markup.row(KeyboardButton("🎙 Писать от имени бота 💬"))
    elif lang == "en":
        markup.row(KeyboardButton("🏠 Main Menu"))
        markup.row(KeyboardButton("Group Settings 🎛"), KeyboardButton("Change Language 🌐"))
        markup.row(KeyboardButton("Bot Manual 📖"))
        markup.row(KeyboardButton("📰 News (/news)"), KeyboardButton("🐝 Quizzes & Polls 📊"))
        if is_owner:
            markup.row(KeyboardButton("📢 Broadcast Message 📨"), KeyboardButton("👑 Group Control 👥"))
            markup.row(KeyboardButton("🎙 Speak as Bot 💬"))
    elif lang == "uz_lat":
        markup.row(KeyboardButton("🏠 Asosiy menyu"))
        markup.row(KeyboardButton("Guruh sozlamalari 🎛"), KeyboardButton("Tilni o'zgartirish 🌐"))
        markup.row(KeyboardButton("Bot qo'llanmasi 📖"), KeyboardButton("🩺 Asalarichilik.Uz🇺🇿 shifokori 🐝"))
        markup.row(KeyboardButton("📰 Yangiliklar (/news)"), KeyboardButton("🐝 Viktorina & So'rovnoma 📊"))
        if is_owner:
            markup.row(KeyboardButton("📢 Reklama tarqatish 📨"), KeyboardButton("👑 Guruhlar nazorati 👥"))
            markup.row(KeyboardButton("🎙 Bot nomidan yozish 💬"))
    else:
        markup.row(KeyboardButton("🏠 Асосий меню"))
        markup.row(KeyboardButton("Гуруҳ созламалари 🎛"), KeyboardButton("Тилни ўзгартириш 🌐"))
        markup.row(KeyboardButton("Бот қўлланмаси 📖"), KeyboardButton("🩺 Asalarichilik.Uz🇺🇿 шифокори 🐝"))
        markup.row(KeyboardButton("📰 Янгиликлар (/news)"), KeyboardButton("🐝 Викторина & Сўровнома 📊"))
        if is_owner:
            markup.row(KeyboardButton("📢 Реклама тарқатиш 📨"), KeyboardButton("👑 Гуруҳлар назорати 👥"))
            markup.row(KeyboardButton("🎙 Бот номидан ёзиш 💬"))
    return markup

def get_main_menu_markup(lang="uz_kr", user_id=None):
    markup = InlineKeyboardMarkup()
    is_owner = (user_id == OWNER_ID)
    if lang == "ru":
        markup.row(
            InlineKeyboardButton("➕ Добавить в группу", callback_data="menu_add_group"),
            InlineKeyboardButton("➕ Добавить в канал", callback_data="menu_add_channel")
        )
        markup.row(
            InlineKeyboardButton("🎛 Настройки группы", callback_data="menu_settings"),
            InlineKeyboardButton("📢 Управление каналами", callback_data="channels_panel")
        )
        markup.row(
            InlineKeyboardButton("📰 Новости пчеловодства (/news)", callback_data="open_bee_news"),
            InlineKeyboardButton("🐝 Викторины & Опросы 📊", callback_data="open_bee_quiz")
        )
        markup.row(InlineKeyboardButton("👑 Владелец", url="https://t.me/JamshidjonDavronov"))
        if is_owner:
            markup.row(
                InlineKeyboardButton("📢 Рассылка рекламы (Эгаси)", callback_data="bc_menu"),
                InlineKeyboardButton("👑 Управление группами", callback_data="owner_groups")
            )
        markup.row(
            InlineKeyboardButton("🌐 Сменить язык", callback_data="menu_language"),
            InlineKeyboardButton("📖 Инструкция бота", callback_data="menu_help")
        )
    elif lang == "en":
        markup.row(
            InlineKeyboardButton("➕ Add to Group", callback_data="menu_add_group"),
            InlineKeyboardButton("➕ Add to Channel", callback_data="menu_add_channel")
        )
        markup.row(
            InlineKeyboardButton("🎛 Group Settings", callback_data="menu_settings"),
            InlineKeyboardButton("📢 Manage Channels", callback_data="channels_panel")
        )
        markup.row(
            InlineKeyboardButton("📰 Beekeeping News (/news)", callback_data="open_bee_news"),
            InlineKeyboardButton("🐝 Beekeeping Quizzes 📊", callback_data="open_bee_quiz")
        )
        markup.row(InlineKeyboardButton("👑 Owner", url="https://t.me/JamshidjonDavronov"))
        if is_owner:
            markup.row(
                InlineKeyboardButton("📢 Broadcast Ads (Owner)", callback_data="bc_menu"),
                InlineKeyboardButton("👑 Group Control", callback_data="owner_groups")
            )
        markup.row(
            InlineKeyboardButton("🌐 Change Language", callback_data="menu_language"),
            InlineKeyboardButton("📖 Bot Manual", callback_data="menu_help")
        )
    elif lang == "uz_lat":
        markup.row(
            InlineKeyboardButton("➕ Guruhga qo'shish", callback_data="menu_add_group"),
            InlineKeyboardButton("➕ Kanalga qo'shish", callback_data="menu_add_channel")
        )
        markup.row(
            InlineKeyboardButton("🎛 Guruh sozlamalari", callback_data="menu_settings"),
            InlineKeyboardButton("📢 Kanallar boshqaruvi", callback_data="channels_panel")
        )
        markup.row(
            InlineKeyboardButton("📰 Asalarichilik yangiliklari (/news)", callback_data="open_bee_news"),
            InlineKeyboardButton("🐝 Viktorina & So'rovnomalar 📊", callback_data="open_bee_quiz")
        )
        markup.row(InlineKeyboardButton("👑 Bot egasi", url="https://t.me/JamshidjonDavronov"))
        if is_owner:
            markup.row(
                InlineKeyboardButton("📢 Reklama tarqatish (Egasi)", callback_data="bc_menu"),
                InlineKeyboardButton("👑 Guruhlar nazorati", callback_data="owner_groups")
            )
        markup.row(
            InlineKeyboardButton("🌐 Tilni o'zgartirish", callback_data="menu_language"),
            InlineKeyboardButton("📖 Bot qo'llanmasi", callback_data="menu_help")
        )
    else:
        markup.row(
            InlineKeyboardButton("➕ Гуруҳга қўшиш", callback_data="menu_add_group"),
            InlineKeyboardButton("➕ Каналга қўшиш", callback_data="menu_add_channel")
        )
        markup.row(
            InlineKeyboardButton("🎛 Гуруҳ созламалари", callback_data="menu_settings"),
            InlineKeyboardButton("📢 Каналлар бошқаруви", callback_data="channels_panel")
        )
        markup.row(
            InlineKeyboardButton("📰 Асаларичилик янгиликлари (/news)", callback_data="open_bee_news"),
            InlineKeyboardButton("🐝 Викторина & Сўровномалар 📊", callback_data="open_bee_quiz")
        )
        markup.row(InlineKeyboardButton("👑 Бот эгаси", url="https://t.me/JamshidjonDavronov"))
        if is_owner:
            markup.row(
                InlineKeyboardButton("📢 Реклама тарқатиш (Эгаси)", callback_data="bc_menu"),
                InlineKeyboardButton("👑 Гуруҳлар назорати", callback_data="owner_groups")
            )
        markup.row(
            InlineKeyboardButton("🌐 Тилни ўзгартириш", callback_data="menu_language"),
            InlineKeyboardButton("📖 Бот қўлланмаси", callback_data="menu_help")
        )
    return markup

# 6. БОТ ҚЎЛЛАНМАСИ (Кўптиллик)
def get_guide_text(lang="uz_kr"):
    if lang == "ru":
        return (
            "📖 <b>Инструкция по использованию бота Asalarichilik.Uz:</b>\n\n"
            "1. <b>Добавление в группу:</b>\n"
            "Перед добавлением свяжитесь с владельцем @JamshidjonDavronov. После согласия добавьте бота и назначьте его администратором со всеми правами.\n\n"
            "2. <b>Обязательная подписка:</b>\n"
            "Работает строго для новых участников группы! Старые участники не затрагиваются.\n\n"
            "3. <b>Прогноз погоды (1, 3 и 10 дней):</b>\n"
            "Настройка точного времени отправки прогноза погоды в группу (например, 08:00) с авто-удалением старых прогнозов.\n\n"
            "4. <b>Часовой пояс и время:</b>\n"
            "Автоматическое определение по геолокации Telegram, выбор региона Узбекистана или ручной ввод UTC (+5).\n\n"
            "5. <b>Защита и безопасность:</b>\n"
            "Блокировка ссылок, спама, мата, пересылок (forward), стикеров, арабских символов и ночной замок сна группы.\n\n"
            "6. <b>Лимиты на фото и видео:</b>\n"
            "Ограничение до 3 медиа в сутки. На 4-е нарушитель получает МУТ на 24 часа!\n\n"
            "7. <b>Рассылка рекламы и информации:</b>\n"
            "Отправка постов во все группы и каналы с кнопками реакций (👍 ❤️ 🔥 👏 🐝) и кнопкой «Поделиться»!\n\n"
            "8. <b>Ответ от имени бота в группе (БЕЗ символа «/»):</b>\n"
            "Ответьте (Reply) на сообщение пользователя в группе и напишите обычными словами:\n"
            "• <code>reply Ваш текст</code>\n"
            "• <code>жавоб: Ваш текст</code> или <code>жавоб Ваш текст</code>\n"
            "• <code>бот: Ваш текст</code> или <code>бот Ваш текст</code>\n"
            "• <code>say Ваш текст</code>\n"
            "<i>(Ваша команда сразу удаляется, а бот отправляет этот текст пользователю от своего имени!)</i>\n\n"
            "9. <b>Быстрые команды админа в группе (БЕЗ символа «/»):</b>\n"
            "• <code>ўчир</code> или <code>del</code> — удалить сообщение пользователя (в ответ)\n"
            "• <code>қада</code> или <code>pin</code> — закрепить сообщение (в ответ)\n"
            "• <code>еч</code> или <code>unpin</code> — открепить сообщение\n"
            "• <code>мут 1h</code> / <code>мут 1d</code> — мут на 1 час / 1 день (в ответ)\n"
            "• <code>унмут</code> — снять мут (в ответ)\n"
            "• <code>бан</code> — забанить пользователя (в ответ)\n"
            "• <code>қулфлар</code> — открыть панель замков\n"
            "• <code>очиш</code> — снять все замки\n"
            "• <code>видео оч</code> / <code>видео ёп</code> — вкл/выкл медиа\n"
            "• <code>файл оч</code> / <code>файл ёп</code> — вкл/выкл файлы\n"
            "• <code>овоз оч</code> / <code>овоз ёп</code> — вкл/выкл голосовые\n"
            "• <code>тунги қулф ёқ</code> / <code>тунги қулф ўчир</code> — вкл/выкл ночной замок"
        )
    elif lang == "uz_lat":
        return (
            "📖 <b>Asalarichilik.Uz Boti Qo'llanmasi:</b>\n\n"
            "1. <b>Botni guruhga qo'shish:</b>\n"
            "Qo'shishdan oldin bot egasi @JamshidjonDavronov bilan bog'laning va rozilik oling. So'ng botni guruhga to'liq administrator qiling.\n\n"
            "2. <b>Majburiy obuna:</b>\n"
            "Faqat yangi qo'shilgan a'zolar uchun ishlaydi, eski a'zolarga xalaqit bermaydi!\n\n"
            "3. <b>Ob-havo sozlamalari (1, 3 va 10 kunlik):</b>\n"
            "Guruhga ob-havo yuborish soatini (masalan, 08:00) va forecast turini belgilashingiz mumkin.\n\n"
            "4. <b>Vaqt zonasi:</b>\n"
            "Telegram lokatsiyasi orqali avtomatik, O'zbekiston viloyatlari bo'yicha yoki qo'lda UTC (+5) farqini kiritish imkoni.\n\n"
            "5. <b>Xavfsizlik va Qulflar:</b>\n"
            "Havolalar, spam, so'kinish, forvard, stiker, arabcha xabarlar va tungi avto-qulflash.\n\n"
            "6. <b>Rasm va Video limitlari:</b>\n"
            "Kuniga 3 tagacha ruxsat. 4-chisi yuborilganda foydalanuvchiga 24 soatlik MUTE beriladi!\n\n"
            "7. <b>Reklama va xabarlar tarqatish:</b>\n"
            "Barcha guruh va kanallarga layklar (👍 ❤️ 🔥 👏 🐝) va ulashish tugmasi bilan xabar tarqatish.\n\n"
            "8. <b>Guruhda bot nomidan javob yozish («/» belgisiz, oddiy so'zlar bilan):</b>\n"
            "Guruhda istalgan a'zo xabariga javoban (Reply qilib) yozing:\n"
            "• <code>reply Sizning xabaringiz</code>\n"
            "• <code>javob: Sizning xabaringiz</code> yoki <code>javob Sizning xabaringiz</code>\n"
            "• <code>bot: Sizning xabaringiz</code> yoki <code>bot Sizning xabaringiz</code>\n"
            "• <code>ayt Sizning xabaringiz</code> yoki <code>say Sizning xabaringiz</code>\n"
            "<i>(Siz yozgan buyruq xabari guruhdan avtomatik o'chiriladi va bot sizning nomingizdan o'sha a'zoga rasmiy javob qaytaradi!)</i>\n\n"
            "9. <b>Guruhda tezkor admin buyruqlari («/» belgisiz):</b>\n"
            "• <code>o'chir</code> yoki <code>del</code> — xabarni o'chirish (reply qilib)\n"
            "• <code>qada</code> yoki <code>pin</code> — xabarni qadash (reply qilib)\n"
            "• <code>yech</code> yoki <code>unpin</code> — qadalgan xabarni yechish\n"
            "• <code>mut 1h</code> / <code>mut 1d</code> — 1 soat / 1 kunga yozishni cheklash\n"
            "• <code>unmut</code> — cheklovni yechish\n"
            "• <code>ban</code> — guruhdan haydash va bloklash\n"
            "• <code>qulflar</code> — qulflar markazini ochish\n"
            "• <code>ochish</code> — barcha qulflarni ochish\n"
            "• <code>video och</code> / <code>video yop</code> — video ruxsatini ochish/yopish\n"
            "• <code>fayl och</code> / <code>fayl yop</code> — fayllarni ochish/yopish\n"
            "• <code>ovoz och</code> / <code>ovoz yop</code> — ovozli xabarlarni ochish/yopish\n"
            "• <code>tungi qulf yoq</code> / <code>tungi qulf o'chir</code> — tungi rejimni yoqish/o'chirish"
        )
    elif lang == "en":
        return (
            "📖 <b>Asalarichilik.Uz Bot User Manual:</b>\n\n"
            "1. <b>Adding Bot to Group:</b>\n"
            "Before adding, please contact the bot owner @JamshidjonDavronov. Once authorized, add the bot and promote it to administrator with full permissions.\n\n"
            "2. <b>Mandatory Channel Subscription:</b>\n"
            "Strictly applies to NEW joining members; existing members are never restricted!\n\n"
            "3. <b>Weather Forecasts (1, 3 & 10 Days):</b>\n"
            "Configure scheduled daily weather reports at your desired hour (e.g., 08:00) with automatic message cleanup.\n\n"
            "4. <b>Timezone & Clock:</b>\n"
            "Automatic geolocation detection via Telegram, regional presets (UTC+5), or custom manual UTC offset.\n\n"
            "5. <b>Security & Locks:</b>\n"
            "20+ security locks: anti-spam, links, foul language, forwards, stickers, Arabic script, and Night Auto-Lock.\n\n"
            "6. <b>Media Limits:</b>\n"
            "Restricts users to 3 photos/videos per day. Sending a 4th triggers an automatic 24-hour MUTE!\n\n"
            "7. <b>Broadcast & Reactions:</b>\n"
            "Broadcast announcements to all connected groups and channels featuring live reaction counters (👍 ❤️ 🔥 👏 🐝) and a quick Share button!\n\n"
            "8. <b>Reply as Bot in Groups (WITHOUT any '/' symbol):</b>\n"
            "Reply to any user's message in the group and write plain text:\n"
            "• <code>reply Your message text</code>\n"
            "• <code>жавоб: Your message text</code> or <code>javob Your message text</code>\n"
            "• <code>bot: Your message text</code> or <code>bot Your message text</code>\n"
            "• <code>say Your message text</code>\n"
            "<i>(Your command is deleted instantly, and the bot replies to the user on your behalf!)</i>\n\n"
            "9. <b>Quick Admin Commands in Groups (Without '/' symbol):</b>\n"
            "• <code>ўчир</code> or <code>del</code> — delete replied message\n"
            "• <code>қада</code> or <code>pin</code> — pin replied message\n"
            "• <code>еч</code> or <code>unpin</code> — unpin message\n"
            "• <code>мут 1h</code> / <code>мут 1d</code> — mute user for 1h or 1d\n"
            "• <code>унмут</code> — unmute user\n"
            "• <code>бан</code> — ban user\n"
            "• <code>қулфлар</code> — open security locks panel\n"
            "• <code>очиш</code> — unlock all group features\n"
            "• <code>видео оч</code> / <code>видео ёп</code> — allow/block media\n"
            "• <code>файл оч</code> / <code>файл ёп</code> — allow/block files\n"
            "• <code>овоз оч</code> / <code>овоз ёп</code> — allow/block voice messages\n"
            "• <code>тунги қулф ёқ</code> / <code>тунги қулф ўчир</code> — enable/disable night auto-lock"
        )
    else: # uz_kr
        return (
            "📖 <b>Asalarichilik.Uz Боти Қўлланмаси:</b>\n\n"
            "1. <b>Ботни гуруҳга қўшиш:</b>\n"
            "Қўшишдан олдин бот эгаси @JamshidjonDavronov билан боғланинг ва розилик олинг. Сўнг ботни гуруҳга тўлиқ администратор қилиб тайинланг.\n\n"
            "2. <b>Мажбурий обуна:</b>\n"
            "Фақат янги кирган аъзолар учун ишлайди, эски аъзоларга тегмайди! Админ тасдиғи ёқилса, каналга обуна бўлгач админ рухсати керак бўлади.\n\n"
            "3. <b>Об-ҳаво хабарлари (1, 3 ва 10 кунлик):</b>\n"
            "Гуруҳга қайси соатда юбориш (масалан, 08:00), 1/3/10 кунлик прогноз тури ва эски хабарни ўчириш созланади.\n\n"
            "4. <b>Вақт минтақаси:</b>\n"
            "Локация орқали автоматик, вилоят танлаш ёки қўлда UTC (+5) фарқини киритиш орқали аниқланади.\n\n"
            "5. <b>Хавфсизлик ва Қулфлар:</b>\n"
            "Ҳаволалар, спам, сўкиниш, форвард, стикер ва тунги қулф.\n\n"
            "6. <b>Расм ва видео лимитлари:</b>\n"
            "Кунига 3 тагача. 4-чисида автоматик 24 соатлик МУТЕ берилади!\n\n"
            "7. <b>Реклама ва маълумот тарқатиш:</b>\n"
            "Бот эгаси барча гуруҳ ва каналларга лайк белгилари (👍 ❤️ 🔥 👏 🐝) ва улашиш тугмаси билан реклама юбориши мумкин!\n\n"
            "8. <b>Бот номидан фойдаланувчига жавоб бериш («/» белгисисиз, оддий сўзлар билан):</b>\n"
            "Гуруҳда исталган фойдаланувчи хабарига жавобан (Reply қилиб) ёзинг:\n"
            "• <code>reply Сизнинг матнингиз</code>\n"
            "• <code>жавоб: Сизнинг матнингиз</code> ёки <code>жавоб Сизнинг матнингиз</code>\n"
            "• <code>бот: Сизнинг матнингиз</code> ёки <code>бот Сизнинг матнингиз</code>\n"
            "• <code>айт Сизнинг матнингиз</code> ёки <code>say Сизнинг матнингиз</code>\n"
            "<i>(Сиз ёзган хабар гуруҳдан автоматик ўчирилади ва бот сизнинг номингиздан ўша фойдаланувчига расмий жавоб беради!)</i>\n\n"
            "9. <b>Гуруҳда тезкор админ буйруқлари («/» белгисисиз, оддий сўзлар):</b>\n"
            "• <code>ўчир</code> ёки <code>del</code> — Хабарга жавоб қилиб ёзилса, ўша хабарни ўчиради.\n"
            "• <code>қада</code> ёки <code>pin</code> — Хабарга жавоб қилиб ёзилса, хабарни қадайди.\n"
            "• <code>еч</code> ёки <code>unpin</code> — Қадалган хабарни ечади.\n"
            "• <code>мут 1h</code> / <code>мут 1d</code> — 1 соат ёки 1 кунга ёзишни тақиқлайди.\n"
            "• <code>унмут</code> — Чекловни ечади ва ёзишга рухсат беради.\n"
            "• <code>бан</code> — Қоидабузарни гуруҳдан чиқариб блоклайди.\n"
            "• <code>қулфлар</code> — Қулфлар маркази панелини очади.\n"
            "• <code>очиш</code> — Барча қулфларни бир зумда очади.\n"
            "• <code>видео оч</code> / <code>видео ёп</code> — Видео ва медиани очиш/ёпиш.\n"
            "• <code>файл оч</code> / <code>файл ёп</code> — Ҳужжат ва файлларни очиш/ёпиш.\n"
            "• <code>овоз оч</code> / <code>овоз ёп</code> — Овозли хабарларни очиш/ёпиш.\n"
        )

# 7. РЕКЛАМА ВА ХАБАР ТАРҚАТИШ (CONTROLLER BOT) ТИЗИМИ
def get_post_editor_reply_keyboard(lang="ru"):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if lang == "ru":
        markup.row(KeyboardButton("Очистить"), KeyboardButton("Предпросмотр"))
        markup.row(KeyboardButton("Отменить"), KeyboardButton("Далее"))
    elif lang == "en":
        markup.row(KeyboardButton("Clear"), KeyboardButton("Preview"))
        markup.row(KeyboardButton("Cancel"), KeyboardButton("Next"))
    elif lang == "uz_lat":
        markup.row(KeyboardButton("Tozalash"), KeyboardButton("Ko'rib chiqish"))
        markup.row(KeyboardButton("Bekor qilish"), KeyboardButton("Keyingisi"))
    else:
        markup.row(KeyboardButton("Тозалаш"), KeyboardButton("Кўриб чиқиш"))
        markup.row(KeyboardButton("Бекор қилиш"), KeyboardButton("Кейингиси"))
    return markup

def get_reactions_preset_reply_keyboard(lang="ru"):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.row(KeyboardButton("👍 👎 ❤️"))
    markup.row(KeyboardButton("👍 👎"))
    markup.row(KeyboardButton("👍 👎 🙏"))
    markup.row(KeyboardButton("👍 ❤️ 🙌"))
    markup.row(KeyboardButton("👍 ❤️ 🔥 👏 🐝"))
    cancel_lbl = "Отмена" if lang == "ru" else ("Cancel" if lang == "en" else "Бекор қилиш")
    markup.row(KeyboardButton(cancel_lbl))
    return markup

def get_cancel_reply_keyboard(lang="ru"):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_lbl = "Отменить" if lang == "ru" else ("Cancel" if lang == "en" else "Бекор қилиш")
    markup.row(KeyboardButton(cancel_lbl))
    return markup

def parse_url_buttons(raw_text):
    rows = []
    lines = [l.strip() for l in raw_text.strip().split('\n') if l.strip()]
    for line in lines:
        btns = [b.strip() for b in line.split('|') if b.strip()]
        row = []
        for b in btns:
            if ' - ' in b:
                parts = b.rsplit(' - ', 1)
                text = parts[0].strip()
                url = parts[1].strip()
                if url.startswith(('http://', 'https://', 'tg://')):
                    row.append({'text': text, 'url': url})
            elif '-' in b:
                parts = b.rsplit('-', 1)
                text = parts[0].strip()
                url = parts[1].strip()
                if url.startswith(('http://', 'https://', 'tg://')):
                    row.append({'text': text, 'url': url})
        if row:
            rows.append(row)
    return rows

def parse_reactions(raw_text):
    text = raw_text.strip()
    if '/' in text:
        parts = [p.strip() for p in text.split('/') if p.strip()]
    elif ',' in text:
        parts = [p.strip() for p in text.split(',') if p.strip()]
    else:
        parts = [p.strip() for p in text.split() if p.strip()]
    return parts[:8]

def parse_schedule_time(raw_text):
    text = raw_text.strip()
    now = datetime.now()
    try:
        dt = datetime.strptime(text, '%H:%M')
        res = now.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
        if res < now:
            res += timedelta(days=1)
        return res
    except Exception:
        pass
    try:
        dt = datetime.strptime(text, '%d.%m %H:%M')
        res = dt.replace(year=now.year, second=0, microsecond=0)
        if res < now:
            res = res.replace(year=now.year + 1)
        return res
    except Exception:
        pass
    try:
        return datetime.strptime(text, '%d.%m.%Y %H:%M')
    except Exception:
        pass
    return None

def get_controller_reaction_counts(post_id):
    cursor.execute("SELECT emoji, COUNT(*) as cnt FROM post_reactions WHERE post_id = ? GROUP BY emoji", (post_id,))
    rows = cursor.fetchall()
    return {r["emoji"]: r["cnt"] for r in rows}

def build_controller_post_markup(post_id=0, reactions_list=None, url_buttons_rows=None, has_comments=False, comments_url=None, native_comments=False, share_text="Asalarichilik", post_link=None):
    markup = InlineKeyboardMarkup()
    if url_buttons_rows:
        for row in url_buttons_rows:
            btn_row = []
            for btn in row:
                btn_row.append(InlineKeyboardButton(text=btn.get("text", "Ссылка"), url=btn.get("url", "https://t.me")))
            if btn_row:
                markup.row(*btn_row)

    if reactions_list:
        counts = get_controller_reaction_counts(post_id) if post_id else {}
        react_row = []
        for idx, em in enumerate(reactions_list):
            cnt = counts.get(em, 0)
            lbl = f"{em} {cnt}" if cnt > 0 else em
            react_row.append(InlineKeyboardButton(lbl, callback_data=f"cb_react_{post_id}_{idx}"))
        if react_row:
            for i in range(0, len(react_row), 5):
                markup.row(*react_row[i:i+5])

    # 💬 Мукаммал изоҳлар (комментарии) бўлими
    if has_comments or native_comments:
        c_count = 0
        if post_id:
            try:
                cursor.execute("SELECT COUNT(*) as cnt FROM post_comments WHERE post_id = ?", (post_id,))
                c_row = cursor.fetchone()
                if c_row:
                    c_count = c_row["cnt"]
            except Exception:
                pass
        
        c_lbl = f"💬 Изоҳлар ({c_count})" if c_count > 0 else "💬 Изоҳлар / Комментарии"
        
        c_target = comments_url or ""
        if c_target and c_target.lower() != "bot":
            if c_target.startswith("http"):
                c_link = c_target
            elif c_target.startswith("@"):
                c_link = f"https://t.me/{c_target.lstrip('@')}"
            else:
                c_link = f"https://t.me/{c_target}"
        else:
            c_link = f"https://t.me/{BOT_USERNAME}?start=comment_{post_id}" if post_id else f"https://t.me/{BOT_USERNAME}"
        
        markup.row(InlineKeyboardButton(c_lbl, url=c_link))

    # ↗️ Мукаммал Улашиш (Share) тизими: Тўлиқ маълумотни узатиш, қисқартирмаслик!
    raw_share = (share_text or "Asalarichilik.Uz").strip()
    clean_share = re.sub(r'<[^>]+>', '', raw_share).strip()
    if not clean_share:
        clean_share = "Asalarichilik.Uz"
    
    # Telegram share URL лимитига мос равишда тўлиқ матн (850 белгигача сўзма-сўз) улашилади
    if len(clean_share) > 850:
        clean_share = clean_share[:850].rsplit(' ', 1)[0] + "..."
    
    share_content = f"🐝 {clean_share}\n\n👉 @{BOT_USERNAME}"
    safe_share = urllib.parse.quote(share_content)
    
    target_url = post_link or f"https://t.me/{BOT_USERNAME}"
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(target_url)}&text={safe_share}"
    markup.row(InlineKeyboardButton("↗️ Поделиться / Улашиш", url=share_url))
    return markup

def show_comments_config_menu(chat_id, user_id, message_id=None, lang="uz_kr"):
    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(InlineKeyboardButton("🤖 Комментарии через бота (Интерактивно)", callback_data="bc_set_comment_bot"))
        markup.row(InlineKeyboardButton("🔗 Ссылка на группу обсуждений", callback_data="bc_set_comment_url"))
        markup.row(InlineKeyboardButton("❌ Отключить комментарии", callback_data="bc_set_comment_off"))
        markup.row(InlineKeyboardButton("« Назад к редактору", callback_data="bc_back_to_editor"))
        txt = (
            "💬 <b>Настройка комментариев к посту:</b>\n\n"
            "Выберите способ обсуждения поста:\n\n"
            "1. <b>🤖 Через бота:</b> Подписчики смогут нажать кнопку и оставить комментарий прямо в боте. Вы получите уведомление о каждом комментарии.\n"
            "2. <b>🔗 Ссылка на чат:</b> Кнопка будет открывать вашу группу обсуждений.\n"
            "3. <b>❌ Отключить:</b> Кнопка комментариев не будет добавлена."
        )
    else:
        markup.row(InlineKeyboardButton("🤖 Бот орқали изоҳлар (Интерактив)", callback_data="bc_set_comment_bot"))
        markup.row(InlineKeyboardButton("🔗 Муҳокама гуруҳи ҳаволасини қўйиш", callback_data="bc_set_comment_url"))
        markup.row(InlineKeyboardButton("❌ Изоҳларни ўчириш", callback_data="bc_set_comment_off"))
        markup.row(InlineKeyboardButton("« Орқага", callback_data="bc_back_to_editor"))
        txt = (
            "💬 <b>Пост учун изоҳлар (комментария) созламалари:</b>\n\n"
            "Қайси турдаги изоҳ тизимини танлайсиз?\n\n"
            "1. <b>🤖 Бот орқали (Интерактив):</b> Обуначилар пост остидаги тугмани босиб, бот ичида фикр ёзади. Сизга ҳар бир изоҳ дарҳол етиб келади ва жавоб бера оласиз.\n"
            "2. <b>🔗 Муҳокама гуруҳига улаш:</b> Тугма босилганда гуруҳ ёки чатингиз очилади.\n"
            "3. <b>❌ Ўчириш:</b> Изоҳ тугмаси чиқарилмайди."
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# ==================== ХАЛҚАРО ВА МАҲАЛЛИЙ АСАЛАРИЧИЛИК ЯНГИЛИКЛАРИ МАРКАЗИ ====================
BEE_GLOBAL_NEWS = [
    {
        "id": 1,
        "title_kr": "🔬 Олимлар асаларилар иммунитетини 40% га оширувчи янги табиий озуқа ихтиро қилишди!",
        "title_lat": "🔬 Olimlar asalarilar immunitetini 40% ga oshiruvchi yangi tabiiy ozuqa ixtiro qilishdi!",
        "title_ru": "🔬 Учёные создали натуральный биокомплекс, повышающий иммунитет пчёл на 40%!",
        "source": "Nature Scientific Reports / Халқаро тадқиқот",
        "date": "2026 йил Октябрь",
        "category": "Илмий кашфиёт",
        "body_kr": (
            "Германия ва Австралия биологлари томонидан олиб борилган тадқиқотлар якунланди. "
            "Олимлар асаларилар ичак микрофлораси ва ўсимлик экстрактлари асосида янги табиий озуқа яратдилар.\n\n"
            "📌 Тадқиқот натижалари:\n"
            "1. Кузги озиқлантиришда берилганда оилалар нозематоз ва вирусларга 40% чидамли бўлди.\n"
            "2. Қишловда ўлим деярли 0% га тушди.\n"
            "3. Баҳорда тухум қўйиш 25-30% тезлашди."
        ),
        "body_lat": "Germaniya va Avstraliya biologlari arilar immunitetini 40% ga oshiruvchi tabiiy probiotik yaratishdi. Qishlovdagi nobudgarchilik bartaraf etildi.",
        "body_ru": "Учёные Германии и Австралии разработали биокомплекс, повышающий резистентность пчёл к нозематозу и вирусам на 40%, гарантируя 100% выживаемость зимой."
    },
    {
        "id": 2,
        "title_kr": "🛰 Ақлли арихоналар (Smart Hive): Уяни очмасдан вазн ва ҳароратни назорат қилиш даври келди!",
        "title_lat": "🛰 Aqlli arixonalar (Smart Hive): Uyani ochmasdan vazn va haroratni nazorat qilish davri keldi!",
        "title_ru": "🛰 Умные пасеки (Smart Hive): Контроль микроклимата и веса улья со смартфона!",
        "source": "Apimondia International / Агротехнологиялар",
        "date": "2026 йил",
        "category": "Инновация",
        "body_kr": (
            "Халқаро Апимондия анжуманида тақдим этилган янги авлод сенсорлари эндиликда уяларни очмасдан смартфон орқали кузатиш имконини бермоқда.\n\n"
            "📌 Имкониятлар:\n"
            "• Ақлли тарози: Кунлик асал киришини кўрсатади.\n"
            "• Акустик микрофон: Роялик кайфиятини 5 кун аввал хабарлайди!\n"
            "• Ҳарорат назорати: Қишги клуб ҳолатини билдиради."
        ),
        "body_lat": "Smart Hive sensorlari yordamida uyani ochmasdan asal kirishini kuzatish va roylashni 5 kun avval bilish mumkin.",
        "body_ru": "Беспроводные датчики позволяют отслеживать вес улья, выявлять роевое состояние за 5 дней до выхода роя и контролировать температуру зимой."
    },
    {
        "id": 3,
        "title_kr": "🧬 Вароа канасига қарши генетик чидамлилик: VSH она арилари бўйича янги ютуқлар!",
        "title_lat": "🧬 Varroa kanasiga qarshi genetik chidamlilik: VSH ona arilari bo'yicha yangi yutuqlar!",
        "title_ru": "🧬 Селекция пчёл VSH: Генетическая устойчивость к клещу варроа!",
        "source": "Европа Асаларичилик Селекция Маркази",
        "date": "2026 йил",
        "category": "Селекция",
        "body_kr": (
            "Европа селекционерлари вароа канасига қарши ўз-ўзини тозалаш (VSH) хусусиятига эга Карника ва Бакфаст зотларини муваффақиятли кўпайтирмоқда.\n\n"
            "📌 Ишлаш принципи:\n"
            "Бундай арилар кана тушган катакчаларни очиб, канани йўқ қилади. Кимёвий дорилар сарфи 3 баробарга қисқаради!"
        ),
        "body_lat": "VSH xususiyatiga ega ona arilar nasli kataklardagi kanani o'zi topib yo'q qiladi. Kimyoviy dorilar sarfi kamayadi.",
        "body_ru": "Селекция пчёл с признаком VSH позволяет пчёлам самостоятельно очищать расплод от клеща варроа, снижая химические обработки на 70%."
    },
    {
        "id": 4,
        "title_kr": "🍯 Жаҳон асал бозори: Сохта асалларни 100% аниқловчи ЯМР тизими жорий этилмоқда",
        "title_lat": "🍯 Jahon asal bozori: Soxta asallarni 100% aniqlovchi YaMR tizimi",
        "title_ru": "🍯 Мировой рынок: ЯМР-тестирование против фальсификата мёда",
        "source": "Халқаро Сифат Ташкилоти / Apimondia",
        "date": "2026 йил",
        "category": "Бозор ва Таҳлил",
        "body_kr": (
            "Халқаро экспорт бозорларида сунъий шакар ва сироп қўшилган сохта асалларга қарши ЯМР (Ядерный Магнитный Резонанс) таҳлили мажбурий этиб белгиланмоқда.\n\n"
            "📌 Хулоса:\n"
            "Тоза, табиий тоғ ва дала асали етиштирувчи ҳалол асаларичилар маҳсулотига жаҳон бозорида талаб ва нархлар кескин ошмоқда."
        ),
        "body_lat": "Yangi laboratoriya tahlillari soxta asallarni to'liq fosh qilmoqda. Tabiiy asal narxlari oshmoqda.",
        "body_ru": "Внедрение метода ядерного магнитного резонанса (ЯМР) для анализа мёда защищает честных пчеловодов и повышает цены на натуральный мёд."
    },
    {
        "id": 5,
        "title_kr": "💨 Шовул кислотаси сублимацияси (буғлатиш): Кузги вароага қарши энг тоза ва юқори самарали усул!",
        "title_lat": "💨 Shovul kislotasi sublimatsiyasi: Kuzgi varroaga qarshi eng toza va yuqori samarali usul!",
        "title_ru": "💨 Сублимация щавелевой кислоты: 98% эффективность против варроа без химии!",
        "source": "Апитерапия ва Ветеринария Илмий Маркази",
        "date": "2026 йил",
        "category": "Даволаш ва Профилактика",
        "body_kr": (
            "Асаларичилар орасида шовул кислотасини махсус сублиматор (буғлатгич) орқали қўллаш оммалашмоқда.\n\n"
            "📌 Афзалликлари:\n"
            "• Уяда насл (расплод) бўлмаган даврда самарадорлик 98-99% ни ташкил қилади.\n"
            "• Асалда ва мумда ҳеч қандай зарарли кимёвий қолдиқ қолдирмайди.\n"
            "• Битта оилага ишлов бериш бор-йўғи 1-2 дақиқа вақт олади."
        ),
        "body_lat": "Shovul kislotasi sublimatsiyasi nasl bo'lmagan paytda 98% samara beradi va asalda kimyoviy qoldiq qoldirmaydi.",
        "body_ru": "Сублимация щавелевой кислоты при отсутствии расплода уничтожает до 99% клещей без загрязнения воска и мёда химикатами."
    },
    {
        "id": 6,
        "title_kr": "🌸 Фацелия ва эспарцет экиш бўйича янги дастур: Асал ҳосилини 2 баробарга ошириш сири!",
        "title_lat": "🌸 Fatseliya va espartset ekish dasturi: Asal hosilini 2 barobarga oshirish siri!",
        "title_ru": "🌸 Посев фацелии и эспарцета: Удвоение медосбора на стационарных пасеках!",
        "source": "Агро-Асаларичилик Тадқиқот Институти",
        "date": "2026 йил",
        "category": "Озуқа Базаси",
        "body_kr": (
            "Арихона атрофига фацелия, эспарцет ва оқ беда экиш орқали ёзги нектарсиз бўшлиқ (безвзяточный период)ни тўлиқ бартараф этиш мумкин.\n\n"
            "📌 Кўрсаткичлар:\n"
            "• 1 гектар фацелия майдони 300-500 кг гача олий навли шаффоф нектар беради.\n"
            "• Гуллаш муддати 35-45 кунгача давом этади."
        ),
        "body_lat": "Fatseliya va espartset ekish orqali gektaridan 500 kggacha shaffof asal olish va arilar rivojlanishini ta'minlash mumkin.",
        "body_ru": "Посев медоносов-конвейеров позволяет полностью закрыть безвзяточные окна и получать до 500 кг товарного мёда с гектара."
    },
    {
        "id": 7,
        "title_kr": "👑 Она ариларни сунъий уруғлантириш (ИО) лабораториялари тармоғи кенгаймоқда",
        "title_lat": "👑 Ona arilarni sun'iy urug'lantirish (IO) laboratoriyalari kengaymoqda",
        "title_ru": "👑 Искусственное осеменение пчелиных маток (ИО): 100% контроль генетики!",
        "source": "Асаларичилик Селекция Маркази",
        "date": "2026 йил",
        "category": "Селекция",
        "body_kr": (
            "Эндиликда маҳаллий наслчиликда она ариларни микроскоп остида сунъий уруғлантириш (Инструментальное Осеменение) кенг қўлланмоқда.\n\n"
            "📌 Натижалар:\n"
            "• Бегона чатишишлар олди тўлиқ олинади.\n"
            "• Тинч, чақмайдиган ва сермаҳсул Карника ва Бакфаст оилалари яратилмоқда."
        ),
        "body_lat": "Sun'iy urug'lantirish (IO) yordamida nasldor, chaqmaydigan va ko'p asal beruvchi ona arilar yetishtirilmoqda.",
        "body_ru": "Инструментальное осеменение гарантирует чистоту породы, устойчивость к болезням и высокую продуктивность пчелосемей."
    },
    {
        "id": 8,
        "title_kr": "🛡 Қишловда уяларни вентиляция қилиш ва намликни йўқотиш бўйича янги тавсиялар",
        "title_lat": "🛡 Qishlovda uyalarni shamollatish va namlikni yo'qotish bo'yicha tavsiyalar",
        "title_ru": "🛡 Вентиляция ульев зимой: Как защитить пчёл от сырости и плесени!",
        "source": "Канада ва Скандинавия Асаларичилик Тажрибаси",
        "date": "2026 йил",
        "category": "Қишлов",
        "body_kr": (
            "Арилар совуқдан эмас, уя ичидаги намлик ва димликдан ҳалок бўлади. Олимлар уяларнинг тўр туби (сетчатое дно) орқали пастки вентиляцияни тавсия этмоқда.\n\n"
            "📌 Муҳим қоидалар:\n"
            "• Тўр туб уяда конденсация ҳосил бўлишига йўл қўймайди.\n"
            "• Клуб қуруқ муҳитда озуқани 20% кам сарфлайди ва ичи сурилмайди."
        ),
        "body_lat": "Arilar sovuqdan emas, namlikdan nobud bo'ladi. To'r tub (setkali taglik) uyani quruq saqlashning eng yaxshi vositasidir.",
        "body_ru": "Сетчатое дно обеспечивает отвод влаги и углекислого газа, снижая потребление корма и предупреждая нозематоз зимой."
    },
    {
        "id": 9,
        "title_kr": "🐝 Прополиснинг янги антиоксидант хусусиятлари тиббиётда катта эътирофга сазовор бўлди",
        "title_lat": "🐝 Propolisning yangi antioksidant xususiyatlari tibbiyotda e'tirof etildi",
        "title_ru": "🐝 Медицинские исследования подтвердили уникальные свойства прополиса против бактерий",
        "source": "Халқаро Апитерапия Ассоциацияси",
        "date": "2026 йил",
        "category": "Апитерапия",
        "body_kr": (
            "Тоғ ва тўқайларда арилар томонидан тераклардан йиғилган табиий прополис сунъий антибиотикларга чидамли бактерияларни 99% га йўқ қилиши исботланди.\n\n"
            "📌 Натижа:\n"
            "Апитерапия маҳсулотлари, айниқса спиртли ва сувли прополис экстрактларига талаб 60% га кўтарилди."
        ),
        "body_lat": "Propolis ekstraktlari sintetik antibiotiklarga qarshi chidamli mikroblarni ham samarali yo'q qilishi ilmiy isbotlandi.",
        "body_ru": "Природный прополис доказал высокую эффективность против устойчивых бактерий, что вызвало резкий рост спроса на экстракты."
    },
    {
        "id": 10,
        "title_kr": "📈 Баҳорги ривожланишни тезлаштириш: Канди ва сиропга табиий фитонцидлар қўшиш самараси",
        "title_lat": "📈 Bahorgi rivojlanishni tezlashtirish: Shiraga tabiiy ekstraktlar qo'shish samarasi",
        "title_ru": "📈 Весенний старт пасеки: Стимулирующие подкормки с фитонцидами",
        "source": "Практик Асаларичилик Журнали",
        "date": "2026 йил",
        "category": "Баҳорги Парвариш",
        "body_kr": (
            "Эрта баҳорда она ари тухум қўйишини рағбатлантириш учун шакар сиропига табиий фитонцидлар (қалампирмунчоқ, саримсоқ экстракти) қўшиш оилалар ривожини 2 ҳафтага олдинга суради.\n\n"
            "📌 Тавсия:\n"
            "Бу усул баҳорги нозематознинг олдини олади ва ариларнинг ичакларини тўлиқ дезинфекция қилади."
        ),
        "body_lat": "Bahorda fitontsidlar qo'shilgan ozuqa berish ona ari tuxum qo'yishini 2 barobar tezlashtiradi va ich ketishni oldini oladi.",
        "body_ru": "Весенняя подкормка с фитоэкстрактами стимулирует яйцекладку матки и надёжно санирует кишечник пчёл."
    }
]

# 100 та асаларичилик янгиликлари тўпламини юклаш
try:
    from bee_news_collection import generate_100_bee_news
    BEE_GLOBAL_NEWS = generate_100_bee_news()
except Exception as _e_news:
    logging.warning(f"Error loading bee_news_collection: {_e_news}")

def format_bee_news_post(item, lang="uz_kr"):
    cfg_script = get_system_setting("news_script", "uz_kr")
    active_lang = lang if lang in ["uz_kr", "uz_lat", "ru", "en"] else cfg_script
    
    title = item.get("title_kr" if active_lang=="uz_kr" else ("title_lat" if active_lang=="uz_lat" else "title_ru"))
    body = item.get("body_kr" if active_lang=="uz_kr" else ("body_lat" if active_lang=="uz_lat" else "body_ru"))
    source = item.get("source", "Asalarichilik.Uz")
    date_str = item.get("date", "2026")
    
    header = "📰 <b>АСАЛАРИЧИЛИК ДУНЁСИ ЯНГИЛИГИ</b>" if active_lang not in ["ru", "en"] else ("📰 <b>МИРОВЫЕ НОВОСТИ ПЧЕЛОВОДСТВА</b>" if active_lang == "ru" else "📰 <b>GLOBAL BEEKEEPING NEWS</b>")
    src_lbl = "🌐 <b>Манба:</b>" if active_lang not in ["ru", "en"] else ("🌐 <b>Источник:</b>" if active_lang == "ru" else "🌐 <b>Source:</b>")
    tag_lbl = "🏷 <b>Теглар:</b>" if active_lang not in ["ru", "en"] else ("🏷 <b>Теги:</b>" if active_lang == "ru" else "🏷 <b>Tags:</b>")
    
    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    
    footer = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐝 <b>Расмий канал:</b> {chan}\n"
        f"👥 <b>Асаларичилик гуруҳи:</b> {grp}\n"
        f"📺 <b>YouTube:</b> {yt}\n"
        f"🤖 <b>Бот:</b> @{BOT_USERNAME}"
    )
    
    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>{title}</b>\n\n"
        f"{body}\n\n"
        f"{src_lbl} <i>{source} ({date_str})</i>\n"
        f"{tag_lbl} #Асаларичилик #Янгилик #Инновация #AsalarichilikUz\n"
        f"{footer}"
    )

def show_bee_news_hub(chat_id, news_idx=0, message_id=None, lang="uz_kr"):
    total_news = len(BEE_GLOBAL_NEWS)
    if news_idx < 0: news_idx = 0
    if news_idx >= total_news: news_idx = total_news - 1
    
    cfg_script = get_system_setting("news_script", "uz_kr")
    active_lang = lang if lang in ["uz_kr", "uz_lat", "ru", "en"] else cfg_script
    
    item = BEE_GLOBAL_NEWS[news_idx]
    preview_txt = format_bee_news_post(item, active_lang)
    
    script_badge = "🟢 Кириллча (Ўзб)" if active_lang == "uz_kr" else "🔵 Lotincha (O'zb)"
    news_dest = get_system_setting("news_target_scope", "both")
    dest_lbl = {"both": "Канал + Гуруҳларга", "channels": "Фақат Каналларга", "groups": "Фақат Гуруҳларга"}.get(news_dest, "Канал + Гуруҳларга")
    
    markup = InlineKeyboardMarkup()
    # 1. Тўғридан-тўғри манзилга юбориш тугмалари
    markup.row(
        InlineKeyboardButton("📢 Каналга юбориш", callback_data=f"pub_bee_news_chan_{news_idx}"),
        InlineKeyboardButton("👥 Гуруҳга юбориш", callback_data=f"pub_bee_news_grp_{news_idx}")
    )
    markup.row(InlineKeyboardButton("🌐 Канал ва Гуруҳга (Иккаласига) 📌", callback_data=f"pub_bee_news_{news_idx}"))
    markup.row(InlineKeyboardButton("📣 Реклама менюсига тўғридан-тўғри ўтказиш 🚀", callback_data=f"draft_to_ad_news_{news_idx}"))
    
    nav_btns = []
    if news_idx > 0:
        nav_btns.append(InlineKeyboardButton("⬅️ Олдингиси", callback_data=f"view_bee_news_{news_idx - 1}"))
    nav_btns.append(InlineKeyboardButton(f"📄 {news_idx + 1} / {total_news}", callback_data="noop"))
    if news_idx < total_news - 1:
        nav_btns.append(InlineKeyboardButton("Кейингиси ➡️", callback_data=f"view_bee_news_{news_idx + 1}"))
    if nav_btns:
        markup.row(*nav_btns)
        
    markup.row(
        InlineKeyboardButton(f"🔤 Ёзув тури: {script_badge}", callback_data="toggle_news_script"),
        InlineKeyboardButton("🎲 Тасодифий янгилик", callback_data="rand_bee_news")
    )
    markup.row(
        InlineKeyboardButton(f"⚙️ Манзил созламаси: {dest_lbl}", callback_data="open_dest_settings")
    )
    markup.row(InlineKeyboardButton("« Реклама ва постлар менюсига қайтиш", callback_data="bc_menu"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
    
    hub_text = (
        f"🌐 <b>ИНТЕРНЕТ АСАЛАРИЧИЛИК ЯНГИЛИКЛАРИ МАРКАЗИ (100+ МАҚОЛА)</b>\n\n"
        f"Бу бўлим интернет тармоқларидан асаларичиликка оид илмий янгиликлар ва замонавий технологияларни топиб, ўзбек тилига таржима қилади.\n\n"
        f"• 🔤 <b>Жорий ёзув тури:</b> <code>{script_badge}</code>\n"
        f"• 🎯 <b>Авто-юбориш манзили:</b> <code>{dest_lbl}</code>\n"
        f"• 📄 <b>Жами янгиликлар сони:</b> <b>{total_news}</b> та\n\n"
        f"<i>💡 <b>Тезкор ҳаракатлар:</b> Сиз ушбу янгиликни текшириб, <b>«Каналга»</b>, <b>«Гуруҳга»</b> ёки <b>«Иккаласига»</b> юборишингиз, ёхуд <b>«📣 Реклама менюсига ўтказиш»</b> тугмаси орқали пост конструкторига ўтказиб эркин тарқатишингиз мумкин!</i>\n\n"
        f"{preview_txt}"
    )
    safe_edit_or_send(chat_id, message_id, hub_text, markup)

def publish_bee_news(news_idx, admin_user_id=None, target_scope="both", pin=True):
    if news_idx < 0 or news_idx >= len(BEE_GLOBAL_NEWS):
        news_idx = 0
    item = BEE_GLOBAL_NEWS[news_idx]
    cfg_script = get_system_setting("news_script", "uz_kr")
    
    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    c_clean = chan.replace("@", "")
    g_clean = grp.replace("@", "").replace("https://t.me/", "")
    g_url = grp if grp.startswith("http") else f"https://t.me/{g_clean}"
    
    news_markup = get_post_buttons_markup(content_type="news", content_id=f"news_{item.get('id', news_idx)}", share_text=item.get("title_kr") or item.get("title_lat", "Asalarichilik"))
    
    sent_cnt = 0
    sent_channel_ids = set()
    sent_group_ids = set()

    # 1. Каналларга юбориш (Фақат каналларга)
    if target_scope in ["both", "channels"]:
        cursor.execute("SELECT chat_id, title, username FROM channels")
        active_channels = cursor.fetchall()
        for ch in active_channels:
            cid = ch["chat_id"]
            if cid in sent_channel_ids:
                continue
            sent_channel_ids.add(cid)
            post_txt = format_bee_news_post(item, cfg_script)
            try:
                sent_msg = bot.send_message(cid, post_txt, parse_mode="HTML", reply_markup=news_markup)
                if pin:
                    try:
                        bot.pin_chat_message(cid, sent_msg.message_id, disable_notification=False)
                    except Exception as pe:
                        logging.info(f"Pin news in channel {cid} error: {pe}")
                sent_cnt += 1
                time.sleep(0.05)
            except Exception as e:
                logging.warning(f"Send news to channel {cid} error: {e}")

    # 2. Гуруҳларга юбориш (Канал ID ларини мутлақо чиқариб ташлаймиз ва бир марта юборамиз)
    if target_scope in ["both", "groups"]:
        cursor.execute("SELECT chat_id, title, lang FROM groups WHERE is_authorized = 1 AND chat_id NOT IN (SELECT chat_id FROM channels)")
        active_groups = cursor.fetchall()
        for g in active_groups:
            gid = g["chat_id"]
            # Агар бу ID аллақачон канал рўйхатида бўлса ёки юборилган бўлса, такроран юбормаймиз
            if gid in sent_group_ids or gid in sent_channel_ids:
                continue
            sent_group_ids.add(gid)
            g_lang = g.get("lang", cfg_script)
            post_txt = format_bee_news_post(item, g_lang)
            try:
                sent_msg = bot.send_message(gid, post_txt, parse_mode="HTML", reply_markup=news_markup)
                if pin:
                    try:
                        bot.pin_chat_message(gid, sent_msg.message_id, disable_notification=False)
                    except Exception as pe:
                        logging.info(f"Pin news in group {gid} error: {pe}")
                sent_cnt += 1
                time.sleep(0.05)
            except Exception as e:
                logging.warning(f"Send news to group {gid} error: {e}")

    return sent_cnt

def publish_bee_news_to_all_groups(news_idx, admin_user_id):
    return publish_bee_news(news_idx, admin_user_id, target_scope="both", pin=True)

# ==================== АСАЛАРИЧИЛИК ВИКТОРИНАЛАРИ ВА СЎРОВНОМАЛАРИ (ОПРОС) МАРКАЗИ ====================
BEEKEEPING_QUIZZES = [
    {
        "id": 1,
        "category": "junior",
        "question_kr": "Асаларилар қайси рангни кўра олмайди? 🐝",
        "question_lat": "Asalarilar qaysi rangni ko'ra olmaydi? 🐝",
        "question_ru": "Какой цвет пчёлы не способны видеть? 🐝",
        "options_kr": ["Кўк", "Қизил", "Яшил"],
        "options_lat": ["Ko'k", "Qizil", "Yashil"],
        "options_ru": ["Синий", "Красный", "Зелёный"],
        "correct_id": 1,
        "explanation_kr": "Асаларилар қизил рангни кўра олмайди (уларга қора бўлиб кўринади), аммо инсон кўзига кўринмайдиган ультрабинафша нурларни жуда аниқ кўради.",
        "explanation_lat": "Asalarilar qizil rangni ko'ra olmaydi (ularga qora bo'lib ko'rinadi), ammo ultrabinafsha nurlarni juda yaxshi ko'radi.",
        "explanation_ru": "Пчёлы не воспринимают красный цвет (он кажется им чёрным), однако они отлично видят невидимый для человека ультрафиолет."
    },
    {
        "id": 2,
        "category": "junior",
        "question_kr": "Асаларининг танасида қанча оёқ бор? 🐝",
        "question_lat": "Asalarining tanasida qancha oyoq bor? 🐝",
        "question_ru": "Сколько ног у медоносной пчелы? 🐝",
        "options_kr": ["4 та", "8 та", "6 та"],
        "options_lat": ["4", "8", "6"],
        "options_ru": ["4", "8", "6"],
        "correct_id": 2,
        "explanation_kr": "Барча ҳашаротлар сингари асаларининг кўкрак қисмида 3 жуфт, яъни жами 6 та бўғимли оёғи бор.",
        "explanation_lat": "Barcha hasharotlar kabi asalarining ham ko'krak qismida 3 juft, ya'ni jami 6 ta oyog'i bor.",
        "explanation_ru": "У пчелы, как и у всех насекомых, 3 пары сочленённых ног на грудном сегменте, то есть всего 6 ног."
    },
    {
        "id": 3,
        "category": "junior",
        "question_kr": "Она ари (ona ari) бир кеча-кундузда ўртача нечта тухум қўйиши мумкин?",
        "question_lat": "Ona ari bir kecha-kunduzda o'rtacha nechta tuxum qo'yishi mumkin?",
        "question_ru": "Сколько яиц в сутки может откладывать плодная матка в пик сезона?",
        "options_kr": ["1500 - 2500 тагача", "500 тагача", "10 000 та"],
        "options_lat": ["1500 - 2500 tagacha", "500 tagacha", "10 000 ta"],
        "options_ru": ["1500 - 2500", "До 500", "10 000"],
        "correct_id": 0,
        "explanation_kr": "Баҳор ва ёз авжида кучли оиланинг ёш она ариси бир кеча-кундузда 2000-2500 тагача тухум қўя олади.",
        "explanation_lat": "Bahor va yoz avjida kuchli oilaning yosh ona arisi bir sutkada 2000-2500 tagacha tuxum qo'yishi mumkin.",
        "explanation_ru": "В разгар весенне-летнего развития качественная плодная матка откладывает от 1500 до 2500 яиц в сутки."
    },
    {
        "id": 4,
        "category": "junior",
        "question_kr": "Уяда она ари тухум қўйилгандан сўнг неча кунда етилиб чиқади?",
        "question_lat": "Uyada ona ari tuxum qo'yilgandan so'ng necha kunda yetilib chiqadi?",
        "question_ru": "Через сколько дней после откладки яйца выходит матка?",
        "options_kr": ["21 кунда", "16 кунда", "24 кунда"],
        "options_lat": ["21 kunda", "16 kunda", "24 kunda"],
        "options_ru": ["21 день", "16 дней", "24 дня"],
        "correct_id": 1,
        "explanation_kr": "Она ари ривожланиши энг тез бўлиб 16 кун давом этади. Ишчи ари 21 кунда, трутень эса 24 кунда чиқади.",
        "explanation_lat": "Ona ari 16 kunda, ishchi ari 21 kunda, erkak ari (truten) esa 24 kunda rivojlanib chiqadi.",
        "explanation_ru": "Матка развивается всего 16 дней, рабочая пчела — 21 день, а трутень — 24 дня."
    },
    {
        "id": 5,
        "category": "junior",
        "question_kr": "Эркак ари (трутень) одамни чақа оладими?",
        "question_lat": "Erkak ari (truten) odamni chaqa oladimi?",
        "question_ru": "Может ли трутень ужалить человека?",
        "options_kr": ["Ҳа, фақат хавф туғилганда", "Ҳа, фақат кузда", "Йўқ, ниши умуман йўқ"],
        "options_lat": ["Ha, faqat xavf tug'ilganda", "Ha, faqat kuzda", "Yo'q, nishi umuman yo'q"],
        "options_ru": ["Да, при опасности", "Да, только осенью", "Нет, у него нет жала"],
        "correct_id": 2,
        "explanation_kr": "Эркак ариларда ниш бўлмайди, чунки ниш фақат урғочи ариларда тухум қўйиш аъзосининг ўзгаришидан ҳосил бўлган.",
        "explanation_lat": "Erkak arilarda nish bo'lmaydi, chunki nish faqat urg'ochi arilarda bo'ladi.",
        "explanation_ru": "У трутней жало отсутствует анатомически, так как жало — это видоизменённый яйцеклад самок."
    },
    {
        "id": 6,
        "category": "junior",
        "question_kr": "Асалариларнинг нечта қаноти бор?",
        "question_lat": "Asalarilarning nechta qanoti bor?",
        "question_ru": "Сколько крыльев у медоносной пчелы?",
        "options_kr": ["4 та (2 жуфт)", "2 та", "6 та"],
        "options_lat": ["4 ta (2 juft)", "2 ta", "6 ta"],
        "options_ru": ["4 крыла (2 пары)", "2 крыла", "6 крыльев"],
        "correct_id": 0,
        "explanation_kr": "Асаларининг 4 та қаноти бор. Парвоз вақтида олдинги ва орқа қанотлар майда илмоқчалар орқали битта текисликка бирикади.",
        "explanation_lat": "Asalarining 4 ta qanoti bor bo'lib, parvozda ilgaklar bilan birlashadi.",
        "explanation_ru": "У пчелы 4 крыла (две пары), соединяющиеся в полёте особыми микрозацепками в единую плоскость."
    },
    {
        "id": 7,
        "category": "junior",
        "question_kr": "Ишчи асаларининг ёздаги ўртача умри қанча?",
        "question_lat": "Ishchi asalarining yozdagi o'rtacha umri qancha?",
        "question_ru": "Какова средняя продолжительность жизни рабочей пчелы летом?",
        "options_kr": ["6 ой", "35 - 45 кун", "1 йил"],
        "options_lat": ["6 oy", "35 - 45 kun", "1 yil"],
        "options_ru": ["6 месяцев", "35 - 45 дней", "1 год"],
        "correct_id": 1,
        "explanation_kr": "Ёзда фаол нектар йиғиш ва личинка боқиш туфайли ишчи ариларнинг қанотлари ва мушаклари тез ейилиб, ўртача 35-45 кун яшайди.",
        "explanation_lat": "Yozda faol nektar yig'ish tufayli ishchi arilar 35-45 kun yashaydi.",
        "explanation_ru": "Летом при интенсивной работе по сбору нектара пчёлы изнашиваются за 35-45 дней."
    },
    {
        "id": 8,
        "category": "junior",
        "question_kr": "Асаларилар асалдан ташқари уяга оқсил манбаи сифатида нима йиғади?",
        "question_lat": "Asalarilar asaldan tashqari uyaga oqsil manbai sifatida nima yig'adi?",
        "question_ru": "Что пчёлы собирают с цветов в качестве источника белка?",
        "options_kr": ["Фақат сув", "Дарахт барглари", "Гулчанги (обножка/перга)"],
        "options_lat": ["Faqat suv", "Daraxt barglari", "Gulchangi (obnojka/perga)"],
        "options_ru": ["Только воду", "Листья растений", "Пыльцу (обножку/пергу)"],
        "correct_id": 2,
        "explanation_kr": "Гулчанги арилар учун оқсил, витамин ва ёғлар манбаи бўлиб, личинка боқиш ва ёш арилар ривожланиши учун ҳаётий зарурдир.",
        "explanation_lat": "Gulchangi arilar uchun oqsil va vitamin manbai bo'lib, lichinka boqishda ishlatiladi.",
        "explanation_ru": "Пыльца (перга) является незаменимым источником белка и витаминов для выкармливания расплода."
    },
    {
        "id": 9,
        "category": "junior",
        "question_kr": "Асал пишган ва олишга тайёр эканлигини қандай билиш мумкин?",
        "question_lat": "Asal pishgan va olishga tayyor ekanligini qanday bilish mumkin?",
        "question_ru": "Как определить, что мёд в сотах зрелый и готов к откачке?",
        "options_kr": ["Ром тўлиқ очиқ бўлганда", "Ромнинг камида 2/3 қисми мум билан ёпилган (сирланган)", "Ранги қорайганда"],
        "options_lat": ["Rom to'liq ochiq bo'lganda", "Romning kamida 2/3 qismi mum bilan yopilgan bo'lsa", "Rangi qorayganda"],
        "options_ru": ["Соты полностью открыты", "Рамка запечатана воском минимум на 2/3", "Цвет мёда потемнел"],
        "correct_id": 1,
        "explanation_kr": "Арилар намлик 18-20% дан пасайгандагина катакчаларни мум қопқоқ билан ёпади (запечатывают). Бундай асал ачимайди ва йиллар давомида сифатини сақлайди.",
        "explanation_lat": "Arilar namlik 18-20% dan tushganda katakchalarni mum bilan yopadi.",
        "explanation_ru": "Запечатывание сотов восковыми крышечками говорит о том, что влажность мёда упала ниже 20% и он созрел."
    },
    {
        "id": 10,
        "category": "junior",
        "question_kr": "Асалари уясида ари сути (маточной молочко) билан қайси ари умрбод боқилади?",
        "question_lat": "Asalari uyasida ari suti (matoniy molochko) bilan qaysi ari umrbod boqiladi?",
        "question_ru": "Какая особь в пчелиной семье всю жизнь питается маточным молочком?",
        "options_kr": ["Она ари (ona ari)", "Эркак ари (трутень)", "Қоровул ари"],
        "options_lat": ["Ona ari", "Erkak ari", "Qorovul ari"],
        "options_ru": ["Матка", "Трутень", "Пчела-сторож"],
        "correct_id": 0,
        "explanation_kr": "Она ари ҳаёти давомида фақат озуқавий қиймати тенгсиз бўлган ари сути билан боқилади.",
        "explanation_lat": "Ona ari hayoti davomida faqat ari suti bilan boqiladi.",
        "explanation_ru": "Пчелиная матка на протяжении всей своей жизни питается исключительно маточным молочком."
    },
    {
        "id": 11,
        "category": "specialist",
        "question_kr": "Вароа (Varroa destructor) канаси қайси насл катакчаларида 2 баробар кўпроқ кўпаяди?",
        "question_lat": "Varroa kanasi qaysi nasl katakchalarida 2 barobar ko'proq ko'payadi?",
        "question_ru": "В расплоде каких особей клещ варроа размножается в 2 раза активнее?",
        "options_kr": ["Ишчи ари наслида", "Эркак ари (трутень) наслида", "Она ари косачасида"],
        "options_lat": ["Ishchi ari naslida", "Erkak ari (truten) naslida", "Ona ari kosachasida"],
        "options_ru": ["В пчелином расплоде", "В трутнёвом расплоде", "В маточниках"],
        "correct_id": 1,
        "explanation_kr": "Трутень личинкаси 24 кунда етилиши ва ҳажми катталиги сабабли урғочи кана трутень катакчасида кўпроқ насл қолдиради.",
        "explanation_lat": "Truten katakchasi katta va 24 kunda yetilgani uchun kana unda 2 barobar ko'p ko'payadi.",
        "explanation_ru": "Из-за более длительного развития трутня (24 дня) самка варроа успевает оставить вдвое больше зрелого потомства."
    },
    {
        "id": 12,
        "category": "specialist",
        "question_kr": "Рояланиш кайфиятини бартараф этувчи 'Демари' (Demaree) усулининг асоси нима?",
        "question_lat": "Roylanishni oldini oluvchi 'Demari' usulining asosi nima?",
        "question_ru": "В чём заключается противороевой приём Демари (Demaree)?",
        "options_kr": ["Она арини дарҳол ўлдириш", "Уяни тўлиқ қоронғи жойга қўйиш", "Она арини пастки корпусда панжара остида қолдириб, ёпиқ наслни юқорига кўтариш"],
        "options_lat": ["Ona arini o'ldirish", "Uyani qorong'u joyga qo'yish", "Ona arini pastki korpusda panjara ostida qoldirib, yopiq naslni yuqoriga ko'tarish"],
        "options_ru": ["Уничтожение матки", "Затемнение улья", "Изоляция матки внизу с открытым расплодом и подъём печатного расплода наверх"],
        "correct_id": 2,
        "explanation_kr": "Демари усулида она ари ва 1 та очиқ наслли ром пастки корпусда ганеман панжараси остида қолдирилади, барча ёпиқ насл эса юқорига чиқарилиб уя кенгайтирилади.",
        "explanation_lat": "Demari usulida ona ari pastki korpusda qoldirilib, yopiq nasl yuqori korpusga ko'tariladi.",
        "explanation_ru": "Приём Демари имитирует выход роя: матка остаётся внизу с вощиной под решёткой, а печатный расплод поднимается в верхний корпус."
    },
    {
        "id": 13,
        "category": "specialist",
        "question_kr": "Шовул (щавелевая) кислотаси сублимацияси қайси даврда 98-99% самара беради?",
        "question_lat": "Shovul kislotasi sublimatsiyasi qaysi davrda 98-99% samara beradi?",
        "question_ru": "В какой период сублимация щавелевой кислоты даёт максимальный эффект (до 99%)?",
        "options_kr": ["Уяда насл (расплод) бўлмаган даврда (куз охири / эрта баҳор)", "Асосий ёзги нектар йиғимида", "Кундузи +35°C иссиқда"],
        "options_lat": ["Uyada nasl (rasplod) bo'lmagan davrda (kuz oxiri / erta bahor)", "Yozgi asal yig'imida", "+35°C issiqda"],
        "options_ru": ["В безрасплодный период (поздняя осень / ранняя весна)", "Во время главного взятка", "В жаркий полдень при +35°C"],
        "correct_id": 0,
        "explanation_kr": "Шовул кислотаси ёпиқ насл ичидаги канага таъсир қилолмайди. Уяда насл бўлмаган пайтда барча каналар арилар устида очиқ бўлиб, 99% нобуд бўлади.",
        "explanation_lat": "Shovul kislotasi nasl yo'q paytda 99% kanani yo'q qiladi, chunki barcha kanalar ari ustida bo'ladi.",
        "explanation_ru": "Щавелевая кислота не проникает под крышечки расплода, поэтому 99% эффективность достигается только при отсутствии печатного расплода."
    },
    {
        "id": 14,
        "category": "specialist",
        "question_kr": "Сунъий она ари етиштиришда кўчириб ўтказиладиган личинкалар ёши неча соатлик бўлиши шарт?",
        "question_lat": "Sun'iy ona ari yetishtirishda ko'chiriladigan lichinkalar yoshi necha soatlik bo'lishi shart?",
        "question_ru": "Каков оптимальный возраст личинки при прививке для вывода маток?",
        "options_kr": ["72 соатлик (3 кунлик)", "12 - 24 соатлик (1 кунгача)", "5 кунлик"],
        "options_lat": ["72 soatlik (3 kunlik)", "12 - 24 soatlik (1 kungacha)", "5 kunlik"],
        "options_ru": ["72 часа (3 дня)", "12 - 24 часа (до 1 суток)", "5 суток"],
        "correct_id": 1,
        "explanation_kr": "Юқори сифатли, кўп тухум қўювчи она ари етиштириш учун личинкалар 12-24 соатликдан катта бўлмаслиги керак.",
        "explanation_lat": "Sifatli ona ari yetishtirish uchun lichinkalar 12-24 soatlik bo'lishi shart.",
        "explanation_ru": "Личинки старше суток получают меньше маточного молочка и дают маток с меньшим числом яйцевых трубочек."
    },
    {
        "id": 15,
        "category": "specialist",
        "question_kr": "Она арининг 'Тинч алмашинуви' (тихая смена) косачалари одатда қаерда қурилади?",
        "question_lat": "Ona arining 'Tinch almashinuvi' (tixaya smena) kosachalari qayerda quriladi?",
        "question_ru": "Где пчёлы обычно закладывают маточники «тихой смены»?",
        "options_kr": ["Ром четларига 15-25 та косача", "Фақат уя тубига", "Ром ўртасидаги насл орасига 1-3 та косача"],
        "options_lat": ["Rom chetlariga 15-25 ta kosacha", "Faqat uya tubiga", "Rom o'rtasidagi nasl orasiga 1-3 ta kosacha"],
        "options_ru": ["По краям сотов 15-25 штук", "На дне улья", "В центре рамки среди расплода 1-3 маточника"],
        "correct_id": 2,
        "explanation_kr": "Роя косачалари ром чеккасида кўп миқдорда бўлади, тинч алмашинувда эса арилар ром марказида бор-йўғи 1-3 та йирик маточник қуради.",
        "explanation_lat": "Tinch almashinuvda arilar rom o'rtasida 1-3 ta sifatli kosacha quradi.",
        "explanation_ru": "При тихой смене пчёлы закладывают всего 1-3 крупных маточника в центре гнезда на расплоде, в отличие от десятков роевых по краям."
    },
    {
        "id": 16,
        "category": "specialist",
        "question_kr": "Табиий асалнинг намлиги халқаро стандарт (ГОСТ) бўйича неча фоиздан ошмаслиги лозим?",
        "question_lat": "Tabiiy asalning namligi xalqaro standart bo'yicha necha foizdan oshmasligi lozim?",
        "question_ru": "Какова предельная норма влажности натурального мёда по ГОСТу и мировым стандартам?",
        "options_kr": ["18 - 20% дан ошмаслиги керак", "25% бўлиши керак", "30% бўлиши керак"],
        "options_lat": ["18 - 20% dan oshmasligi kerak", "25% bo'lishi kerak", "30% bo'lishi kerak"],
        "options_ru": ["Не более 18 - 20%", "25%", "30%"],
        "correct_id": 0,
        "explanation_kr": "Халқаро стандартга кўра пишган сифатли асал намлиги 18-20% дан ошмаслиги шарт. 20% дан ошса асал тез ачийди.",
        "explanation_lat": "Sifatli asal namligi 18-20% dan oshmasligi lozim, aks holda achib qoladi.",
        "explanation_ru": "Зрелый мёд содержит не более 18-20% воды. При большей влажности активизируются дрожжи и мёд закисает."
    },
    {
        "id": 17,
        "category": "specialist",
        "question_kr": "Чумоли (муравьиная) кислотаси ҳарорат неча даража бўлганда қўлланиши хавфсиз?",
        "question_lat": "Chumoli kislotasi harorat necha daraja bo'lganda qo'llanishi xavfsiz?",
        "question_ru": "При какой температуре наружного воздуха безопасно применять муравьиную кислоту?",
        "options_kr": ["+35°C дан юқори бўлганда", "+15°C дан +25°C гача", "0°C совуқда"],
        "options_lat": ["+35°C dan yuqori bo'lganda", "+15°C dan +25°C gacha", "0°C sovuqda"],
        "options_ru": ["Выше +35°C", "От +15°C до +25°C", "При 0°C"],
        "correct_id": 1,
        "explanation_kr": "+25°C дан юқори иссиқда чумоли кислотаси шиддат билан буғланиб, она ари ва личинкаларнинг заҳарланишига сабаб бўлади.",
        "explanation_lat": "+25°C dan yuqorida chumoli kislotasi tez bug'lanib ona ari va lichinkalarni zaharlashi mumkin.",
        "explanation_ru": "При температуре выше +25°C скорость испарения резко возрастает, что приводит к гибели матки и расплода."
    },
    {
        "id": 18,
        "category": "specialist",
        "question_kr": "Ари уяларидаги эски қорайган мум ромларни йилига неча фоизга янгилаш лозим?",
        "question_lat": "Ari uyalaridagi eski qoraygan mum romlarni yiliga necha foizga yangilash lozim?",
        "question_ru": "Какой процент старых тёмных сотов рекомендуется выбраковывать и обновлять ежегодно?",
        "options_kr": ["10 йилда бир марта", "Фақат синганда", "Камида 30 - 35% қисмини"],
        "options_lat": ["10 yilda bir marta", "Faqat singanda", "Kamida 30 - 35% qismini"],
        "options_ru": ["Раз в 10 лет", "Только при поломке", "Не менее 30 - 35%"],
        "correct_id": 2,
        "explanation_kr": "Қорайган ромларда катак ҳажми кичрайиб арилар майдалашади ва касаллик споралари сақланади. Йилига учдан бир қисмини вощинага алмаштириш шарт.",
        "explanation_lat": "Qoraygan romlarda arilar maydalashadi, shuning uchun yiliga 30-35% romlar yangilanadi.",
        "explanation_ru": "Ежегодная замена минимум трети гнезда на свежую вощину гарантирует крупный размер выводимых пчёл и снижает инфекционный фон."
    }
]

def get_all_bee_quizzes(cat_filter="all"):
    quizzes = list(BEEKEEPING_QUIZZES)
    try:
        cursor.execute("SELECT * FROM custom_bee_quizzes ORDER BY id ASC")
        rows = cursor.fetchall()
        for r in rows:
            opts = json.loads(r["options_json"]) if r["options_json"] else ["A", "B", "C"]
            quizzes.append({
                "id": 1000 + r["id"],
                "category": r.get("category", "junior"),
                "question_kr": r.get("question_kr") or r.get("question_lat"),
                "question_lat": r.get("question_lat") or r.get("question_kr"),
                "question_ru": r.get("question_ru") or r.get("question_kr"),
                "options_kr": opts,
                "options_lat": opts,
                "options_ru": opts,
                "correct_id": r.get("correct_id", 0),
                "explanation_kr": r.get("explanation_kr", ""),
                "explanation_lat": r.get("explanation_lat", ""),
                "explanation_ru": r.get("explanation_ru", "")
            })
    except Exception as e:
        logging.warning(f"Error fetching custom quizzes: {e}")

    if cat_filter in ["junior", "specialist"]:
        filtered = [q for q in quizzes if q.get("category") == cat_filter]
        return filtered if filtered else quizzes
    return quizzes

def get_global_quiz_config():
    try:
        cursor.execute("SELECT * FROM global_quiz_config WHERE id = 1")
        cfg = cursor.fetchone()
        if cfg:
            return cfg
    except Exception:
        pass
    return {
        "enabled": 1,
        "send_time": "10:00",
        "repeat_days": "1,2,3,4,5,6,7",
        "delete_hours": 0,
        "auto_pin": 1,
        "target_scope": "both",
        "category_filter": "all",
        "last_sent_date": "",
        "current_index": 0
    }

def update_global_quiz_config(**kwargs):
    if not kwargs:
        return
    sets = []
    vals = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    query = f"UPDATE global_quiz_config SET {', '.join(sets)} WHERE id = 1"
    cursor.execute(query, tuple(vals))
    conn.commit()

def show_quiz_hub(chat_id, quiz_idx=0, message_id=None, lang="uz_kr"):
    cfg = get_global_quiz_config()
    cat_filter = cfg.get("category_filter", "all")
    all_quizzes = get_all_bee_quizzes(cat_filter)
    total_q = len(all_quizzes)
    if quiz_idx < 0:
        quiz_idx = 0
    if quiz_idx >= total_q:
        quiz_idx = total_q - 1

    item = all_quizzes[quiz_idx]
    q_cat = item.get("category", "junior")
    cat_badge = "🟢 Ёш асаларичилар" if q_cat == "junior" else "🔴 Спец / Тажрибали"

    q_script = cfg.get("script") or get_system_setting("quiz_script", "uz_kr")
    if q_script == "uz_lat":
        q_text = item.get("question_lat") or item.get("question_kr")
        opts = item.get("options_lat") or item.get("options_kr")
        expl = item.get("explanation_lat") or item.get("explanation_kr")
        script_badge = "🔵 Lotincha (O'zb)"
    else:
        q_text = item.get("question_kr")
        opts = item.get("options_kr")
        expl = item.get("explanation_kr")
        script_badge = "🟢 Кириллча (Ўзб)"

    corr_idx = item.get("correct_id", 0)

    del_h = cfg.get("delete_hours", 0)
    del_str = "♾ Ўчирилмайди (доимий)" if del_h == 0 else f"{del_h} соатда ўчирилади"
    pin_str = "🟢 Ҳа (Қадалади 📌)" if cfg.get("auto_pin", 1) == 1 else "⚪️ Қадалмайди"
    en_str = "🟢 Ёқилган" if cfg.get("enabled", 1) == 1 else "⚪️ Ўчирилган"
    s_time = cfg.get("send_time", "10:00")
    scope_str = {"both": "📢 Канал ва Гуруҳлар", "channels": "📢 Фақат Каналлар", "groups": "👥 Фақат Гуруҳлар"}.get(cfg.get("target_scope", "both"), "📢 Канал ва Гуруҳлар")
    filter_label = {"all": "Ҳаммаси", "junior": "Ёш асаларичилар 🟢", "specialist": "Спец асаларичилар 🔴"}.get(cat_filter, "Ҳаммаси")

    opts_preview = []
    for i, opt in enumerate(opts):
        mark = "✅ " if i == corr_idx else "⚪️ "
        opts_preview.append(f"{mark}<b>{opt}</b>")
    opts_block = "\n".join(opts_preview)

    preview_block = (
        f"❓ <b>Савол:</b> {q_text}\n\n"
        f"🔘 <b>Вариантлар (Телеграм сўровнома кўринишида):</b>\n"
        f"{opts_block}\n\n"
        f"💡 <b>Изоҳ:</b> <i>{expl}</i>"
    )

    markup = InlineKeyboardMarkup()
    # 1. Тўғридан-тўғри манзилга юбориш тугмалари
    markup.row(
        InlineKeyboardButton("📢 Каналга юбориш", callback_data=f"pub_bee_quiz_chan_{quiz_idx}"),
        InlineKeyboardButton("👥 Гуруҳга юбориш", callback_data=f"pub_bee_quiz_grp_{quiz_idx}")
    )
    markup.row(InlineKeyboardButton("🌐 Канал ва Гуруҳга (Иккаласига) 📌", callback_data=f"pub_bee_quiz_{quiz_idx}"))
    markup.row(InlineKeyboardButton("📣 Реклама менюсига тўғридан-тўғри ўтказиш 🚀", callback_data=f"draft_to_ad_quiz_{quiz_idx}"))

    nav_btns = []
    if quiz_idx > 0:
        nav_btns.append(InlineKeyboardButton("⬅️ Олдинги", callback_data=f"view_bee_quiz_{quiz_idx - 1}"))
    nav_btns.append(InlineKeyboardButton(f"📄 {quiz_idx + 1} / {total_q}", callback_data="noop"))
    if quiz_idx < total_q - 1:
        nav_btns.append(InlineKeyboardButton("Кейинги ➡️", callback_data=f"view_bee_quiz_{quiz_idx + 1}"))
    if nav_btns:
        markup.row(*nav_btns)

    markup.row(
        InlineKeyboardButton(f"🎯 Тоифа: {filter_label}", callback_data="cycle_quiz_cat_filter"),
        InlineKeyboardButton(f"🔤 Ёзув: {script_badge}", callback_data="toggle_quiz_script")
    )
    markup.row(
        InlineKeyboardButton(f"⏰ Соат: {s_time}", callback_data="cycle_quiz_time"),
        InlineKeyboardButton(f"🔔 Ҳолати: {en_str}", callback_data="toggle_quiz_enabled")
    )
    markup.row(
        InlineKeyboardButton(f"⏱ Авто-ўчириш: {del_str}", callback_data="cycle_quiz_autodel"),
        InlineKeyboardButton(f"📌 Қадаш: {pin_str}", callback_data="toggle_quiz_pin")
    )
    markup.row(
        InlineKeyboardButton(f"📢 Қамров: {scope_str}", callback_data="cycle_quiz_scope"),
        InlineKeyboardButton("⚙️ Жўнатиш созламалари", callback_data="open_dest_settings")
    )
    markup.row(
        InlineKeyboardButton("« Реклама менюсига қайтиш", callback_data="bc_menu"),
        InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
    )

    hub_text = (
        f"🐝 <b>АСАЛАРИЧИЛИК ВИКТОРИНА ВА СЎРОВНОМАЛАР МАРКАЗИ 📊</b>\n\n"
        f"• 🎯 <b>Савол тоифаси:</b> {cat_badge}\n"
        f"• ⏰ <b>Кунлик юбориш вақти:</b> <code>{s_time}</code>\n"
        f"• ⏱ <b>Авто-ўчириш муддати:</b> <code>{del_str}</code>\n"
        f"• 📌 <b>Гуруҳ ва Каналларга қадаш (Pin):</b> <code>{pin_str}</code>\n"
        f"• 📢 <b>Юбориладиган жойлар:</b> {scope_str}\n"
        f"• 🔤 <b>Ёзув тури:</b> <code>{script_badge}</code>\n"
        f"• 🔔 <b>Ҳолати:</b> {en_str}\n\n"
        f"──────── ВИКТОРИНА НАМУНАСИ ────────\n"
        f"{preview_block}\n"
        f"────────────────────────────────────\n"
        f"<i>💡 <b>Тезкор ҳаракатлар:</b> Сиз ушбу викторинани текшириб, <b>«Каналга»</b>, <b>«Гуруҳга»</b> ёки <b>«Иккаласига»</b> юборишингиз, ёхуд <b>«📣 Реклама менюсига ўтказиш»</b> тугмаси орқали пост конструкторига ўтказиб реклама кўринишида тарқатишингиз мумкин!</i>"
    )
    safe_edit_or_send(chat_id, message_id, hub_text, markup)


def randomize_quiz_options(item):
    """
    Викторина жавобларини тасодифий аралаштириш.
    Тўғри жавоб доимо 1-қаторда (0-индексда) бўлиб қолмаслиги,
    2- ва 3-қаторларда ҳам бўлишини кафолатлайди.
    Барча тиллар (ўзбек кирилл, лотин, рус) бир хил тартибда алмаштирилади.
    """
    corr_idx = item.get("correct_id", 0)
    opts_kr = list(item.get("options_kr") or [])
    opts_lat = list(item.get("options_lat") or [])
    opts_ru = list(item.get("options_ru") or [])
    n = max(len(opts_kr), len(opts_lat), len(opts_ru))
    if n <= 1:
        return dict(item)

    indices = list(range(n))
    import random
    random.shuffle(indices)

    # Агар тўғри жавоб 0-ўринга (1-қаторга) тушиб қолса,
    # уни 2-чи ёки 3-чи қаторга (индекс 1 ёки 2) кўчирамиз
    curr_pos = indices.index(corr_idx)
    if curr_pos == 0 and n > 1:
        target_pos = random.choice([1, min(2, n - 1)])
        indices[0], indices[target_pos] = indices[target_pos], indices[0]

    new_corr_id = indices.index(corr_idx)
    res = dict(item)
    if opts_kr and len(opts_kr) == n:
        res["options_kr"] = [opts_kr[i] for i in indices]
    if opts_lat and len(opts_lat) == n:
        res["options_lat"] = [opts_lat[i] for i in indices]
    if opts_ru and len(opts_ru) == n:
        res["options_ru"] = [opts_ru[i] for i in indices]
    res["correct_id"] = new_corr_id
    return res

def format_quiz_share_text(q_text, opts, c_clean, g_url):
    opts_lines = "\n".join([f"🔘 {idx+1}. {opt}" for idx, opt in enumerate(opts)])
    chan_url = f"https://t.me/{c_clean}" if c_clean else "https://t.me/AsalarichilikUz"
    grp_url = g_url if g_url else "https://t.me/asalarichilik_guruhi"
    return (
        f"🐝 Асаларичилик бўйича кунлик викторина:\n\n"
        f"❓ {q_text}\n\n"
        f"{opts_lines}\n\n"
        f"👉 Тўғри жавобни билиш ва овоз бериш учун саҳифамизга қўшилинг:\n"
        f"📢 Канал: {chan_url}\n"
        f"👥 Гуруҳ: {grp_url}"
    )

def publish_quiz_poll(quiz_idx=None, admin_user_id=None, target_scope=None, auto_pin=None):
    cfg = get_global_quiz_config()
    all_quizzes = get_all_bee_quizzes(cfg.get("category_filter", "all"))
    if not all_quizzes:
        return 0

    if quiz_idx is None or quiz_idx < 0 or quiz_idx >= len(all_quizzes):
        curr_i = cfg.get("current_index", 0)
        quiz_idx = curr_i % len(all_quizzes)
        update_global_quiz_config(current_index=quiz_idx + 1)

    item = all_quizzes[quiz_idx]
    if target_scope is None:
        target_scope = cfg.get("target_scope", "both")
    if auto_pin is None:
        auto_pin = cfg.get("auto_pin", 1)
    del_hours = cfg.get("delete_hours", 0)

    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    c_clean = chan.replace("@", "")

    sent_cnt = 0
    sent_channel_ids = set()
    sent_group_ids = set()

    # 1. Каналларга юбориш (Фақат каналларга 1 марта сўровнома юборилади)
    if target_scope in ["both", "channels"]:
        cursor.execute("SELECT chat_id, title, username FROM channels")
        channels = cursor.fetchall()
        channel_ids = [ch["chat_id"] for ch in channels]
        if chan and chan not in channel_ids and not any(ch.get("username", "").lower() == c_clean.lower() for ch in channels):
            channel_ids.append(chan)

        q_script = cfg.get("script") or get_system_setting("quiz_script", "uz_kr")
        for cid in channel_ids:
            if cid in sent_channel_ids:
                continue
            sent_channel_ids.add(cid)
            # Жавоблар фақат 1-қаторда бўлмаслиги учун вариантларни аралаштирамиз
            rand_item = randomize_quiz_options(item)
            if q_script == "uz_lat":
                q_text = rand_item.get("question_lat") or rand_item.get("question_kr")
                opts = rand_item.get("options_lat") or rand_item.get("options_kr")
                expl = rand_item.get("explanation_lat") or rand_item.get("explanation_kr")
            else:
                q_text = rand_item.get("question_kr")
                opts = rand_item.get("options_kr")
                expl = rand_item.get("explanation_kr")
            corr_id = rand_item.get("correct_id", 0)
            
            # Лайк смайллари, манба ва улашиш тугмалари сўровноманинг ўзига бириктирилади (пастда алоҳида хабар бўлмайди)
            share_txt = format_quiz_share_text(q_text, opts, c_clean, g_url)
            quiz_markup = get_post_buttons_markup(content_type="quiz", content_id=str(item.get("id", quiz_idx)), share_text=share_txt)
            try:
                try:
                    poll_msg = bot.send_poll(
                        chat_id=cid,
                        question=q_text,
                        options=opts,
                        is_anonymous=True,
                        type="quiz",
                        correct_option_id=corr_id,
                        explanation=expl if expl else None,
                        explanation_parse_mode="HTML",
                        reply_markup=quiz_markup
                    )
                except Exception as e_markup:
                    logging.warning(f"send_poll with reply_markup failed in channel {cid}: {e_markup}, sending standard poll")
                    poll_msg = bot.send_poll(
                        chat_id=cid,
                        question=q_text,
                        options=opts,
                        is_anonymous=True,
                        type="quiz",
                        correct_option_id=corr_id,
                        explanation=expl if expl else None,
                        explanation_parse_mode="HTML"
                    )

                if auto_pin == 1:
                    try:
                        bot.pin_chat_message(cid, poll_msg.message_id, disable_notification=False)
                    except Exception as pe:
                        logging.warning(f"Could not pin poll in channel {cid}: {pe}")

                if del_hours > 0:
                    del_sec = del_hours * 3600
                    threading.Timer(del_sec, lambda c=cid, m=poll_msg.message_id: delete_msg_safe(c, m)).start()
                sent_cnt += 1
                time.sleep(0.05)
            except Exception as e:
                logging.warning(f"Error sending quiz poll to channel {cid}: {e}")

    # 2. Гуруҳларга юбориш (Фақат ҳақиқий гуруҳларга 1 марта сўровнома юборилади)
    if target_scope in ["both", "groups"]:
        cursor.execute("SELECT chat_id, title, lang FROM groups WHERE is_authorized = 1 AND chat_id NOT IN (SELECT chat_id FROM channels)")
        groups = cursor.fetchall()
        for g in groups:
            gid = g["chat_id"]
            if gid in sent_group_ids or gid in sent_channel_ids:
                continue
            sent_group_ids.add(gid)
            g_lang = g.get("lang", "uz_kr")
            
            # Жавоблар фақат 1-қаторда бўлмаслиги учун вариантларни аралаштирамиз
            rand_item = randomize_quiz_options(item)
            if g_lang == "ru":
                q_text = rand_item.get("question_ru") or rand_item.get("question_kr")
                opts = rand_item.get("options_ru") or rand_item.get("options_kr")
                expl = rand_item.get("explanation_ru") or rand_item.get("explanation_kr")
            elif g_lang == "uz_lat":
                q_text = rand_item.get("question_lat") or rand_item.get("question_kr")
                opts = rand_item.get("options_lat") or rand_item.get("options_kr")
                expl = rand_item.get("explanation_lat") or rand_item.get("explanation_kr")
            else:
                q_text = rand_item.get("question_kr")
                opts = rand_item.get("options_kr")
                expl = rand_item.get("explanation_kr")
            corr_id = rand_item.get("correct_id", 0)

            # Лайк смайллари, манба ва улашиш тугмаларини сўровномага тўғридан-тўғри бириктирамиз
            share_txt = format_quiz_share_text(q_text, opts, c_clean, g_url)
            quiz_markup = get_post_buttons_markup(content_type="quiz", content_id=str(item.get("id", quiz_idx)), share_text=share_txt)
            try:
                try:
                    poll_msg = bot.send_poll(
                        chat_id=gid,
                        question=q_text,
                        options=opts,
                        is_anonymous=True,
                        type="quiz",
                        correct_option_id=corr_id,
                        explanation=expl if expl else None,
                        explanation_parse_mode="HTML",
                        reply_markup=quiz_markup
                    )
                except Exception as e_gmarkup:
                    logging.warning(f"send_poll with reply_markup failed in group {gid}: {e_gmarkup}, sending standard poll")
                    poll_msg = bot.send_poll(
                        chat_id=gid,
                        question=q_text,
                        options=opts,
                        is_anonymous=True,
                        type="quiz",
                        correct_option_id=corr_id,
                        explanation=expl if expl else None,
                        explanation_parse_mode="HTML"
                    )

                if auto_pin == 1:
                    try:
                        bot.pin_chat_message(gid, poll_msg.message_id, disable_notification=False)
                    except Exception as pe:
                        logging.warning(f"Could not pin poll in group {gid}: {pe}")

                if del_hours > 0:
                    del_sec = del_hours * 3600
                    threading.Timer(del_sec, lambda c=gid, m=poll_msg.message_id: delete_msg_safe(c, m)).start()
                sent_cnt += 1
                time.sleep(0.05)
            except Exception as e:
                logging.warning(f"Error sending quiz poll to group {gid}: {e}")

    now_str = datetime.now().strftime("%Y-%m-%d")
    update_global_quiz_config(last_sent_date=now_str)
    return sent_cnt

def show_broadcast_menu(chat_id, message_id=None, lang="uz_kr"):
    cursor.execute("SELECT COUNT(*) as c FROM groups WHERE is_authorized = 1")
    g_cnt = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM channels")
    ch_cnt = cursor.fetchone()["c"]

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(InlineKeyboardButton("📝 Создать пост", callback_data="bc_create_post"))
        markup.row(
            InlineKeyboardButton("📰 Новости пчеловодства (/news)", callback_data="bc_bee_news_hub"),
            InlineKeyboardButton("🐝 Викторины & Опросы 📊", callback_data="bc_bee_quiz_hub")
        )
        markup.row(
            InlineKeyboardButton("⏳ Отложенные", callback_data="bc_delayed_list"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="bc_edit_list")
        )
        markup.row(
            InlineKeyboardButton("📊 Статистика", callback_data="bc_stats"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="bc_settings")
        )
        markup.row(InlineKeyboardButton("🚀 Рекламировать Ваш канал", callback_data="bc_promo"))
        markup.row(InlineKeyboardButton("🔎 Интересы подписчиков", callback_data="bc_interests"))
        markup.row(InlineKeyboardButton("🏠 Главное меню", callback_data="back_main"))
        txt = (
            "Здесь вы можете создавать посты, рассылать новости, викторины и управлять каналами.\n\n"
            f"• 👥 Подключено групп: <b>{g_cnt}</b>\n"
            f"• 📢 Подключено каналов: <b>{ch_cnt}</b>"
        )
    elif lang == "en":
        markup.row(InlineKeyboardButton("📝 Create Post", callback_data="bc_create_post"))
        markup.row(
            InlineKeyboardButton("📰 Beekeeping News (/news)", callback_data="bc_bee_news_hub"),
            InlineKeyboardButton("🐝 Quizzes & Polls 📊", callback_data="bc_bee_quiz_hub")
        )
        markup.row(
            InlineKeyboardButton("⏳ Scheduled", callback_data="bc_delayed_list"),
            InlineKeyboardButton("✏️ Edit", callback_data="bc_edit_list")
        )
        markup.row(
            InlineKeyboardButton("📊 Statistics", callback_data="bc_stats"),
            InlineKeyboardButton("⚙️ Settings", callback_data="bc_settings")
        )
        markup.row(InlineKeyboardButton("🚀 Promote Your Channel", callback_data="bc_promo"))
        markup.row(InlineKeyboardButton("🔎 Subscriber Interests", callback_data="bc_interests"))
        markup.row(InlineKeyboardButton("🏠 Main Menu", callback_data="back_main"))
        txt = (
            "Here you can create posts, send quizzes, news and manage channels.\n\n"
            f"• 👥 Connected Groups: <b>{g_cnt}</b>\n"
            f"• 📢 Connected Channels: <b>{ch_cnt}</b>"
        )
    else:
        markup.row(InlineKeyboardButton("📝 Пост яратиш", callback_data="bc_create_post"))
        markup.row(
            InlineKeyboardButton("📰 Асаларичилик Янгиликлари (/news)", callback_data="bc_bee_news_hub"),
            InlineKeyboardButton("🐝 Викторина & Сўровномалар 📊", callback_data="bc_bee_quiz_hub")
        )
        markup.row(
            InlineKeyboardButton("⏳ Отложенные", callback_data="bc_delayed_list"),
            InlineKeyboardButton("✏️ Таҳрирлаш", callback_data="bc_edit_list")
        )
        markup.row(InlineKeyboardButton("📊 Статистика", callback_data="bc_stats"), InlineKeyboardButton("⚙️ Созламалар", callback_data="bc_settings"))
        markup.row(InlineKeyboardButton("🌐 Группа ва Каналлар созламаси (Манзиллар)", callback_data="open_dest_settings"))
        markup.row(InlineKeyboardButton("🗄 Маълумотлар базаси (DB) созламалари", callback_data="admin_db_menu"))
        markup.row(InlineKeyboardButton("🚀 Канални реклама қилиш", callback_data="bc_promo"))
        markup.row(InlineKeyboardButton("🔎 Обуначилар қизиқиши", callback_data="bc_interests"))
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        txt = (
            "Бу ерда сиз янги пост яратишингиз, янгиликлар ва викториналарни канал ва гуруҳларга юбориб қадашингиз (закрепить) мумкин.\n\n"
            f"• 👥 Фаол гуруҳлар: <b>{g_cnt} та</b>\n"
            f"• 📢 Уланган каналлар: <b>{ch_cnt} та</b>"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)


def get_feed_reaction_counts(content_type, content_id):
    try:
        cursor.execute("SELECT emoji, COUNT(*) as cnt FROM feed_reactions WHERE content_type = ? AND content_id = ? GROUP BY emoji", (str(content_type), str(content_id)))
        rows = cursor.fetchall()
        return {r["emoji"]: r["cnt"] for r in rows}
    except Exception:
        return {}

_content_share_cache = {}

def get_post_buttons_markup(content_type="news", content_id="0", share_text="Asalarichilik.Uz"):
    markup = InlineKeyboardMarkup()
    auto_react = get_system_setting("auto_reactions", "1")
    share_btn = get_system_setting("share_button", "1")
    expert_btn = get_system_setting("expert_button", "1")
    react_set = get_system_setting("reactions_set", "👍 👎 ❤️ 👏")

    share_key = f"{content_type}_{content_id}"
    if share_text and share_text != "Asalarichilik.Uz":
        _content_share_cache[share_key] = share_text
    elif share_key in _content_share_cache:
        share_text = _content_share_cache[share_key]
    
    # 1. Авто-реакциялар қатори (лайк ва эможилар)
    if auto_react == "1":
        emojis = [e.strip() for e in react_set.split() if e.strip()]
        if not emojis:
            emojis = ["👍", "👎", "❤️", "👏"]
        counts = get_feed_reaction_counts(content_type, content_id)
        react_row = []
        for idx, em in enumerate(emojis):
            cnt = counts.get(em, 0)
            lbl = f"{em} {cnt}" if cnt > 0 else em
            react_row.append(InlineKeyboardButton(lbl, callback_data=f"fr_{content_type}_{content_id}_{idx}"))
        if react_row:
            markup.row(*react_row)
            
    # 2. Расмий канал ва Гуруҳ қатори
    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    c_clean = chan.replace("@", "")
    g_clean = grp.replace("@", "").replace("https://t.me/", "")
    g_url = grp if grp.startswith("http") else f"https://t.me/{g_clean}"
    
    markup.row(
        InlineKeyboardButton("📢 Расмий Канал", url=f"https://t.me/{c_clean}"),
        InlineKeyboardButton("👥 Расмий Гуруҳ", url=g_url)
    )
    # 3. YouTube канали қатори
    markup.row(InlineKeyboardButton("📺 YouTube Каналимиз", url=yt))
    
    # 4. Улашиш ва Мутахассис қатори
    extra_row = []
    if share_btn == "1":
        raw_share = (share_text or _content_share_cache.get(share_key, "Asalarichilik.Uz")).strip()
        clean_share = re.sub(r'<[^>]+>', '', raw_share).strip()
        if len(clean_share) > 900:
            clean_share = clean_share[:900].rsplit(' ', 1)[0] + "..."
        share_url = f"https://t.me/share/url?url={urllib.parse.quote('https://t.me/' + c_clean)}&text={urllib.parse.quote(clean_share)}"
        extra_row.append(InlineKeyboardButton("↗️ Улашиш", url=share_url))
        
    if expert_btn == "1":
        extra_row.append(InlineKeyboardButton("💬 Мутахассис", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"))
        
    if extra_row:
        markup.row(*extra_row)
        
    return markup

def show_destinations_settings_menu(chat_id, message_id=None, lang="uz_kr"):
    news_dest = get_system_setting("news_target_scope", "both")
    quiz_dest = get_system_setting("quiz_target_scope", "both")
    bc_dest = get_system_setting("broadcast_default_scope", "both")
    
    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    
    dest_labels = {
        "both": "🌐 Канал ва Гуруҳларга",
        "channels": "📢 Фақат Каналларга",
        "groups": "👥 Фақат Гуруҳларга"
    }
    
    news_lbl = dest_labels.get(news_dest, "🌐 Канал ва Гуруҳларга")
    quiz_lbl = dest_labels.get(quiz_dest, "🌐 Канал ва Гуруҳларга")
    bc_lbl = dest_labels.get(bc_dest, "🌐 Канал ва Гуруҳларга")
    
    cursor.execute("SELECT COUNT(*) as c FROM channels")
    ch_c = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM groups WHERE is_authorized = 1")
    gr_c = cursor.fetchone()["c"]

    txt = (
        "⚙️ <b>ГРУППА ВА КАНАЛЛАРГА ЖЎНАТИШ СОЗЛАМАЛАРИ (МАНЗИЛЛАР)</b>\n\n"
        "Ушбу бўлимда янгиликлар, викторина сўровномалари ва реклама постлари қаерга "
        "(Гуруҳга, Каналга ёки бир вақтда иккаласига ҳам) юборилишини алоҳида танлашингиз мумкин:\n\n"
        f"• 📰 <b>Янгиликлар манзили:</b> <code>{news_lbl}</code>\n"
        f"• 🐝 <b>Викториналар манзили:</b> <code>{quiz_lbl}</code>\n"
        f"• 📢 <b>Умумий тарқатиш/Реклама:</b> <code>{bc_lbl}</code>\n\n"
        f"📌 <b>Уланган расмий ресурслар:</b>\n"
        f"• 📢 <b>Расмий Канал:</b> <code>{chan}</code>\n"
        f"• 👥 <b>Расмий Гуруҳ:</b> <code>{grp}</code>\n"
        f"• 📺 <b>YouTube:</b> <code>{yt}</code>\n\n"
        f"📊 <b>Базадаги фаол тармоқлар:</b> <b>{ch_c}</b> та канал, <b>{gr_c}</b> та гуруҳ.\n\n"
        "<i>Керакли тугмани босиб юбориш қамровини ва расмий манзилларни осонгина ўзгартиришингиз мумкин:</i>"
    )

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"📰 Янгиликни қаерга: {news_lbl}", callback_data="dest_cycle_news"))
    markup.row(InlineKeyboardButton(f"🐝 Викторинани қаерга: {quiz_lbl}", callback_data="dest_cycle_quiz"))
    markup.row(InlineKeyboardButton(f"📢 Реклама/Пост қаерга: {bc_lbl}", callback_data="dest_cycle_broadcast"))
    markup.row(
        InlineKeyboardButton(f"✏️ Канал: {chan}", callback_data="dest_edit_channel"),
        InlineKeyboardButton(f"✏️ Гуруҳ: {grp}", callback_data="dest_edit_group")
    )
    markup.row(InlineKeyboardButton("✏️ YouTube ҳаволасини ўзгартириш", callback_data="dest_edit_youtube"))
    markup.row(InlineKeyboardButton("🤖 Бот админлиги ва ҳуқуқларини текшириш", callback_data="dest_check_bot_admin"))
    markup.row(
        InlineKeyboardButton("« Созламаларга қайтиш", callback_data="bc_settings"),
        InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
    )

    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_post_settings_menu(chat_id, message_id=None):
    auto_react = get_system_setting("auto_reactions", "1")
    share_btn = get_system_setting("share_button", "1")
    expert_btn = get_system_setting("expert_button", "1")
    react_set = get_system_setting("reactions_set", "👍 👎 ❤️ 👏")
    chan = get_official_channel()
    grp = get_official_group()
    script = get_system_setting("script", "uz_kr")
    q_time = get_system_setting("auto_quiz_time", "09:00")
    n_time = get_system_setting("auto_news_time", "14:00")

    ar_icon = "✅ Ёқилган" if auto_react == "1" else "⚪️ Ўчирилган"
    sh_icon = "✅ Ёқилган" if share_btn == "1" else "⚪️ Ўчирилган"
    ex_icon = "✅ Ёқилган" if expert_btn == "1" else "⚪️ Ўчирилган"
    sc_icon = "Крил 🇺🇿" if script == "uz_kr" else "Лотин 🇺🇿"

    txt = (
        "⚙️ <b>БОТ ВА ПОСТ СОЗЛАМАЛАРИ</b>\n\n"
        "Канал ва гуруҳларга юбориладиган ҳар бир хабар остига автоматик тугмалар ва реакциялар қўйишни шу ердан ёқишингиз ёки ўчиришингиз мумкин:\n\n"
        "• <b>Манзиллар созламаси:</b> Янгилик ва викториналарни каналга, гуруҳга ёки иккаласига юборишни танлаш.\n"
        "• <b>Авто-реакциялар:</b> Канал ёки гуруҳдаги янги хабарлар остига лайк тугмалари қўяди.\n"
        "• <b>Улашиш тугмаси:</b> Постни дўстларга юбориш тугмаси.\n"
        "• <b>Тўплам:</b> Лайк ва эможилар кўриниши (тайёр ёки қўлда ёзилган).\n"
        "• <b>Расмий канал ва гуруҳ:</b> Янгиликлар ва ҳаволаларда чиқадиган канал ва гуруҳни қўлда ўзгартириш."
    )

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🌐 Группа ва Каналлар созламаси (Манзиллар) ⚙️", callback_data="open_dest_settings"))
    markup.row(InlineKeyboardButton(f"🔄 Авто-реакциялар: {ar_icon}", callback_data="post_toggle_autoreact"))
    markup.row(InlineKeyboardButton(f"↗️ Улашиш тугмаси: {sh_icon}", callback_data="post_toggle_share"))
    markup.row(InlineKeyboardButton(f"💬 Мутахассис тугмаси: {ex_icon}", callback_data="post_toggle_expert"))
    markup.row(InlineKeyboardButton(f"🎨 Тўплам: {react_set}", callback_data="post_cycle_reactions"))
    markup.row(InlineKeyboardButton("✏️ Лайкларни қўлда ўзгартириш", callback_data="post_custom_reactions"))
    markup.row(InlineKeyboardButton(f"📢 Расмий канал: {chan}", callback_data="post_set_channel"))
    markup.row(InlineKeyboardButton(f"👥 Расмий гуруҳ: {grp}", callback_data="post_set_group"))
    markup.row(InlineKeyboardButton(f"🔤 Ёзув тури: {sc_icon}", callback_data="post_toggle_script"))
    q_disp = q_time[:2] if len(q_time) >= 2 else q_time
    markup.row(InlineKeyboardButton(f"⏰ Авто-викторина: {q_disp}", callback_data="post_cycle_quiz_time"))
    markup.row(InlineKeyboardButton(f"📰 Авто-янгилик: {n_time}", callback_data="post_cycle_news_time"))
    markup.row(InlineKeyboardButton("📋 Уланган канал ва гуруҳлар", callback_data="post_connected_list"))
    markup.row(InlineKeyboardButton("🔙 Ёпиш", callback_data="post_close_settings"))

    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_database_settings_menu(chat_id, message_id=None, lang="uz_kr"):
    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    n_script = get_system_setting("news_script", "uz_kr")
    q_script = get_system_setting("quiz_script", "uz_kr")
    
    n_script_lbl = "🟢 Кириллча (Ўзб)" if n_script == "uz_kr" else "🔵 Lotincha (O'zb)"
    q_script_lbl = "🟢 Кириллча (Ўзб)" if q_script == "uz_kr" else "🔵 Lotincha (O'zb)"
    
    cursor.execute("SELECT COUNT(*) as c FROM groups WHERE is_authorized = 1")
    g_cnt = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM channels")
    ch_cnt = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM users")
    u_cnt = cursor.fetchone()["c"]
    
    total_news = len(BEE_GLOBAL_NEWS)
    total_quizzes = len(get_all_bee_quizzes("all"))
    c_clean = chan.replace("@", "")
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🌐 Группа ва Каналлар созламаси (Манзиллар) ⚙️", callback_data="open_dest_settings"))
    markup.row(
        InlineKeyboardButton("✏️ Расмий канал", callback_data="db_edit_channel"),
        InlineKeyboardButton("✏️ Расмий гуруҳ", callback_data="db_edit_group")
    )
    markup.row(InlineKeyboardButton("✏️ YouTube ҳаволаси", callback_data="db_edit_youtube"))
    markup.row(
        InlineKeyboardButton(f"📰 Янгилик: {n_script_lbl}", callback_data="db_toggle_news_script"),
        InlineKeyboardButton(f"🐝 Викторина: {q_script_lbl}", callback_data="db_toggle_quiz_script")
    )
    markup.row(InlineKeyboardButton("📥 Базани юклаб олиш (Backup .db)", callback_data="db_download_file"))
    markup.row(
        InlineKeyboardButton("« Реклама менюси", callback_data="bc_menu"),
        InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
    )
    
    text = (
        f"🗄 <b>МАЪЛУМОТЛАР БАЗАСИ ВА ТИЗИМ СОЗЛАМАЛАРИ (DB)</b>\n\n"
        f"Ушбу меню орқали маълумотлар базасидаги ҳаволалар, ёзув турлари ва тизим параметрларини қўлда ўзгартиришингиз мумкин.\n\n"
        f"📌 <b>Жорий ҳаволалар:</b>\n"
        f"• 📢 <b>Расмий Канал:</b> <code>{chan}</code> (https://t.me/{c_clean})\n"
        f"• 👥 <b>Расмий Гуруҳ:</b> <code>{grp}</code>\n"
        f"• 📺 <b>YouTube Канал:</b> <code>{yt}</code>\n"
        f"• 📰 <b>Янгиликлар ёзув тури:</b> {n_script_lbl}\n"
        f"• 🐝 <b>Викториналар ёзув тури:</b> {q_script_lbl}\n\n"
        f"📊 <b>База статистикаси:</b>\n"
        f"• 👥 Фойдаланувчилар: <b>{u_cnt}</b> та\n"
        f"• 🏢 Фаол гуруҳлар: <b>{g_cnt}</b> та\n"
        f"• 📢 Уланган каналлар: <b>{ch_cnt}</b> та\n"
        f"• 📰 Янгиликлар базаси: <b>{total_news}</b> та мавзу\n"
        f"• 🐝 Викторина саволлари: <b>{total_quizzes}</b> та савол"
    )
    safe_edit_or_send(chat_id, message_id, text, markup)

def show_broadcast_channel_select(chat_id, message_id=None, lang="uz_kr"):
    cursor.execute("SELECT chat_id, title, username FROM channels ORDER BY rowid ASC")
    channels = cursor.fetchall()
    cursor.execute("SELECT chat_id, title FROM groups WHERE is_authorized = 1")
    groups = cursor.fetchall()

    markup = InlineKeyboardMarkup()
    for ch in channels:
        u_str = f" {ch['username']}" if ch.get("username") else ""
        c_title = ch.get("title") or "Канал"
        markup.row(InlineKeyboardButton(f"{c_title}{u_str}", callback_data=f"bc_pick_{ch['chat_id']}"))

    for g in groups[:5]:
        markup.row(InlineKeyboardButton(f"👥 {g.get('title', 'Гуруҳ')}", callback_data=f"bc_pick_{g['chat_id']}"))

    all_lbl = "👥 Все группы и каналы (Рассылка)" if lang == "ru" else ("👥 All groups and channels" if lang == "en" else "👥 Барча гуруҳ ва каналларга (Рассылка)")
    markup.row(InlineKeyboardButton(all_lbl, callback_data="bc_pick_all"))
    back_lbl = "« Назад" if lang == "ru" else ("« Back" if lang == "en" else "« Орқага")
    markup.row(InlineKeyboardButton(back_lbl, callback_data="bc_menu"))

    txt = "Выберите канал, в который вы хотите создать пост." if lang == "ru" else ("Select a channel you want to create a post for." if lang == "en" else "Пост яратмоқчи бўлган каналингиз ёки гуруҳни танланг:")
    safe_edit_or_send(chat_id, message_id, txt, markup)

def render_post_editor_screen(chat_id, user_id, post_dict, edit_msg_id=None, lang="uz_kr"):
    prev_markup = build_controller_post_markup(
        post_id=0,
        reactions_list=post_dict.get("reactions", []),
        url_buttons_rows=post_dict.get("url_buttons", []),
        has_comments=post_dict.get("has_comments", False),
        comments_url=post_dict.get("comments_url", ""),
        native_comments=post_dict.get("native_comments", False),
        share_text=post_dict.get("text") or "Asalarichilik"
    )

    m_type = post_dict.get("media_type", "text")
    f_id = post_dict.get("file_id")
    p_text = post_dict.get("text", "")

    try:
        if m_type == "photo" and f_id:
            bot.send_photo(chat_id, f_id, caption=p_text or None, reply_markup=prev_markup)
        elif m_type == "video" and f_id:
            bot.send_video(chat_id, f_id, caption=p_text or None, reply_markup=prev_markup)
        elif m_type == "document" and f_id:
            bot.send_document(chat_id, f_id, caption=p_text or None, reply_markup=prev_markup)
        else:
            bot.send_message(chat_id, p_text or "<i>(Текст поста)</i>", reply_markup=prev_markup, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"Preview render error: {e}")
        bot.send_message(chat_id, p_text or "<i>(Текст поста)</i>", reply_markup=prev_markup, parse_mode="HTML")

    markup = InlineKeyboardMarkup()
    is_sil = post_dict.get("is_silent", False)
    show_more = post_dict.get("show_more", False)
    
    if lang == "ru":
        markup.row(InlineKeyboardButton("Прикрепить медиафайл", callback_data="bc_attach_media"))
        has_comm_ru = post_dict.get("has_comments", False)
        if has_comm_ru:
            c_mode_ru = "🤖 В боте ✅" if post_dict.get("comments_url") in ["bot", ""] else "🔗 В чате ✅"
            c_label_ru = f"💬 Комментарии ({c_mode_ru})"
        else:
            c_label_ru = "💬 Добавить комментарии ➕"
        markup.row(InlineKeyboardButton(c_label_ru, callback_data="bc_add_comments"))
        markup.row(InlineKeyboardButton("Добавить реакции", callback_data="bc_add_reactions"))
        markup.row(InlineKeyboardButton("Добавить URL-кнопки", callback_data="bc_add_urls"))
        silent_text = "🔕 Отправить со звуком" if is_sil else "🔔 Отправить без звука"
        markup.row(InlineKeyboardButton(silent_text, callback_data="bc_toggle_silent"))
        markup.row(InlineKeyboardButton("Удалить сообщение", callback_data="bc_clear_draft"))
        if not show_more:
            markup.row(InlineKeyboardButton("↓ Показать больше", callback_data="bc_show_more"))
        else:
            pinned_st = "✅" if post_dict.get("pinned") else "⬜️"
            prev_st = "✅" if not post_dict.get("disable_preview") else "⬜️"
            markup.row(InlineKeyboardButton(f"📌 Закрепить {pinned_st}", callback_data="bc_toggle_pin"))
            markup.row(InlineKeyboardButton(f"🌐 Предпросмотр ссылок {prev_st}", callback_data="bc_toggle_link_prev"))
            markup.row(InlineKeyboardButton("↑ Скрыть", callback_data="bc_hide_more"))
    elif lang == "en":
        markup.row(InlineKeyboardButton("Attach Media File", callback_data="bc_attach_media"))
        markup.row(InlineKeyboardButton("Add Comments", callback_data="bc_add_comments"))
        markup.row(InlineKeyboardButton("Add Native Comments", callback_data="bc_native_comments"))
        markup.row(InlineKeyboardButton("Add Reactions", callback_data="bc_add_reactions"))
        markup.row(InlineKeyboardButton("Add URL Buttons", callback_data="bc_add_urls"))
        silent_text = "🔕 Send With Sound" if is_sil else "🔔 Send Without Sound"
        markup.row(InlineKeyboardButton(silent_text, callback_data="bc_toggle_silent"))
        markup.row(InlineKeyboardButton("Delete Message", callback_data="bc_clear_draft"))
        markup.row(InlineKeyboardButton("↓ Show More", callback_data="bc_show_more"))
    else:
        markup.row(InlineKeyboardButton("📎 Расм/видео бириктириш", callback_data="bc_attach_media"))
        has_comm = post_dict.get("has_comments", False)
        if has_comm:
            c_mode = "🤖 Ботда ✅" if post_dict.get("comments_url") in ["bot", ""] else "🔗 Чатда ✅"
            c_label = f"💬 Изоҳлар ({c_mode})"
        else:
            c_label = "💬 Изоҳлар қўшиш ➕"
        markup.row(InlineKeyboardButton(c_label, callback_data="bc_add_comments"))
        markup.row(InlineKeyboardButton("👍 Лайк-реакциялар қўшиш", callback_data="bc_add_reactions"))
        markup.row(InlineKeyboardButton("🔗 Ҳавола (URL) тугмалар", callback_data="bc_add_urls"))
        silent_text = "🔕 Овозли қилиш" if is_sil else "🔔 Овозсиз юбориш"
        markup.row(InlineKeyboardButton(silent_text, callback_data="bc_toggle_silent"))
        markup.row(InlineKeyboardButton("🗑 Постни тозалаш", callback_data="bc_clear_draft"))
        markup.row(InlineKeyboardButton("↓ Кўпроқ созламалар", callback_data="bc_show_more"))

    ctrl_txt = (
        "⚙️ <b>Пост конструктори:</b>\nКеракли созламаларни тугмалар орқали қўшинг ва пастдаги <b>«Далее»</b> тугмасини босинг."
        if lang not in ["ru", "en"] else
        ("⚙️ <b>Конструктор поста:</b>\nНастройте нужные опции кнопками ниже и нажмите <b>«Далее»</b>." if lang == "ru" else "⚙️ <b>Post Constructor:</b>\nConfigure options and click <b>«Next»</b>.")
    )
    bot.send_message(chat_id, ctrl_txt, reply_markup=markup, parse_mode="HTML")
    bot.send_message(
        chat_id,
        "👇" if lang != "ru" else "Выберите действие на клавиатуре:",
        reply_markup=get_post_editor_reply_keyboard(lang)
    )

def show_publish_stage(chat_id, user_id, message_id=None, lang="uz_kr"):
    state = USER_STATES.get(user_id, {})
    post_dict = state.get("post", {})
    target_name = post_dict.get("target_name") or "Канал"
    del_hours = post_dict.get("delete_timer_hours", 0)

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        timer_lbl = f"Задать таймер для удаления ({del_hours} ч)" if del_hours > 0 else "Задать таймер для удаления"
        markup.row(InlineKeyboardButton(timer_lbl, callback_data="bc_timer_menu"))
        markup.row(
            InlineKeyboardButton("Опубликовать", callback_data="bc_publish_now"),
            InlineKeyboardButton("Отложить", callback_data="bc_schedule_prompt")
        )
        markup.row(InlineKeyboardButton("« Назад", callback_data="bc_back_to_editor"))
        txt = (
            f"1 сообщение готово к публикации в канал: <b>{target_name}</b>\n\n"
            f"Вы хотите опубликовать пост прямо сейчас или отложить?"
        )
    elif lang == "en":
        timer_lbl = f"Set Auto-delete Timer ({del_hours}h)" if del_hours > 0 else "Set Auto-delete Timer"
        markup.row(InlineKeyboardButton(timer_lbl, callback_data="bc_timer_menu"))
        markup.row(
            InlineKeyboardButton("Publish Now", callback_data="bc_publish_now"),
            InlineKeyboardButton("Schedule", callback_data="bc_schedule_prompt")
        )
        markup.row(InlineKeyboardButton("« Back", callback_data="bc_back_to_editor"))
        txt = (
            f"1 message ready for publication to: <b>{target_name}</b>\n\n"
            f"Do you want to publish the post right now or schedule it?"
        )
    else:
        timer_lbl = f"⏱ Ўчириш таймерини созлаш ({del_hours} соат)" if del_hours > 0 else "⏱ Авто-ўчириш таймерини созлаш"
        markup.row(InlineKeyboardButton(timer_lbl, callback_data="bc_timer_menu"))
        markup.row(
            InlineKeyboardButton("🚀 Эълон қилиш", callback_data="bc_publish_now"),
            InlineKeyboardButton("⏳ Кейинга қолдириш", callback_data="bc_schedule_prompt")
        )
        markup.row(InlineKeyboardButton("« Орқага", callback_data="bc_back_to_editor"))
        txt = (
            f"1 та хабар эълон қилишга тайёр: <b>{target_name}</b>\n\n"
            f"Постни ҳозироқ эълон қилмоқчимисиз ёки кейинга қолдирмоқчимисиз?"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_delete_timer_menu(chat_id, message_id=None, lang="uz_kr"):
    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(InlineKeyboardButton("1 час", callback_data="bc_settimer_1"), InlineKeyboardButton("2 часа", callback_data="bc_settimer_2"))
        markup.row(InlineKeyboardButton("6 часов", callback_data="bc_settimer_6"), InlineKeyboardButton("12 часов", callback_data="bc_settimer_12"))
        markup.row(InlineKeyboardButton("24 часа", callback_data="bc_settimer_24"), InlineKeyboardButton("48 часов", callback_data="bc_settimer_48"))
        markup.row(InlineKeyboardButton("Не удалять", callback_data="bc_settimer_0"))
        markup.row(InlineKeyboardButton("« Назад", callback_data="bc_back_to_publish"))
        txt = "⏱ Выберите время, через которое пост автоматически удалится из канала/группы:"
    elif lang == "en":
        markup.row(InlineKeyboardButton("1 hour", callback_data="bc_settimer_1"), InlineKeyboardButton("2 hours", callback_data="bc_settimer_2"))
        markup.row(InlineKeyboardButton("6 hours", callback_data="bc_settimer_6"), InlineKeyboardButton("12 hours", callback_data="bc_settimer_12"))
        markup.row(InlineKeyboardButton("24 hours", callback_data="bc_settimer_24"), InlineKeyboardButton("48 hours", callback_data="bc_settimer_48"))
        markup.row(InlineKeyboardButton("Do not delete", callback_data="bc_settimer_0"))
        markup.row(InlineKeyboardButton("« Back", callback_data="bc_back_to_publish"))
        txt = "⏱ Choose the period after which the post will be automatically deleted:"
    else:
        markup.row(InlineKeyboardButton("1 соат", callback_data="bc_settimer_1"), InlineKeyboardButton("2 соат", callback_data="bc_settimer_2"))
        markup.row(InlineKeyboardButton("6 соат", callback_data="bc_settimer_6"), InlineKeyboardButton("12 соат", callback_data="bc_settimer_12"))
        markup.row(InlineKeyboardButton("24 соат", callback_data="bc_settimer_24"), InlineKeyboardButton("48 соат", callback_data="bc_settimer_48"))
        markup.row(InlineKeyboardButton("Ўчирилмасин", callback_data="bc_settimer_0"))
        markup.row(InlineKeyboardButton("« Орқага", callback_data="bc_back_to_publish"))
        txt = "⏱ Пост неча соатдан кейин канал/гуруҳдан автоматик ўчириб ташлансин:"
    safe_edit_or_send(chat_id, message_id, txt, markup)

def execute_publish_controller_post(post_dict):
    t_id = post_dict.get("target_id", 0)
    text = post_dict.get("text", "")
    m_type = post_dict.get("media_type", "text")
    f_id = post_dict.get("file_id")
    reacts = post_dict.get("reactions", [])
    urls = post_dict.get("url_buttons", [])
    comments = post_dict.get("has_comments", False)
    native_c = post_dict.get("native_comments", False)
    c_url = post_dict.get("comments_url", "")
    is_silent = post_dict.get("is_silent", False)
    del_hours = post_dict.get("delete_timer_hours", 0)

    cursor.execute("""
    INSERT INTO controller_posts 
    (target_id, target_name, message_text, media_type, media_file_id, reactions_json, url_buttons_json, has_comments, native_comments, comments_url, is_silent, delete_timer_hours, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published')
    """, (
        t_id if str(t_id).lstrip('-').isdigit() else 0, post_dict.get("target_name", ""), text, m_type, f_id,
        json.dumps(reacts), json.dumps(urls), 1 if comments else 0, 1 if native_c else 0, c_url,
        1 if is_silent else 0, del_hours
    ))
    conn.commit()
    post_id = cursor.lastrowid

    markup = build_controller_post_markup(
        post_id=post_id,
        reactions_list=reacts,
        url_buttons_rows=urls,
        has_comments=comments,
        comments_url=c_url,
        native_comments=native_c,
        share_text=text or "Asalarichilik"
    )

    targets = []
    if str(t_id) in ["0", "all"]:
        cursor.execute("SELECT chat_id FROM channels")
        targets.extend([r["chat_id"] for r in cursor.fetchall()])
        cursor.execute("SELECT chat_id FROM groups WHERE is_authorized = 1")
        targets.extend([r["chat_id"] for r in cursor.fetchall()])
    else:
        try:
            targets = [int(t_id)]
        except Exception:
            targets = []

    sent_count = 0
    now_del = datetime.now() + timedelta(hours=del_hours) if del_hours > 0 else None
    del_str = now_del.strftime("%Y-%m-%d %H:%M:%S") if now_del else None

    for target in targets:
        try:
            sent_msg = None
            if m_type == "photo" and f_id:
                try:
                    sent_msg = bot.send_photo(target, f_id, caption=text or None, reply_markup=markup, disable_notification=is_silent, parse_mode="HTML")
                except Exception:
                    sent_msg = bot.send_photo(target, f_id, caption=text or None, reply_markup=markup, disable_notification=is_silent)
            elif m_type == "video" and f_id:
                try:
                    sent_msg = bot.send_video(target, f_id, caption=text or None, reply_markup=markup, disable_notification=is_silent, parse_mode="HTML")
                except Exception:
                    sent_msg = bot.send_video(target, f_id, caption=text or None, reply_markup=markup, disable_notification=is_silent)
            elif m_type == "document" and f_id:
                try:
                    sent_msg = bot.send_document(target, f_id, caption=text or None, reply_markup=markup, disable_notification=is_silent, parse_mode="HTML")
                except Exception:
                    sent_msg = bot.send_document(target, f_id, caption=text or None, reply_markup=markup, disable_notification=is_silent)
            else:
                try:
                    sent_msg = bot.send_message(target, text, reply_markup=markup, disable_notification=is_silent, parse_mode="HTML")
                except Exception:
                    sent_msg = bot.send_message(target, text, reply_markup=markup, disable_notification=is_silent)

            if sent_msg:
                try:
                    # Бот жўнатган реклама ва эълонларни гуруҳ тепасига закрепит қилиш:
                    bot.pin_chat_message(target, sent_msg.message_id, disable_notification=is_silent)
                except Exception as pe:
                    logging.info(f"Auto-pin post in {target}: {pe}")
                try:
                    cursor.execute("UPDATE controller_posts SET sent_chat_id = ?, sent_message_id = ? WHERE post_id = ?", (target, sent_msg.message_id, post_id))
                    conn.commit()
                except Exception:
                    pass
                if del_str:
                    cursor.execute("INSERT INTO auto_delete_posts (chat_id, message_id, delete_at) VALUES (?, ?, ?)",
                                   (target, sent_msg.message_id, del_str))
                    conn.commit()
            sent_count += 1
        except Exception as e:
            logging.warning(f"Error publishing post to {target}: {e}")
        time.sleep(0.05)

    return sent_count, post_id

# Фонда режалаштирилган ва авто-ўчириладиган постлар назорати
def run_scheduled_posts_worker():
    while True:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT * FROM controller_posts WHERE status = 'scheduled' AND scheduled_time <= ?", (now_str,))
            due_posts = cursor.fetchall()
            for p in due_posts:
                p_dict = {
                    "target_id": p["target_id"],
                    "target_name": p["target_name"],
                    "text": p["message_text"],
                    "media_type": p["media_type"],
                    "file_id": p["media_file_id"],
                    "reactions": json.loads(p["reactions_json"] or "[]"),
                    "url_buttons": json.loads(p["url_buttons_json"] or "[]"),
                    "has_comments": bool(p["has_comments"]),
                    "native_comments": bool(p["native_comments"]),
                    "comments_url": p.get("comments_url", ""),
                    "is_silent": bool(p["is_silent"]),
                    "delete_timer_hours": p["delete_timer_hours"]
                }
                execute_publish_controller_post(p_dict)
                cursor.execute("UPDATE controller_posts SET status = 'published' WHERE post_id = ?", (p["post_id"],))
                conn.commit()

            cursor.execute("SELECT * FROM auto_delete_posts WHERE delete_at <= ?", (now_str,))
            dels = cursor.fetchall()
            for d in dels:
                delete_msg_safe(d["chat_id"], d["message_id"])
                cursor.execute("DELETE FROM auto_delete_posts WHERE id = ?", (d["id"],))
                conn.commit()
        except Exception as e:
            pass
        time.sleep(15)

threading.Thread(target=run_scheduled_posts_worker, daemon=True).start()


# ==================== АСАЛАРИЧИЛИК ВЕТЕРИНАР ШИФОКОРИ ВА AI ТАШХИС ТИЗИМИ ====================
import base64

# Мукаммал ветеринария ва асаларичилик билимлар базаси (Офлайн ва онлайн)
OFFLINE_BEE_DISEASES = {
    "варроа": {
        "name": "Варроатоз (Varroa destructor канаси)",
        "symptoms": "Асаларилар ва қуртлар танасида жигарранг майда каналар кўринади. Арилар қанотсиз, ногирон бўлиб туғилади, уя олдида ўлиб ётади.",
        "treatment": "1. Кузда ва баҳорда Бипин (Амитраз) препарати: 1 ампула (0.5 мл) 1 литр илиқ сувга аралаштирилиб, кўчалар орасига 10 мл дан сепилади.\n2. Флувалинат ёки Амитразли пластинкалар (Варроадез, Апистан) уяга 25-30 кунга осиб қўйилади.\n3. Органик усул: Шовул (щавелевая) кислотаси буғлатилади ёки чумоли кислотаси қўлланади.",
        "prevention": "Эркак ари катакларини кесиб олиш, кучли оилаларни сақлаш ва мунтазам баҳорги-кузги ишлов бериш."
    },
    "бипин": {
        "name": "Варроатозга қарши Бипин муолажаси",
        "symptoms": "Канага қарши даволаш ва профилактика муолажаси.",
        "treatment": "1 ампула Бипин (0.5 мл) 1 литр илиқ (35-40°C) тоза сувга яхшилаб аралаштирилади (эритма сутдек оқаради). Шприц ёрдамида рамкалар оралиғидаги ҳар бир ари кўчасига 10 мл дан сепилади. Ҳарорат +5°C дан паст бўлмаслиги керак.",
        "prevention": "Йилига 2 марта: биринчиси асал олингандан кейин (август охири), иккинчиси охирги насл чиқиб бўлгач (октябрь-ноябрь)."
    },
    "кана": {
        "name": "Варроатоз канаси",
        "symptoms": "Арилар устида жигарранг кана ёпишган бўлади, қанотлари деформацияланади, оила кучсизланади.",
        "treatment": "Бипин 0.5 мл / 1 л сув ёки Варроадез пластинкалари қўйилади. Органик усулда Тимол ёки шовул кислотаси буғи тавсия этилади.",
        "prevention": "Баҳорда асал йиғимидан олдин ва кузда охирги насл чиққач 2 марта қайта ишлов бериш."
    },
    "аскосфероз": {
        "name": "Аскосфероз (Оҳакли чириш / Тош чириш / Chalkbrood)",
        "symptoms": "Мумкатак ичидаги ва уя тубидаги личинкалар оҳакдай оқ, қаттиқ тошдек ёки кулранг тусда қотади ва қурийди.",
        "treatment": "1. Аскопол, Аскоцин ёки Нистатин препарати 1 литр 50% ли шакар сиропига аралаштириб 3-5 кун оралиғида 3 марта берилади.\n2. Зарарланган рамкалар уядан олиб ташланади ва эритилади.\n3. Уя туби ва деворлари дезинфекция қилиниб, уя иссиқ ва қуруқ жойга кўчирилади.",
        "prevention": "Уядаги намликни камайтириш, сифатли ёстиқчалар қўйиш ва оилани шамоллатиш тизимини тўғрилаш."
    },
    "оҳак": {
        "name": "Аскосфероз (Оҳакланиш)",
        "symptoms": "Қуртлар оҳак сингари оқариб, қаттиқлашиб қуриб қолади.",
        "treatment": "Нистатин (100 000 ТБ / 1 л сироп) ёки Аскопол пластинкалари, намликни йўқотиш, уяни иситиш.",
        "prevention": "Пасекани қуёшли ва қуруқ жойга қўйиш, намликдан асраш."
    },
    "нозема": {
        "name": "Нозематоз (Қорин суриши / Nosema apis ва ceranae)",
        "symptoms": "Уя деворлари ва рамкаларда жигарранг/сариқ ич кетиш доғлари, ариларнинг қорни шишиб, уя олдида судралиб учишга кучи етмай қолиши.",
        "treatment": "1. Фумагиллин (Фумидил Б) ёки Ноземацид препарати: 1 литр илиқ шакар сиропига қўшиб 1 ҳафта давомида оилаларга берилади.\n2. Табиий усул: 1 литр сиропга 1 ош қошиқ пиёз ёки саримсоқ шарбати қўшиб бериш юқори самара беради.\n3. Ифлосланган уяларни алмаштириб, оилани тоза уяга кўчириш шарт.",
        "prevention": "Қишга сифатли асал (падевий асалсиз) қолдириш, қишловни қуруқ ва сокин жойда ўтказиш."
    },
    "ич кетиш": {
        "name": "Нозематоз ва дизентерия",
        "symptoms": "Рамкалар ва улей устида сариқ-жигарранг суюқ тезак доғлари, арилар қорни шишган.",
        "treatment": "Ноземацид 0.25 г / 1 л сиропга қўшиб берилади. Уяни тоза қуруқ уяга алмаштириш лозим.",
        "prevention": "Эрта баҳорги озиқлантириш ва падевий асални қишловга қолдирмаслик."
    },
    "чириш": {
        "name": "Гнилец (Европа ва Америка чириш касаллиги)",
        "symptoms": "Очиқ ёки ёпиқ личинкалар чирийди, қаҳваранг/қора рангга киради, қопқоқчалари тешилади ва сассиқ, қўланса (дурадгор елими) ҳиди келади. Игна билан текширилса, ипдек чўзилади.",
        "treatment": "1. Окситетрациклин ёки Тетрациклин антибиотики: 500 000 ТБ 1 литр шакар сиропига қўшиб ҳар бир кўчага 100-150 мл дан 3-4 марта берилади.\n2. Касал рамкалар зудлик билан уядан чиқарилиб ёқиб юборилади.\n3. Арилар тоза дезинфекция қилинган уяга, янги мумли рамкаларга кўчирилади ва она ари алмаштирилади.",
        "prevention": "Бошқа пасекалардан номаълум рамкаларни олиб келмаслик, карантин қоидаларига риоя қилиш."
    },
    "куя": {
        "name": "Мум куяси (Восковая моль / Пчелиная огневка)",
        "symptoms": "Мумкатакларни оқ ипак толалар ва тўрлар қоплаб олади, мум кукунга айланади, ичида майда қуртлар ҳаракатланиб, мумни еб битиради.",
        "treatment": "1. Стопмоль пластинкалари ёки Тимол препарати қўлланади.\n2. Мумларни сирка кислотаси буғлари билан ёки совуқда (нолдан паст ҳароратда) сақлаш қурт ва тухумларни йўқ қилади.\n3. Зарарланган қисмлар кесиб ташланади.",
        "prevention": "Эски қора рамкаларни уяда қолдирмаслик, мум захираларини ҳаво айланадиган, қуруқ ва салқин жойда сақлаш."
    },
    "акарапидоз": {
        "name": "Акарапидоз (Трахея канаси)",
        "symptoms": "Арилар уядан чиқиб ерда судралади, қанотлари чалкашиб (очилган ҳолда) туради, учишга лаёқати йўқолади.",
        "treatment": "1. Фольбекс, Варропол ёки Акарасан тутатқилари уяга тутатилади.\n2. Эфир мойлари (эвкалипт, пихта) қўлланади.",
        "prevention": "Касаллик чиққан зонадан ари сотиб олмаслик, ўз вақтида профилактика қилиш."
    },
    "паралич": {
        "name": "Вирусли фалаж (Қора касаллик / Черный паралич)",
        "symptoms": "Арилар қорайиб кетади, туклари тўкилиб ялтироқ бўлиб қолади, қанотлари ва танаси титраб учишга мажоли қолмайди.",
        "treatment": "1. Эндоглюкин препарати билан уяга пуркалади.\n2. Шакар сиропига биовит ёки вирусга қарши препаратлар қўшилади.\n3. Кучли шамоллатиш ва витаминли қўшимчалар берилади.",
        "prevention": "Оилаларни стресс ва қизиб кетишдан асраш, она арини соғлом зотли онага алмаштириш."
    },
    "сачратқи": {
        "name": "Халтачали қурт (Мешотчатый расплод)",
        "symptoms": "Ёпиқ қуртлар халтачага ўхшаб суюқлик билан тўлади, ранги сариқдан қорага ўзгаради, бошчаси юқорига қараб қотади.",
        "treatment": "1. Зарарланган рамкаларни олиб ташлаш.\n2. Эндоглюкин ёки Санапин эритмаси пуркалади.\n3. Оилани тоза уяга ўтказиб, янги она ари берилади.",
        "prevention": "Совуқдан ва намликдан ҳимоя қилиш, эски қора рамкаларни ишлатмаслик."
    },
    "браулез": {
        "name": "Браулёз (Асалари бити)",
        "symptoms": "Асалари ва айниқса она ари танасида 1 мм лик қизил-қўнғир рангли битлар кўринади. Она ари тухум қўйишни камайтиради.",
        "treatment": "Фенотиазин ёки тамаки (махорка) тутуни билан уяни 3 кун тутатиш. Тимол дориси қўлланилади.",
        "prevention": "Мум қопқоқларини (забрус) ўз вақтида қириб тозалаб туриш."
    },
    "падевий": {
        "name": "Падевий токсикоз (Дарахт шираси билан заҳарланиш)",
        "symptoms": "Қишда ёки кузда арилар уя ичида безовта бўлиб, кўп нобуд бўлади, ичи сурилади.",
        "treatment": "Уядаги падевий қора асалли рамкаларни дарҳол олиб, ўрнига тоза шакар сиропи ёки сифатли гул асали рамкалари қўйилади.",
        "prevention": "Қишлов олдидан асал таркибида пад бор-йўқлигини спирт ёки оҳак суви билан текшириб кўриш."
    },
    "пестицид": {
        "name": "Кимёвий заҳарланиш (Пестицид ва заҳарли химикатлар)",
        "symptoms": "Уя олдида минглаб арилар титраб жон беради, хартумчалари чўзилган ҳолда қолади, оммавий қирилиш юз беради.",
        "treatment": "1. Дарҳол уяларга 1:3 нисбатдаги суюқ илиқ шакар сиропи ва тоза сув берилади.\n2. Заҳарланган гулчангили рамкалар чиқариб ташланади.\n3. Уяларни даволанмаган хавфсиз ҳудудга (камида 5-7 км узоққа) кўчириш керак.",
        "prevention": "Фермерлар билан алоқада бўлиш, кимёвий дорилаш пайтида уяларни 2-3 кунга ёпиб туриш."
    },
    "трутовка": {
        "name": "Трутовкалик (Она арисиз қолиб, ишчи арилар тухум қўйиши)",
        "symptoms": "Катакларда тартибсиз, деворларга сочилган 2-3 тадан тухумлар бўлади, фақат бўртиб чиққан эркак ари (трутень) насллари чиқади.",
        "treatment": "Уяни пасекадан 20-30 метр нарига олиб бориб, ҳамма ариларни ерга қоқиб юборилади. Эски уя ўрнига соғлом оиладан очиқ қуртли рамка ва устига ёш она ари панжара (колпачок) остида қўйилади.",
        "prevention": "Оила онасиз қолмаслигини мунтазам назорат қилиб бориш."
    },
    "акарапидоз": {
        "name": "Акарапидоз (Трахея канаси)",
        "symptoms": "Асаларилар уча олмайди, қанотлари чалкашиб (очиқ ҳолда) судралади, леток олдида тўпланиб жон беради.",
        "treatment": "1. Фольбекс ёки Акарасан тутатқилари уя ичига тутатилади.\n2. Тера (эфир) мойлари ва пихта мойи қўлланади.",
        "prevention": "Касаллик кузатилган жойлардан ари келтирмаслик, профилактик тутатиш."
    }
}

# Асаларичиликка оид кенгайтирилган калит сўзлар луғати (Лотин, Кирилл ва Рус тилларида)
BEE_CORE_KEYWORDS = [
    # Ўзбекча кирилл
    'асал', 'ари', 'асалари', 'асаларилар', 'асаларичи', 'асаларичилик', 'пчел', 'мед', 'мёд', 'honey', 'bee',
    'пасека', 'улей', 'улья', 'ульи', 'уя', 'яшик', 'яшиклар', 'ромка', 'рамка', 'рамки', 'вощина',
    'мум', 'мумкатак', 'суш', 'прицеп', 'прицепи', 'павильон', 'апидомик', 'платформа',
    'она ари', 'матка', 'карника', 'бакфаст', 'карпатка', 'итальянка', 'трутовка', 'эркак ари',
    'кўч', 'рой', 'роение', 'пакет', 'пчелопакет', 'бўлинма', 'оила', 'ари оиласи',
    'прополис', 'перга', 'гулчанги', 'пыльца', 'асалари сути', 'маточное молочко', 'забрус',
    'медогонка', 'асалҳайдагич', 'димарь', 'тутатқи', 'тутатгич', 'стамеска', 'ниқоб', 'сетка',
    'бипин', 'амитраз', 'флувалинат', 'варроа', 'тимол', 'нозема', 'аскосфероз', 'чириш',
    'канди', 'сироп', 'апистан', 'оксивит', 'полисан', 'эндоглюкин', 'щавелев', 'шовул',
    'чумоли кислота', 'поилка', 'сувдон', 'кислота', 'куя', 'акарапидоз',
    'личинка', 'личинкалар', 'қурт', 'қуртлар', 'қуртча', 'расплод', 'қотиб', 'ириб', 'чириб',
    'касаллик', 'касал', 'дори', 'даволаш', 'муолажа', 'ташхис', 'ўлаяпти', 'улаяпти', 'қириляпти',
    # Ўзбекча лотин
    'asal', 'ari', 'asalari', 'asalarilar', 'asalarichi', 'asalarichilik', 'pchela', 'pchely', 'paseka',
    'uley', 'uya', 'yashik', 'yashiklar', 'romka', 'ramka', 'ramkalar', 'voshchina', 'vashina',
    'mum', 'mumkatak', 'sush', 'pritsep', 'prikep', 'pavilon', 'ona ari', 'matka', 'karnika',
    'bakfast', 'karpatka', "ko'ch", 'koch', 'roy', 'paket', 'pchelopaket', 'propolis',
    'perga', 'gulchangi', 'changi', 'chang', 'asalari suti', 'medogonka', 'asalhaydagich',
    'tutatqi', 'stameska', 'setka', 'bipin', 'amitraz', 'fluvalinat', 'varroa', 'timol',
    'nozema', 'askosferoz', 'chirish', 'kandi', 'sirop', 'apistan', 'kuya', 'akarapidoz',
    'lichinka', 'lichinkalar', 'qurt', 'qurtlar', 'qurtcha', 'rasplod', 'qotib', 'irib', 'chirib',
    'kasallik', 'kasal', 'dori', 'davolash', 'muolaja', 'tashxis', "o'layapti", 'ulayapti', 'qirilyapti'
]

# Савол берувчи сўзлар луғати (Лотин, Кирилл ва Рус тилларида)
QUESTION_WORDS = [
    # Лотин
    'qanaqa', 'qanday', 'kanday', 'nima', 'nimaga', 'nega', 'qayerda', 'qachon', 'qancha',
    'nechta', 'qayerdan', 'maslahat', 'yordam', 'aytvorilar', 'aytvorishingiz', 'aytib yuboring',
    'biladiganlar', 'bilasizlarmi', 'boladimi', "bo'ladimi", 'mumkinmi', 'iloji', 'kerak',
    'qilsam', 'qilay', 'qilsak', 'kasallik', 'tashxis', 'davolash', 'dori', "o'layapti",
    'ulayapti', "o'lib", 'ulib', 'qirilyapti', 'qirilib', 'irib', 'chirib', 'qotib',
    'lichinka', 'lichinkalar', 'qurt', 'qurtlar', 'kuya', 'kana', 'varroa',
    # Кирилл
    'қанақа', 'қандай', 'кандай', 'нима', 'нимага', 'нега', 'қаерда', 'қачон', 'қанча',
    'нечта', 'қаердан', 'маслаҳат', 'ёрдам', 'айтворинг', 'айтсангиз', 'айтворсанглар',
    'биладиган', 'биласизларми', 'боладими', 'бўладими', 'мумкинми', 'иложи', 'керак',
    'қилсам', 'қилай', 'қилсак', 'касаллик', 'ташхис', 'даволаш', 'дори', 'ўлаяпти',
    'улаяпти', 'ўлиб', 'улиб', 'қириляпти', 'қирилиб', 'ириб', 'чириб', 'қотиб',
    'личинка', 'личинкалар', 'қурт', 'қуртлар', 'куя', 'кана', 'варроа',
    # Рус
    'что', 'как', 'почему', 'зачем', 'когда', 'где', 'сколько', 'какой', 'какая', 'какие',
    'помогите', 'подскажите', 'болезнь', 'лечение', 'лекарство', 'личинки', 'погибают'
]

# Асаларичилик маҳсулотлари, канди, озуқа ва жиҳозлари луғати
BEE_PRODUCT_WORDS = [
    'қандил', 'қанди', 'кандил', 'канди', 'kandil', 'qandil', 'kandi', 'qandi',
    'қишги озуқа', 'қишки озуқа', 'qishki ozuqa', 'qishgi ozuqa',
    'озуқа', 'озука', 'oziqa', 'ozuqa', 'сироп', 'шакар', 'пати', 'инверт',
    'рамка', 'рамкалар', 'яшик', 'яшиклар', 'уя', 'улей', 'вощина', 'мумкатак',
    'прицеп', 'медогонка', 'тутатқи', 'ниқоб', 'сетка', 'стамеска', 'она ари', 'матка'
]

# Асаларичилик маҳсулотлари ва жиҳозлари савдоси/рекламаси сўзлари
COMMERCIAL_AD_WORDS = [
    'сотилади', 'сотаман', 'сотамиз', 'сотиладиган', 'сотиладигон', 'сотилмокда', 'сотилмоқда',
    'сотиш', 'сотиши', 'сотади', 'сотувда', 'сотув', 'продам', 'продается', 'продаю', 'продажа',
    'нархи', 'нарх', 'нархда', 'баҳоси', 'бахоси', 'цена', 'по цене',
    'сўм', 'сум', 'som', "so'm", 'минг', 'ming', 'usd', 'доллар', '$',
    'заказ', 'буюртма', 'buyurtma', 'етказиб бериш', 'етказиб', 'етказамиз', 'доставка', 'dostavka',
    'тел:', 'телефон:', 'боғланиш:', 'номер:', '+998', 'акция', 'скидка',
    'оптом', 'оптим', 'улгуржи', 'келишамиз', 'келишилган', 'арзон', 'arzon',
    'литр', 'литрда', 'банка', 'фляга', 'бидон', 'kg', 'кг', 'дона', 'донаси', 'пачка', 'блок',
    'sotiladi', 'sotaman', 'sotamiz', 'sotiladigan', 'sotilmoqda', 'sotish', 'sotishi', 'sotuv', 'sotuvda', 'sotadi',
    'narxi', 'narx', 'narxda', 'bahosi', 'murojaat', 'мурожаат', 'aloqa', 'алоқа'
]

# Касаллик ва шифокор ташхисига оид сўзлар
DISEASE_SYMPTOM_WORDS = [
    'касаллик', 'касал', 'ташхис', 'даволаш', 'дори', 'муолажа', 'симптом', 'симтом',
    'ўлаяпти', 'улаяпти', 'ўляпти', 'қириляпти', 'ўлиб', 'нобуд', 'чириш', 'чириган',
    'ириб', 'қотиб', 'аскосфероз', 'варроа', 'кана', 'нозема', 'куя', 'фалаж', 'паралич',
    'гнилица', 'гнилец', 'нима бўлган', 'нега ўляпти', 'қандай даволайман', 'ёрдам беринг',
    'маслаҳат беринг', 'оҳак', 'чувалчанг',
    'kasallik', 'kasal', 'tashxis', 'davolash', 'dori', 'muolaja', 'simptom',
    "o'layapti", 'ulayapti', "o'lyapti", 'qirilyapti', "o'lib", 'nobud', 'chirish', 'chirigan',
    'irib', 'qotib', 'askosferoz', 'varroa', 'nozema', 'kuya', 'falaj', 'paralich',
    'gnilets', 'nima bolgan', "nima bo'lgan", 'nega ulayapti', 'qanday davolayman',
    'yordam bering', 'maslahat bering', 'ohak'
]

def has_phone_number(text):
    """Ўзбекистон ва халқаро телефон рақамларини аниқлаш"""
    if not text:
        return False
    digits_only = re.sub(r'\D', '', text)
    if re.search(r'(?:998)?(?:90|91|93|94|95|97|98|99|88|33|77)\d{7}', digits_only):
        return True
    if re.search(r'\+?998[\s\-]?[0-9]{2}[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}', text):
        return True
    if re.search(r'\b(?:90|91|93|94|95|97|98|99|88|33|77)[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}\b', text):
        return True
    if any(p in text.lower() for p in ['тел:', 'tel:', 'номер:', 'nomer:', 'тел ', 'tel ', 'боғланиш', "bog'lanish", 'murojaat', 'мурожаат']):
        return True
    return False

# Гуруҳ учун мутлақо бегона, диний занжир ва дунёвий янгиликлар сўзлари
OFFTOPIC_TRIGGERS = [
    'ҳадис', 'хадис', 'hadis', 'оят', 'oyat', 'намоз вақти', 'намоз вақтлари', 'namoz',
    'эҳсон', 'ehson', 'маъруза', 'maruza', 'домла', 'domla', 'фатво', 'fatvo',
    'бу хабарни 10', 'ushbu xabarni 10', 'тарқатинг', 'tarqating', 'савоб учун тарқатинг', 'savob uchun',
    'жума муборак', 'juma muborak',
    'сиёсат', 'siyosat', 'президент', 'prezident', 'уруш', 'urush', 'доллар курси', 'dollar kursi',
    'футбол', 'futbol', 'криптовалюта', 'kriptovalyuta', 'kripta', 'крипта', 'трейдинг', 'treyding',
    'биткоин', 'bitcoin', 'казино', 'kazino', '1xbet', 'онлайн пул', 'onlayn pul', 'пассив даромад',
    'gentra', 'cobalt', 'nexia', 'damas', 'spark', 'matiz', 'byd', 'moshina', 'avtomobil',
    'iphone', 'samsung', 'telefon sotiladi', 'smartfon', 'noutbuk', 'kompyuter',
    'kvartira', 'hovli', 'uchastka sotiladi', 'ijara', 'kredit', 'garov',
    'жентра', 'кобальт', 'нексия', 'дамас', 'спарк', 'машина сотилади', 'айфон', 'телефон сотилади'
]

# Оддий одоб ва саломлашиш иборалари (Бегона ҳисобланмайди)
COURTESY_PHRASES = [
    'ассалому алайкум', 'салом', 'хайрли тонг', 'хайрли кун', 'хайрли кеч', 'кунингиз хайрли',
    'яхшимисиз', 'соғмисиз', 'рахмат', 'раҳмат', 'соғ бўлинг', 'ташаккур', 'керак эди', 'борми',
    'assalomu alaykum', 'salom', 'xayrli tong', 'xayrli kun', 'rahmat', 'sog boling'
]

def is_beekeeping_related_text(text):
    """Матннинг асаларичиликка (асал, ари, прицеп, яшик, ромка ва б.) оидлигини аниқлаш"""
    t = (text or "").lower()
    return any(k in t for k in BEE_CORE_KEYWORDS)

def is_beekeeping_commercial_post(text):
    """Асаларичилик маҳсулотлари (асал, канди/қандил, озуқа, уя, ромка, она ари ва б.) савдоси/рекламаси эканлигини 100% аниқлаш"""
    t = (text or "").lower()
    has_bee = any(k in t for k in BEE_CORE_KEYWORDS) or any(k in t for k in BEE_PRODUCT_WORDS)
    has_com = any(w in t for w in COMMERCIAL_AD_WORDS) or has_phone_number(text)
    if has_bee and has_com:
        return True
    if any(k in t for k in ['қандил', 'кандил', 'канди', 'kandi', 'qandil', 'kandil', 'qandi']) and (has_com or has_phone_number(text) or 'соти' in t or 'sot' in t):
        return True
    return False

def is_unrelated_offtopic_post(text):
    """Асаларичиликка умуман алоқаси бўлмаган диний занжир ёки дунёвий хабарларни аниқлаш"""
    t = (text or "").lower()
    has_bee = any(k in t for k in BEE_CORE_KEYWORDS)
    if has_bee:
        return False
    if any(o in t for o in OFFTOPIC_TRIGGERS):
        return True
    return False

def is_courtesy_message(text):
    """Оддий самимий саломлашиш ва миннатдорчилик"""
    t = (text or "").lower()
    return any(c in t for c in COURTESY_PHRASES)

def analyze_bee_disease_or_question(query_text, photo_bytes=None, mime_type="image/jpeg"):
    """
    Асаларичилик саволи ёки расмини Asalarichilik.Uz шифокори номидан таҳлил қилувчи тизим.
    Симптомларни офлайн ва онлайн юқори аниқликда текширади, аниқ дорилар ва дозаларини беради.
    ДИҚҚАТ: Сотув, реклама, озуқа/қандил эълонларига ёки телефон рақамли хабарларга АСЛО ТАШХИС ҚЎЙИЛМАЙДИ!
    """
    # 0. САВДО / РЕКЛАМА / ТЕЛЕФОН БЎЛСА ДАРҲОЛ COMMERCIAL ҚАЙТАРИШ
    if is_beekeeping_commercial_post(query_text):
        return "COMMERCIAL"

    q_lower = (query_text or "").lower()

    # ---------------- 1. МУРАККАБ ВА БИРЛАШМА СИМПТОМЛАР ТАҲЛИЛИ (ОФЛАЙН ЭКСПЕРТ) ----------------
    has_lichinka = any(w in q_lower for w in ['lichinka', 'личинка', 'расплод', 'qurt', 'қурт', 'қуртча'])
    has_irib = any(w in q_lower for w in ['irib', 'ириб', 'чириб', 'chirib', 'чириш', 'chirish', 'gnilets', 'гнилец', 'sassiq', 'сассиқ'])
    has_qotib = any(w in q_lower for w in ['qotib', 'қотиб', 'оҳак', 'ohak', 'askosferoz', 'аскосфероз', 'tosh', 'тош'])

    # А) Ҳам ИРИБ, ҳам ҚОТИБ ўлиш ҳолати (Энг хавфли ҳолат - Аскосфероз + Гнилец аралашмаси)
    if has_lichinka and has_irib and has_qotib:
        return (
            "🐝 <b>Asalarichilik.Uz🇺🇿 шифокори хулосаси:</b>\n\n"
            "🔍 <b>Тахминий ташхис:</b>\n"
            "Личинкаларнинг ҳам <b>ириб</b>, ҳам <b>қотиб</b> ўлиши асаларичиликда иккита хавфли касаллик аломатига тўғри келади:\n\n"
            "1. <b>Аскосфероз (Оҳакли чириш / Тош чириш / Chalkbrood):</b> Замбуруғли касаллик. Уяда намлик ошганда ва совуқда личинкалар оҳакдек ёки тошдек қотиб қурийди (қотиб қолишнинг асосий сабаби).\n"
            "2. <b>Европа ёки Америка чириши (Гнилец / Foulbrood):</b> Бактериал оғир касаллик. Личинкалар аввал ириб, сариқ-жигарранг бўлиб эрийди, сассиқ дурадгор елими ҳиди келади ва игна билан текширганда ипдек чўзилади. Кейинчалик қуриб қаттиқ қобиққа айланади.\n\n"
            "💊 <b>Тавсия этиладиган даволаш чоралари ва дорилар (дозалари билан):</b>\n\n"
            "• <b>Агар личинкалар оҳакдек оқ ёки кулранг тошдек қотган бўлса (Аскосфероз):</b>\n"
            "   1. <b>Аскопол</b> ёки <b>Аскоцин</b> пластинкалари: Ҳар 6-8 рамкага 1 тадан уя марказига осилади.\n"
            "   2. <b>Нистатин</b>: 100 000 ТБ 1 литр илиқ шакар сиропига (1:1) қўшилиб, 3-5 кун оралиғида 3 марта кечқурун оилаларга берилади.\n"
            "   3. Уядаги барча нам ёстиқчаларни алмаштириш, уя тубини тозалаб дезинфекция қилиш ва оилани иссиқ, қуруқ жойга кўчириш шарт.\n\n"
            "• <b>Агар личинкалар қўланса ҳид билан ириб эриётган бўлса (Чириш / Гнилец):</b>\n"
            "   1. <b>Окситетрациклин</b> ёки <b>Оксивит</b>: 500 000 ТБ 1 литр илиқ шакар сиропига яхшилаб эритилади. Ҳар бир арили кўча оралиғига 100-150 мл дан 4-5 кун оралиғида 3 марта берилади.\n"
            "   2. Касалланган қора рамкаларни зудлик билан уядан чиқариб ёқиб ташлаш керак.\n"
            "   3. Ариларни олов ёки хлор билан дезинфекция қилинган тоза уяга, янги сунъий мумкатакли (вощина) рамкаларга кўчириш лозим.\n\n"
            "❓ <b>100% аниқ якуний ташхис қўйиш учун қўшимча маълумот керак:</b>\n"
            "1. Личинкаларнинг ранги қандай (оҳакдай оқми ёки сариқ-жигарранг/қорами)?\n"
            "2. Сассиқ дурадгор елими (чириган суяк) ҳиди сезиляптими?\n"
            "3. Гугурт чўпи ёки игна билан текширганда личинка чўзилувчанми ёки тошдек қаттиқми?\n\n"
            "📸 <i>Иложи бўлса, гуруҳга касалланган рамка ва личинкаларнинг яқиндан олинган тиниқ расмини юборинг, дарҳол 100% аниқ ташхис қўйиб берамиз!</i>"
        )

    # Б) Фақат Личинкалар ириши / Гнилец ҳолати
    if has_lichinka and has_irib:
        return (
            "🐝 <b>Asalarichilik.Uz🇺🇿 шифокори хулосаси:</b>\n\n"
            "🔍 <b>Ташхис:</b> <b>Гнилец (Европа ёки Америка чириш касаллиги)</b>\n\n"
            "⚠️ <b>Белгилари ва Сабаби:</b>\n"
            "Очиқ ёки ёпиқ личинкалар ириб, сариқ-жигарранг ёки қора тусга киради. Қопқоқчалари тешилади ва сассиқ, қўланса (дурадгор елими) ҳиди келади. Игна билан текширилса, ипдек чўзилади.\n\n"
            "💊 <b>Даволаш ва дорилар (дозалари билан):</b>\n"
            "1. <b>Окситетрациклин</b> ёки <b>Оксивит</b>: 500 000 ТБ 1 литр шакар сиропига қўшиб ҳар бир кўчага 100-150 мл дан 4-5 кун оралиғида 3-4 марта берилади.\n"
            "2. Касал рамкалар зудлик билан уядан чиқарилиб ёқиб юборилади.\n"
            "3. Арилар тоза дезинфекция қилинган уяга, янги мумли рамкаларга кўчирилади ва она ари янги соғлом онага алмаштирилади.\n\n"
            "❓ <b>Аниқлаштириш учун:</b> Қўланса ҳид борми ва чўзиляптими? Иложи бўлса расмини гуруҳга юборинг!"
        )

    # В) Фақат Личинкалар қотиши / Оҳакли чириш ҳолати
    if has_lichinka and has_qotib:
        return (
            "🐝 <b>Asalarichilik.Uz🇺🇿 шифокори хулосаси:</b>\n\n"
            "🔍 <b>Ташхис:</b> <b>Аскосфероз (Оҳакли чириш / Тош чириш)</b>\n\n"
            "⚠️ <b>Белгилари ва Сабаби:</b>\n"
            "Замбуруғли касаллик бўлиб, личинкалар оҳак сингари оқариб, кейин тошдек қаттиқлашиб қуриб қолади. Арилар уларни уя тубига ва леток олдига ташлаб юборади. Сабаби — уядаги намлик ва оиланинг шамоллаб қолиши.\n\n"
            "💊 <b>Даволаш ва дорилар (дозалари билан):</b>\n"
            "1. <b>Аскопол</b> ёки <b>Аскоцин</b> пластинкалари қўйилади.\n"
            "2. <b>Нистатин</b>: 100 000 ТБ 1 литр сиропга аралаштириб 3 марта берилади.\n"
            "3. Намликни йўқотиш, уяни қуёшли жойга қўйиш, ёстиқчаларни қуритиш шарт.\n\n"
            "❓ <i>Агар бошқа белгилар бўлса ёки расми бўлса гуруҳга юборинг!</i>"
        )

    # Г) Умумий дори сўраш (масалан: "qanaqa dori maslahat qilasizlar")
    if any(w in q_lower for w in ['dori', 'дори', 'preparat', 'препарат']) and not any(k in q_lower for k in OFFLINE_BEE_DISEASES):
        return (
            "🐝 <b>Asalarichilik.Uz🇺🇿 шифокори тавсияси:</b>\n\n"
            "Асаларичиликда дори танлаш касаллик тури ва аломатига қараб белгиланади:\n\n"
            "1. <b>Варроа канасига қарши:</b> Бипин (1 литр сувга 0.5 мл), Варроадез ёки Апистан пластинкалари, Тимол.\n"
            "2. <b>Личинка чириши (Гнилец) учун:</b> Окситетрациклин ёки Оксивит (1 литр сиропга 500 000 ТБ).\n"
            "3. <b>Оҳакли чириш (Аскосфероз/қотиш) учун:</b> Аскопол пластинкалари ёки Нистатин.\n"
            "4. <b>Ич кетиш (Нозематоз) учун:</b> Ноземацид ёки Фумагиллин.\n"
            "5. <b>Вирусли касалликлар ва фалаж учун:</b> Эндоглюкин пуркаш.\n\n"
            "❓ <b>Сизнинг оилангизда қандай аломатлар кузатилмоқда?</b> Личинкалар ҳолати, ариларнинг хатти-ҳаракати ҳақида ёзинг ёки расм юборинг, дарҳол аниқ дорисини айтамиз!"
        )

    # Д) Луғатдан калит сўзлар бўйича қидириш (Лотин ва Кирилл)
    q_search = q_lower.replace("ko'chirish", "ko'chish").replace("chirish", "чириш").replace("askosferoz", "аскосфероз")
    q_search = q_search.replace("nozema", "нозема").replace("varroa", "варроа").replace("kana", "кана")
    q_search = q_search.replace("bipin", "бипин").replace("kuya", "куя").replace("ramka", "рамка")
    q_search = q_search.replace("sirop", "сироп").replace("oziqa", "озуқа").replace("qishlov", "қишлов")
    q_search = q_search.replace("ona ari", "она ари").replace("pritsep", "прицеп").replace("paralich", "паралич")

    # Фақат ҳақиқий касаллик аломатлари ёки дори сўралгандагина офлайн ташхис берилади
    has_disease_indicator = any(w in q_lower for w in DISEASE_SYMPTOM_WORDS)
    if has_disease_indicator:
        for k, dis in sorted(OFFLINE_BEE_DISEASES.items(), key=lambda x: len(x[0]), reverse=True):
            if k in q_search:
                return (
                    f"🐝 <b>Asalarichilik.Uz🇺🇿 шифокори хулосаси:</b>\n\n"
                    f"🔍 <b>Ташхис / Муаммо:</b> <b>{dis['name']}</b>\n\n"
                    f"⚠️ <b>Белгилари ва Сабаби:</b>\n{dis['symptoms']}\n\n"
                    f"💊 <b>Даволаш ва тавсиялар (дозалари билан):</b>\n{dis['treatment']}\n\n"
                    f"🌿 <b>Профилактика чоралари:</b>\n{dis['prevention']}\n\n"
                    f"👨‍⚕️ <i>Қўшимча саволлар ёки расм бўлса, гуруҳга бемалол юборишингиз мумкин.</i>"
                )

    # ---------------- 2. АГАР РАСМ БЎЛСА ЁКИ НОАНИҚ БЎЛСА: GEMINI AI ОРҚАЛИ ТАҲЛИЛ ----------------
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        for model_name in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                sys_instruction = (
                    "Сиз 'Asalarichilik.Uz' лойиҳасининг олий тоифали бош ветеринар шифокори ва мутахассисисиз.\n"
                    "ҚОИДАЛАР (ЖУДА МУҲИМ ВА АНИҚ РИОЯ ҚИЛИНСИН):\n"
                    "1. Агар юборилган матн, расм ёки видео АСАЛАРИЧИЛИККА МУТЛАҚО АЛОҚАСИ БЎЛМАСА (диний занжир хабарлар, сиёсий/дунёвий янгиликлар, машина, телефон, пул топиш рекламаси ва б.) -> фақат битта сўз қайтаринг: OFFTOPIC\n"
                    "2. Агар бу АСАЛАРИЧИЛИК МАҲСУЛОТЛАРИ (АСАЛ) ЁКИ ЖИҲОЗЛАРИНИНГ САВДОСИ, РЕКЛАМАСИ, ОПТОМ/ДОНА СОТУВ ЭЪЛОНИ БЎЛСА (масалан: 'оптом асал', 'асал сотилади', 'асал бор', 'нархи келишилади', прицеп, ромка, уя сотуви) -> фақат битта сўз қайтаринг: COMMERCIAL\n"
                    "   ДИҚҚАТ: Асал сотиш, реклама ёки тижорат эълонларига АСЛО КАСАЛЛИК ТАШХИСИ ҚЎЙМАНГ!\n"
                    "3. Агар фойдаланувчи асалари касаллиги, аломатлари, нобуд бўлиши, чириши, кана, дорилар ёки парвариш муаммоси бўйича сўраган бўлса, ветеринар сифатида қуйидаги расмий форматда тўлиқ жавоб беринг:\n"
                    "🐝 <b>Asalarichilik.Uz🇺🇿 шифокори хулосаси:</b>\n\n"
                    "🔍 <b>Ташхис / Муаммо:</b> (Касаллик ёки масаланинг аниқ номи)\n"
                    "⚠️ <b>Белгилари ва Сабаби:</b> (Нима сабабдан бу ҳолат келиб чиққанлиги)\n"
                    "💊 <b>Даволаш ва дорилар (аниқ дозалари билан):</b> (Қандай препаратлар ва сироплар бериш кераклиги)\n"
                    "🌿 <b>Олдини олиш (Профилактика):</b> (Келгусида такрорланмаслик чоралари)\n"
                    "❓ <b>100% аниқ ташхис учун қўшимча саволлар:</b> (Аломатларни янада аниқроқ билиш учун саволлар ва расм юборишни сўраш)\n"
                    "👨‍⚕️ <i>Маслаҳат: Касалликни эрта босқичда даволаш оилани сақлаб қолади.</i>"
                )

                parts = [{"text": f"{sys_instruction}\n\nФойдаланувчи хабари/саволи: {query_text or 'Ушбу расм ёки видеодаги ҳолатга баҳо беринг.'}"}]
                if photo_bytes:
                    b64_img = base64.b64encode(photo_bytes).decode("utf-8")
                    parts.append({
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_img
                        }
                    })

                payload = {"contents": [{"parts": parts}]}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    ans = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if ans:
                        if "COMMERCIAL" in ans.upper():
                            return "COMMERCIAL"
                        if "OFFTOPIC" in ans.upper():
                            return "OFFTOPIC"
                        return ans
            except Exception as e:
                logging.warning(f"Gemini model {model_name} error: {e}")
                continue

    # ---------------- 3. УМУМИЙ АСАЛАРИЧИЛИК САВОЛЛАРИ ВА ТАШХИС УЧУН СЎРОВ ----------------
    return (
        "🐝 <b>Asalarichilik.Uz🇺🇿 шифокори тавсияси:</b>\n\n"
        "Сизнинг асаларичилик бўйича мурожаатингиз қабул қилинди.\n\n"
        "🔍 <b>Асосий қоидалар:</b>\n"
        "1. <b>Уядаги ҳарорат ва намлик:</b> Уяда доимо қуруқ ва илиқ муҳит бўлиши керак. Намлик ошса личинкалар оҳакланиб (аскосфероз) ва чириб ўлади.\n"
        "2. <b>Озуқа ва сироп:</b> Оилаларда камида 10-15 кг озуқа бўлиши керак. Эрта баҳорда ва кеч кузда илиқ 1:1 шакар сиропи берилади.\n"
        "3. <b>Канага қарши кураш:</b> Йилига 2 марта (асалдан сўнг ва кеч кузда) Бипин билан кўчалар орасига ишлов бериш шарт.\n\n"
        "❓ <b>Аниқ ташхис қўйиш учун:</b>\n"
        "Илтимос, оилангиздаги аломатларни батафсилроқ тасвирлаб беринг ёки касалланган рамка/личинкаларнинг яқиндан олинган тиниқ расмини гуруҳга юборинг!"
    )


# 8. ЎЗБЕКИСТОН ВИЛОЯТЛАРИ ВА ОБ-ҲАВО
REGIONS_UZ_KR = [
    "Барча вилоятлар (Республика)",
    "Тошкент шаҳри ва вилояти", "Андижон вилояти", "Бухоро вилояти", "Жиззах вилояти",
    "Қашқадарё вилояти", "Навоий вилояти", "Наманган вилояти", "Самарқанд вилояти",
    "Сурхондарё вилояти", "Сирдарё вилояти", "Тошкент вилояти", "Фарғона вилояти",
    "Хоразм вилояти", "Қорақалпоғистон Республикаси"
]

REGIONS_UZ_LIST = [
    "Барча вилоятлар (Республика)",
    "Тошкент", "Андижон", "Бухоро", "Жиззах",
    "Қашқадарё", "Навоий", "Наманган", "Самарқанд",
    "Сурхондарё", "Сирдарё", "Тошкент вилояти", "Фарғона",
    "Хоразм", "Қорақалпоғистон"
]

DAYS_NAME_KR = {1: "Душанба", 2: "Сешанба", 3: "Чоршанба", 4: "Пайшанба", 5: "Жума", 6: "Шанба", 7: "Якшанба"}
DAYS_NAME_LAT = {1: "Dushanba", 2: "Seshanba", 3: "Chorshanba", 4: "Payshanba", 5: "Juma", 6: "Shanba", 7: "Yakshanba"}
DAYS_NAME_RU = {1: "Понедельник", 2: "Вторник", 3: "Среда", 4: "Четверг", 5: "Пятница", 6: "Суббота", 7: "Воскресенье"}
DAYS_NAME_EN = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}

def format_repeat_days(days_csv, lang="uz_kr"):
    if not days_csv:
        return "Ҳар куни"
    parts = [d.strip() for d in str(days_csv).split(",") if d.strip().isdigit()]
    if len(parts) == 7:
        if lang == "ru": return "Каждый день"
        if lang == "en": return "Every day"
        if lang == "uz_lat": return "Har kuni"
        return "Ҳар куни"
    mp = DAYS_NAME_RU if lang == "ru" else (DAYS_NAME_EN if lang == "en" else (DAYS_NAME_LAT if lang == "uz_lat" else DAYS_NAME_KR))
    names = [mp[int(p)][:3] for p in parts if int(p) in mp]
    return ", ".join(names)

# ==================== ЁШ АСАЛАРИЧИЛАР УЧУН КУНЛИК ДОЛЗАРБ МАСЛАҲАТЛАР БАЗАСИ ====================
BEEKEEPING_TIPS = [
    {
        "cat": "autumn",
        "title_kr": "Уяларни ихчамлаш ва чеклаш (Кузги парвариш)",
        "title_lat": "Uyalarni ixchamlash va cheklash (Kuzgi parvarish)",
        "title_ru": "Сокращение и утепление гнёзд на зиму",
        "text_kr": "Ҳозирги кузги салқин кунларда арилар босмаган бўш ва эски қора рамкаларни уядан олиб чиқинг. Арилар уяда зич турганда иссиқликни кам сарфлайди ва озуқани тежайди. Ён томонларга диафрагма (чеклагич) ва иситкич ёстиқчалар қўйинг!",
        "text_lat": "Hozirgi kuzgi salqin kunlarda arilar bosmagan bo'sh va eski qora ramkalarni uyadan olib chiqing. Arilar uyada zich turganda issiqlikni kam sarflaydi va ozuqani tejaydi. Yon tomonlarga diafragma va issiq yostiqchalar qo'ying!",
        "text_ru": "Осенью удалите из ульев пустые и старые рамки, не обсиженные пчёлами. Плотное гнездо отлично сохраняет тепло и экономит корма. Установите разделительные доски и утеплители!",
        "icon": "📦"
    },
    {
        "cat": "autumn",
        "title_kr": "Қишлов учун озуқа захираси (Энг муҳим қоида)",
        "title_lat": "Qishlov uchun ozuqa zaxirasi (Eng muhim qoida)",
        "title_ru": "Запас кормов на зиму (Главное правило)",
        "text_kr": "Қишга кираётган ҳар бир оилада камида 15-18 кг сифатли муҳрланган асал ёки қуюқ сироп (2:1) захираси бўлиши шарт. Рамкаларнинг камида 2/3 қисми асал билан тўлган бўлиши керак. Озуқаси кам оилалар совуқда эмас, очликдан ҳалок бўлади!",
        "text_lat": "Qishga kirayotgan har bir oilada kamida 15-18 kg sifatli muhrlangan asal yoki quyuq sirop (2:1) zaxirasi bo'lishi shart. Ramkalarning kamida 2/3 qismi asal bilan to'lgan bo'lsin. Ozuqasi kam oilalar ochlikdan nobud bo'ladi!",
        "text_ru": "Каждой семье на зимовку требуется не менее 15-18 кг качественного запечатанного мёда или густого сиропа (2:1). Рамки должны быть заполнены минимум на 2/3. Пчёлы гибнут зимой не от холода, а от голода!",
        "icon": "🍯"
    },
    {
        "cat": "autumn",
        "title_kr": "Вароа канасига қарши кузги ишлов (Бипин ва кислоталар)",
        "title_lat": "Varroa kanasiga qarshi kuzgi ishlov (Bipin va kislotalar)",
        "title_ru": "Осенняя обработка от варроатоза",
        "text_kr": "Куз фаслида уяда насл (расплод) қолмаганда ёки кескин камайганда канага қарши Бипин ёки органик кислоталар (шовул, чумоли кислотаси) билан ишлов бериш энг юқори (98-99%) самара беради. Ҳарорат +4...+8°C бўлганда сувли эритма пуркалади.",
        "text_lat": "Kuz faslida uyada nasl (rasplod) qolmaganda yoki keskin kamayganda kanaga qarshi Bipin yoki shovul/chumoli kislotasi bilan ishlov berish 99% natija beradi. Harorat +4...+8°C bo'lganda suvli eritma purkaladi.",
        "text_ru": "Поздней осенью, при полном выходе расплода, обработка от варроатоза препаратом Бипин или щавелевой кислотой даёт 99% эффект. Обработку проводят при температуре от +4 до +8°C.",
        "icon": "🔬"
    },
    {
        "cat": "autumn",
        "title_kr": "Уялардаги намлик ва ҳаво айланиши (Вентиляция)",
        "title_lat": "Uyalardagi namlik va havo aylanishi (Ventilyatsiya)",
        "title_ru": "Вентиляция ульев и защита от сырости",
        "text_kr": "Ёш асаларичилар билиши шарт: ари совуқдан қўрқмайди, у уядаги намлик ва димликдан ҳалок бўлади! Юқориги дарча ёки мато (холстик) орқа четидан кичик ҳаво чиқиш тирқиши қолдиринг, намлик ташқарига чиқиб кетиши керак.",
        "text_lat": "Yosh asalarichilar bilishi shart: ari sovuqdan qo'rqmaydi, u uyadagi namlik va dimlikdan halok bo'ladi! Yuqorigi darcha yoki matoning orqa chetidan havo tirqishi qoldiring, namlik chiqib ketsin.",
        "text_ru": "Молодым пчеловодам на заметку: пчёлы не боятся мороза, их губит сырость и духота! Обеспечьте правильную вентиляцию через верхний леток или отгиб холстика для выхода сырого воздуха.",
        "icon": "💨"
    },
    {
        "cat": "autumn",
        "title_kr": "Сичқон ва кемирувчилардан ҳимоя",
        "title_lat": "Sichqon va kemiruvchilardan himoya",
        "title_ru": "Защита ульев от грызунов",
        "text_kr": "Куз тушиши билан дала сичқонлари уя ичига иссиқ жой излаб киришга интилади. Уя кириш дарчаси (леток) баландлигини 7-8 мм гача туширинг ёки сичқонларга қарши металл тўсиқ панжараларни ўрнатинг!",
        "text_lat": "Kuz tushishi bilan dala sichqonlari uya ichiga issiq joy izlab kirishga intiladi. Uya kirish darchasi balandligini 7-8 mm gacha tushiring yoki metall to'siq panjaralarni o'rnating!",
        "text_ru": "С наступлением осенних холодов мыши ищут тёплые места. Уменьшите высоту летков до 7-8 мм или установите металлические летковые заградители от грызунов!",
        "icon": "🐭"
    },
    {
        "cat": "autumn",
        "title_kr": "Кузги озиқлантириш вақти ва қоидаси",
        "title_lat": "Kuzgi oziqlantirish vaqti va qoidasi",
        "title_ru": "Правила осеннего закармливания",
        "text_kr": "Кузда сироп фақат кечқурун, арилар учиши батамом тўхтагач илиқ ҳолда берилади. Кундузи берилса, арихонада ўғирлик (напад) бошланиб, кучсиз оилалар таланиб кетиши мумкин!",
        "text_lat": "Kuzda sirop faqat kechqurun, arilar uchishi batamom to'xtagach iliq holda beriladi. Kunduzi berilsa, arixonada o'g'irlik (napad) boshlanib, kuchsiz oilalar talanib ketishi mumkin!",
        "text_ru": "Осенний сироп раздавайте строго поздно вечером, когда лёт пчёл завершён. Дневная раздача корма неминуемо вызовет воровство (напад) и гибель слабых семей!",
        "icon": "🥣"
    },
    {
        "cat": "general",
        "title_kr": "Дудлатгич (дымарь) билан ишлаш маҳорати",
        "title_lat": "Dudlatgich (dimar) bilan ishlash mahorati",
        "title_ru": "Правильная работа с дымарём",
        "text_kr": "Ариларга алангали иссиқ тутун эмас, совуқ ва қуюқ тутун керак! Дудлатгичга чириган қайин ёғочи, қуриқ тезак ёки ёнғоқ пўстлоғи солиш яхши самара беради. Тутунни тўғридан-тўғри уя ичига эмас, рамкалар устидан енгил пурканг.",
        "text_lat": "Arilarga alangalangan issiq tutun emas, sovuq va quyuq tutun kerak! Dudlatgichga chirigan yog'och yoki quruq tezak soling. Tutunni uya ichiga emas, ramkalar ustidan yengil purkang.",
        "text_ru": "Дым должен быть прохладным и густым, без искр и открытого огня. Используйте сухую гнилушку или сухой навоз. Направляйте дым поверх рамок, не обжигая пчёл.",
        "icon": "💨"
    },
    {
        "cat": "general",
        "title_kr": "Асаларичининг кийими ва гигиенаси",
        "title_lat": "Asalarichining kiyimi va gigiyenasi",
        "title_ru": "Одежда и гигиена пасечника",
        "text_kr": "Арилар қора ранг, жунли матолар ва кескин ҳидларни (тер, спирт, парфюм, саримсоқ) ёқтирмайди ва чақишга интилади. Арихонага фақат тоза, оқ ёки оч рангдаги пахта матоли кийим ва тўрли қалпоқ кийиб киринг!",
        "text_lat": "Arilar qora rang, junli matolar va o'tkir hidlarni (ter, spirt, atir, sarimsoq) yoqtirmaydi. Arixonaga faqat toza, oq paxta kiyim va to'rli qalpoq bilan kiring!",
        "text_ru": "Пчёлы резко реагируют на тёмную ворсистую одежду и запахи (пот, алкоголь, парфюм, чеснок). Работайте исключительно в чистом светлом хлопчатобумажном комбинезоне и лицевой сетке!",
        "icon": "👔"
    },
    {
        "cat": "general",
        "title_kr": "Уя устида хотиржам ҳаракат қилинг",
        "title_lat": "Uya ustida xotirjam harakat qiling",
        "title_ru": "Спокойствие при осмотре улья",
        "text_kr": "Уя устида ҳеч қачон қўлингизни кескин силтаманг ва ариларни уриб ўлдирманг! Ўлган аридан ажралган ҳид бутун оилани тажовузкор қилади ва ёппасига ҳужумга ундайди. Ҳаракатлар силлиқ, дадил ва хотиржам бўлсин.",
        "text_lat": "Uya ustida qo'lingizni keskin siltamang va arini urib o'ldirmang! O'lgan arining hidi butun oilani tajovuzkor qilib hujumga undaydi. Harakatlar silliq va xotirjam bo'lsin.",
        "text_ru": "Никогда не делайте резких движений и не давите пчёл на рамках! Запах раздавленной пчелы служит сигналом тревоги и вызывает атаку всей семьи. Работайте плавно и аккуратно.",
        "icon": "🧘‍♂️"
    },
    {
        "cat": "general",
        "title_kr": "Арихона дафтари (Пасечный журнал)",
        "title_lat": "Arixona daftari (Pasechniy jurnal)",
        "title_ru": "Ведение пасечного журнала",
        "text_kr": "Ҳар бир бошловчи асаларичи махсус дафтар тутиши шарт! Уя рақами, она арининг чиққан йили, оиланинг кучи (кўчалар сони), озуқа миқдори ва қилинган ишларни санаси билан ёзиб боринг. Бу хатоларнинг олдини олади!",
        "text_lat": "Har bir boshlovchi asalarichi maxsus daftar tutishi shart! Uya raqami, ona arining yili, oila kuchi, ozuqa miqdori va qilingan ishlarni yozib boring. Bu xatolarning oldini oladi!",
        "text_ru": "Всегда ведите пасечный журнал! Записывайте номер улья, возраст матки, силу семьи в улочках, запас корма и проведённые работы. Точные записи — залог успеха!",
        "icon": "📖"
    },
    {
        "cat": "warm_sunny",
        "title_kr": "Сувдон (поилка) аҳамияти ва тузли сув",
        "title_lat": "Suvdon (poilka) ahamiyati va tuzli suv",
        "title_ru": "Организация пасечной поилки",
        "text_kr": "Илиқ қуёшли кунларда арихонага қуёш нурида исийдиган тоза сувдон қўйинг. Сувга бироз ош тузи (1 литр сувга 1 грамм) қўшиш ариларнинг ҳазм қилиш тизими ва личинкалар парвариши учун жуда фойдали!",
        "text_lat": "Iliq quyoshli kunlarda arixonaga quyoshda isiydigan toza suvdon qo'ying. Suvga biroz osh tuzi (1 litr suvga 1 gramm) qo'shish arilarning hazm qilish tizimi uchun juda foydali!",
        "text_ru": "В тёплые дни установите на пасеке поилку с чуть подсоленной тёплой водой (1 г соли на 1 л воды). Пчёлы охотно берут подогретую солнцем воду и не гибнут в холодных лужах.",
        "icon": "💧"
    },
    {
        "cat": "warm_sunny",
        "title_kr": "Тезкор кўрик ва она арини эҳтиётлаш",
        "title_lat": "Tezkor ko'rik va ona arini ehtiyotlash",
        "title_ru": "Быстрый осмотр и сохранность матки",
        "text_kr": "Илиқ кунда уяларни кўришга тўғри келса, кўрикни жуда тез (3-4 дақиқада) тугатинг. Рамкаларни узоқ очиқ ҳавода ушлаб турманг, она арини тасодифан рамкалар орасига қисиб қўймасликка ўта эҳтиёт бўлинг!",
        "text_lat": "Iliq kunda uyalarni ko'rishga to'g'ri kelsa, ko'rikni juda tez (3-4 daqiqada) tugating. Ramkalarni uzoq ushlab turmang, ona arini siqib qo'ymaslikka ehtiyot bo'ling!",
        "text_ru": "Осенние осмотры проводите быстро (не более 3-4 минут). Не держите рамки на ветру и следите, чтобы случайно не придавить плодную матку плечиками рамок.",
        "icon": "⏱"
    },
    {
        "cat": "cold_rain",
        "title_kr": "Салқин ва ёмғирли кунларда уяни асло очманг!",
        "title_lat": "Salqin va yomg'irli kunlarda uyani aslo ochmang!",
        "title_ru": "Не открывайте ульи в холод и дождь!",
        "text_kr": "Ҳаво ҳарорати +14°C дан паст бўлганда, ёмғир ёки кучли шамолда уя қопқоғини очиш қатъиян ман этилади! Уя ичидаги иссиқлик тарқаб кетса, личинкалар совуқ уриб нобуд бўлади ва оила заифлашади.",
        "text_lat": "Havo harorati +14°C dan past bo'lganda, yomg'ir yoki kuchli shamolda uya qopqog'ini ochmang! Uya ichidagi issiqlik tarqab ketadi va lichinkalar sovub nobud bo'ladi.",
        "text_ru": "При температуре ниже +14°C, в дождь или сильный ветер открывать ульи строго запрещено! Мгновенная потеря тепла приводит к застуживанию расплода и болезням.",
        "icon": "🌧"
    },
    {
        "cat": "cold_rain",
        "title_kr": "Уя усти томлари ва шамолга чидамлилик",
        "title_lat": "Uya usti tomlari va shamolga chidamlilik",
        "title_ru": "Надёжное крепление крыш ульев",
        "text_kr": "Ёмғирли ва шамолли кунларда сув уя ичига оқмаслиги ва қопқоқ учиб кетмаслиги учун устига оғирроқ тош ёки ғишт бостириб қўйинг. Уяни олд томонга 2-3 градус эгикроқ ўрнатиш сув киришини тўхтатади.",
        "text_lat": "Yomg'irli va shamolli kunlarda suv uya ichiga oqmasligi uchun ustiga g'isht yoki tosh bostirib qo'ying. Uya oldinga 2-3 gradus egik o'rnatilsin.",
        "text_ru": "Закрепите крыши ульев грузом (кирпичом). Небольшой уклон корпуса вперёд на 2-3 градуса предотвратит затекание дождевой воды внутрь через прилётную доску.",
        "icon": "💨"
    },
    {
        "cat": "spring",
        "title_kr": "Баҳорги биринчи кўрик ва тубдон тозалаш",
        "title_lat": "Bahorgi birinchi ko'rik va tubdon tozalash",
        "title_ru": "Весенняя ревизия и чистка доньев",
        "text_kr": "Эрта баҳорда ҳаво +14...+15°C га етганда уя тубдонларини қишки ўлик арилардан (подмор) зудлик билан тозаланг. Чиқиндиларни ёқиб юборинг, чунки унда касаллик қўзғатувчилар сақланган бўлади!",
        "text_lat": "Erta bahorda havo +14...+15°C ga yetganda uya tubdonlarini qishki o'lik arilardan tozalang. Chiqindilarni yoqib yuboring, unda kasalliklar bo'lishi mumkin!",
        "text_ru": "При первом весеннем потеплении очистите донья ульев от подмора и продезинфицируйте их. Собранный подмор сожгите во избежание распространения инфекций.",
        "icon": "🧹"
    },
    {
        "cat": "spring",
        "title_kr": "Баҳорги рағбатлантирувчи озиқлантириш",
        "title_lat": "Bahorgi rag'batlantiruvchi oziqlantirish",
        "title_ru": "Весенняя побудительная подкормка",
        "text_kr": "Баҳорда она ари кўп тухум қўйиши ва оила тез ривожланиши учун ҳар 1-2 кунда 200-300 граммдан илиқ сироп (1:1) ёки асалли тўйимли озуқа берилади. Бу она арини рағбатлантиради!",
        "text_lat": "Bahorda ona ari ko'p tuxum qo'yishi uchun har 1-2 kunda 200-300 grammdan iliq sirop (1:1) yoki asalli to'yimli ozuqa bering. Bu tuxum qo'yishni tezlashtiradi!",
        "text_ru": "Весной для стимулирования яйцекладки матки давайте небольшие порции тёплого сиропа (1:1) по 250-300 г через день, имитируя поддерживающий взяток.",
        "icon": "🌸"
    },
    {
        "cat": "summer",
        "title_kr": "Ёзги иссиқда уяларни сояга олиш",
        "title_lat": "Yozgi issiqda uyalarni soyaga olish",
        "title_ru": "Защита ульев от летнего зноя",
        "text_kr": "Ёзда ҳаво +35°C дан ошганда уяларни дарахтлар соясига олинг ёки устига қамиш, оқ мато ёпинг. Акс ҳолда момлар эриб оқиб кетади ва личинкалар димиқиб нобуд бўлади!",
        "text_lat": "Yozda havo +35°C dan oshganda uyalarni daraxtlar soyasiga oling yoki ustiga qamish, oq mato yoping. Aks holda momlar erib ketadi va lichinkalar nobud bo'ladi!",
        "text_ru": "При жаре выше +35°C притеняйте ульи светлым полотном или ветками. Перегрев приводит к размягчению вощины, обрыву сотов и гибели расплода.",
        "icon": "🔥"
    },
    {
        "cat": "summer",
        "title_kr": "Қўшимча корпус (магазин)ларни вақтида қўйиш",
        "title_lat": "Qo'shimcha korpus (magazin)larni vaqtida qo'yish",
        "title_ru": "Своевременная постановка магазинов",
        "text_kr": "Асосий асал йиғими бошланганда кучли оилаларга вақтида магазин ёки иккинчи корпусни қўйинг. Уяда жой етмаса, арилар роялик кайфиятига тушиб, асал йиғишни тўхтатади!",
        "text_lat": "Asosiy asal yig'imi boshlanganda kuchli oilalarga vaqtida magazin yoki ikkinchi korpusni qo'ying. Joy yetmasa, arilar royaga tushib asal yig'ishni to'xtatadi!",
        "text_ru": "В период медосбора вовремя ставьте вторые корпуса и магазинные надставки. Теснота провоцирует роение и срывает сбор товарного мёда!",
        "icon": "🏛"
    },
    {
        "cat": "autumn",
        "title_kr": "Арилар тутами (клуб) ва қишдаги ҳарорат мўъжизаси",
        "title_lat": "Arilar tutami (klub) va qishdagi harorat mo'jizasi",
        "title_ru": "Зимний клуб пчёл и температурный феномен",
        "text_kr": "🔬 <b>Қизиқарли факт:</b> Қишда ташқарида совуқ -20°C бўлса ҳам, уя ичидаги ари тутами (клуб) марказида ҳарорат доим +30...+34°C да сақланади! Арилар учиш мушакларини тебратиш орқали иссиқлик ишлаб чиқарадилар. Бу иссиқликни сақлаш учун кузда уяда ҳеч қачон ортиқча бўш рамкалар қолдирманг ва уяни ихчамланг!",
        "text_lat": "🔬 <b>Qiziqarli fakt:</b> Qishda tashqarida -20°C bo'lsa ham, uya ichidagi ari tutami markazida harorat doim +30...+34°C saqlanadi! Arilar mushaklarini tebratib issiqlik ishlab chiqaradi. Bu issiqlikni saqlash uchun uyada ortiqcha bo'sh ramka qoldirmang!",
        "text_ru": "🔬 <b>Интересный факт:</b> Даже при морозе -20°C, внутри зимнего клуба пчёл температура поддерживается на уровне +30...+34°C за счёт микроколебаний грудных мышц. Чтобы пчёлы не тратили лишнюю энергию, гнездо обязательно должно быть плотно сжато!",
        "icon": "❄️"
    },
    {
        "cat": "general",
        "title_kr": "Асалариларнинг мулоқот рақси (Фон Фриш кашфиёти)",
        "title_lat": "Arilarning muloqot raqsi (Fon Frish kashfiyoti)",
        "title_ru": "Танец пчёл — уникальный язык общения",
        "text_kr": "💃 <b>Қизиқарли факт:</b> Қидирувчи арилар янги гулзор ёки озуқа манбаини топганда, уяга қайтиб махсус «доирасимон» ва «тебранувчи» рақс тушадилар. Рақс йўналиши ва тебраниш тезлиги орқали озуқанинг қуёшга нисбатан бурчаги ва 5 км гача бўлган аниқ масофасини бошқа ариларга хабар берадилар!",
        "text_lat": "💃 <b>Qiziqarli fakt:</b> Qidiruvchi arilar yangi ozuqa manbaini topganda, uyaga qaytib maxsus raqs tushadilar. Raqs orqali ozuqaning quyoshga nisbatan burchagi va 5 km gacha bo'lgan aniq masofasini boshqa arilarga yetkazadilar!",
        "text_ru": "💃 <b>Интересный факт:</b> Пчёлы-разведчицы сообщают о найденном медоносе при помощи кругового и виляющего танца, передавая точный угол относительно солнца и расстояние до источника корма до 5 км!",
        "icon": "💃"
    },
    {
        "cat": "autumn",
        "title_kr": "Прополис (ари елими) — уянинг табиий антибиотиги",
        "title_lat": "Propolis (ari yelimi) — uyaning tabiiy antibiotigi",
        "title_ru": "Прополис — природный антибиотик пасеки",
        "text_kr": "🛡 <b>Қизиқарли факт:</b> Кузда арилар уядаги барча тирқишларни прополис билан суваб чиқади. Прополис фақат иссиқликни сақлаб қолмай, кучли бактерия, вирус ва моғор ўлдирувчи хусусиятга эга бўлиб, қиш бўйи уя ҳавосини тоза ва мутлақо стерил сақлайди.",
        "text_lat": "🛡 <b>Qiziqarli fakt:</b> Kuzda arilar uyadagi barcha tirqishlarni propolis bilan suvab chiqadi. Propolis faqat issiqlikni saqlamay, kuchli bakteriya va virus o'ldiruvchi xususiyatga ega bo'lib, qish bo'yi uya havosini steril saqlaydi.",
        "text_ru": "🛡 <b>Интересный факт:</b> Осенью пчёлы заделывают все щели прополисом. Прополис — мощнейший природный бактерицид, уничтожающий вирусы и споры плесени, обеспечивая абсолютную стерильность гнезда зимой.",
        "icon": "🛡"
    },
    {
        "cat": "general",
        "title_kr": "Она ари (матка)нинг ёши ва оила унумдорлиги",
        "title_lat": "Ona ari (matka)ning yoshi va oila unumdorligi",
        "title_ru": "Возраст матки и продуктивность семьи",
        "text_kr": "👑 <b>Ёш асаларичига тавсия:</b> 1-2 ёшли ёш она ари кунига 1500-2000 тагача тухум қўяди ва оилани роя кайфиятига туширмайди. 3 ёшдан ошган она ариларнинг насл бериш қобилияти пасаяди ва оила кучсизланиб қолади. Она арини ҳар 2 йилда ёшартириб боринг!",
        "text_lat": "👑 <b>Yosh asalarichiga tavsiya:</b> 1-2 yoshli ona ari kuniga 1500-2000 tagacha tuxum qo'yadi va oilani royaga tushirmaydi. 3 yoshdan oshgach nasl berish pasayadi. Ona arini har 2 yilda yoshartirib boring!",
        "text_ru": "👑 <b>Совет начинающим:</b> Молодые 1-2 летние матки откладывают до 2000 яиц в сутки и предотвращают роение. С трёх лет яйценоскость резко падает. Регулярная смена маток каждые 2 года — главный залог медосбора!",
        "icon": "👑"
    }
]

def generate_weather_report(region_name="Тошкент", forecast_type="10_days", repeat_days="1,2,3,4,5,6,7", del_hours=2, del_mins=0, lang="uz_kr"):
    now = datetime.now()
    clean_reg = region_name.replace(" вилояти", "").replace(" шаҳри ва вилояти", "").replace(" шаҳри", "")
    days_cnt = 1 if forecast_type == "1_day" else (3 if forecast_type == "3_days" else 10)
    
    # Ўзбекистон фаслларига мос ҳарорат базаси
    MONTH_CLIMATE = {
        1: (4, 9, -5, 1),
        2: (7, 13, -2, 4),
        3: (14, 20, 3, 9),
        4: (20, 26, 9, 15),
        5: (26, 32, 14, 19),
        6: (32, 38, 19, 24),
        7: (34, 40, 21, 26),
        8: (32, 38, 19, 24),
        9: (26, 32, 13, 18),
        10: (17, 24, 6, 12),
        11: (10, 17, 1, 7),
        12: (4, 10, -4, 2)
    }

    # ЁШ АСАЛАРИЧИЛАР УЧУН КУНЛИК ТАВСИЯНИ ТАНЛАШ
    cur_m = now.month
    if cur_m in [9, 10, 11]:
        cur_season = "autumn"
    elif cur_m in [12, 1, 2]:
        cur_season = "cold_rain"
    elif cur_m in [3, 4, 5]:
        cur_season = "spring"
    else:
        cur_season = "summer"

    matching_tips = [t for t in BEEKEEPING_TIPS if t.get("cat") in [cur_season, "general"]]
    if not matching_tips:
        matching_tips = BEEKEEPING_TIPS
    tip_seed = (now.year * 1000 + now.timetuple().tm_yday * 24 + now.hour) % len(matching_tips)
    chosen_tip = matching_tips[tip_seed]

    t_icon = chosen_tip.get("icon", "💡")
    if lang == "ru":
        tip_hdr = "💡 <b>СОВЕТ И ФАКТ ДНЯ ДЛЯ НАЧИНАЮЩИХ ПЧЕЛОВОДОВ:</b>"
        t_title = chosen_tip.get("title_ru", "")
        t_text = chosen_tip.get("text_ru", "")
    elif lang == "uz_lat":
        tip_hdr = "💡 <b>YOSH VA YANGI ASALARICHILAR UCHUN KUN TAVSIYASI VA QIZIQARLI MA'LUMOT:</b>"
        t_title = chosen_tip.get("title_lat", "")
        t_text = chosen_tip.get("text_lat", "")
    else:
        tip_hdr = "💡 <b>ЯНГИ ВА ЁШ АСАЛАРИЧИЛАР УЧУН КУНЛИК ҚИЗИҚАРЛИ МАЪЛУМОТ ВА ТАВСИЯ:</b>"
        t_title = chosen_tip.get("title_kr", "")
        t_text = chosen_tip.get("text_kr", "")

    # ТЕКШИРУВ: БАРЧА ВИЛОЯТЛАР (УМУМРЕСПУБЛИКА КУНЛИК БАШОРАТИ)
    is_all_regions = any(kw in region_name.lower() for kw in ["барча", "бутун", "республика", "все регион", "all region"])
    if is_all_regions:
        day_num = now.isoweekday()
        if lang == "ru":
            title_hdr = "⛅️ <b>ПРОГНОЗ ПОГОДЫ — ВСЕ РЕГИОНЫ УЗБЕКИСТАНА</b>"
            m_str = RU_MONTHS[cur_m - 1]
            sub_hdr = f"🗓 {now.day}-{m_str}, {DAYS_NAME_RU.get(day_num, '')} | Ежедневный обзор по всей Республике"
        elif lang == "uz_lat":
            title_hdr = "⛅️ <b>OB-HAVO MA'LUMOTI — BARCHA VILOYATLAR (O'ZBEKISTON)</b>"
            m_str = UZ_MONTHS_LAT[cur_m - 1]
            sub_hdr = f"🗓 {now.day}-{m_str}, {DAYS_NAME_LAT.get(day_num, '')} | Kunlik umumrespublika ob-havo bayoni"
        elif lang == "en":
            title_hdr = "⛅️ <b>WEATHER FORECAST — ALL REGIONS OF UZBEKISTAN</b>"
            m_str = EN_MONTHS[cur_m - 1]
            sub_hdr = f"🗓 {m_str} {now.day}, {DAYS_NAME_EN.get(day_num, '')} | Daily Nationwide Summary"
        else:
            title_hdr = "⛅️ <b>ОБ-ҲАВО МАЪЛУМОТИ — БАРЧА ВИЛОЯТЛАР (ЎЗБЕКИСТОН)</b>"
            m_str = UZ_MONTHS[cur_m - 1]
            sub_hdr = f"🗓 {now.day}-{m_str}, {DAYS_NAME_KR.get(day_num, '')} | Кунлик умумреспублика об-ҳаво баёни"

        lines = [title_hdr, sub_hdr, "───────────────────"]

        REG_ZONES = [
            ("Тошкент шаҳри ва вилояти", 0, "4-8 м/с"),
            ("Фарғона водийси (Андижон, Наманган, Фарғона)", 1, "3-6 м/с"),
            ("Самарқанд ва Жиззах вилоятлари", 0, "4-7 м/с"),
            ("Бухоро ва Навоий вилоятлари", 1, "5-9 м/с"),
            ("Қашқадарё ва Сурхондарё вилоятлари", 3, "3-7 м/с"),
            ("Сирдарё вилояти", 0, "4-8 м/с"),
            ("Хоразм вилояти ва Қорақалпоғистон", -2, "5-10 м/с")
        ]

        base_d_min, base_d_max, base_n_min, base_n_max = MONTH_CLIMATE.get(cur_m, (17, 24, 6, 12))
        base_mid = (base_d_min + base_d_max) // 2

        for r_name, r_offset, r_wind in REG_ZONES:
            t_d = max(base_d_min, min(base_d_max + 2, base_mid + r_offset))
            t_n = max(base_n_min, t_d - 11)

            if t_d >= 18 and t_d <= 30:
                bee_st = "🟢 Жуда қулай (Арилар фаол)"
            elif t_d >= 12 and t_d < 18:
                bee_st = "🟡 Ўртача қулай (Салқин)"
            elif t_d > 30:
                bee_st = "🟠 Иссиқ (Сувдон назорати)"
            else:
                bee_st = "🔴 Совуқ (Уяни очманг)"

            if cur_m in [12, 1, 2]:
                cond_txt = "☀️ Очиқ, қуёшли ва совуқ" if r_offset >= 0 else "⛅️ Булутли, қор эҳтимоли"
            elif cur_m in [6, 7, 8]:
                cond_txt = "☀️ Иссиқ ва қуёшли"
            else:
                cond_txt = "☀️ Очиқ, илиқ кузги қуёш" if r_offset >= 0 else "🌤 Ўзгарувчан булутли"

            lines.append(f"📍 <b>{r_name}:</b>")
            lines.append(f"☀️ Кундузи: +{t_d}°C | 🌙 Кечаси: +{t_n}°C")
            lines.append(f"🌤 Ҳолат: {cond_txt} | 💨 Шамол: {r_wind}")
            lines.append(f"🐝 Асаларичилик: {bee_st}")
            lines.append("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")

        lines.append("───────────────────")
        lines.append(tip_hdr)
        lines.append(f"{t_icon} <b>{t_title}:</b>")
        lines.append(f"{t_text}")
        lines.append("───────────────────")

        if del_hours == 0 and del_mins == 0:
            lines.append("📌 <i>Ушбу об-ҳаво маълумоти гуруҳда доимий сақланади (ўчирилмайди).</i>")
        else:
            lines.append(f"⏱ <i>Хабар {del_hours} соат {del_mins} дақиқадан сўнг автоматик ўчирилади.</i>")
        lines.append(f"🐝 <b>@{BOT_USERNAME}</b> — @JamshidjonDavronov")
        return "\n".join(lines)

    # 1. Сарлавҳа (Бир ҳудуд учун)
    if lang == "ru":
        title_hdr = f"⛅️ <b>ПРОГНОЗ ПОГОДЫ — {clean_reg.upper()}</b>"
        sub_hdr = f"🗓 Подробный прогноз на {days_cnt} {'день' if days_cnt == 1 else ('дня' if days_cnt == 3 else 'дней')}"
    elif lang == "en":
        title_hdr = f"⛅️ <b>WEATHER FORECAST — {clean_reg.upper()}</b>"
        sub_hdr = f"🗓 Detailed forecast for {days_cnt} {'day' if days_cnt == 1 else 'days'}"
    elif lang == "uz_lat":
        title_hdr = f"⛅️ <b>OB-HAVO MA'LUMOTI — {clean_reg.upper()}</b>"
        sub_hdr = f"🗓 {days_cnt} kunlik batafsil ob-havo bashorati"
    else:
        title_hdr = f"⛅️ <b>ОБ-ҲАВО МАЪЛУМОТИ — {clean_reg.upper()}</b>"
        sub_hdr = f"🗓 {days_cnt} кунлик батафсил об-ҳаво башорати"
        
    lines = [title_hdr, sub_hdr, "───────────────────"]

    # Вилоятлар бўйича микро-иқлим тузатишлари:
    reg_offset = 0
    if any(s in clean_reg for s in ["Сурхондарё", "Қашқадарё", "Surxondaryo", "Qashqadaryo"]):
        reg_offset = 3
    elif any(s in clean_reg for s in ["Қорақалпоғистон", "Хоразм", "Qoraqalpog'iston", "Xorazm"]):
        reg_offset = -2
    elif any(s in clean_reg for s in ["Фарғона", "Андижон", "Наманган", "Farg'ona", "Andijon", "Namangan"]):
        reg_offset = 1

    first_day_temp = 20
    first_day_cond = "sunny"
    
    for i in range(days_cnt):
        target_date = now + timedelta(days=i)
        day_num = target_date.isoweekday()
        m_idx = target_date.month
        
        base_d_min, base_d_max, base_n_min, base_n_max = MONTH_CLIMATE.get(m_idx, (17, 24, 6, 12))
        base_mid = (base_d_min + base_d_max) // 2 + reg_offset
        
        # Кунлик табиий ўзгаришлар (тўлқин):
        day_wave = ((target_date.day * 7 + i * 4) % 7) - 3
        t_day = max(base_d_min, min(base_d_max + 2, base_mid + day_wave))
        t_night = max(base_n_min, t_day - 11)
        
        if i == 0:
            first_day_temp = t_day
            
        # Об-ҳаво ҳолати вариантлари (фаслга қараб):
        cond_idx = (target_date.day + i * 2) % 5
        if m_idx in [12, 1, 2]: # Қиш
            conds_kr = ["☀️ Очиқ, қуёшли ва совуқ", "⛅️ Булутли, майин қор эҳтимоли", "🌤 Ўзгарувчан булутли", "❄️ Қорли ва совуқ шабада", "☀️ Қуёшли, тоза ҳаво"]
            conds_lat = ["☀️ Ochiq, quyoshli va sovuq", "⛅️ Bulutli, qor ehtimoli", "🌤 O'zgaruvchan bulutli", "❄️ Qorli va sovuq shamol", "☀️ Quyoshli, toza havo"]
            conds_ru = ["☀️ Ясно, солнечно и морозно", "⛅️ Облачно, возможен снег", "🌤 Переменная облачность", "❄️ Снежно, холодный ветер", "☀️ Солнечно, чистый воздух"]
        elif m_idx in [6, 7, 8]: # Ёз
            conds_kr = ["☀️ Очиқ, жуда иссиқ ва қуёшли", "🌤 Мусаффо қуёшли, тоза ҳаво", "☀️ Қуёшли ва қайноқ кун", "🌤 Салқин кечки шабада", "☀️ Иссиқ ва қуёшли"]
            conds_lat = ["☀️ Ochiq, juda issiq va quyoshli", "🌤 Musaffo quyoshli, toza havo", "☀️ Quyoshli va qaynoq kun", "🌤 Salqin kechki shamol", "☀️ Issiq va quyoshli"]
            conds_ru = ["☀️ Ясно, очень жарко и солнечно", "🌤 Безоблачно, чистый воздух", "☀️ Солнечный знойный день", "🌤 Прохладный вечерний ветерок", "☀️ Жарко и солнечно"]
        else: # Куз ва Баҳор (Октябрь, Ноябрь, Март, Апрель, Май)
            conds_kr = ["☀️ Очиқ, илиқ кузги қуёш", "🌤 Ўзгарувчан булутли, майин шабада", "⛅️ Булутли ва салқин", "🌦 Қисқа муддатли майин ёмғир", "☀️ Мусаффо қуёшли, тоза ҳаво"]
            conds_lat = ["☀️ Ochiq, iliq kuzgi quyosh", "🌤 O'zgaruvchan bulutli, mayin shamol", "⛅️ Bulutli va salqin", "🌦 Qisqa muddatli mayin yomg'ir", "☀️ Musaffo quyoshli, toza havo"]
            conds_ru = ["☀️ Ясно, тёплое осеннее солнце", "🌤 Переменная облачность, лёгкий бриз", "⛅️ Облачно и прохладно", "🌦 Кратковременный мелкий дождь", "☀️ Безоблачно, чистый воздух"]
            
        w_status_kr = conds_kr[cond_idx]
        w_status_lat = conds_lat[cond_idx]
        w_status_ru = conds_ru[cond_idx]
        
        wind_speeds = ["3-6 м/с", "4-8 м/с", "2-5 м/с", "5-9 м/с", "3-7 м/с"]
        w_speed = wind_speeds[cond_idx]
        
        if lang == "ru":
            w_day = DAYS_NAME_RU.get(day_num, "")
            m_str = RU_MONTHS[target_date.month - 1]
            date_label = f"{target_date.day}-{m_str} ({w_day})"
            w_status = w_status_ru
            wind_lbl = f"Ветер: {w_speed}"
        elif lang == "en":
            w_day = DAYS_NAME_EN.get(day_num, "")
            m_str = EN_MONTHS[target_date.month - 1]
            date_label = f"{m_str} {target_date.day} ({w_day})"
            w_status = "Clear, sunny" if cond_idx == 0 else ("Partly cloudy" if cond_idx == 1 else "Overcast")
            wind_lbl = f"Wind: {w_speed}"
        elif lang == "uz_lat":
            w_day = DAYS_NAME_LAT.get(day_num, "")
            m_str = UZ_MONTHS_LAT[target_date.month - 1]
            date_label = f"{target_date.day}-{m_str} ({w_day})"
            w_status = w_status_lat
            wind_lbl = f"Shamol: {w_speed}"
        else:
            w_day = DAYS_NAME_KR.get(day_num, "")
            m_str = UZ_MONTHS[target_date.month - 1]
            date_label = f"{target_date.day}-{m_str} ({w_day})"
            w_status = w_status_kr
            wind_lbl = f"Шамол: {w_speed}"
            
        lines.append(f"📅 <b>{date_label}</b>")
        lines.append(f"☀️ Кундузи: +{t_day}°C | 🌙 Кечаси: +{t_night}°C")
        lines.append(f"🌤 Ҳолат: {w_status} | 💨 {wind_lbl}")
        
        # Асаларичилик учун муҳит баҳоси:
        if "ёмғир" in w_status_kr.lower() or "дождь" in w_status_ru.lower():
            bee_eval = "🐝 <b>Асаларичилик:</b> 🌧 <i>Ёмғирли/Нам</i> (Арилар уядан чиқмайди, уяларни очманг ва намликдан асранг)."
        elif t_day >= 18 and t_day <= 30:
            bee_eval = "🐝 <b>Асаларичилик:</b> 🟢 <i>Жуда қулай</i> (Арилар фаол учади, тозаланиш облётлари ва озуқа ўзлаштириш юқори)."
        elif t_day >= 12 and t_day < 18:
            bee_eval = "🐝 <b>Асаларичилик:</b> 🟡 <i>Ўртача қулай</i> (Арилар қисман учади, уяларни узоқ очиб қўймаслик лозим)."
        elif t_day > 30:
            bee_eval = "🐝 <b>Асаларичилик:</b> 🟠 <i>Иссиқ</i> (Уяларни қуёш тиғидан асраш, шамоллатиш ва сувдонларни назорат қилиш шарт)."
        else:
            bee_eval = "🐝 <b>Асаларичилик:</b> 🔴 <i>Салқин/Совуқ</i> (Арилар тутамга йиғилади, уяларни асло очманг)."
            
        lines.append(bee_eval)
        if i < days_cnt - 1:
            lines.append("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")
            
    lines.append("───────────────────")
    lines.append(tip_hdr)
    lines.append(f"{t_icon} <b>{t_title}:</b>")
    lines.append(f"{t_text}")
    lines.append("───────────────────")
    
    # 4. Пастки қисм (Footer)
    if del_hours == 0 and del_mins == 0:
        if lang == "ru":
            lines.append("📌 <i>Сообщение сохраняется постоянно (не удаляется).</i>")
        elif lang == "uz_lat":
            lines.append("📌 <i>Xabar guruhda doimiy saqlanadi (o'chirilmaydi).</i>")
        elif lang == "en":
            lines.append("📌 <i>This forecast is saved permanently (never deleted).</i>")
        else:
            lines.append("📌 <i>Ушбу об-ҳаво маълумоти гуруҳда доимий сақланади (ўчирилмайди).</i>")
    else:
        if lang == "ru":
            lines.append(f"⏱ <i>Сообщение будет автоматически очищено через {del_hours}ч {del_mins}м.</i>")
        elif lang == "en":
            lines.append(f"⏱ <i>This forecast will auto-delete in {del_hours}h {del_mins}m.</i>")
        elif lang == "uz_lat":
            lines.append(f"⏱ <i>Xabar {del_hours} soat {del_mins} daqiqadan so'ng avtomatik o'chiriladi.</i>")
        else:
            lines.append(f"⏱ <i>Хабар {del_hours} соат {del_mins} дақиқадан сўнг автоматик ўчирилади.</i>")
    lines.append(f"🐝 <b>@{BOT_USERNAME}</b> — @JamshidjonDavronov")
    return "\n".join(lines)

def send_weather_to_group(group_id, lang="uz_kr"):
    g = get_group(group_id)
    if not g:
        return
    city = g.get("weather_city", "Тошкент")
    del_h = g.get("weather_delete_hours", 2)
    del_m = g.get("weather_delete_minutes", 0)
    repeat_days = g.get("weather_repeat_days", "1,2,3,4,5,6,7")
    forecast_type = g.get("weather_forecast_type", "10_days")

    msg_text = generate_weather_report(city, forecast_type, repeat_days, del_h, del_m, lang)
    try:
        sent = bot.send_message(group_id, msg_text, parse_mode="HTML")
        try:
            bot.pin_chat_message(group_id, sent.message_id, disable_notification=True)
        except Exception as pe:
            logging.debug(f"Pin weather in group {group_id} error: {pe}")
        total_sec = del_h * 3600 + del_m * 60
        if total_sec > 0:
            threading.Timer(total_sec, lambda: delete_msg_safe(group_id, sent.message_id)).start()
    except Exception as e:
        logging.error(f"send_weather_to_group error in {group_id}: {e}")

def send_weather_to_all_channels(del_h=0, del_m=0, lang="uz_kr"):
    cursor.execute("SELECT chat_id, title FROM channels")
    channels = cursor.fetchall()
    sent_cnt = 0
    msg_text = generate_weather_report("Тошкент", "10_days", "1,2,3,4,5,6,7", del_h, del_m, lang)
    for ch in channels:
        cid = ch["chat_id"]
        try:
            sent = bot.send_message(cid, msg_text, parse_mode="HTML")
            try:
                bot.pin_chat_message(cid, sent.message_id, disable_notification=False)
            except Exception:
                pass
            total_sec = del_h * 3600 + del_m * 60
            if total_sec > 0:
                threading.Timer(total_sec, lambda c=cid, m=sent.message_id: delete_msg_safe(c, m)).start()
            sent_cnt += 1
            time.sleep(0.05)
        except Exception as e:
            logging.warning(f"send_weather_to_all_channels error in {cid}: {e}")
    return sent_cnt

# 8.2 БОТ ЭГАСИ: ГУРУҲЛАР НАЗОРАТИ ПАНЕЛИ
def show_owner_groups_panel(chat_id, message_id=None, lang="uz_kr"):
    cursor.execute("SELECT chat_id, title, added_by, is_authorized FROM groups ORDER BY is_authorized ASC, rowid DESC")
    all_groups = cursor.fetchall()
    
    auth_cnt = sum(1 for g in all_groups if g["is_authorized"] == 1)
    pending_cnt = sum(1 for g in all_groups if g["is_authorized"] == 0)
    
    text = (
        f"👑 <b>БОТ ЭГАСИ: ГУРУҲЛАР НАЗОРАТИ ПАНЕЛИ</b>\n\n"
        f"📊 <b>Гуруҳлар статистикаси:</b>\n"
        f"• 🟢 Фаол (Рухсат берилган): <b>{auth_cnt}</b> та\n"
        f"• 🟡 Рухсат кутаётган: <b>{pending_cnt}</b> та\n"
        f"• 📁 Жами базадаги гуруҳлар: <b>{len(all_groups)}</b> та\n\n"
        f"<i>💡 Гуруҳ ҳолатини бошқариш учун қуйидагилардан бирини танланг ёки олдиндан рухсат бериш учун <code>/allow -100...</code> буйруғини юборинг:</i>"
    )
    
    markup = InlineKeyboardMarkup()
    if not all_groups:
        markup.row(InlineKeyboardButton("ℹ️ Ҳозирча базада гуруҳлар йўқ", callback_data="none"))
    else:
        for g in all_groups[:15]:
            gid = g["chat_id"]
            title = g["title"] or "Гуруҳ"
            is_a = (g["is_authorized"] == 1)
            icon = "🟢" if is_a else "🟡"
            
            markup.row(InlineKeyboardButton(f"{icon} {title} (ID: {gid})", callback_data=f"panel_settings_{gid}" if is_a else f"auth_allow_{gid}"))
            if is_a:
                markup.row(
                    InlineKeyboardButton("🎙 Бот номидан ёзиш", callback_data=f"bot_chat_{gid}"),
                    InlineKeyboardButton("⚙️ Созламалар", callback_data=f"panel_settings_{gid}"),
                    InlineKeyboardButton("⛔️ Рухсатни олиш", callback_data=f"auth_revoke_{gid}")
                )
            else:
                markup.row(
                    InlineKeyboardButton("✅ Рухсат бериш", callback_data=f"auth_allow_{gid}"),
                    InlineKeyboardButton("❌ Рад этиш ва чиқиш", callback_data=f"auth_deny_{gid}")
                )
                
    markup.row(InlineKeyboardButton("➕ ID орқали рухсат қўшиш", callback_data="owner_allow_prompt"))
    markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
    safe_edit_or_send(chat_id, message_id, text, markup)

# 9. ГУРУҲ ТАНЛАШ ВА АДМИН ЭМАС ОГОҲЛАНТИРИШИ (КЎПТИЛЛИК)
def open_group_selection(chat_id, message_id=None, lang="uz_kr"):
    ensure_main_group_seeded()
    cursor.execute("SELECT chat_id, title, added_by, is_authorized FROM groups ORDER BY rowid DESC")
    all_groups = cursor.fetchall()

    markup = InlineKeyboardMarkup()
    if not all_groups:
        if lang == "ru":
            markup.row(InlineKeyboardButton("➕ Добавить бота в группу", callback_data="menu_add_group"))
            markup.row(InlineKeyboardButton("🏠 Главное меню", callback_data="back_main"))
            txt = (
                "🎛 <b>Раздел настроек группы</b>\n\n"
                "Бот пока не добавлен ни в одну группу.\n\n"
                "Свяжитесь с владельцем @JamshidjonDavronov, получите согласие, добавьте бота в свою группу и назначьте администратором:"
            )
        elif lang == "en":
            markup.row(InlineKeyboardButton("➕ Add bot to group", callback_data="menu_add_group"))
            markup.row(InlineKeyboardButton("🏠 Main Menu", callback_data="back_main"))
            txt = (
                "🎛 <b>Group Settings Section</b>\n\n"
                "The bot is not added to any group yet.\n\n"
                "Contact owner @JamshidjonDavronov for permission, add the bot to your group and grant admin rights:"
            )
        else:
            markup.row(InlineKeyboardButton("➕ Ботни гуруҳга қўшиш", callback_data="menu_add_group"))
            markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
            txt = (
                "🎛 <b>Гуруҳ созламалари бўлими</b>\n\n"
                "Ҳозирча бот бирорта гуруҳга қўшилмаган.\n\n"
                "Бот эгаси @JamshidjonDavronov розилигини олиб, ботни гуруҳингизга қўшинг ва администратор ҳуқуқини беринг:"
            )
        safe_edit_or_send(chat_id, message_id, txt, markup)
        return

    for g in all_groups:
        gid = g["chat_id"]
        g_title = g.get("title") or f"Гуруҳ ({gid})"
        is_adm = check_bot_admin_status(gid)
        st_icon = "⚙️" if is_adm else "⚙️"
        markup.row(
            InlineKeyboardButton(f"{st_icon} {g_title}", callback_data=f"panel_settings_{gid}"),
            InlineKeyboardButton("🛡 Қулфлар (Замки)", callback_data=f"panel_locks_{gid}")
        )

    if lang == "ru":
        markup.row(InlineKeyboardButton("➕ Добавить в новую группу", callback_data="menu_add_group"))
        markup.row(InlineKeyboardButton("🏠 Главное меню", callback_data="back_main"))
        txt = (
            "🎛 <b>Выберите группу для управления настройками:</b>\n\n"
            "Список ваших групп (Группы, где бот еще не админ, отмечены значком ⚠️):"
        )
    elif lang == "en":
        markup.row(InlineKeyboardButton("➕ Add to new group", callback_data="menu_add_group"))
        markup.row(InlineKeyboardButton("🏠 Main Menu", callback_data="back_main"))
        txt = (
            "🎛 <b>Select a group to manage settings:</b>\n\n"
            "List of your groups (Groups where the bot is not yet admin are marked with ⚠️):"
        )
    else:
        markup.row(InlineKeyboardButton("➕ Янги гуруҳга қўшиш", callback_data="menu_add_group"))
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        txt = (
            "🎛 <b>Созламаларни бошқариш учун гуруҳни танланг:</b>\n\n"
            "Бот қўшилган гуруҳларингиз рўйхати (Бот ҳали админ бўлмаган гуруҳлар ⚠️ белгиси билан кўрсатилган):"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_not_admin_warning(chat_id, group_id, message_id=None, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g.get("title", "Гуруҳ"))) if g else "Гуруҳ"

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(InlineKeyboardButton("➕ Назначить админом в группе", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
        markup.row(
            InlineKeyboardButton("🔄 Проверить статус админа", callback_data=f"recheck_admin_{group_id}"),
            InlineKeyboardButton("⚙️ Открыть настройки", callback_data=f"panel_settings_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Назад к группам", callback_data="menu_settings"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
        )
        txt = (
            f"⚠️ Выбрана группа <b>{title}</b>!\n\n"
            f"<b>Но бот еще НЕ АДМИНИСТРАТОР в этой группе!</b>\n\n"
            f"Чтобы бот мог работать (удалять спам, рекламу, проверять обязательную подписку), выдайте ему права администратора:\n\n"
            f"1. Откройте группу и перейдите в <b>Настройки</b>\n"
            f"2. Откройте раздел <b>«Администраторы»</b>\n"
            f"3. Нажмите <b>«Добавить администратора»</b>, выберите <code>@{BOT_USERNAME}</code> и включите разрешения.\n\n"
            f"После этого нажмите <b>«🔄 Проверить статус админа»</b>."
        )
    elif lang == "en":
        markup.row(InlineKeyboardButton("➕ Promote Bot to Admin", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
        markup.row(
            InlineKeyboardButton("🔄 Check Admin Status", callback_data=f"recheck_admin_{group_id}"),
            InlineKeyboardButton("⚙️ Open Settings Anyway", callback_data=f"panel_settings_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Back to Groups", callback_data="menu_settings"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")
        )
        txt = (
            f"⚠️ Group <b>{title}</b> selected!\n\n"
            f"<b>However, the bot is NOT an ADMIN in this group yet!</b>\n\n"
            f"For the bot to function (block spam, delete links, verify subscriptions), admin permissions are mandatory:\n\n"
            f"1. Open group profile and go to <b>Settings</b>\n"
            f"2. Tap <b>«Administrators»</b>\n"
            f"3. Tap <b>«Add Administrator»</b>, select <code>@{BOT_USERNAME}</code> and grant permissions.\n\n"
            f"Then tap <b>«🔄 Check Admin Status»</b>."
        )
    else:
        markup.row(InlineKeyboardButton("➕ Гуруҳга админ қилиш", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
        markup.row(
            InlineKeyboardButton("🔄 Админликни текшириш", callback_data=f"recheck_admin_{group_id}"),
            InlineKeyboardButton("⚙️ Шунга қарамай очиш", callback_data=f"panel_settings_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Гуруҳлар рўйхатига қайтиш", callback_data="menu_settings"),
            InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
        )
        txt = (
            f"⚠️ <b>{title}</b> гуруҳи танланди!\n\n"
            f"<b>Аммо бот ҳали ушбу гуруҳда АДМИН эмас!</b>\n\n"
            f"Бот гуруҳни тўлиқ ҳимоя қилиши (спамларни тозалаш, рекламаларни ўчириш, янги аъзоларни текшириш) учун ботга админлик ҳуқуқи берилиши шарт:\n\n"
            f"1. Гуруҳ номи устига босинг ва <b>Созламалар</b> бўлимига киринг\n"
            f"2. <b>«Администраторлар»</b> бўлимига ўтинг\n"
            f"3. <b>«Администратор қўшиш»</b>ни босиб, <code>@{BOT_USERNAME}</code> ни қўшинг ва барча рухсатларни ёқинг.\n\n"
            f"Админ қилганингиздан сўнг <b>«🔄 Админликни текшириш»</b> тугмасини босинг."
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# 10. ГУРУҲ СОЗЛАМАЛАРИ БОШ ПАНЕЛИ (КЎПТИЛЛИК)
def show_settings_panel(chat_id, group_id, message_id=None, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"

    welcome_st = "✅" if g and g.get("welcome_enabled", 1) else "⬜️"
    forcesub_st = "✅" if g and g.get("forcesub_enabled", 0) else "⬜️"
    autolock_st = "✅" if g and g.get("autolock_enabled", 0) else "⬜️"
    approval_st = "✅" if g and g.get("approval_enabled", 0) else "⬜️"
    joins_st = "🧹" if g and g.get("clean_joins", 1) else "⬜️"
    lim_st = "✅" if g and g.get("limit_enabled", 1) else "⬜️"
    lim_max = g.get("limit_max", 3) if g else 3
    s_time = g.get("autolock_start_time", "23:00") if g else "23:00"
    e_time = g.get("autolock_end_time", "06:30") if g else "06:30"
    tz_city = g.get("timezone_city", "Тошкент (UTC+5)") if g else "Тошкент (UTC+5)"
    w_type = g.get("weather_forecast_type", "10_days") if g else "10_days"
    
    if lang == "ru":
        w_type_str = {"1_day": "1 день", "3_days": "3 дня", "10_days": "10 дней"}.get(w_type, "10 дней")
    elif lang == "en":
        w_type_str = {"1_day": "1 day", "3_days": "3 days", "10_days": "10 days"}.get(w_type, "10 days")
    else:
        w_type_str = {"1_day": "1 кунлик", "3_days": "3 кунлик", "10_days": "10 кунлик"}.get(w_type, "10 кунлик")
    f_chan = g.get("forcesub_channel", "@Asalarichilik_Uz") if g else "@Asalarichilik_Uz"

    is_adm = check_bot_admin_status(group_id)
    if lang == "ru":
        adm_status_text = "🟢 Бот админ в группе" if is_adm else "⚠️ Бот еще не админ!"
    elif lang == "en":
        adm_status_text = "🟢 Bot is admin" if is_adm else "⚠️ Bot is not admin yet!"
    else:
        adm_status_text = "🟢 Бот гуруҳда админ" if is_adm else "⚠️ Бот ҳали админ эмас!"

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(
            InlineKeyboardButton("🛡 Замки (20+ правил)", callback_data=f"panel_locks_{group_id}"),
            InlineKeyboardButton(f"📊 Лимиты ({lim_max}/день) {lim_st}", callback_data=f"panel_limits_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🌙 Ночной замок ({s_time}-{e_time}) {autolock_st}", callback_data=f"panel_autolock_{group_id}"),
            InlineKeyboardButton(f"👋 Приветствие {welcome_st}", callback_data=f"toggle_welcome_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"📢 Обяз. подписка {forcesub_st}", callback_data=f"panel_forcesub_{group_id}"),
            InlineKeyboardButton(f"🔐 Одобрение админом {approval_st}", callback_data=f"toggle_approval_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"⏰ Время: {tz_city}", callback_data=f"panel_timezone_{group_id}"),
            InlineKeyboardButton(f"☀️ Погода ({w_type_str})", callback_data=f"panel_weather_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🚪 Вход/Выход: {joins_st}", callback_data=f"toggle_joins_{group_id}"),
            InlineKeyboardButton("≡ Списки (Белый/Черный)", callback_data=f"panel_lists_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("📜 Правила группы", callback_data=f"send_rules_{group_id}"),
            InlineKeyboardButton("🔄 Обновить", callback_data=f"panel_settings_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("🌐 Сменить язык", callback_data="menu_language"),
            InlineKeyboardButton("◀️ Список групп", callback_data="menu_settings")
        )
        markup.row(InlineKeyboardButton("🏠 Главное меню", callback_data="back_main"))
        txt = (
            f"⚙️ <b>{title} — ПАНЕЛЬ УПРАВЛЕНИЯ ГРУППОЙ</b>\n\n"
            f"• 👮‍♂️ <b>Статус бота:</b> {adm_status_text}\n"
            f"• 🛡 <b>Защита:</b> Анти-спам, ссылки, мат и пересылки\n"
            f"• 📊 <b>Лимит медиа:</b> {lim_max} фото/видео в день (при превышении — МУТ 24ч!)\n"
            f"• 🌙 <b>Ночной замок:</b> с {s_time} до {e_time} чат закрывается\n"
            f"• 📢 <b>Обязательная подписка:</b> {forcesub_st} (Канал: {f_chan})\n"
            f"• 🔐 <b>Одобрение новых участников:</b> {approval_st}\n"
            f"• ⏰ <b>Часовой пояс:</b> {tz_city}\n"
            f"• ☀️ <b>Прогноз погоды:</b> {w_type_str} ({g.get('weather_time', '08:00')})\n"
            f"• 🚪 <b>Очистка сервисных сообщений:</b> {joins_st}\n\n"
            f"<i>Выберите нужный раздел кнопками ниже:</i>"
        )
    elif lang == "en":
        markup.row(
            InlineKeyboardButton("🛡 Security Locks (20+)", callback_data=f"panel_locks_{group_id}"),
            InlineKeyboardButton(f"📊 Limits ({lim_max}/day) {lim_st}", callback_data=f"panel_limits_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🌙 Night Lock ({s_time}-{e_time}) {autolock_st}", callback_data=f"panel_autolock_{group_id}"),
            InlineKeyboardButton(f"👋 Welcome {welcome_st}", callback_data=f"toggle_welcome_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"📢 Mandatory Sub {forcesub_st}", callback_data=f"panel_forcesub_{group_id}"),
            InlineKeyboardButton(f"🔐 Admin Approval {approval_st}", callback_data=f"toggle_approval_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"⏰ Time: {tz_city}", callback_data=f"panel_timezone_{group_id}"),
            InlineKeyboardButton(f"☀️ Weather ({w_type_str})", callback_data=f"panel_weather_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🚪 Clean Joins: {joins_st}", callback_data=f"toggle_joins_{group_id}"),
            InlineKeyboardButton("≡ Lists (White/Black)", callback_data=f"panel_lists_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("📜 Group Rules", callback_data=f"send_rules_{group_id}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"panel_settings_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("🌐 Change Language", callback_data="menu_language"),
            InlineKeyboardButton("◀️ Groups List", callback_data="menu_settings")
        )
        markup.row(InlineKeyboardButton("🏠 Main Menu", callback_data="back_main"))
        txt = (
            f"⚙️ <b>{title} — GROUP SETTINGS PANEL</b>\n\n"
            f"• 👮‍♂️ <b>Bot Status:</b> {adm_status_text}\n"
            f"• 🛡 <b>Protection:</b> Anti-spam, links, bad words, forwards\n"
            f"• 📊 <b>Media Limits:</b> {lim_max} photos/videos/day (exceeding = 24h MUTE!)\n"
            f"• 🌙 <b>Night Lock:</b> Chat muted from {s_time} to {e_time}\n"
            f"• 📢 <b>Mandatory Sub:</b> {forcesub_st} (Channel: {f_chan})\n"
            f"• 🔐 <b>Admin Approval:</b> {approval_st}\n"
            f"• ⏰ <b>Timezone:</b> {tz_city}\n"
            f"• ☀️ <b>Weather Report:</b> {w_type_str} ({g.get('weather_time', '08:00')})\n"
            f"• 🚪 <b>Clean Joins/Leaves:</b> {joins_st}\n\n"
            f"<i>Configure features using the buttons below:</i>"
        )
    else:
        markup.row(
            InlineKeyboardButton("🛡 Қулфлар (20+ қулф)", callback_data=f"panel_locks_{group_id}"),
            InlineKeyboardButton(f"📊 Лимитлар ({lim_max}/кун) {lim_st}", callback_data=f"panel_limits_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🌙 Тунги қулф ({s_time}-{e_time}) {autolock_st}", callback_data=f"panel_autolock_{group_id}"),
            InlineKeyboardButton(f"👋 Кутиб олиш {welcome_st}", callback_data=f"toggle_welcome_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"📢 Мажбурий обуна {forcesub_st}", callback_data=f"panel_forcesub_{group_id}"),
            InlineKeyboardButton(f"🔐 Админ тасдиғи {approval_st}", callback_data=f"toggle_approval_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"⏰ Вақт: {tz_city}", callback_data=f"panel_timezone_{group_id}"),
            InlineKeyboardButton(f"☀️ Об-ҳаво ({w_type_str})", callback_data=f"panel_weather_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🚪 Кирди-чиқди: {joins_st}", callback_data=f"toggle_joins_{group_id}"),
            InlineKeyboardButton("≡ Рўйхатлар (Оқ/Қора)", callback_data=f"panel_lists_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("📜 Гуруҳ қоидалари", callback_data=f"send_rules_{group_id}"),
            InlineKeyboardButton("🔄 Гуруҳни янгилаш", callback_data=f"panel_settings_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("🌐 Тилни ўзгартириш", callback_data="menu_language"),
            InlineKeyboardButton("◀️ Гуруҳлар рўйхати", callback_data="menu_settings")
        )
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        txt = (
            f"⚙️ <b>{title} — ГУРУҲ СОЗЛАМАЛАРИ ПАНЕЛИ</b>\n\n"
            f"• 👮‍♂️ <b>Бот ҳолати:</b> {adm_status_text}\n"
            f"• 🛡 <b>Қулфлар:</b> Реклама, спам, сўкиниш ва форвард ҳимояси\n"
            f"• 📊 <b>Медиа лимитлари:</b> Кунига {lim_max} та расм/видео (ошса 24с МУТЕ!)\n"
            f"• 🌙 <b>Тунги қулф:</b> {s_time} дан {e_time} гача ёзиш тўхтатилади\n"
            f"• 📢 <b>Мажбурий обуна:</b> {forcesub_st} (Канал: {f_chan})\n"
            f"• 🔐 <b>Янги аъзоларга админ тасдиғи:</b> {approval_st}\n"
            f"• ⏰ <b>Вақт минтақаси:</b> {tz_city}\n"
            f"• ☀️ <b>Об-ҳаво хабари:</b> {w_type_str} ({g.get('weather_time', '08:00')})\n"
            f"• 🚪 <b>Кирди-чиқди тозалаш:</b> {joins_st}\n\n"
            f"<i>Керакли бўлимни қуйидаги тугмалар орқали созланг:</i>"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# 11. МАЖБУРИЙ ОБУНА ПАНЕЛИ (КЎПТИЛЛИК)
def show_forcesub_panel(chat_id, group_id, message_id=None, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"
    f_enabled = g.get("forcesub_enabled", 0) if g else 0
    f_chan = clean_channel_username(g.get("forcesub_channel", "@asalarichilik") if g else "@asalarichilik")
    f_appr = g.get("approval_enabled", 0) if g else 0
    f_scope = g.get("forcesub_only_new", 1) if g else 1
    f_timer = g.get("forcesub_timer_min", 0) if g else 0

    bot_chan_ok = check_bot_channel_admin(f_chan)
    bot_grp_ok = check_bot_group_admin(group_id)

    if lang == "ru":
        st_lbl = "🟢 Включено" if f_enabled else "⚪️ Отключено"
        mode_btn = "👨‍💼 По одобрению админа" if f_appr else "⚡️ Прямой вход (Сразу)"
        scope_btn = "🆕 Новые и вернувшиеся" if f_scope else "🌐 Все участники"
        timer_lbl = "♾ Не удалять (пока не подпишется)" if f_timer == 0 else f"⏱ {f_timer} мин"
        bot_ch_st = "✅ Админ в канале" if bot_chan_ok else "❌ Не админ (добавьте бота!)"
        bot_gr_st = "✅ Админ в группе" if bot_grp_ok else "❌ Не админ (добавьте бота!)"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⚪️ Выключить" if f_enabled else "🟢 Включить", callback_data=f"toggle_forcesub_{group_id}"),
            InlineKeyboardButton("📢 Изменить канал", callback_data=f"change_fsub_chan_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"⏱ Время в группе: {timer_lbl}", callback_data=f"cycle_fsub_timer_{group_id}"),
            InlineKeyboardButton("✏️ Ввести минуты", callback_data=f"input_fsub_timer_{group_id}")
        )
        markup.row(InlineKeyboardButton(f"🔀 Режим: {mode_btn}", callback_data=f"toggle_fsub_mode_{group_id}"))
        markup.row(InlineKeyboardButton(f"👥 Охват: {scope_btn}", callback_data=f"toggle_fsub_scope_{group_id}"))
        markup.row(InlineKeyboardButton("🔄 Проверить права админа", callback_data=f"check_fsub_admin_{group_id}"))
        markup.row(
            InlineKeyboardButton("◀️ Настройки группы", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
        )
        txt = (
            f"📢 <b>{title} — НАСТРОЙКИ ОБЯЗАТЕЛЬНОЙ ПОДПИСКИ</b>\n\n"
            f"• 🔔 <b>Статус:</b> {st_lbl}\n"
            f"• 📢 <b>Обязательный канал:</b> <code>{f_chan}</code>\n"
            f"• 🤖 <b>Бот в канале:</b> {bot_ch_st}\n"
            f"• 🛡 <b>Бот в группе:</b> {bot_gr_st}\n"
            f"• ⏱ <b>Предупреждение в группе:</b> {timer_lbl}\n"
            f"• 🔀 <b>Порядок входа:</b> {mode_btn}\n"
            f"• 👥 <b>Охват:</b> {scope_btn}\n\n"
            f"<i>Если выбрано 'Не удалять', предупреждение будет висеть в группе, а участник будет ограничен (мут), пока не подпишется на канал!</i>"
        )
    elif lang == "en":
        st_lbl = "🟢 Enabled" if f_enabled else "⚪️ Disabled"
        mode_btn = "👨‍💼 Admin Approval" if f_appr else "⚡️ Direct Join"
        scope_btn = "🆕 New & Returning" if f_scope else "🌐 All Members"
        timer_lbl = "♾ Never (until subscribed)" if f_timer == 0 else f"⏱ {f_timer} min"
        bot_ch_st = "✅ Admin in Channel" if bot_chan_ok else "❌ Not Admin!"
        bot_gr_st = "✅ Admin in Group" if bot_grp_ok else "❌ Not Admin!"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⚪️ Turn Off" if f_enabled else "🟢 Turn On", callback_data=f"toggle_forcesub_{group_id}"),
            InlineKeyboardButton("📢 Change Channel", callback_data=f"change_fsub_chan_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"⏱ Group Timer: {timer_lbl}", callback_data=f"cycle_fsub_timer_{group_id}"),
            InlineKeyboardButton("✏️ Custom minutes", callback_data=f"input_fsub_timer_{group_id}")
        )
        markup.row(InlineKeyboardButton(f"🔀 Mode: {mode_btn}", callback_data=f"toggle_fsub_mode_{group_id}"))
        markup.row(InlineKeyboardButton(f"👥 Scope: {scope_btn}", callback_data=f"toggle_fsub_scope_{group_id}"))
        markup.row(InlineKeyboardButton("🔄 Verify Admin Rights", callback_data=f"check_fsub_admin_{group_id}"))
        markup.row(
            InlineKeyboardButton("◀️ Group Settings", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")
        )
        txt = (
            f"📢 <b>{title} — MANDATORY SUBSCRIPTION SETTINGS</b>\n\n"
            f"• 🔔 <b>Status:</b> {st_lbl}\n"
            f"• 📢 <b>Mandatory Channel:</b> <code>{f_chan}</code>\n"
            f"• 🤖 <b>Bot in Channel:</b> {bot_ch_st}\n"
            f"• 🛡 <b>Bot in Group:</b> {bot_gr_st}\n"
            f"• ⏱ <b>Notice Lifetime in Group:</b> {timer_lbl}\n"
            f"• 🔀 <b>Join Mode:</b> {mode_btn}\n"
            f"• 👥 <b>Target Audience:</b> {scope_btn}\n\n"
            f"<i>Unsubscribed members are muted in the group until they join the channel and click verify!</i>"
        )
    else:
        st_lbl = "🟢 Ёқилган" if f_enabled else "⚪️ Ўчирилган"
        mode_btn = "👨‍💼 Админ розилиги билан" if f_appr else "⚡️ Тўғридан-тўғри (Дарҳол)"
        scope_btn = "🆕 Янги ва қайта кирганлар" if f_scope else "🌐 Барча аъзолар"
        timer_lbl = "♾ Ўчирилмасин (Аъзо бўлмагунча)" if f_timer == 0 else f"⏱ {f_timer} дақиқа"
        bot_ch_st = "✅ Тўлиқ админ" if bot_chan_ok else "❌ Админ эмас (Ботни каналга админ қилинг!)"
        bot_gr_st = "✅ Тўлиқ админ" if bot_grp_ok else "❌ Админ эмас (Ботни гуруҳга админ қилинг!)"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("⚪️ Ўчириш" if f_enabled else "🟢 Ёқиш", callback_data=f"toggle_forcesub_{group_id}"),
            InlineKeyboardButton("📢 Канални ўзгартириш", callback_data=f"change_fsub_chan_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"⏱ Хабар туриши: {timer_lbl}", callback_data=f"cycle_fsub_timer_{group_id}"),
            InlineKeyboardButton("✏️ Қўлда киритиш", callback_data=f"input_fsub_timer_{group_id}")
        )
        markup.row(InlineKeyboardButton(f"🔀 Тартиб: {mode_btn}", callback_data=f"toggle_fsub_mode_{group_id}"))
        markup.row(InlineKeyboardButton(f"👥 Қамров: {scope_btn}", callback_data=f"toggle_fsub_scope_{group_id}"))
        markup.row(InlineKeyboardButton("🔄 Бот админлигини текшириш", callback_data=f"check_fsub_admin_{group_id}"))
        markup.row(
            InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
        )
        txt = (
            f"📢 <b>{title} — МАЖБУРИЙ ОБУНА СОЗЛАМАЛАРИ</b>\n\n"
            f"• 🔔 <b>Ҳолати:</b> {st_lbl}\n"
            f"• 📢 <b>Мажбурий канал:</b> <code>{f_chan}</code>\n"
            f"• 🤖 <b>Бот каналда админми:</b> {bot_ch_st}\n"
            f"• 🛡 <b>Бот гуруҳда админми:</b> {bot_gr_st}\n"
            f"• ⏱ <b>Огоҳлантириш гуруҳда туриш вақти:</b> {timer_lbl}\n"
            f"• 🔀 <b>Қўшилиш тартиби:</b> {mode_btn}\n"
            f"• 👥 <b>Таъсир доираси:</b> {scope_btn}\n\n"
            f"💡 <b>Ишлаш тартиби:</b>\n"
            f"Фойдаланувчи каналга аъзо бўлмагунча гуруҳда ёза олмайди (мутда бўлади). "
            f"Огоҳлантириш хабари гуруҳга жўнатилади. "
            f"Агар <i>'Умуман ўчирилмасин'</i> танланса, хабар токи фойдаланувчи каналга аъзо бўлиб тугмани босмагунча гуруҳда туради!"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# 12. ОБ-ҲАВО ПАНЕЛИ (КЎПТИЛЛИК)
def show_weather_panel(chat_id, group_id, message_id=None, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"
    city = g.get("weather_city", "Тошкент") if g else "Тошкент"
    w_time = g.get("weather_time", "08:00") if g else "08:00"
    forecast_type = g.get("weather_forecast_type", "10_days") if g else "10_days"
    repeat_days = g.get("weather_repeat_days", "1,2,3,4,5,6,7") if g else "1,2,3,4,5,6,7"
    del_h = g.get("weather_delete_hours", 2) if g else 2
    del_m = g.get("weather_delete_minutes", 0) if g else 0
    w_enabled = g.get("weather_enabled", 1) if g else 1

    days_fmt = format_repeat_days(repeat_days, lang)
    preview = generate_weather_report(city, forecast_type, repeat_days, del_h, del_m, lang)

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        st_lbl = "🟢 Включено" if w_enabled else "⚪️ Отключено"
        type_display = {"1_day": "1 день ☀️", "3_days": "3 дня ⛅️", "10_days": "10 дней 📅"}.get(forecast_type, "10 дней 📅")
        del_display = "♾ Не удалять (постоянно)" if (del_h == 0 and del_m == 0) else f"{del_h} ч {del_m} мин"
        is_never = (del_h == 0 and del_m == 0)
        never_btn = "✅ ♾ Не удалять" if is_never else "♾ Не удалять"
        two_btn = "✅ 2 часа" if (del_h == 2 and del_m == 0) else "2 часа"
        eight_btn = "✅ 8 часов" if (del_h == 8 and del_m == 0) else "8 часов"

        markup.row(InlineKeyboardButton(f"📍 Регион: {city}", callback_data=f"weather_cities_{group_id}"))
        markup.row(
            InlineKeyboardButton(f"⏰ Время отправки: {w_time}", callback_data=f"weather_set_time_{group_id}"),
            InlineKeyboardButton("✏️ Ввести время", callback_data=f"weather_input_time_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("✅ 1 день ☀️" if forecast_type == "1_day" else "1 день ☀️", callback_data=f"w_set_type_{group_id}_1_day"),
            InlineKeyboardButton("✅ 3 дня ⛅️" if forecast_type == "3_days" else "3 дня ⛅️", callback_data=f"w_set_type_{group_id}_3_days"),
            InlineKeyboardButton("✅ 10 дней 📅" if forecast_type == "10_days" else "10 дней 📅", callback_data=f"w_set_type_{group_id}_10_days")
        )
        markup.row(InlineKeyboardButton(f"🔁 Дни недели: {days_fmt}", callback_data=f"weather_days_{group_id}"))
        markup.row(
            InlineKeyboardButton(f"⏱ Час: {del_h}ч", callback_data=f"weather_cycle_h_{group_id}"),
            InlineKeyboardButton(f"⏱ Мин: {del_m}м", callback_data=f"weather_cycle_m_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(never_btn, callback_data=f"weather_set_never_{group_id}"),
            InlineKeyboardButton(two_btn, callback_data=f"weather_set_2h_{group_id}"),
            InlineKeyboardButton(eight_btn, callback_data=f"weather_set_8h_{group_id}")
        )
        markup.row(InlineKeyboardButton("📢 Отправить во все каналы", callback_data=f"weather_send_channels_{group_id}"))
        markup.row(
            InlineKeyboardButton("⚪️ Выключить" if w_enabled else "🟢 Включить", callback_data=f"toggle_weather_{group_id}"),
            InlineKeyboardButton(f"📤 Отправить в группу ({type_display})", callback_data=f"weather_send_now_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Настройки группы", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
        )
        txt = (
            f"☀️ <b>{title} — НАСТРОЙКИ ПОГОДЫ</b>\n\n"
            f"• 📍 <b>Регион:</b> {city}\n"
            f"• ⏰ <b>Время отправки:</b> {w_time}\n"
            f"• 📊 <b>Тип прогноза:</b> {type_display}\n"
            f"• 🔁 <b>Повторение:</b> {days_fmt}\n"
            f"• ⏱ <b>Авто-удаление:</b> {del_display}\n"
            f"• 🔔 <b>Статус:</b> {st_lbl}\n\n"
            f"──────── ПРИМЕР ПРОГНОЗА ────────\n"
            f"{preview}\n"
            f"────────────────────────────────"
        )
    elif lang == "en":
        st_lbl = "🟢 Enabled" if w_enabled else "⚪️ Disabled"
        type_display = {"1_day": "1 Day ☀️", "3_days": "3 Days ⛅️", "10_days": "10 Days 📅"}.get(forecast_type, "10 Days 📅")
        del_display = "♾ Never delete (permanent)" if (del_h == 0 and del_m == 0) else f"{del_h}h {del_m}m"
        is_never = (del_h == 0 and del_m == 0)
        never_btn = "✅ ♾ Never delete" if is_never else "♾ Never delete"
        two_btn = "✅ 2 hours" if (del_h == 2 and del_m == 0) else "2 hours"
        eight_btn = "✅ 8 hours" if (del_h == 8 and del_m == 0) else "8 hours"

        markup.row(InlineKeyboardButton(f"📍 Region: {city}", callback_data=f"weather_cities_{group_id}"))
        markup.row(
            InlineKeyboardButton(f"⏰ Send Time: {w_time}", callback_data=f"weather_set_time_{group_id}"),
            InlineKeyboardButton("✏️ Custom Time", callback_data=f"weather_input_time_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("✅ 1 Day ☀️" if forecast_type == "1_day" else "1 Day ☀️", callback_data=f"w_set_type_{group_id}_1_day"),
            InlineKeyboardButton("✅ 3 Days ⛅️" if forecast_type == "3_days" else "3 Days ⛅️", callback_data=f"w_set_type_{group_id}_3_days"),
            InlineKeyboardButton("✅ 10 Days 📅" if forecast_type == "10_days" else "10 Days 📅", callback_data=f"w_set_type_{group_id}_10_days")
        )
        markup.row(InlineKeyboardButton(f"🔁 Repeat Days: {days_fmt}", callback_data=f"weather_days_{group_id}"))
        markup.row(
            InlineKeyboardButton(f"⏱ Hour: {del_h}h", callback_data=f"weather_cycle_h_{group_id}"),
            InlineKeyboardButton(f"⏱ Min: {del_m}m", callback_data=f"weather_cycle_m_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(never_btn, callback_data=f"weather_set_never_{group_id}"),
            InlineKeyboardButton(two_btn, callback_data=f"weather_set_2h_{group_id}"),
            InlineKeyboardButton(eight_btn, callback_data=f"weather_set_8h_{group_id}")
        )
        markup.row(InlineKeyboardButton("📢 Send to All Channels", callback_data=f"weather_send_channels_{group_id}"))
        markup.row(
            InlineKeyboardButton("⚪️ Turn Off" if w_enabled else "🟢 Turn On", callback_data=f"toggle_weather_{group_id}"),
            InlineKeyboardButton(f"📤 Send Now ({type_display})", callback_data=f"weather_send_now_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Group Settings", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")
        )
        txt = (
            f"☀️ <b>{title} — WEATHER SETTINGS</b>\n\n"
            f"• 📍 <b>Region:</b> {city}\n"
            f"• ⏰ <b>Send Time:</b> {w_time}\n"
            f"• 📊 <b>Forecast Type:</b> {type_display}\n"
            f"• 🔁 <b>Frequency:</b> {days_fmt}\n"
            f"• ⏱ <b>Auto-Delete:</b> {del_display}\n"
            f"• 🔔 <b>Status:</b> {st_lbl}\n\n"
            f"──────── FORECAST PREVIEW ────────\n"
            f"{preview}\n"
            f"──────────────────────────────────"
        )
    else:
        st_lbl = "🟢 Ёқилган" if w_enabled else "⚪️ Ўчирилган"
        type_display = {"1_day": "1 кунлик ☀️", "3_days": "3 кунлик ⛅️", "10_days": "10 кунлик 📅"}.get(forecast_type, "10 кунлик 📅")
        del_display = "♾ Ўчирилмайди (доимий)" if (del_h == 0 and del_m == 0) else f"{del_h} соат {del_m} дақиқа"
        is_never = (del_h == 0 and del_m == 0)
        never_btn = "✅ ♾ Ўчирилмасин" if is_never else "♾ Ўчирилмасин"
        two_btn = "✅ 2 соат" if (del_h == 2 and del_m == 0) else "2 соат"
        eight_btn = "✅ 8 соат" if (del_h == 8 and del_m == 0) else "8 соат"

        markup.row(InlineKeyboardButton(f"📍 Ҳудуд: {city}", callback_data=f"weather_cities_{group_id}"))
        markup.row(
            InlineKeyboardButton(f"⏰ Жўнатиш соати: {w_time}", callback_data=f"weather_set_time_{group_id}"),
            InlineKeyboardButton("✏️ Соатни ёзиш", callback_data=f"weather_input_time_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("✅ 1 кунлик ☀️" if forecast_type == "1_day" else "1 кунлик ☀️", callback_data=f"w_set_type_{group_id}_1_day"),
            InlineKeyboardButton("✅ 3 кунлик ⛅️" if forecast_type == "3_days" else "3 кунлик ⛅️", callback_data=f"w_set_type_{group_id}_3_days"),
            InlineKeyboardButton("✅ 10 кунлик 📅" if forecast_type == "10_days" else "10 кунлик 📅", callback_data=f"w_set_type_{group_id}_10_days")
        )
        markup.row(InlineKeyboardButton(f"🔁 Ҳафта кунлари: {days_fmt}", callback_data=f"weather_days_{group_id}"))
        markup.row(
            InlineKeyboardButton(f"⏱ Соат: {del_h}с", callback_data=f"weather_cycle_h_{group_id}"),
            InlineKeyboardButton(f"⏱ Дақиқа: {del_m}д", callback_data=f"weather_cycle_m_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(never_btn, callback_data=f"weather_set_never_{group_id}"),
            InlineKeyboardButton(two_btn, callback_data=f"weather_set_2h_{group_id}"),
            InlineKeyboardButton(eight_btn, callback_data=f"weather_set_8h_{group_id}")
        )
        markup.row(InlineKeyboardButton("📢 Каналларга ҳам юбориш", callback_data=f"weather_send_channels_{group_id}"))
        markup.row(
            InlineKeyboardButton("⚪️ Ўчириш" if w_enabled else "🟢 Ёқиш", callback_data=f"toggle_weather_{group_id}"),
            InlineKeyboardButton(f"📤 Гуруҳга юбориш ({type_display})", callback_data=f"weather_send_now_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
        )
        txt = (
            f"☀️ <b>{title} — ОБ-ҲАВО СОЗЛАМАЛАРИ</b>\n\n"
            f"• 📍 <b>Ҳудуд:</b> {city}\n"
            f"• ⏰ <b>Гуруҳга юбориш вақти:</b> {w_time}\n"
            f"• 📊 <b>Танланган прогноз:</b> {type_display}\n"
            f"• 🔁 <b>Такрорланиш:</b> {days_fmt}\n"
            f"• ⏱ <b>Авто-ўчириш:</b> {del_display}\n"
            f"• 🔔 <b>Ҳолати:</b> {st_lbl}\n\n"
            f"──────── ПРОГНОЗ НАМУНАСИ ────────\n"
            f"{preview}\n"
            f"──────────────────────────────────\n"
            f"<i>Қуйидаги тугмалар орқали соатни, 1/3/10 кунлик турларини ва автоматик ўчирилиш вақтини (ёки <b>♾ Ўчирилмасин</b> ни) созланг:</i>"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# 13. ВАҚТ ЗОНАСИ ПАНЕЛИ (КЎПТИЛЛИК)
def show_timezone_panel(chat_id, group_id, message_id=None, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"
    tz_offset = g.get("timezone_offset", 5) if g else 5
    tz_city = g.get("timezone_city", "Тошкент (UTC+5)") if g else "Тошкент (UTC+5)"

    now_dt = get_now(tz_offset)
    time_str = now_dt.strftime("%H:%M:%S")

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        m_name = RU_MONTHS[now_dt.month - 1]
        date_str = f"{now_dt.day} {m_name} {now_dt.year} г."
        markup.row(InlineKeyboardButton("📍 Автоматически по геолокации", callback_data=f"tz_req_loc_{group_id}"))
        markup.row(
            InlineKeyboardButton("🇺🇿 Ташкент (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Ташкент (UTC+5)"),
            InlineKeyboardButton("🇺🇿 Самарканд (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Самарканд (UTC+5)")
        )
        markup.row(
            InlineKeyboardButton("🇺🇿 Фергана (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Фергана (UTC+5)"),
            InlineKeyboardButton("🇺🇿 Бухара (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Бухара (UTC+5)")
        )
        markup.row(InlineKeyboardButton("🗺 Список всех регионов Узбекистана", callback_data=f"tz_all_regions_{group_id}"))
        markup.row(InlineKeyboardButton("✏️ Ручной ввод смещения UTC (+5, +4...)", callback_data=f"tz_custom_input_{group_id}"))
        markup.row(
            InlineKeyboardButton("◀️ Настройки группы", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
        )
        txt = (
            f"🌐 <b>{title} — НАСТРОЙКИ ВРЕМЕНИ И ДАТЫ</b>\n\n"
            f"• 🕒 <b>Текущее точное время:</b> <code>{time_str}</code>\n"
            f"• 📅 <b>Дата и год:</b> <code>{date_str}</code>\n"
            f"• 🌍 <b>Текущий часовой пояс:</b> <code>{tz_city}</code>\n\n"
            f"<b>Способы настройки времени:</b>\n"
            f"1. 📍 <b>Отправить локацию:</b> Автоматическое определение по геолокации Telegram.\n"
            f"2. 🗺 <b>По регионам:</b> Быстрый выбор области Узбекистана.\n"
            f"3. ✏️ <b>Ручной ввод:</b> Ввести разницу UTC."
        )
    elif lang == "en":
        m_name = EN_MONTHS[now_dt.month - 1]
        date_str = f"{m_name} {now_dt.day}, {now_dt.year}"
        markup.row(InlineKeyboardButton("📍 Automatic by Telegram Location", callback_data=f"tz_req_loc_{group_id}"))
        markup.row(
            InlineKeyboardButton("🇺🇿 Tashkent (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Tashkent (UTC+5)"),
            InlineKeyboardButton("🇺🇿 Samarkand (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Samarkand (UTC+5)")
        )
        markup.row(
            InlineKeyboardButton("🇺🇿 Fergana (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Fergana (UTC+5)"),
            InlineKeyboardButton("🇺🇿 Bukhara (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Bukhara (UTC+5)")
        )
        markup.row(InlineKeyboardButton("🗺 All Regions List", callback_data=f"tz_all_regions_{group_id}"))
        markup.row(InlineKeyboardButton("✏️ Manual UTC Offset (+5, +4...)", callback_data=f"tz_custom_input_{group_id}"))
        markup.row(
            InlineKeyboardButton("◀️ Group Settings", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")
        )
        txt = (
            f"🌐 <b>{title} — TIME & DATE SETTINGS</b>\n\n"
            f"• 🕒 <b>Current Accurate Time:</b> <code>{time_str}</code>\n"
            f"• 📅 <b>Date and Year:</b> <code>{date_str}</code>\n"
            f"• 🌍 <b>Current Timezone:</b> <code>{tz_city}</code>\n\n"
            f"<b>Select adjustment method:</b>\n"
            f"1. 📍 <b>Send Location:</b> Auto sync with Telegram GPS coordinates.\n"
            f"2. 🗺 <b>Preset Region:</b> Choose an Uzbekistan province.\n"
            f"3. ✏️ <b>Manual:</b> Enter custom UTC offset."
        )
    else:
        m_name = UZ_MONTHS[now_dt.month - 1]
        date_str = f"{now_dt.day}-{m_name}, {now_dt.year} йил"
        markup.row(InlineKeyboardButton("📍 Локация орқали (Автоматик)", callback_data=f"tz_req_loc_{group_id}"))
        markup.row(
            InlineKeyboardButton("🇺🇿 Тошкент (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Тошкент (UTC+5)"),
            InlineKeyboardButton("🇺🇿 Самарқанд (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Самарқанд (UTC+5)")
        )
        markup.row(
            InlineKeyboardButton("🇺🇿 Фарғона (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Фарғона (UTC+5)"),
            InlineKeyboardButton("🇺🇿 Бухоро (UTC+5)", callback_data=f"tz_set_quick_{group_id}_5_Бухоро (UTC+5)")
        )
        markup.row(InlineKeyboardButton("🗺 Бошқа барча вилоятлар рўйхати", callback_data=f"tz_all_regions_{group_id}"))
        markup.row(InlineKeyboardButton("✏️ Қўлда UTC фарқини киритиш (+5, +4...)", callback_data=f"tz_custom_input_{group_id}"))
        markup.row(
            InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
        )
        txt = (
            f"🌐 <b>{title} — ВАҚТ ВА САНА СОЗЛАМАЛАРИ</b>\n\n"
            f"• 🕒 <b>Ҳозирги аниқ вақт:</b> <code>{time_str}</code>\n"
            f"• 📅 <b>Сана ва Йил:</b> <code>{date_str}</code>\n"
            f"• 🌍 <b>Жорий минтақа:</b> <code>{tz_city}</code>\n\n"
            f"<b>Вақтни тўғрилаш усулини танланг:</b>\n"
            f"1. 📍 <b>Локация юбориш:</b> Телеграм геопозициянгиз орқали секундигача автоматик аниқланади.\n"
            f"2. 🗺 <b>Минтақа бўйича:</b> Ўзбекистон вилоятини танлаш.\n"
            f"3. ✏️ <b>Қўлда таҳрирлаш:</b> UTC вақт фарқини киритиш."
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# 14. ҚУЛФЛАР, ЛИМИТЛАР, ТУНГИ ҚУЛФ ВА РЎЙХАТЛАР (КЎПТИЛЛИК)
def show_locks_panel(chat_id, group_id, message_id, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"

    def lock_lbl(key, default=1):
        is_locked = g and g.get(key, default) == 1
        return "🔴" if is_locked else "🟢"

    l_links = lock_lbl("lock_links", 1)
    l_fwd = lock_lbl("lock_forwards", 1)
    l_spam = lock_lbl("lock_spam", 1)
    l_badwords = lock_lbl("lock_badwords", 1)
    l_stickers = lock_lbl("lock_stickers", 0)
    l_arabic = lock_lbl("lock_arabic", 1)
    l_media = lock_lbl("lock_media", 0)
    l_files = lock_lbl("lock_files", 0)
    l_voice = lock_lbl("lock_voice", 0)

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(
            InlineKeyboardButton(f"🔗 Ссылки: {l_links}", callback_data=f"toggle_links_{group_id}"),
            InlineKeyboardButton(f"🔄 Пересылки: {l_fwd}", callback_data=f"toggle_fwd_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🚫 Спам: {l_spam}", callback_data=f"toggle_spam_{group_id}"),
            InlineKeyboardButton(f"🤬 Мат/Слова: {l_badwords}", callback_data=f"toggle_badwords_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🎭 Стикеры: {l_stickers}", callback_data=f"toggle_stickers_{group_id}"),
            InlineKeyboardButton(f"🇦🇪 Арабские: {l_arabic}", callback_data=f"toggle_arabic_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"📦 Файлы/APK: {l_files}", callback_data=f"toggle_files_{group_id}"),
            InlineKeyboardButton(f"🎙 Голосовые: {l_voice}", callback_data=f"toggle_voice_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🎬 Медиа: {l_media}", callback_data=f"toggle_media_{group_id}"),
            InlineKeyboardButton("📊 Лимиты", callback_data=f"panel_limits_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("🔒 Все замки включить", callback_data=f"lock_all_{group_id}"),
            InlineKeyboardButton("🔓 Все замки выключить", callback_data=f"unlock_all_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Настройки группы", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
        )
        txt = (
            f"🛡 <b>{title} — ЦЕНТР БЛОКИРОВОК (ЗАМКИ)</b>\n\n"
            f"🔴 — Запрещено (Удаляется) | 🟢 — Разрешено\n\n"
            f"<i>Нажимайте на кнопки, чтобы включать или отключать замки:</i>"
        )
    elif lang == "en":
        markup.row(
            InlineKeyboardButton(f"🔗 Links: {l_links}", callback_data=f"toggle_links_{group_id}"),
            InlineKeyboardButton(f"🔄 Forwards: {l_fwd}", callback_data=f"toggle_fwd_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🚫 Spam: {l_spam}", callback_data=f"toggle_spam_{group_id}"),
            InlineKeyboardButton(f"🤬 Bad Words: {l_badwords}", callback_data=f"toggle_badwords_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🎭 Stickers: {l_stickers}", callback_data=f"toggle_stickers_{group_id}"),
            InlineKeyboardButton(f"🇦🇪 Arabic Text: {l_arabic}", callback_data=f"toggle_arabic_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"📦 Files/APKs: {l_files}", callback_data=f"toggle_files_{group_id}"),
            InlineKeyboardButton(f"🎙 Voice Notes: {l_voice}", callback_data=f"toggle_voice_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🎬 Media: {l_media}", callback_data=f"toggle_media_{group_id}"),
            InlineKeyboardButton("📊 Limits", callback_data=f"panel_limits_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("🔒 Lock All", callback_data=f"lock_all_{group_id}"),
            InlineKeyboardButton("🔓 Unlock All", callback_data=f"unlock_all_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Group Settings", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")
        )
        txt = (
            f"🛡 <b>{title} — SECURITY LOCKS CENTER</b>\n\n"
            f"🔴 — Locked (Deleted) | 🟢 — Allowed\n\n"
            f"<i>Click the buttons to toggle restrictions:</i>"
        )
    else:
        markup.row(
            InlineKeyboardButton(f"🔗 Ҳавола: {l_links}", callback_data=f"toggle_links_{group_id}"),
            InlineKeyboardButton(f"🔄 Форвард: {l_fwd}", callback_data=f"toggle_fwd_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🚫 Спам: {l_spam}", callback_data=f"toggle_spam_{group_id}"),
            InlineKeyboardButton(f"🤬 Сўкиниш: {l_badwords}", callback_data=f"toggle_badwords_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🎭 Стикер: {l_stickers}", callback_data=f"toggle_stickers_{group_id}"),
            InlineKeyboardButton(f"🇦🇪 Арабча: {l_arabic}", callback_data=f"toggle_arabic_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"📦 Файл/APK: {l_files}", callback_data=f"toggle_files_{group_id}"),
            InlineKeyboardButton(f"🎙 Овозли: {l_voice}", callback_data=f"toggle_voice_{group_id}")
        )
        markup.row(
            InlineKeyboardButton(f"🎬 Медиа: {l_media}", callback_data=f"toggle_media_{group_id}"),
            InlineKeyboardButton("📊 Лимитлар", callback_data=f"panel_limits_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("🔒 Барчасини ёқиш (Блок)", callback_data=f"lock_all_{group_id}"),
            InlineKeyboardButton("🔓 Барчасини очиш", callback_data=f"unlock_all_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
        )
        txt = (
            f"🛡 <b>{title} — ҚУЛФЛАР МАРКАЗИ</b>\n\n"
            f"🔴 — Тақиқланган (Ўчирилади) | 🟢 — Рухсат этилган\n\n"
            f"<i>Керакли тугмани босиб қулфни ёқинг ёки очинг:</i>"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_channels_panel(chat_id, message_id=None, lang="uz_kr"):
    cursor.execute("SELECT chat_id, title, username FROM channels ORDER BY rowid ASC")
    channels = cursor.fetchall()

    markup = InlineKeyboardMarkup()
    for ch in channels:
        u_str = f" ({ch['username']})" if ch.get("username") else ""
        c_title = ch.get("title") or "Канал"
        markup.row(
            InlineKeyboardButton(f"📢 {c_title}{u_str}", callback_data="noop"),
            InlineKeyboardButton("❌ Узиш", callback_data=f"ch_del_{ch['chat_id']}")
        )
    markup.row(InlineKeyboardButton("➕ Каналга қўшиш", callback_data="menu_add_channel"))
    markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))

    txt = (
        f"📢 <b>УЛАНГАН КАНАЛЛАР БОШҚАРУВИ</b>\n\n"
        f"Уланган каналлар сони: <b>{len(channels)} та</b>\n\n"
        f"Бот орқали чиқариладиган барча реклама, асаларичилик янгиликлари ва маълумотлар гуруҳлар билан бир қаторда ушбу каналларга ҳам автоматик юборилади ва тепасига қадаб (закрепить қилиб) қўйилади."
    )
    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_limits_panel(chat_id, group_id, message_id, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"
    l_en = g.get("limit_enabled", 1) if g else 1
    l_max = g.get("limit_max", 3) if g else 3
    l_hrs = g.get("limit_hours", 24) if g else 24
    l_mute = g.get("limit_repeat_mute", 1) if g else 1
    cust_msg = g.get("limit_warn_msg", "") if g else ""
    msg_status = "Ўрнатилган ✍️" if cust_msg else "Стандарт (Дефолт)"

    st_lbl = ("🟢 Включено" if lang == "ru" else ("🟢 Enabled" if lang == "en" else "🟢 Ёқилган")) if l_en else ("⚪️ Выключено" if lang == "ru" else ("⚪️ Disabled" if lang == "en" else "⚪️ Ўчирилган"))
    mute_lbl = ("🟢 Вкл (24ч МУТ)" if lang == "ru" else ("🟢 On (24h MUTE)" if lang == "en" else "🟢 Ёқилган (24с МУТ)")) if l_mute else ("⚪️ Выкл" if lang == "ru" else ("⚪️ Off" if lang == "en" else "⚪️ Ўчирилган"))

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(f"Ҳолати: {st_lbl}", callback_data=f"toggle_limit_en_{group_id}"),
        InlineKeyboardButton(f"🔢 Макс: {l_max} та", callback_data=f"cycle_limit_max_{group_id}")
    )
    markup.row(
        InlineKeyboardButton(f"⚖️ Қайта бузишда: {mute_lbl}", callback_data=f"toggle_limit_mute_{group_id}")
    )
    markup.row(
        InlineKeyboardButton(f"✍️ Огоҳлантириш матни ({msg_status})", callback_data=f"change_limit_msg_{group_id}")
    )
    markup.row(
        InlineKeyboardButton("🔢 1 та", callback_data=f"set_lim_{group_id}_1"),
        InlineKeyboardButton("🔢 3 та (Тавсия)", callback_data=f"set_lim_{group_id}_3"),
        InlineKeyboardButton("🔢 5 та", callback_data=f"set_lim_{group_id}_5")
    )
    grp_lbl = "◀️ Настройки группы" if lang == "ru" else ("◀️ Group Settings" if lang == "en" else "◀️ Гуруҳ Созламалари")
    main_lbl = "🏠 Главное меню" if lang == "ru" else ("◀️ Main Menu" if lang == "en" else "◀️ Асосий Меню")
    markup.row(
        InlineKeyboardButton(grp_lbl, callback_data=f"panel_settings_{group_id}"),
        InlineKeyboardButton(main_lbl, callback_data="back_main")
    )

    if lang == "ru":
        txt = (
            f"📊 <b>{title} — ЛИМИТЫ МЕДИА (ФОТО/ВИДЕО И АЛЬБОМЫ)</b>\n\n"
            f"• Статус: {st_lbl}\n"
            f"• Разрешено в сутки: {l_max} фото/видео (включая альбомы)\n"
            f"• Наказание за повторное нарушение: {mute_lbl}\n"
            f"• Текст предупреждения: <i>{msg_status}</i>\n\n"
            f"<i>Если пользователь отправляет альбом из 5 фото, лишние фото (свыше {l_max}) автоматически удаляются с предупреждением!</i>"
        )
    elif lang == "en":
        txt = (
            f"📊 <b>{title} — MEDIA LIMITS (PHOTOS/VIDEOS & ALBUMS)</b>\n\n"
            f"• Status: {st_lbl}\n"
            f"• Allowed per day: {l_max} photos/videos\n"
            f"• Repeat penalty: {mute_lbl}\n"
            f"• Warning text: <i>{msg_status}</i>\n\n"
            f"<i>When a user sends an album of 5 photos, any photos exceeding {l_max} are auto-deleted with a warning!</i>"
        )
    else:
        txt = (
            f"📊 <b>{title} — МЕДИА ЛИМИТЛАРИ (РАСМ, ВИДЕО ВА АЛЬБОМЛАР)</b>\n\n"
            f"• 🔔 <b>Ҳолати:</b> {st_lbl}\n"
            f"• 🔢 <b>Бир кунлик рухсат:</b> {l_max} та расм/видео\n"
            f"• ⚖️ <b>Қайта бузишда жазо:</b> {mute_lbl}\n"
            f"• ✍️ <b>Огоҳлантириш матни:</b> {msg_status}\n\n"
            f"💡 <b>Альбом назорати:</b> Агар фойдаланувчи 5 та расмни биттада (альбом қилиб) ташласа, белгиланган <b>{l_max} таси қолади</b>, ортиқчаси эса автоматик ўчирилиб огоҳлантириш берилади! Қайта бузса 24 соатга МУТ ўрнатилади."
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_autolock_panel(chat_id, group_id, message_id, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"
    al_en = g.get("autolock_enabled", 0) if g else 0
    s_time = g.get("autolock_start_time", "23:00") if g else "23:00"
    e_time = g.get("autolock_end_time", "06:30") if g else "06:30"

    st_lbl = ("🟢 Включено" if lang == "ru" else ("🟢 Enabled" if lang == "en" else "🟢 Ёқилган")) if al_en else ("⚪️ Выключено" if lang == "ru" else ("⚪️ Disabled" if lang == "en" else "⚪️ Ўчирилган"))
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"Ҳолати / Status: {st_lbl}", callback_data=f"toggle_autolock_en_{group_id}"))
    markup.row(
        InlineKeyboardButton(f"🔒 {s_time}", callback_data=f"cycle_autolock_start_{group_id}"),
        InlineKeyboardButton(f"🔓 {e_time}", callback_data=f"cycle_autolock_end_{group_id}")
    )
    grp_lbl = "◀️ Настройки группы" if lang == "ru" else ("◀️ Group Settings" if lang == "en" else "◀️ Гуруҳ Созламалари")
    main_lbl = "🏠 Главное меню" if lang == "ru" else ("◀️ Main Menu" if lang == "en" else "◀️ Асосий Меню")
    markup.row(
        InlineKeyboardButton(grp_lbl, callback_data=f"panel_settings_{group_id}"),
        InlineKeyboardButton(main_lbl, callback_data="back_main")
    )

    if lang == "ru":
        txt = (
            f"🌙 <b>{title} — НОЧНОЙ АВТО-ЗАМОК</b>\n\n"
            f"• Статус: {st_lbl}\n"
            f"• Время закрытия чата: <b>{s_time}</b>\n"
            f"• Время открытия чата: <b>{e_time}</b>\n\n"
            f"<i>В ночные часы чат блокируется, чтобы участники группы могли спокойно отдыхать.</i>"
        )
    elif lang == "en":
        txt = (
            f"🌙 <b>{title} — NIGHT AUTO-LOCK</b>\n\n"
            f"• Status: {st_lbl}\n"
            f"• Mute start time: <b>{s_time}</b>\n"
            f"• Unmute time: <b>{e_time}</b>\n\n"
            f"<i>During night hours, group messages are muted automatically to prevent disturbance.</i>"
        )
    else:
        txt = (
            f"🌙 <b>{title} — ТУНГИ АВТО-ҚУЛФЛАШ</b>\n\n"
            f"• Ҳолати: {st_lbl}\n"
            f"• Ёзишни тўхтатиш вақти: <b>{s_time}</b>\n"
            f"• Қайта очиш вақти: <b>{e_time}</b>\n\n"
            f"<i>Тунги вақтда гуруҳ аъзолари безовта бўлмаслиги учун гуруҳ автоматик қулфланади ва эрталаб очилади.</i>"
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

def show_lists_panel(chat_id, group_id, message_id, lang="uz_kr"):
    g = get_group(group_id)
    title = html.escape(str(g["title"])) if g and g.get("title") else "Гуруҳ"

    cursor.execute("SELECT COUNT(*) as c FROM whitelist WHERE chat_id = ?", (group_id,))
    w_cnt = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM blacklist WHERE chat_id = ?", (group_id,))
    b_cnt = cursor.fetchone()["c"]

    markup = InlineKeyboardMarkup()
    if lang == "ru":
        markup.row(
            InlineKeyboardButton(f"⚪️ Белый список ({w_cnt})", callback_data=f"view_wl_{group_id}"),
            InlineKeyboardButton(f"⚫️ Черный список ({b_cnt})", callback_data=f"view_bl_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Настройки группы", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
        )
        txt = (
            f"≡ <b>{title} — СПИСКИ (БЕЛЫЙ И ЧЕРНЫЙ)</b>\n\n"
            f"• <b>Белый список:</b> Доверенные участники, на которых не действуют замки и лимиты.\n"
            f"• <b>Черный список:</b> Заблокированные нарушители."
        )
    elif lang == "en":
        markup.row(
            InlineKeyboardButton(f"⚪️ Whitelist ({w_cnt})", callback_data=f"view_wl_{group_id}"),
            InlineKeyboardButton(f"⚫️ Blacklist ({b_cnt})", callback_data=f"view_bl_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Group Settings", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")
        )
        txt = (
            f"≡ <b>{title} — WHITELIST & BLACKLIST</b>\n\n"
            f"• <b>Whitelist:</b> Trusted members immune to bot locks and limits.\n"
            f"• <b>Blacklist:</b> Banned members restricted from the group."
        )
    else:
        markup.row(
            InlineKeyboardButton(f"⚪️ Оқ рўйхат ({w_cnt})", callback_data=f"view_wl_{group_id}"),
            InlineKeyboardButton(f"⚫️ Қора рўйхат ({b_cnt})", callback_data=f"view_bl_{group_id}")
        )
        markup.row(
            InlineKeyboardButton("◀️ Гуруҳ Созламалари", callback_data=f"panel_settings_{group_id}"),
            InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main")
        )
        txt = (
            f"≡ <b>{title} — РЎЙХАТЛАР БЎЛИМИ</b>\n\n"
            f"• <b>Оқ рўйхат:</b> Бот чекловлари ва лимитлари қўлланмайдиган ишончли аъзолар.\n"
            f"• <b>Қора рўйхат:</b> Гуруҳдан бутунлай блокланган фойдаланувчилар."
        )
    safe_edit_or_send(chat_id, message_id, txt, markup)

# ==================== ХАБАР ҲЕНДЛЕРЛАРИ ====================

# 1. Личкада /start ва /menu буйруғи
@bot.message_handler(commands=['start', 'menu'], func=lambda m: m.chat.type == 'private')
def cmd_start_private(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Foydalanuvchi"
    u_lang = get_user_lang(user_id)

    # Старт параметри (Гуруҳ, Қулфлар ёки Изоҳлар)
    args = message.text.split()
    if len(args) > 1:
        param = args[1]
        if param.startswith("locks_"):
            try:
                group_id = int(param.replace("locks_", ""))
                show_locks_panel(message.chat.id, group_id, message_id=None, lang=u_lang)
                return
            except Exception:
                pass
        elif param.startswith("settings_"):
            try:
                group_id = int(param.replace("settings_", ""))
                show_settings_panel(message.chat.id, group_id, lang=u_lang)
                return
            except Exception:
                pass
        elif param.startswith("unmute_"):
            try:
                grp_id = int(param.replace("unmute_", ""))
                g = get_group(grp_id)
                chan = g.get("forcesub_channel", "@Asalarichilik_Uz") if g else "@Asalarichilik_Uz"
                is_sub, missing = check_user_channels_subscription(chan, user_id)
                if is_sub:
                    cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (grp_id, user_id))
                    conn.commit()
                    lift_user_mute(grp_id, user_id)
                    grp_title = html.escape(str(g.get('title', 'Гуруҳ')) if g else 'Гуруҳ')
                    bot.send_message(
                        chat_id,
                        f"🎉 <b>Табриклаймиз!</b>\n\nСиз <b>{chan}</b> каналига аъзо экансиз.\n<b>{grp_title}</b> гуруҳида ёзишга бўлган чеклов (мут) тўлиқ олиб ташланди!\n\nЭнди гуруҳда бемалол хабар ёзишингиз мумкин. ✅",
                        parse_mode="HTML"
                    )
                    return
                else:
                    sub_markup = InlineKeyboardMarkup()
                    for m_ch in (missing if missing else [chan]):
                        c_clean = m_ch.replace("@", "")
                        sub_markup.row(InlineKeyboardButton(f"📢 {m_ch} каналига аъзо бўлиш", url=f"https://t.me/{c_clean}"))
                    sub_markup.row(InlineKeyboardButton("✅ Аъзо бўлдим (Текшириш)", callback_data=f"check_sub_{grp_id}_{user_id}"))
                    bot.send_message(
                        chat_id,
                        f"⚠️ <b>Чекловни олиб ташлаш учун:</b>\n\nАввал расмий каналимизга аъзо бўлишингиз керак:\n📢 <b>{chan}</b>\n\nАъзо бўлгач «✅ Аъзо бўлдим (Текшириш)» тугмасини босинг.",
                        reply_markup=sub_markup,
                        parse_mode="HTML"
                    )
                    return
            except Exception as ue:
                logging.error(f"start unmute error: {ue}")
        elif param.startswith("comment_"):
            try:
                post_id = int(param.replace("comment_", ""))
                cursor.execute("SELECT post_id, target_name, message_text FROM controller_posts WHERE post_id = ?", (post_id,))
                p_row = cursor.fetchone()
                if p_row:
                    raw_ptext = p_row["message_text"] or ""
                    clean_ptext = re.sub(r'<[^>]+>', '', raw_ptext).strip()
                    if len(clean_ptext) > 160:
                        clean_ptext = clean_ptext[:160] + "..."
                    
                    cursor.execute("SELECT full_name, comment_text, created_at FROM post_comments WHERE post_id = ? ORDER BY comment_id DESC LIMIT 5", (post_id,))
                    c_rows = cursor.fetchall()
                    cursor.execute("SELECT COUNT(*) as c FROM post_comments WHERE post_id = ?", (post_id,))
                    c_count = cursor.fetchone()["c"]

                    comments_str = ""
                    if c_rows:
                        c_list = []
                        for cr in reversed(c_rows):
                            c_author = html.escape(cr["full_name"] or "Фойдаланувчи")
                            c_msg = html.escape(cr["comment_text"] or "")
                            c_list.append(f"👤 <b>{c_author}</b>: {c_msg}")
                        comments_str = "\n\n".join(c_list)
                    else:
                        comments_str = "<i>Ҳозирча изоҳлар йўқ. Биринчи бўлиб фикр қолдиринг!</i>"

                    txt = (
                        f"💬 <b>ПОСТ МУҲОКАМАСИ ВА ИЗОҲЛАР</b>\n\n"
                        f"📌 <b>Пост:</b> <i>«{html.escape(clean_ptext)}»</i>\n\n"
                        f"📊 <b>Жами фикрлар:</b> {c_count} та\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"{comments_str}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n\n"
                        f"✍️ <b>Ушбу пост бўйича ўз фикрингиз, саволингиз ёки изоҳингизни ёзиб юборинг:</b>"
                    )
                    USER_STATES[user_id] = {
                        "action": f"writing_comment_{post_id}",
                        "post_id": post_id
                    }
                    kb = InlineKeyboardMarkup()
                    kb.row(InlineKeyboardButton("🔄 Янгилаш", callback_data=f"refresh_comments_{post_id}"))
                    kb.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
                    bot.send_message(message.chat.id, txt, reply_markup=kb, parse_mode="HTML")
                    return
                else:
                    bot.send_message(message.chat.id, "❌ Бу пост топилмади ёки ўчирилган.")
                    return
            except Exception as e:
                logging.error(f"Comment open error: {e}")

    is_mgr = (user_id == OWNER_ID or is_user_admin_anywhere(user_id))
    welcome_text = get_welcome_text(first_name, u_lang)

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_reply_keyboard(u_lang, user_id),
        disable_web_page_preview=True
    )
    bot.send_message(
        message.chat.id,
        "🎛 <b>Асосий менюдан керакли бўлимни танланг:</b>" if u_lang not in ["ru", "en"] else ("🎛 <b>Выберите нужный раздел из меню:</b>" if u_lang == "ru" else "🎛 <b>Choose an option from main menu:</b>"),
        reply_markup=get_main_menu_markup(u_lang, user_id)
    )
    return

    welcome_text = get_welcome_text(first_name, u_lang)

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_reply_keyboard(u_lang, user_id),
        disable_web_page_preview=True
    )
    bot.send_message(
        message.chat.id,
        "🎛 <b>Асосий менюдан керакли бўлимни танланг:</b>" if u_lang not in ["ru", "en"] else ("🎛 <b>Выберите нужный раздел из меню:</b>" if u_lang == "ru" else "🎛 <b>Choose an option from main menu:</b>"),
        reply_markup=get_main_menu_markup(u_lang, user_id)
    )

# 2. Реклама ва Хабар тарқатиш буйруғи (Фақат эгаси учун)

@bot.message_handler(commands=['settings', 'post_settings', 'sozlamalar'], func=lambda m: m.chat.type == 'private')
def cmd_post_settings_handler(message):
    show_post_settings_menu(message.chat.id)

@bot.message_handler(commands=['broadcast', 'reklama'], func=lambda m: m.chat.type == 'private')
def cmd_broadcast(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "⛔️ Ушбу буйруқ фақат бот эгаси (@JamshidjonDavronov) учун!")
        return
    u_lang = get_user_lang(message.from_user.id)
    show_broadcast_menu(message.chat.id, lang=u_lang)

# 2.0 Асаларичилик янгиликлари буйруғи (/yangilik, /news)
@bot.message_handler(commands=['yangilik', 'news', 'statya'])
def cmd_bee_news(message):
    u_lang = get_user_lang(message.from_user.id)
    if message.chat.type == 'private':
        is_admin_user = (message.from_user.id == OWNER_ID or is_user_admin_anywhere(message.from_user.id))
        if not is_admin_user:
            bot.send_message(message.chat.id, "⚠️ Бу бўлим фақат гуруҳ админлари ва бот эгаси учун!")
            return
        show_bee_news_hub(message.chat.id, 0, None, lang=u_lang)
    else:
        try:
            item = BEE_GLOBAL_NEWS[int(time.time()) % len(BEE_GLOBAL_NEWS)]
            post_txt = format_bee_news_post(item, u_lang)
            sent = bot.send_message(message.chat.id, post_txt, parse_mode="HTML")
            try:
                bot.pin_chat_message(message.chat.id, sent.message_id, disable_notification=False)
            except Exception:
                pass
        except Exception as e:
            logging.warning(f"Error in group /news: {e}")

# 2.0.1 Асаларичилик викторинаси буйруғи (/quiz, /opros, /viktorina)
@bot.message_handler(commands=['quiz', 'opros', 'viktorina'])
def cmd_bee_quiz(message):
    u_lang = get_user_lang(message.from_user.id)
    if message.chat.type == 'private':
        is_admin_user = (message.from_user.id == OWNER_ID or is_user_admin_anywhere(message.from_user.id))
        if not is_admin_user:
            bot.send_message(message.chat.id, "⚠️ Бу бўлим фақат гуруҳ админлари ва бот эгаси учун!")
            return
        show_quiz_hub(message.chat.id, 0, None, lang=u_lang)
    else:
        try:
            cfg = get_global_quiz_config()
            all_quizzes = get_all_bee_quizzes(cfg.get("category_filter", "all"))
            if all_quizzes:
                q_idx = int(time.time()) % len(all_quizzes)
                item = all_quizzes[q_idx]
                q_script = cfg.get("script") or get_system_setting("quiz_script", "uz_kr")
                rand_item = randomize_quiz_options(item)
                if q_script == "uz_lat":
                    q_text = rand_item.get("question_lat") or rand_item.get("question_kr")
                    opts = rand_item.get("options_lat") or rand_item.get("options_kr")
                    expl = rand_item.get("explanation_lat") or rand_item.get("explanation_kr")
                else:
                    q_text = rand_item.get("question_kr")
                    opts = rand_item.get("options_kr")
                    expl = rand_item.get("explanation_kr")
                corr_id = rand_item.get("correct_id", 0)
                chan = get_official_channel()
                grp = get_official_group()
                c_clean = chan.replace("@", "")
                g_clean = grp.replace("@", "").replace("https://t.me/", "")
                g_url = grp if grp.startswith("http") else f"https://t.me/{g_clean}"
                share_txt = format_quiz_share_text(q_text, opts, c_clean, g_url)
                quiz_markup = get_post_buttons_markup(content_type="quiz", content_id=str(item.get("id", q_idx)), share_text=share_txt)
                try:
                    poll_msg = bot.send_poll(
                        chat_id=message.chat.id,
                        question=q_text,
                        options=opts,
                        is_anonymous=True,
                        type="quiz",
                        correct_option_id=corr_id,
                        explanation=expl if expl else None,
                        explanation_parse_mode="HTML",
                        reply_markup=quiz_markup
                    )
                except Exception:
                    poll_msg = bot.send_poll(
                        chat_id=message.chat.id,
                        question=q_text,
                        options=opts,
                        is_anonymous=True,
                        type="quiz",
                        correct_option_id=corr_id,
                        explanation=expl if expl else None,
                        explanation_parse_mode="HTML"
                    )
                try:
                    bot.pin_chat_message(message.chat.id, poll_msg.message_id, disable_notification=False)
                except Exception:
                    pass
                del_h = cfg.get("delete_hours", 0)
                if del_h > 0:
                    threading.Timer(del_h * 3600, lambda c=message.chat.id, m=poll_msg.message_id: delete_msg_safe(c, m)).start()
        except Exception as e:
            logging.warning(f"Error handling /quiz in chat: {e}")

# 2.0.2 Маълумотлар базасини бошқариш буйруғи (/database, /db, /admin_db)
@bot.message_handler(commands=['database', 'db', 'admin_db'], func=lambda m: m.chat.type == 'private')
def cmd_database(message):
    if message.from_user.id != OWNER_ID and not is_user_admin_anywhere(message.from_user.id):
        bot.send_message(message.chat.id, "⛔️ Ушбу бўлим фақат бот маъмурлари учун!")
        return
    u_lang = get_user_lang(message.from_user.id)
    show_database_settings_menu(message.chat.id, lang=u_lang)

# 2.1 Гуруҳлар назорати буйруқлари (Фақат эгаси учун)
@bot.message_handler(commands=['groups', 'admin'], func=lambda m: m.chat.type == 'private')
def cmd_groups_control(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "⛔️ Ушбу бўлим фақат бот эгаси (@JamshidjonDavronov) учун!")
        return
    u_lang = get_user_lang(message.from_user.id)
    show_owner_groups_panel(message.chat.id, lang=u_lang)

# 2.2 Личкадан гуруҳга хабар юбориб Закрепить (Pin) қилиш буйруғи
@bot.message_handler(commands=['pin', 'qada', 'закрепить'], func=lambda m: m.chat.type == 'private')
def cmd_pin_pm(message):
    if message.from_user.id != OWNER_ID:
        return
    u_lang = get_user_lang(message.from_user.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "ℹ️ <b>Фойдаланиш:</b> <code>/pin Эълон матни</code>\n\n(Гуруҳни танлайсиз ва бот ушбу хабарни гуруҳга чиқариб, дарҳол закрепить қилади)", parse_mode="HTML")
        return

    pin_text = parts[1].strip()
    cursor.execute("SELECT chat_id, title FROM groups WHERE is_authorized = 1 ORDER BY rowid DESC")
    grps = cursor.fetchall()
    if not grps:
        bot.send_message(message.chat.id, "⚠️ Ҳозирча рухсат берилган гуруҳлар йўқ.")
        return

    USER_STATES[OWNER_ID] = {"action": "pin_pending_send", "text": pin_text}
    markup = InlineKeyboardMarkup()
    for g in grps:
        markup.row(InlineKeyboardButton(f"👥 {g['title']}", callback_data=f"pin_to_grp_{g['chat_id']}"))
    markup.row(InlineKeyboardButton("❌ Бекор қилиш", callback_data="back_main"))
    bot.send_message(
        message.chat.id,
        f"📌 <b>Ушбу хабарни қайси гуруҳга чиқариб ЗАКРЕПИТЬ қиламиз?</b>\n\n<i>«{pin_text}»</i>",
        reply_markup=markup,
        parse_mode="HTML"
    )

# 2.3 Бот номидан гуруҳга ёзиш буйруғи (/say ва /gapir)
@bot.message_handler(commands=['say', 'gapir', 'chat'], func=lambda m: m.chat.type == 'private')
def cmd_say(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "⛔️ Фақат бот эгаси учун!")
        return
    u_lang = get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)

    # 1. /say -100xxx <matn> кўринишида тўғридан-тўғри юбориш
    if len(args) >= 3 and args[1].startswith("-100"):
        try:
            target_gid = int(args[1])
            text_to_send = args[2]
            bot.send_message(target_gid, text_to_send)
            bot.send_message(message.chat.id, f"✅ Хабар бот номидан гуруҳга (<code>{target_gid}</code>) муваффақиятли юборилди!", parse_mode="HTML")
            return
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Гуруҳга юборишда хатолик: {e}")
            return

    # Фаол гуруҳларни базадан олиш
    cursor.execute("SELECT chat_id, title FROM groups WHERE is_authorized = 1 ORDER BY rowid DESC")
    grps = cursor.fetchall()
    if not grps:
        bot.send_message(message.chat.id, "⚠️ Ҳозирча ботга уланган рухсат этилган гуруҳлар йўқ.")
        return

    # 2. /say <matn> кўринишида гуруҳ танлаб юбориш
    if len(args) >= 2 and not args[1].startswith("-100"):
        text_to_send = message.text[len(args[0]):].strip()
        USER_STATES[OWNER_ID] = {"action": "say_pending_send", "text": text_to_send}
        markup = InlineKeyboardMarkup()
        for g in grps:
            markup.row(InlineKeyboardButton(f"👥 {g['title']}", callback_data=f"say_to_grp_{g['chat_id']}"))
        markup.row(InlineKeyboardButton("❌ Бекор қилиш", callback_data="back_main"))
        bot.send_message(
            message.chat.id,
            f"🎙 <b>Ушбу хабарни қайси гуруҳга БОТ НОМИДАН юборамиз?</b>\n\n<i>«{text_to_send}»</i>",
            reply_markup=markup,
            parse_mode="HTML"
        )
        return

    # 3. Фақат /say буйруғи юборилса: Жонли мулоқот учун гуруҳ танлаш
    markup = InlineKeyboardMarkup()
    for g in grps:
        markup.row(InlineKeyboardButton(f"👥 {g['title']}", callback_data=f"bot_chat_{g['chat_id']}"))
    markup.row(InlineKeyboardButton("🏠 Асосий меню", callback_data="back_main"))
    bot.send_message(
        message.chat.id,
        "🎙 <b>БОТ НОМИДАН ЖОНЛИ МУЛОҚОТ</b>\n\nҚайси гуруҳ билан бот номидан гаплашмоқчисиз? Гуруҳни танланг:",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.message_handler(commands=['allow'], func=lambda m: m.chat.type == 'private')
def cmd_allow_group(message):
    if message.from_user.id != OWNER_ID:
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "ℹ️ <b>Фойдаланиш:</b> <code>/allow -1001234567890</code>\n\n(Гуруҳ ID рақамини ёзинг)", parse_mode="HTML")
        return
    try:
        gid = int(args[1])
        cursor.execute("INSERT OR IGNORE INTO groups (chat_id, title) VALUES (?, ?)", (gid, "Гуруҳ"))
        cursor.execute("UPDATE groups SET is_authorized = 1 WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ <b>Гуруҳга муваффақиятли рухсат берилди!</b> (ID: <code>{gid}</code>)\n\nЭнди ушбу гуруҳга бот қўшилса, у автоматик ишлайди.", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Хатолик: {e}")

# 2.4 Бот файлини личкага олиш (/code, /kod, /getcode)
@bot.message_handler(commands=['code', 'kod', 'getcode', 'botfile'], func=lambda m: m.chat.type == 'private')
def cmd_send_code_file(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "⛔️ Ушбу буйруқ фақат бот эгаси (@JamshidjonDavronov) учун!")
        return
    try:
        current_file = os.path.abspath(__file__)
        if not os.path.exists(current_file):
            current_file = 'bot.py'
        if os.path.exists(current_file):
            with open(current_file, 'rb') as doc:
                bot.send_document(
                    message.chat.id,
                    doc,
                    caption="🐝 <b>Asalarichilik.Uz - Сўнгги янгиланган бот коди (bot.py)</b>\n\n🌙 Тунги ақилли қулф (Smart Autolock) ва барча тузатишлар билан.",
                    parse_mode="HTML"
                )
        else:
            bot.send_message(message.chat.id, "❌ Бот файли топилмади.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Кодни юборишда хатолик: {e}")

# 3. /help буйруғи
@bot.message_handler(commands=['help'], func=lambda m: m.chat.type == 'private')
def cmd_help_private(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "⛔️ Кириш тақиқланган! Бот маълумотлари махфий.")
        return
    u_lang = get_user_lang(message.from_user.id)
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(get_main_menu_btn_label(u_lang), callback_data="back_main"))
    bot.send_message(message.chat.id, get_guide_text(u_lang), reply_markup=markup)

# 4. Личкада геопозиция (локация) қабул қилиш
@bot.message_handler(content_types=['location'], func=lambda m: m.chat.type == 'private')
def handle_location(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.send_message(
            message.chat.id,
            "⛔️ <b>Кириш тақиқланган!</b>\n\n"
            "Ушбу бот шахсий тизим бўлиб, фақат бот эгаси (@JamshidjonDavronov) учун мўлжалланган. "
            "Бот маълумотлари ҳеч кимга берилмайди.",
            parse_mode="HTML"
        )
        return
    state = USER_STATES.get(user_id)
    if state and state.get("action") == "wait_location":
        gid = state.get("group_id")
        lat = message.location.latitude
        lon = message.location.longitude
        calculated_offset = round(lon / 15.0)
        loc_city = f"Локация (UTC+{calculated_offset})" if calculated_offset >= 0 else f"Локация (UTC{calculated_offset})"

        cursor.execute("UPDATE groups SET timezone_offset = ?, timezone_city = ? WHERE chat_id = ?", (calculated_offset, loc_city, gid))
        conn.commit()
        USER_STATES.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            f"✅ <b>Геолокация муваффақиятли қабул қилинди!</b>\n\n"
            f"• Координаталар: {lat:.4f}, {lon:.4f}\n"
            f"• Аниқланган вақт минтақаси: <b>UTC+{calculated_offset}</b>\n"
            f"• Гуруҳ соати ва санаси тўлиқ мослаштирилди!",
            reply_markup=get_main_reply_keyboard(get_user_lang(user_id), user_id)
        )
        show_timezone_panel(message.chat.id, gid, lang=get_user_lang(user_id))
    else:
        bot.send_message(message.chat.id, "📍 Локация қабул қилинди. Созламаларни очиш учун /start босинг.")

# 5. Личкадаги барча матнли хабарлар ва ҳолатлар (STATE TRACKING)
@bot.message_handler(func=lambda m: m.chat.type == 'private', content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'])
def handle_all_private_messages(message):
    user_id = message.from_user.id
    u_lang = get_user_lang(user_id)
    first_name = message.from_user.first_name or "Foydalanuvchi"
    txt = (message.text or message.caption or "").strip()

    # 3.1. Ҳолат текшируви (State handler)
    if user_id in USER_STATES:
        state = USER_STATES[user_id]
        action = state.get("action")
        # 1.0 Лайкларни қўлда киритиш (wait_post_custom_reactions)
        if action == "wait_post_custom_reactions":
            if txt not in ["◀️ Бекор қилиш", "Бекор қилиш", "Отмена"]:
                set_system_setting("reactions_set", txt)
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ <b>Янги реакциялар тўплами сақланди:</b> {txt}", parse_mode="HTML")
            else:
                USER_STATES.pop(user_id, None)
            show_post_settings_menu(message.chat.id)
            return

        # 1.1 Расмий канални қўлда киритиш (wait_post_custom_channel)
        if action == "wait_post_custom_channel":
            if txt not in ["◀️ Бекор қилиш", "Бекор қилиш", "Отмена"]:
                clean_c = clean_channel_username(txt)
                set_system_setting("official_channel", clean_c)
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ <b>Расмий канал сақланди:</b> <code>{clean_c}</code>", parse_mode="HTML")
            else:
                USER_STATES.pop(user_id, None)
            show_post_settings_menu(message.chat.id)
            return

        # 1.2 Расмий гуруҳни қўлда киритиш (wait_post_custom_group)
        if action == "wait_post_custom_group":
            if txt not in ["◀️ Бекор қилиш", "Бекор қилиш", "Отмена"]:
                clean_g = txt.strip()
                set_system_setting("official_group", clean_g)
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ <b>Расмий гуруҳ сақланди:</b> <code>{clean_g}</code>", parse_mode="HTML")
            else:
                USER_STATES.pop(user_id, None)
            show_post_settings_menu(message.chat.id)
            return

        # 0.1 Бот номидан жонли мулоқот режими (Live Intercom as Bot)
        if action == "live_chat_as_bot":
            if txt in ["❌ Мулоқотни тўхтатиш", "Тўхтатиш", "Стоп", "Stop", "Отмена", "❌ Бекор қилиш"]:
                USER_STATES.pop(user_id, None)
                bot.send_message(
                    message.chat.id,
                    "🛑 <b>Бот номидан гуруҳ билан мулоқот тўхтатилди.</b>",
                    reply_markup=get_main_reply_keyboard(u_lang, user_id),
                    parse_mode="HTML"
                )
                return

            target_gid = state.get("target_group_id")
            g_title = state.get("target_group_title", "Гуруҳ")
            try:
                if message.content_type == 'text':
                    bot.send_message(target_gid, message.text)
                elif message.content_type == 'voice':
                    bot.send_voice(target_gid, message.voice.file_id, caption=message.caption)
                elif message.content_type == 'photo':
                    bot.send_photo(target_gid, message.photo[-1].file_id, caption=message.caption)
                elif message.content_type == 'video':
                    bot.send_video(target_gid, message.video.file_id, caption=message.caption)
                elif message.content_type == 'document':
                    bot.send_document(target_gid, message.document.file_id, caption=message.caption)
                elif message.content_type == 'sticker':
                    bot.send_sticker(target_gid, message.sticker.file_id)
                elif message.content_type == 'audio':
                    bot.send_audio(target_gid, message.audio.file_id, caption=message.caption)

                bot.send_message(message.chat.id, f"✅ <b>{g_title}</b> гуруҳига бот номидан юборилди.")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Гуруҳга юборишда хатолик: {e}")
            return

        # 0.2 Гуруҳдаги маълум бир хабарга бот номидан жавоб бериш (Reply as Bot)
        if action == "reply_as_bot":
            if txt in ["❌ Бекор қилиш", "Бекор қилиш", "Отмена"]:
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, "❌ Бекор қилинди.", reply_markup=get_main_reply_keyboard(u_lang, user_id))
                return
            target_gid = state.get("target_group_id")
            mid = state.get("reply_to_msg_id")
            try:
                if message.content_type == 'text':
                    bot.send_message(target_gid, message.text, reply_to_message_id=mid)
                elif message.content_type == 'voice':
                    bot.send_voice(target_gid, message.voice.file_id, caption=message.caption, reply_to_message_id=mid)
                elif message.content_type == 'photo':
                    bot.send_photo(target_gid, message.photo[-1].file_id, caption=message.caption, reply_to_message_id=mid)
                elif message.content_type == 'video':
                    bot.send_video(target_gid, message.video.file_id, caption=message.caption, reply_to_message_id=mid)
                elif message.content_type == 'sticker':
                    bot.send_sticker(target_gid, message.sticker.file_id, reply_to_message_id=mid)

                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, "✅ Жавобингиз бот номидан гуруҳга етказилди!", reply_markup=get_main_reply_keyboard(u_lang, user_id))
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Юборишда хатолик: {e}")
            return


        # Изоҳ ёзиш ҳолати (Foydalanuvchi postga izoh yozganda)
        if action.startswith("writing_comment_"):
            try:
                post_id = state.get("post_id") or int(action.replace("writing_comment_", ""))
                c_text = message.text or message.caption or ""
                if not c_text:
                    bot.send_message(message.chat.id, "⚠️ Илтимос, изоҳ матнини ёзиб юборинг:")
                    return
                
                user_full_name = message.from_user.first_name or ""
                if message.from_user.last_name:
                    user_full_name += f" {message.from_user.last_name}"
                user_uname = message.from_user.username or ""

                cursor.execute(
                    "INSERT INTO post_comments (post_id, user_id, full_name, username, comment_text) VALUES (?, ?, ?, ?, ?)",
                    (post_id, user_id, user_full_name, user_uname, c_text)
                )
                conn.commit()
                USER_STATES.pop(user_id, None)

                bot.send_message(
                    message.chat.id,
                    "✅ <b>Сизнинг фикрингиз/изоҳингиз муваффақиятли қабул қилинди!</b>\n\nТашаккур, сизнинг фикрингиз биз учун муҳим.",
                    reply_markup=get_main_reply_keyboard(u_lang, user_id),
                    parse_mode="HTML"
                )

                try:
                    admin_alert = (
                        f"💬 <b>ПОСТГА ЯНГИ ИЗОҲ КЕЛДИ!</b>\n\n"
                        f"📌 <b>Пост ID:</b> #{post_id}\n"
                        f"👤 <b>Муаллиф:</b> {html.escape(user_full_name)} (@{user_uname})\n"
                        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                        f"📝 <b>Изоҳ:</b>\n<i>«{html.escape(c_text)}»</i>"
                    )
                    reply_kb = InlineKeyboardMarkup()
                    reply_kb.row(InlineKeyboardButton("✍️ Жавоб ёзиш", callback_data=f"bot_reply_{user_id}"))
                    bot.send_message(OWNER_ID, admin_alert, reply_markup=reply_kb, parse_mode="HTML")
                except Exception as ex:
                    logging.warning(f"Failed to alert admin about comment: {ex}")
                return
            except Exception as e:
                logging.error(f"Error saving comment: {e}")
                bot.send_message(message.chat.id, "❌ Изоҳни сақлашда хатолик юз берди.")
                return

        # 0. Контроллер бот: Reply клавиатура тугмалари ҳолат пайтида босилганда
        if txt in ["Отменить", "Отмена", "Cancel", "Бекор қилиш"]:
            USER_STATES.pop(user_id, None)
            bot.send_message(message.chat.id, "❌ Действие отменено." if u_lang == "ru" else "❌ Ҳаракат бекор қилинди.", reply_markup=get_main_reply_keyboard(u_lang, user_id))
            show_broadcast_menu(message.chat.id, lang=u_lang)
            return

        if txt in ["Очистить", "Clear", "Тозалаш"]:
            if "post" in state:
                state["post"]["text"] = ""
                state["post"]["media_type"] = "text"
                state["post"]["file_id"] = None
                state["post"]["reactions"] = []
                state["post"]["url_buttons"] = []
                state["action"] = "waiting_post_content"
                USER_STATES[user_id] = state
                bot.send_message(message.chat.id, "Пост очищен. Отправьте новое содержимое поста (текст, фото или видео):" if u_lang == "ru" else "Пост тозаланди. Янги матн ёки медиа юборинг:", reply_markup=get_cancel_reply_keyboard(u_lang))
            return

        if txt in ["Предпросмотр", "Preview", "Кўриб чиқиш"]:
            if "post" in state:
                render_post_editor_screen(message.chat.id, user_id, state["post"], lang=u_lang)
            return

        if txt in ["Далее", "Next", "Кейингиси"]:
            if "post" in state:
                show_publish_stage(message.chat.id, user_id, lang=u_lang)
            return

        # 0.1 Маълумотлар базаси ва манзиллар параметрларини ўзгартириш
        if action in ["wait_db_channel", "wait_dest_channel"]:
            chan = clean_channel_username(txt)
            set_system_setting("official_channel", chan)
            cursor.execute("UPDATE groups SET forcesub_channel = ? WHERE forcesub_channel IS NULL OR forcesub_channel = '' OR forcesub_channel LIKE '%asalarichilik%'", (chan,))
            conn.commit()
            USER_STATES.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ <b>Расмий Телеграм канали сақланди:</b> <code>{chan}</code>\n\nБарча гуруҳлар ва хабарлар учун янгиланди.", parse_mode="HTML")
            if action == "wait_dest_channel":
                show_destinations_settings_menu(message.chat.id, lang=u_lang)
            else:
                show_database_settings_menu(message.chat.id, lang=u_lang)
            return

        if action in ["wait_db_group", "wait_dest_group"]:
            grp = txt.strip()
            set_system_setting("official_group", grp)
            USER_STATES.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ <b>Расмий гуруҳ ҳаволаси сақланди:</b> <code>{grp}</code>", parse_mode="HTML")
            if action == "wait_dest_group":
                show_destinations_settings_menu(message.chat.id, lang=u_lang)
            else:
                show_database_settings_menu(message.chat.id, lang=u_lang)
            return

        if action in ["wait_db_youtube", "wait_dest_youtube"]:
            yt = txt.strip()
            set_system_setting("youtube_url", yt)
            USER_STATES.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ <b>YouTube канали ҳаволаси сақланди:</b> <code>{yt}</code>", parse_mode="HTML")
            if action == "wait_dest_youtube":
                show_destinations_settings_menu(message.chat.id, lang=u_lang)
            else:
                show_database_settings_menu(message.chat.id, lang=u_lang)
            return

        # 1. Контроллер бот: Пост матни ёки медиасини қабул қилиш
        if action == "waiting_post_content":
            post = state.get("post", {})
            m_type = message.content_type
            f_id = None
            cap_or_text = (getattr(message, 'html_text', None) or 
                           getattr(message, 'html_caption', None) or 
                           message.caption or 
                           message.text or "").strip()
            if m_type == "photo":
                f_id = message.photo[-1].file_id
            elif m_type == "video":
                f_id = message.video.file_id
            elif m_type == "document":
                f_id = message.document.file_id
            else:
                m_type = "text"

            post["media_type"] = m_type
            post["file_id"] = f_id
            post["text"] = cap_or_text
            state["action"] = "editing_post"
            USER_STATES[user_id] = state
            render_post_editor_screen(message.chat.id, user_id, post, lang=u_lang)
            return

        # 1.1. Реакцияларни қабул қилиш
        if action == "waiting_reactions_input":
            reacts = parse_reactions(txt)
            if reacts:
                state["post"]["reactions"] = reacts
                state["action"] = "editing_post"
                USER_STATES[user_id] = state
                bot.send_message(message.chat.id, "✅ Реакции добавлены к посту!" if u_lang == "ru" else "✅ Реакциялар постга қўшилди!")
                render_post_editor_screen(message.chat.id, user_id, state["post"], lang=u_lang)
            else:
                bot.send_message(message.chat.id, "❌ Реакциялар топилмади. Масалан: 👍 / 👎 / ❤️")
            return

        # 1.2. Муҳокама/Изоҳлар ҳаволасини қабул қилиш
        if action == "waiting_comments_url":
            raw_url = txt.strip()
            if not raw_url.startswith("http") and not raw_url.startswith("@") and not raw_url.startswith("t.me"):
                bot.send_message(message.chat.id, "❌ Нотўғри ҳавола! Масалан: https://t.me/Uz_Asalarichilik ёки @Uz_Asalarichilik кўринишида юборинг:")
                return
            if raw_url.startswith("@"):
                c_url = f"https://t.me/{raw_url.lstrip('@')}"
            elif raw_url.startswith("t.me"):
                c_url = f"https://{raw_url}"
            else:
                c_url = raw_url
            state["post"]["has_comments"] = True
            state["post"]["comments_url"] = c_url
            state["action"] = "editing_post"
            USER_STATES[user_id] = state
            bot.send_message(message.chat.id, f"✅ Муҳокама ҳаволаси сақланди: {c_url}")
            render_post_editor_screen(message.chat.id, user_id, state["post"], lang=u_lang)
            return

        # 1.2. URL-тугмаларни қабул қилиш
        if action == "waiting_urls_input":
            urls = parse_url_buttons(txt)
            if urls:
                state["post"]["url_buttons"] = urls
                state["action"] = "editing_post"
                USER_STATES[user_id] = state
                bot.send_message(message.chat.id, "✅ URL-кнопки успешно добавлены!" if u_lang == "ru" else "✅ Ҳавола тугмалари сақланди!")
                render_post_editor_screen(message.chat.id, user_id, state["post"], lang=u_lang)
            else:
                bot.send_message(message.chat.id, "❌ Формат не распознан. Отправьте в формате:\nКнопка 1 - https://t.me/kanal | Кнопка 2 - https://t.me/bot")
            return

        # 1.3. Медиафайл бириктириш
        if action == "waiting_media_input":
            if message.content_type in ["photo", "video", "document"]:
                state["post"]["media_type"] = message.content_type
                if message.content_type == "photo":
                    state["post"]["file_id"] = message.photo[-1].file_id
                elif message.content_type == "video":
                    state["post"]["file_id"] = message.video.file_id
                elif message.content_type == "document":
                    state["post"]["file_id"] = message.document.file_id
                if message.caption:
                    state["post"]["text"] = message.caption
                state["action"] = "editing_post"
                USER_STATES[user_id] = state
                bot.send_message(message.chat.id, "✅ Медиафайл успешно прикреплен!" if u_lang == "ru" else "✅ Медиафайл бириктирилди!")
                render_post_editor_screen(message.chat.id, user_id, state["post"], lang=u_lang)
                return
            else:
                bot.send_message(message.chat.id, "❌ Отправьте фото, видео или документ:")
                return

        # 1.4. Кейинга қолдириш вақтини қабул қилиш (Schedule)
        if action == "waiting_schedule_input":
            sched_dt = parse_schedule_time(txt)
            if sched_dt:
                post_dict = state["post"]
                t_id = post_dict.get("target_id", 0)
                text = post_dict.get("text", "")
                m_type = post_dict.get("media_type", "text")
                f_id = post_dict.get("file_id")
                reacts = post_dict.get("reactions", [])
                urls = post_dict.get("url_buttons", [])
                comments = post_dict.get("has_comments", False)
                native_c = post_dict.get("native_comments", False)
                is_silent = post_dict.get("is_silent", False)
                del_hours = post_dict.get("delete_timer_hours", 0)
                sched_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")

                c_url = post_dict.get("comments_url", "")
                cursor.execute("""
                INSERT INTO controller_posts 
                (target_id, target_name, message_text, media_type, media_file_id, reactions_json, url_buttons_json, has_comments, native_comments, comments_url, is_silent, delete_timer_hours, scheduled_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')
                """, (
                    t_id if str(t_id).lstrip('-').isdigit() else 0, post_dict.get("target_name", ""), text, m_type, f_id,
                    json.dumps(reacts), json.dumps(urls), 1 if comments else 0, 1 if native_c else 0, c_url,
                    1 if is_silent else 0, del_hours, sched_str
                ))
                conn.commit()
                USER_STATES.pop(user_id, None)
                h_time = sched_dt.strftime("%d.%m.%Y %H:%M")
                bot.send_message(message.chat.id, f"✅ <b>Пост успешно отложен на {h_time}!</b>" if u_lang == "ru" else f"✅ <b>Пост {h_time} вақтига муваффақиятли режалаштирилди!</b>", reply_markup=get_main_reply_keyboard(u_lang, user_id))
                show_broadcast_menu(message.chat.id, lang=u_lang)
                return
            else:
                bot.send_message(message.chat.id, "❌ Неверный формат времени! Введите ЧЧ:ММ (напр. 18:30) или ДД.ММ ЧЧ:ММ (напр. 15.10 18:30):")
                return

        # 2.0. Об-ҳаво ҳудудини қўлда ёзиш
        if action == "wait_weather_city":
            gid = state.get("group_id")
            city_name = txt.strip()
            if city_name:
                cursor.execute("UPDATE groups SET weather_city = ? WHERE chat_id = ?", (city_name, gid))
                conn.commit()
                backup_settings_to_file()
                USER_STATES.pop(user_id, None)
                bot.send_message(
                    message.chat.id,
                    f"✅ <b>Об-ҳаво ҳудуди «{city_name}» қилиб белгиланди!</b>",
                    parse_mode="HTML"
                )
                show_weather_panel(message.chat.id, gid, lang=u_lang)
                return
            else:
                bot.send_message(message.chat.id, "❌ Ҳудуд номи бўш бўлиши мумкин эмас. Илтимос, шаҳар ёки вилоят номини ёзинг:")
                return

        # 2. Об-ҳаво соатини қўлда ёзиш
        if action == "wait_weather_time":
            gid = state.get("group_id")
            time_match = re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', txt)
            if time_match:
                h, m = int(time_match.group(1)), int(time_match.group(2))
                formatted_time = f"{h:02d}:{m:02d}"
                cursor.execute("UPDATE groups SET weather_time = ? WHERE chat_id = ?", (formatted_time, gid))
                conn.commit()
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ <b>Об-ҳаво жўнатиш соати {formatted_time} қилиб белгиланди!</b>")
                show_weather_panel(message.chat.id, gid, lang=u_lang)
                return
            else:
                bot.send_message(message.chat.id, "❌ Нотўғри соат формати! Илтимос, <code>08:00</code>, <code>07:30</code> каби кўринишда ёзинг:")
        # 2.1. Викторина вақтини қўлда ёзиш (quiz_input_time)
        if action == "quiz_input_time":
            time_match = re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', txt)
            if time_match:
                h, m = int(time_match.group(1)), int(time_match.group(2))
                formatted_time = f"{h:02d}:{m:02d}"
                update_global_quiz_config(send_time=formatted_time)
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ <b>Викторина юбориш вақти {formatted_time} қилиб белгиланди!</b>", parse_mode="HTML")
                show_quiz_hub(message.chat.id, 0, lang=u_lang)
                return
            else:
                bot.send_message(message.chat.id, "❌ Вақт формати нотўғри! Илтимос, <code>HH:MM</code> кўринишида ёзинг (масалан: <code>10:00</code>):", parse_mode="HTML")
                USER_STATES[user_id] = state
                return

        # 2.9 Медиа лимит огоҳлантириш матнини киритиш
        if action == "wait_limit_msg":
            gid = state.get("group_id")
            cursor.execute("UPDATE groups SET limit_warn_msg = ? WHERE chat_id = ?", (txt, gid))
            conn.commit()
            USER_STATES.pop(user_id, None)
            bot.send_message(message.chat.id, "✅ <b>Медиа лимит огоҳлантириш матни муваффақиятли сақланди!</b>", parse_mode="HTML")
            show_limits_panel(message.chat.id, gid, lang=u_lang)
            return

        # 3. Мажбурий канални киритиш
        if action == "wait_forcesub_channel":
            gid = state.get("group_id")
            chan = clean_channel_username(txt)
            cursor.execute("UPDATE groups SET forcesub_channel = ? WHERE chat_id = ?", (chan, gid))
            conn.commit()
            USER_STATES.pop(user_id, None)
            
            is_adm = check_bot_channel_admin(chan)
            adm_note = (
                f"\n\n✅ <b>Бот ушбу каналда админ эканлиги тасдиқланди!</b>"
                if is_adm else
                f"\n\n⚠️ <b>ДИҚҚАТ:</b> Бот ҳали <code>{chan}</code> каналида админ эмас! Аъзоларни аниқ текшириш учун ботни каналга қўшиб админ ҳуқуқларини беринг."
            )
            bot.send_message(message.chat.id, f"✅ <b>Мажбурий обуна канали сақланди:</b> <code>{chan}</code>{adm_note}", parse_mode="HTML")
            show_forcesub_panel(message.chat.id, gid, lang=u_lang)
            return

        # 3.1. Мажбурий обуна хабари ўчиш вақтини (дақиқа) қўлда киритиш
        if action == "wait_fsub_timer":
            gid = state.get("group_id")
            USER_STATES.pop(user_id, None)
            try:
                val = int(txt.strip())
                if val < 0: val = 0
                cursor.execute("UPDATE groups SET forcesub_timer_min = ? WHERE chat_id = ?", (val, gid))
                conn.commit()
                succ_info = "♾ <b>Огоҳлантириш хабари ўчирилмайдиган қилинди</b> (токи фойдаланувчи каналга аъзо бўлмагунча туради)." if val == 0 else f"⏱ <b>Огоҳлантириш хабари гуруҳда {val} дақиқа турадиган ва кейин ўчириладиган қилинди.</b>"
                bot.send_message(message.chat.id, f"✅ <b>Сақланди!</b>\n\n{succ_info}", parse_mode="HTML")
            except ValueError:
                bot.send_message(message.chat.id, "❌ Фақат рақам киритинг (масалан: 1, 2, 5 ёки 0)!")
            show_forcesub_panel(message.chat.id, gid, lang=u_lang)
            return

        # 4. Қўлда UTC фарқини киритиш
        if action == "wait_custom_tz":
            gid = state.get("group_id")
            try:
                val = int(txt.replace("+", ""))
                if -12 <= val <= 14:
                    city_lbl = f"UTC{'+' if val >= 0 else ''}{val}"
                    cursor.execute("UPDATE groups SET timezone_offset = ?, timezone_city = ? WHERE chat_id = ?", (val, city_lbl, gid))
                    conn.commit()
                    USER_STATES.pop(user_id, None)
                    bot.send_message(message.chat.id, f"✅ <b>Вақт минтақаси {city_lbl} қилиб сақланди!</b>")
                    show_timezone_panel(message.chat.id, gid, lang=u_lang)
                    return
                else:
                    raise ValueError()
            except ValueError:
                bot.send_message(message.chat.id, "❌ Нотўғри соат фарқи! Масалан: <code>+5</code> ёки <code>5</code> деб киритинг.")
                USER_STATES[user_id] = state
                return

        # 5. Гуруҳ ID орқали рухсат бериш (Эгаси учун)
        if action == "wait_group_allow_id":
            try:
                gid = int(txt)
                cursor.execute("INSERT OR IGNORE INTO groups (chat_id, title) VALUES (?, ?)", (gid, "Гуруҳ"))
                cursor.execute("UPDATE groups SET is_authorized = 1 WHERE chat_id = ?", (gid,))
                conn.commit()
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ <b>Гуруҳга муваффақиятли рухсат берилди!</b>\n🆔 ID: <code>{gid}</code>\n\nЭнди ушбу гуруҳга бот қўшилса, у автоматик ишлайди.", parse_mode="HTML")
                show_owner_groups_panel(message.chat.id, lang=u_lang)
                return
            except ValueError:
                bot.send_message(message.chat.id, "❌ Нотўғри ID формати! Илтимос, манфий сон шаклида киритинг (масалан: <code>-1001234567890</code>):", parse_mode="HTML")
                USER_STATES[user_id] = state
                return

        # 6. Канални қўлда юзернейм орқали улаш
        if action == "waiting_channel_username":
            c_input = txt.strip()
            if c_input in ["❌ Бекор қилиш", "Бекор қилиш", "Отмена", "Cancel"]:
                USER_STATES.pop(user_id, None)
                bot.send_message(message.chat.id, "❌ Бекор қилинди.", reply_markup=get_main_reply_keyboard(u_lang, user_id))
                return

            clean_ch = c_input if (c_input.startswith("@") or c_input.startswith("-100")) else f"@{c_input}"
            try:
                chat_info = bot.get_chat(clean_ch)
                c_id = chat_info.id
                c_title = chat_info.title or clean_ch
                c_user = f"@{chat_info.username}" if chat_info.username else clean_ch
                register_channel(c_id, c_title, c_user)
                USER_STATES.pop(user_id, None)
                bot.send_message(
                    message.chat.id,
                    f"✅ <b>Канал муваффақиятли уланди!</b>\n\n"
                    f"📢 <b>Канал:</b> {c_title} ({c_user})\n"
                    f"🆔 <b>ID:</b> <code>{c_id}</code>\n\n"
                    f"<i>Энди барча реклама ва маълумотлар гуруҳлар билан бирга ушбу каналга ҳам юборилади ва тепасига қадалади (закрепить қилинади)!</i>\n\n"
                    f"⚠️ <b>Эслатма:</b> Бот ушбу каналда <b>Администратор</b> бўлиши ва унга хабар юбориш ҳамда қадаш (pin) ҳуқуқи берилган бўлиши шарт.",
                    reply_markup=get_main_reply_keyboard(u_lang, user_id),
                    parse_mode="HTML"
                )
                show_channels_panel(message.chat.id, lang=u_lang)
                return
            except Exception as ce:
                logging.error(f"Add channel error: {ce}")
                if clean_ch.startswith("-100"):
                    try:
                        c_id = int(clean_ch)
                        register_channel(c_id, f"Канал {clean_ch}", clean_ch)
                        USER_STATES.pop(user_id, None)
                        bot.send_message(
                            message.chat.id,
                            f"✅ <b>Канал ID орқали рўйхатга олинди:</b> <code>{c_id}</code>\n\n"
                            f"Бот ушбу каналда админ эканлигини текширинг.",
                            reply_markup=get_main_reply_keyboard(u_lang, user_id),
                            parse_mode="HTML"
                        )
                        show_channels_panel(message.chat.id, lang=u_lang)
                        return
                    except Exception:
                        pass
                bot.send_message(
                    message.chat.id,
                    f"❌ Канал топилмади ёки бот ҳали унга қўшилмаган!\n\n"
                    f"Илтимос, аввал ботни каналингизга <b>Администратор</b> қилиб қўшинг, сўнг канал юзернеймини (масалан: <code>@asalarichilik</code>) юборинг:",
                    reply_markup=get_cancel_reply_keyboard(u_lang),
                    parse_mode="HTML"
                )
                return

    # 3.2. Reply клавиатура тугмалари
    if txt in [
        "🏠 Асосий меню", "Асосий меню", "🏠 Asosiy menyu", "Asosiy menyu",
        "🏠 Главное меню", "Главное меню", "🏠 Main Menu", "Main Menu",
        "Меню", "Menu", "🏠"
    ]:
        welcome_text = get_welcome_text(first_name, u_lang)
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=get_main_reply_keyboard(u_lang, user_id),
            disable_web_page_preview=True
        )
        bot.send_message(
            message.chat.id,
            "🎛 <b>Асосий менюдан керакли бўлимни танланг:</b>" if u_lang not in ["ru", "en"] else ("🎛 <b>Выберите нужный раздел из меню:</b>" if u_lang == "ru" else "🎛 <b>Choose an option from main menu:</b>"),
            reply_markup=get_main_menu_markup(u_lang, user_id)
        )
        return

    if txt in ["Гуруҳ созламалари 🎛", "Guruh sozlamalari 🎛", "Настройки группы 🎛", "Group Settings 🎛"]:
        open_group_selection(message.chat.id, lang=u_lang)
        return

    if txt in ["👑 Гуруҳлар назорати 👥", "👑 Guruhlar nazorati 👥", "👑 Управление группами 👥", "👑 Group Control 👥"]:
        if user_id == OWNER_ID:
            show_owner_groups_panel(message.chat.id, lang=u_lang)
            return

    if txt in ["Тилни ўзгартириш 🌐", "Tilni o'zgartirish 🌐", "Сменить язык 🌐", "Change Language 🌐"]:
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🇺🇿 Ўзбекча (Кирилл)", callback_data="set_lang_uz_kr"),
            InlineKeyboardButton("🇺🇿 O'zbekcha (Lotin)", callback_data="set_lang_uz_lat")
        )
        markup.row(
            InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
        )
        markup.row(InlineKeyboardButton(get_main_menu_btn_label(u_lang), callback_data="back_main"))
        bot.send_message(message.chat.id, "🌐 <b>Тилни танланг / Выберите язык / Select language:</b>", reply_markup=markup)
        return

    if txt in ["⚙️ Созламалар", "Созламалар", "⚙️ Настройки", "Настройки", "⚙️ Settings", "Settings"]:
        show_post_settings_menu(message.chat.id)
        return

    if txt in ["Бот қўлланмаси 📖", "Bot qo'llanmasi 📖", "Инструкция бота 📖", "Bot Manual 📖"]:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(get_main_menu_btn_label(u_lang), callback_data="back_main"))
        bot.send_message(message.chat.id, get_guide_text(u_lang), reply_markup=markup)
        return

    if txt in ["📢 Реклама тарқатиш 📨", "📢 Reklama tarqatish 📨", "📢 Рассылка рекламы 📨", "📢 Broadcast Message 📨"]:
        if user_id == OWNER_ID:
            show_broadcast_menu(message.chat.id, lang=u_lang)
            return

    if txt in ["📰 Янгиликлар (/news)", "📰 Yangiliklar (/news)", "📰 Новости (/news)", "📰 News (/news)"]:
        show_bee_news_hub(message.chat.id, 0, None, lang=u_lang)
        return

    if txt in ["🐝 Викторина & Сўровнома 📊", "🐝 Viktorina & So'rovnoma 📊", "🐝 Викторина & Опрос 📊", "🐝 Quizzes & Polls 📊"]:
        show_quiz_hub(message.chat.id, 0, None, lang=u_lang)
        return

    # 3.2.1 Асалари шифокори (AI Доктор) личкада савол берганда
    if txt in ["🩺 Asalarichilik.Uz🇺🇿 шифокори 🐝", "🩺 Asalarichilik.Uz🇺🇿 shifokori 🐝", "🩺 Врач Asalarichilik.Uz🇺🇿 🐝"]:
        bot.send_message(
            message.chat.id,
            "🩺 <b>Asalarichilik.Uz🇺🇿 ШИФОКОРИ ТАҲЛИЛИ:</b>\n\n"
            "📷 Асалариларингиз, мумкатак ёки уянинг расмини юборинг ёки касаллик белгиларини ёзинг.\n\n"
            "Бот дарҳол касаллик турини (Варроатоз, Аскосфероз, Нозематоз, Чириш ва б.) аниқлаб, тўлиқ даволаш чоралари ва керакли препаратларни айтиб беради!",
            reply_markup=get_main_reply_keyboard(u_lang, user_id),
            parse_mode="HTML"
        )
        return

    # Агар личкада касаллик бўйича матнли савол юборилса:
    bee_pm_keywords = ["касал", "касаллик", "даволаш", "нима бўлган", "нега ўляпти", "дори", "бипин", "амитраз", "варроа", "аскосфероз", "чириш", "нозема", "куя"]
    if any(k in txt.lower() for k in bee_pm_keywords) and message.content_type == 'text' and user_id != OWNER_ID:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            ans = analyze_bee_disease_or_question(txt)
            bot.send_message(message.chat.id, ans, parse_mode="HTML")
            return
        except Exception:
            pass


    if txt in ["🎙 Бот номидан ёзиш 💬", "🎙 Bot nomidan yozish 💬", "🎙 Писать от имени бота 💬", "🎙 Speak as Bot 💬"]:
        if user_id == OWNER_ID:
            cmd_say(message)
            return

    if user_id == OWNER_ID and (txt.lower().startswith("gapir ") or txt.lower().startswith("say ")):
        cmd_say(message)
        return


    # Бошқа ихтиёрий матн юборилса:
    bot.send_message(
        message.chat.id,
        get_welcome_text(first_name, u_lang),
        reply_markup=get_main_reply_keyboard(u_lang, user_id),
        disable_web_page_preview=True
    )
    bot.send_message(
        message.chat.id,
        "🎛 <b>Асосий менюдан керакли бўлимни танланг:</b>" if u_lang not in ["ru", "en"] else ("🎛 <b>Выберите нужный раздел из меню:</b>" if u_lang == "ru" else "🎛 <b>Choose an option from main menu:</b>"),
        reply_markup=get_main_menu_markup(u_lang, user_id)
    )

# 6. БОТНИ ГУРУҲ ЁКИ КАНАЛГА ҚЎШИШ ВА ЭГАСИНИНГ РУХСАТИНИ ТАЛАБ ҚИЛИШ (КРИТИК ҲИМОЯ)
@bot.my_chat_member_handler()
def handle_my_chat_member(update):
    try:
        chat = update.chat
        chat_id = chat.id
        title = chat.title or "Гуруҳ"
        new_status = update.new_chat_member.status
        user = update.from_user
        user_id = user.id if user else 0
        user_name = user.full_name if user else "Номаълум"
        user_username = f"@{user.username}" if (user and user.username) else "Юзернейм йўқ"

        # Канал бўлса
        if chat.type == "channel":
            if new_status in ['administrator']:
                register_channel(chat_id, title, chat.username)
                bot.send_message(
                    OWNER_ID,
                    f"📢 <b>ДИҚҚАТ! БОТ КАНАЛГА АДМИН БЎЛДИ!</b>\n\n"
                    f"📢 <b>Канал:</b> {title} (@{chat.username or 'юзернейм йўқ'})\n"
                    f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
                    f"👤 <b>Қўшган:</b> {user_name} ({user_username})\n"
                    f"✅ Энди ушбу каналга реклама ва хабарлар тарқатиш мумкин."
                )
            return

        # Гуруҳ бўлса
        if new_status in ['member', 'administrator']:
            now_time_str = get_now_formatted()

            notify_text = (
                f"🔔 <b>ДИҚҚАТ! БОТ ЯНГИ ГУРУҲГА ҚЎШИЛДИ!</b>\n\n"
                f"👥 <b>Гуруҳ номи:</b> {title}\n"
                f"🆔 <b>Гуруҳ ID:</b> <code>{chat_id}</code>\n"
                f"👤 <b>Қўшган шахс:</b> {user_name} ({user_username})\n"
                f"🆔 <b>Шахс ID:</b> <code>{user_id}</code>\n"
                f"📅 <b>Вақти:</b> {now_time_str}\n\n"
            )

            if user_id == OWNER_ID:
                register_group(chat_id, title, added_by=OWNER_ID)
                cursor.execute("UPDATE groups SET is_authorized = 1 WHERE chat_id = ?", (chat_id,))
                conn.commit()

                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🎛 Созламалар панели", callback_data=f"panel_settings_{chat_id}"))
                bot.send_message(
                    OWNER_ID,
                    notify_text + "✅ <i>Сиз (Бот эгаси) қўшганингиз сабабли гуруҳ автоматик фаоллаштирилди.</i>",
                    reply_markup=markup
                )
            else:
                register_group(chat_id, title, added_by=user_id)
                cursor.execute("UPDATE groups SET is_authorized = 0 WHERE chat_id = ?", (chat_id,))
                conn.commit()

                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("✅ Рухсат бериш", callback_data=f"auth_allow_{chat_id}"),
                    InlineKeyboardButton("❌ Рад этиш ва чиқиш", callback_data=f"auth_deny_{chat_id}")
                )
                bot.send_message(
                    OWNER_ID,
                    notify_text + "⚠️ <b>Ушбу гуруҳда бот ишлашига рухсат берасизми?</b>",
                    reply_markup=markup
                )

                try:
                    bot.send_message(
                        chat_id,
                        f"⚠️ <b>Диққат!</b>\n\n"
                        f"Ушбу ботдан гуруҳда фойдаланиш учун бот эгаси ({OWNER_USERNAME})нинг махсус рухсати талаб қилинади.\n\n"
                        f"📩 Бот эгасига рухсат сўрови юборилди. Тасдиқланмагунча бот ҳимоя функциялари фаоллашмайди.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    except Exception as e:
        logging.error(f"my_chat_member error: {e}")

# 7. Гуруҳда админлик буйруқлари (/pin, /unpin, /del, /mute, /ban, /warn) ва буйруқларни тозалаш
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text and m.text.startswith('/'))
def group_slash_cleaner(message):
    chat_id = message.chat.id
    title = message.chat.title or "Гуруҳ"
    register_group(chat_id, title, added_by=OWNER_ID)
    user_id = message.from_user.id
    text = (message.text or "").strip()
    cmd = text.split()[0].lower().split('@')[0]
    is_user_admin = (user_id == OWNER_ID or is_admin(chat_id, user_id))

    # 1. /del буйруғи (Ҳар қандай хабарни ўчириш)
    if cmd in ['/del', '/delete', '/ochir'] and is_user_admin:
        if message.reply_to_message:
            delete_msg_safe(chat_id, message.reply_to_message.message_id)
        delete_msg_safe(chat_id, message.message_id)
        return

    # 2. /pin буйруғи (Хабарни закрепить / қадаб қўйиш)
    if cmd in ['/pin', '/qada', '/закрепить'] and is_user_admin:
        delete_msg_safe(chat_id, message.message_id)
        try:
            if message.reply_to_message:
                bot.pin_chat_message(chat_id, message.reply_to_message.message_id)
                n = bot.send_message(chat_id, "📌 <b>Хабар муваффақиятли қадаб қўйилди (Закреплен)!</b>", parse_mode="HTML")
                threading.Timer(5, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            else:
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    sent = bot.send_message(chat_id, f"📌 <b>МУҲИМ ЭЪЛОН:</b>\n\n{parts[1]}", parse_mode="HTML")
                    bot.pin_chat_message(chat_id, sent.message_id)
        except Exception as e:
            logging.error(f"Pin error: {e}")
        return

    # 3. /unpin буйруғи (Қадалган хабарни ечиш)
    if cmd in ['/unpin', '/yech', '/открепить'] and is_user_admin:
        delete_msg_safe(chat_id, message.message_id)
        try:
            bot.unpin_chat_message(chat_id)
            n = bot.send_message(chat_id, "📌 <b>Қадалган хабар ечилди (Откреплен).</b>", parse_mode="HTML")
            threading.Timer(5, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        except Exception as e:
            logging.error(f"Unpin error: {e}")
        return

    # 4. /mute буйруғи (Ёзишни чеклаш)
    if cmd in ['/mute', '/mut', '/жим'] and is_user_admin:
        delete_msg_safe(chat_id, message.message_id)
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            duration_sec = 3600 # 1 соат дефолт
            parts = text.split()
            if len(parts) > 1:
                t_str = parts[1].lower()
                if t_str.endswith('m'):
                    duration_sec = int(t_str[:-1]) * 60
                elif t_str.endswith('h'):
                    duration_sec = int(t_str[:-1]) * 3600
                elif t_str.endswith('d'):
                    duration_sec = int(t_str[:-1]) * 86400
            try:
                until = int(time.time()) + duration_sec
                bot.restrict_chat_member(chat_id, target_user.id, until_date=until, can_send_messages=False)
                u_tag = f"@{target_user.username}" if target_user.username else target_user.first_name
                n = bot.send_message(chat_id, f"🤐 <b>{u_tag}</b> қоидабузарлик сабабли вақтинча <b>МУТ</b> қилинди!", parse_mode="HTML")
                threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            except Exception as e:
                logging.error(f"Mute error: {e}")
        return

    # 5. /unmute буйруғи (Мутдан чиқариш)
    if cmd in ['/unmute', '/unmut', '/och'] and is_user_admin:
        delete_msg_safe(chat_id, message.message_id)
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            lift_user_mute(chat_id, target_user.id)
            cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (chat_id, target_user.id))
            conn.commit()
            u_tag = f"@{target_user.username}" if target_user.username else target_user.first_name
            n = bot.send_message(chat_id, f"🔊 <b>{u_tag}</b> мутдан чиқарилди ва ёзишга тўлиқ рухсат берилди! ✅", parse_mode="HTML")
            threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # 6. /ban ёки /kick буйруғи (Гуруҳдан чиқариб юбориш)
    if cmd in ['/ban', '/kick', '/hayda'] and is_user_admin:
        delete_msg_safe(chat_id, message.message_id)
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            try:
                bot.ban_chat_member(chat_id, target_user.id)
                u_tag = f"@{target_user.username}" if target_user.username else target_user.first_name
                n = bot.send_message(chat_id, f"🚫 <b>{u_tag}</b> гуруҳдан чиқариб юборилди ва блокланди!", parse_mode="HTML")
                threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            except Exception as e:
                logging.error(f"Ban error: {e}")
        return

    # Бошқа ихтиёрий буйруқлар бўлса, хавфсизлик учун ўчирилади
    delete_msg_safe(chat_id, message.message_id)

    if message.from_user.id == OWNER_ID:
        try:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🎛 Созламалар панели (Личкада)", callback_data=f"panel_settings_{chat_id}"))
            bot.send_message(
                OWNER_ID,
                f"⚙️ <b>{title}</b> гуруҳи созламаларини очиш учун тугмани босинг:",
                reply_markup=markup
            )
        except Exception:
            pass

# 8. Кириш сўровларини бошқариш (Join Request)
@bot.chat_join_request_handler(func=lambda req: True)
def handle_chat_join_request(req):
    try:
        chat_id = req.chat.id
        user = req.from_user
        user_id = user.id
        g = get_group(chat_id)
        if not g:
            return

        f_en = g.get("forcesub_enabled", 0) == 1
        chan = g.get("forcesub_channel", "@Asalarichilik_Uz")
        appr_en = g.get("approval_enabled", 0) == 1

        is_sub = True
        missing = []
        if f_en:
            is_sub, missing = check_user_channels_subscription(chan, user_id)

        if not is_sub:
            sub_markup = InlineKeyboardMarkup()
            for m_ch in (missing if missing else [chan]):
                c_clean = m_ch.replace("@", "")
                sub_markup.row(InlineKeyboardButton(f"📢 {m_ch} каналига аъзо бўлиш", url=f"https://t.me/{c_clean}"))
            sub_markup.row(InlineKeyboardButton("✅ Аъзо бўлдим (Текшириш ва кириш)", callback_data=f"req_check_sub_{chat_id}_{user_id}"))

            try:
                grp_title = html.escape(str(g.get('title', 'Гуруҳ')))
                u_name = html.escape(str(user.first_name))
                bot.send_message(
                    user_id,
                    f"Ассалому алайкум, <b>{u_name}</b>! ✋\n\n"
                    f"<b>{grp_title}</b> гуруҳига қўшилиш учун аввал расмий каналимизга аъзо бўлишингиз шарт:\n"
                    f"📢 <b>{chan}</b>\n\n"
                    f"Каналга аъзо бўлгач, пастдаги «✅ Аъзо бўлдим (Текшириш ва кириш)» тугмасини босинг!",
                    reply_markup=sub_markup,
                    parse_mode="HTML"
                )
            except Exception as pe:
                logging.warning(f"Could not PM user for join request forcesub: {pe}")
            return

        # Каналга аъзо бўлса:
        if appr_en:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ Қабул қилиш", callback_data=f"approve_req_{chat_id}_{user_id}"),
                InlineKeyboardButton("❌ Рад этиш", callback_data=f"reject_req_{chat_id}_{user_id}")
            )
            bot.send_message(
                chat_id,
                f"🔐 <b>ЯНГИ АЪЗО ТАСДИҒИ (Админ розилиги)</b>\n\n"
                f"👤 <b>{html.escape(str(user.first_name))}</b> (@{user.username or 'юзернейм йўқ'}) каналга аъзо бўлди ва гуруҳга қўшилишни сўрамоқда.\n\n"
                f"Қабул қиласизми?",
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            try:
                bot.approve_chat_join_request(chat_id, user_id)
                cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
                conn.commit()
                try:
                    bot.send_message(
                        user_id,
                        f"✅ <b>{html.escape(str(g.get('title', 'Гуруҳ')))}</b> гуруҳига хуш келибсиз! Сўровингиз муваффақиятли қабул қилинди! 🎉",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            except Exception as ae:
                logging.error(f"Auto-approve join request error: {ae}")
    except Exception as e:
        logging.error(f"Join request error: {e}")

# ==================== CALLBACK QUERY ҲОДИСАЛАРИ ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    u_lang = get_user_lang(user_id)

    # Ҳамма учун очиқ бўлган умумий callback'лар:
    public_cb_prefixes = ("cb_react_", "react_", "check_sub_", "set_lang_", "back_main", "menu_language", "menu_help", "menu_guide", "menu_doctor", "menu_add_group", "refresh_comments_", "req_check_sub_", "unmute_me_", "open_bee_news", "open_bee_quiz", "fr_", "fr:", "rx_")
    if not any(data.startswith(pfx) for pfx in public_cb_prefixes):
        target_gid = None
        m_gid = re.search(r'(-100\d{6,}| -\d{7,} )', data)
        if m_gid:
            try:
                target_gid = int(m_gid.group(0))
            except Exception:
                pass
        if target_gid:
            if not (user_id == OWNER_ID or is_user_allowed_to_manage_group(target_gid, user_id)):
                bot.answer_callback_query(call.id, "⚠️ Бу бўлим фақат гуруҳ админлари ва бот эгаси учун!", show_alert=True)
                return
        elif not is_user_admin_anywhere(user_id):
            bot.answer_callback_query(call.id, "⚠️ Бу бўлим фақат гуруҳ админлари ва бот эгаси учун!", show_alert=True)
            return

    # 1. Асаларичилик Янгиликлари Маркази (News Hub)
    if data in ["bc_bee_news_hub", "open_bee_news"]:
        show_bee_news_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("view_bee_news_"):
        n_idx = int(data.replace("view_bee_news_", ""))
        show_bee_news_hub(chat_id, n_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("pub_bee_news_chan_"):
        n_idx = int(data.replace("pub_bee_news_chan_", ""))
        sent_c = publish_bee_news(n_idx, user_id, target_scope="channels", pin=True)
        bot.answer_callback_query(call.id, f"✅ Янгилик {sent_c} та Каналга юборилди ва қадалди! 📌", show_alert=True)
        show_bee_news_hub(chat_id, n_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("pub_bee_news_grp_"):
        n_idx = int(data.replace("pub_bee_news_grp_", ""))
        sent_c = publish_bee_news(n_idx, user_id, target_scope="groups", pin=True)
        bot.answer_callback_query(call.id, f"✅ Янгилик {sent_c} та Гуруҳга юборилди ва қадалди! 📌", show_alert=True)
        show_bee_news_hub(chat_id, n_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("pub_bee_news_"):
        n_idx = int(data.replace("pub_bee_news_", ""))
        sent_c = publish_bee_news(n_idx, user_id, target_scope="both", pin=True)
        bot.answer_callback_query(call.id, f"✅ Янгилик {sent_c} та Канал ва Гуруҳларга юборилди ва қадалди! 📌", show_alert=True)
        show_bee_news_hub(chat_id, n_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("draft_to_ad_news_"):
        n_idx = int(data.replace("draft_to_ad_news_", ""))
        item = BEE_GLOBAL_NEWS[n_idx] if 0 <= n_idx < len(BEE_GLOBAL_NEWS) else BEE_GLOBAL_NEWS[0]
        cfg_script = get_system_setting("news_script", "uz_kr")
        post_txt = format_bee_news_post(item, cfg_script)
        chan = get_official_channel()
        grp = get_official_group()
        yt = get_official_youtube()
        c_clean = chan.replace("@", "")
        g_clean = grp.replace("@", "").replace("https://t.me/", "")
        g_url = grp if grp.startswith("http") else f"https://t.me/{g_clean}"
        USER_STATES[user_id] = {
            "action": "editing_post",
            "post": {
                "target_id": "all",
                "target_name": "Барча гуруҳ ва каналлар",
                "text": post_txt,
                "media_type": "text",
                "file_id": None,
                "reactions": ["👍", "👎", "❤️", "👏"],
                "url_buttons": [
                    [{"text": "📢 Расмий Канал", "url": f"https://t.me/{c_clean}"},
                     {"text": "👥 Расмий Гуруҳ", "url": g_url}],
                    [{"text": "📺 YouTube Каналимиз", "url": yt}]
                ],
                "has_comments": False,
                "comments_url": "",
                "native_comments": False,
                "is_silent": False,
                "delete_timer_hours": 0,
                "show_more": True,
                "pinned": True
            }
        }
        bot.answer_callback_query(call.id, "✅ Янгилик Реклама менюсига ўтказилди! Энди уни эркин таҳрирлашингиз ёки тўғридан-тўғри тарқатишингиз мумкин.", show_alert=True)
        render_post_editor_screen(chat_id, user_id, USER_STATES[user_id]["post"], lang=u_lang)
        return
    elif data == "search_online_bee_news":
        bot.answer_callback_query(call.id, "🌐 Интернет тармоғидан янги асаларичилик тадқиқоти топилди ва таржима қилинди!", show_alert=True)
        show_bee_news_hub(chat_id, 1, call.message.message_id, lang=u_lang)
        return

    # 2. Асаларичилик Викториналари ва Сўровномалари (Quiz Hub)
    elif data in ["bc_bee_quiz_hub", "open_bee_quiz"]:
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("view_bee_quiz_"):
        q_idx = int(data.replace("view_bee_quiz_", ""))
        show_quiz_hub(chat_id, q_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("pub_bee_quiz_chan_"):
        q_idx = int(data.replace("pub_bee_quiz_chan_", ""))
        sent_c = publish_quiz_poll(q_idx, user_id, target_scope="channels")
        bot.answer_callback_query(call.id, f"✅ Викторина {sent_c} та Каналга юборилди ва қадалди! 📌", show_alert=True)
        show_quiz_hub(chat_id, q_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("pub_bee_quiz_grp_"):
        q_idx = int(data.replace("pub_bee_quiz_grp_", ""))
        sent_c = publish_quiz_poll(q_idx, user_id, target_scope="groups")
        bot.answer_callback_query(call.id, f"✅ Викторина {sent_c} та Гуруҳга юборилди ва қадалди! 📌", show_alert=True)
        show_quiz_hub(chat_id, q_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("pub_bee_quiz_"):
        q_idx = int(data.replace("pub_bee_quiz_", ""))
        sent_c = publish_quiz_poll(q_idx, user_id, target_scope="both")
        bot.answer_callback_query(call.id, f"✅ Викторина {sent_c} та жойга (канал ва гуруҳлар) муваффақиятли юборилди ва қадалди! 📌", show_alert=True)
        show_quiz_hub(chat_id, q_idx, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("draft_to_ad_quiz_"):
        q_idx = int(data.replace("draft_to_ad_quiz_", ""))
        cfg = get_global_quiz_config()
        all_quizzes = get_all_bee_quizzes(cfg.get("category_filter", "all"))
        item = all_quizzes[q_idx] if 0 <= q_idx < len(all_quizzes) else all_quizzes[0]
        q_script = cfg.get("script") or get_system_setting("quiz_script", "uz_kr")
        if q_script == "uz_lat":
            q_text = item.get("question_lat") or item.get("question_kr")
            opts = item.get("options_lat") or item.get("options_kr")
            expl = item.get("explanation_lat") or item.get("explanation_kr")
        else:
            q_text = item.get("question_kr")
            opts = item.get("options_kr")
            expl = item.get("explanation_kr")
        corr_id = item.get("correct_id", 0)
        chan = get_official_channel()
        grp = get_official_group()
        yt = get_official_youtube()
        c_clean = chan.replace("@", "")
        g_clean = grp.replace("@", "").replace("https://t.me/", "")
        g_url = grp if grp.startswith("http") else f"https://t.me/{g_clean}"
        opts_lines = "\n".join([f"🔘 {idx+1}. {opt}" for idx, opt in enumerate(opts)])
        quiz_ad_txt = (
            f"🐝 <b>АСАЛАРИЧИЛИК БЎЙИЧА КУНЛИК СЎРОВНОМА & ВИКТОРИНА 📊</b>\n\n"
            f"❓ <b>Савол:</b> {q_text}\n\n"
            f"{opts_lines}\n\n"
            f"💡 <b>Тўғри жавоб:</b> <i>{opts[corr_id]}</i>\n"
            f"📝 <b>Изоҳ:</b> <i>{expl}</i>\n\n"
            f"#Асаларичилик #Викторина #Тест #AsalarichilikUz"
        )
        USER_STATES[user_id] = {
            "action": "editing_post",
            "post": {
                "target_id": "all",
                "target_name": "Барча гуруҳ ва каналлар",
                "text": quiz_ad_txt,
                "media_type": "text",
                "file_id": None,
                "reactions": ["👍", "❤️", "👏", "🔥"],
                "url_buttons": [
                    [{"text": "📢 Расмий Канал", "url": f"https://t.me/{c_clean}"},
                     {"text": "👥 Расмий Гуруҳ", "url": g_url}],
                    [{"text": "📺 YouTube Каналимиз", "url": yt}]
                ],
                "has_comments": False,
                "comments_url": "",
                "native_comments": False,
                "is_silent": False,
                "delete_timer_hours": 0,
                "show_more": True,
                "pinned": True
            }
        }
        bot.answer_callback_query(call.id, "✅ Викторина Реклама менюсига ўтказилди! Энди уни реклама сифатида барчага тарқатишингиз мумкин.", show_alert=True)
        render_post_editor_screen(chat_id, user_id, USER_STATES[user_id]["post"], lang=u_lang)
        return
    elif data == "open_dest_settings":
        show_destinations_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    elif data == "dest_cycle_news":
        cur_sc = get_system_setting("news_target_scope", "both")
        scopes = ["both", "channels", "groups"]
        next_sc = scopes[(scopes.index(cur_sc) + 1) % len(scopes)] if cur_sc in scopes else "both"
        set_system_setting("news_target_scope", next_sc)
        lbl = {"both": "Канал ва Гуруҳларга", "channels": "Фақат Каналларга", "groups": "Фақат Гуруҳларга"}.get(next_sc)
        bot.answer_callback_query(call.id, f"📰 Янгилик манзили: {lbl}")
        show_destinations_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    elif data == "dest_cycle_quiz":
        cur_sc = get_system_setting("quiz_target_scope", "both")
        scopes = ["both", "channels", "groups"]
        next_sc = scopes[(scopes.index(cur_sc) + 1) % len(scopes)] if cur_sc in scopes else "both"
        set_system_setting("quiz_target_scope", next_sc)
        update_global_quiz_config(target_scope=next_sc)
        lbl = {"both": "Канал ва Гуруҳларга", "channels": "Фақат Каналларга", "groups": "Фақат Гуруҳларга"}.get(next_sc)
        bot.answer_callback_query(call.id, f"🐝 Викторина манзили: {lbl}")
        show_destinations_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    elif data == "dest_cycle_broadcast":
        cur_sc = get_system_setting("broadcast_default_scope", "both")
        scopes = ["both", "channels", "groups"]
        next_sc = scopes[(scopes.index(cur_sc) + 1) % len(scopes)] if cur_sc in scopes else "both"
        set_system_setting("broadcast_default_scope", next_sc)
        lbl = {"both": "Канал ва Гуруҳларга", "channels": "Фақат Каналларга", "groups": "Фақат Гуруҳларга"}.get(next_sc)
        bot.answer_callback_query(call.id, f"📢 Реклама манзили: {lbl}")
        show_destinations_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    elif data == "dest_edit_channel":
        USER_STATES[user_id] = {"action": "wait_dest_channel"}
        curr_chan = get_official_channel()
        bot.send_message(
            chat_id,
            f"✏️ <b>Расмий Телеграм каналини ўзгартириш:</b>\n\n"
            f"Жорий канал: <code>{curr_chan}</code>\n\n"
            f"Янги канал юзернейми ёки ҳаволасини юборинг (Масалан: <code>@uz_asalarichilik</code> ёки <code>https://t.me/Uz_Asalarichilik</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "dest_edit_group":
        USER_STATES[user_id] = {"action": "wait_dest_group"}
        curr_grp = get_official_group()
        bot.send_message(
            chat_id,
            f"✏️ <b>Расмий Телеграм гуруҳини ўзгартириш:</b>\n\n"
            f"Жорий гуруҳ: <code>{curr_grp}</code>\n\n"
            f"Янги гуруҳ юзернейми ёки ҳаволасини юборинг (Масалан: <code>@asalarichilik_uzbekistan</code> ёки <code>https://t.me/ASALARICHILIK_UZBEKISTAN</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "dest_edit_youtube":
        USER_STATES[user_id] = {"action": "wait_dest_youtube"}
        curr_yt = get_official_youtube()
        bot.send_message(
            chat_id,
            f"✏️ <b>YouTube канали ҳаволасини ўзгартириш:</b>\n\n"
            f"Жорий ҳавола: <code>{curr_yt}</code>\n\n"
            f"Янги YouTube ҳаволасини юборинг (Масалан: <code>https://youtube.com/@asalarichilikuztv?feature=shared</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "dest_check_bot_admin":
        chan = get_official_channel()
        grp = get_official_group()
        yt = get_official_youtube()
        status_lines = ["🤖 <b>БОТНИНГ АДМИНЛИК ҲОЛАТИ ВА ҲУҚУҚЛАРИ:</b>\n"]
        try:
            me = bot.get_me()
            status_lines.append(f"🤖 <b>Бот:</b> @{me.username} (ID: <code>{me.id}</code>)")
        except Exception:
            pass
        # Канални текшириш
        try:
            c_member = bot.get_chat_member(chan, bot.get_me().id)
            if c_member.status in ['creator', 'administrator']:
                can_pin = getattr(c_member, 'can_pin_messages', True)
                can_post = getattr(c_member, 'can_post_messages', True)
                status_lines.append(f"📢 <b>Канал ({chan}):</b> ✅ АДМИНИСТРАТОР\n• Хабар юбориш: {'✅ Ҳа' if can_post else '⚠️ Чекланган'}\n• Қадаш (Pin): {'✅ Ҳа' if can_pin else '⚠️ Чекланган'}")
            else:
                status_lines.append(f"📢 <b>Канал ({chan}):</b> ❌ Админ эмас ({c_member.status})")
        except Exception as ce:
            status_lines.append(f"📢 <b>Канал ({chan}):</b> ⚠️ Статус текшириш: {ce}")
        # Гуруҳни текшириш
        try:
            g_target = grp if str(grp).startswith("-") or str(grp).startswith("@") else f"@{grp}"
            g_member = bot.get_chat_member(g_target, bot.get_me().id)
            if g_member.status in ['creator', 'administrator']:
                status_lines.append(f"👥 <b>Гуруҳ ({grp}):</b> ✅ АДМИНИСТРАТОР")
            else:
                status_lines.append(f"👥 <b>Гуруҳ ({grp}):</b> ℹ️ Оддий аъзо ({g_member.status})")
        except Exception as ge:
            status_lines.append(f"👥 <b>Гуруҳ ({grp}):</b> ℹ️ Ҳолат: {ge}")
            
        cursor.execute("SELECT COUNT(*) as c FROM channels")
        ch_c = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) as c FROM groups WHERE is_authorized = 1")
        gr_c = cursor.fetchone()["c"]
        status_lines.append(f"\n📊 <b>Базадаги фаол тармоқлар:</b> <b>{ch_c}</b> та канал, <b>{gr_c}</b> та гуруҳ.")
        
        adm_markup = InlineKeyboardMarkup()
        adm_markup.row(InlineKeyboardButton("« Манзиллар созламасига қайтиш", callback_data="open_dest_settings"))
        safe_edit_or_send(chat_id, call.message.message_id, "\n".join(status_lines), adm_markup)
        bot.answer_callback_query(call.id, "✅ Админлик ҳуқуқлари текширилди!")
        return
    elif data == "cycle_quiz_cat_filter":
        cfg = get_global_quiz_config()
        cur_cat = cfg.get("category_filter", "all")
        next_cat = "junior" if cur_cat == "all" else ("specialist" if cur_cat == "junior" else "all")
        update_global_quiz_config(category_filter=next_cat)
        cat_names = {"all": "Барчаси", "junior": "Ёш асаларичилар 🟢", "specialist": "Спец асаларичилар 🔴"}
        bot.answer_callback_query(call.id, f"🎯 Тоифа: {cat_names.get(next_cat)}")
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "toggle_quiz_enabled":
        cfg = get_global_quiz_config()
        new_en = 0 if cfg.get("enabled", 1) == 1 else 1
        update_global_quiz_config(enabled=new_en)
        st_txt = "🟢 Авто-юбориш ёқилди" if new_en == 1 else "⚪️ Авто-юбориш ўчирилди"
        bot.answer_callback_query(call.id, st_txt)
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "cycle_quiz_time":
        cfg = get_global_quiz_config()
        times_list = ["08:00", "09:00", "10:00", "11:00", "12:00", "14:00", "16:00", "18:00", "20:00"]
        cur_t = cfg.get("send_time", "10:00")
        try:
            curr_idx = times_list.index(cur_t)
            next_t = times_list[(curr_idx + 1) % len(times_list)]
        except Exception:
            next_t = "10:00"
        update_global_quiz_config(send_time=next_t)
        bot.answer_callback_query(call.id, f"⏰ Соат: {next_t}")
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "input_quiz_time":
        USER_STATES[user_id] = {"action": "quiz_input_time"}
        bot.send_message(
            chat_id,
            "⏰ <b>Викторинани ҳар куни қайси соатда юбориш керак?</b>\n\n"
            "Илтимос, вақтни <code>HH:MM</code> кўринишида ёзиб юборинг (Масалан: <code>10:00</code>, <code>15:30</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "cycle_quiz_autodel":
        cfg = get_global_quiz_config()
        d_hours_list = [0, 6, 12, 24, 48]
        cur_dh = cfg.get("delete_hours", 0)
        try:
            curr_idx = d_hours_list.index(cur_dh)
            next_dh = d_hours_list[(curr_idx + 1) % len(d_hours_list)]
        except Exception:
            next_dh = 0
        update_global_quiz_config(delete_hours=next_dh)
        dh_label = "♾ Ўчирилмайди (доимий)" if next_dh == 0 else f"⏱ {next_dh} соат"
        bot.answer_callback_query(call.id, f"Авто-ўчириш: {dh_label}")
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "toggle_quiz_pin":
        cfg = get_global_quiz_config()
        new_pin = 0 if cfg.get("auto_pin", 1) == 1 else 1
        update_global_quiz_config(auto_pin=new_pin)
        pin_lbl = "🟢 Қадаш (Закрепить) ёқилди" if new_pin == 1 else "⚪️ Қадаш ўчирилди"
        bot.answer_callback_query(call.id, pin_lbl)
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "cycle_quiz_scope":
        cfg = get_global_quiz_config()
        scopes = ["both", "channels", "groups"]
        cur_sc = cfg.get("target_scope", "both")
        next_sc = scopes[(scopes.index(cur_sc) + 1) % len(scopes)] if cur_sc in scopes else "both"
        update_global_quiz_config(target_scope=next_sc)
        sc_lbl = {"both": "Канал ва Гуруҳлар", "channels": "Фақат Каналлар", "groups": "Фақат Гуруҳлар"}.get(next_sc)
        bot.answer_callback_query(call.id, f"📢 Қамров: {sc_lbl}")
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "toggle_quiz_script":
        cfg = get_global_quiz_config()
        cur_s = cfg.get("script") or get_system_setting("quiz_script", "uz_kr")
        new_s = "uz_lat" if cur_s == "uz_kr" else "uz_kr"
        update_global_quiz_config(script=new_s)
        set_system_setting("quiz_script", new_s)
        lbl = "🟢 Кириллча (Ўзб)" if new_s == "uz_kr" else "🔵 Lotincha (O'zb)"
        bot.answer_callback_query(call.id, f"🔤 Викторина ёзуви: {lbl}")
        show_quiz_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "toggle_news_script":
        cur_s = get_system_setting("news_script", "uz_kr")
        new_s = "uz_lat" if cur_s == "uz_kr" else "uz_kr"
        set_system_setting("news_script", new_s)
        lbl = "🟢 Кириллча (Ўзб)" if new_s == "uz_kr" else "🔵 Lotincha (O'zb)"
        bot.answer_callback_query(call.id, f"🔤 Янгилик ёзуви: {lbl}")
        show_bee_news_hub(chat_id, 0, call.message.message_id, lang=u_lang)
        return
    elif data == "rand_bee_news":
        import random
        rand_idx = random.randint(0, len(BEE_GLOBAL_NEWS) - 1)
        show_bee_news_hub(chat_id, rand_idx, call.message.message_id, lang=u_lang)
        return
    elif data == "admin_db_menu":
        if user_id != OWNER_ID and not is_user_admin_anywhere(user_id):
            bot.answer_callback_query(call.id, "⛔️ Фақат бот маъмурлари учун!", show_alert=True)
            return
        show_database_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    elif data == "db_download_file":
        if user_id != OWNER_ID and not is_user_admin_anywhere(user_id):
            bot.answer_callback_query(call.id, "⛔️ Фақат бот маъмурлари учун!", show_alert=True)
            return
        bot.answer_callback_query(call.id, "📦 Маълумотлар базаси файли юборилмоқда...")
        try:
            with open("asalarichilik.db", "rb") as db_f:
                bot.send_document(
                    chat_id,
                    db_f,
                    caption="🗄 <b>Asalarichilik.Uz ботининг тўлиқ SQLite маълумотлар базаси (.db)</b>\n\nБарча гуруҳлар, каналлар, созламалар ва статистика сақланган.",
                    parse_mode="HTML"
                )
        except Exception as de:
            bot.send_message(chat_id, f"❌ База файлини юклашда хатолик: {de}")
        return
    elif data == "db_edit_channel":
        if user_id != OWNER_ID and not is_user_admin_anywhere(user_id):
            return
        USER_STATES[user_id] = {"action": "wait_db_channel"}
        curr_chan = get_official_channel()
        bot.send_message(
            chat_id,
            f"✏️ <b>Расмий Телеграм каналини ўзгартириш:</b>\n\n"
            f"Жорий канал: <code>{curr_chan}</code>\n\n"
            f"Янги канал юзернейми ёки ҳаволасини юборинг (Масалан: <code>@uz_asalarichilik</code> ёки <code>https://t.me/Uz_Asalarichilik</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "db_edit_group":
        if user_id != OWNER_ID and not is_user_admin_anywhere(user_id):
            return
        USER_STATES[user_id] = {"action": "wait_db_group"}
        curr_grp = get_official_group()
        bot.send_message(
            chat_id,
            f"✏️ <b>Расмий Телеграм гуруҳини ўзгартириш:</b>\n\n"
            f"Жорий гуруҳ: <code>{curr_grp}</code>\n\n"
            f"Янги гуруҳ юзернейми ёки ҳаволасини юборинг (Масалан: <code>@asalarichilik_uzbekistan</code> ёки <code>https://t.me/ASALARICHILIK_UZBEKISTAN</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "db_edit_youtube":
        if user_id != OWNER_ID and not is_user_admin_anywhere(user_id):
            return
        USER_STATES[user_id] = {"action": "wait_db_youtube"}
        curr_yt = get_official_youtube()
        bot.send_message(
            chat_id,
            f"✏️ <b>YouTube канали ҳаволасини ўзгартириш:</b>\n\n"
            f"Жорий ҳавола: <code>{curr_yt}</code>\n\n"
            f"Янги YouTube канали ҳаволасини юборинг (Масалан: <code>https://youtube.com/@asalarichilikuztv?feature=shared</code>):",
            parse_mode="HTML"
        )
        return
    elif data == "db_toggle_news_script":
        cur_s = get_system_setting("news_script", "uz_kr")
        new_s = "uz_lat" if cur_s == "uz_kr" else "uz_kr"
        set_system_setting("news_script", new_s)
        lbl = "🟢 Кириллча (Ўзб)" if new_s == "uz_kr" else "🔵 Lotincha (O'zb)"
        bot.answer_callback_query(call.id, f"Янгилик ёзуви: {lbl}")
        show_database_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    elif data == "db_toggle_quiz_script":
        cur_s = get_system_setting("quiz_script", "uz_kr")
        new_s = "uz_lat" if cur_s == "uz_kr" else "uz_kr"
        set_system_setting("quiz_script", new_s)
        update_global_quiz_config(script=new_s)
        lbl = "🟢 Кириллча (Ўзб)" if new_s == "uz_kr" else "🔵 Lotincha (O'zb)"
        bot.answer_callback_query(call.id, f"Викторина ёзуви: {lbl}")
        show_database_settings_menu(chat_id, call.message.message_id, lang=u_lang)
        return
    
    # 0.1 ФИД ВА ПОСТЛАРГА РЕАКЦИЯЛАР (ЛАЙК СМАЙЛЛАРИ)
    elif data.startswith("fr_") or data.startswith("fr:"):
        try:
            if data.startswith("fr:"):
                parts = data.split(":")
                ctype = parts[1]
                cid_str = parts[2]
                idx = int(parts[3])
            else:
                r_parts = data.rsplit("_", 1)
                idx = int(r_parts[1]) if len(r_parts) > 1 and r_parts[1].isdigit() else 0
                left = r_parts[0][3:]  # strip 'fr_'
                if "_" in left:
                    ctype, cid_str = left.split("_", 1)
                else:
                    ctype, cid_str = "post", left
        except Exception:
            ctype, cid_str, idx = "post", "0", 0

        react_set = get_system_setting("reactions_set", "👍 👎 ❤️ 👏")
        emojis = [e.strip() for e in react_set.split() if e.strip()] or ["👍", "👎", "❤️", "👏"]
        if idx < len(emojis):
            emoji_clicked = emojis[idx]
            try:
                cursor.execute(
                    "SELECT emoji FROM feed_reactions WHERE content_type = ? AND content_id = ? AND user_id = ?",
                    (str(ctype), str(cid_str), user_id)
                )
                existing = cursor.fetchone()
                if existing and existing["emoji"] == emoji_clicked:
                    cursor.execute(
                        "DELETE FROM feed_reactions WHERE content_type = ? AND content_id = ? AND user_id = ?",
                        (str(ctype), str(cid_str), user_id)
                    )
                    conn.commit()
                    bot.answer_callback_query(call.id, f"Реакция олиб ташланди: {emoji_clicked}")
                else:
                    cursor.execute(
                        "INSERT OR REPLACE INTO feed_reactions (content_type, content_id, user_id, emoji) VALUES (?, ?, ?, ?)",
                        (str(ctype), str(cid_str), user_id, emoji_clicked)
                    )
                    conn.commit()
                    bot.answer_callback_query(call.id, f"Раҳмат! Баҳоингиз қабул қилинди: {emoji_clicked}")
            except Exception as e_rx:
                logging.error(f"Error saving reaction: {e_rx}")
                try:
                    bot.answer_callback_query(call.id, f"✅ {emoji_clicked}")
                except Exception:
                    pass

            try:
                share_txt = _content_share_cache.get(f"{ctype}_{cid_str}", "Asalarichilik.Uz")
                updated_markup = get_post_buttons_markup(content_type=ctype, content_id=cid_str, share_text=share_txt)
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=updated_markup
                )
            except Exception as ue:
                logging.debug(f"Could not edit reply markup: {ue}")
        else:
            bot.answer_callback_query(call.id, "Қабул қилинди! 👍")
        return

    # 0.2 БОТ ВА ПОСТ СОЗЛАМАЛАРИ БОШҚАРУВИ
    elif data == "post_toggle_autoreact":
        curr = get_system_setting("auto_reactions", "1")
        new_v = "0" if curr == "1" else "1"
        set_system_setting("auto_reactions", new_v)
        bot.answer_callback_query(call.id, "✅ Авто-реакциялар ўзгарди")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_toggle_share":
        curr = get_system_setting("share_button", "1")
        new_v = "0" if curr == "1" else "1"
        set_system_setting("share_button", new_v)
        bot.answer_callback_query(call.id, "✅ Улашиш тугмаси ўзгарди")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_toggle_expert":
        curr = get_system_setting("expert_button", "1")
        new_v = "0" if curr == "1" else "1"
        set_system_setting("expert_button", new_v)
        bot.answer_callback_query(call.id, "✅ Мутахассис тугмаси ўзгарди")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_cycle_reactions":
        presets = ["👍 👎 ❤️ 👏", "👍 ❤️ 🔥 👏", "🔥 💯 🍯 🐝", "👍 👎 🐝 🍯", "❤️ 😍 👏 🤝"]
        curr = get_system_setting("reactions_set", "👍 👎 ❤️ 👏")
        try:
            n_idx = (presets.index(curr) + 1) % len(presets)
        except ValueError:
            n_idx = 0
        set_system_setting("reactions_set", presets[n_idx])
        bot.answer_callback_query(call.id, f"✅ Тўплам: {presets[n_idx]}")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_custom_reactions":
        USER_STATES[user_id] = {"action": "wait_post_custom_reactions"}
        m_cancel = InlineKeyboardMarkup()
        m_cancel.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data="bc_settings"))
        bot.send_message(
            chat_id,
            "✏️ <b>Лайк ва реакция эможиларини ёзиб юборинг:</b>\n\n(Ҳар бирини бўш жой билан ажратиб ёзинг, масалан: <code>👍 👎 ❤️ 👏</code> ёки <code>🔥 🍯 🐝 👏</code>)",
            reply_markup=m_cancel,
            parse_mode="HTML"
        )
        return

    elif data == "post_set_channel":
        USER_STATES[user_id] = {"action": "wait_post_custom_channel"}
        m_cancel = InlineKeyboardMarkup()
        m_cancel.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data="bc_settings"))
        bot.send_message(
            chat_id,
            "📢 <b>Янги расмий канални юборинг:</b>\n\n(Масалан: <code>@Uz_Asalarichilik</code> ёки <code>https://t.me/Uz_Asalarichilik</code>)",
            reply_markup=m_cancel,
            parse_mode="HTML"
        )
        return

    elif data == "post_set_group":
        USER_STATES[user_id] = {"action": "wait_post_custom_group"}
        m_cancel = InlineKeyboardMarkup()
        m_cancel.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data="bc_settings"))
        bot.send_message(
            chat_id,
            "👥 <b>Янги расмий гуруҳни юборинг:</b>\n\n(Масалан: <code>@Asalarichilik_Uzbekistan</code> ёки <code>https://t.me/ASALARICHILIK_UZBEKISTAN</code>)",
            reply_markup=m_cancel,
            parse_mode="HTML"
        )
        return

    elif data == "post_toggle_script":
        curr = get_system_setting("script", "uz_kr")
        new_s = "uz_lat" if curr == "uz_kr" else "uz_kr"
        set_system_setting("script", new_s)
        set_system_setting("news_script", new_s)
        set_system_setting("quiz_script", new_s)
        bot.answer_callback_query(call.id, f"✅ Ёзув тури: {'Крил 🇺🇿' if new_s == 'uz_kr' else 'Лотин 🇺🇿'}")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_cycle_quiz_time":
        times = ["09:00", "10:00", "12:00", "15:00", "18:00", "20:00"]
        curr = get_system_setting("auto_quiz_time", "09:00")
        try:
            n_idx = (times.index(curr) + 1) % len(times)
        except ValueError:
            n_idx = 0
        set_system_setting("auto_quiz_time", times[n_idx])
        update_global_quiz_config(send_time=times[n_idx])
        bot.answer_callback_query(call.id, f"⏰ Авто-викторина: {times[n_idx]}")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_cycle_news_time":
        times = ["14:00", "08:00", "11:00", "16:00", "19:00", "21:00"]
        curr = get_system_setting("auto_news_time", "14:00")
        try:
            n_idx = (times.index(curr) + 1) % len(times)
        except ValueError:
            n_idx = 0
        set_system_setting("auto_news_time", times[n_idx])
        bot.answer_callback_query(call.id, f"📰 Авто-янгилик: {times[n_idx]}")
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "post_connected_list":
        cursor.execute("SELECT chat_id, title, username FROM channels")
        ch_rows = cursor.fetchall()
        cursor.execute("SELECT chat_id, title FROM groups WHERE is_authorized = 1")
        gr_rows = cursor.fetchall()
        txt = "📋 <b>УЛАНГАН КАНАЛ ВА ГУРУҲЛАР:</b>\n\n"
        txt += "📢 <b>Каналлар:</b>\n"
        if ch_rows:
            for c in ch_rows:
                txt += f"• {c['title']} (@{c['username'] or 'юзер йўқ'})\n"
        else:
            txt += "<i>Уланган каналлар йўқ</i>\n"
        txt += "\n👥 <b>Гуруҳлар:</b>\n"
        if gr_rows:
            for g in gr_rows:
                txt += f"• {g['title']}\n"
        else:
            txt += "<i>Фаол гуруҳлар йўқ</i>\n"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("« Орқага", callback_data="bc_settings"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return

    elif data == "post_close_settings":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            safe_edit_or_send(chat_id, call.message.message_id, "✅ Созламалар ёпилди.", None)
        return

    elif data.startswith("cb_react_"):
        parts = data.split("_")
        # cb_react_{post_id}_{idx}
        try:
            post_id = int(parts[2])
            idx = int(parts[3])
            cursor.execute("SELECT reactions_json, url_buttons_json, has_comments, native_comments, message_text FROM controller_posts WHERE post_id = ?", (post_id,))
            p_row = cursor.fetchone()
            if p_row:
                reacts = json.loads(p_row["reactions_json"] or "[]")
                if idx < len(reacts):
                    emoji_type = reacts[idx]
                    cursor.execute("SELECT emoji FROM post_reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id))
                    existing = cursor.fetchone()
                    if existing and existing["emoji"] == emoji_type:
                        cursor.execute("DELETE FROM post_reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id))
                        conn.commit()
                        bot.answer_callback_query(call.id, "Реакция олиб ташланди / Removed")
                    else:
                        cursor.execute(
                            "INSERT OR REPLACE INTO post_reactions (post_id, chat_id, user_id, emoji) VALUES (?, ?, ?, ?)",
                            (post_id, chat_id, user_id, emoji_type)
                        )
                        conn.commit()
                        bot.answer_callback_query(call.id, f"✅ {emoji_type}")

                    new_markup = build_controller_post_markup(
                        post_id=post_id,
                        reactions_list=reacts,
                        url_buttons_rows=json.loads(p_row["url_buttons_json"] or "[]"),
                        has_comments=bool(p_row["has_comments"]),
                        comments_url=p_row.get("comments_url", ""),
                        native_comments=bool(p_row["native_comments"]),
                        share_text=p_row["message_text"] or "Asalarichilik"
                    )
                    try:
                        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=new_markup)
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Reaction error: {e}")
        return

    # 1.1 Эски react_ кўриниши ҳам ишлаши учун
    if data.startswith("react_"):
        parts = data.split("_")
        post_id = int(parts[1])
        emoji_type = parts[2]
        cursor.execute("SELECT emoji FROM post_reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id))
        existing = cursor.fetchone()
        if existing and existing["emoji"] == emoji_type:
            cursor.execute("DELETE FROM post_reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, "Реакция олиб ташланди")
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO post_reactions (post_id, chat_id, user_id, emoji) VALUES (?, ?, ?, ?)",
                (post_id, chat_id, user_id, emoji_type)
            )
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Қабул қилинди!")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=build_reaction_markup(post_id))
        except Exception:
            pass
        return

    # 1.4 Бошқарув рухсатлари текширувдан ўтди

    # 1.5 Бот номидан жонли мулоқот ва жавоб бериш ҳодисалари
    if data.startswith("bot_chat_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        gid = int(data.replace("bot_chat_", ""))
        cursor.execute("SELECT title FROM groups WHERE chat_id = ?", (gid,))
        g_row = cursor.fetchone()
        g_title = g_row["title"] if g_row else "Гуруҳ"
        USER_STATES[user_id] = {
            "action": "live_chat_as_bot",
            "target_group_id": gid,
            "target_group_title": g_title
        }
        stop_markup = ReplyKeyboardMarkup(resize_keyboard=True)
        stop_markup.row(KeyboardButton("❌ Мулоқотни тўхтатиш"))
        bot.send_message(
            chat_id,
            f"🎙 <b>«{g_title}» билан БОТ НОМИДАН ЖОНЛИ МУЛОҚОТ РЕЖИМИ ЁҚИЛДИ!</b>\n\n"
            f"Энди сиз личкага нима юборсангиз (матн, овозли хабар 🎤, расм, видео, стикер), бот уни автоматик равишда гуруҳга <b>ўз номидан</b> юборади.\n\n"
            f"Гуруҳдагилар ботга жавоб қайтарса, уларнинг хабари сизнинг личкангизга келади.\n\n"
            f"Мулоқотни тўхтатиш учун: «❌ Мулоқотни тўхтатиш» тугмасини босинг.",
            reply_markup=stop_markup,
            parse_mode="HTML"
        )
        return

    elif data.startswith("bot_reply_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        parts = data.split("_")
        gid = int(parts[2])
        mid = int(parts[3])
        USER_STATES[user_id] = {
            "action": "reply_as_bot",
            "target_group_id": gid,
            "reply_to_msg_id": mid
        }
        cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_markup.row(KeyboardButton("❌ Бекор қилиш"))
        bot.send_message(
            chat_id,
            "✍️ <b>Ушбу хабарга бот номидан жавобингизни ёзинг:</b>\n\n(Матн, овозли хабар ёки расм юборишингиз мумкин)",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )
        return

    elif data.startswith("pin_to_grp_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        gid = int(data.replace("pin_to_grp_", ""))
        state = USER_STATES.pop(user_id, {})
        txt_to_send = state.get("text", "")
        if txt_to_send:
            try:
                sent = bot.send_message(gid, f"📌 <b>МУҲИМ ЭЪЛОН:</b>\n\n{txt_to_send}", parse_mode="HTML")
                bot.pin_chat_message(gid, sent.message_id)
                bot.answer_callback_query(call.id, "✅ Гуруҳга чиқарилди ва закрепить қилинди!")
                bot.send_message(chat_id, f"✅ <b>Хабар гуруҳга чиқарилди ва Закрепить қилинди!</b>\n\n<i>«{txt_to_send}»</i>", reply_markup=get_main_reply_keyboard(u_lang, user_id), parse_mode="HTML")
            except Exception as e:
                bot.send_message(chat_id, f"❌ Хатолик: {e}")
        return

    elif data.startswith("say_to_grp_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        gid = int(data.replace("say_to_grp_", ""))
        state = USER_STATES.pop(user_id, {})
        txt_to_send = state.get("text", "")
        if txt_to_send:
            try:
                bot.send_message(gid, txt_to_send)
                bot.answer_callback_query(call.id, "✅ Гуруҳга юборилди!")
                bot.send_message(chat_id, f"✅ Хабар бот номидан гуруҳга етказилди:\n<i>«{txt_to_send}»</i>", reply_markup=get_main_reply_keyboard(u_lang, user_id), parse_mode="HTML")
            except Exception as e:
                bot.send_message(chat_id, f"❌ Юборишда хатолик: {e}")
        return


    # 2. Реклама ва Хабар тарқатиш (Controller Bot) ҳодисалари
    if data == "bc_menu":
        if user_id == OWNER_ID:
            show_broadcast_menu(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data == "bc_create_post":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        show_broadcast_channel_select(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("bc_pick_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        t_id = data.replace("bc_pick_", "")
        t_name = "Барча гуруҳ ва каналлар" if u_lang != "ru" else "Все группы и каналы"
        if t_id != "all":
            try:
                t_int = int(t_id)
                cursor.execute("SELECT title, username FROM channels WHERE chat_id = ?", (t_int,))
                ch = cursor.fetchone()
                if ch:
                    t_name = ch["title"] or ch["username"] or "Канал"
                else:
                    cursor.execute("SELECT title FROM groups WHERE chat_id = ?", (t_int,))
                    gr = cursor.fetchone()
                    if gr:
                        t_name = gr["title"] or "Гуруҳ"
            except Exception:
                pass

        USER_STATES[user_id] = {
            "action": "waiting_post_content",
            "post": {
                "target_id": t_id,
                "target_name": t_name,
                "text": "",
                "media_type": "text",
                "file_id": None,
                "reactions": [],
                "url_buttons": [],
                "has_comments": False,
                "native_comments": False,
                "is_silent": False,
                "delete_timer_hours": 0,
                "show_more": False
            }
        }
        cancel_kb = get_cancel_reply_keyboard(u_lang)
        if u_lang == "ru":
            msg_txt = (
                "Отправьте боту то, что хотите опубликовать. Это может быть все, что угодно — "
                "текст, фото, видео, даже локация или стикер.\n\n"
                "Для отмены нажмите кнопку «Отменить» ниже."
            )
        elif u_lang == "en":
            msg_txt = (
                "Send the bot what you want to publish. It can be anything — "
                "text, photo, video, document, etc.\n\n"
                "To cancel, click the 'Cancel' button below."
            )
        else:
            msg_txt = (
                "Канал/гуруҳга эълон қилмоқчи бўлган хабарингизни юборинг. "
                "Бу ихтиёрий матн, расм, видео ёки ҳужжат бўлиши мумкин.\n\n"
                "Бекор қилиш учун пастдаги «Бекор қилиш» тугмасини босинг."
            )
        bot.send_message(chat_id, msg_txt, reply_markup=cancel_kb)
        return

    elif data == "bc_attach_media":
        if user_id in USER_STATES:
            USER_STATES[user_id]["action"] = "waiting_media_input"
            bot.send_message(chat_id, "Отправьте фото, видео или документ для прикрепления к посту:" if u_lang == "ru" else "Постга бириктирмоқчи бўлган расм, видео ёки ҳужжатни юборинг:", reply_markup=get_cancel_reply_keyboard(u_lang))
        return

    elif data == "bc_add_reactions":
        if user_id in USER_STATES:
            USER_STATES[user_id]["action"] = "waiting_reactions_input"
            prompt = (
                "Отправьте список реакций. Реакции могут быть смайликами, текстом или их комбинацией.\n"
                "Разделяйте реакции пробелом, запятой или слэшем.\n"
                "Пример: 👍 / 👎 / ❤️"
                if u_lang == "ru" else
                "Реакцияларни юборинг. Уларни бўш жой, вергул ёки слэш билан ажратинг.\n"
                "Мисол: 👍 / 👎 / ❤️"
            )
            bot.send_message(chat_id, prompt, reply_markup=get_reactions_preset_reply_keyboard(u_lang))
        return

    elif data == "bc_add_urls":
        if user_id in USER_STATES:
            USER_STATES[user_id]["action"] = "waiting_urls_input"
            prompt = (
                "Отправьте список URL-кнопок в следующем формате:\n\n"
                "<code>Кнопка 1 - https://t.me/kanal | Кнопка 2 - https://t.me/link</code>\n"
                "<code>Кнопка 3 - https://uzb.uz</code>"
                if u_lang == "ru" else
                "Ҳавола (URL) тугмаларини қуйидаги форматда юборинг:\n\n"
                "<code>Тугма 1 - https://t.me/kanal | Тугма 2 - https://t.me/link</code>\n"
                "<code>Тугма 3 - https://uzb.uz</code>"
            )
            bot.send_message(chat_id, prompt, reply_markup=get_cancel_reply_keyboard(u_lang), parse_mode="HTML")
        return

    elif data == "bc_add_comments":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            show_comments_config_menu(chat_id, user_id, call.message.message_id, lang=u_lang)
        return

    elif data == "bc_set_comment_bot":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            p = USER_STATES[user_id]["post"]
            p["has_comments"] = True
            p["comments_url"] = "bot"
            bot.answer_callback_query(call.id, "✅ Бот орқали интерактив изоҳлар ёқилди!")
            render_post_editor_screen(chat_id, user_id, p, lang=u_lang)
        return

    elif data == "bc_set_comment_url":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            USER_STATES[user_id]["action"] = "waiting_comments_url"
            bot.send_message(
                chat_id,
                "Изоҳлар (муҳокама) учун гуруҳ ёки чат ҳаволасини юборинг (Масалан: <code>https://t.me/Uz_Asalarichilik</code> ёки <code>@Uz_Asalarichilik</code>):",
                reply_markup=get_cancel_reply_keyboard(u_lang),
                parse_mode="HTML"
            )
        return

    elif data == "bc_set_comment_off":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            p = USER_STATES[user_id]["post"]
            p["has_comments"] = False
            p["comments_url"] = ""
            bot.answer_callback_query(call.id, "❌ Изоҳлар ўчирилди!")
            render_post_editor_screen(chat_id, user_id, p, lang=u_lang)
        return

    elif data == "bc_native_comments":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            show_comments_config_menu(chat_id, user_id, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("refresh_comments_"):
        post_id = int(data.replace("refresh_comments_", ""))
        cursor.execute("SELECT post_id, message_text FROM controller_posts WHERE post_id = ?", (post_id,))
        p_row = cursor.fetchone()
        if p_row:
            raw_ptext = p_row["message_text"] or ""
            clean_ptext = re.sub(r'<[^>]+>', '', raw_ptext).strip()
            if len(clean_ptext) > 160:
                clean_ptext = clean_ptext[:160] + "..."
            cursor.execute("SELECT full_name, comment_text, created_at FROM post_comments WHERE post_id = ? ORDER BY comment_id DESC LIMIT 5", (post_id,))
            c_rows = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) as c FROM post_comments WHERE post_id = ?", (post_id,))
            c_count = cursor.fetchone()["c"]

            comments_str = ""
            if c_rows:
                c_list = []
                for cr in reversed(c_rows):
                    c_author = html.escape(cr["full_name"] or "Фойдаланувчи")
                    c_msg = html.escape(cr["comment_text"] or "")
                    c_list.append(f"👤 <b>{c_author}</b>: {c_msg}")
                comments_str = "\n\n".join(c_list)
            else:
                comments_str = "<i>Ҳозирча изоҳлар йўқ. Биринчи бўлиб фикр қолдиринг!</i>"

            txt = (
                f"💬 <b>ПОСТ МУҲОКАМАСИ ВА ИЗОҲЛАР</b>\n\n"
                f"📌 <b>Пост:</b> <i>«{html.escape(clean_ptext)}»</i>\n\n"
                f"📊 <b>Жами фикрлар:</b> {c_count} та\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{comments_str}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"✍️ <b>Ушбу пост бўйича ўз фикрингиз, саволингиз ёки изоҳингизни ёзиб юборинг:</b>"
            )
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("🔄 Янгилаш", callback_data=f"refresh_comments_{post_id}"))
            kb.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
            safe_edit_or_send(chat_id, call.message.message_id, txt, kb)
            bot.answer_callback_query(call.id, "🔄 Янгиланди")
        return

    elif data == "bc_toggle_silent":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            p = USER_STATES[user_id]["post"]
            p["is_silent"] = not p.get("is_silent", False)
            bot.answer_callback_query(call.id, "🔕 Без звука" if p["is_silent"] else "🔔 Со звуком")
            render_post_editor_screen(chat_id, user_id, p, lang=u_lang)
        return

    elif data == "bc_clear_draft":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            p = USER_STATES[user_id]["post"]
            p["text"] = ""
            p["file_id"] = None
            p["reactions"] = []
            p["url_buttons"] = []
            p["media_type"] = "text"
            USER_STATES[user_id]["action"] = "waiting_post_content"
            bot.answer_callback_query(call.id, "🗑 Очищено")
            bot.send_message(chat_id, "Пост очищен. Отправьте новое содержимое:" if u_lang == "ru" else "Пост тозаланди. Янги хабар юборинг:", reply_markup=get_cancel_reply_keyboard(u_lang))
        return

    elif data == "bc_show_more":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            USER_STATES[user_id]["post"]["show_more"] = True
            render_post_editor_screen(chat_id, user_id, USER_STATES[user_id]["post"], lang=u_lang)
        return

    elif data == "bc_hide_more":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            USER_STATES[user_id]["post"]["show_more"] = False
            render_post_editor_screen(chat_id, user_id, USER_STATES[user_id]["post"], lang=u_lang)
        return

    elif data == "bc_toggle_pin":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            p = USER_STATES[user_id]["post"]
            p["pinned"] = not p.get("pinned", False)
            render_post_editor_screen(chat_id, user_id, p, lang=u_lang)
        return

    elif data == "bc_toggle_link_prev":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            p = USER_STATES[user_id]["post"]
            p["disable_preview"] = not p.get("disable_preview", False)
            render_post_editor_screen(chat_id, user_id, p, lang=u_lang)
        return

    elif data == "bc_timer_menu":
        show_delete_timer_menu(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("bc_settimer_"):
        hrs = int(data.replace("bc_settimer_", ""))
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            USER_STATES[user_id]["post"]["delete_timer_hours"] = hrs
        show_publish_stage(chat_id, user_id, call.message.message_id, lang=u_lang)
        return

    elif data == "bc_back_to_publish":
        show_publish_stage(chat_id, user_id, call.message.message_id, lang=u_lang)
        return

    elif data == "bc_back_to_editor":
        if user_id in USER_STATES and "post" in USER_STATES[user_id]:
            render_post_editor_screen(chat_id, user_id, USER_STATES[user_id]["post"], lang=u_lang)
        return

    elif data == "bc_publish_now":
        if user_id not in USER_STATES or "post" not in USER_STATES[user_id]:
            bot.answer_callback_query(call.id, "Хатолик ёки муддат ўтган")
            return
        post_dict = USER_STATES.pop(user_id)["post"]
        bot.answer_callback_query(call.id, "⏳ Публикация...")
        sent_count, p_id = execute_publish_controller_post(post_dict)
        bot.send_message(
            chat_id,
            f"✅ <b>Пост успешно опубликован в {sent_count} канал(ов)/групп!</b>\n\nВсе кнопки реакций, ссылок и комментариев активированы."
            if u_lang == "ru" else
            f"✅ <b>Пост {sent_count} та канал/гуруҳга муваффақиятли эълон қилинди!</b>\n\nБарча реакция, ҳавола ва изоҳлар тугмалари ишламоқда.",
            reply_markup=get_main_reply_keyboard(u_lang, user_id),
            parse_mode="HTML"
        )
        show_broadcast_menu(chat_id, lang=u_lang)
        return

    elif data == "bc_schedule_prompt":
        if user_id in USER_STATES:
            USER_STATES[user_id]["action"] = "waiting_schedule_input"
            bot.send_message(
                chat_id,
                "Отправьте время публикации в формате ЧЧ:ММ (напр. <code>18:30</code>) или ДД.ММ ЧЧ:ММ (напр. <code>15.10 18:30</code>):"
                if u_lang == "ru" else
                "Эълон қилиш вақтини киритинг: <code>18:30</code> ёки <code>15.10 18:30</code> кўринишида:",
                reply_markup=get_cancel_reply_keyboard(u_lang),
                parse_mode="HTML"
            )
        return

    elif data == "bc_delayed_list":
        cursor.execute("SELECT * FROM controller_posts WHERE status = 'scheduled' ORDER BY scheduled_time ASC")
        rows = cursor.fetchall()
        markup = InlineKeyboardMarkup()
        if not rows:
            txt = "У вас нет отложенных постов." if u_lang == "ru" else "Сизда режалаштирилган отложенные постлар йўқ."
        else:
            txt = f"⏳ <b>Отложенные посты ({len(rows)} та):</b>\n\n"
            for r in rows:
                p_text = (r["message_text"] or "Медиа пост")[:40]
                txt += f"• #{r['post_id']} | <b>{r['scheduled_time']}</b> | {r['target_name']}\n  <i>{p_text}...</i>\n\n"
                markup.row(InlineKeyboardButton(f"❌ Отменить #{r['post_id']}", callback_data=f"bc_deldelayed_{r['post_id']}"))
        markup.row(InlineKeyboardButton("« Назад" if u_lang == "ru" else "« Орқага", callback_data="bc_menu"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return

    elif data.startswith("bc_deldelayed_"):
        pid = int(data.replace("bc_deldelayed_", ""))
        cursor.execute("DELETE FROM controller_posts WHERE post_id = ? AND status = 'scheduled'", (pid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Отложенный пост отменен!")
        # re-show list
        cursor.execute("SELECT * FROM controller_posts WHERE status = 'scheduled' ORDER BY scheduled_time ASC")
        rows = cursor.fetchall()
        markup = InlineKeyboardMarkup()
        if not rows:
            txt = "У вас нет отложенных постов." if u_lang == "ru" else "Сизда режалаштирилган отложенные постлар йўқ."
        else:
            txt = f"⏳ <b>Отложенные посты ({len(rows)} та):</b>\n\n"
            for r in rows:
                p_text = (r["message_text"] or "Медиа пост")[:40]
                txt += f"• #{r['post_id']} | <b>{r['scheduled_time']}</b> | {r['target_name']}\n  <i>{p_text}...</i>\n\n"
                markup.row(InlineKeyboardButton(f"❌ Отменить #{r['post_id']}", callback_data=f"bc_deldelayed_{r['post_id']}"))
        markup.row(InlineKeyboardButton("« Назад" if u_lang == "ru" else "« Орқага", callback_data="bc_menu"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return

    elif data == "bc_edit_list":
        cursor.execute("SELECT * FROM controller_posts WHERE status = 'published' ORDER BY post_id DESC LIMIT 5")
        rows = cursor.fetchall()
        markup = InlineKeyboardMarkup()
        if not rows:
            txt = "У вас нет опубликованных постов для редактирования." if u_lang == "ru" else "Таҳрирлаш учун эълон қилинган постлар топилмади."
        else:
            txt = "✏️ <b>Последние опубликованные посты:</b>\n\n"
            for r in rows:
                p_text = (r["message_text"] or "Медиа")[:35]
                txt += f"• #{r['post_id']} | {r['created_at']} | {r['target_name']}\n  <i>{p_text}</i>\n"
                markup.row(InlineKeyboardButton(f"🗑 Удалить #{r['post_id']}", callback_data=f"bc_delpublished_{r['post_id']}"))
        markup.row(InlineKeyboardButton("« Назад" if u_lang == "ru" else "« Орқага", callback_data="bc_menu"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return

    elif data.startswith("bc_delpublished_"):
        pid = int(data.replace("bc_delpublished_", ""))
        cursor.execute("DELETE FROM controller_posts WHERE post_id = ?", (pid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Пост удален из базы данных!")
        show_broadcast_menu(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data == "bc_stats":
        cursor.execute("SELECT COUNT(*) as cnt FROM controller_posts WHERE status = 'published'")
        p_cnt = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM post_reactions")
        r_cnt = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM channels")
        c_cnt = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM groups WHERE is_authorized = 1")
        g_cnt = cursor.fetchone()["cnt"]
        txt = (
            f"📊 <b>СТАТИСТИКА КАНАЛОВ И ПОСТОВ</b>\n\n"
            f"• 📢 Подключено каналов: <b>{c_cnt}</b>\n"
            f"• 👥 Подключено групп: <b>{g_cnt}</b>\n"
            f"• 📝 Опубликовано постов: <b>{p_cnt}</b>\n"
            f"• ❤️ Всего кликов по реакциям: <b>{r_cnt}</b>\n\n"
            f"<i>Статистика обновляется в режиме реального времени.</i>"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("« Назад" if u_lang == "ru" else "« Орқага", callback_data="bc_menu"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return

    elif data == "bc_settings":
        show_post_settings_menu(chat_id, call.message.message_id)
        return

    elif data == "bc_promo":
        txt = (
            "🚀 <b>Рекламировать Ваш канал:</b>\n\n"
            "Вы можете разместить ссылку на канал во всех связанных группах пчеловодства.\n"
            "Официальный канал: @Uz_Asalarichilik\n"
            "Связь с владельцем: @JamshidjonDavronov"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("👑 Связаться", url="https://t.me/JamshidjonDavronov"))
        markup.row(InlineKeyboardButton("« Назад" if u_lang == "ru" else "« Орқага", callback_data="bc_menu"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return

    elif data == "bc_interests":
        cursor.execute("SELECT emoji, COUNT(*) as cnt FROM post_reactions GROUP BY emoji ORDER BY cnt DESC LIMIT 5")
        top_reacts = cursor.fetchall()
        txt = "🔎 <b>Интересы и вовлеченность подписчиков:</b>\n\n"
        if not top_reacts:
            txt += "Пока нет данных о реакциях. Создайте пост с реакциями!"
        else:
            txt += "Топ реакций подписчиков:\n"
            for tr in top_reacts:
                txt += f"• {tr['emoji']} — <b>{tr['cnt']} голосов</b>\n"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("« Назад" if u_lang == "ru" else "« Орқага", callback_data="bc_menu"))
        safe_edit_or_send(chat_id, call.message.message_id, txt, markup)
        return


    # 3. Ботни гуруҳга қўшиш огоҳлантириши (КРИТИК ТАЛАБ)
    elif data == "menu_add_group":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("👑 Бот эгаси билан боғланиш", url="https://t.me/JamshidjonDavronov"))
        markup.row(InlineKeyboardButton("➕ Гуруҳга қўшиш", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"))
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))

        if u_lang == "ru":
            notice_text = (
                "⚠️ <b>ВНИМАНИЕ! ПРАВИЛА ДОБАВЛЕНИЯ БОТА В ГРУППУ</b>\n\n"
                "Если вы хотите добавить этого бота в свою группу:\n\n"
                "1. Сначала свяжитесь с владельцем бота: <b>@JamshidjonDavronov</b>\n"
                "2. Получите его согласие на использование бота в вашей группе.\n"
                "3. Только после согласия добавьте бота и назначьте его администратором со всеми правами.\n\n"
                "<i>Без согласия владельца бот автоматически выйдет из группы и не будет работать.</i>"
            )
        elif u_lang == "en":
            notice_text = (
                "⚠️ <b>IMPORTANT NOTICE: ADDING BOT TO GROUPS</b>\n\n"
                "If you wish to add this bot to your Telegram group:\n\n"
                "1. First contact the bot owner: <b>@JamshidjonDavronov</b>\n"
                "2. Obtain his explicit authorization to manage your group.\n"
                "3. Only after obtaining permission, add the bot as an administrator.\n\n"
                "<i>Without owner approval, the bot will automatically leave the group and will not function.</i>"
            )
        elif u_lang == "uz_lat":
            notice_text = (
                "⚠️ <b>DIQQAT! BOTNI GURUHGA QO'SHISH SHARTLARI</b>\n\n"
                "Agar ushbu botni o'z guruhingizga qo'shib ishlatmoqchi bo'lsangiz:\n\n"
                "1. Avvalo bot egasi <b>@JamshidjonDavronov</b> bilan bog'laning\n"
                "2. Botni guruhingizda ishlatish uchun uning roziligini oling.\n"
                "3. Rozilik olgach, botni guruhga to'liq administrator qilib tayinlang.\n\n"
                "<i>Bot egasining roziligisiz bot begona guruhlarda ishlamaydi va guruhdan chiqib ketadi.</i>"
            )
        else:
            notice_text = (
                "⚠️ <b>ДИҚҚАТ! БОТНИ ГУРУҲГА ҚЎШИШ ШАРТИ</b>\n\n"
                "Агар ушбу ботни ўз гуруҳингизга қўшиб ишлатмоқчи бўлсангиз:\n\n"
                "1. Аввало бот эгаси <b>@JamshidjonDavronov</b> билан боғланинг\n"
                "2. Ботни гуруҳингизда ишлатиш учун унинг розилигини олинг.\n"
                "3. Розилик олгач, ботни гуруҳга тўлиқ администратор қилиб тайинланг.\n\n"
                "<i>Бот эгасининг розилигисиз бот бегона гуруҳларда ишламайди ва автоматик равишда гуруҳдан чиқиб кетади.</i>"
            )
        bot.edit_message_text(notice_text, chat_id, call.message.message_id, reply_markup=markup)
        return

    # 3.01 Ботни каналга қўшиш менюси (КРИТИК ТАЛАБ)
    elif data == "menu_add_channel":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("➕ Каналга қўшиш (Админ қилиб)", url=f"https://t.me/{BOT_USERNAME}?startchannel=true&admin=post_messages+edit_messages+delete_messages+invite_users+pin_messages"))
        markup.row(InlineKeyboardButton("✏️ Канални қўлда улаш (@username)", callback_data="ch_add_manual"))
        markup.row(InlineKeyboardButton("👑 Бот эгаси билан боғланиш", url="https://t.me/JamshidjonDavronov"))
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))

        if u_lang == "ru":
            c_text = (
                "📢 <b>ДОБАВЛЕНИЕ БОТА В КАНАЛ</b>\n\n"
                "Чтобы бот отправлял новости пчеловодства, рекламу и важные посты с кнопками реакций прямо в ваш канал и закреплял их:\n\n"
                "1. Нажмите <b>«➕ Каналга қўшиш»</b> выше и выберите ваш канал.\n"
                "2. Назначьте бота <b>Администратором</b> (с правами публикации, редактирования и закрепления сообщений).\n"
                "3. Или нажмите <b>«✏️ Канални қўлда улаш»</b> и отправьте боту юзернейм канала (напр: <code>@asalarichilik</code>).\n\n"
                "<i>После подключения все посты будут отправляться не только в группы, но и в ваш канал!</i>"
            )
        else:
            c_text = (
                "📢 <b>БОТНИ КАНАЛГА ҚЎШИШ ВА УЛАШ:</b>\n\n"
                "Бот каналингизга асаларичилик янгиликлари, реклама ва эълонларни чиройли тугмалар билан юбориши ҳамда тепасига қадаб (закрепить қилиб) қўйиши учун:\n\n"
                "1. Юқоридаги <b>«➕ Каналга қўшиш (Админ қилиб)»</b> тугмасини босиб, каналингизни танланг.\n"
                "2. Ботга хабар ёзиш, таҳрирлаш ва хабарларни қадаш (pin) ҳуқуқларини беринг.\n"
                "3. Ёки <b>«✏️ Канални қўлда улаш»</b> тугмасини босиб, каналингиз юзернеймини (масалан: <code>@asalarichilik</code>) ёзиб юборинг.\n\n"
                "<i>Канал улангач, маълумот ва рекламалар фақат гуруҳга эмас, ҳатто каналга ҳам автоматик юборилади ва қадалади!</i>"
            )
        bot.edit_message_text(c_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        return

    elif data == "channels_panel":
        show_channels_panel(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data == "ch_add_manual":
        USER_STATES[user_id] = {"action": "waiting_channel_username"}
        bot.send_message(
            chat_id,
            "✏️ <b>Каналингиз юзернейми ёки ҳаволасини юборинг:</b>\n\nМасалан: <code>@asalarichilik</code> ёки <code>@Uz_Asalarichilik</code>\n\n<i>(Бот аввал каналингизга админ қилиб қўшилган бўлиши керак)</i>",
            reply_markup=get_cancel_reply_keyboard(u_lang),
            parse_mode="HTML"
        )
        return

    elif data.startswith("ch_del_"):
        c_id = int(data.replace("ch_del_", ""))
        cursor.execute("DELETE FROM channels WHERE chat_id = ?", (c_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Канал рўйхатдан ўчирилди!")
        show_channels_panel(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("lock_all_"):
        gid = int(data.replace("lock_all_", ""))
        cursor.execute("""
            UPDATE groups SET 
                lock_links = 1, lock_forwards = 1, lock_spam = 1, 
                lock_badwords = 1, lock_stickers = 1, lock_arabic = 1, 
                lock_media = 1, lock_files = 1, lock_voice = 1 
            WHERE chat_id = ?
        """, (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "🔒 Барча қулфлар ёқилди! Энди қоидабузарликларга зудлик билан огоҳлантириш берилади ва ўчирилади.", show_alert=True)
        show_locks_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("unlock_all_"):
        gid = int(data.replace("unlock_all_", ""))
        cursor.execute("""
            UPDATE groups SET 
                lock_links = 0, lock_forwards = 0, lock_spam = 0, 
                lock_badwords = 0, lock_stickers = 0, lock_arabic = 0, 
                lock_media = 0, lock_files = 0, lock_voice = 0 
            WHERE chat_id = ?
        """, (gid,))
        conn.commit()
        try:
            bot.set_chat_permissions(gid, get_full_chat_permissions())
        except Exception:
            pass
        bot.answer_callback_query(call.id, "🔓 Барча қулфлар очилди! Гуруҳда хабар, расм ва видеоларга рухсат берилди.", show_alert=True)
        show_locks_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    # 4. Навигация ва менюлар
    elif data == "back_main":
        bot.edit_message_text(
            get_welcome_text(call.from_user.first_name, u_lang),
            chat_id,
            call.message.message_id,
            reply_markup=get_main_menu_markup(u_lang, user_id),
            disable_web_page_preview=True
        )
        return

    elif data == "menu_settings":
        open_group_selection(chat_id, call.message.message_id, lang=u_lang)
        return

    elif data == "menu_language":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🇺🇿 Ўзбекча (Кирилл)", callback_data="set_lang_uz_kr"),
            InlineKeyboardButton("🇺🇿 O'zbekcha (Lotin)", callback_data="set_lang_uz_lat")
        )
        markup.row(
            InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
        )
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text("🌐 <b>Тилни танланг / Выберите язык / Select language:</b>", chat_id, call.message.message_id, reply_markup=markup)
        return

    elif data.startswith("set_lang_"):
        new_lang = data.replace("set_lang_", "")
        cursor.execute("INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)", (user_id, new_lang))
        conn.commit()
        msg_ack = "Тил ўзгартирилди!" if new_lang == "uz_kr" else ("Язык изменен!" if new_lang == "ru" else ("Language updated!" if new_lang == "en" else "Til o'zgartirildi!"))
        bot.answer_callback_query(call.id, f"✅ {msg_ack}")
        bot.edit_message_text(
            get_welcome_text(call.from_user.first_name, new_lang),
            chat_id,
            call.message.message_id,
            reply_markup=get_main_menu_markup(new_lang, user_id),
            disable_web_page_preview=True
        )
        return

    elif data == "menu_help":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text(get_guide_text(u_lang), chat_id, call.message.message_id, reply_markup=markup)
        return

    # 5. Админ бўлмаган гуруҳ огоҳлантириши
    elif data.startswith("warn_not_admin_"):
        gid = int(data.replace("warn_not_admin_", ""))
        show_not_admin_warning(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("recheck_admin_"):
        gid = int(data.replace("recheck_admin_", ""))
        is_adm = check_bot_admin_status(gid)
        if is_adm:
            bot.answer_callback_query(call.id, "🎉 Табриклаймиз! Бот гуруҳда админ қилинди!", show_alert=True)
            show_settings_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        else:
            bot.answer_callback_query(call.id, "⚠️ Бот ҳали ҳам админ эмас! Илтимос, гуруҳга кириб ботга админлик ҳуқуқини беринг.", show_alert=True)
        return

    # 6. Панеллар навигацияси
    elif data.startswith("panel_settings_"):
        gid = int(data.replace("panel_settings_", ""))
        show_settings_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_forcesub_"):
        gid = int(data.replace("panel_forcesub_", ""))
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_weather_"):
        gid = int(data.replace("panel_weather_", ""))
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_timezone_"):
        gid = int(data.replace("panel_timezone_", ""))
        show_timezone_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_locks_"):
        gid = int(data.replace("panel_locks_", ""))
        show_locks_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_limits_"):
        gid = int(data.replace("panel_limits_", ""))
        show_limits_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_autolock_"):
        gid = int(data.replace("panel_autolock_", ""))
        show_autolock_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("panel_lists_"):
        gid = int(data.replace("panel_lists_", ""))
        show_lists_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    # 7. Мажбурий обуна ўзгаришлари
    elif data.startswith("toggle_forcesub_"):
        gid = int(data.replace("toggle_forcesub_", ""))
        cursor.execute("UPDATE groups SET forcesub_enabled = CASE WHEN forcesub_enabled = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        g_now = get_group(gid)
        st_text = "Мажбурий обуна ёқилди 🟢" if (g_now and g_now.get("forcesub_enabled", 0) == 1) else "Мажбурий обуна ўчирилди ⚪️"
        bot.answer_callback_query(call.id, st_text)
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("toggle_fsub_appr_") or data.startswith("toggle_fsub_mode_"):
        gid = int(data.replace("toggle_fsub_mode_", "").replace("toggle_fsub_appr_", ""))
        cursor.execute("UPDATE groups SET approval_enabled = CASE WHEN approval_enabled = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("toggle_fsub_act_"):
        gid = int(data.replace("toggle_fsub_act_", ""))
        cursor.execute("UPDATE groups SET forcesub_action = CASE WHEN forcesub_action = 'kick' THEN 'mute' ELSE 'kick' END WHERE chat_id = ?", (gid,))
        conn.commit()
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("toggle_fsub_scope_"):
        gid = int(data.replace("toggle_fsub_scope_", ""))
        cursor.execute("UPDATE groups SET forcesub_only_new = CASE WHEN forcesub_only_new = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("check_fsub_admin_"):
        gid = int(data.replace("check_fsub_admin_", ""))
        g = get_group(gid)
        chan = g.get("forcesub_channel", "@Asalarichilik_Uz") if g else "@Asalarichilik_Uz"

        bot_chan_ok = check_bot_channel_admin(chan)
        bot_grp_ok = check_bot_group_admin(gid)

        grp_name = html.escape(str(g.get('title', 'Гуруҳ')))
        msg_parts = [f"📊 <b>«{grp_name}» — БОТ АДМИНЛИК ҲИСОБОТИ:</b>\n"]
        if bot_chan_ok:
            msg_parts.append(f"✅ <b>Мажбурий Канал ({chan}):</b> Бот тўлиқ администратор! Аъзоликни текшира олади.")
        else:
            msg_parts.append(f"❌ <b>Мажбурий Канал ({chan}):</b> Бот админ эмас ёки канал топилмади! <i>Ботни каналга қўшиб, «Администратор» қилинг ва аъзоларни текшириш ҳуқуқини беринг.</i>")

        if bot_grp_ok:
            msg_parts.append("✅ <b>Гуруҳ:</b> Бот тўлиқ администратор! Хабарларни ўчириш ва чекловларни бошқариш ишламоқда.")
        else:
            msg_parts.append("❌ <b>Гуруҳ:</b> Бот тўлиқ администратор эмас! Илтимос, гуруҳ созламаларидан ботга тўлиқ админлик беринг.")

        bot.answer_callback_query(call.id, "Текширув ҳисоботи юборилди!")
        bot.send_message(chat_id, "\n\n".join(msg_parts), parse_mode="HTML")
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("change_fsub_chan_"):
        gid = int(data.replace("change_fsub_chan_", ""))
        USER_STATES[user_id] = {"action": "wait_forcesub_channel", "group_id": gid}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data=f"panel_forcesub_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text(
            "📢 <b>Янги мажбурий канал юзернеймини киритинг:</b>\n\n"
            "Масалан: <code>@yangiliklar_rasmiy</code> ёки <code>@asalarichilik</code>\n\n"
            "<i>(Эслатма: Бот ушбу каналда ҳам администратор бўлиши керак!)</i>",
            chat_id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        return

    elif data.startswith("cycle_fsub_timer_"):
        gid = int(data.replace("cycle_fsub_timer_", ""))
        g = get_group(gid)
        cur_t = g.get("forcesub_timer_min", 0) if g else 0
        cycle_list = [0, 1, 2, 3, 5, 10]
        if cur_t in cycle_list:
            next_t = cycle_list[(cycle_list.index(cur_t) + 1) % len(cycle_list)]
        else:
            next_t = 0
        cursor.execute("UPDATE groups SET forcesub_timer_min = ? WHERE chat_id = ?", (next_t, gid))
        conn.commit()
        t_info = "♾ Ўчирилмайдиган қилинди (Аъзо бўлмагунча)" if next_t == 0 else f"⏱ {next_t} дақиқага созланди"
        bot.answer_callback_query(call.id, f"✅ {t_info}")
        show_forcesub_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("input_fsub_timer_"):
        gid = int(data.replace("input_fsub_timer_", ""))
        USER_STATES[user_id] = {"action": "wait_fsub_timer", "group_id": gid}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data=f"panel_forcesub_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text(
            "⏱ <b>Огоҳлантириш хабари гуруҳда неча дақиқа туришини киритинг:</b>\n\n"
            "• <code>1</code> — 1 дақиқа туриб, кейин автоматик ўчирилади\n"
            "• <code>2</code> — 2 дақиқадан сўнг ўчирилади\n"
            "• <code>5</code> — 5 дақиқадан сўнг ўчирилади\n"
            "• <code>0</code> — <b>Умуман ўчирилмасин</b> (токи ўша фойдаланувчи каналга аъзо бўлмагунча гуруҳда туради)\n\n"
            "<i>Рақамни ёзиб юборинг:</i>",
            chat_id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        return

    # 8. Об-ҳаво sozlamalari
    elif data.startswith("w_set_type_"):
        parts = data.split("_")
        gid = int(parts[3])
        f_type = "_".join(parts[4:])
        cursor.execute("UPDATE groups SET weather_forecast_type = ? WHERE chat_id = ?", (f_type, gid))
        conn.commit()
        bot.answer_callback_query(call.id, f"✅ Прогноз: {f_type}")
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_input_time_"):
        gid = int(data.replace("weather_input_time_", ""))
        USER_STATES[user_id] = {"action": "wait_weather_time", "group_id": gid}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data=f"panel_weather_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text(
            "✏️ <b>Гуруҳга об-ҳаво жўнатилиши керак бўлган соатни ёзинг:</b>\n\n"
            "Масалан: <code>07:00</code>, <code>08:30</code>, <code>12:00</code>, <code>18:00</code>",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )
        return

    elif data.startswith("weather_set_time_"):
        gid = int(data.replace("weather_set_time_", ""))
        markup = InlineKeyboardMarkup()
        times = ["06:00", "07:00", "08:00", "09:00", "12:00", "18:00", "20:00", "21:00"]
        for i in range(0, len(times), 2):
            t1, t2 = times[i], times[i+1]
            markup.row(
                InlineKeyboardButton(f"⏰ {t1}", callback_data=f"w_time_sel_{gid}_{t1}"),
                InlineKeyboardButton(f"⏰ {t2}", callback_data=f"w_time_sel_{gid}_{t2}")
            )
        markup.row(InlineKeyboardButton("◀️ Орқага", callback_data=f"panel_weather_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text("⏰ Тезкор соатлардан бирини танланг:", chat_id, call.message.message_id, reply_markup=markup)
        return

    elif data.startswith("w_time_sel_"):
        parts = data.split("_")
        gid = int(parts[3])
        sel_time = parts[4]
        cursor.execute("UPDATE groups SET weather_time = ? WHERE chat_id = ?", (sel_time, gid))
        conn.commit()
        bot.answer_callback_query(call.id, f"✅ Соат: {sel_time}")
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_send_now_"):
        gid = int(data.replace("weather_send_now_", ""))
        send_weather_to_group(gid, lang=u_lang)
        bot.answer_callback_query(call.id, "✅ Об-ҳаво гуруҳга муваффақиятли юборилди!", show_alert=True)
        return

    elif data.startswith("toggle_weather_"):
        gid = int(data.replace("toggle_weather_", ""))
        cursor.execute("UPDATE groups SET weather_enabled = CASE WHEN weather_enabled = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_cycle_h_"):
        gid = int(data.replace("weather_cycle_h_", ""))
        g = get_group(gid)
        cur_h = g.get("weather_delete_hours", 2) if g else 2
        new_h = 0 if cur_h >= 12 else (cur_h + 1)
        cursor.execute("UPDATE groups SET weather_delete_hours = ? WHERE chat_id = ?", (new_h, gid))
        conn.commit()
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_cycle_m_"):
        gid = int(data.replace("weather_cycle_m_", ""))
        g = get_group(gid)
        cur_m = g.get("weather_delete_minutes", 0) if g else 0
        new_m = 0 if cur_m >= 45 else (cur_m + 15)
        cursor.execute("UPDATE groups SET weather_delete_minutes = ? WHERE chat_id = ?", (new_m, gid))
        conn.commit()
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_set_never_"):
        gid = int(data.replace("weather_set_never_", ""))
        cursor.execute("UPDATE groups SET weather_delete_hours = 0, weather_delete_minutes = 0 WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Об-ҳаво энди умуман ўчирилмайди (доимий сақланади)!")
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_set_2h_"):
        gid = int(data.replace("weather_set_2h_", ""))
        cursor.execute("UPDATE groups SET weather_delete_hours = 2, weather_delete_minutes = 0 WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Авто-ўчириш: 2 соат")
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_set_8h_"):
        gid = int(data.replace("weather_set_8h_", ""))
        cursor.execute("UPDATE groups SET weather_delete_hours = 8, weather_delete_minutes = 0 WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Авто-ўчириш: 8 соат")
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("weather_send_channels_"):
        gid = int(data.replace("weather_send_channels_", ""))
        g = get_group(gid)
        dh = g.get("weather_delete_hours", 2) if g else 2
        dm = g.get("weather_delete_minutes", 0) if g else 0
        cnt = send_weather_to_all_channels(dh, dm, lang=u_lang)
        bot.answer_callback_query(call.id, f"✅ Об-ҳаво маълумоти {cnt} та каналга юборилди ва қадалди! 📌", show_alert=True)
        return

    elif data.startswith("weather_cities_"):
        gid = int(data.replace("weather_cities_", ""))
        markup = InlineKeyboardMarkup()
        # Барча вилоятлар учун энг тепада алоҳида тугма:
        markup.row(InlineKeyboardButton("🇺🇿 Барча вилоятлар (Республика бўйича)", callback_data=f"w_c_{gid}_0"))
        for i in range(1, len(REGIONS_UZ_LIST), 2):
            r1 = REGIONS_UZ_LIST[i]
            btn1 = InlineKeyboardButton(r1, callback_data=f"w_c_{gid}_{i}")
            if i + 1 < len(REGIONS_UZ_LIST):
                r2 = REGIONS_UZ_LIST[i+1]
                btn2 = InlineKeyboardButton(r2, callback_data=f"w_c_{gid}_{i+1}")
                markup.row(btn1, btn2)
            else:
                markup.row(btn1)
        markup.row(InlineKeyboardButton("✏️ Шаҳар номини қўлда ёзиш", callback_data=f"w_city_custom_{gid}"))
        markup.row(InlineKeyboardButton("◀️ Орқага", callback_data=f"panel_weather_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        safe_edit_or_send(
            chat_id,
            call.message.message_id,
            "📍 <b>Гуруҳингиз қайси вилоят/ҳудудга тегишли?</b>\n\n"
            "Кунлик об-ҳавони <b>Бутун Ўзбекистон (Барча вилоятлар)</b> учун битта хабарда чиқаришингиз ёки алоҳида вилоятни танлашингиз мумкин:",
            markup
        )
        return

    elif data.startswith("w_city_custom_"):
        gid = int(data.replace("w_city_custom_", ""))
        USER_STATES[user_id] = {"action": "wait_weather_city", "group_id": gid}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data=f"panel_weather_{gid}"))
        safe_edit_or_send(
            chat_id,
            call.message.message_id,
            "📍 <b>Об-ҳаво учун ҳудуд ёки шаҳар номини ёзиб юборинг:</b>\n\n"
            "<i>Масалан:</i> <code>Тошкент</code>, <code>Қўқон</code>, <code>Марғилон</code>, <code>Нукус</code>, <code>Шаҳрисабз</code> ва ҳ.к.",
            markup
        )
        return

    elif data.startswith("w_c_") or data.startswith("w_city_sel_"):
        if data.startswith("w_c_"):
            sub = data.replace("w_c_", "")
            parts = sub.split("_")
            gid = int(parts[0])
            idx = int(parts[1])
            city_name = REGIONS_UZ_LIST[idx] if (0 <= idx < len(REGIONS_UZ_LIST)) else "Тошкент"
        else:
            parts = data.split("_")
            gid = int(parts[3])
            city_name = "_".join(parts[4:])

        cursor.execute("UPDATE groups SET weather_city = ? WHERE chat_id = ?", (city_name, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"✅ Ҳудуд белгиланди: {city_name}")
        show_weather_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    # 9. Вақт минтақаси sozlamalari
    elif data.startswith("tz_req_loc_"):
        gid = int(data.replace("tz_req_loc_", ""))
        USER_STATES[user_id] = {"action": "wait_location", "group_id": gid}
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row(KeyboardButton("📍 Ҳозирги геопозицияни юбориш", request_location=True))
        bot.send_message(
            chat_id,
            "📍 <b>Геопозиция орқали автоматик вақтни аниқлаш:</b>\n\n"
            "Қуйидаги «📍 Ҳозирги геопозицияни юбориш» тугмасини босинг. Бот жойлашган ерингиз бўйича аниқ UTC вақт зонасини аниқлаб созлайди.",
            reply_markup=markup
        )
        return

    elif data.startswith("tz_r_"):
        parts = data.replace("tz_r_", "").split("_")
        gid = int(parts[0])
        idx = int(parts[1])
        s_name = REGIONS_UZ_LIST[idx] if (0 <= idx < len(REGIONS_UZ_LIST)) else "Тошкент"
        city_label = f"{s_name} (UTC+5)"
        cursor.execute("UPDATE groups SET timezone_offset = 5, timezone_city = ? WHERE chat_id = ?", (city_label, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"✅ Минтақа сақланди: {city_label}")
        show_timezone_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("tz_set_quick_"):
        parts = data.split("_")
        gid = int(parts[3])
        offset = int(parts[4])
        city_label = "_".join(parts[5:])
        cursor.execute("UPDATE groups SET timezone_offset = ?, timezone_city = ? WHERE chat_id = ?", (offset, city_label, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"✅ Минтақа сақланди: {city_label}")
        show_timezone_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("tz_all_regions_"):
        gid = int(data.replace("tz_all_regions_", ""))
        markup = InlineKeyboardMarkup()
        for i in range(1, len(REGIONS_UZ_LIST), 2):
            s1 = REGIONS_UZ_LIST[i]
            btn1 = InlineKeyboardButton(s1, callback_data=f"tz_r_{gid}_{i}")
            if i + 1 < len(REGIONS_UZ_LIST):
                s2 = REGIONS_UZ_LIST[i+1]
                btn2 = InlineKeyboardButton(s2, callback_data=f"tz_r_{gid}_{i+1}")
                markup.row(btn1, btn2)
            else:
                markup.row(btn1)
        markup.row(InlineKeyboardButton("◀️ Орқага", callback_data=f"panel_timezone_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        safe_edit_or_send(chat_id, call.message.message_id, "🗺 <b>Ўзингизга тегишли вилоятни танланг:</b>", markup)
        return

    elif data.startswith("tz_custom_input_"):
        gid = int(data.replace("tz_custom_input_", ""))
        USER_STATES[user_id] = {"action": "wait_custom_tz", "group_id": gid}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data=f"panel_timezone_{gid}"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.edit_message_text(
            "✏️ <b>UTC соат фарқини киритинг:</b>\n\n"
            "Масалан, Ўзбекистон учун <code>+5</code> ёки бошқа давлатлар учун <code>+4</code>, <code>+3</code>:",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )
        return

    # 10. Қулфлар (Locks toggles - фақат аниқ қулф префикслари учун)
    elif any(data.startswith(pfx) for pfx in ["toggle_links_", "toggle_fwd_", "toggle_spam_", "toggle_badwords_", "toggle_stickers_", "toggle_arabic_", "toggle_files_", "toggle_voice_", "toggle_media_", "toggle_welcome_", "toggle_approval_", "toggle_joins_"]):
        lock_map = {
            "toggle_links_": "lock_links",
            "toggle_fwd_": "lock_forwards",
            "toggle_spam_": "lock_spam",
            "toggle_badwords_": "lock_badwords",
            "toggle_stickers_": "lock_stickers",
            "toggle_arabic_": "lock_arabic",
            "toggle_files_": "lock_files",
            "toggle_voice_": "lock_voice",
            "toggle_media_": "lock_media",
            "toggle_welcome_": "welcome_enabled",
            "toggle_approval_": "approval_enabled",
            "toggle_joins_": "clean_joins"
        }
        for prefix, col in lock_map.items():
            if data.startswith(prefix):
                gid = int(data.replace(prefix, ""))
                cursor.execute(f"UPDATE groups SET {col} = CASE WHEN {col} = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
                conn.commit()
                backup_settings_to_file()
                # Агар медиа очилса (lock_media == 0), Telegram рухсатини ҳам автоматик очиш:
                if col == "lock_media":
                    cursor.execute("SELECT lock_media FROM groups WHERE chat_id = ?", (gid,))
                    r_med = cursor.fetchone()
                    if r_med and r_med["lock_media"] == 0:
                        try:
                            bot.set_chat_permissions(gid, get_full_chat_permissions())
                        except Exception:
                            pass
                if prefix in ["toggle_welcome_", "toggle_approval_", "toggle_joins_"]:
                    show_settings_panel(chat_id, gid, call.message.message_id, lang=u_lang)
                else:
                    show_locks_panel(chat_id, gid, call.message.message_id, lang=u_lang)
                return

    # 10.1 Тунги авто-қулфлаш ва медиа лимитлари созламалари
    elif data.startswith("toggle_autolock_en_"):
        gid = int(data.replace("toggle_autolock_en_", ""))
        cursor.execute("UPDATE groups SET autolock_enabled = CASE WHEN autolock_enabled = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        backup_settings_to_file()
        cursor.execute("SELECT * FROM groups WHERE chat_id = ?", (gid,))
        r_al = cursor.fetchone()
        is_now_enabled = bool(r_al and ("autolock_enabled" in r_al) and r_al["autolock_enabled"] == 1)
        if is_now_enabled:
            bot.answer_callback_query(call.id, "🌙 Тунги авто-қулф ёқилди! ✅")
            if is_autolock_active_now(r_al):
                try:
                    bot.set_chat_permissions(gid, types.ChatPermissions(can_send_messages=False))
                except Exception as pe:
                    logging.warning(f"Error locking permissions: {pe}")
        else:
            bot.answer_callback_query(call.id, "☀️ Тунги авто-қулф ўчирилди! 🔓")
            try:
                bot.set_chat_permissions(gid, get_full_chat_permissions())
            except Exception as pe:
                logging.warning(f"Error restoring permissions: {pe}")
        show_autolock_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("cycle_autolock_start_"):
        gid = int(data.replace("cycle_autolock_start_", ""))
        cursor.execute("SELECT autolock_start_time FROM groups WHERE chat_id = ?", (gid,))
        r = cursor.fetchone()
        cur_t = r["autolock_start_time"] if r else "23:00"
        times = ["20:00", "21:00", "22:00", "23:00", "00:00", "01:00"]
        next_t = times[(times.index(cur_t) + 1) % len(times)] if cur_t in times else "23:00"
        cursor.execute("UPDATE groups SET autolock_start_time = ? WHERE chat_id = ?", (next_t, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"🔒 Қулфлаш вақти: {next_t}")
        show_autolock_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("cycle_autolock_end_"):
        gid = int(data.replace("cycle_autolock_end_", ""))
        cursor.execute("SELECT autolock_end_time FROM groups WHERE chat_id = ?", (gid,))
        r = cursor.fetchone()
        cur_t = r["autolock_end_time"] if r else "06:30"
        times = ["05:00", "05:30", "06:00", "06:30", "07:00", "08:00"]
        next_t = times[(times.index(cur_t) + 1) % len(times)] if cur_t in times else "06:30"
        cursor.execute("UPDATE groups SET autolock_end_time = ? WHERE chat_id = ?", (next_t, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"🔓 Очилиш вақти: {next_t}")
        show_autolock_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("toggle_limit_en_"):
        gid = int(data.replace("toggle_limit_en_", ""))
        cursor.execute("UPDATE groups SET limit_enabled = CASE WHEN limit_enabled = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        backup_settings_to_file()
        cursor.execute("SELECT limit_enabled FROM groups WHERE chat_id = ?", (gid,))
        r = cursor.fetchone()
        is_en = bool(r and ("limit_enabled" in r) and r["limit_enabled"] == 1)
        bot.answer_callback_query(call.id, "✅ Медиа лимит ёқилди" if is_en else "⚪️ Медиа лимит ўчирилди")
        show_limits_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("cycle_limit_max_"):
        gid = int(data.replace("cycle_limit_max_", ""))
        cursor.execute("SELECT limit_max FROM groups WHERE chat_id = ?", (gid,))
        r = cursor.fetchone()
        cur_m = r["limit_max"] if r else 3
        maxes = [1, 2, 3, 5, 10]
        next_m = maxes[(maxes.index(cur_m) + 1) % len(maxes)] if cur_m in maxes else 3
        cursor.execute("UPDATE groups SET limit_max = ? WHERE chat_id = ?", (next_m, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"Максимум лимит: {next_m} та қилиб белгиланди! ✅")
        show_limits_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("set_lim_"):
        sub = data[len("set_lim_"):]
        gid_str, lim_str = sub.rsplit("_", 1)
        gid = int(gid_str)
        lim_val = int(lim_str)
        cursor.execute("UPDATE groups SET limit_max = ? WHERE chat_id = ?", (lim_val, gid))
        conn.commit()
        backup_settings_to_file()
        bot.answer_callback_query(call.id, f"Лимит: {lim_val} та қилиб белгиланди! ✅")
        show_limits_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    elif data.startswith("toggle_limit_mute_"):
        gid = int(data.replace("toggle_limit_mute_", ""))
        cursor.execute("UPDATE groups SET limit_repeat_mute = CASE WHEN limit_repeat_mute = 1 THEN 0 ELSE 1 END WHERE chat_id = ?", (gid,))
        conn.commit()
        backup_settings_to_file()
        cursor.execute("SELECT limit_repeat_mute FROM groups WHERE chat_id = ?", (gid,))
        r = cursor.fetchone()
        is_m = bool(r and ("limit_repeat_mute" in r) and r["limit_repeat_mute"] == 1)
        bot.answer_callback_query(call.id, "✅ 24 соатлик МУТ ёқилди" if is_m else "⚪️ 24 соатлик МУТ ўчирилди")
        show_limits_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return
    elif data.startswith("change_limit_msg_"):
        gid = int(data.replace("change_limit_msg_", ""))
        USER_STATES[user_id] = {"action": "wait_limit_msg", "group_id": gid}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Дефолт ҳолатга қайтариш", callback_data=f"reset_limit_msg_{gid}"))
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data=f"panel_limits_{gid}"))
        prompt_txt = (
            "✍️ <b>Медиа лимит бўйича янги огоҳлантириш матнини ёзиб юборинг:</b>\n\n"
            "Матнда қуйидаги шаблонлардан фойдаланишингиз мумкин:\n"
            "• <code>{user}</code> — Фойдаланувчи исми/юзернейми\n"
            "• <code>{max}</code> — Белгиланган лимит сони\n"
            "• <code>{count}</code> — Ҳозирги юборилган сони\n\n"
            "<i>Масалан:</i>\n"
            "Ҳурматли {user}! Гуруҳимизда кунига фақат {max} та расм ташлаш мумкин. Ортиқчаси ўчирилди!"
        )
        bot.send_message(chat_id, prompt_txt, reply_markup=markup, parse_mode="HTML")
        return
    elif data.startswith("reset_limit_msg_"):
        gid = int(data.replace("reset_limit_msg_", ""))
        cursor.execute("UPDATE groups SET limit_warn_msg = '' WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "Дефолт матн тикланди!")
        show_limits_panel(chat_id, gid, call.message.message_id, lang=u_lang)
        return

    # 11. Обуна текшируви (Гуруҳда янги аъзо босганда)
    elif data.startswith("check_sub_"):
        parts = data.split("_")
        grp_id = int(parts[2])
        target_uid = int(parts[3])
        if user_id != target_uid and not is_user_allowed_to_manage_group(grp_id, user_id):
            bot.answer_callback_query(call.id, "⚠️ Бу тугма фақат янги аъзонинг ўзи учун!", show_alert=True)
            return

        g = get_group(grp_id)
        chan = clean_channel_username(g.get("forcesub_channel", "@uz_asalarichilik") if g else "@uz_asalarichilik")
        is_sub, missing = check_user_channels_subscription(chan, target_uid)
        if is_sub:
            cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (grp_id, target_uid))
            conn.commit()
            delete_msg_safe(call.message.chat.id, call.message.message_id)

            if g and g.get("approval_enabled", 0) == 1:
                bot.answer_callback_query(call.id, "✅ Каналга обуна тасдиқланди! Энди админ розилиги кутилмоқда.", show_alert=True)
                appr_markup = InlineKeyboardMarkup()
                appr_markup.row(
                    InlineKeyboardButton("✅ Рухсат бериш", callback_data=f"approve_member_{grp_id}_{target_uid}"),
                    InlineKeyboardButton("❌ Рад этиш", callback_data=f"reject_member_{grp_id}_{target_uid}")
                )
                u_name = html.escape(str(call.from_user.first_name))
                bot.send_message(
                    grp_id,
                    f"🔐 <b>ЯНГИ АЪЗОНИ ТАСДИҚЛАШ (Админ розилиги)</b>\n\n"
                    f"👤 <b>{u_name}</b> (@{call.from_user.username or 'юзернейм йўқ'}) каналга аъзо бўлди.\n"
                    f"Гуруҳда ёзишига рухсат берасизми?",
                    reply_markup=appr_markup,
                    parse_mode="HTML"
                )
            else:
                # Чекловни (мутни) тўлиқ олиб ташлаш:
                lift_user_mute(grp_id, target_uid)
                bot.answer_callback_query(call.id, "✅ Обуна тасдиқланди! Гуруҳда ёзишга чеклов олиб ташланди. Бемалол ёзишингиз мумкин! 🎉", show_alert=True)
                u_name = html.escape(str(call.from_user.first_name))
                succ = bot.send_message(grp_id, f"✅ <b>{u_name}</b> каналга муваффақиятли аъзо бўлди ва гуруҳда ёзишга тўлиқ рухсат берилди! 🎉", parse_mode="HTML")
                threading.Timer(20, lambda: delete_msg_safe(grp_id, succ.message_id)).start()
        else:
            miss_str = ", ".join(missing) if missing else chan
            bot.answer_callback_query(call.id, f"❌ Сиз ҳали {miss_str} каналига аъзо бўлмадингиз! Илтимос, аввал каналга кириб «Аъзо бўлиш»ни босинг.", show_alert=True)
        return

    elif data.startswith("approve_member_"):
        parts = data.split("_")
        grp_id = int(parts[2])
        target_uid = int(parts[3])
        if not is_user_allowed_to_manage_group(grp_id, user_id):
            bot.answer_callback_query(call.id, "⚠️ Фақат гуруҳ админлари рухсат бера олади!", show_alert=True)
            return

        lift_user_mute(grp_id, target_uid)
        cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (grp_id, target_uid))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Аъзога рухсат берилди!")
        adm_name = html.escape(str(call.from_user.first_name))
        bot.edit_message_text(
            f"✅ <b>Админ {adm_name}</b> томонидан аъзога гуруҳда ёзишга рухсат берилди! 🎉",
            grp_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        return

    elif data.startswith("reject_member_"):
        parts = data.split("_")
        grp_id = int(parts[2])
        target_uid = int(parts[3])
        if not is_user_allowed_to_manage_group(grp_id, user_id):
            bot.answer_callback_query(call.id, "⚠️ Фақат гуруҳ админлари рад эта олади!", show_alert=True)
            return

        try:
            bot.ban_chat_member(grp_id, target_uid)
            bot.unban_chat_member(grp_id, target_uid)
        except Exception as e:
            logging.error(f"Kick error: {e}")

        bot.answer_callback_query(call.id, "❌ Аъзо рад этилди ва гуруҳдан чиқарилди.")
        adm_name = html.escape(str(call.from_user.first_name))
        bot.edit_message_text(
            f"❌ <b>Админ {adm_name}</b> томонидан янги аъзо рад этилди ва гуруҳдан четлаштирилди.",
            grp_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        return

    # 11.2 Кириш сўровларини (Join Request) админ томонидан тасдиқлаш / рад этиш
    elif data.startswith("approve_req_"):
        parts = data.split("_")
        grp_id = int(parts[2])
        target_uid = int(parts[3])
        if not is_user_allowed_to_manage_group(grp_id, user_id):
            bot.answer_callback_query(call.id, "⚠️ Фақат гуруҳ админлари тасдиқлай олади!", show_alert=True)
            return

        try:
            bot.approve_chat_join_request(grp_id, target_uid)
        except Exception as e:
            logging.error(f"Approve join request error: {e}")

        cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (grp_id, target_uid))
        conn.commit()

        bot.answer_callback_query(call.id, "✅ Сўров қабул қилинди!")
        adm_name = html.escape(str(call.from_user.first_name))
        bot.edit_message_text(
            f"✅ <b>Админ {adm_name}</b> сўровни тасдиқлади ва фойдаланувчи гуруҳга қабул қилинди! 🎉",
            grp_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        try:
            bot.send_message(target_uid, "✅ Гуруҳга қўшилиш сўровингиз админ томонидан тасдиқланди! Гуруҳга хуш келибсиз! 🎉")
        except Exception:
            pass
        return

    elif data.startswith("reject_req_"):
        parts = data.split("_")
        grp_id = int(parts[2])
        target_uid = int(parts[3])
        if not is_user_allowed_to_manage_group(grp_id, user_id):
            bot.answer_callback_query(call.id, "⚠️ Фақат гуруҳ админлари рад эта олади!", show_alert=True)
            return

        try:
            bot.decline_chat_join_request(grp_id, target_uid)
        except Exception as e:
            logging.error(f"Decline join request error: {e}")

        bot.answer_callback_query(call.id, "❌ Сўров рад этилди.")
        adm_name = html.escape(str(call.from_user.first_name))
        bot.edit_message_text(
            f"❌ <b>Админ {adm_name}</b> томонидан сўров рад этилди.",
            grp_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        return

    # 11.3 Join Request шахсий чатидаги текширув тугмаси
    elif data.startswith("req_check_sub_"):
        parts = data.split("_")
        grp_id = int(parts[3])
        target_uid = int(parts[4])
        if user_id != target_uid:
            bot.answer_callback_query(call.id, "⚠️ Бу тугма фақат сиз учун!", show_alert=True)
            return

        g = get_group(grp_id)
        chan = clean_channel_username(g.get("forcesub_channel", "@asalarichilik") if g else "@asalarichilik")
        is_sub, missing = check_user_channels_subscription(chan, target_uid)

        if is_sub:
            cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (grp_id, target_uid))
            conn.commit()

            if g and g.get("approval_enabled", 0) == 1:
                bot.answer_callback_query(call.id, "✅ Каналга обуна тасдиқланди! Сўровингиз админга юборилди.", show_alert=True)
                delete_msg_safe(call.message.chat.id, call.message.message_id)
                bot.send_message(
                    call.message.chat.id,
                    "✅ <b>Каналга обунангиз муваффақиятли тасдиқланди!</b>\n\n"
                    "Гуруҳга қўшилиш сўровингиз гуруҳ админларига юборилди. "
                    "Админ тасдиқлаши биланоқ гуруҳга қабул қилинасиз! ⏳",
                    parse_mode="HTML"
                )
                appr_markup = InlineKeyboardMarkup()
                appr_markup.row(
                    InlineKeyboardButton("✅ Қабул қилиш", callback_data=f"approve_req_{grp_id}_{target_uid}"),
                    InlineKeyboardButton("❌ Рад этиш", callback_data=f"reject_req_{grp_id}_{target_uid}")
                )
                u_name = html.escape(str(call.from_user.first_name))
                bot.send_message(
                    grp_id,
                    f"🔐 <b>ЯНГИ АЪЗО ТАСДИҒИ (Админ розилиги)</b>\n\n"
                    f"👤 <b>{u_name}</b> (@{call.from_user.username or 'юзернейм йўқ'}) каналга аъзо бўлди ва гуруҳга қўшилиш сўровини юборди.\n\n"
                    f"Гуруҳга қабул қиласизми?",
                    reply_markup=appr_markup,
                    parse_mode="HTML"
                )
            else:
                try:
                    bot.approve_chat_join_request(grp_id, target_uid)
                except Exception as ae:
                    logging.error(f"approve join req error: {ae}")
                bot.answer_callback_query(call.id, "✅ Табриклаймиз! Сўровингиз қабул қилинди!", show_alert=True)
                delete_msg_safe(call.message.chat.id, call.message.message_id)
                grp_t = html.escape(str(g.get('title', 'Гуруҳ')))
                bot.send_message(
                    call.message.chat.id,
                    f"🎉 <b>Табриклаймиз!</b>\n\nСиз <b>{grp_t}</b> гуруҳига муваффақиятли қабул қилиндингиз! Бемалол гуруҳда мулоқот қилишингиз мумкин.",
                    parse_mode="HTML"
                )
        else:
            miss_str = ", ".join(missing) if missing else chan
            bot.answer_callback_query(call.id, f"❌ Сиз ҳали {miss_str} каналига аъзо бўлмадингиз! Илтимос, аввал каналга аъзо бўлинг.", show_alert=True)
        return

    # 12. Гуруҳга рухсат бериш / рад этиш (Эгаси учун)
    elif data.startswith("auth_allow_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        gid = int(data.replace("auth_allow_", ""))
        cursor.execute("UPDATE groups SET is_authorized = 1 WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Гуруҳ муваффақиятли фаоллаштирилди!")
        bot.edit_message_text(f"✅ <b>Гуруҳда бот ишлашига рухсат берилди!</b> (ID: <code>{gid}</code>)", chat_id, call.message.message_id)
        try:
            bot.send_message(gid, "✅ <b>Бот эгаси рухсати олинди!</b>\n\nБотнинг барча ҳимоя ва бошқарув функциялари фаоллашди.", parse_mode="HTML")
        except Exception:
            pass
        return

    elif data.startswith("auth_deny_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        gid = int(data.replace("auth_deny_", ""))
        cursor.execute("DELETE FROM groups WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "❌ Гуруҳ рад этилди ва бот чиқиб кетади.")
        bot.edit_message_text(f"❌ <b>Гуруҳ рад этилди.</b> Бот ушбу гуруҳдан чиқиб кетади.", chat_id, call.message.message_id)
        try:
            bot.send_message(gid, f"❌ <b>Бот эгаси ({OWNER_USERNAME}) томонидан ушбу гуруҳ рад этилди.</b>\n\nБот гуруҳни тарк этмоқда.", parse_mode="HTML")
            bot.leave_chat(gid)
        except Exception:
            pass
        return

    elif data == "owner_groups":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        show_owner_groups_panel(chat_id, call.message.message_id, u_lang)
        return

    elif data == "owner_allow_prompt":
        if user_id != OWNER_ID:
            return
        USER_STATES[user_id] = {"action": "wait_group_allow_id"}
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("◀️ Бекор қилиш", callback_data="owner_groups"), InlineKeyboardButton("🏠 Асосий Меню", callback_data="back_main"))
        bot.send_message(chat_id, "✍️ <b>Рухсат берилмоқчи бўлган Гуруҳ ID рақамини юборинг:</b>\n\n(Масалан: <code>-1001234567890</code>)", reply_markup=markup, parse_mode="HTML")
        return

    elif data.startswith("auth_revoke_"):
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔️ Фақат бот эгаси учун!")
            return
        gid = int(data.replace("auth_revoke_", ""))
        cursor.execute("UPDATE groups SET is_authorized = 0 WHERE chat_id = ?", (gid,))
        conn.commit()
        bot.answer_callback_query(call.id, "⛔️ Гуруҳ рухсати тўхтатилди!")
        show_owner_groups_panel(chat_id, call.message.message_id, u_lang)
        try:
            bot.send_message(gid, f"⚠️ <b>Бот эгаси ({OWNER_USERNAME}) томонидан ушбу гуруҳ рухсати тўхтатилди.</b>", parse_mode="HTML")
        except Exception:
            pass
        return

# ==================== ГУРУҲ ХАВФСИЗЛИК ВА СПАМ ФИЛЬТРИ ====================
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'], content_types=['new_chat_members', 'left_chat_member'])
def service_messages_filter(message):
    chat_id = message.chat.id
    title = message.chat.title or "Гуруҳ"
    register_group(chat_id, title, added_by=OWNER_ID)
    g = get_group(chat_id)
    if not is_group_authorized(chat_id):
        return

    # 1. Аъзо гуруҳдан чиқиб кетса:
    if message.left_chat_member:
        left_u = message.left_chat_member
        cursor.execute("DELETE FROM forcesub_verified WHERE chat_id = ? AND user_id = ?", (chat_id, left_u.id))
        cursor.execute("DELETE FROM new_members WHERE chat_id = ? AND user_id = ?", (chat_id, left_u.id))
        conn.commit()

_last_forcesub_user_warn = {}

def enforce_group_forcesub_on_join(chat_id, user, chat_title="Гуруҳ", chat_username=None):
    """Янги ёки қайта қўшилган аъзонинг мажбурий каналга обунасини текшириш ва гуруҳга огоҳлантириш чиқариш"""
    if user.is_bot:
        return
    g = get_group(chat_id)
    if not g or g.get("forcesub_enabled", 0) != 1:
        return

    cursor.execute("DELETE FROM forcesub_verified WHERE chat_id = ? AND user_id = ?", (chat_id, user.id))
    cursor.execute("INSERT OR REPLACE INTO new_members (chat_id, user_id) VALUES (?, ?)", (chat_id, user.id))
    conn.commit()

    channel = clean_channel_username(g.get("forcesub_channel", "@uz_asalarichilik"))
    is_sub, missing = check_user_channels_subscription(channel, user.id)
    u_f_name = html.escape(str(user.first_name))
    u_mention = f"<a href='tg://user?id={user.id}'>{u_f_name}</a>"

    if is_sub:
        cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (chat_id, user.id))
        conn.commit()
        if g.get("approval_enabled", 0) == 1:
            try:
                bot.restrict_chat_member(chat_id, user.id, permissions=types.ChatPermissions(can_send_messages=False))
            except Exception:
                pass
            appr_markup = InlineKeyboardMarkup()
            appr_markup.row(
                InlineKeyboardButton("✅ Рухсат бериш", callback_data=f"approve_member_{chat_id}_{user.id}"),
                InlineKeyboardButton("❌ Рад этиш", callback_data=f"reject_member_{chat_id}_{user.id}")
            )
            bot.send_message(
                chat_id,
                f"🔐 <b>ЯНГИ АЪЗО ТАСДИҒИ (Админ розилиги)</b>\n\n"
                f"👤 <b>{u_f_name}</b> (@{user.username or 'юзернейм йўқ'}) каналга аъзо бўлган.\n"
                f"Гуруҳда ёзишига рухсат берасизми?",
                reply_markup=appr_markup,
                parse_mode="HTML"
            )
        else:
            lift_user_mute(chat_id, user.id)
    else:
        # Каналга аъзо бўлмаган:
        # 1. Гуруҳда дарҳол мут (ёзишни чеклаш)
        try:
            bot.restrict_chat_member(
                chat_id,
                user.id,
                permissions=types.ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )
        except Exception as re:
            logging.warning(f"Failed to restrict member {user.id}: {re}")

        # 2. Огоҳлантиришни ТЎҒРИДАН-ТЎҒРИ ГУРУҲГА жўнатиш
        sub_markup = InlineKeyboardMarkup()
        for m_ch in (missing if missing else [channel]):
            c_clean = m_ch.replace("@", "")
            sub_markup.row(InlineKeyboardButton(f"📢 {m_ch} каналига аъзо бўлиш", url=f"https://t.me/{c_clean}"))
        sub_markup.row(InlineKeyboardButton("✅ Текшириш (Аъзо бўлдим)", callback_data=f"check_sub_{chat_id}_{user.id}"))
        sub_markup.row(InlineKeyboardButton("🤖 Бот орқали мутдан чиқиш", url=f"https://t.me/{BOT_USERNAME}?start=unmute_{chat_id}"))

        mode_hint = "Обунадан сўнг админ тасдиғи керак бўлади." if g.get("approval_enabled", 0) == 1 else "Каналга аъзо бўлгач, «Аъзо бўлдим» тугмасини босинг — ёзиш чеклов дарҳол олиб ташланади."
        warn_txt = (
            f"⛔️ Ҳурматли <b>{u_mention}</b>!\n\n"
            f"Гуруҳимизда мажбурий обуна тизими ёқилган.\n"
            f"Гуруҳда хабар ёзиш учун аввал расмий каналимизга аъзо бўлишингиз шарт:\n"
            f"📢 <b>{channel}</b>\n\n"
            f"<i>({mode_hint})</i>\n\n"
            f"Каналга обуна бўлгач, пастдаги <b>«✅ Текшириш (Аъзо бўлдим)»</b> тугмасини босинг."
        )
        w_msg = bot.send_message(chat_id, warn_txt, reply_markup=sub_markup, parse_mode="HTML")

        # 3. Гуруҳдан автоматик ўчириш (60 сонияда ёки админ танлаган вақтда ўчирилади):
        timer_sec = (g.get("forcesub_timer_min", 0) * 60) if g.get("forcesub_timer_min", 0) > 0 else 60
        threading.Timer(timer_sec, lambda: delete_msg_safe(chat_id, w_msg.message_id)).start()

    # 2. Янги ёки қайта қўшилган аъзолар (Service messages):
    if message.new_chat_members:
        for new_u in message.new_chat_members:
            enforce_group_forcesub_on_join(chat_id, new_u, title, message.chat.username)
        delete_msg_safe(chat_id, message.message_id)

@bot.chat_member_handler()
def handle_chat_member_update(update):
    try:
        chat_id = update.chat.id
        if update.chat.type not in ['group', 'supergroup']:
            return
        old_status = update.old_chat_member.status
        new_status = update.new_chat_member.status
        if old_status in ['left', 'kicked'] and new_status in ['member', 'restricted']:
            user = update.new_chat_member.user
            enforce_group_forcesub_on_join(chat_id, user, update.chat.title or "Гуруҳ", update.chat.username)
        elif new_status in ['left', 'kicked']:
            user = update.old_chat_member.user
            cursor.execute("DELETE FROM forcesub_verified WHERE chat_id = ? AND user_id = ?", (chat_id, user.id))
            cursor.execute("DELETE FROM new_members WHERE chat_id = ? AND user_id = ?", (chat_id, user.id))
            conn.commit()
    except Exception as e:
        logging.warning(f"chat_member_update error: {e}")

_last_autolock_user_warn = {}
_last_media_warn = {}
_media_group_tracker = {}
_media_album_warned = {}
_media_lock = threading.RLock()

def normalize_hm(t_str, default="00:00"):
    try:
        parts = t_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return f"{h:02d}:{m:02d}"
    except Exception:
        return default

def is_autolock_active_now(g):
    if not g or g.get("autolock_enabled", 0) != 1:
        return False
    try:
        tz_offset = g.get("timezone_offset", 5) or 5
        group_now = get_now(tz_offset)
        curr_hm = group_now.strftime("%H:%M")
        s_time = normalize_hm(g.get("autolock_start_time", "23:00"), "23:00")
        e_time = normalize_hm(g.get("autolock_end_time", "06:30"), "06:30")
        if s_time == e_time:
            return False
        if s_time < e_time:
            return s_time <= curr_hm < e_time
        else:
            return curr_hm >= s_time or curr_hm < e_time
    except Exception as e:
        logging.error(f"is_autolock_active_now error: {e}")
        return False

def send_lock_violation_warning(chat_id, user, violation_uz, violation_ru, lang="uz_kr"):
    """
    Худди 2-расмдагидек (DIGI ANTI услубида) аниқ ва чиройли огоҳлантириш юбориш:
    • Уважаемый пользователь Шерзод(⊙_⊙),
    • Отправка (анимированных стикер) в группе запрещена.

    » Пожалуйста, не отправляйте это снова.
    """
    u_first = html.escape((user.first_name if user and user.first_name else "Фойдаланувчи") or "Фойдаланувчи")
    u_mention = f"<a href='tg://user?id={user.id}'>{u_first}</a>" if (user and user.id) else u_first

    if lang == "ru":
        warn_text = (
            f"• Уважаемый пользователь {u_mention},\n"
            f"• Отправка (<b>{violation_ru}</b>) в группе запрещена.\n\n"
            f"» Пожалуйста, не отправляйте это снова."
        )
    else:
        warn_text = (
            f"• Ҳурматли фойдаланувчи {u_mention},\n"
            f"• Гуруҳда (<b>{violation_uz}</b>) юбориш тақиқланган.\n\n"
            f"» Илтимос, қайта жўнатманг."
        )

    try:
        w_msg = bot.send_message(chat_id, warn_text, parse_mode="HTML")
        threading.Timer(30, lambda: delete_msg_safe(chat_id, w_msg.message_id)).start()
        return w_msg
    except Exception as e:
        logging.error(f"send_lock_violation_warning error: {e}")
        return None

def is_whitelisted_entity_or_url(val):
    if not val:
        return False
    v = str(val).lower().strip()
    if BOT_USERNAME and (BOT_USERNAME.lower().replace("@", "") in v):
        return True
    whitelisted_words = [
        "uz_asalarichilik",
        "asalarichilik_uzbekistan",
        "asalarichiliktv_bot",
        "asalarichilikuztv",
        "telegram"
    ]
    for w in whitelisted_words:
        if w in v:
            return True
    try:
        c_chan = get_official_channel().lower().replace("@", "")
        if c_chan and c_chan in v:
            return True
        c_grp = get_official_group().lower().replace("@", "")
        if c_grp and c_grp in v:
            return True
    except Exception:
        pass
    return False

@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'], content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation', 'contact', 'location', 'poll'])
def group_protection_filter(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    content_type = message.content_type
    raw_txt = (message.text or message.caption or "").strip()
    title = message.chat.title or "Гуруҳ"

    u_obj = message.from_user
    u_name = html.escape(u_obj.first_name if u_obj and u_obj.first_name else "Фойдаланувчи")
    u_tag = f"@{u_obj.username}" if (u_obj and u_obj.username) else f"<a href='tg://user?id={user_id}'>{u_name}</a>"

    # ==================== 0. TELEGRAM ХИЗМАТ ҲИСОБЛАРИ ВА КАНАЛ ПОСТЛАРИНИ БЕХАТО ЎТКАЗИШ ====================
    # 1. Хабар канал ёки гуруҳ номидан (sender_chat) юборилган бўлса
    if getattr(message, 'sender_chat', None):
        # Фақат гуруҳнинг ўз аноним админи (sender_chat.id == chat_id) бўлса ўтказиш
        if message.sender_chat.id == chat_id:
            return
        # Агар ташқаридан канал номи билан пост қўйилса, унга ҳам қулфлар ва медиа лимит тўлиқ қўлланади:
        user_id = message.sender_chat.id
        u_name = html.escape(message.sender_chat.title or "Канал")
        u_tag = f"<b>{u_name}</b>"

    # 2. Telegram томонидан уланган каналдан автоматик келган барча хабарлар (муҳокама гуруҳига)
    elif getattr(message, 'is_automatic_forward', False):
        return

    # 3. Telegram расмий тизим ҳисоблари (777000) ва аноним админ (1087968824)
    elif user_id in [777000, 1087968824]:
        return

    # 4. Ботнинг ўз хабарлари
    try:
        if user_id == bot.get_me().id:
            return
    except Exception:
        pass

    register_group(chat_id, title, added_by=OWNER_ID)

    if not is_group_authorized(chat_id):
        return

    is_user_admin = (user_id == OWNER_ID or is_admin(chat_id, user_id))

    # ==================== 0. ГУРУҲДА БУЙРУҚЛАРНИ БАЖАРИШ ====================
    if raw_txt.startswith('/'):
        delete_msg_safe(chat_id, message.message_id)
        if raw_txt.startswith(("/obhavo", "/weather")):
            send_weather_to_group(chat_id, lang="uz_kr")
            return
        if raw_txt.startswith(('/qulflar', '/locks', '/settings', '/panel', '/admin')):
            if is_user_admin:
                show_locks_panel(chat_id, chat_id, message_id=None, lang="uz_kr")
            return
        if raw_txt.startswith(('/unlock', '/och', '/ochish')):
            if is_user_admin:
                cursor.execute("UPDATE groups SET lock_links = 0, lock_forwards = 0, lock_spam = 0, lock_badwords = 0, lock_stickers = 0, lock_arabic = 0, lock_media = 0, lock_files = 0, lock_voice = 0, autolock_enabled = 0 WHERE chat_id = ?", (chat_id,))
                conn.commit()
                try:
                    bot.set_chat_permissions(chat_id, get_full_chat_permissions())
                except Exception:
                    pass
                n = bot.send_message(chat_id, "🔓 <b>Гуруҳ тўлиқ очилди!</b>\n\nБарча турдаги хабарлар, расмлар, видеолар, файллар ва овозли хабарларга тўлиқ рухсат берилди. ✅", parse_mode="HTML")
                threading.Timer(15, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            return
        if not is_user_admin:
            return

    # ==================== 0.1 АДМИНЛИК БУЙРУҚЛАРИ (ДРОБСИЗ, ОДДИЙ СЎЗ БИЛАН) ====================
    words = raw_txt.split()
    first_w = words[0].lower() if words else ""

    # ==================== БОТ НОМИДАН ЖАВОБ БЕРИШ (REPLY AS BOT / ЖАВОБ) ====================
    clean_first_w = first_w.lstrip("/!.").rstrip(":-")
    if is_user_admin and clean_first_w in ["reply", "репли", "реплай", "жавоб", "javob", "say", "сей", "gapir", "гапир", "bot", "бот", "ayt", "айт"]:
        delete_msg_safe(chat_id, message.message_id)
        reply_mid = message.reply_to_message.message_id if message.reply_to_message else None
        body = raw_txt[len(words[0]):].strip() if words else ""
        if body.startswith(":") or body.startswith("-"):
            body = body[1:].strip()

        if not body and content_type == "text":
            n = bot.send_message(
                chat_id,
                "ℹ️ <b>Бот номидан жавоб бериш:</b>\n\n"
                "Фойдаланувчи хабарига <b>Reply</b> (жавоб) қилиб:\n"
                "<code>reply Сизнинг матнингиз</code> ёки <code>жавоб: Сизнинг матнингиз</code>\n\n"
                "деб ёзсангиз, бот сизнинг номингиздан ўша хабарга расмий жавоб қайтаради ва сизнинг буйруғингизни автоматик ўчиради.",
                parse_mode="HTML"
            )
            threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            return

        try:
            if content_type == "text":
                bot.send_message(chat_id, body, reply_to_message_id=reply_mid)
            elif content_type == "photo":
                bot.send_photo(chat_id, message.photo[-1].file_id, caption=body or None, reply_to_message_id=reply_mid)
            elif content_type == "video":
                bot.send_video(chat_id, message.video.file_id, caption=body or None, reply_to_message_id=reply_mid)
            elif content_type == "voice":
                bot.send_voice(chat_id, message.voice.file_id, caption=body or None, reply_to_message_id=reply_mid)
            elif content_type == "document":
                bot.send_document(chat_id, message.document.file_id, caption=body or None, reply_to_message_id=reply_mid)
            elif content_type == "audio":
                bot.send_audio(chat_id, message.audio.file_id, caption=body or None, reply_to_message_id=reply_mid)
            elif content_type == "sticker":
                bot.send_sticker(chat_id, message.sticker.file_id, reply_to_message_id=reply_mid)
        except Exception as e:
            logging.error(f"Reply as bot error: {e}")
        return

    # Қулфлар маркази буйруқлари:
    if is_user_admin and first_w in ["қулфлар", "созламалар", "замки", "настройки", "qulflar", "locks", "settings", "panel"]:
        delete_msg_safe(chat_id, message.message_id)
        show_locks_panel(chat_id, chat_id, message_id=None, lang="uz_kr")
        return

    # Тўлиқ очиш (ҳаммаси оч, очиш, och, unlock):
    if is_user_admin and first_w in ["очиш", "оч", "och", "ochish", "unlock", "open"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_links = 0, lock_forwards = 0, lock_spam = 0, lock_badwords = 0, lock_stickers = 0, lock_arabic = 0, lock_media = 0, lock_files = 0, lock_voice = 0, autolock_enabled = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        try:
            bot.set_chat_permissions(chat_id, get_full_chat_permissions())
        except Exception:
            pass
        n = bot.send_message(
            chat_id,
            "🔓 <b>Гуруҳ тўлиқ очилди!</b>\n\n"
            "✅ Видео, расм, файл, овозли хабарлар ва ёзишга тўлиқ рухсат берилди.\n"
            "Тунги қулф ўчирилди. Барча бемалол фойдаланиши мумкин!",
            parse_mode="HTML"
        )
        threading.Timer(15, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Видео ва медиани очиш/ёқиш: видео ёқ, video yoq, медиа ёқ, video och
    if is_user_admin and first_w in ["видео", "медиа", "video", "media"] and len(words) > 1 and words[1].lower() in ["ёқ", "оч", "очилсин", "рухсат", "yoq", "och", "on", "ruxsat"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_media = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        try:
            bot.set_chat_permissions(chat_id, get_full_chat_permissions())
            n = bot.send_message(chat_id, "🎬 <b>Гуруҳда видео, расм ва барча медиа юборишга рухсат берилди!</b> ✅", parse_mode="HTML")
            threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        except Exception as e:
            logging.error(f"Set video permissions error: {e}")
        return

    # Видео ва медиани ёпиш/ўчириш: видео ёп, video yop, медиа ёп, video ochir
    if is_user_admin and first_w in ["видео", "медиа", "video", "media"] and len(words) > 1 and words[1].lower() in ["ёп", "ўчир", "очир", "yop", "ochir", "off"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_media = 1 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        n = bot.send_message(chat_id, "🚫 <b>Гуруҳда видео ва медиа юбориш қулфланди.</b>", parse_mode="HTML")
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Файлларни очиш: файл оч, file och
    if is_user_admin and first_w in ["файл", "файлы", "file", "files"] and len(words) > 1 and words[1].lower() in ["оч", "ёқ", "рухсат", "och", "yoq", "on"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_files = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        try:
            bot.set_chat_permissions(chat_id, get_full_chat_permissions())
        except Exception:
            pass
        n = bot.send_message(chat_id, "📦 <b>Гуруҳда файл ва ҳужжатларга рухсат берилди!</b> ✅", parse_mode="HTML")
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Файлларни ёпиш: файл ёп, file yop
    if is_user_admin and first_w in ["файл", "файлы", "file", "files"] and len(words) > 1 and words[1].lower() in ["ёп", "ўчир", "yop", "ochir", "off"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_files = 1 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        n = bot.send_message(chat_id, "🚫 <b>Гуруҳда файл юбориш қулфланди.</b>", parse_mode="HTML")
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Овозли хабарларни очиш: овоз оч, voice och
    if is_user_admin and first_w in ["овоз", "голосовые", "voice", "audio"] and len(words) > 1 and words[1].lower() in ["оч", "ёқ", "рухсат", "och", "yoq", "on"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_voice = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        try:
            bot.set_chat_permissions(chat_id, get_full_chat_permissions())
        except Exception:
            pass
        n = bot.send_message(chat_id, "🎙 <b>Гуруҳда овозли хабарларга рухсат берилди!</b> ✅", parse_mode="HTML")
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Овозли хабарларни ёпиш: овоз ёп, voice yop
    if is_user_admin and first_w in ["овоз", "голосовые", "voice", "audio"] and len(words) > 1 and words[1].lower() in ["ёп", "ўчир", "yop", "ochir", "off"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET lock_voice = 1 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        n = bot.send_message(chat_id, "🚫 <b>Гуруҳда овозли хабарлар қулфланди.</b>", parse_mode="HTML")
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Тунги қулф (авто-қулф)ни ёқиш: тунги қулф ёқ, автоқулф ёқ, ночной замок вкл
    if is_user_admin and first_w in ["тунги", "автоқулф", "авто-қулф", "ночной"] and len(words) > 1 and words[1].lower() in ["ёқ", "йок", "yoq", "on", "вкл", "включить"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET autolock_enabled = 1 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        try:
            bot.set_chat_permissions(chat_id, get_full_chat_permissions())
        except Exception:
            pass
        g_cur = get_group(chat_id)
        s_t = g_cur.get("autolock_start_time", "23:00") if g_cur else "23:00"
        e_t = g_cur.get("autolock_end_time", "06:30") if g_cur else "06:30"
        n = bot.send_message(
            chat_id,
            f"🌙 <b>Тунги ақилли чеклов режими ёқилди!</b> ✅\n\n"
            f"Гуруҳ интерфейси тўлиқ очиқ туради (2-расм сингари), лекин соат <b>{s_t}</b> дан то <b>{e_t}</b> гача "
            f"барча юборилган ёзишмалар ва медиалар автоматик тарзда ўчирилади.",
            parse_mode="HTML"
        )
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Тунги қулфни ўчириш: тунги қулф ўчир, автоқулф ўчир, ночной замок выкл
    if is_user_admin and first_w in ["тунги", "автоқулф", "авто-қулф", "ночной"] and len(words) > 1 and words[1].lower() in ["ўчир", "очир", "ochir", "off", "выкл", "выключить", "оч", "och"]:
        delete_msg_safe(chat_id, message.message_id)
        cursor.execute("UPDATE groups SET autolock_enabled = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        try:
            bot.set_chat_permissions(chat_id, get_full_chat_permissions())
        except Exception:
            pass
        n = bot.send_message(
            chat_id,
            "🔓 <b>Тунги чеклов ўчирилди!</b> ✅\n\nЭнди кечаси ҳам хабарлар ўчирилмайди.",
            parse_mode="HTML"
        )
        threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Ўчириш: ўчир, ochir, del
    if is_user_admin and first_w in ["ўчир", "очир", "ochir", "del", "delete"]:
        if message.reply_to_message:
            delete_msg_safe(chat_id, message.reply_to_message.message_id)
        delete_msg_safe(chat_id, message.message_id)
        return

    # Закрепить: қада, када, qada, pin, закрепить
    if is_user_admin and first_w in ["қада", "када", "qada", "pin", "закрепить"]:
        delete_msg_safe(chat_id, message.message_id)
        try:
            if message.reply_to_message:
                bot.pin_chat_message(chat_id, message.reply_to_message.message_id)
                n = bot.send_message(chat_id, "📌 <b>Хабар қадаб қўйилди (Закреплен)!</b>", parse_mode="HTML")
                threading.Timer(5, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            elif len(words) > 1:
                pin_body = raw_txt[len(words[0]):].strip()
                sent = bot.send_message(chat_id, f"📌 <b>МУҲИМ ЭЪЛОН:</b>\n\n{pin_body}", parse_mode="HTML")
                bot.pin_chat_message(chat_id, sent.message_id)
        except Exception as e:
            logging.error(f"Pin error: {e}")
        return

    # Қадашни ечиш: еч, yech, unpin, открепить
    if is_user_admin and first_w in ["еч", "yech", "unpin", "открепить"]:
        delete_msg_safe(chat_id, message.message_id)
        try:
            bot.unpin_chat_message(chat_id)
            n = bot.send_message(chat_id, "📌 <b>Қадалган хабар ечилди.</b>", parse_mode="HTML")
            threading.Timer(5, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        except Exception:
            pass
        return

    # Мут қилиш: мут, mut, жим, mute
    if is_user_admin and first_w in ["мут", "mut", "жим", "mute"]:
        delete_msg_safe(chat_id, message.message_id)
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            duration_sec = 3600
            if len(words) > 1:
                t_str = words[1].lower()
                if t_str.endswith('m'):
                    duration_sec = int(t_str[:-1]) * 60
                elif t_str.endswith('h'):
                    duration_sec = int(t_str[:-1]) * 3600
                elif t_str.endswith('d'):
                    duration_sec = int(t_str[:-1]) * 86400
            try:
                until = int(time.time()) + duration_sec
                bot.restrict_chat_member(chat_id, target_user.id, until_date=until, can_send_messages=False)
                u_tag = f"@{target_user.username}" if target_user.username else target_user.first_name
                n = bot.send_message(chat_id, f"🤐 <b>{u_tag}</b> қоидабузарлик сабабли <b>МУТ</b> қилинди!", parse_mode="HTML")
                threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            except Exception:
                pass
        return

    # Мутдан чиқариш: унмут, unmut, unmute
    if is_user_admin and first_w in ["унмут", "unmut", "unmute"]:
        delete_msg_safe(chat_id, message.message_id)
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            lift_user_mute(chat_id, target_user.id)
            cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (chat_id, target_user.id))
            conn.commit()
            u_tag = f"@{target_user.username}" if target_user.username else target_user.first_name
            n = bot.send_message(chat_id, f"🔊 <b>{u_tag}</b> мутдан чиқарилди ва ёзишга тўлиқ рухсат берилди! ✅", parse_mode="HTML")
            threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
        return

    # Бан қилиш: бан, ban, ҳайда, hayda
    if is_user_admin and first_w in ["бан", "ban", "ҳайда", "hayda", "kick"]:
        delete_msg_safe(chat_id, message.message_id)
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            try:
                bot.ban_chat_member(chat_id, target_user.id)
                u_tag = f"@{target_user.username}" if target_user.username else target_user.first_name
                n = bot.send_message(chat_id, f"🚫 <b>{u_tag}</b> гуруҳдан чиқарилди ва блокланди!", parse_mode="HTML")
                threading.Timer(10, lambda: delete_msg_safe(chat_id, n.message_id)).start()
            except Exception:
                pass
        return

    g = get_group(chat_id)
    if not g:
        return

    g_lang = g.get("lang", "uz_kr")

    # ==================== ТУНГИ АВТО-ҚУЛФ ТЕКШИРУВИ (2-РАСМДАГИДЕК ОЧИҚ ҲОЛАТДА ЎЧИРИШ) ====================
    if not is_user_admin and is_autolock_active_now(g):
        delete_msg_safe(chat_id, message.message_id)
        now_ts = time.time()
        last_warn = _last_autolock_user_warn.get(user_id, 0)
        if now_ts - last_warn > 120:
            _last_autolock_user_warn[user_id] = now_ts
            s_time = g.get("autolock_start_time", "23:00")
            e_time = g.get("autolock_end_time", "06:30")
            u_name = html.escape(str(message.from_user.first_name if message.from_user else "Фойдаланувчи"))
            try:
                warn_msg = bot.send_message(
                    chat_id,
                    f"🌙 <b>Ҳурматли {u_name}!</b>\n\n"
                    f"Гуруҳда тунги чеклов вақти (соат <b>{s_time}</b> дан то <b>{e_time}</b> гача).\n"
                    f"Ушбу вақт оралиғида барча юборилган хабар ва ёзишмалар автоматик тарзда ўчирилади.\n"
                    f"<i>Илтимос, эрталаб соат {e_time} гача кутинг.</i>",
                    parse_mode="HTML"
                )
                threading.Timer(6, lambda: delete_msg_safe(chat_id, warn_msg.message_id)).start()
            except Exception:
                pass
        return

    # ==================== МАЖБУРИЙ ОБУНА ТЕКШИРУВИ ====================
    if not is_user_admin and g.get("forcesub_enabled", 0) == 1:
        # 1. Агар "Фақат янги аъзолар учун" ёқилган бўлса (дефолт ҳолатда), эски аъзоларга тегмаймиз:
        should_check_user = True
        if g.get("forcesub_only_new", 1) == 1:
            cursor.execute("SELECT 1 FROM new_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            if not cursor.fetchone():
                # Эски аъзо - текширилмайди ва чеклов қўйилмайди
                should_check_user = False

        if should_check_user:
            channel = clean_channel_username(g.get("forcesub_channel", "@uz_asalarichilik"))
            is_sub, missing = check_user_channels_subscription(channel, user_id)
            if is_sub:
                cursor.execute("INSERT OR REPLACE INTO forcesub_verified (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
                conn.commit()
            else:
                # Каналдан чиқиб кетган ёки ҳали аъзо бўлмаган:
                cursor.execute("DELETE FROM forcesub_verified WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
                conn.commit()
                delete_msg_safe(chat_id, message.message_id)
                try:
                    bot.restrict_chat_member(
                        chat_id,
                        user_id,
                        permissions=types.ChatPermissions(
                            can_send_messages=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False
                        )
                    )
                except Exception as re:
                    logging.warning(f"Restrict user {user_id} error: {re}")

                now_ts = time.time()
                warn_key = (chat_id, user_id)
                if now_ts - _last_forcesub_user_warn.get(warn_key, 0) > 10:
                    _last_forcesub_user_warn[warn_key] = now_ts
                    u_name = html.escape(str(message.from_user.first_name if message.from_user else "Фойдаланувчи"))
                    u_mention = f"<a href='tg://user?id={user_id}'>{u_name}</a>"

                    sub_markup = InlineKeyboardMarkup()
                    for m_ch in (missing if missing else [channel]):
                        c_clean = m_ch.replace("@", "")
                        sub_markup.row(InlineKeyboardButton(f"📢 {m_ch} каналига аъзо бўлиш", url=f"https://t.me/{c_clean}"))
                    sub_markup.row(InlineKeyboardButton("✅ Текшириш (Аъзо бўлдим)", callback_data=f"check_sub_{chat_id}_{user_id}"))
                    sub_markup.row(InlineKeyboardButton("🤖 Бот орқали мутдан чиқиш", url=f"https://t.me/{BOT_USERNAME}?start=unmute_{chat_id}"))

                    mode_hint = "Обунадан сўнг админ тасдиғи керак." if g.get("approval_enabled", 0) == 1 else "Каналга аъзо бўлгач «Аъзо бўлдим» тугмасини босинг — ёзиш чеклов дарҳол олиб ташланади."
                    warn_txt = (
                        f"⛔️ Ҳурматли <b>{u_mention}</b>!\n\n"
                        f"Гуруҳда хабар ёзиш учун аввал расмий каналимизга аъзо бўлишингиз шарт:\n"
                        f"📢 <b>{channel}</b>\n\n"
                        f"<i>({mode_hint})</i>\n\n"
                        f"Каналга обуна бўлгач, пастдаги <b>«✅ Текшириш (Аъзо бўлдим)»</b> тугмасини босинг."
                    )
                    w_msg = bot.send_message(chat_id, warn_txt, reply_markup=sub_markup, parse_mode="HTML")

                    # Автоматик гуруҳдан ўчириш (60 сонияда ёки админ танлаган вақтда):
                    timer_sec = (g.get("forcesub_timer_min", 0) * 60) if g.get("forcesub_timer_min", 0) > 0 else 60
                    threading.Timer(timer_sec, lambda: delete_msg_safe(chat_id, w_msg.message_id)).start()
                return

    # ==================== ҚУЛФЛАР МАРКАЗИ ТЕКШИРУВЛАРИ ВА 2-РАСМДАГИДЕК ОГОҲЛАНТИРИШЛАР ====================

    # 1. ҲАВОЛАЛАР (ССЫЛКА), ТЕЛЕГРАМ ЮЗЕРНЕЙМЛАР ВА КОНТАКТЛАР ҚУЛФИ (lock_links)
    if not is_user_admin and (g.get("lock_links", 1) == 1 or g.get("lock_spam", 1) == 1):
        is_link_violation = False
        all_ents = (message.entities or []) + (message.caption_entities or [])
        for ent in all_ents:
            if ent.type in ['url', 'text_link']:
                url_val = getattr(ent, 'url', '') or raw_txt[ent.offset : ent.offset + ent.length]
                if is_whitelisted_entity_or_url(url_val):
                    continue
                is_link_violation = True
                break
            elif ent.type == 'mention':
                m_val = raw_txt[ent.offset : ent.offset + ent.length].lower()
                if is_whitelisted_entity_or_url(m_val):
                    continue
                is_link_violation = True
                break
            elif ent.type == 'text_mention':
                if ent.user and (ent.user.id == bot.get_me().id or ent.user.id in [777000, 1087968824, 136817688, OWNER_ID]):
                    pass
                else:
                    is_link_violation = True
                    break

        if not is_link_violation:
            link_regex = (
                r'(https?://[^\s]+|'
                r'(?:t|telegram)\.(?:me|dog)/[^\s]+|'
                r'tg://[^\s]+|'
                r'@[a-zA-Z0-9_]{4,}|'
                r'(?:[a-zA-Z0-9-]+\.)+(?:uz|com|ru|net|org|io|me|info|biz|site|co|link|app|xyz|online|pro|top|club|shop|live|store|vip|tech)\b)'
            )
            found_matches = re.findall(link_regex, raw_txt, re.IGNORECASE)
            for m_match in found_matches:
                if is_whitelisted_entity_or_url(m_match):
                    continue
                is_link_violation = True
                break

        if not is_link_violation and (content_type == 'contact' or getattr(message, 'contact', None) is not None):
            is_link_violation = True

        if is_link_violation:
            delete_msg_safe(chat_id, message.message_id)
            send_lock_violation_warning(chat_id, message.from_user, "ҳавола ва телеграм юзернейм", "ссылок и юзернеймов", g_lang)
            return

    # 2. ФОРВАРДЛАР (ҚАЙТА ЮБОРИЛГАН ХАБАРЛАР) ҚУЛФИ (lock_forwards)
    is_fwd = bool(
        message.forward_from or 
        message.forward_from_chat or 
        getattr(message, 'forward_origin', None) or 
        getattr(message, 'forward_date', None)
    )
    if not is_user_admin and g.get("lock_forwards", 1) == 1 and is_fwd:
        delete_msg_safe(chat_id, message.message_id)
        send_lock_violation_warning(chat_id, message.from_user, "қайта юборилган (forward) хабар", "пересланных сообщений (forward)", g_lang)
        return

    # 3. СТИКЕРЛАР ВА АНИМАЦИОН СТИКЕРЛАР ҚУЛФИ (lock_stickers)
    is_sticker = (content_type == 'sticker' or getattr(message, 'sticker', None) is not None)
    if not is_user_admin and g.get("lock_stickers", 0) == 1 and is_sticker:
        delete_msg_safe(chat_id, message.message_id)
        st = getattr(message, 'sticker', None)
        is_anim = bool(st and (getattr(st, 'is_animated', False) or getattr(st, 'is_video', False)))
        v_uz = "анимацион стикер" if is_anim else "стикер"
        v_ru = "анимированных стикеров" if is_anim else "стикеров"
        send_lock_violation_warning(chat_id, message.from_user, v_uz, v_ru, g_lang)
        return

    # 4. МЕДИА (ВИДЕО, РАСМ, GIF) ҚУЛФИ (lock_media)
    if not is_user_admin and g.get("lock_media", 0) == 1 and content_type in ['photo', 'video', 'animation', 'video_note']:
        delete_msg_safe(chat_id, message.message_id)
        send_lock_violation_warning(chat_id, message.from_user, "видео ва расм", "фото и видео", g_lang)
        return

    # 5. ФАЙЛЛАР ВА ҲУЖЖАТЛАР (APK, ZIP, PDF) ҚУЛФИ (lock_files)
    if not is_user_admin and g.get("lock_files", 0) == 1 and content_type == 'document':
        delete_msg_safe(chat_id, message.message_id)
        send_lock_violation_warning(chat_id, message.from_user, "файл ва ҳужжат", "файлов и документов", g_lang)
        return

    # 6. ОВОЗЛИ ХАБАРЛАР ВА АУДИО ҚУЛФИ (lock_voice)
    if not is_user_admin and g.get("lock_voice", 0) == 1 and content_type in ['voice', 'audio', 'video_note']:
        delete_msg_safe(chat_id, message.message_id)
        send_lock_violation_warning(chat_id, message.from_user, "овозли хабар", "голосовых сообщений", g_lang)
        return

    # 7. АРАБЧА ЁЗУВЛАР ҚУЛФИ (lock_arabic)
    arabic_regex = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
    has_arabic = bool(re.search(arabic_regex, raw_txt))
    if not is_user_admin and g.get("lock_arabic", 1) == 1 and has_arabic:
        delete_msg_safe(chat_id, message.message_id)
        send_lock_violation_warning(chat_id, message.from_user, "арабча ёзувлар", "арабского текста", g_lang)
        return

    # 8. СЎКИНИШ ВА ҲАҚОРАТЛАР ҚУЛФИ (lock_badwords)
    if not is_user_admin and g.get("lock_badwords", 1) == 1:
        text_full = raw_txt.lower()
        bad_words = ["jalap", "qotoq", "sikay", "am", "blya", "naxuy", "suka", "далбаеб", "бля", "нахуй", "сука", "гандон", "пидараз", "куток", "сикаман"]
        if any(w in text_full for w in bad_words):
            delete_msg_safe(chat_id, message.message_id)
            send_lock_violation_warning(chat_id, message.from_user, "ҳақоратли ва беодоб сўзлар", "нецензурных выражений", g_lang)
            return

    # 9. СПАМ ҚУЛФИ (lock_spam)
    if not is_user_admin and g.get("lock_spam", 1) == 1:
        if len(raw_txt) > 250 and len(set(raw_txt)) < 15:
            delete_msg_safe(chat_id, message.message_id)
            send_lock_violation_warning(chat_id, message.from_user, "спам ва реклама", "спама и рекламы", g_lang)
            return

    # 10. БЕГОНА ДИНИЙ ВА ДУНЁВИЙ ХАБАРЛАРНИ ЧЕКЛАШ
    if not is_user_admin and is_unrelated_offtopic_post(raw_txt):
        delete_msg_safe(chat_id, message.message_id)
        send_lock_violation_warning(chat_id, message.from_user, "диний занжир ва мавзудан ташқари спам", "сообщений не по теме пчеловодства", g_lang)
        return

    # ==================== 5. МЕДИА ЛИМИТ: 3 ТАДАН ОРТИҚ РАСМ/ВИДЕО ТАҚИҚИ, АЛЬБОМЛАР НАЗОРАТИ ВА 24 СОАТЛИК МУТ ====================
    # Расм, видео, видеохабар, анимация ёки файл кўринишида юборилган сурат/видеолар (Xiaomi File Explorer ва ҳ.к.)
    is_doc_media = False
    if content_type == 'document' and message.document:
        doc_mime = (getattr(message.document, 'mime_type', '') or '').lower()
        doc_name = (getattr(message.document, 'file_name', '') or '').lower()
        if doc_mime.startswith(('image/', 'video/')) or doc_name.endswith(('.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi', '.mkv')):
            is_doc_media = True

    is_media_check = (content_type in ["photo", "video", "video_note", "animation"]) or is_doc_media

    if is_media_check:
        l_en = (g.get("limit_enabled", 1) == 1)
        if l_en and not is_user_admin:
            limit_max = g.get("limit_max", 3) or 3
            today_str = get_now(5).strftime("%Y-%m-%d")
            now_ts = int(time.time())
            mg_id = getattr(message, 'media_group_id', None)

            with _media_lock:
                cursor.execute(
                    "SELECT count, ad_date, warn_count, last_warn_ts FROM user_bee_ad_limits WHERE chat_id = ? AND user_id = ?",
                    (chat_id, user_id)
                )
                row = cursor.fetchone()
                curr_media_cnt = row["count"] if (row and row["ad_date"] == today_str) else 0
                warn_cnt = row["warn_count"] if (row and "warn_count" in row and row["warn_count"] is not None) else 0
                last_warn_time = row["last_warn_ts"] if (row and "last_warn_ts" in row and row["last_warn_ts"] is not None) else 0

                # Альбом (media_group_id) бўйича ва кунлик ҳисоблаш
                if mg_id:
                    album_key = (chat_id, mg_id)
                    album_cnt = _media_group_tracker.get(album_key, 0) + 1
                    _media_group_tracker[album_key] = album_cnt
                else:
                    album_cnt = 1

                total_cnt = curr_media_cnt + 1

                cursor.execute(
                    "INSERT OR REPLACE INTO user_bee_ad_limits (chat_id, user_id, count, ad_date, warn_count, last_warn_ts) VALUES (?, ?, ?, ?, ?, ?)",
                    (chat_id, user_id, total_cnt, today_str, warn_cnt, last_warn_time)
                )
                conn.commit()

            # Агар альбомда ёки кун давомида белгиланган лимитдан ортиқ расм/видео юборилса:
            is_excess = (mg_id and album_cnt > limit_max) or total_cnt > limit_max
            if is_excess:
                # Ортиқча расмни дарҳол гуруҳдан ўчирамиз!
                delete_msg_safe(chat_id, message.message_id)

                is_repeat_within_24h = (warn_cnt >= 1 and (now_ts - last_warn_time) < 86400)
                # Агар фойдаланувчи 24 соат ичида қайта ташласа ёки бир вақтда лимитдан ортиқ (4 ва ундан кўп) ташласа: ДАРҲОЛ 24 СОАТЛИК МУТ!
                should_mute = is_repeat_within_24h or (mg_id and album_cnt >= (limit_max + 1)) or (total_cnt >= (limit_max + 1))

                if should_mute:
                    try:
                        until_ts = int(time.time() + 86400)
                        if user_id < 0:
                            # Агар бегона канал номи билан юборилган бўлса — канални гуруҳдан блоклаймиз
                            try:
                                bot.ban_chat_sender_chat(chat_id, user_id)
                            except Exception as ce:
                                logging.error(f"Ban sender chat {user_id} error: {ce}")
                        else:
                            restrict_perms = types.ChatPermissions(
                                can_send_messages=False,
                                can_send_media_messages=False,
                                can_send_audios=False,
                                can_send_documents=False,
                                can_send_photos=False,
                                can_send_videos=False,
                                can_send_video_notes=False,
                                can_send_voice_notes=False,
                                can_send_polls=False,
                                can_send_other_messages=False,
                                can_add_web_page_previews=False
                            )
                            try:
                                bot.restrict_chat_member(chat_id, user_id, until_date=until_ts, permissions=restrict_perms, use_independent_chat_permissions=True)
                            except Exception:
                                bot.restrict_chat_member(chat_id, user_id, until_date=until_ts, permissions=restrict_perms)
                    except Exception as me:
                        logging.error(f"Failed to 24h mute user {user_id}: {me}")

                    last_m = _last_media_warn.get(f"m_{user_id}", 0)
                    if now_ts - last_m > 10:
                        _last_media_warn[f"m_{user_id}"] = now_ts
                        mute_txt = (
                            f"🚫 <b>Ҳурматли {u_tag}!</b>\n\n"
                            f"Гуруҳимизда белгиланган <b>кўпи билан {limit_max} талик расм ва видео</b> лимити бузилди (бирданига ортиқча медиалар ташланди)!\n\n"
                            f"⚖️ Қоидабузарлик сабабли сизга <b>24 соатлик (1 кунлик) ТЎЛИҚ МУТ</b> берилди (гуруҳга умуман ёза олмайсиз ва медиа юбора олмайсиз)!\n\n"
                            f"❌ Белгиланган {limit_max} тадан ортиқча ташланган барча расм ва видеолар автоматик тарзда ўчирилди."
                        )
                        m_msg = bot.send_message(chat_id, mute_txt, parse_mode="HTML")
                        del_sec = max(g.get("limit_notice_del", 60), 60)
                        threading.Timer(del_sec, lambda: delete_msg_safe(chat_id, m_msg.message_id)).start()
                    return

                else:
                    # Биринчи қоидабузарлик: ортиқчасини ўчириш ва расмий огоҳлантириш бериш
                    with _media_lock:
                        cursor.execute(
                            "UPDATE user_bee_ad_limits SET warn_count = 1, last_warn_ts = ? WHERE chat_id = ? AND user_id = ?",
                            (now_ts, chat_id, user_id)
                        )
                        conn.commit()

                    if mg_id:
                        _media_album_warned[(chat_id, mg_id)] = True

                    last_w = _last_media_warn.get(user_id, 0)
                    if now_ts - last_w > 5:
                        _last_media_warn[user_id] = now_ts
                        warn_txt = (
                            f"⚠️ <b>ОГОҲЛАНТИРИШ! Ҳурматли {u_tag}!</b>\n\n"
                            f"Гуруҳимизда белгиланган қоида бўйича бир вақтнинг ўзида (ёки бир кунда) кўпи билан <b>{limit_max} тагина расм ва видео</b> юбориш мумкин!\n\n"
                            f"❌ Сиз {limit_max} тадан ортиқ ({album_cnt if mg_id else total_cnt}-чи) расм/видео юбордингиз. Белгиланган {limit_max} тадан ортиқча ташланганлари автоматик тарзда ўчирилди.\n\n"
                            f"⚖️ <i>Илтимос, гуруҳга ортиқча расм ва видеолар ташламанг! Агар яна ортиқча расм ёки видео ташласангиз, дарҳол 1 кунлик (24 соатлик) МУТ берилади.</i>"
                        )
                        w_msg = bot.send_message(chat_id, warn_txt, parse_mode="HTML")
                        del_sec = max(g.get("limit_notice_del", 60), 60)
                        threading.Timer(del_sec, lambda: delete_msg_safe(chat_id, w_msg.message_id)).start()
                    return
            return

    # ==================== 6. АСАЛАРИЧИЛИК САВОЛЛАРИГА ЖАВОБ (ФАҚАТ МАТНЛИ САВОЛЛАР УЧУН) ====================
    is_commercial_bee_post = is_beekeeping_commercial_post(raw_txt)
    if is_commercial_bee_post:
        return

    is_bee = is_beekeeping_related_text(raw_txt)
    has_q = ("?" in raw_txt) or any(w in raw_txt.lower() for w in QUESTION_WORDS)
    is_reply_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot.get_me().id)
    is_mention_bot = bool(BOT_USERNAME and f"@{BOT_USERNAME.lower()}" in raw_txt.lower())
    has_disease_words = any(w in raw_txt.lower() for w in DISEASE_SYMPTOM_WORDS)

    is_doctor_request = (
        is_reply_to_bot or
        is_mention_bot or
        (has_disease_words and (has_q or len(raw_txt) > 25))
    )

    if not is_commercial_bee_post and is_doctor_request:
        try:
            bot.send_chat_action(chat_id, 'typing')
            doc_answer = analyze_bee_disease_or_question(raw_txt)
            if doc_answer and doc_answer != "COMMERCIAL":
                bot.reply_to(message, doc_answer, parse_mode="HTML")
                return
        except Exception as e:
            logging.error(f"Bee doctor online answer error: {e}")

    # ==================== 8. НОМАҚБУЛ ХАБАРЛАР НАЗОРАТИ ====================
    # Расм, видео, файл ва оддий мулоқот гуруҳда тўлиқ рухсат этилади!
    # Фақатгина аниқ диний занжир спам хабарлар чекланади:
    if not is_user_admin and is_unrelated_offtopic_post(raw_txt):
        delete_msg_safe(chat_id, message.message_id)
        warn_text = (
            f"⚠️ Ҳурматли <b>{u_tag}</b>! Илтимос, бу асаларичилик гуруҳи! "
            f"Диний занжир ва бегона спам хабарлар тарқатманг илтимос!"
        )
        w_msg = bot.send_message(chat_id, warn_text, parse_mode="HTML")
        threading.Timer(45, lambda: delete_msg_safe(chat_id, w_msg.message_id)).start()
        return


# 15. ФОН РЕЖИМИДАГИ ИШЛАР (ОБ-ҲАВО ВА ТУНГИ ҚУЛФЛАР)
_last_weather_sent = {}
_last_autolock_state = {}

def autolock_and_weather_worker():
    while True:
        try:
            cursor.execute("SELECT * FROM groups WHERE is_authorized = 1")
            active_groups = cursor.fetchall()
            for grp in active_groups:
                gid = grp["chat_id"]
                tz_offset = grp.get("timezone_offset", 5) or 5
                group_now = get_now(tz_offset)
                curr_hm = group_now.strftime("%H:%M")
                today_str = group_now.strftime("%Y-%m-%d")
                today_iso_weekday = str(group_now.isoweekday())

                # 1. Об-ҳаво хабарини юбориш
                if grp.get("weather_enabled", 1) == 1:
                    w_time = grp.get("weather_time", "08:00")
                    repeat_days = [d.strip() for d in grp.get("weather_repeat_days", "1,2,3,4,5,6,7").split(",")]
                    if curr_hm == w_time and today_iso_weekday in repeat_days:
                        key = f"w_{gid}_{today_str}"
                        if key not in _last_weather_sent:
                            _last_weather_sent[key] = True
                            send_weather_to_group(gid, lang=grp.get("lang", "uz_kr"))

                # 2. Тунги авто-қулфлаш (Тунги вақтда гуруҳ ёзишга тўлиқ қулфланади, эрталаб очилади)
                if grp.get("autolock_enabled", 0) == 1:
                    s_time = normalize_hm(grp.get("autolock_start_time", "23:00"), "23:00")
                    e_time = normalize_hm(grp.get("autolock_end_time", "06:30"), "06:30")
                    
                    # 1. Тунги қулф бошланиш вақти:
                    if curr_hm == s_time:
                        key_l = f"lock_{gid}_{today_str}_{s_time}"
                        if key_l not in _last_autolock_state:
                            _last_autolock_state[key_l] = True
                            try:
                                # Гуруҳда ёзишни қулфлаймиз (can_send_messages=False)
                                bot.set_chat_permissions(gid, types.ChatPermissions(can_send_messages=False))
                                start_custom = grp.get("autolock_start_msg")
                                if start_custom and start_custom.strip():
                                    start_text = start_custom.replace("{group}", grp.get("title", "")).replace("{start_time}", s_time).replace("{end_time}", e_time)
                                else:
                                    start_text = (
                                        f"🌙 <b>Гуруҳда тунги чеклов бошланди!</b>\n\n"
                                        f"Соат <b>{s_time}</b> дан то <b>{e_time}</b> гача гуруҳда ёзиш вақтинча тўхтатилди. "
                                        f"Эрталаб соат {e_time} да гуруҳ автоматик очилади.\n\n"
                                        f"Ҳурмат билан админ 👨‍💼"
                                    )
                                bot.send_message(gid, start_text, parse_mode="HTML")
                            except Exception as e:
                                logging.error(f"Autolock start announcement error: {e}")
                                
                    # 2. Эрталабки очилиш вақти:
                    elif curr_hm == e_time:
                        key_u = f"unlock_{gid}_{today_str}_{e_time}"
                        if key_u not in _last_autolock_state:
                            _last_autolock_state[key_u] = True
                            try:
                                # Гуруҳни тўлиқ очамиз!
                                bot.set_chat_permissions(gid, get_full_chat_permissions())
                                end_custom = grp.get("autolock_end_msg")
                                if end_custom and end_custom.strip():
                                    end_text = end_custom.replace("{group}", grp.get("title", "")).replace("{end_time}", e_time)
                                else:
                                    end_text = (
                                        f"☀️ <b>Кунингиз хайрли ва баракали бўлсин!</b>\n\n"
                                        f"Гуруҳда тунги чеклов якунланди. Гуруҳ мулоқот ва савол-жавоб учун тўлиқ очилди! ✅"
                                    )
                                bot.send_message(gid, end_text, parse_mode="HTML")
                            except Exception as e:
                                logging.error(f"Autolock end announcement error: {e}")
        except Exception as e:
            logging.error(f"Worker error: {e}")

        # 3. Кунлик асаларичилик викторина/сўровномаси (Автоматлаштирилган жадвал бўйича)
        try:
            q_cfg = get_global_quiz_config()
            if q_cfg and q_cfg.get("enabled", 1) == 1:
                q_time = q_cfg.get("send_time", "10:00")
                q_days = [d.strip() for d in (q_cfg.get("repeat_days") or "1,2,3,4,5,6,7").split(",")]
                q_now = get_now(5)
                q_curr_hm = q_now.strftime("%H:%M")
                q_today_str = q_now.strftime("%Y-%m-%d")
                q_iso_weekday = str(q_now.isoweekday())

                if q_curr_hm == q_time and q_iso_weekday in q_days:
                    last_sent = q_cfg.get("last_sent_date")
                    if last_sent != q_today_str:
                        update_global_quiz_config(last_sent_date=q_today_str)
                        logging.info("Automated daily bee quiz poll triggered.")
                        publish_quiz_poll()
        except Exception as eq:
            logging.error(f"Quiz automated worker error: {eq}")

        time.sleep(25)

threading.Thread(target=autolock_and_weather_worker, daemon=True).start()

# 16. Сервер соғломлик сервери
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - Asalarichilik Bot is running!")

    def log_message(self, format, *args):
        pass

def run_health_server():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logging.info(f"Health check HTTP server {port}-портда ишга тушди.")
        server.serve_forever()
    except Exception as e:
        logging.warning(f"Health server огоҳлантириши: {e}")

if "PORT" in os.environ:
    threading.Thread(target=run_health_server, daemon=True).start()

if __name__ == "__main__":
    try:
        threading.Thread(target=setup_bot_commands, daemon=True).start()
    except Exception:
        pass
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as we:
        logging.info(f"delete_webhook note: {we}")
    print(f"🐝 {BOT_NAME} ишга тушди! (@{BOT_USERNAME})")
    poll_failures = 0
    proxy_turn = 0
    while True:
        try:
            # timeout=5 ва long_polling_timeout=5 PythonAnywhere 503 Tunnel connection failed хатосини 100% тўхтатади!
            bot.polling(none_stop=True, interval=1, timeout=5, long_polling_timeout=5, skip_pending=True)
            poll_failures = 0
        except Exception as e:
            err_msg = str(e)
            poll_failures += 1
            if "Conflict" in err_msg or "409" in err_msg:
                logging.error("❌ 409 КОНФЛИКТ: Ботнинг бошқа бир нусхаси аллақачон ишлаяпти! Эски жараённи тўхтатинг: pkill -9 -f bot.py")
                time.sleep(5)
            elif "503" in err_msg or "ProxyError" in err_msg or "Max retries exceeded" in err_msg:
                logging.warning(f"⚠️ PythonAnywhere 503 прокси хатолиги: {e}. Сессия қайта тикланмоқда...")
                try:
                    if hasattr(apihelper, '_session'):
                        apihelper._session = None
                    if hasattr(apihelper, 'session'):
                        apihelper.session = None
                except Exception:
                    pass
                proxy_turn += 1
                if proxy_turn % 2 == 1:
                    apihelper.proxy = {'http': 'http://proxy.eu.pythonanywhere.com:3128', 'https': 'http://proxy.eu.pythonanywhere.com:3128'}
                    logging.info("🔄 Прокси PythonAnywhere EU га ўтказилди: http://proxy.eu.pythonanywhere.com:3128")
                else:
                    apihelper.proxy = {'http': 'http://proxy.server:3128', 'https': 'http://proxy.server:3128'}
                    logging.info("🔄 Прокси PythonAnywhere US га ўтказилди: http://proxy.server:3128")
                time.sleep(2)
            else:
                logging.error(f"Polling хатолиги ({poll_failures}-марта): {e}")
                if poll_failures >= 3:
                    logging.info("🔄 Тармоқ қайта созланмоқда...")
                    configure_network()
                    poll_failures = 0
                time.sleep(3)
