import datetime, time

from setting import logger
import language
from competition import Competition

import discord

import pymongo
from pymongo.database import Database
from pymongo.collection import Collection

__user_points__ = "User Points"
__competition_history__ = "Competitions"

class Guild():
    __DEFAULT_USER_POINTS__ : int = 1000

    def __fetch_collection__(self, collection_type: str, database_client: pymongo.MongoClient) -> Collection:
        database: Database = database_client.get_database(f"Guild_ID:{self.discord_reference.id}")
        if database == None:
            database = database_client[f"{self.discord_reference.id}"]

        for name in database.list_collection_names():
            if name == collection_type:
                return database.get_collection(collection_type)

        return database.create_collection(collection_type)

    def __create_points_record__(self, member: discord.Member):
        self.user_points_collection.insert_one({
            "_id" : member.id, "name" : member.name,
            "display_name" : member.display_name,
            "points" : self.__DEFAULT_USER_POINTS__,
            "wins" : {
                "total" : 0,
                "largest_win" : 0,
                "number_of" : 0
            }
        })
    
    def __lookup_active_competition__(self):
        record = self.competition_history_collection.find_one({"is_active": True})
        if record:
            self.active_competition = Competition(record["title"], record["believe"]["title"], record["doubt"]["title"], self.discord_reference, record["is_anonymous"], record["bet_minimum"])
            self.active_competition.id = record["_id"]
            
            self.active_competition.believe.amount = record["believe"]["total_amount"]
            self.active_competition.believe.users = record["believe"]["users"]
            
            self.active_competition.doubt.amount = record["doubt"]["total_amount"]
            self.active_competition.doubt.users = record["doubt"]["users"]

    def __init__(self, discord_instance: discord.Guild, database_client: pymongo.MongoClient):
        self.discord_reference = discord_instance
        self.user_points_collection: Collection = self.__fetch_collection__(__user_points__, database_client)
        self.competition_history_collection: Collection = self.__fetch_collection__(__competition_history__, database_client)
        self.active_competition: Competition = None
        
        for member in discord_instance.members:
            record = self.user_points_collection.find({"_id" : member.id})
            if not record: 
                self.__create_points_record__(member)

    def start_competition(self, title: str, duration: int, believe_reason: str, doubt_reason: str, is_anonymous: bool, bet_minimum: int) -> str:
        self.active_competition: Competition = Competition(title, believe_reason, doubt_reason, self.discord_reference, is_anonymous, bet_minimum)
        logger.info(f"Creating a new competition: \n  ID: {self.active_competition.id}\n  Title: {self.active_competition.title}\n  Guild: {self.discord_reference}\n  Is_Anonymous: {self.active_competition.is_anonymous}\n  Bet_Minimum: {self.active_competition.bet_minimum}")

        self.competition_history_collection.insert_one({
            "_id" : self.active_competition.id,
            "title" : self.active_competition.title,
            "believe" : {
                "title": self.active_competition.believe.title,
                "users": self.active_competition.believe.users,
                "total_amount": self.active_competition.believe.amount
            },
            "doubt" : {
                "title": self.active_competition.doubt.title,
                "users": self.active_competition.doubt.users,
                "total_amount": self.active_competition.doubt.amount
            },
            "is_active" : True,
            "is_anonymous" : self.active_competition.is_anonymous,
            "bet_minimum": self.active_competition.bet_minimum
        })

        # SECTION: Text Formatting for return
        self.active_competition.timer = duration
        self.active_competition.end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        minutes, seconds = divmod(duration, 60)

        anon_text = ""
        if self.active_competition.is_anonymous:
            anon_text = "Enabled"
        else:
            anon_text = "Disabled"

        return language.Language().output_string("predict_start").format(
            competition_title = self.active_competition.title,
            believe = self.active_competition.believe.title,
            doubt = self.active_competition.doubt.title,
            duration = self.active_competition.format_time(minutes, seconds),
            anonymous = anon_text,
            bet_min = self.active_competition.bet_minimum
        )

    async def end_competition(self, interaction: discord.Interaction, winner_type_value):
        text_controller = language.Language()
        if self.active_competition.believe.amount == 0 and self.active_competition.doubt.amount == 0:
            # Resets the clocks to stop the while loop from having to keep executing
            self.active_competition.timer = -1
            self.active_competition.end_time = -1

            # Update DB to no longer track and declare the competition inactive
            self.active_competition.clear_competition()
            self.competition_history_collection.update_one({"_id" : self.active_competition.id}, {"$set" : {"is_active" : False}})

            await interaction.response.send_message(text_controller.output_string("winner_empty"))
            return
        
        # Send correct winner text to client
        if winner_type_value == language.end_text_reasons.BELIEVERS.value:
            await interaction.response.send_message(text_controller.get_prediction_end(self.active_competition, language.end_text_reasons.BELIEVERS))
        elif winner_type_value == language.end_text_reasons.DOUBTERS.value:
            await interaction.response.send_message(text_controller.get_prediction_end(self.active_competition, language.end_text_reasons.DOUBTERS))
        else:
            raise ValueError
        
        # Call Competition's helper functions to distribute the winnings of the competition
        self.active_competition.declare_winner(... , winner_type_value)
        
        # Empty the betting Pool
        self.active_competition.clear_competition()
        self.active_competition = None

    def check_if_betting_session_open(self):
        if not self.active_competition:
            raise RuntimeError

        minutes, seconds = divmod(self.active_competition.timer, 60)
        self.active_competition.timer -= 1
        time.sleep(1)

        anon_text = ""
        if self.active_competition.is_anonymous:
            anon_text = "Enabled"
        else:
            anon_text = "Disabled"

        return language.Language().output_string("predict_start").format(
            competition_title = self.active_competition.title,
            believe = self.active_competition.believe.title,
            doubt = self.active_competition.doubt.title,
            duration = self.active_competition.format_time(minutes, seconds),
            anonymous = anon_text,
            bet_min = self.active_competition.bet_minimum
        )