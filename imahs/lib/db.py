import json 
import datetime
import logging
from contextlib import ContextDecorator
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.dialects.mysql import insert, LONGTEXT
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine




class MYSQL(ContextDecorator):
    def insert(self, table_name):
        return insert(table_name)
    def __init__(self, host, port, username, password, database):
        super().__init__()
        self.url = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
    async def __aenter__(self):
        self.engine = create_async_engine(
            url=self.url
        )
        self.session = AsyncSession(self.engine)
        return self
    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.session:
            try:
                if exc_type is None:
                    await self.session.commit()  
                else:
                    await self.session.rollback() 
            finally:
                await self.session.close() 
    def __enter__(self):
        self.engine = create_engine(
            url=self.url
        )
        self.session = Session(self.engine)
        return self
    def __exit__(self, *exc):
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logging.error(f"LINO {e.__traceback__.tb_lineno} - Error: {e}")
            raise
        finally:
            self.session.close()
        return False

BaseTableMYSQL  = declarative_base()

class ChatsTable(BaseTableMYSQL):
    __tablename__ = 'chats'
    msgid     = Column(String(512),          nullable=False, primary_key=True)
    chatid    = Column(String(512),          nullable=False)
    timestamp = Column(DateTime,        nullable=False)
    username  = Column(String(64),          nullable=False)
    author    = Column(String(64),          nullable=False)
    text      = Column(LONGTEXT,          nullable=False)
    checksum  = Column(String(512),          nullable=False)
    source    = Column(Text,          nullable=False)
    otherid   = Column(String(512),          nullable=False)
    def __init__(self, msgid, chatid, timestamp, username, author, text, checksum, source, otherid):
        self.msgid     = msgid
        self.chatid    = chatid
        self.timestamp = timestamp
        self.username  = username
        self.author    = author
        self.text      = text
        self.checksum  = checksum
        self.source    = source
        self.otherid   = otherid
    @staticmethod
    def columns():
        return[c.name for c in ChatsTable.__dict__.get('__table__', None).columns]
    @property
    def json(self):
        res = {}
        for c in self.__table__.columns:
            res[c.name] = getattr(self, c.name)
            if res[c.name] is None:
                res[c.name] = ""
            if isinstance(res[c.name], datetime.datetime):
                res[c.name] = res[c.name].strftime("%d-%m-%y %H:%M:%S")
            res[c.name] = str(res[c.name])
        return res
    def __str__(self):
        return json.dumps(self.json, indent=4)
