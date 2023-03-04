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

    def create_user_history_record(self, user: discord.User, amount: int = 0):
        return {
            "id" : user.id,
            "amount" : amount
        }
    def refund_points(self, betting_collection: Collection, user_points_collection: Collection):
        betting_records = betting_collection.find()
        for betting_record in betting_records:
            user_points_record = user_points_collection.find_one({"_id" : betting_record["_id"]})
            logger.info(f"Refunding User: {user_points_record['name']} (ID: {user_points_record['_id']}) for {betting_record['bet_amount']}")
            user_points_collection.update_one({"_id" : betting_record["_id"]}, {"$set" : {
                "points": user_points_record["points"] + betting_record["bet_amount"]
            }})
        
        self.clear_betting_records(betting_collection)


    def set_points_winnings(self, guild: discord.Guild, betting_collection: Collection, user_points_collection: Collection, winning_group: int):
        betting_records = betting_collection.find({})
        amount = 0

        if winning_group == language.end_text_reasons.BELIEVERS.value:
            for betting_record in betting_records:
                if betting_record["betting_side"] == language.end_text_reasons.DOUBTERS.value:
                    break
                discord_member = guild.get_member(betting_record["_id"])
                user_points_record = user_points_collection.find_one({"_id" : betting_record["_id"]})

                user_winning_ratio = betting_record["bet_amount"] / self.believe.amount
                amount = round(user_winning_ratio * self.doubt.amount + betting_record["bet_amount"])
                logger.info(f"User: {discord_member.display_name or discord_member.name} (ID: {discord_member.id}) \n Has won {amount}\n Prediction: {self.title}")

                # TODO: Include logic for new winning history
                user_points_collection.update_one({"_id" : betting_record["_id"]}, { "$set" : {
                    "points" : user_points_record["points"] + amount,
                    "wins.number_of" : user_points_record["wins"]["number_of"] + 1
                }})
                
        elif winning_group == language.end_text_reasons.DOUBTERS.value:
            for betting_record in betting_records:
                if betting_record["betting_side"] == language.end_text_reasons.BELIEVERS.value:
                    break
                discord_member = guild.get_member(betting_record["_id"])
                user_points_record = user_points_collection.find_one({"_id" : betting_record["_id"]})

                user_winning_ratio = betting_record["bet_amount"] / self.doubt.amount
                amount = round(user_winning_ratio * self.believe.amount + betting_record["bet_amount"])
                logger.info(f"User: {discord_member.display_name or discord_member.name} (ID: {discord_member.id}) \n Has won {amount}\n Prediction: {self.title}")

                # TODO: Include logic for new winning history
                user_points_collection.update_one({"_id" : betting_record["_id"]}, { "$set" : {
                    "points" : user_points_record["points"] + amount,
                    "wins.number_of" : user_points_record["wins"]["number_of"] + 1
                }})
        
        self.clear_betting_records(betting_collection)
    
    async def get_user_bet(self, interaction: discord.Interaction, betting_records: Collection) -> int:
        user_betting_records = betting_records.find_one({"_id" : interaction.user.id})
        if user_betting_records:
            await interaction.response.send_message(language.Language().output_string("check_bet_result").format(
                mention = interaction.user.mention,
                amount = user_betting_records["bet_amount"]
            ), ephemeral = True)
            return
        else:
            await interaction.response.send_message(language.Language().output_string("check_bet_empty").format(
                mention = interaction.user.mention
            ))
            return
    
    def clear_betting_records(self, collection: Collection):
        collection.delete_many({})