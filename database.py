import sqlite3
import os
from functools import wraps
import logging

import numpy as np

from constants import DIRECTORY


class _DBDecorators:
    # * Private class incluing all database decorators

    @classmethod
    def separator(cls, func):
        # * Create some separation during the steps of the database checking.
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info("{:-^30}".format(""))
            func(*args, **kwargs)
            logging.info("{:-^30}".format(""))
        return wrapper

    @classmethod
    def check_db_exist(cls, func):
        # * Check the integrity of the database
        # * If the database dont exist, creates a new one
        # * Rows are empty
        @wraps(func)
        def wrapper(*args, **kwargs):
            # * The first element of the arg variable is the instance of DBManager
            # * The kwargs variable contain db cursor in the 'cursor' key
            
            logging.info("[DB] Connection...")
            if kwargs["cursor"].execute("SELECT name FROM sqlite_master WHERE type='table';").fetchone(): # ? Check if the database is not empty
                logging.info("[DB] Database found!")
            else:
                logging.warning("[DB] Database not found...")
                logging.info("[DB] Creation of a new database, it will not be long.")
                DBInstance = args[0] # * Assign the DBManager instance in a variable to easily access to it
                DBInstance._create_guild_table
                DBInstance._create_member_table
                DBInstance._create_emote_table
            func(*args, **kwargs)
            logging.info("[DB] Ready!")
        return wrapper
    
    @classmethod
    def auto_commit(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            DBInstance = args[0]
            DBInstance.connexion.commit()
        return wrapper
    

class DBSingletonMeta(type):
    # *  Metaclass Singleton to have a single database connection
    _instance = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            instance = super().__call__(*args, **kwargs)
            cls._instance[cls] = instance
        return cls._instance[cls]
        
class DBManager(metaclass=DBSingletonMeta):
    # * Represents the whole class which control the cat database.
    # * The class is a Singleton, each instance return the same class instance.
    
    DB = sqlite3.connect(os.path.join(DIRECTORY, "database.db")) # ? Connection to the cat sqlite3 DB
    
    def __init__(self):
        self._connexion = self.DB
        self._cursor = self.connexion.cursor()   
        self.on_db_launch(cursor=self._cursor)            
        
    @property
    def connexion(self):
        return self._connexion
    
    @connexion.setter
    def connexion(self, *args, **kwargs):
        raise AttributeError # ! Avoid user manually create a connection
    
    @property
    def cursor(self):
        return self._cursor
    
    @cursor.setter
    def cursor(self, *args, **kwargs):
        raise AttributeError  # ! Avoid user manually create a cursor
    
    
    @_DBDecorators.separator
    @_DBDecorators.check_db_exist
    @_DBDecorators.auto_commit
    def on_db_launch(self, cursor):
        logging.info("[DB] Initialization...")
        self.cursor.execute("PRAGMA foreign_keys = ON")
    
    @property 
    @_DBDecorators.auto_commit
    def _create_guild_table(self) -> None:
        self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS guilds(
                    guild_id INTEGER PRIMARY KEY NOT NULL
                    );
                    """)
        logging.info("[DB] Guild table successfully created!")
        
    @property
    @_DBDecorators.auto_commit
    def _create_member_table(self) -> None:
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS members(
                            key INTEGER PRIMARY KEY AUTOINCREMENT, 
                            member_id INTEGER NOT NULL, 
                            guild_id INTEGER NOT NULL,
                            total_emote INTEGER NOT NULL DEFAULT 0,
                            user_emote TEXT NOT NULL DEFAULT ';',
                            FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                        );
                        """) 
        logging.info("[DB] Member table successfully created!")
        
    @property
    @_DBDecorators.auto_commit
    def _create_emote_table(self) -> None:
        self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS emotes(
                        emote_id INTEGER PRIMARY KEY, 
                        guild_id INTEGER NOT NULL, 
                        global_use INTEGER NOT NULL DEFAULT 0, 
                        FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
                    );
                    """)
        logging.info("[DB] Emote table successfully created!")

    @_DBDecorators.auto_commit
    def add_new_guild(self, guild_id: int) -> None:
        self.cursor.execute("""
        INSERT INTO guilds(guild_id) 
        SELECT ?
        WHERE NOT EXISTS(SELECT 1 FROM guilds WHERE guild_id = ?
        );    
        """, (guild_id,)*2)

    @_DBDecorators.auto_commit
    def remove_existing_guild(self, guild_id: int) -> None:
        self.cursor.execute("""
        DELETE FROM guilds
        WHERE guild_id = ?
        """, (guild_id,))

    @_DBDecorators.auto_commit
    def add_new_member(self, guild_id: int, member_id: int) -> None:
        self.cursor.execute("""
        INSERT INTO members(member_id, guild_id) 
        SELECT ?, ?
        WHERE NOT EXISTS(SELECT 1 FROM members WHERE member_id = ? AND guild_id = ?
        );    
        """, (member_id, guild_id)*2)

    @_DBDecorators.auto_commit
    def remove_existing_member(self, guild_id: int, member_id: int) -> None:
        self.cursor.execute("""
        DELETE FROM members
        WHERE guild_id = ? AND member_id = ?
        """, (guild_id, member_id))

    @_DBDecorators.auto_commit
    def add_new_emoji(self, guild_id: int, emote_id: int) -> None:
        self.cursor.execute("""
        INSERT INTO emotes(emote_id, guild_id) 
        SELECT ?, ?
        WHERE NOT EXISTS(SELECT 1 FROM emotes WHERE emote_id = ? AND guild_id = ?
        );    
        """, (emote_id, guild_id)*2)

    @_DBDecorators.auto_commit
    def remove_existing_emoji(self, guild_id: int, emote_id: int) -> None:
        self.cursor.execute("""
        DELETE FROM emotes
        WHERE guild_id = ? AND emote_id = ?
        """, (guild_id, emote_id))
       
    @staticmethod
    def __reformat_db_emote(emoji_id: int, emotes: str, number: int, add=True) -> str:

        format_list = [object_.split(":") for object_ in emotes.split(';') if object_]

        if add:
            new_object = [i if int(i[0]) != emoji_id else
                          [i[0], str(int(i[1]) + number)]
                          for i in format_list]
            
            if format_list == new_object:
                new_object.extend([[f"{emoji_id}", f"{number}"]])

        else:
            new_object = filter(lambda x: int(x[0]) != emoji_id,  format_list)

        return ";".join(":".join(i) for i in new_object) + ";"

    def used_member_emoji(self, member_id: int, guild_id: int) -> str:
        self.cursor.execute("""
        SELECT user_emote
        FROM members
        INNER JOIN guilds
        ON members.guild_id = guilds.guild_id
        WHERE members.member_id = ? AND guilds.guild_id = ?
        ;
        """, (member_id, guild_id))

        return self.cursor.fetchone()[0]

    @_DBDecorators.auto_commit
    def _update_member_emoji(self, new_emoji: str, member_id: int, guild_id: int) -> None:
        self.cursor.execute("""
        UPDATE members
        SET user_emote = ?
        WHERE member_id = ? AND guild_id = ?
        """, (new_emoji, member_id, guild_id))

    def remove_emoji_member(self, member_id: int, guild_id: int, emoji_id: int, number = 1) -> None:
        user_emotes = self.used_member_emoji(member_id, guild_id)
        new_user_emotes = self.__reformat_db_emote(emoji_id, user_emotes, number, add=False)
        if user_emotes == new_user_emotes:
            return
        self._update_member_emoji(new_user_emotes, member_id, guild_id)

    def get_guild_emoji(self, guild_id):
        self.cursor.execute("""
        SELECT emote_id, global_use
        FROM emotes
        INNER JOIN guilds
        ON guilds.guild_id = emotes.guild_id
        WHERE guilds.guild_id = ?
        """, (guild_id,))

        return self.cursor.fetchall()

    def add_emoji_member(self, member_id: int, guild_id: int, emoji_id: int, number = 1) -> None:
        user_emotes = self.used_member_emoji(member_id, guild_id)
        new_user_emotes = self.__reformat_db_emote(emoji_id, user_emotes, number, add=True)

        self._update_member_emoji(new_user_emotes, member_id, guild_id)

    def get_emoji_member(self, member_id: int, guild_id: int) -> None:
        user_emotes = self.used_member_emoji(member_id, guild_id)
        return [emote.split(":") for emote in user_emotes.split(';') if emote]

    @_DBDecorators.auto_commit
    def add_global_emoji_use(self, guild_id: int, emoji_id: int, number=1):
        self.cursor.execute("""
        UPDATE emotes
        SET global_use = ? + (
        SELECT global_use
        FROM emotes
        INNER JOIN guilds
        ON guilds.guild_id = emotes.guild_id
        WHERE guilds.guild_id = ? and emotes.emote_id = ?
        )
        WHERE guild_id = ? and emote_id = ?
        ;
        """, (number, guild_id, emoji_id, guild_id, emoji_id))

if __name__ == "__main__":
    
    s1 = DBManager()
    s2 = DBManager()
    print(id(s1), id(s2))
