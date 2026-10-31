# -*- coding: utf-8 -*-
"""
Asalarichilik.Uz - Ikkala botni bir vaqtda Render serverida yurgizuvchi boshqaruvchi (Runner)
1-bot: bee_bot.py (Asalarichilikuz_bot - aiogram + Ilmiy testlar + Render Web Healthcheck)
2-bot: bot.py (Ikkinchi bot - telebot)
"""
import subprocess
import sys
import time
import os
import signal

print("=" * 60, flush=True)
print("🚀 Asalarichilik serveri: Ikkala bot birga ishga tushirilmoqda...", flush=True)
print("=" * 60, flush=True)

processes = []

def start_bee_bot():
    if os.path.exists("bee_bot.py"):
        print("▶️ [1-BOT] bee_bot.py ishga tushirilmoqda...", flush=True)
        return subprocess.Popen([sys.executable, "bee_bot.py"])
    return None

def start_second_bot():
    if os.path.exists("bot.py"):
        print("▶️ [2-BOT] bot.py (ikkinchi bot) ishga tushirilmoqda...", flush=True)
        return subprocess.Popen([sys.executable, "bot.py"])
    return None

p_bee = start_bee_bot()
p_sec = start_second_bot()

def cleanup(signum, frame):
    print("\n🛑 Botlar to'xtatilmoqda...", flush=True)
    if p_bee and p_bee.poll() is None:
        p_bee.terminate()
    if p_sec and p_sec.poll() is None:
        p_sec.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

try:
    while True:
        time.sleep(10)
        # 1-bot tekshiruvi
        if p_bee and p_bee.poll() is not None:
            print("⚠️ [1-BOT] bee_bot.py to'xtab qoldi, qayta yuklanmoqda...", flush=True)
            p_bee = start_bee_bot()
        # 2-bot tekshiruvi
        if p_sec and p_sec.poll() is not None:
            print("⚠️ [2-BOT] bot.py to'xtab qoldi, qayta yuklanmoqda...", flush=True)
            p_sec = start_second_bot()
except Exception as e:
    print(f"Xatolik: {e}", flush=True)
    cleanup(None, None)
