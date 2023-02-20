import datetime
from database import Database

import discord

class Competition_Reason():
    def __init__(self, title: str, amount: int = 0):
        self.title: str = title
        self.amount: int = amount
        self.users: discord.user = []

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
