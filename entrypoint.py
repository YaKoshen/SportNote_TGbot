import asyncio

from app import HealthcheckerBot


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = HealthcheckerBot()

    try:
        loop.run_until_complete(bot.start())

        loop.run_forever()

    except KeyboardInterrupt:
        print("Keyboard interrupted")
        loop.run_until_complete(bot.shutdown())
