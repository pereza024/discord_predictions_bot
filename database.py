from enum import Enum

from setting import logger

import discord

from pymongo import (MongoClient, database)

class Database():
    __DEFAULT_USER_POINTS__ : int = 1000

    def __init__(self, cluster_link: str, database_name: str):
        self.database: database = MongoClient(cluster_link).get_database(database_name)

    class collection_name_types(Enum):
        MEMBER_POINTS = 1
        BETTING_POOL = 0
    
    def __get_collection_name(self, guild: discord.Guild, type: collection_name_types):
        if type == self.collection_name_types.BETTING_POOL:
            return f'{guild} Betting Pool'
        elif type == self.collection_name_types.MEMBER_POINTS:
            return f"{guild} Member Points"
        else:
            # TODO: Error catching
            pass

    def get_guild_points_collection(self, guild: discord.Guild):
        collection_name = self.__get_collection_name(guild, self.collection_name_types.MEMBER_POINTS)
        if collection_name in self.database.list_collection_names():
            return self.database[collection_name]
        pass

    def get_guild_betting_pool_collection(self, guild: discord.Guild):
        collection_name = self.__get_collection_name(guild, self.collection_name_types.BETTING_POOL)
        if collection_name in self.database.list_collection_names():
            return self.database[collection_name]
        pass

    def insert_betting_record(self, interaction: discord.Interaction, is_doubter: bool, amount: int):
        collection = self.get_guild_betting_pool_collection(interaction.guild)

        data = collection.find_one({"_id": interaction.user.id})
        if not data:
            collection.insert_one({"_id": interaction.user.id, "name": interaction.user.display_name or interaction.user.name, "points": amount, "is_doubter": is_doubter})
        else:
            value = data["points"] + amount
            collection.replace_one({"_id": interaction.user.id}, {"name" : data['name'], "points": value, "is_doubter": is_doubter }, True)

    # Registering all Discord servers the bot belongs to.
    def register_guilds(self, guilds: list[discord.Guild]):
        collections = self.database.list_collection_names()

        for guild in guilds:
            member_points_collection_name = self.__get_collection_name(guild, self.collection_name_types.MEMBER_POINTS)
            betting_pool_collection_name = self.__get_collection_name(guild, self.collection_name_types.BETTING_POOL)
            if member_points_collection_name not in collections:
                logger.info(f"Adding {guild.name} Discord Server into the DB")
                self.database.create_collection(member_points_collection_name)
                self.database.create_collection(betting_pool_collection_name)
                
                collection = self.get_guild_points_collection(guild)
                for member in guild.members:
                    collection.insert_one({"_id" : member.id, "name" : member.display_name or member.name, "points" : self.__DEFAULT_USER_POINTS__})
                logger.info(f"Finished adding {guild.member_count} users from {guild.name} Discord Server into the {member_points_collection_name}")
            else:
                pass