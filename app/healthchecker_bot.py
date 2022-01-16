import asyncio
import os
import json

import aiohttp

from app.config import Config


class HealthcheckerBot:
    def __init__(self):
        self.last_update_id = None
        self.chats_ids = []

    async def start(self):
        # получаем id последнего обновления из файла
        if not os.path.exists(Config.CURRENT_UPDATE_ID_FILE_NAME):
            with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "w") as f:
                f.write(str(0))

        with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "r") as f:
            self.last_update_id = int(f.read().strip())

        # получаем список всех чатов, куда нам надо отправлять оповещения
        if not os.path.exists(Config.CHATS_LIST_FILE_NAME):
            open(Config.CHATS_LIST_FILE_NAME, "a").close()

        with open(Config.CHATS_LIST_FILE_NAME, "r") as f:
            for chat_id in f.readlines():
                self.chats_ids.append(int(chat_id.strip()))
        print(self.chats_ids)

    async def actualize_last_update_id(self, update_id: int):
        self.last_update_id = update_id

        with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "w") as f:
            f.write(str(update_id))

    async def add_notification_chat(self, chat_id):
        self.chats_ids.append(chat_id)

        with open(Config.CHATS_LIST_FILE_NAME, "a") as f:
            f.write(f"{chat_id}\n")

    async def answer(self, update):
        received_msg = update["message"]
        chat_id = received_msg["chat"]["id"]

        if chat_id not in self.chats_ids:
            await self.add_notification_chat(chat_id)
            resp_text = "Chat id added. You will receive sportnote down reports forever"
        else:
            resp_text = "You are already receiving sportnote down reports"

        msg = json.dumps({"chat_id": chat_id, "text": resp_text})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                    data=msg,
                    headers={"Content-Type": "application/json"}
            ) as resp:
                return resp

    async def get_updates(self):
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getUpdates?offset={self.last_update_id + 1}"
                ) as resp:
                    resp_json = await resp.json()
                    if resp_json["ok"]:
                        updates = resp_json["result"]
                        if updates:
                            await self.actualize_last_update_id(updates[-1]["update_id"])

                            answers = [asyncio.create_task(self.answer(update)) for update in updates]
                            results = await asyncio.gather(*answers)
                            print(results)
                            await asyncio.sleep(3)
                    else:
                        print(f"Not ok response: {resp}")
                        await asyncio.sleep(3)
                        continue

    @staticmethod
    async def website_down():
        """Если с сайтом все ок, ничего не возвращает. Если бот не смог достучаться, возвращает описание проблемы"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(Config.WEBSITE_URL) as resp:
                    if resp.status in [200, 202]:
                        return
                    else:
                        return f"Wrong status code: {resp.status}"
            except aiohttp.client_exceptions.ClientConnectorError as e:
                return str(e)

    async def monitor_website(self):
        while True:
            problem = await self.website_down()
            if problem:
                async with aiohttp.ClientSession() as session:
                    for chat_id in self.chats_ids:
                        async with session.post(
                            f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                            data=json.dumps({"chat_id": chat_id, "text": problem}),
                            headers={"Content-Type": "application/json"}
                        ) as resp:
                            print(resp)
            else:
                print(f"No problems with {Config.WEBSITE_URL}")

                """
                reports_params = [json.dumps({"chat_id": chat_id, "text": problem}) for chat_id in self.chats_ids]
                async with aiohttp.ClientSession() as session:
                    reports = [
                        asyncio.create_task(
                            session.post(
                                f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                                data=report_param,
                                headers={"Content-Type": "application/json"}
                            )
                        ) for report_param in reports_params
                    ]
                    results = await asyncio.gather(*reports)
                """

            await asyncio.sleep(Config.PING_FREQUENCY)
