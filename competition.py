from uuid import UUID

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
    def __init__(self, title: str, believe_reason: str, doubt_reason: str, guild: discord.guild):
        self.title: str = title # Title of the Competiton
        self.id: int = UUID.int # ID of the competition
        self.guild: discord.Guild = guild # Associated Discord server calling for the competition
        self.believe: Competition_Reason = Competition_Reason(believe_reason)
        self.doubt: Competition_Reason = Competition_Reason(doubt_reason)

    def format_time(self, minutes: int, seconds: int):
        return '{:02d}:{:02d}'.format(minutes, seconds)

    def add_user_to_pool(self, interaction: discord.Interaction, mongo_client: Database, is_doubter: bool, amount: int):
        if is_doubter:
            self.doubt.amount += amount
            self.doubt.users.append({"_id": interaction.user.id, "name": interaction.user.display_name or interaction.user.name })
        else:
            self.believe.amount += amount
            self.believe.users.append({"_id": interaction.user.id, "name": interaction.user.display_name or interaction.user.name })
        
        mongo_client.insert_betting_record(interaction, is_doubter, amount)

    def declare_winner(self, mongo_client: Database, winning_group: int):
        user_believers, user_doubter = self.believe.users, self.doubt.users

        # TODO: Determine winning amount
        amount = 0
        member_points_collection: Collection = mongo_client.get_guild_points_collection(self.guild)
        betting_pool_collection: Collection = mongo_client.get_guild_betting_pool_collection(self.guild)
        if winning_group == 1:
            for user in user_believers:
                discord_member = self.guild.get_member(user["_id"])

                user_points_data = member_points_collection.find_one({"_id" : user["_id"]})
                user_betting_data = betting_pool_collection.find_one({"_id" : user["_id"]})

                user_winning_ratio = user_betting_data["points"] / self.believe.amount
                amount = round(user_winning_ratio * self.doubt.amount + user_betting_data['points'])
                
                logger.info(f"User: {discord_member.display_name or discord_member.name} (ID: {discord_member.id}) \n Has won {amount}\n Prediction: {self.title}")

                betting_pool_collection.delete_one({"_id" : user_betting_data['_id']})
                member_points_collection.replace_one({"_id" : user_points_data['_id']}, {"name" : user_points_data['name'], "points" : user_points_data["points"] + amount}, True)
        elif winning_group == 2:
            for user in user_doubter:
                discord_member = self.guild.get_member(user["_id"])

                user_points_data = member_points_collection.find_one({"_id" : user["_id"]})
                user_betting_data = betting_pool_collection.find_one({"_id" : user["_id"]})

                user_winning_ratio = user_betting_data["points"] / self.doubt.amount
                amount = round(user_winning_ratio * self.believe.amount + user_betting_data['points'])

                logger.info(f"User: {discord_member.display_name or discord_member.name} (ID: {discord_member.id}) \n Has won {amount}\n Prediction: {self.title}")

                betting_pool_collection.delete_one({"_id" : user_betting_data['_id']})
                member_points_collection.replace_one({"_id" : user_points_data['_id']}, {"name" : user_points_data['name'], "points" : user_points_data["points"] + amount}, True)

    def clear_competition(self, mongo_client: Database, is_refund: bool = False):
        mongo_client.clear_records(self.guild, is_refund)
