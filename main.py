import asyncio
import sys
from flask import Flask
from threading import Thread

# Flask орқали содда веб-сервер яратамиз (UptimeRobot пинг бериши учун)
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running!"

def run_web():
    # Render берган портга мослашиши ёки 8080 портда ишлаши учун
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

async def run_script(script_name):
    # Ҳар бир ботни алоҳида жараён сифатида параллел ишга туширамиз
    process = await asyncio.create_subprocess_exec(sys.executable, script_name)
    await process.wait()

async def main():
    # Веб-серверни орқа фон портда ёқиб юборамиз
    keep_alive()
    
    # bot.py ва bee_bot.py ни бир вақтда узлуксиз юритамиз
    await asyncio.gather(
        run_script("bot.py"),
        run_script("bee_bot.py")
    )

if __name__ == "__main__":
    asyncio.run(main())


