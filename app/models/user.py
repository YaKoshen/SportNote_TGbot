from app.models import db


class UserModel(db.Model):
    __tablename__ = "users"

    tg_id = db.Column(db.Integer(), primary_key=True, nullable=False)
    first_name = db.Column(db.String())
    last_name = db.Column(db.String())
    username = db.Column(db.String())
    current_chat_id = db.Column(db.Integer(), nullable=False)
    receiving_updates = db.Column(db.Boolean(), nullable=False, default=False)

    def __eq__(self, other) -> bool:
        if self.tg_id == other.tg_id:
            return True

        return False

    def __repr__(self):
        return f"<{self.__class__.__name__} (" \
               f"tg_id={self.tg_id}, " \
               f"first_name={self.first_name}, " \
               f"last_name={self.last_name}, " \
               f"username={self.username})>"
