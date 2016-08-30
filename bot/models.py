import os

import peewee

import config

db = peewee.SqliteDatabase(None)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Session(BaseModel):
    chat_id = peewee.IntegerField(primary_key=True)
    trello_token = peewee.CharField(null=True)


db.init(config.DB_FILE)

if not os.path.isfile(config.DB_FILE):
    db.create_tables([Session])
