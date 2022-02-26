import asyncio
import os
import json

import aiohttp

from app.config import Config
from app.monitoring_resource import MonitoringResource
from app.utils import get_logger


class HealthcheckerBot:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.last_update_id = None
        self.chats_ids = []
        self.monitoring_resource = MonitoringResource(name=Config.RESOURCE_NAME, url=Config.WEBSITE_URL)
        self.session = None

        self.__is_running = False  # работает ли бот в целом
        self.__is_receiving_updates = False  # получаем ли апдейты от тг
        self.__is_monitoring = False  # посылает ли он запросы на сайт без исключений

    async def start(self):
        self.logger.info("Starting...")

        # получаем id последнего обновления из файла
        self.logger.debug("Getting last update id from file: %s", Config.CURRENT_UPDATE_ID_FILE_NAME)

        if not os.path.exists(Config.CURRENT_UPDATE_ID_FILE_NAME):
            with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "w") as f:
                f.write(str(0))

        with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "r") as f:
            self.last_update_id = int(f.read().strip())

        self.logger.debug("Last update id got: %s", self.last_update_id)

        # получаем список всех чатов, куда нам надо отправлять оповещения
        self.logger.debug("Getting chats ids we send messages to")

        if not os.path.exists(Config.CHATS_LIST_FILE_NAME):
            open(Config.CHATS_LIST_FILE_NAME, "a").close()

        with open(Config.CHATS_LIST_FILE_NAME, "r") as f:
            for chat_id in f.readlines():
                self.chats_ids.append(int(chat_id.strip()))

        self.logger.debug("Chats to send: %s", self.chats_ids)

        self.session = aiohttp.ClientSession()
        self.logger.debug("Session created")

        self.logger.info("Healthchecker bot started for %s", self.monitoring_resource.name)

    async def _actualize_last_update_id(self, update_id: int):
        self.last_update_id = update_id

        with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "w") as f:
            f.write(str(update_id))

    async def _add_notification_chat(self, chat_id):
        self.chats_ids.append(chat_id)

        with open(Config.CHATS_LIST_FILE_NAME, "a") as f:
            f.write(f"{chat_id}\n")

    async def _delete_notification_chat(self, chat_id):
        if chat_id in self.chats_ids:
            self.chats_ids.remove(chat_id)
        else:
            self.logger.warning("Removing not existing chat id: %s", chat_id)

        with open(Config.CHATS_LIST_FILE_NAME, "w") as f:
            f.write("\n".join([str(_id) for _id in self.chats_ids]))

    async def answer(self, update):
        try:
            received_msg = update["message"]
            chat_id = received_msg["chat"]["id"]

        except KeyError as e:
            self.logger.warning(f"Update {str(e)}: {update}", exc_info=True)
            return None

        resp_text = None

        if received_msg["text"].strip() == "/start" and chat_id not in self.chats_ids:
            await self._add_notification_chat(chat_id)
            resp_text = "You have started to receive SportNote state notifications"

        if received_msg["text"].strip() == "/status":
            resp_text = f"Requested status:\n{self.monitoring_resource.create_current_state_report()}"

        if received_msg["text"].strip() == "/stop":
            resp_text = "You will no longer receive SportNote state notifications"
            await self._delete_notification_chat(chat_id)

        if resp_text:
            msg = json.dumps({"chat_id": chat_id, "text": resp_text})

            async with self.session.post(
                    f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                    data=msg,
                    headers={"Content-Type": "application/json"}
            ) as resp:
                return resp

        return None

    async def receive_updates(self):
        self.__is_receiving_updates = True

        self.logger.info("Started to recieve tg updates")

        while True:
            async with self.session.get(
                f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getUpdates?offset={self.last_update_id + 1}"
            ) as resp:
                resp_json = await resp.json()

                if resp_json["ok"]:
                    updates = resp_json["result"]

                    if updates:
                        await self._actualize_last_update_id(updates[-1]["update_id"])

                        # отвечаем на сообщения
                        answers = [asyncio.create_task(self.answer(update)) for update in updates]
                        results = await asyncio.gather(*answers)

                        await asyncio.sleep(Config.UPDATES_RECEIVE_FREQUENCY)
                else:
                    self.logger.warning("Not ok response: %s", resp)

                    await asyncio.sleep(Config.UPDATES_RECEIVE_FREQUENCY)

                    continue

    async def monitor_website(self):
        self.logger.info("Started to monitor %s", self.monitoring_resource.url)

        while True:
            try:
                self.logger.debug("Sending request to %s", self.monitoring_resource.url)

                async with self.session.get(self.monitoring_resource.url) as resp:
                    self.monitoring_resource.update_status_code(resp.status)

                    self.logger.debug(
                        "Status code for %s: %s",
                        self.monitoring_resource.url,
                        self.monitoring_resource.current_status_code
                    )

                    if not self.__is_monitoring:
                        self.__is_monitoring = True

            except aiohttp.client_exceptions.ClientConnectorError as e:
                self.logger.error(str(e), exc_info=True)
                self.__is_monitoring = False

            else:
                await asyncio.sleep(Config.PING_FREQUENCY)

    async def send_notifications(self):
        while True:
            if self.__is_monitoring and self.__is_receiving_updates:
                self.logger.info("Started to send notifications to %s", self.chats_ids)
                for chat_id in self.chats_ids:
                    
                    async with self.session.post(
                        f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                        data=json.dumps(
                            {
                                "chat_id": chat_id,
                                "text": self.monitoring_resource.create_current_state_report()
                            }
                        ),
                        headers={"Content-Type": "application/json"}
                    ) as resp:
                        self.logger.debug(resp)

            await asyncio.sleep(20)
