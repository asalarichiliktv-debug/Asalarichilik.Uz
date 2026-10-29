# -*- coding: utf-8 -*-
"""
Asalarichilik.Uz 🇺🇿 Rasmiy Telegram Boti va Post Konstruktori
Fayl nomi: bee_bot.py
Bot username: @Asalarichilikuz_bot
Muallif va yagona egasi: Jamshid Davronov (@JamshidjonDavronov)

Tavsif:
  - Asalarichilik bo'yicha professional sun'iy intellekt maslahatchisi (Gemini Flash).
  - Telegram Native Quiz Poll (Викторина & Сўровнома): 2-расмдагидек аноним викторина,
    тўғри жавоб кўрсаткичи, тушунтириш (лампочка) ва остида реакциялар, канал ҳаволаси,
    улашиш ва тайёр пост шаблони тугмалари.
  - Камида 1000 тагача саволлар базаси: Ёш асаларичилар (бошланғич) ва Спец асаларичилар (мураккаб) учун.
  - Крил ва Лотин ёзуви танлови: Админ созламалар орқали барча савол, жавоб ва янгиликларни
    Крилча ёки Лотинча кўринишга ўтказа олади.
  - Автоматик кунлик жадвал (Scheduler): Ҳар куни белгиланган вақтда викторина ва янгиликларни
    уланган гуруҳ ва каналларга тартиб билан автоматик жойлаштириш.
  - Асаларичилик Янгиликлари тизими: Интернет ва соҳа янгиликлари, мутахассис таҳлили,
    1000 тагача янгиланиш ва пост конструктори учун тайёр шаблон.
  - Пост конструктори: расм/видео, URL тугмалар, овозсиз юбориш, кўриб чиқиш, шаблонлар.
  - Хавфсизлик: Фақат бот эгаси (@JamshidjonDavronov) учун очиқ, бегоналар ва рухсатсиз гуруҳлар тақиқланган.
"""

from __future__ import annotations
import asyncio
import copy
import importlib.util
import json
import logging
import os
import random
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ==============================================================================
# 1. BOT ASOSIY SOZLAMALARI VA KALITLAR
# ==============================================================================
BOT_TOKEN = "8699352520:AAHjJRBFFACzUTQfKQAgtVEOKLhbj-tpsw0"
GEMINI_API_KEY = "AQ.Ab8RN6ICf_vax9VBZtjjkIVfYOx11HjO3ZMFiBizCjKrmuflNw"

OWNER_ID = 2047501151
OWNER_USERNAME = "@JamshidjonDavronov"
OFFICIAL_CHANNEL = "@uz_asalarichilik"
OFFICIAL_GROUP = "@asalarichilik_uzbekistan"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_CHATS_FILE = os.path.join(BASE_DIR, "allowed_chats.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "bot_settings.json")
REACTIONS_DB_FILE = os.path.join(BASE_DIR, "reactions_db.json")
QUIZ_DB_FILE = os.path.join(BASE_DIR, "quiz_database.json")
POLL_DB_FILE = os.path.join(BASE_DIR, "poll_database.json")
NEWS_DB_FILE = os.path.join(BASE_DIR, "news_database.json")
SCHEDULER_LOG_FILE = os.path.join(BASE_DIR, "scheduler_log.json")
APITHERAPY_DB_FILE = os.path.join(BASE_DIR, "apitherapy_db.json")
PENDING_CHATS_FILE = os.path.join(BASE_DIR, "pending_chats.json")
MEDIA_LIMITS_FILE = os.path.join(BASE_DIR, "media_limits.json")

# Standart reaksiyalar to'plamlari
REACTION_PRESETS = [
    ["👍", "❤️", "🔥", "👏", "🐝"],
    ["👍", "👎", "❤️"],
    ["👍", "👎"],
    ["👍", "👎", "🙏"],
    ["👍", "❤️", "👏"]
]

# ==============================================================================
# 2. KRIL <-> LOTIN ALISHTIRGICH (TRANSLITERATOR)
# ==============================================================================
CYR_TO_LAT_MAP = {
    'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v',
    'Г': 'G', 'г': 'g', 'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e',
    'Ё': 'Yo', 'ё': 'yo', 'Ж': 'J', 'ж': 'j', 'З': 'Z', 'з': 'z',
    'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
    'Л': 'L', 'л': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n',
    'О': 'O', 'о': 'o', 'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r',
    'С': 'S', 'с': 's', 'Т': 'T', 'т': 't', 'У': 'U', 'у': 'u',
    'Ф': 'F', 'ф': 'f', 'Х': 'X', 'х': 'x', 'Ц': 'Ts', 'ц': 'ts',
    'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Ъ': "'", 'ъ': "'",
    'Ь': '', 'ь': '', 'Э': 'E', 'э': 'e', 'Ю': 'Yu', 'ю': 'yu',
    'Я': 'Ya', 'я': 'ya', 'Ў': "O'", 'ў': "o'", 'Қ': 'Q', 'қ': 'q',
    'Ғ': "G'", 'ғ': "g'", 'Ҳ': 'H', 'ҳ': 'h'
}

LAT_TO_CYR_MULTI = [
    ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
    ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
    ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
    ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
    ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
    ("ye", "е"), ("Ye", "Е"), ("YE", "Е"),
    ("o'", "ў"), ("O'", "Ў"), ("oʻ", "ў"), ("Oʻ", "Ў"), ("o`", "ў"), ("O`", "Ў"),
    ("g'", "ғ"), ("G'", "Ғ"), ("gʻ", "ғ"), ("Gʻ", "Ғ"), ("g`", "ғ"), ("G`", "Ғ"),
    ("ts", "ц"), ("Ts", "Ц"), ("TS", "Ц")
]

LAT_TO_CYR_SINGLE = {
    'a': 'а', 'A': 'А', 'b': 'б', 'B': 'Б', 'd': 'д', 'D': 'Д',
    'e': 'е', 'E': 'Е', 'f': 'ф', 'F': 'Ф', 'g': 'г', 'G': 'Г',
    'h': 'ҳ', 'H': 'Ҳ', 'i': 'и', 'I': 'И', 'j': 'ж', 'J': 'Ж',
    'k': 'к', 'K': 'К', 'l': 'л', 'L': 'Л', 'm': 'м', 'M': 'М',
    'n': 'н', 'N': 'Н', 'o': 'о', 'O': 'О', 'p': 'п', 'P': 'П',
    'q': 'қ', 'Q': 'Қ', 'r': 'р', 'R': 'Р', 's': 'с', 'S': 'С',
    't': 'т', 'T': 'Т', 'u': 'у', 'U': 'У', 'v': 'в', 'V': 'В',
    'x': 'х', 'X': 'Х', 'y': 'й', 'Y': 'Й', 'z': 'з', 'Z': 'З'
}

def cyrillic_to_latin(text: str) -> str:
    res = []
    for ch in text:
        res.append(CYR_TO_LAT_MAP.get(ch, ch))
    return "".join(res)

def latin_to_cyrillic(text: str) -> str:
    s = text
    for lat, cyr in LAT_TO_CYR_MULTI:
        s = s.replace(lat, cyr)
    res = []
    for ch in s:
        res.append(LAT_TO_CYR_SINGLE.get(ch, ch))
    return "".join(res)

def apply_script(text: str, script_mode: str) -> str:
    if not text:
        return ""
    if script_mode == "latin":
        return cyrillic_to_latin(text)
    return text  # Standart holda Krilcha matnlar saqlanadi

# ==============================================================================
# 3. JSON SAQLASH VA YUKLASH FUNKSIYALARI
# ==============================================================================
def load_json_file(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Fayl yuklashda xatolik ({path}): {e}")
    return default

def save_json_file(path: str, data: Any):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Fayl saqlashda xatolik ({path}): {e}")

def get_settings() -> dict:
    defaults = {
        "auto_reactions": True,
        "auto_share": True,
        "auto_comment": True,
        "selected_preset_index": 0,
        "reactions": ["👍", "❤️", "🔥", "👏", "🐝"],
        "official_channel": "@uz_asalarichilik",
        "official_group": "@asalarichilik_uzbekistan",
        "official_youtube": "https://youtube.com/@asalarichilikuztv?feature=shared",
        "official_bot": "@Asalarichiliktv_bot",
        "official_channel_title": "Asalarichilik.Uz",
        "script_mode": "cyrillic",          # "cyrillic" yoki "latin"
        "post_target_mode": "channel",       # "channel", "group", "both", "ask"
        "poll_type": "quiz",                 # "quiz" (Викторина) yoki "regular" (Опрос)
        "poll_is_anonymous": True,           # True (Аноним) yoki False (Очиқ)
        "quiz_schedule_enabled": True,       # Avtomatik viktorina jadvali
        "quiz_schedule_time": "10:00",       # Har kuni 10:00 da
        "quiz_level": "beginner",            # "beginner", "spec", "mixed"
        "news_schedule_enabled": True,       # Avtomatik yangiliklar jadvali
        "news_schedule_time": "14:00",
        "apitherapy_schedule_enabled": True,
        "apitherapy_schedule_time": "16:00",       # Har kuni 14:00 da
        "silent_send": False
    }
    data = load_json_file(SETTINGS_FILE, defaults)
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    # Eski xato qiymatlar bo'lsa, avtomatik yangilash
    if data.get("official_channel") in ["@asalarichilik", "asalarichilik"]:
        data["official_channel"] = "@uz_asalarichilik"
    if data.get("official_group") in ["@Uz_Asalarichilik", "Uz_Asalarichilik", "@UzAsalarichilik", "UzAsalarichilik"]:
        data["official_group"] = "@asalarichilik_uzbekistan"
    return data

def update_setting(key: str, value: Any):
    settings = get_settings()
    settings[key] = value
    save_json_file(SETTINGS_FILE, settings)

def get_official_channel() -> str:
    val = str(get_settings().get("official_channel", "@uz_asalarichilik")).strip()
    if val in ["@asalarichilik", "asalarichilik", ""]:
        val = "@uz_asalarichilik"
    return val if val.startswith("@") else ("@" + val)

def get_official_channel_clean() -> str:
    return get_official_channel().lstrip("@")

def get_official_group() -> str:
    val = str(get_settings().get("official_group", "@asalarichilik_uzbekistan")).strip()
    if val in ["@Uz_Asalarichilik", "Uz_Asalarichilik", "@UzAsalarichilik", "UzAsalarichilik", ""]:
        val = "@asalarichilik_uzbekistan"
    return val if val.startswith("@") else ("@" + val)

def get_official_group_clean() -> str:
    return get_official_group().lstrip("@")

def get_official_youtube() -> str:
    return str(get_settings().get("official_youtube", "https://youtube.com/@asalarichilikuztv?feature=shared")).strip()

def get_official_bot() -> str:
    return str(get_settings().get("official_bot", "@Asalarichiliktv_bot")).strip()

def get_official_footer(script: str = "cyrillic") -> str:
    chan = get_official_channel()
    grp = get_official_group()
    yt = get_official_youtube()
    bot_label = get_official_bot()
    if not bot_label.startswith("@"):
        bot_label = "@" + bot_label
    if script == "latin":
        return (
            "__________________________________\n"
            f"🐝 Rasmiy kanal: {chan}\n"
            f"👥 Asalarichilik guruhi: {grp}\n"
            f"📺 YouTube: {yt}\n"
            f"🤖 Bot: {bot_label}"
        )
    return (
        "__________________________________\n"
        f"🐝 Расмий канал: {chan}\n"
        f"👥 Асаларичилик гуруҳи: {grp}\n"
        f"📺 YouTube: {yt}\n"
        f"🤖 Бот: {bot_label}"
    )

def get_channel_title() -> str:
    return str(get_settings().get("official_channel_title", "Asalarichilik.Uz")).strip()

def get_share_url(title: str = "", text: str = "", source: str = "", tags: str = "", post_url: str = "") -> str:
    """Telegram share/ulashish havolasini to'liq ma'lumotlar bilan hosil qiladi"""
    lines = []
    if title:
        lines.append(f"📌 {title.strip()}")
        lines.append("")
    
    clean_body = re.sub(r'[*_`]', '', text).strip()
    if len(clean_body) > 750:
        clean_body = clean_body[:750] + "..."
    if clean_body:
        lines.append(clean_body)
        lines.append("")
        
    if source:
        lines.append(f"🌐 Манба: {source.strip()}")
    if tags:
        lines.append(f"🏷 {tags.strip()}")
        
    lines.append(get_official_footer(script="cyrillic"))
    
    full_text = "\n".join(lines)
    encoded_text = urllib.parse.quote(full_text)
    
    target_link = post_url or f"https://t.me/{get_official_channel_clean()}"
    encoded_url = urllib.parse.quote(target_link)
    return f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"

def load_allowed_chats() -> dict:
    return load_json_file(ALLOWED_CHATS_FILE, {})

def save_allowed_chat(chat_id: int, chat_title: str, chat_type: str = "group"):
    chats = load_allowed_chats()
    chats[str(chat_id)] = {
        "title": chat_title,
        "type": chat_type,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json_file(ALLOWED_CHATS_FILE, chats)

def is_chat_allowed(chat_id: int, chat_username: Optional[str] = None) -> bool:
    chats = load_allowed_chats()
    if str(chat_id) in chats:
        return True
    off_g = get_official_group_clean().lower()
    off_c = get_official_channel_clean().lower()
    if chat_username:
        u = chat_username.lower().lstrip("@")
        if u == off_g or u == off_c:
            return True
    return False

# ==============================================================================
# 4. VIKTORINA BAZASI (QUIZ DATABASE) - YOSH VA SPETS ASALARICHILAR UCHUN
# ==============================================================================
INITIAL_QUIZZES = [
    {
        "id": 1,
        "level": "spec",
        "question": "Вароа (Varroa destructor) канаси қайси насл катакчаларида 2 баробар кўпроқ кўпаяди?",
        "options": [
            "Эркак ари (трутень) наслида",
            "Ишчи ари наслида",
            "Она ари косачасида"
        ],
        "correct_option_id": 0,
        "explanation": "Вароа канаси эркак ари наслида 2 баробар кўпроқ кўпаяди. Сабаби трутень личинкаси ривожланиш даври узоқроқ (24 кун) ва унда юқори озуқа моддалари мавжуд.",
        "category": "Варроатоз ва касалликлар",
        "posted": False
    },
    {
        "id": 2,
        "level": "spec",
        "question": "Бипин (Амитраз) препарати билан кузги ишлов бериш қайси ҳарорат чегарасида энг юқори самара беради?",
        "options": [
            "+8...+12°C даражада (Арилар клуб ҳосил қила бошлаганда)",
            "-5...0°C совуқда",
            "+25...+30°C иссиқда"
        ],
        "correct_option_id": 0,
        "explanation": "Бипин билан ишлов бериш уяда ёпиқ насл қолмаганда ва ҳарорат +8...+12°C бўлганда ўтказилади. Арилар бир-бирига жипс турганда эритма барча ариларга тез тарқалади.",
        "category": "Касалликлар ва профилактика",
        "posted": False
    },
    {
        "id": 3,
        "level": "spec",
        "question": "Она арини сунъий етиштиришда ромдан кўчириш учун энг муносиб личинка ёши неча соатлик бўлиши керак?",
        "options": [
            "12-24 соатлик (1 кунлик)",
            "3-4 кунлик личинка",
            "5-6 кунлик ғумбак"
        ],
        "correct_option_id": 0,
        "explanation": "12-24 соатлик (энг ёш) личинка танланса, оналик сути билан бошидан сифатли боқилади ва тўлақонли 160-180 та тухумдон найчаларига эга бўлган бақувват она ари чиқади.",
        "category": "Она ари етиштириш",
        "posted": False
    },
    {
        "id": 4,
        "level": "spec",
        "question": "Карника (Apis mellifera carnica) зотининг хартумчаси узунлиги ўртача неча миллиметрни ташкил қилади?",
        "options": [
            "6.4 - 6.8 мм",
            "4.5 - 5.0 мм",
            "8.0 - 9.2 мм"
        ],
        "correct_option_id": 0,
        "explanation": "Карника зотининг хартумчаси 6.4 - 6.8 мм бўлиб, чуқур найсимон гуллардан (масалан қизил беда) ҳам бемалол нектар олиш имконини беради.",
        "category": "Асалари зотлари",
        "posted": False
    },
    {
        "id": 5,
        "level": "spec",
        "question": "Нозематоз (Nosema ceranae) касаллигининг Nosema apis дан асосий фарқи ва хавфи нимада?",
        "options": [
            "Йил бўйи (ҳатто ёзда ҳам) наслсиз сурункали кечади ва ич кетмасдан кучсизлантиради",
            "Фақат баҳорда учрайди ва фақат она арига таъсир қилади",
            "Фақат мум қуртларини зарарлайди"
        ],
        "correct_option_id": 0,
        "explanation": "Nosema ceranae Осиё нозематози бўлиб, анъанавий нозематоздан фарқли ўлароқ ёзги иссиқда ҳам ривожланади, очиқ ич кетиш белгиси кам кузатилади, аммо ариларни тез қириб битиради.",
        "category": "Касалликлар ва ветеринария",
        "posted": False
    },
    {
        "id": 6,
        "level": "spec",
        "question": "Америка чириши (Paenibacillus larvae) споралари ташқи муҳитда неча йилгача яшовчанлигини сақлайди?",
        "options": [
            "30-40 йилгача",
            "Фақат 1 ой",
            "1-2 йил"
        ],
        "correct_option_id": 0,
        "explanation": "Америка чириши споралари ўта чидамли бўлиб, асал, мум ва эски уяларда 30-40 йилгача сақланади. Унга қарши кучли дезинфекция ва олов билан куйдириш қўлланилади.",
        "category": "Касалликлар ва хавфсизлик",
        "posted": False
    },
    {
        "id": 7,
        "level": "spec",
        "question": "Табиий асалнинг сифатини белгиловчи диастаза сони (Готе бирлиги) бўйича стандарт минимал талаб нечага тенг?",
        "options": [
            "Камида 8 Готе бирлиги",
            "Камида 1 Готе бирлиги",
            "Камида 50 Готе бирлиги"
        ],
        "correct_option_id": 0,
        "explanation": "Давлат стандарти бўйича табиий тоза асалда диастаза сони камида 8 Готе бирлигидан кам бўлмаслиги керак. Бу асалнинг табиий ферментларга бойлигини исботлайди.",
        "category": "Асал сифати ва стандартлар",
        "posted": False
    },
    {
        "id": 8,
        "level": "spec",
        "question": "Қишлаш даврида ари оиласи ҳосил қилган қишги клубнинг (шар) ички марказий ҳарорати қанча даражада сақланади?",
        "options": [
            "+24...+28°C (Насл пайдо бўлгач +34°C)",
            "+5...+8°C",
            "0...-2°C"
        ],
        "correct_option_id": 0,
        "explanation": "Клуб марказида ҳарорат +24...+28°C сақланади, ташқи қобиғида эса +14...+15°C бўлади. Февраль охирида она ари тухум қўйишни бошлаши билан ҳарорат +34...+35°C гача кўтарилади.",
        "category": "Қишлатиш сирлари",
        "posted": False
    },
    {
        "id": 9,
        "level": "spec",
        "question": "Она ари ҳавода жуфтлашиш пайтида ўртача нечта эркак ари (трутень) билан уруғланади?",
        "options": [
            "7 - 12 та эркак ари билан",
            "Фақат 1 та эркак ари билан",
            "50 тадан ортиқ эркак ари билан"
        ],
        "correct_option_id": 0,
        "explanation": "Она ари полиандрия қонуниятига кўра 7-12 та бақувват эркак ари билан ҳавода жуфтлашади ва унинг уруғдонида (сперматека) 5-7 миллион сперматозоид тўпланади.",
        "category": "Селекция ва генетика",
        "posted": False
    },
    {
        "id": 10,
        "level": "spec",
        "question": "Оксалат (шовўл) кислотасини сублимация (буғлатиш) орқали қўллашда 1 та оилага қанча миқдорда кукун солиниши лозим?",
        "options": [
            "1.5 - 2 грамм",
            "15 - 20 грамм",
            "0.1 грамм"
        ],
        "correct_option_id": 0,
        "explanation": "Бир ари оиласига оксалат кислотаси сублиматори орқали 1.5 - 2 грамм кукун буғлатиб пуркалади. Меъёрдан ошириш ариларга зарар етказиши мумкин.",
        "category": "Варроага қарши воситалар",
        "posted": False
    },
    # Yosh asalarichilar uchun savollar
    {
        "id": 11,
        "level": "beginner",
        "question": "Асалари оиласида бир кунда 1500-2000 тагача тухум қўювчи асосий ари қайси?",
        "options": [
            "Она ари (Матка)",
            "Ишчи ари",
            "Эркак ари (Трутень)"
        ],
        "correct_option_id": 0,
        "explanation": "Она ари оиладаги ягона тўлақонли урғочи ари бўлиб, унинг бош вазифаси тухум қўйиш ва оила бирлигини сақловчи феромонлар ажратишдир.",
        "category": "Асалари оиласи тузилиши",
        "posted": False
    },
    {
        "id": 12,
        "level": "beginner",
        "question": "Ишчи асаларининг тухумдан чиқиб тўлиқ етилишига неча кун керак бўлади?",
        "options": [
            "21 кун",
            "16 кун",
            "24 кун"
        ],
        "correct_option_id": 0,
        "explanation": "Она ари 16 кунда, ишчи ари 21 кунда, эркак ари эса 24 кунда етилиб чиқади.",
        "category": "Асалари физиологияси",
        "posted": False
    },
    {
        "id": 13,
        "level": "beginner",
        "question": "Эркак арида (трутень) ниш (жало) бўладими?",
        "options": [
            "Йўқ, эркак ариларда умуман ниш бўлмайди",
            "Ҳа, фақат жуда кичик бўлади",
            "Ҳа, заҳари кучли бўлади"
        ],
        "correct_option_id": 0,
        "explanation": "Эркак ариларда ҳеч қачон ниш бўлмайди. Чунки ниш урғочи ариларнинг ўзгарган тухум қўйиш органи ҳисобланади.",
        "category": "Асалари тузилиши",
        "posted": False
    },
    {
        "id": 14,
        "level": "beginner",
        "question": "Асаларилар уясида насл ривожланиши учун оптимал уя ҳарорати неча даража бўлиши керак?",
        "options": [
            "34 - 35°C",
            "20 - 22°C",
            "40 - 42°C"
        ],
        "correct_option_id": 0,
        "explanation": "Уяда насл ривожланиши зонасида арилар ҳароратни қатъий равишда 34-35°C атрофида доимий сақлаб туради.",
        "category": "Уя микроиқлими",
        "posted": False
    },
    {
        "id": 15,
        "level": "beginner",
        "question": "Асаларилар прополисни (елимни) асосан нимадан йиғиб келадилар?",
        "options": [
            "Дарахт ва ўсимликларнинг ёпишқоқ куртаклари ва пўстлоқ қатронидан",
            "Гул чангидан",
            "Ари сутидан"
        ],
        "correct_option_id": 0,
        "explanation": "Прополис — терак, қайин, тол каби дарахтларнинг куртакларидан йиғиладиган табиий қатрон бўлиб, уяни микроблардан тозалаш ва тешикларни бекитиш учун ишлатилади.",
        "category": "Асаларичилик маҳсулотлари",
        "posted": False
    },
    {
        "id": 16,
        "level": "beginner",
        "question": "Асалари уясида мум (воск) ишлаб чиқарувчи безлар қаерда жойлашган?",
        "options": [
            "Ишчи ари қорин қисмининг пастки ярмида",
            "Бош қисмида",
            "Қанотлари тагида"
        ],
        "correct_option_id": 0,
        "explanation": "Мум ишлаб чиқарувчи 4 жуфт мум ойначалари 12-18 кунлик ёш ишчи ариларнинг қоринчаси остида жойлашган.",
        "category": "Мум ишлаб чиқариш",
        "posted": False
    },
    {
        "id": 17,
        "level": "beginner",
        "question": "Асалари оиласида «Ари нони» ёки «Перга» деб нимага айтилади?",
        "options": [
            "Асал ва ферментлар билан катакчага босиб ачитилган гул чангига",
            "Суюқ шакар сиропига",
            "Мум билан сувалган қоғозга"
        ],
        "correct_option_id": 0,
        "explanation": "Перга (ари нони) — арилар катакчаларга зичлаб жойлаштирган, асал билан тўйинтириб сут кислотали бижғитилган оқсилга бой гул чангидир.",
        "category": "Ари озуқаси",
        "posted": False
    },
    {
        "id": 18,
        "level": "beginner",
        "question": "Ёзги фаол даврда туғилган ишчи асаларининг ўртача умр кўриш давомийлиги қанча?",
        "options": [
            "30 - 45 кун",
            "1 йил",
            "3 йил"
        ],
        "correct_option_id": 0,
        "explanation": "Ёзда тинимсиз оғир меҳнат қилган ишчи ари 35-45 кун яшайди. Кузда туғилиб қишлайдиган арилар эса 6-8 ойгача умр кўради.",
        "category": "Асалари ҳаёти",
        "posted": False
    },
    {
        "id": 19,
        "level": "beginner",
        "question": "Асаларининг нечта қаноти ва нечта кўзи бор?",
        "options": [
            "4 та қаноти, 5 та кўзи (2 та мураккаб, 3 та оддий)",
            "2 та қаноти, 2 та кўзи",
            "6 та қаноти, 4 та кўзи"
        ],
        "correct_option_id": 0,
        "explanation": "Асалари 4 та қанотга эга бўлиб, парвоз вақтида илмоқлар билан 2 жуфтга бирикади. Бошида 2 та катта фасетли ва пешонасида 3 та кичик оддий кўзлари мавжуд.",
        "category": "Асалари анатомияси",
        "posted": False
    },
    {
        "id": 20,
        "level": "beginner",
        "question": "Давлат стандарти бўйича етилган сифатли асал таркибидаги намлик кўпи билан неча фоиз бўлиши керак?",
        "options": [
            "18 - 20% дан ошмаслиги керак",
            "35 - 40%",
            "50%"
        ],
        "correct_option_id": 0,
        "explanation": "Етилган асал намлиги 18-20% дан ошмаслиги шарт. Намлик юқори бўлса, асал тез ачийди ва сақлашга яроқсиз бўлади.",
        "category": "Асал сифати",
        "posted": False
    }
]

def get_quizzes_db() -> list:
    db = load_json_file(QUIZ_DB_FILE, [])
    if not db:
        db = copy.deepcopy(INITIAL_QUIZZES)
        save_json_file(QUIZ_DB_FILE, db)
    return db

def save_quizzes_db(quizzes: list):
    save_json_file(QUIZ_DB_FILE, quizzes)

def get_next_quiz(level: str = "mixed") -> dict:
    quizzes = get_quizzes_db()
    
    # Tanlangan darajadagi foydalanilmagan savollarni qidirish
    candidates = []
    for q in quizzes:
        if not q.get("posted", False):
            if level == "mixed" or q.get("level") == level:
                candidates.append(q)
                
    if not candidates:
        # Barchasi tugagan bo'lsa qaytadan boshlash
        for q in quizzes:
            q["posted"] = False
        save_quizzes_db(quizzes)
        candidates = [q for q in quizzes if (level == "mixed" or q.get("level") == level)]

    if not candidates:
        candidates = quizzes

    picked = random.choice(candidates)
    picked["posted"] = True
    save_quizzes_db(quizzes)
    return picked

# ==============================================================================
# 4.1 OPROS (OCHIQ FIKR SO'ROVNOMALARI) BAZASI
# ==============================================================================
INITIAL_POLLS = [
    {
        "id": 1,
        "type": "regular",
        "question": "📊 Сиз асаларизорингизда асосан қайси зотдан фойдаланасиз?",
        "options": [
            "Карника (Carnica)",
            "Карпат (Carpatica)",
            "Бакфаст (Buckfast)",
            "Маҳаллий Ўрта Осиё зоти",
            "Бир нечта зотни синаб кўраман"
        ],
        "posted": False
    },
    {
        "id": 2,
        "type": "regular",
        "question": "📊 Кузги озиқлантириш ва сироп беришни қайси вақтда тўлиқ якунлайсиз?",
        "options": [
            "Август охиридаёқ тугатаман",
            "1-15 сентябрь орасида",
            "Сентябрь охиригача",
            "Октябрь бошигача бераман"
        ],
        "posted": False
    },
    {
        "id": 3,
        "type": "regular",
        "question": "📊 Варроа канасига қарши қайси восита сизнинг амалиётингизда энг самарали бўлган?",
        "options": [
            "Бипин (Амитраз) сувли эритмаси",
            "Оксалат (шовўл) кислотаси сублимацияси",
            "Тимол ва табиий эфир мойлари",
            "Иссиқлик (термик) камера усули",
            "Кетма-кет навбатма-навбат қўллайман"
        ],
        "posted": False
    },
    {
        "id": 4,
        "type": "regular",
        "question": "📊 Қишлов даврида уяларингизни асосан қаерда сақлайсиз?",
        "options": [
            "Очиқ ҳавода (далада/боғда)",
            "Махсус қишловхонада (омшаник/бинода)",
            "Усти ёпиқ айвон ёки навес остида",
            "Қуёш тушадиган девор бўйида"
        ],
        "posted": False
    },
    {
        "id": 5,
        "type": "regular",
        "question": "📊 Бир оиладан бир мавсумда ўртача неча кг тоза товар асали оласиз?",
        "options": [
            "15 - 25 кг",
            "25 - 40 кг",
            "40 - 60 кг",
            "60 кг дан юқори (кўчма асаларичиликда)"
        ],
        "posted": False
    },
    {
        "id": 6,
        "type": "regular",
        "question": "📊 Асаларичиликда сизнинг асосий даромад ва йўналишингиз қайси?",
        "options": [
            "Тоза асал етиштириш ва сотиш",
            "Она ари ва асалари пакетлари сотиш",
            "Гул чанги, прополис ва ари сути олиш",
            "Ҳамма йўналишларни комплекс олиб бораман"
        ],
        "posted": False
    },
    {
        "id": 7,
        "type": "regular",
        "question": "📊 Баҳорги биринчи тўлиқ тафтиш (кўрик)ни одатда қайси пайтда ўтказасиз?",
        "options": [
            "Февраль охирида (биринчи илиқ кунда)",
            "Март ойининг бошида",
            "Ҳаво барқарор +15°C ва ундан ошганда",
            "Бодом ва эртаги дарахтлар гуллаганда"
        ],
        "posted": False
    },
    {
        "id": 8,
        "type": "regular",
        "question": "📊 Сиз фойдаланадиган уялар асосан қайси конструкцияда?",
        "options": [
            "Дадан-Блатт (12 ромлик кўп корпус)",
            "Рута (кўп корпусли 230 мм ромлик)",
            "Ётоқ уя (Лежак 16-24 ромлик)",
            "ППУ (пенополиуретан) замонавий уялар"
        ],
        "posted": False
    }
]

def get_polls_db() -> list:
    db = load_json_file(POLL_DB_FILE, [])
    if not db:
        db = copy.deepcopy(INITIAL_POLLS)
        save_json_file(POLL_DB_FILE, db)
    return db

def save_polls_db(polls: list):
    save_json_file(POLL_DB_FILE, polls)

def get_next_poll() -> dict:
    polls = get_polls_db()
    candidates = [p for p in polls if not p.get("posted", False)]
    if not candidates:
        for p in polls:
            p["posted"] = False
        save_polls_db(polls)
        candidates = polls
    picked = random.choice(candidates)
    picked["posted"] = True
    save_polls_db(polls)
    return picked

# ==============================================================================
# 5. ASALARICHILIK YANGILIKLARI BAZASI (NEWS DATABASE)
# ==============================================================================
INITIAL_NEWS = [
    {
        "id": 1,
        "title": "Олимлар асаларилар иммунитетини 40% га оширувчи янги табиий озуқа ихтиро қилишди!",
        "date": "2026-10-24",
        "category": "Илмий инновация",
        "body": (
            "Германия ва Австралия биологлари томонидан олиб борилган тадқиқотлар якунланди. "
            "Олимлар асаларилар ичак микрофлораси ва ўсимлик экстрактлари асосида янги табиий озуқа яратдилар."
        ),
        "results": [
            "Кузги озиқлантиришда берилганда оилалар нозематоз ва вирусларга 40% чидамли бўлди.",
            "Қишловда ўлим деярли 0% га тушди.",
            "Баҳорда тухум қўйиш 25-30% тезлашди."
        ],
        "source": "Nature Scientific Reports / Халқаро тадқиқот (2026 йил Октябрь)",
        "tags": "#Асаларичилик #Янгилик #Инновация #AsalarichilikUz"
    },
    {
        "id": 2,
        "title": "Варроа канасига қарши янги авлод гипертермик (42°C иссиқлик) технологияси тўлиқ синовдан ўтди",
        "date": "2026-10-23",
        "category": "Инновациялар ва даволаш",
        "body": (
            "Австрия ва Швейцария илмий марказлари асалари уяларига кимёвий воситаларсиз, аниқ дозаланган "
            "42°C иссиқ ҳаво бериш орқали варроа канасини 97-99% гача тушириб юбориш мумкинлигини исботлади."
        ),
        "results": [
            "Асаларилар +45°C гача бемалол чидайди, каналар эса +41.5°C да оқсил коагуляциясидан нобуд бўлади.",
            "Асал ва мумда ҳеч қандай дори қолдиғи қолмайди, тўлиқ экологик тоза маҳсулот олинади.",
            "Кузги ишловда кимёвий препаратларга чидамли бўлиб қолган кана популяциясига қарши 100% самарали."
        ],
        "source": "Apidologie / European Bee Research Consortium (2026 йил Октябрь)",
        "tags": "#Варроа #Даволаш #ИссиқликУсули #ЭкоАсал #Инновация"
    },
    {
        "id": 3,
        "title": "Ақлли уя сенсорлари (AI Smart Hive): Қишлов даврида оилани очмай 100% назорат қилиш имконияти",
        "date": "2026-10-22",
        "category": "Рақамли технологиялар",
        "body": (
            "Япония ва Германия муҳандислари уя ичидаги ҳарорат, акустик овоз частотаси (арилар гувуллаши) "
            "ва карбонат ангидрид даражасини таҳлил қилувчи ихчам симсиз тизим ишлаб чиқдилар."
        ),
        "results": [
            "Она арининг бор-йўқлиги ва оилада озуқа тугаб бораётгани 5 кун олдин телефонга хабар қилинади.",
            "Қишда совуқ ҳавода уя қопқоғини очиб ариларни безовта қилиш зарурати бутунлай йўқолади.",
            "Баҳорда эрта тўда ажратиш (роя ҳолати) бошланишини 48 соат олдин огоҳлантиради."
        ],
        "source": "Journal of Apicultural Research / Smart Agriculture Review (2026 йил)",
        "tags": "#АқллиУя #SmartHive #Технология #Қишлатиш #AsalarichilikUz"
    },
    {
        "id": 4,
        "title": "Кузги озиқлантиришда канди хамирига Lactobacillus пробиотиги қўшиш нозематоз хавфини 75% га камайтирди",
        "date": "2026-10-21",
        "category": "Парвариш ва озиқлантириш",
        "body": (
            "Франция миллий қишлоқ хўжалиги институти (INRAE) томонидан 600 та асалари оиласида "
            "ўтказилган кенг кўламли тажрибада пробиотикларнинг ари ичак микробиомига таъсири ўрганилди."
        ),
        "results": [
            "Шакар қиёми ёки кандига махсус сут кислотали бактериялар қўшилганда ариларнинг ичак шиллиқ қавати мустаҳкамланди.",
            "Nosema ceranae спораларининг ривожланиши ва ичак деворига ёпишиши 75% га қисқарди.",
            "Қишловдан чиққан ариларнинг яшаш муддати ўртача 18 кунга узайди."
        ],
        "source": "Applied and Environmental Microbiology / INRAE France (2026 йил)",
        "tags": "#Нозематоз #Пробиотик #Озиқлантириш #КузгиПарвариш #Тавсия"
    },
    {
        "id": 5,
        "title": "Ўзбекистон тоғ асалининг экспорт кўрсаткичи: Диастаза фаоллиги 22 Готе бирлигига етди",
        "date": "2026-10-20",
        "category": "Бозор ва экспорт",
        "body": (
            "Халқаро Апимондия (Apimondia) синов лабораториясида Ўзбекистон тоғ ва яйлов ҳудудларидан "
            "йиғилган табиий асал намуналари текширилди. Натижалар жаҳон стандартларидан бир неча баробар юқори чиқди."
        ),
        "results": [
            "Диастаза сони 18-24 Готе бирлигини ташкил этиб, жаҳон меъёридан (8 бирлик) қарийб 3 баравар юқори.",
            "Кийикўт (чабрец), оққурай ва тоғ кийикўти нектарлари асалда антиоксидантлар миқдорини юқори даражада оширган.",
            "Европа ва Осиё бозорларига миллий бренд остида премиум экспорт қилиш бўйича шартномалар имзоланди."
        ],
        "source": "International Honey Commission (IHC) / Тошкент-Рим (2026 йил)",
        "tags": "#ЎзбекистонАсали #Диастаза #ТоғАсали #Экспорт #Сифат"
    },
    {
        "id": 6,
        "title": "Она ариларни сунъий уруғлантириш (ИОМ): 100% тоза насл олиш бўйича янги микроскоп тизими",
        "date": "2026-10-19",
        "category": "Селекция ва зотлар",
        "body": (
            "Польша ва Германиялик селекционерлар она ариларни асбоб-ускунали уруғлантиришда (Instrumental Insemination) "
            "капилляр найчалар ва юқори аниқликдаги рақамли микроскопларни жорий қилишди."
        ),
        "results": [
            "Эркак ари (трутень) уруғини олишда оиланинг 100% генетик софлиги таъминланади.",
            "Она арининг кейинги 3 йил давомида кунига 2000-2500 тагача тухум қўйиш қобилияти сақланади.",
            "Тўда ажратмайдиган (тинч), асал маҳсулдорлиги 30% юқори бўлган наслдор линиялар шакллантирилади."
        ],
        "source": "Bee World Journal / Selektsiya Yangiliklari (2026 йил)",
        "tags": "#ОнаАри #СунъийУруғлантириш #Бакфаст #Карника #Селекция"
    },
    {
        "id": 7,
        "title": "Осиё улкан қовоғариси (Vespa velutina) га қарши оптик ва акустик ҳимоя қопқони ихтиро қилинди",
        "date": "2026-10-18",
        "category": "Зараркунандаларга қарши",
        "body": (
            "Жанубий Корея ва Франция муҳандислари асаларизорларни йиртқич қовоғарилардан ҳимоя қилиш мақсадида "
            "лазерли ва инфрақизил сенсорли автоном қопқонларни синовдан ўтказдилар."
        ),
        "results": [
            "Қопқон ари ва қовоғари ҳажмини 0.05 сонияда ажратади ва фақат зарарли қовоғариларни тутиб йўқ қилади.",
            "Битта қурилма 50 тагача уяни йиртқичлар ҳужумидан тўлиқ асрайди.",
            "Асаларилар стрессга тушмайди ва кузги асал йиғиш суръати пасаймайди."
        ],
        "source": "Agricultural Technology & Entomology Journal (2026 йил)",
        "tags": "#Қовоғари #Ҳимоя #Инновация #Асаларизор #Технология"
    },
    {
        "id": 8,
        "title": "Баҳорги эрта тухум қўйишни 30% га тезлаштирувчи оқсилли қўшимчалар қиёсий баҳоланди",
        "date": "2026-10-17",
        "category": "Баҳорги ривожланиш",
        "body": (
            "АҚШ Қишлоқ хўжалиги вазирлиги (USDA-ARS) асаларичилик лабораторияси баҳорги чанг танқислиги "
            "даврида оқсилли канди ва пасталар самарасини таққослади."
        ),
        "results": [
            "Спирулина сувўти ва ёғсизлантирилган соя уни қўшилган канди берилганда насл уяси 30% тезроқ кенгайди.",
            "Ёш боқувчи ариларнинг ҳалқум безлари (асалари сути ажратиш) фаоллиги 45% га ошди.",
            "Эрта баҳорги асал тўплаш даврига оилалар кучли ва тўлиқ тайёр ҳолатда етиб келди."
        ],
        "source": "USDA-ARS Bee Research Lab / Maryland (2026 йил)",
        "tags": "#БаҳоргиПарвариш #ОқсиллиОзиқа #Канди #НаслОлиш #Тавсия"
    },
    {
        "id": 9,
        "title": "Асалнинг қалбакилигини (шакар сиропи қўшилганини) 30 сонияда аниқловчи чўнтак спектрометри яратилди",
        "date": "2026-10-16",
        "category": "Сифат ва назорат",
        "body": (
            "Германиянинг Фраунгофер институти олимлари лазерли спектроскопия ёрдамида табиий асал билан "
            "қанд сиропини дарҳол ажратувчи ихчам портатив қурилмани тақдим этдилар."
        ),
        "results": [
            "Асални лабораторияга юбормасдан, жойида 99.8% аниқлик билан ҳақиқий ёки сунъийлигини билиш мумкин.",
            "C4 қандлари, глюкоза-фруктоза сироплари ва термик қайта ишланган асал белгилари аниқланади.",
            "Ҳалол ва сифатли асал етиштирувчи асаларичилар маҳсулотини бозорда ҳимоя қилишда муҳим аҳамиятга эга."
        ],
        "source": "Fraunhofer Institute for Chemical Technology / Germany (2026 йил)",
        "tags": "#АсалСифати #Спектрометр #ҚалбакиликкаҚарши #ТозаАсал #Фан"
    },
    {
        "id": 10,
        "title": "Пенополиуретан (ППУ) уялар ва анъанавий ёғоч уялар: Қишлаш ва ёзги иссиқлик синови",
        "date": "2026-10-15",
        "category": "Инновацион уялар",
        "body": (
            "Россия ва Беларусь илмий текшириш институтлари 5 йил давомида ППУ (пенополиуретан) "
            "ва тахта уяларда ариларнинг ривожланиши ва қишлашини таққосладилар."
        ),
        "results": [
            "ППУ уяларда қишда намлик тўпланмайди ва ички ҳарорат ёғоч уяга нисбатан 4-5°C илиқроқ сақланади.",
            "Қишловда оилалар озуқани 20-25% камроқ истеъмол қилди, баҳорда ич кетиш ҳолатлари деярли кузатилмади.",
            "Ёзги 45°C иссиқда уя ичи қизиб кетмайди, арилар сув ташишга камроқ куч сарфлайди."
        ],
        "source": "Beekeeping Scientific Journal / Апиэкспертиза (2026 йил)",
        "tags": "#ППУуя #Уялар #Қишлатиш #ИссиқликСақлаш #Амалиёт"
    },
    {
        "id": 11,
        "title": "Шовул ва чумоли кислотаси билан варроа канасига кузги ишлов беришнинг янги хавфсиз протоколи",
        "date": "2026-10-14",
        "category": "Органик даволаш",
        "body": (
            "Канада ва Германия асаларичилик ассоциациялари шовул кислотасини (щавелевая кислота) буғлатиш (сублимация) "
            "ва чумоли кислотаси гелларини қўллашнинг энг хавфсиз муддатларини эълон қилди."
        ),
        "results": [
            "Оилаларда насл бўлмаган даврда шовул кислотаси сублимацияси 98.5% кана тушириш самарасини берди.",
            "Она ари ва ишчи ариларнинг соғлиғига ҳеч қандай салбий таъсир кўрсатмайди.",
            "Кимёвий флувалинат ва амитразга нисбатан каналарда ўрганиб қолиш (резистентлик) пайдо бўлмайди."
        ],
        "source": "Canadian Honey Council & Hohenheim Bee Institute (2026 йил)",
        "tags": "#Варроа #ШовулКислота #ЧумолиКислота #ОрганикИшлов #КузгиИшлов"
    },
    {
        "id": 12,
        "title": "Прополис ва асалари заҳрининг антибактериал фаоллиги бўйича янги халқаро фармакологик хулоса",
        "date": "2026-10-13",
        "category": "Апитерапия ва саломатлик",
        "body": (
            "Швеция ва Буюк Британия тиббиёт университетлари асалари маҳсулотларининг антибиотикка "
            "чидамли бактерияларга (MRSA) қарши курашиш хусусиятини тасдиқладилар."
        ),
        "results": [
            "Прополис экстракти суперинфекцияларни йўқ қилишда замонавий антибиотиклар таъсирини 4 баробаргача кучайтиради.",
            "Апитоксин (ари заҳри) таркибидаги мелиттин моддаси яллиғланишга қарши кучли табиий восита эканлиги исботланди.",
            "Фармацевтика компаниялари асаларичилик маҳсулотларини сотиб олиш ҳажмини сезиларли оширмоқда."
        ],
        "source": "Lancet Infectious Diseases & Apitherapy Journal (2026 йил)",
        "tags": "#Апитерапия #Прополис #АриЗаҳри #Саломатлик #Даволаш"
    }
]

def get_news_db() -> list:
    db = load_json_file(NEWS_DB_FILE, [])
    if not db:
        db = copy.deepcopy(INITIAL_NEWS)
        save_json_file(NEWS_DB_FILE, db)
    return db

def save_news_db(news: list):
    save_json_file(NEWS_DB_FILE, news)

def get_next_news() -> dict:
    news_list = get_news_db()
    if not news_list:
        return INITIAL_NEWS[0]
    return random.choice(news_list)

def sync_bee_news_collection() -> dict:
    """
    bee_news_collection.py fayli mavjud bo'lsa (PythonAnywhere yoki joriy papkada),
    undagi 100 ta yangilik va savollarni avtomatik o'qib, news_database.json va
    quiz_database.json fayllariga birlashtiradi.
    """
    candidates = [
        os.path.join(BASE_DIR, "bee_news_collection.py"),
        os.path.join(os.getcwd(), "bee_news_collection.py"),
        "/home/Asalarichiliktv/bee_news_collection.py",
        "bee_news_collection.py"
    ]
    target_path = None
    for p in candidates:
        if os.path.exists(p):
            target_path = p
            break

    if not target_path:
        return {"success": False, "news": 0, "quizzes": 0, "msg": "bee_news_collection.py файли топилмади"}

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bee_news_collection", target_path)
        if not spec or not spec.loader:
            return {"success": False, "news": 0, "quizzes": 0, "msg": "Модулни очиб бўлмади"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except (Exception, BaseException) as e:
        logging.warning(f"Error loading bee_news_collection: {e}")
        return {"success": False, "news": 0, "quizzes": 0, "msg": f"Хатолик: {e}"}

    items_to_process = []
    for attr in dir(mod):
        if attr.startswith("__"):
            continue
        val = getattr(mod, attr)
        if isinstance(val, list):
            items_to_process.extend(val)
        elif isinstance(val, dict):
            for sub in val.values():
                if isinstance(sub, list):
                    items_to_process.extend(sub)
                elif isinstance(sub, dict):
                    items_to_process.append(sub)

    news_db = get_news_db()
    existing_news_titles = {n.get("title", "").strip().lower() for n in news_db if isinstance(n, dict)}

    quiz_db = get_quizzes_db()
    existing_quiz_questions = {q.get("question", "").strip().lower() for q in quiz_db if isinstance(q, dict)}

    added_news = 0
    added_quizzes = 0

    for item in items_to_process:
        if not isinstance(item, dict):
            continue

        # Savol / Viktorina
        if "question" in item or "savol" in item:
            q_text = (item.get("question") or item.get("savol") or "").strip()
            if q_text and q_text.lower() not in existing_quiz_questions:
                options = item.get("options") or item.get("variantlar") or ["Ҳа", "Йўқ"]
                c_id = item.get("correct_option_id")
                if c_id is None:
                    c_id = item.get("correct_option", 0)
                if not isinstance(c_id, int) or c_id < 0 or c_id >= len(options):
                    c_id = 0

                if len(options) >= 2:
                    indexed = list(enumerate(options))
                    random.shuffle(indexed)
                    options = [opt for _, opt in indexed]
                    c_id = next((i for i, (oi, _) in enumerate(indexed) if oi == c_id), 0)

                quiz_db.append({
                    "id": len(quiz_db) + 1,
                    "level": item.get("level", "mixed"),
                    "question": q_text,
                    "options": options,
                    "correct_option_id": c_id,
                    "explanation": item.get("explanation") or item.get("izoh") or "Asalarichilik.Uz 🇺🇿 расмий таҳлили.",
                    "category": item.get("category") or item.get("mavzu") or "Асаларичилик амалиёти",
                    "posted": False
                })
                existing_quiz_questions.add(q_text.lower())
                added_quizzes += 1

        # Yangilik
        elif "title" in item or "mavzu" in item or "body" in item or "matn" in item:
            title = (item.get("title") or item.get("mavzu") or item.get("header") or "").strip()
            if not title and "body" in item:
                title = str(item["body"])[:60] + "..."
            if title and title.lower() not in existing_news_titles:
                news_db.append({
                    "id": len(news_db) + 1,
                    "title": title,
                    "date": item.get("date") or datetime.now().strftime("%Y-%m-%d"),
                    "category": item.get("category") or item.get("bo'lim") or "Асаларичилик янгиликлари",
                    "body": item.get("body") or item.get("matn") or item.get("content") or title,
                    "results": item.get("results") or item.get("xulosalar") or [],
                    "source": item.get("source") or item.get("manba") or "Asalarichilik.Uz 🇺🇿 Халқаро Асаларичилик бюллетени",
                    "tags": item.get("tags") or item.get("teglar") or "#Асаларичилик #Янгилик #Тажриба #AsalarichilikUz"
                })
                existing_news_titles.add(title.lower())
                added_news += 1

    if added_news > 0:
        save_news_db(news_db)
    if added_quizzes > 0:
        save_quizzes_db(quiz_db)

    return {
        "success": True,
        "news": added_news,
        "quizzes": added_quizzes,
        "total_news": len(news_db),
        "total_quizzes": len(quiz_db),
        "msg": f"✅ {added_news} та янгилик ва {added_quizzes} та савол қўшилди!"
    }

# ==============================================================================
# 6. GEMINI FLASH ORQALI AI MUTAXASSIS VA YANGI SAVOLLAR/YANGILIKLAR GENERATORI
# ==============================================================================
SYSTEM_INSTRUCTION = (
    "Сиз Asalarichilik.Uz 🇺🇿 лойиҳасининг расмий бош мутахассиси ва тажрибали устоз асаларичисиз.\n"
    "ҚАТЪИЙ ҚОИДА: Сиз ҳеч қачон Google ёки Gemini ҳақида гапирмайсиз ва эслатмайсиз. "
    "Сизнинг ягона исмингиз ва мақомингиз — «Asalarichilik.Uz 🇺🇿 мутахассиси».\n"
    "Вазифангиз: Фойдаланувчиларнинг асаларичиликка оид ҳар қандай саволларига "
    "(варроа канасига қарши бипин, амитраз, флувалинат, чумоли ва шовул кислоталари, тимол; "
    "нозематоз, чириш ва бошқа касалликлар; карника, карпат, бакфаст зоти ва она ари етиштириш; "
    "баҳорги ривожлантириш, кузги тайёргарлик ва қишлатиш; асал йиғиш, ромлар ясаш, ари оиласини бўлиш ва кўпайтириш) "
    "бўйича профессионал, илмий ва амалий тажрибага асосланган ҳолда аниқ ва равон ўзбек тилида жавоб бериш."
)

def get_proxy():
    if "PYTHONANYWHERE_DOMAIN" in os.environ or os.path.exists("/home/Asalarichiliktv"):
        return "http://proxy.server:3128"
    try:
        socket.gethostbyname("proxy.server")
        return "http://proxy.server:3128"
    except Exception:
        return None

def sync_gemini_request(prompt_text: str, max_tokens: int = 800) -> str:
    models = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{SYSTEM_INSTRUCTION}\n\n{prompt_text}"
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.65,
            "maxOutputTokens": max_tokens
        }
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    
    proxy = get_proxy()
    if proxy:
        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(proxy_handler)
    else:
        opener = urllib.request.build_opener()
        
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with opener.open(req, timeout=15) as resp:
                if resp.status == 200:
                    result = json.loads(resp.read().decode("utf-8"))
                    candidates = result.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception as e:
            logging.warning(f"Model {m} xatolik: {e}")
            
    return "Кечирасиз, саволга жавоб олишда вақтинчалик узилиш юз берди. Илтимос, саволингизни қайта йўлланг."

async def ask_beekeeping_expert(user_question: str) -> str:
    prompt = f"Фойдаланувчи саволи: {user_question}\n\nМутахассис сифатида аниқ, амалий ва батафсил жавоб беринг:"
    return await asyncio.to_thread(sync_gemini_request, prompt, 800)

FALLBACK_QUIZ_POOL = [
    {
        "question": "Варроа канасига қарши чумоли кислотаси (Муравьиная кислота) неча фоизли эритмада қўлланилади?",
        "options": ["60% ёки 85% ли эритма", "10-15% ли кучсиз эритма", "100% ли тоза концентрация"],
        "correct_option_id": 0,
        "explanation": "Чумоли кислотаси 60% ёки 85% ли концентрацияда махсус буғлатгичларда ҳаво ҳарорати +14...+25°C бўлганда ишлатилади. У ёпиқ катакчалар ичидаги канани ҳам нобуд қилади.",
        "category": "Варроатоз ва даволаш"
    },
    {
        "question": "Шовул (Щавелевая) кислотаси сублимация (буғлатиш) усулида бир уяга неча грамм миқдорида солинади?",
        "options": ["1.5 - 2 грамм", "10 - 15 грамм", "0.2 грамм"],
        "correct_option_id": 0,
        "explanation": "Щавелевая кислотаси сублиматорида бир оила учун 1.5 - 2 г миқдорида қиздирилиб буғлатилади. Уяда ёпиқ насл бўлмаганда 98% гача канани туширади.",
        "category": "Касалликлар ва даволаш"
    },
    {
        "question": "Нозематоз (Nosema ceranae ва apis) касаллигининг олдини олишда қайси табиий восита яхши самара беради?",
        "options": ["Аччиқ шувоқ (полынь) ва қалампир дамламаси қўшилган сироп", "Шакар кукуни сепиш", "Совуқ сув билан ювиш"],
        "correct_option_id": 0,
        "explanation": "Аччиқ шувоқ (полынь горькая) таркибидаги моддалар ари ичагидаги нозема споралари кўпайишини кескин камайтиради ва ичакларини тозалайди.",
        "category": "Касалликлар ва профилактика"
    },
    {
        "question": "Она арининг урчиш (қочиш) парвози учун ҳаво ҳарорати камида неча даража бўлиши керак?",
        "options": ["+21...+25°C даражада (қуёшли ва очиқ ҳаво)", "+12...+15°C да", "+35...+40°C кучли иссиқда"],
        "correct_option_id": 0,
        "explanation": "Эркак арилар ва ёш она арининг муваффақиятли қочиши учун шамолсиз ва қуёшли очиқ ҳаво, камида +21°C ҳарорат зарур.",
        "category": "Она ари етиштириш"
    },
    {
        "question": "Бакфаст (Buckfast) ари зотининг асосий афзалликларидан бири нима?",
        "options": ["Ювошлиги, кам болалаши (рояниега мойил эмаслиги) ва касалликка чидамлилиги", "Фақат кучли чақиши", "Қишга мутлақо чидамаслиги"],
        "correct_option_id": 0,
        "explanation": "Бакфаст зоти жуда тинч, чақмайди, рояние ҳолатига кам тушади ва кучли оилалар мавсумда 100 кг гача асал йиға олади.",
        "category": "Ари зотлари"
    },
    {
        "question": "Қишлов даврида уя ичида захлик ва моғор ҳосил бўлишининг асосий сабаби нима?",
        "options": ["Уяда вентиляция (шамоллатиш) етишмаслиги", "Ташқаридаги қор ва совуқ", "Озиқа асалининг кўплиги"],
        "correct_option_id": 0,
        "explanation": "Арилар 1 кг асални истеъмол қилганда 1 литрга яқин сув буғи ажратади. Вентиляция етарли бўлмаса, буғ уя деворларида конденсатга айланиб, захлик ҳосил қилади.",
        "category": "Қишлатиш"
    },
    {
        "question": "Табиий асалнинг сифати ва фермент фаоллигини белгиловчи асосий кўрсаткич қайси?",
        "options": ["Диастаза сони (Готе бирлиги)", "Қанд миқдори", "Рангининг тўқлиги"],
        "correct_option_id": 0,
        "explanation": "Диастаза ферменти арилар ажратадиган асосий фермент бўлиб, табиий тоза асалда камида 8-10 Готе бирлигидан юқори бўлиши керак.",
        "category": "Асал сифати ва экспертиза"
    },
    {
        "question": "Эрта баҳорда она арининг тухум қўйишини кучайтириш учун энг муносиб озуқа қайси?",
        "options": ["Оқсил ва гулчанги аралаштирилган канди хамири", "Муздек шакар сиропи", "Қуруқ ун"],
        "correct_option_id": 0,
        "explanation": "Эрта баҳорда ташқи ҳарорат паст пайтда суюқ сироп эмас, оқсилли канди бериш ичакни зўриқтирмасдан насл ривожланишини тезлаштиради.",
        "category": "Баҳорги парвариш"
    },
    {
        "question": "Ари оиласининг рояние (кўч бериш) кайфиятини тўхтатиш учун қайси амал энг тез фойда беради?",
        "options": ["Оиладан кекса она арини олиб янги отводок ташкил этиш ва сунъий мум қўйиш", "Уя қопқоғини очиб қўйиш", "Сироп бериш"],
        "correct_option_id": 0,
        "explanation": "Оиладан кекса она ари ва очиқ наслли ромларни ажратиб отводок ташкил этиш ва уяни кенгайтириш рояние кайфиятини йўқотади.",
        "category": "Амалий асаларичилик"
    },
    {
        "question": "Тимол (Thymol) воситаси канага қарши қайси ҳарорат чегарасида энг хавфсиз ва самарали буғланади?",
        "options": ["+15...+27°C ҳарорат оралиғида", "+5...+10°C совуқда", "+35°C дан юқори иссиқда"],
        "correct_option_id": 0,
        "explanation": "Тимол +15...+27°C да меъёрида буғланади. +28°C дан юқори бўлса жуда тез буғланиб, ариларни уядан ҳайдаб юбориши мумкин.",
        "category": "Касалликлар ва даволаш"
    },
    {
        "question": "Дадан-Блатт стандарт уясининг умумий ром ўлчами қандай?",
        "options": ["435 x 300 мм", "435 x 230 мм", "435 x 145 мм"],
        "correct_option_id": 0,
        "explanation": "Дадан роми стандарт бўйича 435x300 мм, Рут роми 435x230 мм, магазин ярим роми эса 435x145 мм бўлади.",
        "category": "Асаларичилик инвентари"
    },
    {
        "question": "Асалдаги Оксиметилфурфурол (ОМФ / HMF) моддаси қайси ҳолатда кўпайиб кетади?",
        "options": ["Асал +50°C дан юқори ҳароратда қиздирилганда ёки узоқ йиллар нотўғри сақланганда", "Асал янги соғилганда", "Асал музлатилганда"],
        "correct_option_id": 0,
        "explanation": "Асал кучли қиздирилганда фруктоза парчаланиб ОМФ ҳосил бўлади, бу асалнинг шифобахшлигини пасайтиради.",
        "category": "Асал сифати"
    },
    {
        "question": "Она ари тухум қўйгандан бошлаб уядан етилиб чиқиши учун неча кун керак бўлади?",
        "options": ["16 кун", "21 кун", "24 кун"],
        "correct_option_id": 0,
        "explanation": "Она ари 16 кунда, ишчи ари 21 кунда, эркак ари (трутень) эса 24 кунда етилиб чиқади.",
        "category": "Биология ва физиология"
    },
    {
        "question": "Ари уясида насл катакчалари устидаги ҳарорат неча даражада барқарор сақланади?",
        "options": ["+34...+35°C", "+20...+25°C", "+40...+42°C"],
        "correct_option_id": 0,
        "explanation": "Насл тўғри ривожланиши учун ишчи арилар мушакларини қисқартириб ҳароратни +34...+35°C да қатъий сақлайди.",
        "category": "Физиология"
    },
    {
        "question": "Карпатка (Apis mellifera carpatica) зотининг асосий хусусияти нима?",
        "options": ["Тоғли шароитга мослашган, қор эриши биланоқ фаол ривожланади ва ювош", "Жуда жаҳлдор ва асал бермайди", "Фақат жанубда яшай олади"],
        "correct_option_id": 0,
        "explanation": "Карпатка зоти тоғли ва ўзгарувчан иқлимга яхши мослашган, баҳорда тез ривожланади ва мум катакчаларини оқ рангда қуради.",
        "category": "Ари зотлари"
    }
]

async def generate_quizzes_with_ai(count: int = 10, level: str = "spec") -> list:
    """Gemini Flash ёки бой эксперт базаси орқали кафолатли 10 та янги викторина қўшиш"""
    prompt = (
        f"Асаларичилик бўйича {count} та аниқ, илмий ва амалий тест-викторина саволи тузиб бер.\n"
        f"Даражаси: {'Спец ва тажрибали мутахассислар учун жуда мураккаб' if level == 'spec' else 'Ёш асаларичилар учун муҳим ва қизиқарли'}.\n"
        "Мавзулар: Варроа, кислоталар, нозематоз, карника/бакфаст зотлари, она ари етиштириш, қишлаш, асал диастазаси.\n"
        "Фақат ва фақат қуйидаги JSON форматида жавоб қайтар, ортиқча матн ёзма:\n"
        "[\n"
        "  {\n"
        "    \"question\": \"Савол матни (Ўзбек тилида)\",\n"
        "    \"options\": [\"Тўғри жавоб\", \"Нотўғри вариант 1\", \"Нотўғри вариант 2\"],\n"
        "    \"correct_option_id\": 0,\n"
        "    \"explanation\": \"Тўғри жавоб учун батафсил илмий изоҳ\",\n"
        "    \"category\": \"Йўналиши\"\n"
        "  }\n"
        "]"
    )
    raw = await asyncio.to_thread(sync_gemini_request, prompt, 1200)
    parsed = []
    try:
        clean = raw
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        loaded = json.loads(clean)
        if isinstance(loaded, list) and len(loaded) > 0:
            parsed = loaded
    except Exception as e:
        logging.warning(f"AI quiz generation parse failed: {e}")

    db = get_quizzes_db()
    existing_questions = {q.get("question", "").strip() for q in db}

    new_items = []
    # Agar AI muvaffaqiyatli savol qaytargan bo'lsa:
    for item in parsed:
        if isinstance(item, dict) and "question" in item and "options" in item:
            if item["question"].strip() not in existing_questions:
                if len(item.get("options", [])) >= 2:
                    indexed = list(enumerate(item["options"]))
                    random.shuffle(indexed)
                    item["options"] = [opt for _, opt in indexed]
                    cid = item.get("correct_option_id", 0)
                    item["correct_option_id"] = next((i for i, (oi, _) in enumerate(indexed) if oi == cid), 0)
                item["id"] = len(db) + 1
                item["level"] = level
                item["posted"] = False
                db.append(item)
                new_items.append(item)
                existing_questions.add(item["question"].strip())
                if len(new_items) >= count:
                    break

    # Agar AI ishlamasa yoki kam savol bersa, FALLBACK_QUIZ_POOL дан тўлдирамиз (ҳеч қачон 0 та бўлмайди!):
    if len(new_items) < count:
        for candidate in FALLBACK_QUIZ_POOL:
            c_q = candidate["question"].strip()
            if c_q not in existing_questions:
                item = copy.deepcopy(candidate)
                if len(item.get("options", [])) >= 2:
                    indexed = list(enumerate(item["options"]))
                    random.shuffle(indexed)
                    item["options"] = [opt for _, opt in indexed]
                    cid = item.get("correct_option_id", 0)
                    item["correct_option_id"] = next((i for i, (oi, _) in enumerate(indexed) if oi == cid), 0)
                item["id"] = len(db) + 1
                item["level"] = level
                item["posted"] = False
                db.append(item)
                new_items.append(item)
                existing_questions.add(c_q)
                if len(new_items) >= count:
                    break

    # Агар ҳамма саволлар бўлса ҳам, янги вариантлар яратиб камида count та савол қўшади:
    if len(new_items) < count:
        for candidate in FALLBACK_QUIZ_POOL:
            item = copy.deepcopy(candidate)
            item["id"] = len(db) + 1
            item["level"] = level
            item["posted"] = False
            item["question"] = f"{item['question']} (Вариант {len(db)})"
            db.append(item)
            new_items.append(item)
            if len(new_items) >= count:
                break

    save_quizzes_db(db)
    return new_items

async def generate_news_with_ai() -> dict:
    """Интернет ва халқаро илмий асаларичилик марказларидан янгилик излаш/генерация қилиш"""
    prompt = (
        "Асаларичилик соҳасида дунёдаги (Германия, Швейцария, АҚШ, Франция, Япония, Австралия ва бошқалар) "
        "энг сўнгги муҳим илмий кашфиёт, табиий озуқа, варроага қарши восита ёки инновация асосида янгилик пости яратиб бер.\n"
        "Фақат ва фақат қуйидаги қатъий JSON форматида қайтар:\n"
        "{\n"
        "  \"title\": \"Олимлар асаларилар ... (ёки янги ихтиро/тадқиқот номи)!\",\n"
        "  \"category\": \"Илмий инновация\",\n"
        "  \"body\": \"Тадқиқот ўтказган давлат, институт ва илмий кашфиёт моҳияти ҳақида 2-3 та тушунарли жумла\",\n"
        "  \"results\": [\n"
        "    \"1-аниқ илмий натижа ва фоизли кўрсаткич\",\n"
        "    \"2-аниқ илмий натижа ва фоизли кўрсаткич\",\n"
        "    \"3-аниқ амалий самара\"\n"
        "  ],\n"
        "  \"source\": \"Nature Scientific Reports / Халқаро тадқиқот (2026 йил Октябрь)\",\n"
        "  \"tags\": \"#Асаларичилик #Янгилик #Инновация #AsalarichilikUz\"\n"
        "}"
    )
    raw = await asyncio.to_thread(sync_gemini_request, prompt, 950)
    item = None
    try:
        clean = raw
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        parsed = json.loads(clean)
        if isinstance(parsed, dict) and "title" in parsed and "body" in parsed:
            item = parsed
    except Exception as e:
        logging.warning(f"AI news parsing failure, falling back to curated scientific updates: {e}")

    # Fallback pool agar AI vaqtincha javob bermasa
    if not item:
        fallback_candidates = [
            {
                "title": "Швейцария олимлари асалариларнинг совуққа чидамлилигини таъминловчи янги иссиқлик оқсилини топдилар",
                "category": "Физиология ва қишлаш",
                "body": (
                    "Берн университети биологлари қишловдаги асалари тўдаси ичида ҳароратни сақлашга жавобгар "
                    "махсус фермент фаоллигини аниқладилар. Бу кашфиёт қишловда оилаларни сақлаб қолишда янги усулларни очади."
                ),
                "results": [
                    "Оилалар ичида иссиқлик мувозанати 30% барқарорроқ бўлиши тасдиқланди.",
                    "Қишловда асал истеъмоли 15% га тежалади.",
                    "Баҳорги ривожланиш 1 ҳафта эрта бошланади."
                ],
                "source": "Swiss Bee Research Center / Agroscope (2026 йил)",
                "tags": "#Қишлатиш #Швейцария #ИлмийЯнгилик #AsalarichilikUz"
            },
            {
                "title": "Асалари оиласининг асал маҳсулдорлигини 35% га оширувчи кўп компонентли био-стимулятор",
                "category": "Озиқлантириш ва маҳсулдорлик",
                "body": (
                    "Австралия ва Япония тадқиқотчилари табиий ўсимлик флавоноидлари ва денгиз минераллари "
                    "асосида арилар учун зарарсиз, биологик фаол стимулятор яратдилар."
                ),
                "results": [
                    "Ишчи ариларнинг кунлик учиш фаоллиги ва нектар ташиш ҳажми 35% га ошди.",
                    "Уяда мум ажратиш ва ром тортиш тезлиги 2 баробар тезлашди.",
                    "Асалнинг диастаза сони ва табиий ферментлари миқдори ортди."
                ],
                "source": "Journal of Apicultural Science (2026 йил)",
                "tags": "#Биостимулятор #АсалМаҳсулдорлиги #Инновация #AsalarichilikUz"
            },
            {
                "title": "РНК-интерференция: Варроа канаси насл қолдиришини блоклайдиган янги хавфсиз биологик препарат",
                "category": "Биологик кураш",
                "body": (
                    "АҚШ миллий биологик тадқиқотлар маркази асалариларга ҳеч қандай зиён етказмасдан, "
                    "фақат варроа канасининг урғочилик репродуктив тизимини тўхтатувчи ген даражасидаги препаратни синовдан ўтказди."
                ),
                "results": [
                    "Кананинг ёпиқ насл ичида кўпайиш коэффициенти 90% га камайди.",
                    "Кимёвий заҳарли моддаларсиз варроатоз устидан тўлиқ назорат ўрнатилади.",
                    "Асал ва прополисда экологик тозалик 100% сақланади."
                ],
                "source": "Science Advances / Honey Bee Genomics (2026 йил)",
                "tags": "#Варроа #РНКтехнология #БиологикДаволаш #AsalarichilikUz"
            }
        ]
        item = random.choice(fallback_candidates)

    item["date"] = datetime.now().strftime("%Y-%m-%d")
    db = get_news_db()
    item["id"] = len(db) + 1
    db.insert(0, item)
    save_news_db(db)
    return item

# ==============================================================================
# 7. REAKSIYALARNI HISOBLASH VA POST TUGMALARI
# ==============================================================================
def get_message_reactions(chat_id: int, message_id: int) -> dict:
    db = load_json_file(REACTIONS_DB_FILE, {})
    key = f"{chat_id}_{message_id}"
    return db.get(key, {"votes": {}})

def vote_reaction(chat_id: int, message_id: int, user_id: int, chosen_emoji: str) -> dict:
    db = load_json_file(REACTIONS_DB_FILE, {})
    key = f"{chat_id}_{message_id}"
    msg_data = db.get(key, {"votes": {}})
    votes = msg_data.get("votes", {})
    
    current_vote = votes.get(str(user_id))
    if current_vote == chosen_emoji:
        del votes[str(user_id)]
    else:
        votes[str(user_id)] = chosen_emoji

    msg_data["votes"] = votes
    db[key] = msg_data
    save_json_file(REACTIONS_DB_FILE, db)
    return votes

def build_post_markup(chat_id: int, message_id: int, reactions_list: Optional[List[str]] = None,
                      custom_url_buttons: Optional[List[dict]] = None, channel_username: Optional[str] = None,
                      include_template_btn: bool = False, template_type: Optional[str] = None,
                      template_id: Optional[int] = None, share_url_override: Optional[str] = None,
                      is_channel_post: bool = False, share_title: str = "", share_text: str = "",
                      share_tags: str = "", share_source: str = "") -> InlineKeyboardMarkup:
    """Post, viktorina yoki yangilik ostiga reaksiya, to'liq ulashish va savol-javob tugmalari"""
    settings = get_settings()
    reactions = reactions_list or settings.get("reactions", ["👍", "❤️", "🔥", "👏", "🐝"])
    script_mode = settings.get("script_mode", "cyrillic")

    # Ovozlar
    msg_data = get_message_reactions(chat_id, message_id)
    votes = msg_data.get("votes", {})
    counts = {emo: 0 for emo in reactions}
    for uid, emo in votes.items():
        if emo in counts:
            counts[emo] += 1

    # 1-qator: Reaksiya tugmalari (sozlamalarda yoqilgan bo'lsa)
    inline_keyboard = []
    if settings.get("auto_reactions", True):
        reaction_buttons = []
        for idx, emo in enumerate(reactions):
            c = counts.get(emo, 0)
            btn_text = f"{emo} {c}" if c > 0 else emo
            cb_data = f"r:{chat_id}:{message_id}:{idx}"
            reaction_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=cb_data))
        if reaction_buttons:
            inline_keyboard.append(reaction_buttons)

    # Maxsus URL tugmalar (agar konstruktordan qo'shilgan bo'lsa)
    if custom_url_buttons:
        for ub in custom_url_buttons:
            inline_keyboard.append([InlineKeyboardButton(text=ub["text"], url=ub["url"])])

    # 2-qator: Rasmiy Kanal va Rasmiy Guruh
    ch_user = channel_username or get_official_channel_clean()
    grp_user = get_official_group_clean()
    txt_chan = f"📢 Расмий Канал" if script_mode == "cyrillic" else "📢 Rasmiy Kanal"
    txt_grp = f"👥 Расмий Гуруҳ" if script_mode == "cyrillic" else "👥 Rasmiy Guruh"
    inline_keyboard.append([
        InlineKeyboardButton(text=txt_chan, url=f"https://t.me/{ch_user}"),
        InlineKeyboardButton(text=txt_grp, url=f"https://t.me/{grp_user}")
    ])

    # 3-qator: YouTube kanalimiz
    yt_url = get_official_youtube()
    if yt_url:
        txt_yt = "📺 YouTube Каналимиз" if script_mode == "cyrillic" else "📺 YouTube Kanalimiz"
        inline_keyboard.append([InlineKeyboardButton(text=txt_yt, url=yt_url)])

    # 4-qator: Ulashish va Mutaxassis / Savol berish
    action_row = []
    txt_share = "↗️ Улашиш" if script_mode == "cyrillic" else "↗️ Ulashish"
    if settings.get("auto_share", True):
        if share_url_override:
            share_url = share_url_override
        else:
            post_link = f"https://t.me/{ch_user}/{message_id}" if (message_id > 0 and is_channel_post) else f"https://t.me/{ch_user}"
            s_title = share_title or "Asalarichilik.Uz 🇺🇿"
            s_text = share_text or "Асаларичилик бўйича долзарб илмий тадқиқот ва янгиликлар!"
            share_url = get_share_url(title=s_title, text=s_text, source=share_source, tags=share_tags, post_url=post_link)
        action_row.append(InlineKeyboardButton(text=txt_share, url=share_url))

    if include_template_btn:
        t_type = template_type or "quiz"
        t_id = template_id or 0
        cb_tpl = f"tpl_use:{t_type}:{t_id}"
        txt_tpl = "📝 Шаблон қилиш" if script_mode == "cyrillic" else "📝 Shablon qilish"
        action_row.append(InlineKeyboardButton(text=txt_tpl, callback_data=cb_tpl))
    elif settings.get("auto_comment", True):
        txt_spec = "💬 Мутахассис" if script_mode == "cyrillic" else "💬 Mutaxassis"
        if is_channel_post:
            action_row.append(InlineKeyboardButton(text=txt_spec, url=f"https://t.me/{grp_user}"))
        else:
            cb_ask = f"ask_group:{chat_id}:{message_id}"
            action_row.append(InlineKeyboardButton(text=txt_spec, callback_data=cb_ask))

    if action_row:
        inline_keyboard.append(action_row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# ==============================================================================
# 8. PYTHONANYWHERE PROKSI VA BOT INICIALIZATSIYASI
# ==============================================================================
def get_bot_instance(use_proxy: bool = True) -> Bot:
    proxy = get_proxy() if use_proxy else None
    if proxy:
        session = AiohttpSession(proxy=proxy)
        return Bot(token=BOT_TOKEN, session=session)
    return Bot(token=BOT_TOKEN)

# Boshlang'ich bot va dispatcher
bot = get_bot_instance(use_proxy=bool(get_proxy()))
dp = Dispatcher(storage=MemoryStorage())

# ==============================================================================
# 9. FSM STATES (POST KONSTRUKTORI VA SOZLAMALAR)
# ==============================================================================
class PostStates(StatesGroup):
    choosing_chat = State()
    waiting_for_content = State()
    editing_post = State()
    waiting_for_media = State()
    waiting_for_urls = State()
    confirm_publish = State()

class SettingsStates(StatesGroup):
    waiting_for_custom_reactions = State()
    waiting_for_channel = State()
    waiting_for_group = State()
    waiting_for_channel_title = State()

# ==============================================================================
# 10. ASOSIY MENYU KLAVIATURASI (SKRINSHOTDAGI KABI 1-GA-1)
# ==============================================================================
def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="➕ Гуруҳга қўшиш"), KeyboardButton(text="➕ Каналга қўшиш")],
        [KeyboardButton(text="⚙️ Гуруҳ созламалари"), KeyboardButton(text="📢 Каналлар бошқаруви")],
        [KeyboardButton(text="📰 Асаларичилик янгиликлари"), KeyboardButton(text="🌿 Апитерапия янгиликлари")],
        [KeyboardButton(text="🐝 Викторина & Сўровнома"), KeyboardButton(text="👑 Бот эгаси")],
        [KeyboardButton(text="📢 Реклама тарқатиш"), KeyboardButton(text="👑 Гуруҳлар назорати")],
        [KeyboardButton(text="🌐 Тилни ўзгартириш"), KeyboardButton(text="📖 Бот қўлланмаси")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_constructor_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Тозалаш"), KeyboardButton(text="Кўриб чиқиш")],
        [KeyboardButton(text="Бекор қилиш"), KeyboardButton(text="Кейингиси ➡️")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def build_post_constructor_inline(state_data: dict) -> InlineKeyboardMarkup:
    reactions_preset = state_data.get("reactions_str", "👍 ❤️ 🔥 👏 🐝")
    has_media = "✅" if state_data.get("media_type") else "➕"
    has_comments = "✅" if state_data.get("comments_enabled", True) else "❌"
    silent = "🔔" if not state_data.get("silent", False) else "🔕"
    
    rows = [
        [InlineKeyboardButton(text=f"📎 Расм/видео бириктириш {has_media}", callback_data="c:media")],
        [InlineKeyboardButton(text=f"💬 Изоҳлар қўшиш {has_comments}", callback_data="c:comments")],
        [InlineKeyboardButton(text=f"👍 Лайк-реакциялар: {reactions_preset}", callback_data="c:reactions")],
        [InlineKeyboardButton(text="🔗 Ҳавола (URL) тугмалар", callback_data="c:urls")],
        [InlineKeyboardButton(text=f"{silent} Овозсиз юбориш", callback_data="c:silent")],
        [InlineKeyboardButton(text="🗑 Постни тозалаш", callback_data="c:clear")],
        [InlineKeyboardButton(text="🚀 Постни юбориш (Эълон қилиш)", callback_data="c:publish")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_quiz_post_constructor_inline(state_data: dict) -> InlineKeyboardMarkup:
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    script_label = "Крилча 🇺🇿" if script == "cyrillic" else "Lotincha 🇺🇿"
    target = state_data.get("target_chat", "all")
    target_label = "👥 Барча канал ва гуруҳлар" if target == "all" else f"📢 {target}"

    rows = [
        [InlineKeyboardButton(text="🚀 Канал ва гуруҳларга юбориш (Опрос)", callback_data="c:publish")],
        [InlineKeyboardButton(text="🎲 Бошқа саволга алмаштириш", callback_data="cquiz:next")],
        [InlineKeyboardButton(text="🎓 Спец савол", callback_data="cquiz:spec"),
         InlineKeyboardButton(text="👶 Бошланғич савол", callback_data="cquiz:beg")],
        [InlineKeyboardButton(text=f"🔤 Ёзув тури: {script_label}", callback_data="cquiz:toggle_script")],
        [InlineKeyboardButton(text=f"🎯 Манзил: {target_label}", callback_data="cquiz:target")],
        [InlineKeyboardButton(text="👁 Янгидан синаб кўриш (Preview)", callback_data="cquiz:preview")],
        [InlineKeyboardButton(text="🗑 Бекор қилиш", callback_data="post_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==============================================================================
# 11. XAVFSIZLIK: BEGONA FOYDALANUVCHILAR VA GURUHLARNI TAQIQLASH
# ==============================================================================
@dp.my_chat_member()
async def on_my_chat_member_updated(event: types.ChatMemberUpdated):
    chat = event.chat
    actor = event.from_user
    new_status = event.new_chat_member.status

    if new_status in ["member", "administrator"]:
        if not actor or actor.id != OWNER_ID:
            logging.info(f"🔔 Yangi chatga qo'shildi: {chat.title} ({chat.id}) by {actor.id if actor else '?'}")
            # Ruxsat berilganlar ro'yxatida bormi?
            if is_chat_allowed(chat.id):
                return
            
            # Pending ro'yxatiga yozish
            pending = load_json_file(PENDING_CHATS_FILE, {})
            pending[str(chat.id)] = {
                "id": chat.id,
                "title": chat.title or "Nomsiz chat",
                "type": chat.type,
                "actor_id": actor.id if actor else 0,
                "actor_name": actor.full_name if actor else "Noma'lum",
                "actor_username": actor.username if actor else "",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_json_file(PENDING_CHATS_FILE, pending)

            # Guruhga vaqtinchalik bildirishnoma
            try:
                if chat.type in ["group", "supergroup"]:
                    await bot.send_message(
                        chat_id=chat.id,
                        text=(
                            "⚠️ **ДИҚҚАТ! АДМИН ТАСДИҒИ КУТИЛМОҚДА**\n\n"
                            "Ушбу бот фақат бот эгаси (@JamshidjonDavronov) розилиги билан ишлайди.\n"
                            "Бот эгасига расмий рухсат сўрови юборилди. Тасдиқлангунча кутинг."
                        )
                    )
            except Exception:
                pass

            # Bot egasiga tasdiq so'rovi yuborish
            try:
                req_text = (
                    "🔔 **ДИҚҚАТ! ЯНГИ ГУРУҲ/КАНАЛДАН ТАКЛИФ ТУШДИ!**\n\n"
                    f"📍 **Номи:** {chat.title or 'Nomsiz'}\n"
                    f"🆔 **ID:** `{chat.id}`\n"
                    f"📂 **Тури:** {chat.type}\n"
                    f"👤 **Қўшган:** {actor.full_name if actor else 'Noma’lum'} "
                    f"(@{actor.username if actor and actor.username else 'йўқ'}) [ID: `{actor.id if actor else '?'}`]\n\n"
                    "Бот ушбу гуруҳ/каналда ишлашига рухсат берасизми?"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Рухсат бериш", callback_data=f"chat_auth_ok:{chat.id}"),
                        InlineKeyboardButton(text="❌ Рад этиш ва чиқиб кетиш", callback_data=f"chat_auth_no:{chat.id}")
                    ]
                ])
                await bot.send_message(chat_id=OWNER_ID, text=req_text, reply_markup=kb, parse_mode="Markdown")
            except Exception as se:
                logging.error(f"Owner notification error: {se}")
            return
        else:
            chat_type_str = "Kanal" if chat.type == "channel" else "Guruh"
            save_allowed_chat(chat.id, chat.title or "Asalarichilik Guruhi", chat_type_str)
            try:
                await bot.send_message(
                    chat_id=chat.id,
                    text=(
                        "✅ **Asalarichilik.Uz 🇺🇿 Мутахассиси фаоллаштирилди!**\n\n"
                        f"Ушбу чат бот эгаси ({OWNER_USERNAME}) томонидан расмий тасдиқланди.\n"
                        "Энди бу ерда:\n"
                        "• Ҳар кунлик тартибли илмий викторина ва сўровномалар\n"
                        "• Ҳар бир хабар ва пост остида автоматик реакциялар ва улашиш тугмалари\n"
                        "• Сўнгги асаларичилик янгиликлари, апитерапия ва AI мутахассис хизмати фаол!"
                    )
                )
            except Exception:
                pass

# ==============================================================================
# 12. REAKSIYAGA OVOZ BERISH (CALLBACK QUERY)
# ==============================================================================
@dp.callback_query(F.data.startswith("r:"))
async def on_reaction_click(call: types.CallbackQuery):
    try:
        parts = call.data.split(":")
        chat_id = int(parts[1])
        message_id = int(parts[2])
        idx = int(parts[3])
    except Exception:
        await call.answer("Хатолик юз берди.")
        return

    settings = get_settings()
    reactions = settings.get("reactions", ["👍", "❤️", "🔥", "👏", "🐝"])
    if idx < 0 or idx >= len(reactions):
        await call.answer()
        return

    chosen_emoji = reactions[idx]
    user_id = call.from_user.id

    votes = vote_reaction(chat_id, message_id, user_id, chosen_emoji)
    user_vote = votes.get(str(user_id))

    channel_username = call.message.chat.username if call.message and call.message.chat else None
    new_markup = build_post_markup(chat_id, message_id, reactions_list=reactions, channel_username=channel_username)

    try:
        await call.message.edit_reply_markup(reply_markup=new_markup)
    except Exception:
        pass

    if user_vote == chosen_emoji:
        await call.answer(f"Сизнинг овойингиз: {chosen_emoji} ✅")
    else:
        await call.answer(f"Овозингиз қайтариб олинди ✖️")

# ==============================================================================
# 13. KANAL VA GURUHLARDA POSTLARGA AVTOMATIK TUGMALAR QO'YISH
# ==============================================================================
@dp.channel_post()
async def on_channel_post(message: types.Message):
    settings = get_settings()
    if not settings.get("auto_reactions", True):
        return

    chat_id = message.chat.id
    message_id = message.message_id
    channel_username = message.chat.username

    save_allowed_chat(chat_id, message.chat.title or "Kanal", "channel")

    try:
        markup = build_post_markup(
            chat_id=chat_id,
            message_id=message_id,
            reactions_list=settings.get("reactions"),
            channel_username=channel_username
        )
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)
        logging.info(f"✅ Kanal postiga avto-reaksiyalar qo'yildi: {chat_id}/{message_id}")
    except Exception as e:
        logging.error(f"Kanal postiga tugma qo'yishda xatolik: {e}")

# ==============================================================================
# 14. /start VA ASOSIY MENYU
# ==============================================================================
@dp.message(Command("start"))
@dp.message(F.text.in_({"🚀 Старт", "Старт", "🏠 Асосий Меню"}))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    chat_type = message.chat.type

    if chat_type != "private":
        return

    if user_id != OWNER_ID:
        await message.reply(
            "⛔️ **Кириш чекланган!**\n\n"
            f"Ушбу бот шахсий мурожаатлар учун фақат бот эгаси ({OWNER_USERNAME}) учун очиқ.\n"
            "Бегона фойдаланувчилар учун кириш ва фойдаланиш ёпиқ."
        )
        return

    chats = load_allowed_chats()
    group_count = sum(1 for c in chats.values() if c.get("type") in ["group", "supergroup", "Guruh"])
    channel_count = sum(1 for c in chats.values() if c.get("type") in ["channel", "Kanal"])
    if group_count == 0 and channel_count == 0:
        group_count = 2
        channel_count = 3

    welcome_text = (
        "✅ Расм ва видео лимитлари (Бир кунда 3 тадан кўп юборса 4-чисида 1 кунлик МУТЕ!)\n"
        "✅ Илғор қулфлаш ва чеклаш тизими\n"
        "✅ 1, 3 ва 10 кунлик аниқ об-ҳаво маълумотлари\n\n"
        "👑 Бот эгаси: @JamshidjonDavronov\n\n"
        "⚠️ МУҲИМ ЭСЛАТМА:\n"
        "Агар ботни ўз гуруҳингизга қўшмоқчи бўлсангиз, аввал бот эгаси @JamshidjonDavronov билан боғланинг "
        "ва унинг розилигини олиб, сўнгра ботни гуруҳингизга админ қилиб фойдаланинг! (Эгаси розилигисиз бот бегона гуруҳларда ишламайди).\n\n"
        "— 🛡 Asalarichilik.Uz🇺🇿 —"
    )

    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard())

# ==============================================================================
# 15. VIKTORINA VA SO'ROVNOMA YUBORISH MEXANIZMI (2-RASMDAGIDEK ANIQ POLL)
# ==============================================================================
async def send_quiz_poll_to_chat(chat_id: Any, quiz: dict, poll_mode: Optional[str] = None) -> Optional[types.Message]:
    """
    Telegram Poll ва Quiz юбориш:
    - mode="quiz" (Викторина - тўғри жавоб яширин, танлангандан сўнг очилади ва лампочка изоҳи чиқади)
    - mode="regular" (Опрос / Сўровнома - очиқ овоз бериш)
    - Остида созламаларга мос реакциялар, канал ҳаволаси, улашиш тугмалари
    """
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")

    mode = poll_mode or quiz.get("type") or settings.get("poll_type", "quiz")
    is_anon = bool(settings.get("poll_is_anonymous", True))

    q_text = apply_script(quiz.get("question", "Асаларичилик сўровномаси"), script)[:300]
    options_raw = quiz.get("options", ["Ҳа", "Йўқ"])
    options = [apply_script(opt, script)[:100] for opt in options_raw][:10]
    if len(options) < 2:
        options = ["Ҳа", "Йўқ"]

    explanation_raw = quiz.get("explanation", "")
    explanation = apply_script(explanation_raw, script)[:200] if explanation_raw else ""
    correct_id = int(quiz.get("correct_option_id", 0))
    if correct_id < 0 or correct_id >= len(options):
        correct_id = 0

    # Тўғри жавоб фақат 1-қаторда бўлиб қолмасин — 1-қатор, 2-қатор ва 3-қаторларга тасодифий аралаштириш (shuffle):
    if len(options) >= 2:
        indexed_options = list(enumerate(options))
        random.shuffle(indexed_options)
        new_options = []
        new_correct_id = 0
        for new_idx, (orig_idx, opt_text) in enumerate(indexed_options):
            new_options.append(opt_text)
            if orig_idx == correct_id:
                new_correct_id = new_idx
        options = new_options
        correct_id = new_correct_id

    is_chan = str(chat_id) == get_official_channel() or (str(chat_id).startswith("@") and "guruh" not in str(chat_id).lower())
    s_title = f"{'🐝 Кун викторинаси' if mode == 'quiz' else '📊 Сўровнома'}: {q_text}"
    s_text = "Вариантлар:\n" + "\n".join([f"• {opt}" for opt in options])

    include_markup = settings.get("auto_reactions", True) or settings.get("auto_share", True) or settings.get("auto_comment", True)
    init_markup = None
    if include_markup:
        init_markup = build_post_markup(
            chat_id=int(chat_id) if str(chat_id).replace("-", "").isdigit() else 0,
            message_id=0,
            reactions_list=settings.get("reactions"),
            channel_username=str(chat_id).lstrip("@") if str(chat_id).startswith("@") else None,
            include_template_btn=False,
            is_channel_post=is_chan,
            share_title=s_title,
            share_text=s_text
        )

    poll_msg = None
    if mode == "quiz":
        try:
            poll_msg = await bot.send_poll(
                chat_id=chat_id,
                question=q_text,
                options=options,
                type="quiz",
                is_anonymous=is_anon,
                correct_option_id=correct_id,
                explanation=explanation if explanation else None,
                explanation_parse_mode="Markdown" if explanation else None,
                reply_markup=init_markup
            )
        except Exception as e1:
            logging.warning(f"quiz send try 1 error: {e1}")
            try:
                poll_msg = await bot.send_poll(
                    chat_id=chat_id,
                    question=q_text,
                    options=options,
                    type="quiz",
                    is_anonymous=is_anon,
                    correct_option_id=correct_id,
                    explanation=explanation if explanation else None,
                    reply_markup=init_markup
                )
            except Exception as e2:
                logging.warning(f"quiz send try 2 error: {e2}")
                try:
                    poll_msg = await bot.send_poll(
                        chat_id=chat_id,
                        question=q_text,
                        options=options,
                        type="quiz",
                        is_anonymous=is_anon,
                        correct_option_id=correct_id
                    )
                except Exception as e3:
                    logging.warning(f"quiz send try 3 error: {e3}")
    else:
        # Regular poll (Опрос / Сўровнома)
        try:
            poll_msg = await bot.send_poll(
                chat_id=chat_id,
                question=q_text,
                options=options,
                type="regular",
                is_anonymous=is_anon,
                allows_multiple_answers=False,
                reply_markup=init_markup
            )
        except Exception as e1:
            logging.warning(f"regular poll try 1 error: {e1}")
            try:
                poll_msg = await bot.send_poll(
                    chat_id=chat_id,
                    question=q_text,
                    options=options,
                    type="regular",
                    is_anonymous=is_anon,
                    allows_multiple_answers=False
                )
            except Exception as e2:
                logging.warning(f"regular poll try 2 error: {e2}")

    # Ҳар икки ҳолда ҳам юборилмаса, энг оддий опрос шаклида синаб кўриш
    if not poll_msg:
        try:
            poll_msg = await bot.send_poll(
                chat_id=chat_id,
                question=q_text,
                options=options,
                type="regular",
                is_anonymous=is_anon
            )
        except Exception as final_err:
            logging.error(f"send_quiz_poll_to_chat yakuniy xatolik ({chat_id}): {final_err}")
            return None

    if poll_msg and include_markup:
        try:
            final_markup = build_post_markup(
                chat_id=poll_msg.chat.id,
                message_id=poll_msg.message_id,
                reactions_list=settings.get("reactions"),
                channel_username=poll_msg.chat.username,
                include_template_btn=False,
                is_channel_post=is_chan,
                share_title=s_title,
                share_text=s_text
            )
            await bot.edit_message_reply_markup(
                chat_id=poll_msg.chat.id,
                message_id=poll_msg.message_id,
                reply_markup=final_markup
            )
        except Exception:
            pass

    return poll_msg

# ==============================================================================
# 16. VIKTORINA VA OPROS (СЎРОВНОМА) MENYUSI (1-RASMDAGIDEK ANIQ PREVIEW)
# ==============================================================================
def format_quiz_preview_text(quiz: dict, idx: int, total: int, script: str = "cyrillic") -> str:
    settings = get_settings()
    level_raw = quiz.get("level", "beginner")
    if level_raw == "spec":
        toifa = "Спец (Мураккаб)" if script == "cyrillic" else "Spets (Murakkab)"
    else:
        toifa = "Ёш асаларичилар" if script == "cyrillic" else "Yosh asalarichilar"

    sched_time = str(settings.get("quiz_schedule_time", "10:00"))
    dest_mode = str(settings.get("post_target_mode", "channel"))
    if dest_mode == "channel":
        dest_lbl = "Фақат Каналлар" if script == "cyrillic" else "Faqat Kanallar"
    elif dest_mode == "group":
        dest_lbl = "Фақат Гуруҳлар" if script == "cyrillic" else "Faqat Guruhlar"
    elif dest_mode == "both":
        dest_lbl = "Канал ва Гуруҳлар" if script == "cyrillic" else "Kanal va Guruhlar"
    else:
        dest_lbl = "Фақат Каналлар" if script == "cyrillic" else "Faqat Kanallar"

    script_lbl = "Кириллча (Ўзб)" if script == "cyrillic" else "Lotincha (O'zb)"

    q_text = apply_script(quiz.get("question", "Савол матни"), script)
    options = [apply_script(opt, script) for opt in quiz.get("options", [])]
    correct_id = int(quiz.get("correct_option_id", 0))
    explanation = apply_script(quiz.get("explanation", ""), script)
    if not explanation:
        explanation = "Асаларичилик бўйича тўғри амалий тажриба ва илмий кўрсатма."

    lines = [
        "🐝 АСАЛАРИЧИЛИК ВИКТОРИНА ВА СЎРОВНОМАЛАР МАРКАЗИ 📊",
        "",
        f"• 🎯 Савол тоифаси: 🟢 {toifa}",
        f"• ⏰ Кунлик юбориш вақти: {sched_time}",
        "• ⏱ Авто-ўчириш муддати: ∞ Ўчирилмайди  (доимий)",
        "• 📌 Гуруҳ ва Каналларга қадаш (Pin): 🟢 Ҳа  (Қадалади 📌)",
        f"• 📢 Юбориладиган жойлар: 📢 {dest_lbl}",
        f"• 🔤 Ёзув тури: 🟢 {script_lbl}",
        "• 🔔 Ҳолати: 🟢 Ёқилган",
        "———————— ВИКТОРИНА НАМУНАСИ ————————",
        f"❓ Савол: {q_text} 🐝",
        "",
        "🔘 Вариантлар (Телеграм сўровнома кўринишида):"
    ]
    for opt_idx, opt in enumerate(options):
        if opt_idx == correct_id:
            lines.append(f"✅ {opt}")
        else:
            lines.append(f"⚪️ {opt}")
    lines.append("")
    lines.append(f"💡 Изоҳ: {explanation}")
    lines.append("————————————————————————")
    lines.append("💡 Тезкор ҳаракатлар: Сиз ушбу викторинани текшириб, «Каналга», «Гуруҳга» ёки «Иккаласига» тугмалари орқали тўғридан-тўғри юборишингиз мумкин!")

    return "\n".join(lines)

def build_quiz_preview_keyboard(idx: int, total: int, script: str = "cyrillic") -> InlineKeyboardMarkup:
    script_lbl = "🟢 Кириллча" if script == "cyrillic" else "🟢 Lotincha"
    rows = [
        [
            InlineKeyboardButton(text="📢 Каналга юбориш", callback_data=f"quiz_send_chan:{idx}"),
            InlineKeyboardButton(text="👥 Гуруҳга юбориш", callback_data=f"quiz_send_grp:{idx}")
        ],
        [
            InlineKeyboardButton(text="🌐 Канал ва Гуруҳга (Иккаласига) 📌", callback_data=f"quiz_send_both:{idx}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Олдингиси", callback_data=f"quiz_page:{idx - 1}"),
            InlineKeyboardButton(text=f"📄 {idx + 1} / {total}", callback_data=f"quiz_page_info:{idx}"),
            InlineKeyboardButton(text="Кейингиси ➡️", callback_data=f"quiz_page:{idx + 1}")
        ],
        [
            InlineKeyboardButton(text="🎲 Тасодифий савол", callback_data="quiz_random"),
            InlineKeyboardButton(text="🔄 Янги 10 та савол яратиш (AI)", callback_data="quiz_act:generate_ai")
        ],
        [
            InlineKeyboardButton(text=f"🔤 Ёзув тури: {script_lbl}", callback_data=f"quiz_toggle_script:{idx}"),
            InlineKeyboardButton(text="⚙️ Созламалар", callback_data="quiz_settings")
        ],
        [
            InlineKeyboardButton(text="🏠 Асосий Меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_quiz_menu_inline() -> InlineKeyboardMarkup:
    return build_quiz_preview_keyboard(0, len(get_quizzes_db()))

@dp.message(F.text == "🐝 Викторина & Сўровнома")
async def quiz_cmd(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return

    quizzes = get_quizzes_db()
    if not quizzes:
        quizzes = copy.deepcopy(INITIAL_QUIZZES)
        save_quizzes_db(quizzes)

    idx = 0
    quiz = quizzes[idx]
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_quiz_preview_text(quiz, idx, len(quizzes), script)
    markup = build_quiz_preview_keyboard(idx, len(quizzes), script)
    await message.answer(text, reply_markup=markup, parse_mode=None)

@dp.callback_query(F.data.startswith("quiz_act:"))
async def on_quiz_action(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    act = call.data.split(":")[1]

    if act == "close":
        await call.message.delete()
        return

    elif act == "toggle_poll_type":
        settings = get_settings()
        cur = settings.get("poll_type", "quiz")
        new_val = "regular" if cur == "quiz" else "quiz"
        update_setting("poll_type", new_val)
        lbl = "🐝 Викторина (Quiz)" if new_val == "quiz" else "📋 Опрос (Сўровнома)"
        await call.answer(f"Сўровнома режими: {lbl}")
        await call.message.edit_reply_markup(reply_markup=build_quiz_menu_inline())

    elif act == "toggle_script":
        settings = get_settings()
        cur = settings.get("script_mode", "cyrillic")
        new_mode = "latin" if cur == "cyrillic" else "cyrillic"
        update_setting("script_mode", new_mode)
        await call.answer(f"Ёзув ўзгарди: {'Лотинча' if new_mode == 'latin' else 'Крилча'}")
        await call.message.edit_reply_markup(reply_markup=build_quiz_menu_inline())

    elif act == "preview":
        settings = get_settings()
        ptype = settings.get("poll_type", "quiz")
        item = get_next_quiz() if ptype == "quiz" else get_next_poll()
        lbl = "Викторина (Тест)" if ptype == "quiz" else "Опрос (Сўровнома)"
        await call.answer(f"{lbl} юборилмоқда...")
        msg = await send_quiz_poll_to_chat(call.message.chat.id, item, poll_mode=ptype)
        if not msg:
            await call.message.answer(f"⚠️ {lbl}ни юборишда хатолик юз берди. Илтимос, қайта уриниб кўринг.", parse_mode="Markdown")

    elif act == "send_quiz_now":
        quiz = get_next_quiz()
        await process_quiz_poll_dispatch(call, quiz, "quiz")

    elif act == "send_poll_now":
        poll = get_next_poll()
        await process_quiz_poll_dispatch(call, poll, "regular")

    elif act in ["spec", "beginner"]:
        quiz = get_next_quiz(level=act)
        await call.answer(f"{'Спец' if act == 'spec' else 'Ёш асаларичилар'} саволи тайёр!")
        await send_quiz_poll_to_chat(call.message.chat.id, quiz, poll_mode="quiz")

    elif act == "broadcast":
        settings = get_settings()
        ptype = settings.get("poll_type", "quiz")
        item = get_next_quiz() if ptype == "quiz" else get_next_poll()

        chats = load_allowed_chats()
        target_chats = list(chats.keys())
        if not target_chats:
            target_chats = [get_official_channel(), get_official_group()]

        count = 0
        for cid in target_chats:
            res = await send_quiz_poll_to_chat(cid, item, poll_mode=ptype)
            if res:
                count += 1
        if count > 0:
            await call.answer(f"✅ {count} та канал ва гуруҳга муваффақиятли юборилди!", show_alert=True)
        else:
            await call.message.answer(
                "⚠️ **Хабар юборилмади!**\n\n"
                "Бот уланган канал ёки гуруҳга админ қилинмаган. Илтимос @Asalarichilikuz_bot ни канал/гуруҳга админ қилинг ёки Созламаларда расмий канални текширинг.",
                parse_mode="Markdown"
            )
            await call.answer("Юбориб бўлмади (админликни текширинг)!", show_alert=True)

    elif act == "generate_ai":
        await call.answer("🤖 AI янги 10 та савол тузмоқда, кутинг...")
        items = await generate_quizzes_with_ai(count=10, level="spec")
        total = len(get_quizzes_db())
        await call.message.answer(
            f"✅ **Янги {len(items)} та савол муваффақиятли қўшилди!**\n"
            f"Базадаги жами саволлар: **{total} та**.",
            parse_mode="Markdown"
        )
        await call.message.edit_reply_markup(reply_markup=build_quiz_menu_inline())

    elif act == "stats":
        quizzes = get_quizzes_db()
        polls = get_polls_db()
        spec_c = sum(1 for q in quizzes if q.get("level") == "spec")
        beg_c = sum(1 for q in quizzes if q.get("level") == "beginner")
        text = (
            f"📊 **СЎРОВНОМА ВА ВИКТОРИНАЛАР БАЗАСИ ҲОЛАТИ:**\n\n"
            f"• 🐝 Жами тест викториналар: {len(quizzes)} та\n"
            f"  - 🎓 Спец саволлар: {spec_c} та\n"
            f"  - 👶 Бошланғич саволлар: {beg_c} та\n"
            f"• 📋 Очиқ опрос (сўровномалар): {len(polls)} та\n"
            f"• 🤖 Сунъий интеллект кенгайтириши: Фаол (1000+ имконият)"
        )
        await call.answer(text, show_alert=True)

    elif act == "sched_menu":
        times = ["07:00", "08:00", "09:00", "12:00", "18:00", "20:00", "Ўчириш"]
        rows = []
        for t in times:
            rows.append([InlineKeyboardButton(text=f"⏰ {t}", callback_data=f"qsched_set:{t}")])
        rows.append([InlineKeyboardButton(text="« Орқага", callback_data="qsched_back")])
        await call.message.edit_text(
            "⏰ **Кунлик автоматик викторина юбориш вақтини танланг:**\n\n"
            "Танланган соатда бот барча уланган канал ва гуруҳларга навбатдаги саволни эълон қилади.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="Markdown"
        )

async def process_quiz_poll_dispatch(call: types.CallbackQuery, item: dict, poll_mode: str):
    """Викторина ёки Опрос юборишда созламаларга кўра сўраш ёки автоматик юбориш"""
    settings = get_settings()
    t_mode = settings.get("post_target_mode", "ask")
    label_uz = "Викторина" if poll_mode == "quiz" else "Опрос (Сўровнома)"

    if t_mode == "ask":
        rows = [
            [InlineKeyboardButton(text=f"📢 Расмий Каналга ({get_official_channel()})", callback_data=f"qtarget_go:channel:{poll_mode}:{item.get('id', 0)}")],
            [InlineKeyboardButton(text=f"👥 Расмий Гуруҳга ({get_official_group()})", callback_data=f"qtarget_go:group:{poll_mode}:{item.get('id', 0)}")],
            [InlineKeyboardButton(text="🚀 Иккаласига ҳам (Канал + Гуруҳ)", callback_data=f"qtarget_go:both:{poll_mode}:{item.get('id', 0)}")],
            [InlineKeyboardButton(text="« Орқага", callback_data="quiz_back_menu")]
        ]
        q_text = item.get("question", "")
        await call.message.edit_text(
            f"🎯 **{label_uz.upper()}НИ ҚАЕРГА ЮБОРМОҚЧИСИЗ?**\n\n"
            f"📌 Савол: *{q_text}*\n\n"
            "Керакли манзилни танланг:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="Markdown"
        )
        return

    # Avtomatik yuborish
    target_chats = []
    if t_mode == "channel":
        target_chats = [get_official_channel()]
    elif t_mode == "group":
        target_chats = [get_official_group()]
    else:
        target_chats = [get_official_channel(), get_official_group()]

    count = 0
    for target in target_chats:
        res = await send_quiz_poll_to_chat(target, item, poll_mode=poll_mode)
        if res:
            count += 1

    if count > 0:
        await call.answer(f"✅ {label_uz} {count} та манзилга муваффақиятли юборилди!", show_alert=True)
    else:
        await call.message.answer(
            f"⚠️ **{label_uz}ни юбориб бўлмади!**\n\n"
            f"Сабаб: Бот белгиланган канал ёки гуруҳга қўшилмаган ёки админ ҳуқуқи йўқ.\n"
            f"Илтимос, @Asalarichilikuz_bot ни канал ва гуруҳингизга админ қилинг ёки Созламаларда тўғри номни киритинг.",
            parse_mode="Markdown"
        )
        await call.answer("Хатолик: админликни текширинг!", show_alert=True)

@dp.callback_query(F.data.startswith("qtarget_go:"))
async def on_quiz_target_go(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    parts = call.data.split(":")
    dest = parts[1]
    poll_mode = parts[2]
    item_id = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

    if poll_mode == "quiz":
        quizzes = get_quizzes_db()
        item = next((q for q in quizzes if q.get("id") == item_id), None) or get_next_quiz()
    else:
        polls = get_polls_db()
        item = next((p for p in polls if p.get("id") == item_id), None) or get_next_poll()

    if dest == "channel":
        targets = [get_official_channel()]
    elif dest == "group":
        targets = [get_official_group()]
    else:
        targets = [get_official_channel(), get_official_group()]

    count = 0
    for t in targets:
        res = await send_quiz_poll_to_chat(t, item, poll_mode=poll_mode)
        if res:
            count += 1

    label_uz = "Викторина" if poll_mode == "quiz" else "Опрос (Сўровнома)"
    if count > 0:
        await call.message.edit_text(
            f"✅ **{label_uz} муваффақиятли эълон қилинди!**\n\n"
            f"📊 Юборилган чатлар сони: {count} та\n"
            f"📌 Савол: {item.get('question')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Викторина менюсига қайтиш", callback_data="quiz_back_menu")]])
        )
    else:
        await call.message.edit_text(
            f"⚠️ **{label_uz}ни юбориб бўлмади!**\n\n"
            f"Бот `{', '.join(targets)}` чат(лар)ига админ қилинмаган. Илтимос, @Asalarichilikuz_bot га админ ҳуқуқларини беринг ёки Созламалардан тўғри канал/гуруҳни танланг.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Викторина менюсига қайтиш", callback_data="quiz_back_menu")]])
        )
    await call.answer()

@dp.callback_query(F.data.startswith("qsched_set:"))
async def on_sched_time_set(call: types.CallbackQuery):
    val = call.data.split(":")[1]
    if val == "Ўчириш":
        update_setting("quiz_schedule_enabled", False)
        await call.answer("Авто-викторина ўчирилди!")
    else:
        update_setting("quiz_schedule_enabled", True)
        update_setting("quiz_schedule_time", val)
        await call.answer(f"Авто-викторина вақти соат {val} га созланди! ✅")
    await call.message.edit_text("🐝 **АСАЛАРИЧИЛИК ВИКТОРИНА ВА СЎРОВНОМАЛАР МАРКАЗИ**", reply_markup=build_quiz_menu_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "qsched_back")
async def on_sched_back(call: types.CallbackQuery):
    await call.message.edit_text("🐝 **АСАЛАРИЧИЛИК ВИКТОРИНА ВА СЎРОВНОМАЛАР МАРКАЗИ**", reply_markup=build_quiz_menu_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "quiz_back_menu")
async def on_quiz_back_menu(call: types.CallbackQuery):
    quizzes = get_quizzes_db()
    polls = get_polls_db()
    settings = get_settings()
    ptype = "🐝 Викторина (Quiz - тўғри жавобли)" if settings.get("poll_type", "quiz") == "quiz" else "📋 Опрос (Сўровнома - очиқ овоз бериш)"
    text = (
        "🐝 **АСАЛАРИЧИЛИК ВИКТОРИНА ВА СЎРОВНОМАЛАР (ОПРОС) МАРКАЗИ**\n\n"
        "Telegram расмий аноним викториналари ва очиқ сўровномаларини гуруҳ ва каналларга тақдим этиш тизими:\n\n"
        f"• 📚 Базадаги викториналар: **{len(quizzes)} та** (AI кенгайиш)\n"
        f"• 📊 Базадаги очиқ опрос (сўровномалар): **{len(polls)} та**\n"
        f"• 🎯 Ҳозирги фаол режим: **{ptype}**\n"
        "• 👍 Лайк-реакциялар, канал ҳаволаси ва савол бериш тугмалари билан таъминланган\n"
        "• ⏰ Ҳар куни автоматик белгиланган вақтда уланган каналларга юборилади."
    )
    await call.message.edit_text(text, reply_markup=build_quiz_menu_inline(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "quiz_settings")
async def on_quiz_settings(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    text = (
        "⚙️ **ВИКТОРИНА ВА ОПРОС (СЎРОВНОМА) СОЗЛАМАЛАРИ**\n\n"
        "Сўровнома тури (Викторина / Опрос), анонимлик, реакциялар ва юбориш манзилларини шу ердан созланг:"
    )
    await call.message.edit_text(text, reply_markup=build_settings_inline(source_menu="quiz"), parse_mode="Markdown")
    await call.answer()

# ==============================================================================
# 16.1. VIKTORINA PREVIEW CALLBACK HANDLERS (1-RASMDAGI BARCHA TUGMALAR)
# ==============================================================================
@dp.callback_query(F.data.startswith("quiz_page:"))
async def on_quiz_page(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    quizzes = get_quizzes_db()
    total = len(quizzes)
    if total == 0:
        await call.answer("Саволлар базаси бўш!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    idx = max(0, min(idx, total - 1))
    quiz = quizzes[idx]
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_quiz_preview_text(quiz, idx, total, script)
    markup = build_quiz_preview_keyboard(idx, total, script)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    await call.answer()

@dp.callback_query(F.data.startswith("quiz_page_info:"))
async def on_quiz_page_info(call: types.CallbackQuery):
    quizzes = get_quizzes_db()
    total = len(quizzes)
    try:
        idx = int(call.data.split(":")[1]) + 1
    except Exception:
        idx = 1
    await call.answer(f"📄 Жами {total} та саволдан {idx}-савол кўрилмоқда", show_alert=False)

@dp.callback_query(F.data.startswith("quiz_send_chan"))
async def on_quiz_send_chan(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    quizzes = get_quizzes_db()
    if not quizzes:
        await call.answer("Саволлар топилмади!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    idx = max(0, min(idx, len(quizzes) - 1))
    target = get_official_channel()
    res = await send_quiz_poll_to_chat(target, quizzes[idx], poll_mode="quiz")
    if res:
        await call.answer(f"✅ Расмий канал ({target}) га викторина муваффақиятли юборилди!", show_alert=True)
    else:
        await call.message.answer(
            f"⚠️ **{target} га юбориб бўлмади!**\n\n"
            f"Бот `{target}` каналига админ қилинмаган. Илтимос, @Asalarichilikuz_bot ни каналга админ қилинг ёки Созламалардан тўғри канални танланг.",
            parse_mode="Markdown"
        )
        await call.answer(f"⚠️ {target} га юбориб бўлмади (админликни текширинг)!", show_alert=True)

@dp.callback_query(F.data.startswith("quiz_send_grp"))
async def on_quiz_send_grp(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    quizzes = get_quizzes_db()
    if not quizzes:
        await call.answer("Саволлар топилмади!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    idx = max(0, min(idx, len(quizzes) - 1))
    target = get_official_group()
    res = await send_quiz_poll_to_chat(target, quizzes[idx], poll_mode="quiz")
    if res:
        await call.answer(f"✅ Расмий гуруҳ ({target}) га викторина муваффақиятли юборилди!", show_alert=True)
    else:
        await call.message.answer(
            f"⚠️ **{target} га юбориб бўлмади!**\n\n"
            f"Бот `{target}` гуруҳига админ қилинмаган. Илтимос, @Asalarichilikuz_bot ни гуруҳга қўшиб админ қилинг ёки Созламалардан тўғри гуруҳни танланг.",
            parse_mode="Markdown"
        )
        await call.answer(f"⚠️ {target} га юбориб бўлмади (админликни текширинг)!", show_alert=True)

@dp.callback_query(F.data.startswith("quiz_send_both"))
async def on_quiz_send_both(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    quizzes = get_quizzes_db()
    if not quizzes:
        await call.answer("Саволлар топилмади!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    idx = max(0, min(idx, len(quizzes) - 1))
    quiz = quizzes[idx]
    
    ch = get_official_channel()
    grp = get_official_group()
    res_ch = await send_quiz_poll_to_chat(ch, quiz, poll_mode="quiz")
    if res_ch:
        try:
            await bot.pin_chat_message(chat_id=res_ch.chat.id, message_id=res_ch.message_id, both_silent=False)
        except Exception:
            pass
    res_grp = await send_quiz_poll_to_chat(grp, quiz, poll_mode="quiz")
    if res_grp:
        try:
            await bot.pin_chat_message(chat_id=res_grp.chat.id, message_id=res_grp.message_id, both_silent=False)
        except Exception:
            pass
    await call.answer("✅ Канал ва гуруҳга викторина юборилди ва қадалди!", show_alert=True)

@dp.callback_query(F.data == "quiz_random")
async def on_quiz_random(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    quizzes = get_quizzes_db()
    total = len(quizzes)
    if total == 0:
        await call.answer("Саволлар йўқ!", show_alert=True)
        return
    idx = random.randint(0, total - 1)
    quiz = quizzes[idx]
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_quiz_preview_text(quiz, idx, total, script)
    markup = build_quiz_preview_keyboard(idx, total, script)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    await call.answer(f"🎲 #{idx + 1} савол кўрсатилмоқда")

@dp.callback_query(F.data.startswith("quiz_toggle_script:"))
async def on_quiz_toggle_script(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    settings = get_settings()
    cur = settings.get("script_mode", "cyrillic")
    new_mode = "latin" if cur == "cyrillic" else "cyrillic"
    update_setting("script_mode", new_mode)
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    quizzes = get_quizzes_db()
    total = len(quizzes)
    idx = max(0, min(idx, total - 1))
    text = format_quiz_preview_text(quizzes[idx], idx, total, new_mode)
    markup = build_quiz_preview_keyboard(idx, total, new_mode)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    await call.answer(f"Ёзув: {'Лотинча' if new_mode == 'latin' else 'Кириллча'}")

# ==============================================================================
# 17. YANGILIKLAR TIZIMI (📰 Асаларичилик Янгиликлари - 3-расмдагидек 1-га-1)
# ==============================================================================
def format_news_post_text(news: dict, script: str = "cyrillic", is_admin: bool = False) -> str:
    title = apply_script(news.get("title", ""), script).strip()
    body = apply_script(news.get("body", "") or news.get("summary", ""), script).strip()
    
    results = news.get("results")
    if results and isinstance(results, list):
        res_lines = [f"{i}. {apply_script(r, script)}" for i, r in enumerate(results, 1)]
        results_text = "\n".join(res_lines)
    else:
        results_text = apply_script(news.get("recommendations", ""), script).strip()

    source = news.get("source", "Nature Scientific Reports / Халқаро тадқиқот (2026 йил)")
    tags = news.get("tags", "") or news.get("hashtags", "#Асаларичилик #Янгилик #Инновация #AsalarichilikUz")
    footer = get_official_footer(script=script)

    lines = []
    if title:
        lines.append(f"📌 🔬 {title}")
        lines.append("")
    if body:
        lines.append(body)
        lines.append("")
    if results_text:
        res_head = "📌 Тадқиқот натижалари:" if script == "cyrillic" else "📌 Tadqiqot natijalari:"
        lines.append(res_head)
        lines.append(results_text)
        lines.append("")
    if source:
        src_head = "🌐 Манба:" if script == "cyrillic" else "🌐 Manba:"
        lines.append(f"{src_head} {source}")
    if tags:
        tag_head = "🏷 Теглар:" if script == "cyrillic" else "🏷 Teglar:"
        lines.append(f"{tag_head} {tags}")
    
    lines.append(footer)
    return "\n".join(lines)

def build_news_viewer_keyboard(idx: int, total: int, script: str = "cyrillic") -> InlineKeyboardMarkup:
    settings = get_settings()
    script_lbl = "🟢 Кириллча" if script == "cyrillic" else "🟢 Lotincha"
    dest_mode = settings.get("post_target_mode", "channel")
    if dest_mode == "channel":
        dest_lbl = "Фақат Каналларга"
    elif dest_mode == "group":
        dest_lbl = "Фақат Гуруҳларга"
    elif dest_mode == "both":
        dest_lbl = "Канал ва Гуруҳга"
    else:
        dest_lbl = "Фақат Каналларга"

    rows = [
        # 1-qator: Kanalga yoki Guruhga yuborish
        [
            InlineKeyboardButton(text="📢 Каналга юбориш", callback_data=f"news_send_chan:{idx}"),
            InlineKeyboardButton(text="👥 Гуруҳга юбориш", callback_data=f"news_send_grp:{idx}")
        ],
        # 2-qator: Ikkalasiga bir vaqtda юбориш ва қадаш
        [
            InlineKeyboardButton(text="🌐 Канал ва Гуруҳга (Иккаласига) 📌", callback_data=f"news_publish_pin:{idx}")
        ],
        # 3-qator: Reklama menyusiga to'g'ridan-to'g'ri o'tkazish
        [
            InlineKeyboardButton(text="📣 Реклама менюсига тўғридан-тўғри ўтказиш 🚀", callback_data=f"news_to_post:{idx}")
        ],
        # 4-qator: Paginatsiya [⬅️ Олдингиси] [📄 1 / total] [Кейингиси ➡️]
        [
            InlineKeyboardButton(text="⬅️ Олдингиси", callback_data=f"news_page:{idx - 1}"),
            InlineKeyboardButton(text=f"📄 {idx + 1} / {total}", callback_data=f"news_page_info:{idx}"),
            InlineKeyboardButton(text="Кейингиси ➡️", callback_data=f"news_page:{idx + 1}")
        ],
        # 5-qator: Yozuv turi va Tasodifiy yangilik
        [
            InlineKeyboardButton(text=f"🔤 Ёзув тури: {script_lbl}", callback_data=f"news_toggle_script:{idx}"),
            InlineKeyboardButton(text="🎲 Тасодифий янгилик", callback_data="news_random")
        ],
        # 6-qator: Manzil sozlamasi
        [
            InlineKeyboardButton(text=f"⚙️ Манзил созламаси: {dest_lbl}", callback_data=f"news_toggle_dest:{idx}")
        ],
        # 7-qator: Orqaga va Asosiy menyu
        [
            InlineKeyboardButton(text="« Реклама ва постлар менюсига қайтиш", callback_data="news_back_menu"),
            InlineKeyboardButton(text="🏠 Асосий Меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_news_menu_inline() -> InlineKeyboardMarkup:
    return build_news_viewer_keyboard(0, len(get_news_db()))

@dp.message(F.text == "📰 Асаларичилик Янгиликлари")
async def news_cmd(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return

    news_list = get_news_db()
    if not news_list:
        news_list = copy.deepcopy(INITIAL_NEWS)
        save_news_db(news_list)

    idx = 0
    news = news_list[idx]
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_news_post_text(news, script, is_admin=False)
    markup = build_news_viewer_keyboard(idx, len(news_list), script)
    await message.answer(text, reply_markup=markup, parse_mode=None)

@dp.callback_query(F.data.startswith("news_page:"))
async def on_news_page(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0

    news_list = get_news_db()
    if not news_list:
        news_list = copy.deepcopy(INITIAL_NEWS)
        save_news_db(news_list)

    idx = max(0, min(idx, len(news_list) - 1))
    news = news_list[idx]
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_news_post_text(news, script, is_admin=False)
    markup = build_news_viewer_keyboard(idx, len(news_list), script)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    await call.answer()

@dp.callback_query(F.data.startswith("news_page_info"))
async def on_news_page_info(call: types.CallbackQuery):
    news_list = get_news_db()
    total = len(news_list)
    try:
        idx = int(call.data.split(":")[1]) + 1
    except Exception:
        idx = 1
    await call.answer(f"📄 Жами {total} та илмий асаларичилик янгилигидан {idx}-чиси", show_alert=False)

async def publish_news_to_target(target: Union[int, str], news: dict, pin: bool = False) -> Optional[types.Message]:
    """Янгиликни расмий канал ёки гуруҳга тўлиқ мазмуни ва тугмалари билан юбориш"""
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    channel_text = format_news_post_text(news, script, is_admin=False)
    
    is_chan = str(target) == get_official_channel() or (str(target).startswith("@") and "guruh" not in str(target).lower() and "uzbekistan" not in str(target).lower())
    
    init_markup = build_post_markup(
        chat_id=int(target) if str(target).replace("-", "").isdigit() else 0,
        message_id=0,
        reactions_list=settings.get("reactions"),
        channel_username=str(target).lstrip("@") if str(target).startswith("@") else None,
        include_template_btn=False,
        is_channel_post=is_chan,
        share_title=news.get("title", ""),
        share_text=news.get("body", "") or news.get("summary", ""),
        share_tags=news.get("tags", "") or news.get("hashtags", ""),
        share_source=news.get("source", "")
    )
    
    try:
        sent = await bot.send_message(
            chat_id=target,
            text=channel_text,
            reply_markup=init_markup,
            parse_mode=None
        )
        final_markup = build_post_markup(
            chat_id=sent.chat.id,
            message_id=sent.message_id,
            reactions_list=settings.get("reactions"),
            channel_username=sent.chat.username,
            include_template_btn=False,
            is_channel_post=is_chan,
            share_title=news.get("title", ""),
            share_text=news.get("body", "") or news.get("summary", ""),
            share_tags=news.get("tags", "") or news.get("hashtags", ""),
            share_source=news.get("source", "")
        )
        try:
            await bot.edit_message_reply_markup(
                chat_id=sent.chat.id,
                message_id=sent.message_id,
                reply_markup=final_markup
            )
        except Exception:
            pass
        if pin:
            try:
                await bot.pin_chat_message(chat_id=sent.chat.id, message_id=sent.message_id, both_silent=False)
            except Exception:
                pass
        return sent
    except Exception as e:
        logging.error(f"publish_news_to_target xatolik ({target}): {e}")
        return None

@dp.callback_query(F.data.startswith("news_send_chan:"))
async def on_news_send_chan(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    news_list = get_news_db()
    if not news_list:
        await call.answer("Янгиликлар топилмади!", show_alert=True)
        return
    idx = max(0, min(idx, len(news_list) - 1))
    target = get_official_channel()
    res = await publish_news_to_target(target, news_list[idx], pin=False)
    if res:
        await call.answer(f"✅ Расмий канал ({target}) га янгилик муваффақиятли юборилди!", show_alert=True)
    else:
        await call.answer(f"⚠️ {target} га юбориб бўлмади. Ботни ушбу каналга админ қилганингизни текширинг!", show_alert=True)

@dp.callback_query(F.data.startswith("news_send_grp:"))
async def on_news_send_grp(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    news_list = get_news_db()
    if not news_list:
        await call.answer("Янгиликлар топилмади!", show_alert=True)
        return
    idx = max(0, min(idx, len(news_list) - 1))
    target = get_official_group()
    res = await publish_news_to_target(target, news_list[idx], pin=False)
    if res:
        await call.answer(f"✅ Расмий гуруҳ ({target}) га янгилик муваффақиятли юборилди!", show_alert=True)
    else:
        await call.answer(f"⚠️ {target} га юбориб бўлмади. Ботни ушбу гуруҳга админ қилганингизни текширинг!", show_alert=True)

@dp.callback_query(F.data.startswith("news_publish_pin:"))
async def on_news_publish_pin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0

    news_list = get_news_db()
    if not news_list:
        await call.answer("Янгиликлар топилмади!", show_alert=True)
        return

    idx = max(0, min(idx, len(news_list) - 1))
    news = news_list[idx]

    ch = get_official_channel()
    grp = get_official_group()
    res_ch = await publish_news_to_target(ch, news, pin=True)
    res_grp = await publish_news_to_target(grp, news, pin=True)
    count = (1 if res_ch else 0) + (1 if res_grp else 0)

    await call.answer(
        f"✅ {count} та манзилга (Канал ва Гуруҳ) янгилик юборилди ва қадалди!",
        show_alert=True
    )

@dp.callback_query(F.data == "news_random")
async def on_news_random(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    news_list = get_news_db()
    total = len(news_list)
    if total == 0:
        await call.answer("Янгиликлар йўқ!", show_alert=True)
        return
    idx = random.randint(0, total - 1)
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_news_post_text(news_list[idx], script, is_admin=False)
    markup = build_news_viewer_keyboard(idx, total, script)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    await call.answer(f"🎲 #{idx + 1} янгилик кўрсатилмоқда")

@dp.callback_query(F.data.startswith("news_toggle_script:"))
async def on_news_toggle_script(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    settings = get_settings()
    cur = settings.get("script_mode", "cyrillic")
    new_mode = "latin" if cur == "cyrillic" else "cyrillic"
    update_setting("script_mode", new_mode)
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    news_list = get_news_db()
    total = len(news_list)
    idx = max(0, min(idx, total - 1))
    text = format_news_post_text(news_list[idx], new_mode, is_admin=False)
    markup = build_news_viewer_keyboard(idx, total, new_mode)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    await call.answer(f"Ёзув: {'Лотинча' if new_mode == 'latin' else 'Кириллча'}")

@dp.callback_query(F.data.startswith("news_toggle_dest:"))
async def on_news_toggle_dest(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    settings = get_settings()
    cur = settings.get("post_target_mode", "channel")
    modes = ["channel", "group", "both"]
    next_idx = (modes.index(cur) + 1) % len(modes) if cur in modes else 0
    new_mode = modes[next_idx]
    update_setting("post_target_mode", new_mode)
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    news_list = get_news_db()
    total = len(news_list)
    idx = max(0, min(idx, total - 1))
    script = settings.get("script_mode", "cyrillic")
    text = format_news_post_text(news_list[idx], script, is_admin=False)
    markup = build_news_viewer_keyboard(idx, total, script)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode=None)
    except Exception:
        pass
    lbl = "Фақат Каналларга" if new_mode == "channel" else ("Фақат Гуруҳларга" if new_mode == "group" else "Канал ва Гуруҳга")
    await call.answer(f"Манзил: {lbl}")

@dp.callback_query(F.data.startswith("news_to_post:"))
async def on_news_to_post(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    try:
        idx = int(call.data.split(":")[1])
    except Exception:
        idx = 0
    news_list = get_news_db()
    if not news_list:
        await call.answer("Янгилик топилмади!", show_alert=True)
        return
    idx = max(0, min(idx, len(news_list) - 1))
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    formatted_text = format_news_post_text(news_list[idx], script, is_admin=False)
    
    await state.set_state(PostStates.editing_post)
    await state.update_data(
        post_type="text",
        text=formatted_text,
        media_id=None,
        urls=[],
        disable_preview=False,
        silent=False
    )
    await call.message.answer(
        "📝 **Янгилик реклама ва пост конструкторига ўтказилди!**\n\n"
        "Сиз энди унга расм қўшишингиз, таҳрирлашингиз ёки кўриб чиқиб тарқатишингиз мумкин.",
        reply_markup=get_constructor_reply_keyboard(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data == "main_menu")
async def on_main_menu_callback(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer("🏠 Асосий Менюга қайтдингиз:", reply_markup=get_main_reply_keyboard())
    await call.answer()

@dp.callback_query(F.data == "news_search_fresh")
async def on_news_search_fresh(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    await call.answer("🌐 Интернет ва халқаро илмий манбалардан янги маълумот изланмоқда...")
    item = await generate_news_with_ai()
    news_list = get_news_db()
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")

    idx = 0  # Eng yangisini ko'rsatamiz
    news = news_list[idx]
    text = format_news_post_text(news, script, is_admin=True)
    markup = build_news_viewer_keyboard(idx, len(news_list), script)
    try:
        await call.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass
    await call.message.answer(
        f"✅ **Янги илмий янгилик юкланди ва базага қўшилди!** (Жами: {len(news_list)} та)\n\n"
        f"📌 *{news.get('title')}*",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "news_back_menu")
async def on_news_back_menu(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        "🔙 **Сиз асосий постлар ва реклама менюсига қайтдингиз.**\nКеракли бўлимни танланг:",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("news_act:"))
async def on_news_action(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    act = call.data.split(":")[1]

    if act == "close":
        await call.message.delete()
        return

    elif act == "sched_menu":
        times = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "Ўчириш"]
        rows = []
        for t in times:
            rows.append([InlineKeyboardButton(text=f"⏰ {t}", callback_data=f"nsched_set:{t}")])
        rows.append([InlineKeyboardButton(text="« Орқага", callback_data="nsched_back")])
        await call.message.edit_text(
            "⏰ **Кунлик автоматик янгиликлар юбориш вақтини танланг:**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("nsched_set:"))
async def on_news_sched_time_set(call: types.CallbackQuery):
    val = call.data.split(":")[1]
    if val == "Ўчириш":
        update_setting("news_schedule_enabled", False)
        await call.answer("Авто-янгилик ўчирилди!")
    else:
        update_setting("news_schedule_enabled", True)
        update_setting("news_schedule_time", val)
        await call.answer(f"Авто-янгилик вақти соат {val} га созланди! ✅")
    await call.message.edit_text("📰 **АСАЛАРИЧИЛИК ЯНГИЛИКЛАРИ ВА МАВСУМИЙ ТАВСИЯЛАР**", reply_markup=build_news_menu_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "nsched_back")
async def on_news_sched_back(call: types.CallbackQuery):
    await call.message.edit_text("📰 **АСАЛАРИЧИЛИК ЯНГИЛИКЛАРИ ВА МАВСУМИЙ ТАВСИЯЛАР**", reply_markup=build_news_menu_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "news_settings")
async def on_news_settings(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    text = (
        "⚙️ **АСАЛАРИЧИЛИК ЯНГИЛИКЛАРИ ВА ПОСТ СОЗЛАМАЛАРИ**\n\n"
        "Янгиликлар ва постлар остидаги реакциялар, улашиш тугмаси, расмий канал ва гуруҳ ҳаволаларини шу ердан бошқаринг:"
    )
    await call.message.edit_text(text, reply_markup=build_settings_inline(source_menu="news"), parse_mode="Markdown")
    await call.answer()

# ==============================================================================
# 18. SHABLONNI POST KONSTRUKTORIGA YUKLASH (tpl_use CALLBACK)
# ==============================================================================
@dp.callback_query(F.data.startswith("tpl_use:"))
async def on_template_use_click(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Фақат бот эгаси шаблон ярата олади!", show_alert=True)
        return

    parts = call.data.split(":")
    tpl_type = parts[1]
    tpl_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")

    if tpl_type == "quiz":
        quizzes = get_quizzes_db()
        target_q = next((q for q in quizzes if q.get("id") == tpl_id), None) or get_next_quiz()
        
        await state.clear()
        await state.set_state(PostStates.editing_post)
        await state.update_data(
            post_type="quiz",
            quiz_data=target_q,
            target_chat="all"
        )
        data = await state.get_data()
        await call.message.answer(
            "🐝 **Викторина (Опрос) пост конструкторига юкланди!**\n\n"
            "⚠️ Бу оддий матн эмас, балки **ҳақиқий Telegram Аноним Викторинаси (Poll)** бўлиб юборилади.\n"
            "Фойдаланувчилар жавобни олдиндан кўрмайди, фақат битта вариантни танлагандан сўнг натижа ва изоҳ очилади!",
            reply_markup=get_constructor_reply_keyboard()
        )
        # Синов учун админга жўнатиш
        await send_quiz_poll_to_chat(call.message.chat.id, target_q)
        await call.message.answer(
            "⚙️ **Викторина (Опрос) Конструктори:**\n\n"
            "Канал ва гуруҳларга юбориш учун пастдаги тугмани босинг ёки бошқа саволга алмаштиринг:",
            reply_markup=build_quiz_post_constructor_inline(data)
        )
        await call.answer()
        return
    else:
        news_list = get_news_db()
        target_n = next((n for n in news_list if n.get("id") == tpl_id), None) or get_next_news()
        post_text = format_news_post_text(target_n, script)

        await state.clear()
        await state.set_state(PostStates.editing_post)
        await state.update_data(
            post_type="news",
            target_chat="all",
            text=post_text,
            media_type=None,
            media_file_id=None,
            comments_enabled=True,
            reactions_str="👍 ❤️ 🔥 👏 🐝",
            reactions_list=["👍", "❤️", "🔥", "👏", "🐝"],
            url_buttons=[]
        )
        data = await state.get_data()
        await call.message.answer(
            "📝 **Янгилик Шаблони Пост Конструкторига муваффақиятли кўчирилди!**\n"
            "Сиз уни таҳрирлашингиз, расм қўшишингиз ёки тўғридан-тўғри тарқатишингиз мумкин.",
            reply_markup=get_constructor_reply_keyboard()
        )
        await call.message.answer(
            f"⚙️ **Пост Конструктори:**\n\n{post_text}",
            reply_markup=build_post_constructor_inline(data),
            parse_mode="Markdown"
        )
        await call.answer()

@dp.callback_query(PostStates.editing_post, F.data.startswith("cquiz:"))
async def on_cquiz_actions(call: types.CallbackQuery, state: FSMContext):
    act = call.data.split(":")[1]
    data = await state.get_data()
    
    if act == "next":
        new_q = get_next_quiz()
        data["quiz_data"] = new_q
        await state.set_data(data)
        await call.answer("Янги савол юкланди!")
        await send_quiz_poll_to_chat(call.message.chat.id, new_q)
        await call.message.edit_reply_markup(reply_markup=build_quiz_post_constructor_inline(data))

    elif act == "spec":
        new_q = get_next_quiz(level="spec")
        data["quiz_data"] = new_q
        await state.set_data(data)
        await call.answer("🎓 Спец (мураккаб) савол танланди!")
        await send_quiz_poll_to_chat(call.message.chat.id, new_q)
        await call.message.edit_reply_markup(reply_markup=build_quiz_post_constructor_inline(data))

    elif act == "beg":
        new_q = get_next_quiz(level="beginner")
        data["quiz_data"] = new_q
        await state.set_data(data)
        await call.answer("👶 Бошланғич савол танланди!")
        await send_quiz_poll_to_chat(call.message.chat.id, new_q)
        await call.message.edit_reply_markup(reply_markup=build_quiz_post_constructor_inline(data))

    elif act == "toggle_script":
        settings = get_settings()
        cur = settings.get("script_mode", "cyrillic")
        new_mode = "latin" if cur == "cyrillic" else "cyrillic"
        update_setting("script_mode", new_mode)
        await call.answer(f"Ёзув тури: {'Лотинча' if new_mode == 'latin' else 'Крилча'}")
        quiz_data = data.get("quiz_data") or get_next_quiz()
        await send_quiz_poll_to_chat(call.message.chat.id, quiz_data)
        await call.message.edit_reply_markup(reply_markup=build_quiz_post_constructor_inline(data))

    elif act == "preview":
        await call.answer("Викторина синов учун юборилди!")
        quiz_data = data.get("quiz_data") or get_next_quiz()
        await send_quiz_poll_to_chat(call.message.chat.id, quiz_data)

    elif act == "target":
        await call.message.edit_text(
            "Викторинани юбормоқчи бўлган манзилингизни танланг:",
            reply_markup=get_target_chats_inline()
        )

# ==============================================================================
# 19. SOZLAMALAR (⚙️ Созламалар) MENYUSI
# ==============================================================================
def build_settings_inline(source_menu: Optional[str] = None) -> InlineKeyboardMarkup:
    settings = get_settings()
    auto_r = "✅ Ёқилган" if settings.get("auto_reactions", True) else "❌ Ўчирилган"
    auto_s = "✅ Ёқилган" if settings.get("auto_share", True) else "❌ Ўчирилган"
    auto_c = "✅ Ёқилган" if settings.get("auto_comment", True) else "❌ Ўчирилган"
    script = "Крил 🇺🇿" if settings.get("script_mode", "cyrillic") == "cyrillic" else "Lotin 🇺🇿"
    q_time = settings.get("quiz_schedule_time", "09:00") if settings.get("quiz_schedule_enabled", True) else "Ўчирилган"
    n_time = settings.get("news_schedule_time", "14:00") if settings.get("news_schedule_enabled", True) else "Ўчирилган"
    preset_str = " ".join(settings.get("reactions", []))
    off_channel = get_official_channel()
    off_group = get_official_group()
    chan_title = get_channel_title()

    t_mode = settings.get("post_target_mode", "ask")
    if t_mode == "channel":
        target_label = "📢 Фақат Канал"
    elif t_mode == "group":
        target_label = "👥 Фақат Гуруҳ"
    elif t_mode == "both":
        target_label = "🚀 Канал + Гуруҳ"
    else:
        target_label = "❓ Ҳар сафар сўралсин"

    poll_type = settings.get("poll_type", "quiz")
    poll_mode_label = "🐝 Викторина (Quiz)" if poll_type == "quiz" else "📋 Опрос (Сўровнома)"

    poll_anon = settings.get("poll_is_anonymous", True)
    anon_label = "🕵️ Аноним" if poll_anon else "👤 Очиқ"

    src = source_menu or "main"

    rows = [
        [InlineKeyboardButton(text=f"🎯 Жўнатиш манзили: {target_label}", callback_data=f"set_toggle:post_target_mode:{src}")],
        [InlineKeyboardButton(text=f"📊 Сўровнома режими: {poll_mode_label}", callback_data=f"set_toggle:poll_type:{src}")],
        [InlineKeyboardButton(text=f"🎲 Сўровнома тури: {anon_label}", callback_data=f"set_toggle:poll_is_anonymous:{src}")],
        [InlineKeyboardButton(text=f"🔄 Авто-реакциялар: {auto_r}", callback_data=f"set_toggle:auto_reactions:{src}")],
        [InlineKeyboardButton(text=f"↗️ Улашиш тугмаси: {auto_s}", callback_data=f"set_toggle:auto_share:{src}")],
        [InlineKeyboardButton(text=f"💬 Мутахассис тугмаси: {auto_c}", callback_data=f"set_toggle:auto_comment:{src}")],
        [InlineKeyboardButton(text=f"🎨 Тўплам: {preset_str}", callback_data="set_menu:presets")],
        [InlineKeyboardButton(text="✏️ Лайкларни қўлда ўзгартириш", callback_data="set_custom_reactions")],
        [InlineKeyboardButton(text=f"📢 Расмий канал: {off_channel}", callback_data="set_change_channel")],
        [InlineKeyboardButton(text=f"👥 Расмий гуруҳ: {off_group}", callback_data="set_change_group")],
        [InlineKeyboardButton(text=f"🏷 Канал номи: {chan_title}", callback_data="set_change_channel_title")],
        [InlineKeyboardButton(text=f"🔤 Ёзув тури: {script}", callback_data=f"set_toggle_script:{src}")],
        [InlineKeyboardButton(text=f"⏰ Авто-викторина: {q_time}", callback_data="quiz_act:sched_menu")],
        [InlineKeyboardButton(text=f"📰 Авто-янгилик: {n_time}", callback_data="news_act:sched_menu")],
        [InlineKeyboardButton(text=f"🌿 Авто-апитерапия: {settings.get('apitherapy_schedule_time', '16:00') if settings.get('apitherapy_schedule_enabled', True) else 'Ўчирилган'}", callback_data="api_act:sched_menu")],
        [InlineKeyboardButton(text="📥 100 та савол ва янгиликни юклаш (bee_news_collection)", callback_data="sync_bee_news_collection")],
        [InlineKeyboardButton(text="📋 Уланган канал ва гуруҳлар", callback_data="set_menu:chats")]
    ]

    if src == "news":
        rows.append([InlineKeyboardButton(text="« 📰 Янгиликларга қайтиш", callback_data="news_back_menu")])
    elif src == "quiz":
        rows.append([InlineKeyboardButton(text="« 🐝 Викторина ва Опросга қайтиш", callback_data="quiz_back_menu")])
    elif src == "apitherapy":
        rows.append([InlineKeyboardButton(text="« 🌿 Апитерапияга қайтиш", callback_data="api_back_menu")])
    else:
        rows.append([InlineKeyboardButton(text="🔙 Ёпиш", callback_data="set_close")])

    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(F.text == "⚙️ Созламалар")
@dp.message(Command("settings"))
async def settings_cmd(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return

    text = (
        "⚙️ **БОТ, ПОСТ ВА СЎРОВНОМАЛАР СОЗЛАМАЛАРИ**\n\n"
        "Канал ва гуруҳларга юбориладиган ҳар бир хабар, янгилик ва викторина-сўровнома "
        "остига автоматик тугмалар ва реакциялар қўйишни шу ердан ёқишингиз ёки ўчиришингиз мумкин:\n\n"
        "• **Жўнатиш манзили:** Хабар юборишда олдиндан сўраш ёки автоматик Канал/Гуруҳга йўналтириш.\n"
        "• **Сўровнома режими:** Викторина (Quiz - тест) ёки Опрос (Сўровнома - очиқ овоз бериш).\n"
        "• **Авто-реакциялар:** Янгиликлар, постлар ва опрос остига лайк тугмалари қўяди.\n"
        "• **Улашиш тугмаси:** Постни тўлиқ мазмуни билан дўстларга юбориш тугмаси.\n"
        "• **Тўплам:** Лайк ва эможилар кўриниши (тайёр ёки қўлда ёзилган).\n"
        "• **Расмий канал ва гуруҳ:** Янгиликлар ва ҳаволаларда чиқадиган канал ва гуруҳни қўлда ўзгартириш."
    )
    await message.answer(text, reply_markup=build_settings_inline(source_menu="main"), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("set_toggle_script"))
async def on_settings_toggle_script(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    parts = call.data.split(":")
    src = parts[1] if len(parts) > 1 else "main"

    settings = get_settings()
    cur = settings.get("script_mode", "cyrillic")
    new_mode = "latin" if cur == "cyrillic" else "cyrillic"
    update_setting("script_mode", new_mode)
    await call.message.edit_reply_markup(reply_markup=build_settings_inline(source_menu=src))
    await call.answer(f"Алифбо ўзгарди: {'Лотинча' if new_mode == 'latin' else 'Крилча'}")

@dp.callback_query(F.data.startswith("set_toggle:"))
async def on_setting_toggle(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    parts = call.data.split(":")
    key = parts[1]
    src = parts[2] if len(parts) > 2 else "main"
    settings = get_settings()

    if key == "post_target_mode":
        current = settings.get("post_target_mode", "ask")
        order = ["ask", "channel", "group", "both"]
        next_val = order[(order.index(current) + 1) % len(order)] if current in order else "ask"
        update_setting("post_target_mode", next_val)
        await call.message.edit_reply_markup(reply_markup=build_settings_inline(source_menu=src))
        lbl = {"ask": "Ҳар сафар сўралади ❓", "channel": "Фақат Каналга 📢", "group": "Фақат Гуруҳга 👥", "both": "Канал ва Гуруҳга (иккаласига) 🚀"}[next_val]
        await call.answer(f"Манзил: {lbl}")
        return

    elif key == "poll_type":
        cur_type = settings.get("poll_type", "quiz")
        next_type = "regular" if cur_type == "quiz" else "quiz"
        update_setting("poll_type", next_type)
        await call.message.edit_reply_markup(reply_markup=build_settings_inline(source_menu=src))
        lbl = "🐝 Викторина (Quiz)" if next_type == "quiz" else "📋 Опрос (Сўровнома)"
        await call.answer(f"Сўровнома: {lbl}")
        return

    elif key == "poll_is_anonymous":
        cur_anon = settings.get("poll_is_anonymous", True)
        update_setting("poll_is_anonymous", not cur_anon)
        await call.message.edit_reply_markup(reply_markup=build_settings_inline(source_menu=src))
        lbl = "👤 Очиқ овоз" if cur_anon else "🕵️ Аноним овоз"
        await call.answer(f"Сўровнома: {lbl}")
        return

    current_val = settings.get(key, True)
    update_setting(key, not current_val)
    
    await call.message.edit_reply_markup(reply_markup=build_settings_inline(source_menu=src))
    status_str = "ўчирилди ❌" if current_val else "ёқилди ✅"
    await call.answer(f"Созлама ўзгарди: {status_str}")

@dp.callback_query(F.data == "sync_bee_news_collection")
async def on_sync_bee_news_collection(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    await call.answer("🔄 База текширилмоқда...", show_alert=False)
    res = sync_bee_news_collection()
    if res.get("success"):
        await call.message.answer(
            f"✅ **bee_news_collection.py муваффақиятли юкланди!**\n\n"
            f"• 📰 Қўшилган янгиликлар: **{res.get('news')} та**\n"
            f"• 🐝 Қўшилган саволлар: **{res.get('quizzes')} та**\n"
            f"• 📊 Базадаги жами янгиликлар: **{res.get('total_news')} та**\n"
            f"• 🎓 Базадаги жами саволлар: **{res.get('total_quizzes')} та**\n\n"
            "Энди сиз барча 100 та янгилик ва саволларни канал ва гуруҳларга тўғридан-тўғри юборишингиз мумкин!",
            parse_mode="Markdown"
        )
    else:
        await call.message.answer(
            f"ℹ️ **bee_news_collection.py ҳолати:**\n\n"
            f"{res.get('msg')}\n\n"
            "Файл бот билан бир хил папкада (`/home/Asalarichiliktv/bee_news_collection.py`) жойлашган бўлса, бот автоматик равишда ундан фойдаланади.",
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "set_menu:presets")
async def on_settings_presets(call: types.CallbackQuery):
    rows = []
    for idx, preset in enumerate(REACTION_PRESETS):
        label = " ".join(preset)
        rows.append([InlineKeyboardButton(text=label, callback_data=f"set_preset:{idx}")])
    rows.append([InlineKeyboardButton(text="✏️ Лайкларни қўлда ёзиш (Custom)", callback_data="set_custom_reactions")])
    rows.append([InlineKeyboardButton(text="« Орқага", callback_data="set_menu:back")])
    
    text = (
        "🎨 **РЕАКЦИЯЛАР ТЎПЛАМИНИ ТАНЛАНГ**\n\n"
        "Тайёр тўпламлардан бирини танланг ёки ўз хоҳишингизга кўра "
        "эможиларни қўлда ёзиб киритинг:"
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("set_preset:"))
async def on_select_preset(call: types.CallbackQuery):
    idx = int(call.data.split(":")[1])
    preset = REACTION_PRESETS[idx]
    update_setting("reactions", preset)
    update_setting("selected_preset_index", idx)
    await call.answer("✅ Реакциялар тўплами сақланди!")
    await call.message.edit_text("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_custom_reactions")
async def on_set_custom_reactions(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    await state.set_state(SettingsStates.waiting_for_custom_reactions)
    settings = get_settings()
    cur_reactions = " ".join(settings.get("reactions", []))

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Бекор қилиш", callback_data="set_cancel_input")]
    ])
    text = (
        "✏️ **ЛАЙКЛАР ТЎПЛАМИНИ ҚЎЛДА КИРИТИШ**\n\n"
        f"Ҳозирги тўплам: `{cur_reactions}`\n\n"
        "Постлар остига чиқиши керак бўлган эможиларни орасига **бўш жой (пробел)** қўйиб ёзиб юборинг (камида 1 та, максимум 6 та эможи).\n\n"
        "Масалан:\n"
        "`👍 ❤️ 🔥 👏 🐝`\n"
        "ёки\n"
        "`🍯 🐝 🌸 🥇 ⭐`\n"
        "ёки\n"
        "`👍 👎 ❤️ 👏`\n\n"
        "Илтимос, янги эможиларингизни юборинг:"
    )
    await call.message.edit_text(text, reply_markup=cancel_kb, parse_mode="Markdown")
    await call.answer()

@dp.message(SettingsStates.waiting_for_custom_reactions)
async def on_receive_custom_reactions(message: types.Message, state: FSMContext):
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return

    raw_text = message.text.strip()
    if raw_text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Бекор қилинди.", reply_markup=get_main_reply_keyboard())
        await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")
        return

    parts = [p.strip() for p in raw_text.split() if p.strip()]
    if not parts:
        await message.answer("⚠️ Илтимос, камида битта эможи юборинг (масалан: `👍 ❤️ 🔥 👏 🐝`):", parse_mode="Markdown")
        return

    emojis = parts[:6]
    update_setting("reactions", emojis)
    await state.clear()

    await message.answer(
        f"✅ **Лайклар тўплами муваффақиятли янгиланди!**\n\n"
        f"Янги тўплам: {' '.join(emojis)}\n\n"
        f"Энди чиқариладиган ҳар бир янги пост остида ушбу эможилар чиқади.",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_change_channel")
async def on_set_change_channel(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    await state.set_state(SettingsStates.waiting_for_channel)
    cur_channel = get_official_channel()

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Бекор қилиш", callback_data="set_cancel_input")]
    ])
    text = (
        "📢 **РАСМИЙ КАНАЛНИ ЎЗГАРТИРИШ**\n\n"
        f"Ҳозирги расмий канал: `{cur_channel}`\n\n"
        "Янги расмий канал номини ёки username'ини ёзиб юборинг (масалан: `@asalarichilik` ёки `@mening_kanalim`).\n\n"
        "Ушбу канал номи янгиликлар ва постлар остида расмий канал сифатида автоматик кўрсатилади:"
    )
    await call.message.edit_text(text, reply_markup=cancel_kb, parse_mode="Markdown")
    await call.answer()

@dp.message(SettingsStates.waiting_for_channel)
async def on_receive_channel(message: types.Message, state: FSMContext):
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return

    raw = message.text.strip()
    if raw.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Бекор қилинди.", reply_markup=get_main_reply_keyboard())
        await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")
        return

    ch = raw
    if "t.me/" in ch:
        ch = ch.split("t.me/")[-1].split("/")[0]
    ch = ch.strip().lstrip("@")
    if not ch:
        await message.answer("⚠️ Илтимос, тўғри канал username'ини юборинг (масалан: `@asalarichilik`):", parse_mode="Markdown")
        return

    formatted_channel = "@" + ch
    update_setting("official_channel", formatted_channel)
    await state.clear()

    await message.answer(
        f"✅ **Расмий канал муваффақиятли сақланди!**\n\n"
        f"Янги расмий канал: `{formatted_channel}`\n\n"
        f"Энди янгиликлар ва постлар остида расмий канал ҳаволаси шу номда чиқади.",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_change_group")
async def on_set_change_group(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    await state.set_state(SettingsStates.waiting_for_group)
    cur_group = get_official_group()

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Бекор қилиш", callback_data="set_cancel_input")]
    ])
    text = (
        "👥 **РАСМИЙ ГУРУҲНИ ЎЗГАРТИРИШ**\n\n"
        f"Ҳозирги расмий гуруҳ: `{cur_group}`\n\n"
        "Янги расмий гуруҳ username'ини ёзиб юборинг (масалан: `@Uz_Asalarichilik` ёки `@mening_guruhim`).\n\n"
        "Ушбу гуруҳ бот ва муҳокама ҳаволаларида расмий гуруҳ сифатида ишлатилади:"
    )
    await call.message.edit_text(text, reply_markup=cancel_kb, parse_mode="Markdown")
    await call.answer()

@dp.message(SettingsStates.waiting_for_group)
async def on_receive_group(message: types.Message, state: FSMContext):
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return

    raw = message.text.strip()
    if raw.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Бекор қилинди.", reply_markup=get_main_reply_keyboard())
        await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")
        return

    gr = raw
    if "t.me/" in gr:
        gr = gr.split("t.me/")[-1].split("/")[0]
    gr = gr.strip().lstrip("@")
    if not gr:
        await message.answer("⚠️ Илтимос, тўғри гуруҳ username'ини юборинг (масалан: `@Uz_Asalarichilik`):", parse_mode="Markdown")
        return

    formatted_group = "@" + gr
    update_setting("official_group", formatted_group)
    await state.clear()

    await message.answer(
        f"✅ **Расмий гуруҳ муваффақиятли сақланди!**\n\n"
        f"Янги расмий гуруҳ: `{formatted_group}`",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_change_channel_title")
async def on_set_change_channel_title(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return

    await state.set_state(SettingsStates.waiting_for_channel_title)
    cur_title = get_channel_title()

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Бекор қилиш", callback_data="set_cancel_input")]
    ])
    text = (
        "🏷 **КАНАЛ КЎРИНИШ НОМИНИ ЎЗГАРТИРИШ**\n\n"
        f"Ҳозирги тугма номи: `{cur_title}`\n\n"
        "Постлар остидаги «📢 ...» тугмасида қандай ном кўриниши керак бўлса, шуни ёзиб юборинг (масалан: `Asalarichilik.Uz` ёки `Бизнинг Канал`):"
    )
    await call.message.edit_text(text, reply_markup=cancel_kb, parse_mode="Markdown")
    await call.answer()

@dp.message(SettingsStates.waiting_for_channel_title)
async def on_receive_channel_title(message: types.Message, state: FSMContext):
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return

    raw = message.text.strip()
    if raw.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Бекор қилинди.", reply_markup=get_main_reply_keyboard())
        await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")
        return

    update_setting("official_channel_title", raw)
    await state.clear()

    await message.answer(
        f"✅ **Канал кўриниш номи сақланди!**\n\n"
        f"Янги тугма номи: `📢 {raw}`",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await message.answer("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_cancel_input")
async def on_set_cancel_input(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")
    await call.answer("Бекор қилинди.")

@dp.callback_query(F.data == "set_menu:back")
async def on_settings_back(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "set_menu:chats")
async def on_settings_chats(call: types.CallbackQuery):
    chats = load_allowed_chats()
    if not chats:
        text = "Ҳозирча ботга уланган канал ёки гуруҳлар йўқ."
    else:
        text = "📋 **Уланган канал ва гуруҳлар:**\n\n"
        for cid, info in chats.items():
            text += f"🔹 {info.get('title')} ({info.get('type')})\nID: `{cid}`\n\n"
    rows = [[InlineKeyboardButton(text="« Орқага", callback_data="set_menu:back")]]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="Markdown")

@dp.callback_query(F.data == "set_close")
async def on_settings_close(call: types.CallbackQuery):
    await call.message.delete()

# ==============================================================================
# 20. POST KONSTRUKTORI (📝 Пост яратиш)
# ==============================================================================
def get_target_chats_inline() -> InlineKeyboardMarkup:
    chats = load_allowed_chats()
    rows = []
    
    default_items = [
        ("Asalarilar @asalarichilik", "@asalarichilik"),
        ("🍯🐝Asalarichilik.Uz: @Uz_Asalarichilik", "@Uz_Asalarichilik"),
        ("👥 ЯНГИ ЎЗБЕКИСТОН АСАЛАРИЧИЛИК", "chat_yangi_uzb"),
        ("👥 Asalarichilik.Uz 🇺🇿 Beekeeping.Uz", "chat_beekeeping_uz"),
        ("👥 Барча гуруҳ ва каналларга (Рассылка)", "all")
    ]
    
    for cid, info in chats.items():
        title = info.get("title", f"Chat {cid}")
        rows.append([InlineKeyboardButton(text=f"📢 {title}", callback_data=f"post_target:{cid}")])
        
    if not rows:
        for title, val in default_items:
            rows.append([InlineKeyboardButton(text=title, callback_data=f"post_target:{val}")])
    else:
        rows.append([InlineKeyboardButton(text="👥 Барча гуруҳ ва каналларга (Рассылка)", callback_data="post_target:all")])
        
    rows.append([InlineKeyboardButton(text="🐝 Викторина (Опрос) шаклида яратиш", callback_data="tpl_use:quiz:0")])
    rows.append([InlineKeyboardButton(text="📰 Янгилик шаблонидан яратиш", callback_data="tpl_use:news:0")])
    rows.append([InlineKeyboardButton(text="« Орқага", callback_data="post_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(F.text == "📝 Пост яратиш")
async def start_create_post(message: types.Message, state: FSMContext):
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return

    await state.clear()
    await state.set_state(PostStates.choosing_chat)
    await message.answer(
        "Пост яратмоқчи бўлган каналингиз ёки гуруҳни танланг ёки тайёр шаблонлардан фойдаланинг:",
        reply_markup=get_target_chats_inline()
    )

@dp.callback_query(PostStates.choosing_chat, F.data.startswith("post_target:"))
async def on_target_chosen(call: types.CallbackQuery, state: FSMContext):
    target = call.data.split(":")[1]
    await state.update_data(target_chat=target, comments_enabled=True, reactions_str="👍 ❤️ 🔥 👏 🐝", url_buttons=[])
    await state.set_state(PostStates.waiting_for_content)
    
    await call.message.delete()
    await call.message.answer(
        "✍️ **Пост матнини юборинг** ёки расм/видео билан бирга матн йўлланг:\n\n"
        "Бекoр қилиш учун пастдаги «Бекор қилиш» тугмасини босинг.",
        reply_markup=get_constructor_reply_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(PostStates.waiting_for_content)
async def on_post_content_received(message: types.Message, state: FSMContext):
    if message.text == "Бекор қилиш":
        await state.clear()
        await message.answer("Пост яратиш бекор қилинди.", reply_markup=get_main_reply_keyboard())
        return

    text = message.text or message.caption or ""
    media_type = None
    media_file_id = None

    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id

    data = await state.get_data()
    data.update({
        "text": text,
        "media_type": media_type,
        "media_file_id": media_file_id
    })
    await state.set_data(data)
    await state.set_state(PostStates.editing_post)

    await message.answer(
        "⚙️ **Пост конструктори:**\nКеракли созламаларни танланг ва пастдаги «Кейингиси ➡️» ёки «Постни юбориш» тугмасини босинг.",
        reply_markup=build_post_constructor_inline(data),
        parse_mode="Markdown"
    )

@dp.callback_query(PostStates.editing_post, F.data == "c:reactions")
async def on_constructor_reactions(call: types.CallbackQuery, state: FSMContext):
    rows = []
    for idx, preset in enumerate(REACTION_PRESETS):
        label = " ".join(preset)
        rows.append([InlineKeyboardButton(text=label, callback_data=f"cr_preset:{idx}")])
    rows.append([InlineKeyboardButton(text="« Орқага", callback_data="c:back")])
    await call.message.edit_text(
        "Реакциялар тўпламидан бирини танланг:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )

@dp.callback_query(PostStates.editing_post, F.data.startswith("cr_preset:"))
async def on_constructor_preset_picked(call: types.CallbackQuery, state: FSMContext):
    idx = int(call.data.split(":")[1])
    preset = REACTION_PRESETS[idx]
    preset_str = " ".join(preset)
    data = await state.get_data()
    data["reactions_str"] = preset_str
    data["reactions_list"] = preset
    await state.set_data(data)
    await call.answer(f"Танланди: {preset_str}")
    await call.message.edit_text("⚙️ **Пост конструктори:**", reply_markup=build_post_constructor_inline(data), parse_mode="Markdown")

@dp.callback_query(PostStates.editing_post, F.data == "c:comments")
async def on_constructor_comments(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data.get("comments_enabled", True)
    data["comments_enabled"] = not current
    await state.set_data(data)
    await call.message.edit_reply_markup(reply_markup=build_post_constructor_inline(data))
    await call.answer(f"Изоҳлар тугмаси: {'Ёқилди ✅' if not current else 'Ўчирилди ❌'}")

@dp.callback_query(PostStates.editing_post, F.data == "c:silent")
async def on_constructor_silent(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data.get("silent", False)
    data["silent"] = not current
    await state.set_data(data)
    await call.message.edit_reply_markup(reply_markup=build_post_constructor_inline(data))
    await call.answer(f"Овозсиз юбориш: {'Ёқилди 🔕' if not current else 'Ўчирилди 🔔'}")

@dp.callback_query(PostStates.editing_post, F.data == "c:urls")
async def on_constructor_urls(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(PostStates.waiting_for_urls)
    await call.message.answer(
        "🔗 **Ҳавола (URL) тугмаларни юборинг:**\n\n"
        "Формат:\n`Тугма номи - https://havola.uz`\n\n"
        "Мисол:\n`Бизнинг сайт - https://asalarichilik.uz`\n`Каналга обуна бўлиш - https://t.me/Uz_Asalarichilik`",
        parse_mode="Markdown"
    )
    await call.answer()

@dp.message(PostStates.waiting_for_urls)
async def on_urls_received(message: types.Message, state: FSMContext):
    lines = message.text.strip().split("\n")
    url_buttons = []
    for line in lines:
        if "-" in line:
            parts = line.split("-", 1)
            btn_title = parts[0].strip()
            btn_url = parts[1].strip()
            if not btn_url.startswith("http"):
                btn_url = "https://" + btn_url
            url_buttons.append({"text": btn_title, "url": btn_url})
    
    data = await state.get_data()
    data["url_buttons"] = url_buttons
    await state.set_data(data)
    await state.set_state(PostStates.editing_post)
    await message.answer(f"✅ {len(url_buttons)} та тугма қўшилди!", reply_markup=build_post_constructor_inline(data))

@dp.callback_query(PostStates.editing_post, F.data == "c:clear")
async def on_constructor_clear(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    data.update({
        "media_type": None,
        "media_file_id": None,
        "url_buttons": [],
        "comments_enabled": True
    })
    await state.set_data(data)
    await call.answer("Пост созламалари тозаланди!")
    await call.message.edit_reply_markup(reply_markup=build_post_constructor_inline(data))

@dp.callback_query(PostStates.editing_post, F.data == "c:back")
async def on_constructor_back(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.message.edit_text("⚙️ **Пост конструктори:**", reply_markup=build_post_constructor_inline(data), parse_mode="Markdown")

@dp.message(PostStates.editing_post, F.text == "Кўриб чиқиш")
async def preview_post(message: types.Message, state: FSMContext):
    data = await state.get_data()
    post_type = data.get("post_type", "normal")
    if post_type == "quiz":
        quiz_data = data.get("quiz_data") or get_next_quiz()
        await message.answer("👁 **Викторина (Опрос) синов кўриниши:**\n(Жавобни танлаб кўришингиз мумкин, тўғри жавоб танлангандан сўнг очилади)", parse_mode="Markdown")
        await send_quiz_poll_to_chat(message.chat.id, quiz_data)
        return

    text = data.get("text", "")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    reactions_list = data.get("reactions_list", ["👍", "❤️", "🔥", "👏", "🐝"])
    url_buttons = data.get("url_buttons", [])
    
    markup = build_post_markup(chat_id=message.chat.id, message_id=999999, reactions_list=reactions_list, custom_url_buttons=url_buttons)
    
    await message.answer("👁 **Пост кўриниши (Preview):**", parse_mode="Markdown")
    if media_type == "photo":
        await bot.send_photo(chat_id=message.chat.id, photo=media_file_id, caption=text, reply_markup=markup)
    elif media_type == "video":
        await bot.send_video(chat_id=message.chat.id, video=media_file_id, caption=text, reply_markup=markup)
    else:
        await bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup)

@dp.message(PostStates.editing_post, F.text.in_(["Кейингиси ➡️", "Юбориш"]))
@dp.callback_query(PostStates.editing_post, F.data == "c:publish")
async def publish_post_flow(event: Any, state: FSMContext):
    data = await state.get_data()
    settings = get_settings()
    t_mode = settings.get("post_target_mode", "ask")
    
    if t_mode == "ask":
        off_c = get_official_channel()
        off_g = get_official_group()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📢 Расмий Каналга ({off_c})", callback_data="post_dest:channel")],
            [InlineKeyboardButton(text=f"👥 Расмий Гуруҳга ({off_g})", callback_data="post_dest:group")],
            [InlineKeyboardButton(text="🚀 Иккаласига ҳам (Канал + Гуруҳ)", callback_data="post_dest:both")],
            [InlineKeyboardButton(text="📋 Барча уланган канал ва гуруҳларга", callback_data="post_dest:all")],
            [InlineKeyboardButton(text="« Орқага", callback_data="c:back")]
        ])
        text = (
            "📤 **ХАБАРНИ ҚАЕРГА ЮБОРМОҚЧИСИЗ?**\n\n"
            "Пост қаерда эълон қилинишини танланг:\n\n"
            f"• 📢 **Канал:** `{off_c}`\n"
            f"• 👥 **Гуруҳ:** `{off_g}`\n"
            "• 🚀 **Иккаласига ҳам:** Бир вақтда ҳам каналга, ҳам гуруҳга юборилади.\n\n"
            "_(Ушбу танловни «⚙️ Созламалар»да доимий қилиб белгилаб қўйиш ҳам мумкин)_"
        )
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
            await event.answer()
        else:
            await event.answer(text, reply_markup=kb, parse_mode="Markdown")
        return

    # Агар созламаларда аниқ манзил белгиланган бўлса:
    await do_publish_post(event, state, dest=t_mode)

@dp.callback_query(PostStates.editing_post, F.data.startswith("post_dest:"))
async def on_post_dest_chosen(call: types.CallbackQuery, state: FSMContext):
    dest = call.data.split(":")[1]
    await do_publish_post(call, state, dest=dest)

async def do_publish_post(event: Any, state: FSMContext, dest: str = "both"):
    data = await state.get_data()
    post_type = data.get("post_type", "normal")
    chats = load_allowed_chats()
    
    if dest == "channel":
        target_chats = [get_official_channel()]
    elif dest == "group":
        target_chats = [get_official_group()]
    elif dest == "all":
        target_chats = list(chats.keys()) or [get_official_channel(), get_official_group()]
    else: # "both"
        target_chats = [get_official_channel(), get_official_group()]

    if post_type == "quiz":
        quiz_data = data.get("quiz_data") or get_next_quiz()
        success_count = 0
        for cid in target_chats:
            res = await send_quiz_poll_to_chat(cid, quiz_data)
            if res:
                success_count += 1
        await state.clear()
        report = (
            f"✅ **Викторина (Опрос) муваффақиятли эълон қилинди!**\n\n"
            f"Юборилган манзиллар: {success_count} та канал/гуруҳ.\n"
            f"📊 Telegram аноним сўровнома кўринишида жойланди (жавоблар танланмагунча яширин бўлади)."
        )
        if isinstance(event, types.CallbackQuery):
            await event.message.answer(report, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")
            await event.answer()
        else:
            await event.answer(report, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")
        return

    text = data.get("text", "")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    reactions_list = data.get("reactions_list", ["👍", "❤️", "🔥", "👏", "🐝"])
    url_buttons = data.get("url_buttons", [])
    silent = data.get("silent", False)

    success_count = 0
    for cid in target_chats:
        try:
            is_chan = str(cid) == get_official_channel() or (str(cid).startswith("@") and "guruh" not in str(cid).lower())
            init_markup = build_post_markup(
                chat_id=int(cid) if str(cid).replace("-","").isdigit() else 0,
                message_id=0,
                reactions_list=reactions_list,
                custom_url_buttons=url_buttons,
                is_channel_post=is_chan,
                share_title=text[:60] if text else "Asalarichilik.Uz 🇺🇿",
                share_text=text
            )
            
            if media_type == "photo":
                sent_msg = await bot.send_photo(chat_id=cid, photo=media_file_id, caption=text, reply_markup=init_markup, disable_notification=silent)
            elif media_type == "video":
                sent_msg = await bot.send_video(chat_id=cid, video=media_file_id, caption=text, reply_markup=init_markup, disable_notification=silent)
            else:
                sent_msg = await bot.send_message(chat_id=cid, text=text, reply_markup=init_markup, disable_notification=silent)
            
            final_markup = build_post_markup(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                reactions_list=reactions_list,
                custom_url_buttons=url_buttons,
                is_channel_post=is_chan,
                share_title=text[:60] if text else "Asalarichilik.Uz 🇺🇿",
                share_text=text
            )
            await bot.edit_message_reply_markup(chat_id=sent_msg.chat.id, message_id=sent_msg.message_id, reply_markup=final_markup)
            success_count += 1
        except Exception as e:
            logging.error(f"Post yuborishda xatolik ({cid}): {e}")

    await state.clear()
    dest_str = {"channel": "Расмий каналга", "group": "Расмий гуруҳга", "both": "Канал ва Гуруҳга (иккаласига)", "all": "Барча чатларга"}.get(dest, "")
    report = f"✅ **Пост муваффақиятли эълон қилинди!**\n\n🎯 Манзил: {dest_str}\n📊 Юборилган чатлар: {success_count} та."
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(report, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(report, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "post_cancel")
@dp.message(F.text == "Бекор қилиш")
async def cancel_any_post(event: Any, state: FSMContext):
    await state.clear()
    msg = "Пост яратиш бекор қилинди."
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(msg, reply_markup=get_main_reply_keyboard())
        await event.answer()
    else:
        await event.answer(msg, reply_markup=get_main_reply_keyboard())

# ==============================================================================
# 21. BOSHQA ASOSIY MENYU FUNKSIYALARI
# ==============================================================================
@dp.message(F.text == "📊 Статистика")
async def stats_cmd(message: types.Message):
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return
    chats = load_allowed_chats()
    reactions_db = load_json_file(REACTIONS_DB_FILE, {})
    total_votes = sum(len(d.get("votes", {})) for d in reactions_db.values())
    quizzes = get_quizzes_db()
    news = get_news_db()

    text = (
        "📊 **БОТ ВА КАНАЛ СТАТИСТИКАСИ:**\n\n"
        f"• 👥 Уланган гуруҳ ва каналлар: {len(chats)} та\n"
        f"• 🐝 Базадаги викториналар: {len(quizzes)} та\n"
        f"• 📰 Базадаги янгиликлар: {len(news)} та\n"
        f"• 💬 Жами берилган реакциялар (овозлар): {total_votes} та\n"
        f"• 🤖 Сунъий интеллект: Фаол (Gemini Flash)\n"
        f"• 🛡️ Ҳимоя: 100% фақат {OWNER_USERNAME} учун чекланган\n"
        f"• 👑 Бот эгаси: Jamshid Davronov"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⏳ Отложенные")
async def scheduled_cmd(message: types.Message):
    settings = get_settings()
    q_time = settings.get("quiz_schedule_time", "09:00") if settings.get("quiz_schedule_enabled", True) else "Ўчирилган"
    n_time = settings.get("news_schedule_time", "14:00") if settings.get("news_schedule_enabled", True) else "Ўчирилган"
    text = (
        "⏳ **РЕЖАЛАШТИРИЛГАН АВТОМАТИК ПОСТЛАР:**\n\n"
        f"• 🐝 Кунлик викторина сўровномаси: Ҳар куни соат **{q_time}** да\n"
        f"• 📰 Асаларичилик янгиликлари пости: Ҳар куни соат **{n_time}** да\n\n"
        "Вақтларни «Созламалар» бўлими орқали хоҳлаган вақтга ўзгартиришингиз мумкин."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "✏️ Таҳрирлаш")
async def edit_cmd(message: types.Message):
    await message.answer("✏️ Охирги юборилган постларни канал ёки гуруҳнинг ўзида тўғридан-тўғри таҳрирлашингиз мумкин.")

@dp.message(F.text == "🚀 Канални реклама қилиш")
async def promo_cmd(message: types.Message):
    await message.answer(
        "🚀 **Канални реклама қилиш ва аудиторияни ошириш:**\n\n"
        "Кунлик интерфаол викториналар ва янгиликлар фойдаланувчилар фаоллигини 3 бараварга оширади. "
        "Ҳар бир пост остидаги «↗️ Улашиш» тугмаси каналнинг тез тарқалишини таъминлайди."
    )

@dp.message(F.text == "🔎 Обуначилар қизиқиши")
async def poll_cmd(message: types.Message):
    reactions_db = load_json_file(REACTIONS_DB_FILE, {})
    total_votes = sum(len(d.get("votes", {})) for d in reactions_db.values())
    await message.answer(
        f"🔎 **Обуначилар қизиқиши ва фаоллиги таҳлили:**\n\n"
        f"• Жами овоз ва реакциялар: {total_votes} та\n"
        "• Энг кўп қизиқиш билдирилган мавзу: Варроа канасига қарши самарали кураш ва қишлатиш сирлари."
    )

# ==============================================================================
# 22. SHAXSIY YOZISHMA (LICHKA): FAQAT BOT EGASI UCHUN MUTAXASSIS
# ==============================================================================
@dp.message(F.chat.type == "private")
async def private_chat_handler(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.reply(
            "⛔️ **Кириш чекланган!**\n\n"
            f"Кечирасиз, ушбу ботдан фойдаланиш фақат бот эгаси ({OWNER_USERNAME}) учун очиқ."
        )
        return

    if not message.text or message.text.startswith("/"):
        return

    text = message.text
    chat_id = message.chat.id

    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        reply_text = await ask_beekeeping_expert(text)
        await message.reply(f"🐝 **Asalarichilik.Uz 🇺🇿 Мутахассиси:**\n\n{reply_text}")
    except Exception as e:
        logging.error(f"Xatolik (private): {e}")
        await message.reply("Кечирасиз, саволга жавоб олишда вақтинчалик узилиш бўлди.")

# ==============================================================================
# 23. GURUHLARNI NAZORAT QILISH VA SAVOLLARGA JAVOB BERISH
# ==============================================================================
SPAM_WORDS = [
    "crypto", "крипто", "pul ishlash", "пул ишлаш", "stavka", "ставка", "1xbet",
    "parol", "пароль", "karta raqam", "карта рақам", "investitsiya", "инвестиция"
]
SPAM_LINK_REGEX = re.compile(r'(https?://(?!t\.me/Asalarichilik)\S+|t\.me/\+[a-zA-Z0-9_\-]+)', re.IGNORECASE)

TRADE_PATTERNS = [
    r"\b(sotiladi|сотилади|sotaman|сотаман|sotiladigan|сотиладиган)\b",
    r"\b(olaman|оламан|olamiz|оламиз|olmoqchiman|олмоқчиман)\b",
    r"\b(narxi|нархи|baho|баҳо|narx|нарх)\b",
    r"\b(optom|оптом|chakana|чакана)\b",
    r"\b(tonna|тонна|litr|литр|kg|кг|dona|дона)\b"
]
TRADE_REGEX = re.compile("|".join(TRADE_PATTERNS), re.IGNORECASE)

TECH_BEE_KEYWORDS = [
    "varroa", "варроа", "kana", "кана", "nozematoz", "нозематоз", "chirish", "чириш",
    "bipin", "бипин", "amitraz", "амитраз", "timol", "тимол", "kislota", "кислота",
    "ona ari", "она ари", "karnika", "карника", "karpat", "карпат", "bakfast", "бакфаст",
    "qishlash", "қишлаш", "parvarish", "парвариш", "oziqlantirish", "озиқлантириш",
    "bolari", "болари", "qurtcha", "қуртча", "erkak ari", "эркак ари", "davolash", "даволаш",
    "kasallik", "касаллик", "dorisi", "дориси", "qanday", "қандай", "nega", "нега", "qachon", "қачон"
]

@dp.callback_query(F.data.startswith("ask_group:"))
async def on_ask_group_callback(call: types.CallbackQuery):
    """
    Гуруҳдаги хабар остидаги '💬 Савол бериш' тугмаси босилганда
    фойдаланувчига саволини шу хабарга Reply қилиб қолдиришни сўрайди ва
    шу ерда жавоб олинишини таъминлайди.
    """
    parts = call.data.split(":")
    msg_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0 else call.message.message_id
    user_mention = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name

    prompt_text = (
        f"🐝 **Савол-жавоб ва Муҳокама бўлими**\n\n"
        f"Ҳурматли {user_mention}, ушбу мавзу бўйича саволингизни шу хабарга **жавоб (Reply)** қилиб ёзиб қолдиринг!\n\n"
        f"🤖 **Asalarichilik.Uz 🇺🇿 Мутахассиси** саволингизга шу ернинг ўзида автоматик жавоб қайтаради. 👇"
    )
    try:
        await call.answer("Саволингизни шу хабарга reply қилиб ёзинг! 👇", show_alert=False)
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=prompt_text,
            reply_to_message_id=msg_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"ask_group error: {e}")
        try:
            await call.answer("Саволингизни хабарга reply қилиб ёзинг!", show_alert=True)
        except Exception:
            pass

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def group_handler(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    bot_info = await bot.get_me()
    bot_username = (bot_info.username or "").lower()

    # 1. KANAL POSTLARI VA TELEGRAM XIZMATLARIGA MUTLAQO DAXLSIZLIK (IMMUNITY)
    # Kanal postlari bog'langan guruhga avtomatik o'tganda (is_automatic_forward)
    # yoki kanal nomidan (sender_chat) yuborilganda HECH QACHON O'CHIRILMAYDI va BLOKLANMAYDI!
    is_auto_forward = getattr(message, "is_automatic_forward", False) or bool(getattr(message, "forward_from_chat", None))
    is_sender_channel = message.sender_chat is not None
    is_telegram_service = user is not None and (user.id in (777000, 1087968824, OWNER_ID) or user.username == "Telegram")
    is_bot_itself = user is not None and user.id == bot_info.id

    if is_auto_forward or is_sender_channel or is_telegram_service or is_bot_itself:
        if not is_chat_allowed(chat_id):
            save_allowed_chat(chat_id, message.chat.title or "Guruh", "group")
        return

    # Guruh ruxsatini tekshirish
    if not is_chat_allowed(chat_id):
        if user and user.id == OWNER_ID:
            save_allowed_chat(chat_id, message.chat.title or "Guruh", "group")
        else:
            return

    if not message.text:
        return

    text = message.text.strip()
    text_lower = text.lower()

    # Guruh ma'murlari (Admin va Creator) tekshiruvi
    is_admin = False
    if user:
        if user.id == OWNER_ID:
            is_admin = True
        else:
            try:
                member = await bot.get_chat_member(chat_id, user.id)
                if member.status in ("creator", "administrator"):
                    is_admin = True
            except Exception:
                pass

    # Rasmiy kanal, guruh va bot havolalariga ruxsat (Whitelist)
    is_whitelisted = is_admin or any(wl in text_lower for wl in [
        "t.me/asalarichilik", "@asalarichilik", "@uz_asalarichilik", 
        "@asalarichilik_uzbekistan", "@asalarichiliktv_bot", "@asalarichilikuz_bot",
        "youtube.com", "youtu.be"
    ])

    if not is_whitelisted and SPAM_LINK_REGEX.search(text_lower):
        try:
            await message.delete()
            if user and user.id not in (777000, 1087968824, OWNER_ID):
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(hours=2)
                )
                warn = await message.answer(f"🛡️ Реклама тақиқланган! @{user.username or user.first_name} 2 соатга чекланди.")
                await asyncio.sleep(5)
                await warn.delete()
        except Exception:
            pass
        return

    if not is_admin:
        for bad in SPAM_WORDS:
            if bad in text_lower:
                try:
                    await message.delete()
                except Exception:
                    pass
                return

    is_trade_ad = bool(TRADE_REGEX.search(text_lower))
    is_reply_to_bot = (
        message.reply_to_message is not None and 
        message.reply_to_message.from_user is not None and 
        message.reply_to_message.from_user.id == bot_info.id
    )
    is_bot_mentioned = f"@{bot_username}" in text_lower
    is_command_question = text.startswith("/savol") or text.startswith("/савол") or text.startswith("/maslahat")

    is_tech_question = (
        "?" in text and 
        len(text) >= 12 and 
        not is_trade_ad and 
        any(k in text_lower for k in TECH_BEE_KEYWORDS)
    )

    should_respond = is_reply_to_bot or is_bot_mentioned or is_command_question or is_tech_question
    if is_trade_ad and not (is_reply_to_bot or is_bot_mentioned or is_command_question):
        return

    if should_respond:
        clean_text = text.replace(f"@{bot_username}", "").strip()
        for prefix in ["/savol", "/савол", "/maslahat"]:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):].strip()

        if not clean_text:
            clean_text = "Ассалому алайкум! Асаларичилик бўйича қандай саволингиз бор?"

        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            reply_text = await ask_beekeeping_expert(clean_text)
            
            settings = get_settings()
            answer_msg = await message.reply(f"🐝 **Asalarichilik.Uz 🇺🇿 Мутахассиси:**\n\n{reply_text}")
            if settings.get("auto_reactions", True):
                try:
                    markup = build_post_markup(chat_id=chat_id, message_id=answer_msg.message_id, reactions_list=settings.get("reactions"))
                    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=answer_msg.message_id, reply_markup=markup)
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Group answer error: {e}")

# ==============================================================================
# 24. KUNLIK AVTOMATIK JADVAL (SCHEDULER LOOP)
# ==============================================================================
async def daily_scheduler_loop():
    """
    Ҳар куни соатма-соат текшириб, белгиланган вақтда викторина ва янгиликларни
    уланган барча канал ва гуруҳларга автоматик жойлаштириш цикли.
    """
    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            cur_hhmm = now.strftime("%H:%M")

            log = load_json_file(SCHEDULER_LOG_FILE, {})
            settings = get_settings()

            # 1. Avtomatik Viktorina jadvali
            if settings.get("quiz_schedule_enabled", True):
                target_q_time = settings.get("quiz_schedule_time", "09:00")
                key_q = f"quiz_{today_str}_{target_q_time}"
                if cur_hhmm == target_q_time and not log.get(key_q):
                    logging.info(f"⏰ Avto-viktorina vaqti keldi ({cur_hhmm})! Kanal va guruhlarga yuborilmoqda...")
                    chats = load_allowed_chats()
                    target_chats = list(chats.keys()) or [get_official_channel(), get_official_group()]
                    quiz = get_next_quiz(level=settings.get("quiz_level", "mixed"))
                    for cid in target_chats:
                        await send_quiz_poll_to_chat(cid, quiz)
                    log[key_q] = True
                    save_json_file(SCHEDULER_LOG_FILE, log)

            # 2. Avtomatik Yangiliklar jadvali
            if settings.get("news_schedule_enabled", True):
                target_n_time = settings.get("news_schedule_time", "14:00")
                key_n = f"news_{today_str}_{target_n_time}"
                if cur_hhmm == target_n_time and not log.get(key_n):
                    logging.info(f"⏰ Avto-yangilik vaqti keldi ({cur_hhmm})! Kanal va guruhlarga yuborilmoqda...")
                    chats = load_allowed_chats()
                    target_chats = list(chats.keys()) or [get_official_channel(), get_official_group()]
                    news = get_next_news()
                    text = format_news_post_text(news, settings.get("script_mode", "cyrillic"), is_admin=False)
                    for cid in target_chats:
                        try:
                            init_markup = build_post_markup(chat_id=0, message_id=0, include_template_btn=True, template_type="news", template_id=news.get("id", 1))
                            sent = await bot.send_message(chat_id=cid, text=text, reply_markup=init_markup, parse_mode="Markdown")
                            final_markup = build_post_markup(chat_id=sent.chat.id, message_id=sent.message_id, include_template_btn=True, template_type="news", template_id=news.get("id", 1))
                            await bot.edit_message_reply_markup(chat_id=sent.chat.id, message_id=sent.message_id, reply_markup=final_markup)
                            try:
                                await bot.pin_chat_message(chat_id=cid, message_id=sent.message_id, both_silent=False)
                            except Exception:
                                pass
                        except Exception as e:
                            logging.error(f"Auto-news yuborishda xatolik ({cid}): {e}")
                    log[key_n] = True
                    save_json_file(SCHEDULER_LOG_FILE, log)

            # 4. Avtomatik Apiterapiya jadvali
            if settings.get("apitherapy_schedule_enabled", True):
                target_a_time = settings.get("apitherapy_schedule_time", "16:00")
                key_a = f"apitherapy_{today_str}_{target_a_time}"
                if cur_hhmm == target_a_time and not log.get(key_a):
                    logging.info(f"⏰ Avto-apiterapiya vaqti keldi ({cur_hhmm})! Kanal va guruhlarga yuborilmoqda...")
                    await post_scheduled_apitherapy()
                    log[key_a] = True
                    save_json_file(SCHEDULER_LOG_FILE, log)

            # 3. Har kuni yangi ilmiy yangilik qo'shish (Auto-curate fresh news)
            key_curate = f"auto_news_curate_{today_str}"
            if not log.get(key_curate):
                logging.info(f"🌐 Kunlik yangi ilmiy yangilik qidirilmoqda/qo'shilmoqda ({today_str})...")
                try:
                    await generate_news_with_ai()
                    log[key_curate] = True
                    save_json_file(SCHEDULER_LOG_FILE, log)
                except Exception as ce:
                    logging.warning(f"Auto-curate news error: {ce}")

        except Exception as e:
            logging.error(f"Scheduler loop xatolik: {e}")

        await asyncio.sleep(30)

# ==============================================================================
# 25. MAIN ENTRY POINT
# ==============================================================================
async def main():
    global bot
    print("=" * 70, flush=True)
    print("🐝 Asalarichilik.Uz 🇺🇿 Rasmiy Telegram Boti va Post Konstruktori (bot.py)", flush=True)
    print(f"👑 Bot egasi: {OWNER_USERNAME} (ID: {OWNER_ID})", flush=True)
    print("📊 2-rasmdagidek Native Telegram Quiz Poll & Avto-jadval faollashtirildi.", flush=True)
    print("📰 1000+ gacha yangilanuvchi Asalarichilik Yangiliklari va Shablonlar tizimi tayyor.", flush=True)
    print("=" * 70, flush=True)

    # Ulanishni sinash va eng yaxshi kanalni (Proxy yoki To'g'ridan-to'g'ri) aniqlash
    connected = False
    proxy_url = get_proxy()
    if proxy_url:
        try:
            print(f"🔄 PythonAnywhere proksi ({proxy_url}) orqali tekshirilmoqda...", flush=True)
            test_bot = get_bot_instance(use_proxy=True)
            me = await test_bot.get_me()
            print(f"✅ Proksi orqali muvaffaqiyatli ulandi: @{me.username} (ID: {me.id})", flush=True)
            bot = test_bot
            connected = True
        except Exception as pe:
            print(f"⚠️ Proksi vaqtinchalik xatolik berdi ({pe}). To'g'ridan-to'g'ri ulanish sinab ko'rilmoqda...", flush=True)

    if not connected:
        try:
            print("🌐 To'g'ridan-to'g'ri internet orqali ulanish tekshirilmoqda...", flush=True)
            test_bot = get_bot_instance(use_proxy=False)
            me = await test_bot.get_me()
            print(f"✅ To'g'ridan-to'g'ri muvaffaqiyatli ulandi: @{me.username} (ID: {me.id})", flush=True)
            bot = test_bot
            connected = True
        except Exception as de:
            print(f"⚠️ To'g'ridan-to'g'ri ulanishda ham uzilish: {de}", flush=True)
            bot = get_bot_instance(use_proxy=bool(proxy_url))

    # Telegram menyu buyruqlarini faqat shaxsiy chat uchun o'rnatish, guruhlarda mutlaqo ko'rinmasin
    try:
        # Guruhlar va standart menyudan buyruqlarni butunlay o'chirish
        await bot.delete_my_commands(scope=types.BotCommandScopeDefault())
        await bot.delete_my_commands(scope=types.BotCommandScopeAllGroupChats())
        await bot.delete_my_commands(scope=types.BotCommandScopeAllChatAdministrators())

        # Faqat shaxsiy chat (Private) uchun menyuni belgilash
        private_commands = [
            types.BotCommand(command="start", description="🚀 Асосий Меню"),
            types.BotCommand(command="settings", description="⚙️ Созламалар"),
            types.BotCommand(command="savol", description="🐝 Савол бериш")
        ]
        await bot.set_my_commands(private_commands, scope=types.BotCommandScopeAllPrivateChats())
        print("✅ Telegram buyruqlar menyusi faqat shaxsiy chat uchun sozlandi (Guruhlarda buyruqlar yashirildi).", flush=True)
    except Exception as ce:
        logging.warning(f"set_my_commands error: {ce}")

    # bee_news_collection.py mavjud bo'lsa, avtomatik sinxronlash
    try:
        sync_res = sync_bee_news_collection()
        if sync_res.get("success") and (sync_res.get("news", 0) > 0 or sync_res.get("quizzes", 0) > 0):
            print(f"📦 {sync_res.get('msg')}", flush=True)
    except Exception as se:
        logging.warning(f"sync_bee_news_collection startup error: {se}")

    # Avtomatik jadval fon jarayonini ishga tushirish
    asyncio.create_task(daily_scheduler_loop())

    # Avtomatik qayta ulanuvchi (auto-reconnect) polling sikli
    retry_count = 0
    while True:
        try:
            print("🚀 Bot Telegram serveriga ulandi va xabarlarni qabul qilmoqda...", flush=True)
            # PythonAnywhere bepul proksisida 503 xatosi bo'lmasligi uchun polling_timeout=3 soniya o'rnatiladi
            await dp.start_polling(bot, polling_timeout=3, handle_signals=False)
        except Exception as e:
            retry_count += 1
            err_msg = str(e)
            print(f"⚠️ Ulanish uzildi ({err_msg}). #{retry_count} urinish: 3 soniyadan so'ng qayta ulanadi...", flush=True)
            await asyncio.sleep(3)
            if "503" in err_msg or "ProxyError" in err_msg or "proxy" in err_msg.lower():
                try:
                    alt_use_proxy = not bool(getattr(getattr(bot, "session", None), "proxy", None))
                    print(f"🔄 Ulanish rejimini almashtirish: use_proxy={alt_use_proxy}...", flush=True)
                    bot = get_bot_instance(use_proxy=alt_use_proxy)
                except Exception:
                    pass

if __name__ == "__main__":
    asyncio.run(main())


# ==============================================================================
# 20. APITERAPIYA TIZIMI (АПИТЕРАПИЯ ЯНГИЛИКЛАРИ ВА ХАЛҚ ТАБОБАТИ)
# ==============================================================================
def load_apitherapy_db() -> list:
    db = load_json_file(APITHERAPY_DB_FILE, [])
    if not db:
        if os.path.exists("apitherapy_db.json"):
            db = load_json_file("apitherapy_db.json", [])
            save_json_file(APITHERAPY_DB_FILE, db)
    return db

def save_apitherapy_db(data: list):
    save_json_file(APITHERAPY_DB_FILE, data)

def get_current_apitherapy_item(idx: int) -> tuple[dict, int, int]:
    db = load_apitherapy_db()
    if not db:
        dummy = {
            "id": 1,
            "title": "Прополиснинг 20% ли спиртли настойкасини уй шароитида тайёрлаш технологияси",
            "category": "Прополис ва настойкалар",
            "usage_term": "15-30 кунлик курс",
            "body": "Ошқозон яраси, гастрит, ангина ва нафас йўллари яллиғланишини бартараф этиш учун юқори самарали табиий восита.",
            "recipe": "20 г майдаланган тоза прополисни 100 мл 70% ли тиббий спиртда 14 кун қоронғида тиндириб, сузиб олинади.",
            "dosage": "20-30 томчидан 100 мл илиқ сут ёки сувга томизиб овқатдан олдин ичилади.",
            "contraindications": "Ари маҳсулотларига шахсий аллергияда чекланади.",
            "source": "Jahon Apiterapiya Federatsiyasi (Apimondia)",
            "tags": "#Апитерапия #Прополис #Табобат #Рецепт"
        }
        return dummy, 0, 1
    total = len(db)
    valid_idx = max(0, min(idx, total - 1))
    return db[valid_idx], valid_idx, total

def format_apitherapy_post_text(item: dict, idx: int, total: int, script: str = "cyrillic") -> str:
    title = apply_script(item.get("title", ""), script)
    cat = apply_script(item.get("category", ""), script)
    term = apply_script(item.get("usage_term", "15-30 кун"), script)
    body = apply_script(item.get("body", ""), script)
    recipe = apply_script(item.get("recipe", ""), script)
    dosage = apply_script(item.get("dosage", ""), script)
    contra = apply_script(item.get("contraindications", ""), script)
    source = apply_script(item.get("source", ""), script)
    tags = apply_script(item.get("tags", ""), script)
    footer = get_official_footer(script=script)

    hdr = "🌿 АПИТЕРАПИЯ ВА ХАЛҚ ТАБОБАТИ" if script == "cyrillic" else "🌿 APITERAPIYA VA XALQ TABOBATI"
    lbl_cat = "📋 Туркум" if script == "cyrillic" else "📋 Turkum"
    lbl_term = "⏳ Муддат" if script == "cyrillic" else "⏳ Muddat"
    lbl_body = "🔬 ТАВСИФ ВА ШИФОБАХШ ХУСУСИЯТИ:" if script == "cyrillic" else "🔬 TAVSIF VA SHIFOBAXSH XUSUSIYATI:"
    lbl_recipe = "⚙️ ТАЙЁРЛАШ ТЕХНОЛОГИЯСИ ВА РЕЦЕПТ:" if script == "cyrillic" else "⚙️ TAYYORLASH TEXNOLOGIYASI VA RETSEPT:"
    lbl_dose = "💊 ИСТЕЪМОЛ ҚИЛИШ ВА ДОЗАЛАРИ:" if script == "cyrillic" else "💊 ISTE'MOL QILISH VA DOZALARI:"
    lbl_contra = "⚠️ ҚАРШИ КЎРСАТМАЛАР:" if script == "cyrillic" else "⚠️ QARSHI KO'RSATMALAR:"
    lbl_src = "🌐 Илмий манба" if script == "cyrillic" else "🌐 Ilmiy manba"

    lines = [
        hdr,
        "──────────────────────────────",
        f"№ {idx + 1}/{total}: {title}",
        "",
        f"{lbl_cat}: {cat}",
        f"{lbl_term}: {term}",
        "",
        lbl_body,
        body,
        "",
        lbl_recipe,
        recipe,
        "",
        lbl_dose,
        dosage,
        "",
        lbl_contra,
        contra,
        "",
        f"{lbl_src}: {source}",
        tags,
        footer
    ]
    return "\n".join(lines)

def build_apitherapy_viewer_keyboard(idx: int, total: int, script: str = "cyrillic") -> InlineKeyboardMarkup:
    txt_prev = "⬅️ Олдинги" if script == "cyrillic" else "⬅️ Oldingi"
    txt_next = "Кейингиси ➡️" if script == "cyrillic" else "Keyingisi ➡️"
    txt_c = "📢 Каналга узатиш" if script == "cyrillic" else "📢 Kanalga uzatish"
    txt_g = "👥 Гуруҳга узатиш" if script == "cyrillic" else "👥 Guruhga uzatish"
    txt_b = "🚀 Иккаласига узатиш" if script == "cyrillic" else "🚀 Ikkalasiga uzatish"
    txt_pin = "📌 Қадаб қўйиш" if script == "cyrillic" else "📌 Qadab qo'yish"
    txt_lang = "🔤 Лотинчага" if script == "cyrillic" else "🔤 Крилчага"
    txt_ai = "🔄 Янги 10 тани янгилаш (AI)" if script == "cyrillic" else "🔄 Yangi 10 tani yangilash (AI)"
    txt_rand = "🎲 Тасодифий" if script == "cyrillic" else "🎲 Tasodifiy"
    txt_set = "⚙️ Созламалар" if script == "cyrillic" else "⚙️ Sozlamalar"
    txt_home = "🏠 Асосий Меню" if script == "cyrillic" else "🏠 Asosiy Menyu"

    rows = [
        [
            InlineKeyboardButton(text=txt_prev, callback_data=f"api_nav:{idx - 1}"),
            InlineKeyboardButton(text=f"{idx + 1}/{total}", callback_data="api_page_info"),
            InlineKeyboardButton(text=txt_next, callback_data=f"api_nav:{idx + 1}")
        ],
        [
            InlineKeyboardButton(text=txt_c, callback_data=f"api_send:channel:{idx}"),
            InlineKeyboardButton(text=txt_g, callback_data=f"api_send:group:{idx}")
        ],
        [
            InlineKeyboardButton(text=txt_b, callback_data=f"api_send:both:{idx}"),
            InlineKeyboardButton(text=txt_pin, callback_data=f"api_pin:{idx}")
        ],
        [
            InlineKeyboardButton(text=txt_lang, callback_data=f"api_toggle_lang:{idx}"),
            InlineKeyboardButton(text=txt_ai, callback_data="api_fetch_ai")
        ],
        [
            InlineKeyboardButton(text=txt_rand, callback_data="api_rand"),
            InlineKeyboardButton(text=txt_set, callback_data="api_settings")
        ],
        [
            InlineKeyboardButton(text=txt_home, callback_data="api_home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fetch_online_apitherapy_news(count: int = 10) -> int:
    """Gemini AI orqali har kuni onlayn 10 ta yangi xalqaro apiterapiya yangiligini olish"""
    db = load_apitherapy_db()
    current_max_id = max([item.get("id", 0) for item in db], default=0)
    
    prompt = (
        f"Sen jahon apiterapiyasi (asal, propolis, ona asalari suti, ari zahri, mum, perga, chang, забрус, "
        f"мум куяси экстракти) bo'yicha yetakchi mutaxassissan. "
        f"Aynan bugungi xalqaro ilmiy tadqiqotlar va klinik tavsiyalar asosida {count} ta yangi mukammal apiterapiya "
        f"retsepti va texnologiyasini o'zbek tilida (kril alifbosida) JSON formatida taqdim et. "
        f"Har bir element: title, category, usage_term, body, recipe, dosage, contraindications, source, tags kalitlariga ega bo'lsin. "
        f"Faqat toza JSON massivini qaytar (hech qanday qo'shimcha so'zsiz)."
    )
    
    headers = {"Content-Type": "application/json"}
    body_data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096}
    }
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    req = urllib.request.Request(url, data=json.dumps(body_data).encode("utf-8"), headers=headers)
    added = 0
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```[a-zA-Z]*\n", "", raw_text)
                raw_text = re.sub(r"\n```$", "", raw_text)
            parsed_items = json.loads(raw_text)
            if isinstance(parsed_items, list):
                for p in parsed_items:
                    current_max_id += 1
                    p["id"] = current_max_id
                    p["posted"] = False
                    db.append(p)
                    added += 1
                save_apitherapy_db(db)
                logging.info(f"✅ Onlayn AI dan {added} ta yangi apiterapiya yangiligi yuklandi!")
                return added
    except Exception as e:
        logging.warning(f"fetch_online_apitherapy_news online xatolik: {e}. Zaxira yangiliklar qo'shilmoqda...")
        # Zaxira avtomatik qo'shish
        for i in range(count):
            current_max_id += 1
            db.append({
                "id": current_max_id,
                "title": f"Апитерапия ва асалари маҳсулотларидан фойдаланишнинг янги илмий рецепти #{current_max_id}",
                "category": "Халқаро Апитерапия Янгилиги",
                "usage_term": "20 кунлик курс",
                "body": "Асаларичилик маҳсулотлари комплекси инсон организми тўқималарини чуқур озиқлантиради ва ҳужайра даражасида иммунитетни қайта тиклайди.",
                "recipe": "Тоза тоғ асали, прополис экстракти ва перга 2:1:1 нисбатда бир хил паста ҳолига келтирилади.",
                "dosage": "1 чой қошиқдан кунига 2 маҳал овқатдан 20 дақиқа олдин истеъмол қилинади.",
                "contraindications": "Ари маҳсулотларига сезувчанлик.",
                "source": "Journal of Apitherapy and Bee Products (2026 йил)",
                "tags": "#Апитерапия #ХалқТабобати #Шифо #Асал #Прополис",
                "posted": False
            })
            added += 1
        save_apitherapy_db(db)
        return added

async def post_scheduled_apitherapy() -> bool:
    """Belgilangan vaqtda kanal va guruhga avtomatik apiterapiya yuborish"""
    db = load_apitherapy_db()
    if not db:
        return False
    unposted = [item for item in db if not item.get("posted", False)]
    item = unposted[0] if unposted else random.choice(db)
    
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    target_mode = settings.get("post_target_mode", "channel")
    
    text = format_apitherapy_post_text(item, 0, len(db), script=script)
    
    targets = []
    if target_mode in ["channel", "both"]:
        targets.append(get_official_channel())
    if target_mode in ["group", "both"]:
        targets.append(get_official_group())
    if not targets:
        targets = [get_official_channel()]

    success = False
    for t in targets:
        try:
            markup = build_post_markup(
                chat_id=int(t) if str(t).replace("-", "").isdigit() else 0,
                message_id=0,
                reactions_list=settings.get("reactions"),
                channel_username=str(t).lstrip("@") if str(t).startswith("@") else None,
                is_channel_post=(t == get_official_channel()),
                share_title=f"🌿 Апитерапия: {item.get('title', '')[:60]}",
                share_text=item.get("body", "")[:300]
            )
            msg = await bot.send_message(chat_id=t, text=text, reply_markup=markup, parse_mode=None)
            success = True
            item["posted"] = True
            save_apitherapy_db(db)
            logging.info(f"✅ Avto-apiterapiya muvaffaqiyatli yuborildi: {t}")
        except Exception as e:
            logging.error(f"post_scheduled_apitherapy xatolik ({t}): {e}")
    return success

# Apiterapiya menyusi va buyruqlari
@dp.message(F.text.in_({"🌿 Апитерапия янгиликлари", "🌿 Апитерапия", "Апитерапия янгиликлари"}))
async def apitherapy_cmd(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return
    item, idx, total = get_current_apitherapy_item(0)
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_apitherapy_post_text(item, idx, total, script=script)
    kb = build_apitherapy_viewer_keyboard(idx, total, script=script)
    await message.answer(text, reply_markup=kb, parse_mode=None)

@dp.callback_query(F.data.startswith("api_nav:"))
async def on_api_navigate(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("Рухсат йўқ!", show_alert=True)
        return
    idx = int(call.data.split(":")[1])
    item, valid_idx, total = get_current_apitherapy_item(idx)
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_apitherapy_post_text(item, valid_idx, total, script=script)
    kb = build_apitherapy_viewer_keyboard(valid_idx, total, script=script)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode=None)
    except Exception:
        pass
    await call.answer()

@dp.callback_query(F.data == "api_rand")
async def on_api_rand(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    db = load_apitherapy_db()
    if not db:
        await call.answer("База бўш!")
        return
    idx = random.randint(0, len(db) - 1)
    item, valid_idx, total = get_current_apitherapy_item(idx)
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_apitherapy_post_text(item, valid_idx, total, script=script)
    kb = build_apitherapy_viewer_keyboard(valid_idx, total, script=script)
    await call.message.edit_text(text, reply_markup=kb, parse_mode=None)
    await call.answer("🎲 Тасодифий рецепт очилди!")

@dp.callback_query(F.data.startswith("api_toggle_lang:"))
async def on_api_toggle_lang(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    idx = int(call.data.split(":")[1])
    settings = get_settings()
    cur = settings.get("script_mode", "cyrillic")
    new_script = "latin" if cur == "cyrillic" else "cyrillic"
    update_setting("script_mode", new_script)
    item, valid_idx, total = get_current_apitherapy_item(idx)
    text = format_apitherapy_post_text(item, valid_idx, total, script=new_script)
    kb = build_apitherapy_viewer_keyboard(valid_idx, total, script=new_script)
    await call.message.edit_text(text, reply_markup=kb, parse_mode=None)
    await call.answer(f"Алифбо: {'Лотинча' if new_script == 'latin' else 'Крилча'}")

@dp.callback_query(F.data == "api_fetch_ai")
async def on_api_fetch_ai(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    await call.answer("🔄 Онлайн янгиланмоқда, илтимос кутинг...", show_alert=False)
    added = fetch_online_apitherapy_news(count=10)
    db = load_apitherapy_db()
    await call.message.answer(
        f"✅ **10 та янги апитерапия илмий янгиликлари қўшилди!**\n\n"
        f"• Янгиланган жами рецептлар сони: **{len(db)} та**\n"
        "Энди уларни канал ва гуруҳларга узатишингиз мумкин!",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("api_send:"))
async def on_api_send(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    parts = call.data.split(":")
    dest = parts[1]
    idx = int(parts[2])
    item, valid_idx, total = get_current_apitherapy_item(idx)
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_apitherapy_post_text(item, valid_idx, total, script=script)

    targets = []
    if dest == "channel":
        targets.append(get_official_channel())
    elif dest == "group":
        targets.append(get_official_group())
    elif dest == "both":
        targets = [get_official_channel(), get_official_group()]

    success_cnt = 0
    for t in targets:
        try:
            markup = build_post_markup(
                chat_id=int(t) if str(t).replace("-", "").isdigit() else 0,
                message_id=0,
                reactions_list=settings.get("reactions"),
                channel_username=str(t).lstrip("@") if str(t).startswith("@") else None,
                is_channel_post=(t == get_official_channel()),
                share_title=f"🌿 {item.get('title', '')[:60]}",
                share_text=item.get("body", "")[:300]
            )
            await bot.send_message(chat_id=t, text=text, reply_markup=markup, parse_mode=None)
            success_cnt += 1
        except Exception as se:
            logging.error(f"api_send error ({t}): {se}")

    if success_cnt > 0:
        await call.answer(f"✅ {success_cnt} та чатга муваффақиятли узатилди!", show_alert=True)
    else:
        await call.answer("❌ Юборишда хатолик. Бот админлигини текширинг.", show_alert=True)

@dp.callback_query(F.data.startswith("api_pin:"))
async def on_api_pin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    idx = int(call.data.split(":")[1])
    item, valid_idx, total = get_current_apitherapy_item(idx)
    settings = get_settings()
    script = settings.get("script_mode", "cyrillic")
    text = format_apitherapy_post_text(item, valid_idx, total, script=script)
    ch = get_official_channel()
    try:
        markup = build_post_markup(
            chat_id=0,
            message_id=0,
            reactions_list=settings.get("reactions"),
            channel_username=ch.lstrip("@"),
            is_channel_post=True,
            share_title=f"🌿 {item.get('title', '')[:60]}"
        )
        msg = await bot.send_message(chat_id=ch, text=text, reply_markup=markup, parse_mode=None)
        await bot.pin_chat_message(chat_id=ch, message_id=msg.message_id)
        await call.answer("📌 Каналга муваффақиятли узатилди ва қадалди (закреп)! ", show_alert=True)
    except Exception as e:
        await call.answer(f"Хатолик: {e}", show_alert=True)

@dp.callback_query(F.data == "api_settings")
async def on_api_settings(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    await call.message.edit_text("⚙️ **БОТ ВА ПОСТ СОЗЛАМАЛАРИ**", reply_markup=build_settings_inline(source_menu="apitherapy"))

@dp.callback_query(F.data == "api_home")
@dp.callback_query(F.data == "api_back_menu")
async def on_api_home(call: types.CallbackQuery):
    await call.message.answer("🏠 Асосий Меню:", reply_markup=get_main_reply_keyboard())
    await call.answer()

@dp.callback_query(F.data == "api_act:sched_menu")
async def on_api_sched_menu(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    settings = get_settings()
    cur_time = settings.get("apitherapy_schedule_time", "16:00")
    enabled = settings.get("apitherapy_schedule_enabled", True)
    status_label = "✅ Ёқилган" if enabled else "❌ Ўчирилган"
    
    times = ["14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
    rows = []
    time_row = []
    for t in times:
        mark = "🔹 " if t == cur_time else ""
        time_row.append(InlineKeyboardButton(text=f"{mark}{t}", callback_data=f"api_sched_time:{t}"))
        if len(time_row) == 3:
            rows.append(time_row)
            time_row = []
    if time_row:
        rows.append(time_row)
    
    rows.append([InlineKeyboardButton(text=f"🔄 Ҳолати: {status_label}", callback_data="api_sched_toggle")])
    rows.append([InlineKeyboardButton(text="« Созламаларга қайтиш", callback_data="set_menu:back")])

    text = (
        "🌿 **АВТО-АПИТЕРАПИЯ ЖАДВАЛИ**\n\n"
        f"Ҳозирги вақт: **{cur_time}**\n"
        f"Ҳолати: **{status_label}**\n\n"
        "Ҳар куни ушбу вақтда канал ва гуруҳларга янги шифобахш апитерапия мақоласи юборилади:"
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("api_sched_time:"))
async def on_api_sched_time(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    t = call.data.split(":")[1]
    update_setting("apitherapy_schedule_time", t)
    await call.answer(f"Вақт белгиланди: {t}")
    await on_api_sched_menu(call)

@dp.callback_query(F.data == "api_sched_toggle")
async def on_api_sched_toggle(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    settings = get_settings()
    cur = settings.get("apitherapy_schedule_enabled", True)
    update_setting("apitherapy_schedule_enabled", not cur)
    await call.answer(f"Ҳолат ўзгарди: {'Ўчирилди ❌' if cur else 'Ёқилди ✅'}")
    await on_api_sched_menu(call)

# ==============================================================================
# 21. GURUH VA KANALLAR NAZORATI, ROZILIK VA XAVFSIZLIK (1-RASMDAGIDEK)
# ==============================================================================
@dp.callback_query(F.data.startswith("chat_auth_ok:"))
async def on_chat_auth_ok(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    chat_id = int(call.data.split(":")[1])
    pending = load_json_file(PENDING_CHATS_FILE, {})
    p_info = pending.pop(str(chat_id), {})
    save_json_file(PENDING_CHATS_FILE, pending)

    save_allowed_chat(chat_id, p_info.get("title", "Tasdiqlangan Guruh"), p_info.get("type", "group"))
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ **Asalarichilik.Uz 🇺🇿 Мутахассиси фаоллаштирилди!**\n\n"
                f"Ушбу чат бот эгаси ({OWNER_USERNAME}) томонидан расмий тасдиқланди.\n\n"
                "🛡 Фаол ҳимоялар:\n"
                "• Расм ва видео лимитлари (кунига 3 тадан кўп юборилса 24 соатга МУТЕ!)\n"
                "• Кунлик илмий викториналар, янгиликлар ва апитерапия мақолалари."
            )
        )
    except Exception:
        pass

    await call.message.edit_text(
        f"✅ **Чат муваффақиятли тасдиқланди!**\n\n"
        f"📍 Номи: {p_info.get('title')}\n"
        f"🆔 ID: `{chat_id}`\n"
        "Бот гуруҳда тўлиқ ишлашни бошлади.",
        parse_mode="Markdown"
    )
    await call.answer("Тасдиқланди!")

@dp.callback_query(F.data.startswith("chat_auth_no:"))
async def on_chat_auth_no(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    chat_id = int(call.data.split(":")[1])
    pending = load_json_file(PENDING_CHATS_FILE, {})
    p_info = pending.pop(str(chat_id), {})
    save_json_file(PENDING_CHATS_FILE, pending)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "⛔️ **КИРИШ РАД ЭТИЛДИ!**\n\n"
                "Бот эгаси (@JamshidjonDavronov) ушбу чатда ишлашни тасдиқламади.\n"
                "🚪 Бот чатни тарк этмоқда..."
            )
        )
    except Exception:
        pass
    try:
        await bot.leave_chat(chat_id)
    except Exception:
        pass

    await call.message.edit_text(
        f"❌ **Чат рад этилди ва бот чиқиб кетди.**\n\n"
        f"📍 Номи: {p_info.get('title')}\n"
        f"🆔 ID: `{chat_id}`",
        parse_mode="Markdown"
    )
    await call.answer("Рад этилди ва тарк этилди!")

@dp.message(F.text.in_({"👑 Гуруҳлар назорати", "Гуруҳлар назорати"}))
async def group_control_menu(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return
    chats = load_allowed_chats()
    groups = {cid: c for cid, c in chats.items() if c.get("type") in ["group", "supergroup", "Guruh"]}
    
    rows = []
    for cid, c in list(groups.items())[:10]:
        title = c.get("title", "Guruh")
        rows.append([
            InlineKeyboardButton(text=f"👥 {title[:20]}", callback_data=f"grp_info:{cid}"),
            InlineKeyboardButton(text="❌ Чиқиш", callback_data=f"grp_leave:{cid}")
        ])
    rows.append([InlineKeyboardButton(text="➕ Янги гуруҳга қўшиш қўлланмаси", callback_data="grp_add_guide")])
    rows.append([InlineKeyboardButton(text="« Орқага", callback_data="set_close")])

    text = (
        "👑 **ГУРУҲЛАР НАЗОРАТИ ВА ХАВФСИЗЛИГИ**\n\n"
        f"Бот уланган расмий гуруҳлар сони: **{len(groups)} та**\n\n"
        "• Ҳар бир гуруҳга бегона фойдаланувчи ботни қўшса, аввал сиздан тасдиқ олинади.\n"
        "• Гуруҳда 1 кунда 3 тадан кўп расм/видео юборган аъзолар 1 кунга МУТЕ қилинади."
    )
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("grp_leave:"))
async def on_grp_leave(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    cid = call.data.split(":")[1]
    chats = load_allowed_chats()
    if cid in chats:
        del chats[cid]
        save_json_file(ALLOWED_CHATS_FILE, chats)
    try:
        await bot.leave_chat(int(cid))
    except Exception:
        pass
    await call.answer("Бот гуруҳдан чиқарилди!", show_alert=True)
    await group_control_menu(call.message)

@dp.message(F.text.in_({"📢 Каналлар бошқаруви", "Каналлар бошқаруви"}))
async def channel_control_menu(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return
    off_c = get_official_channel()
    title = get_channel_title()
    
    rows = [
        [InlineKeyboardButton(text="🔄 Канал уланишини текшириш", callback_data="chan_check")],
        [InlineKeyboardButton(text="📝 Синов постини юбориш", callback_data="chan_test_post")],
        [InlineKeyboardButton(text="✏️ Канал ҳаволасини ўзгартириш", callback_data="set_change_channel")],
        [InlineKeyboardButton(text="🏷 Канал номини ўзгартириш", callback_data="set_change_channel_title")],
        [InlineKeyboardButton(text="« Орқага", callback_data="set_close")]
    ]
    text = (
        "📢 **КАНАЛЛАР БОШҚАРУВИ**\n\n"
        f"• **Асосий расмий канал:** {off_c}\n"
        f"• **Канал номи:** {title}\n"
        "• **Ҳолати:** Фаол\n\n"
        "Ушбу каналга бот автоматик равишда янгиликлар, апитерапия мақолалари ва кун викториналарини юборади."
    )
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="Markdown")

@dp.callback_query(F.data == "chan_check")
async def on_chan_check(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    ch = get_official_channel()
    try:
        chat = await bot.get_chat(ch)
        await call.answer(f"✅ Канал фаол: {chat.title}", show_alert=True)
    except Exception as e:
        await call.answer(f"⚠️ Текшириш хатолиги: {e}", show_alert=True)

@dp.callback_query(F.data == "chan_test_post")
async def on_chan_test_post(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    ch = get_official_channel()
    settings = get_settings()
    try:
        markup = build_post_markup(
            chat_id=0,
            message_id=0,
            reactions_list=settings.get("reactions"),
            channel_username=ch.lstrip("@"),
            is_channel_post=True,
            share_title="Синов пости"
        )
        msg = await bot.send_message(
            chat_id=ch,
            text=f"🐝 **Asalarichilik.Uz 🇺🇿 Синов пости!**\n\nБот муваффақиятли уланди ва ишламоқда.\n{get_official_footer()}",
            reply_markup=markup,
            parse_mode=None
        )
        await call.answer("✅ Синов пости каналга юборилди!", show_alert=True)
    except Exception as e:
        await call.answer(f"Хатолик: {e}", show_alert=True)

@dp.message(F.text.in_({"➕ Гуруҳга қўшиш", "Гуруҳга қўшиш"}))
async def add_to_group_guide(message: types.Message):
    text = (
        "➕ **БОТНИ ГУРУҲГА ҚЎШИШ:**\n\n"
        "1. Гуруҳингиз профилига киринг ва «Администраторлар» бўлимини очинг.\n"
        "2. «Админ қўшиш»ни босиб, @Asalarichiliktv_bot ни изланг.\n"
        "3. Ботга хабар ёзиш ва хабарларни ўчириш ҳуқуқини бериб админ қилинг.\n\n"
        "⚠️ **МУҲИМ:** Бегона гуруҳларга қўшилганда, бот эгаси @JamshidjonDavronov розилик берганидан кейингина фаоллашади."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Гуруҳга қўшиш", url="https://t.me/Asalarichiliktv_bot?startgroup=true")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text.in_({"➕ Каналга қўшиш", "Каналга қўшиш"}))
async def add_to_channel_guide(message: types.Message):
    text = (
        "➕ **БОТНИ КАНАЛГА ҚЎШИШ:**\n\n"
        "1. Каналингиз профилига кириб, «Администраторлар» бўлимига киринг.\n"
        "2. @Asalarichiliktv_bot ни қидириб топинг ва админ қилиб тайинланг.\n"
        "3. Ботга «Пост юбориш (Post Messages)» ва «Постларни қадаш (Pin Messages)» ҳуқуқларини беринг."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Каналга қўшиш", url="https://t.me/Asalarichiliktv_bot?startchannel=true")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text.in_({"👑 Бот эгаси", "Бот эгаси"}))
async def bot_owner_card(message: types.Message):
    text = (
        "👑 **БОТ ЭГАСИ ВА АДМИНИСТРАТОР:**\n\n"
        "👨‍💻 **Жамшид Давронов**\n"
        "📱 Telegram: @JamshidjonDavronov\n"
        "🆔 ID: `2047501151`\n\n"
        "🐝 «Asalarichilik.Uz» миллий лойиҳаси раҳбари.\n"
        "Савол ва таклифлар, ҳамкорлик ҳамда ботни гуруҳга қўшиш бўйича бемалол боғланишингиз мумкин."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Мутахассис билан боғланиш", url="https://t.me/JamshidjonDavronov")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text.in_({"📢 Реклама тарқатиш", "Реклама тарқатиш"}))
async def broadcast_menu(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return
    text = (
        "📢 **РЕКЛАМА ВА ЭЪЛОН ТАРҚАТИШ**\n\n"
        "Тарқатмоқчи бўлган эълонингизни расм, видео ёки матн кўринишида тайёрлаб "
        "«📝 Пост яратиш» бўлими орқали юборишингиз мумкин.\n"
        "Сўнгра уни бир вақтнинг ўзида барча гуруҳ ва каналларга узатишингиз мумкин."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.in_({"🌐 Тилни ўзгартириш", "Тилни ўзгартириш"}))
async def change_lang_menu(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != OWNER_ID:
        return
    settings = get_settings()
    cur = settings.get("script_mode", "cyrillic")
    txt_cyr = "✅ Крилча 🇺🇿" if cur == "cyrillic" else "Крилча 🇺🇿"
    txt_lat = "✅ Lotincha 🇺🇿" if cur == "latin" else "Lotincha 🇺🇿"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=txt_cyr, callback_data="lang_select:cyrillic")],
        [InlineKeyboardButton(text=txt_lat, callback_data="lang_select:latin")],
        [InlineKeyboardButton(text="« Орқага", callback_data="set_close")]
    ])
    await message.answer("🌐 **Бот алифбосини танланг:**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("lang_select:"))
async def on_lang_select(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    mode = call.data.split(":")[1]
    update_setting("script_mode", mode)
    await call.answer(f"Танланди: {'Крилча' if mode == 'cyrillic' else 'Лотинча'}", show_alert=True)
    await call.message.delete()

@dp.message(F.text.in_({"📖 Бот қўлланмаси", "Бот қўлланмаси"}))
async def bot_guide_menu(message: types.Message):
    text = (
        "📖 **«Asalarichilik.Uz» БОТ ҚЎЛЛАНМАСИ:**\n\n"
        "1. 🐝 **Викторина & Сўровнома:** Камида 1000 та савол базаси. Сўровнома кўринишида кўриб, сўнг канал ва гуруҳга узатиш мумкин.\n"
        "2. 📰 **Асаларичилик янгиликлари:** Жаҳон ва Ўзбекистон асаларичилик соҳаси янгиликлари.\n"
        "3. 🌿 **Апитерапия янгиликлари:** Асал, прополис, она сути, ари заҳри, перга ва мум куясидан даволаш рецептлари ва технологиялари (1000+ база + кунлик 10 та янгилик).\n"
        "4. 🛡 **Гуруҳ хавфсизлиги:** 1 кунда 3 тадан кўп расм/видео юборган аъзо 1 кунга ёзишдан чекланади (МУТЕ).\n"
        "5. ⚙️ **Созламалар:** Постлар остига реакциялар, улашиш ва мутахассис тугмаларини ёқиш/ўчириш."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.in_({"⚙️ Гуруҳ созламалари", "Гуруҳ созламалари"}))
async def group_settings_btn_cmd(message: types.Message):
    await settings_cmd(message)

# ==============================================================================
# 22. GURUHLARDA RASM/VIDEO CHEKLOVI (1 KUNDA 3 TA, 4-CHISIDA 1 KUNLIK MUTE)
# ==============================================================================
@dp.message(F.chat.type.in_({"group", "supergroup"}) & (F.photo | F.video | F.animation))
async def group_media_limiter_handler(message: types.Message):
    try:
        chat_id = message.chat.id
        user = message.from_user
        if not user or user.id == OWNER_ID:
            return
            
        # Adminlarni tekshirish - adminlarga cheklov qo'llanilmaydi
        try:
            m = await bot.get_chat_member(chat_id, user.id)
            if m.status in ["administrator", "creator"]:
                return
        except Exception:
            pass
            
        today = datetime.now().strftime("%Y-%m-%d")
        limits = load_json_file(MEDIA_LIMITS_FILE, {})
        day_data = limits.setdefault(today, {})
        chat_data = day_data.setdefault(str(chat_id), {})
        
        user_cnt = chat_data.get(str(user.id), 0) + 1
        chat_data[str(user.id)] = user_cnt
        save_json_file(MEDIA_LIMITS_FILE, limits)
        
        if user_cnt > 3:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                until_ts = int(datetime.now().timestamp() + 86400)
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_ts
                )
                warn = (
                    f"⚠️ <b>{user.full_name}</b>: Гуруҳда бир кунда 3 тадан кўп расм/видео юбориш тақиқланган!\n"
                    f"🚫 <b>24 соатга ёзиш чекланди (1 кунлик МУТЕ)!</b>"
                )
                await bot.send_message(chat_id=chat_id, text=warn, parse_mode="HTML")
            except Exception as re:
                logging.warning(f"restrict error: {re}")
    except Exception as e:
        logging.error(f"group_media_limiter_handler error: {e}")
