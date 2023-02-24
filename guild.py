from competition import Competition

import discord

import pymongo
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

__user_points__ = "'User Points"
__competition_history__ = "Competitions"

class Guild():
    def __fetch_collection__(self, collection_type: str, database_client: pymongo.MongoClient) -> Collection:
        database: Database = database_client.get_database(self.discord_reference)
        if not database:
            database = database_client[self.discord_reference]
        return database.create_collection(collection_type)
    
    def __init__(self, discord_instance: discord.Guild, database_client: pymongo.MongoClient):
        self.discord_reference = discord_instance
        self.user_points_collection: Collection = self.__fetch_collection__(__competition_history__, database_client)
        self.competition_history_collection: Collection = self.__fetch_collection__(__competition_history__, database_client)
        self.active_competition: Competition = None