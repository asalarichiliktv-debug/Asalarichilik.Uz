import asyncio
from bot import dp as bot1_dp, bot as bot1
from bee_bot import dp as bee_dp, bot as bee_bot

async def main():
    # Иккала ботни бир вақтда параллел ишга тушириш
    await asyncio.gather(
        bot1_dp.start_polling(bot1),
        bee_dp.start_polling(bee_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
