import asyncio
import sys

async def run_script(script_name):
    # Ҳар бир ботни алоҳида жараён сифатида параллел ишга туширамиз
    process = await asyncio.create_subprocess_exec(sys.executable, script_name)
    await process.wait()

async def main():
    # bot.py ва bee_bot.py ни бир вақтда узлуксиз юритамиз
    await asyncio.gather(
        run_script("bot.py"),
        run_script("bee_bot.py")
    )

if __name__ == "__main__":
    asyncio.run(main())

