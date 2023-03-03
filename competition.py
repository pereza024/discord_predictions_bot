import secrets, bson

import language
from database import Database
from setting import logger

import discord

from pymongo.collection import Collection

class Competition_Reason():
    def __init__(self, title: str):
        self.title: str = title
        self.amount: int = 0
        self.users = []

class Competition():
    def __create_id__(self) -> int:
        """Used for the purpose of creating a random ID for the competitions to be stored into the DB"""        
        return int.from_bytes(secrets.token_bytes(6), byteorder='big')

    def __init__(self, title: str, believe_reason: str, doubt_reason: str, guild: discord.Guild, is_anonymous: bool, bet_minimum: int):
        self.title: str = title # Title of the Competiton
        self.id: int = self.__create_id__() # ID of the competition
        self.guild: discord.Guild = guild # Associated Discord server calling for the competition
        self.timer: int = -1
        self.end_time: int = -1
        self.believe: Competition_Reason = Competition_Reason(believe_reason)
        self.doubt: Competition_Reason = Competition_Reason(doubt_reason)
        self.is_anonymous: bool = is_anonymous
        self.bet_minimum: int = bet_minimum

    def format_time(self, minutes: int, seconds: int):
        return '{:02d}:{:02d}'.format(minutes, seconds)

    def create_user_history_record(self, user: discord.User | discord.Member, amount: int = 0):
        return {
            "id" : user.id,
            "amount" : amount
        }

    def set_points_winnings(self, betting_collection: Collection, user_points_collection: Collection, competition_history_collection: Collection, winning_group: int):
        user_believers, user_doubter = self.believe.users, self.doubt.users
        amount = 0

        if winning_group == language.end_text_reasons.BELIEVERS:
            for user in user_believers:
                discord_member = self.guild.get_member(user["_id"])

                user_points_data = user_points_collection.find_one({"_id" : user["_id"]})
                user_winning_data = user_points_data["wins"]
                user_betting_data = betting_collection.find_one({"_id" : user["_id"]})

                user_winning_ratio = user_betting_data["points"] / self.believe.amount
                amount = round(user_winning_ratio * self.doubt.amount + user_betting_data['points'])
                
                logger.info(f"User: {discord_member.display_name or discord_member.name} (ID: {discord_member.id}) \n Has won {amount}\n Prediction: {self.title}")

                # TODO: Include logic for new winning history
                user_winning_data["number_of"] += 1

                user_points_collection.update_one({"_id" : user_points_data["_id"]}, {"$set" : {
                    "points" : user_points_data["points"] + amount,
                    "wins" : user_winning_data
                }})
                
        elif winning_group == 2:
            for user in user_doubter:
                discord_member = self.guild.get_member(user["_id"])

                user_points_data = user_points_collection.find_one({"_id" : user["_id"]})
                user_winning_data = user_points_data["wins"]
                user_betting_data = betting_collection.find_one({"_id" : user["_id"]})

                user_winning_ratio = user_betting_data["points"] / self.doubt.amount
                amount = round(user_winning_ratio * self.believe.amount + user_betting_data['points'])

                logger.info(f"User: {discord_member.display_name or discord_member.name} (ID: {discord_member.id}) \n Has won {amount}\n Prediction: {self.title}")

                # TODO: Include logic for new winning history
                user_winning_data["number_of"] += 1

                user_points_collection.update_one({"_id" : user_points_data["_id"]}, {"$set" : {
                    "points" : user_points_data["points"] + amount,
                    "wins" : user_winning_data
                }})
        
        competition_history_collection.update_one({"_id" : self.id}, {"$set" : {"is_active" : False}})
        
        self.clear_betting_records(betting_collection)

    def clear_betting_records(self, collection: Collection):
        collection.delete_many({})