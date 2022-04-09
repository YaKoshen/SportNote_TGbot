import json
from dataclasses import dataclass, field, asdict
import os

from app.config import Config


@dataclass
class User:
    tg_id: int = field()
    first_name: str = field()
    last_name: str = field()
    username: str = field()
    current_chat_id: int = field()
    receiving_updates: bool = field(default=False)

    @property
    def filename(self):
        return os.path.join(Config.USERS_STORAGE_DIRECTORY, f"{self.tg_id}.json")

    @property
    def exist(self):
        return os.path.exists(self.filename)

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=4)

    def delete(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def update(self):
        with open(self.filename, "w") as f:
            f.write("")
            json.dump(asdict(self), f, ensure_ascii=False, indent=4)

    @classmethod
    def load(cls, file):
        return cls(**json.load(file))

    def __eq__(self, other):
        if self.tg_id == other.tg_id:
            return True

        return False
