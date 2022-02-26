import asyncio

from app import HealthcheckerBot


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bot = HealthcheckerBot()

    try:
        loop.run_until_complete(bot.start())

        asyncio.ensure_future(bot.receive_updates())
        asyncio.ensure_future(bot.monitor_website())
        asyncio.ensure_future(bot.send_notifications())

        loop.run_forever()

    except KeyboardInterrupt:
        print("Stopped")
