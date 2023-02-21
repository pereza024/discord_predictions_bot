import datetime
from database import Database

import discord

from pymongo import collection

class Competition_Reason():
    def __init__(self, title: str, amount: int = 0):
        self.title: str = title
        self.amount: int = amount
        self.users = []

class Competition():
    def __init__(self, title: str, believe_reason: str, doubt_reason: str, duration: int, guild: discord.guild):
        self.title: str = title # Title of the Competiton

        self.Timer = duration
        self.endTime = datetime.datetime.now() + datetime.timedelta(seconds=duration) # Tracker of the time duration of the prediction
        
        self.guild: discord.guild = guild # Associated Discord server calling for the competition
        self.believe: Competition_Reason = Competition_Reason(believe_reason)
        self.doubt: Competition_Reason = Competition_Reason(doubt_reason)

    def format_time(self, minutes: int, seconds: int):
        return '{:02d}:{:02d}'.format(minutes, seconds)

    def add_user_to_pool(self, interaction: discord.Interaction, mongo_client: Database, is_doubter: bool, amount: int):
        if is_doubter:
            self.doubt.users.append({"_id": interaction.user.id, "name": interaction.user.display_name or interaction.user.name })
        else:
            self.believe.users.append({"_id": interaction.user.id, "name": interaction.user.display_name or interaction.user.name })
        
        mongo_client.insert_betting_record(interaction, is_doubter, amount)

    def clear_competition(self, mongo_client: Database):
        mongo_client.clear_records(self.guild)
