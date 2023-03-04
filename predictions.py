import secrets, bson, datetime, time
from threading import Timer

import language
from setting import logger

import discord

import pymongo
from pymongo.database import Database
from pymongo.collection import Collection

class Guild():
    __DEFAULT_USER_POINTS__ : int = 1000

    def __fetch_collection__(self, collection_type: str, database_client: pymongo.MongoClient) -> Collection:
        database: Database = database_client.get_database(f"Guild_ID:{self.discord_reference.id}")
        if database == None:
            database = database_client[f"{self.id}"]

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
        """Function created for the bot to call anytime it needs to reference the DB if a competition session is active but not in active memory of the bot. Shouldn't be used for normal bot operations."""
        record = self.competition_history_collection.find_one({"is_active": True})
        if record:
            self.active_competition = Competition(record["title"], record["believe"]["title"], record["doubt"]["title"], self, record["is_anonymous"], record["bet_minimum"])
            self.active_competition.id = record["_id"]
            
            self.active_competition.believe.amount = record["believe"]["total_amount"]
            self.active_competition.believe.users = record["believe"]["users"]
            
            self.active_competition.doubt.amount = record["doubt"]["total_amount"]
            self.active_competition.doubt.users = record["doubt"]["users"]

    async def __lookup_voice_channel_activity__(self):
        logger.info(language.Language().output_string("polling_checker").format(name = self.discord_reference.name))
        for voice_channel in self.discord_reference.voice_channels:
            if len(voice_channel.members) > 0:
                for member in voice_channel.members:
                    points = 0
                    if member.voice.deaf or member.voice.self_deaf:
                        points = random.randint(1 , 5)
                    else:
                        points = random.randint(20 , 30)
                    # self.add_user_points() # Function does not work
                    logger.info(bot.language_controller.output_string("activity_reward").format(
                        name = member.display_name or member.name,
                        id = member.id,
                        points = points,
                        guild_name = guild.discord_reference.name
                    ))
        
        this = Timer(60 * 15, check_server_member_status)
        this.start()

    def __init__(self, discord_reference: discord.Guild, database_client: pymongo.MongoClient):
        __user_points__ = "User Points"
        __competition_history__ = "Competitions"
        __betting_pool__ = "Betting Pool"

        self.discord_reference: discord.Guild =  discord_reference
        self.user_points_collection: Collection = self.__fetch_collection__(__user_points__, database_client)
        self.competition_history_collection: Collection = self.__fetch_collection__(__competition_history__, database_client)
        self.betting_record_collection: Collection = self.__fetch_collection__(__betting_pool__, database_client)
        self.active_competition: Competition = None
        
        for member in self.discord_reference.members:
            record = self.user_points_collection.find_one({"_id" : member.id})
            if not record: 
                self.__create_points_record__(member)
    
    def get_user_points(self, user: discord.User):
        record = self.user_points_collection.find_one({"_id" : user.id})
        return record["points"]
    
    def get_betting_session_status(self):
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
            duration = language.Language().format_time(minutes, seconds),
            anonymous = anon_text,
            bet_min = self.active_competition.bet_minimum
        )

    async def set_user_bet(self, interaction: discord.Interaction, amount: int, is_doubter: bool) -> str:
        if not self.active_competition:
            await interaction.response.send_message(language.Language().output_string("betting_prediction_over_error").format(
                mention = interaction.user.mention
            ), ephemeral = True)
            return

        user_betting_record = self.betting_record_collection.find_one({"_id" : interaction.user.id})
        user_points_record = self.user_points_collection.find_one({"_id" : interaction.user.id})
        active_competition_record = self.competition_history_collection.find_one({"_id" : self.active_competition.id})

        if self.active_competition and self.active_competition.timer > -1:
            # User already picked opposite side
            if is_doubter:
                for user in active_competition_record["believe"]["users"]:
                    if interaction.user.id == user["id"]:
                        await interaction.response.send_message(language.Language().output_string("betting_side_error").format(
                            mention = interaction.user.mention
                        ), ephemeral = True)
                    return
            else:
                for user in active_competition_record["doubt"]["users"]:
                    if interaction.user.id == user["id"]:
                        await interaction.response.send_message(language.Language().output_string("betting_side_error").format(
                            mention = interaction.user.mention
                        ), ephemeral = True)
                    return
            
            # User has insufficiant points for betting
            # TODO: Might want to split this up into seperate exceptions to give more specific feedback to the user
            if amount > user_points_record['points'] or amount < self.active_competition.bet_minimum or user_points_record['points'] <= 0:
                await interaction.response.send_message(language.Language().output_string("betting_amount_error").format(
                    mention = interaction.user.mention
                ), ephemeral = True)
                return

            if is_doubter:
                if not user_betting_record:
                    # Update the competition logs
                    users_array: list = active_competition_record["doubt"]["users"]
                    record = self.active_competition.create_user_history_record(interaction.user, amount)
                    users_array.append(record)
                    self.competition_history_collection.update_one({"_id" : self.active_competition.id} , {"$set" : {
                        "doubt.total_amount": active_competition_record["doubt"]["total_amount"] + amount,
                        "doubt.users": users_array
                    }})
                    # Add betting history records
                    self.betting_record_collection.insert_one({
                        "_id" : interaction.user.id,
                        "bet_amount" : amount,
                        "betting_side" : language.end_text_reasons.DOUBTERS.value
                    })
                else:
                    # Update the competition logs
                    users_array: list = active_competition_record["doubt"]["users"]
                    for user in users_array:
                        if user["id"] == interaction.user.id:
                            user["amount"] = user["amount"] + amount
                            break
                    self.competition_history_collection.update_one({"_id" : self.active_competition.id}, { "$set" : {
                        "doubt.total_amount" : active_competition_record["doubt"]["total_amount"] + amount,
                        "doubt.users": users_array
                    }})
                    # Update to the betting logs
                    self.betting_record_collection.update_one({"_id" : interaction.user.id}, { "$set" : {
                        "bet_amount": user_betting_record["bet_amount"] + amount
                    }})

                self.active_competition.doubt.amount += amount

                # Remove points from the user's wallet
                self.user_points_collection.update_one({"_id" : interaction.user.id}, {"$set": {
                    "points" : user_points_record["points"] - amount
                }})
                
                await interaction.response.send_message(language.Language().output_string("betting_doubt_result").format(
                    name = interaction.user.display_name,
                    amount = amount,
                    title = self.active_competition.title
                ))

                logger.info(language.Language().output_string("logging_betting_negative").format(
                    guild = interaction.guild,
                    name = interaction.user.name,
                    id = interaction.user.id,
                    amount = amount
                ))

            else:
                if not user_betting_record:
                    # Update the competition logs
                    users_array: list = active_competition_record["believe"]["users"]
                    record = self.active_competition.create_user_history_record(interaction.user, amount)
                    users_array.append(record)
                    self.competition_history_collection.update_one({"_id" : self.active_competition.id} , {"$set" : {
                        "believe.total_amount": active_competition_record["believe"]["total_amount"] + amount,
                        "believe.users": users_array
                    }})
                    # Add betting history records
                    self.betting_record_collection.insert_one({
                        "_id" : interaction.user.id,
                        "bet_amount" : amount,
                        "betting_side" : language.end_text_reasons.BELIEVERS.value
                    })
                else:
                    # Update the competition logs
                    users_array: list = active_competition_record["believe"]["users"]
                    for user in users_array:
                        if user["id"] == interaction.user.id:
                            user["amount"] = user["amount"] + amount
                            break
                    self.competition_history_collection.update_one({"_id" : self.active_competition.id}, { "$set" : {
                        "believe.total_amount" : active_competition_record["believe"]["total_amount"] + amount,
                        "believe.users": users_array
                    }})
                    # Update to the betting logs
                    self.betting_record_collection.update_one({"_id" : interaction.user.id}, { "$set" : {
                        "bet_amount": user_betting_record["bet_amount"] + amount
                    }})
                self.active_competition.believe.amount += amount

                # Remove points from the user's wallet
                self.user_points_collection.update_one({"_id" : interaction.user.id}, {"$set": {
                    "points" : user_points_record["points"] - amount
                }})
                
                await interaction.response.send_message(language.Language().output_string("betting_believe_result").format(
                    name = interaction.user.display_name,
                    amount = amount,
                    title = self.active_competition.title
                ))

                logger.info(language.Language().output_string("logging_betting_positive").format(
                    guild = interaction.guild,
                    name = interaction.user.name,
                    id = interaction.user.id,
                    amount = amount
                ))
        elif self.active_competition and self.active_competition.timer == -1:
            await interaction.response.send_message(language.Language().output_string("betting_over_error").format(
                mention = interaction.user.mention
            ), ephemeral = True)
    
    def start_competition(self, title: str, duration: int, believe_reason: str, doubt_reason: str, is_anonymous: bool, bet_minimum: int) -> str:
        self.active_competition: Competition = Competition(title, believe_reason, doubt_reason, self, is_anonymous, bet_minimum)
        logger.info(f"Creating a new competition: \n  ID: {self.active_competition.id}\n  Title: {self.active_competition.title}\n  Guild: {self}\n  Is_Anonymous: {self.active_competition.is_anonymous}\n  Bet_Minimum: {self.active_competition.bet_minimum}")

        self.competition_history_collection.insert_one({
            "_id" : self.active_competition.id,
            "title" : self.active_competition.title,
            "believe" : {
                "title": self.active_competition.believe.title,
                "users": self.active_competition.believe.users,
                "total_amount": self.active_competition.believe.amount,
                "won" : False
            },
            "doubt" : {
                "title": self.active_competition.doubt.title,
                "users": self.active_competition.doubt.users,
                "total_amount": self.active_competition.doubt.amount,
                "won" : False
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
            duration = language.Language().format_time(minutes, seconds),
            anonymous = anon_text,
            bet_min = self.active_competition.bet_minimum
        )

    async def end_competition(self, interaction: discord.Interaction, winner_type_value):
        text_controller = language.Language()
        # Resets the clocks to stop the while loop from having to keep executing
        self.active_competition.timer = -1
        self.active_competition.end_time = -1
        
        if self.active_competition.believe.amount == 0 and self.active_competition.doubt.amount == 0:    
            # Update DB to no longer track and declare the competition inactive
            self.active_competition.clear_betting_records(self.betting_record_collection)
            self.competition_history_collection.update_one({"_id" : self.active_competition.id}, {"$set" : {"is_active" : False}})

            await interaction.response.send_message(text_controller.output_string("winner_empty"))

            self.active_competition = None
            return
        
        if winner_type_value == language.end_text_reasons.REFUND.value:
            self.active_competition.refund_points(self.betting_record_collection, self.user_points_collection)
            await interaction.response.send_message(language.Language().format_end_competition(self.active_competition, language.end_text_reasons.REFUND), ephemeral = False)
            self.competition_history_collection.update_one({"_id" : self.active_competition.id}, {"$set" : {"is_active" : False}})
            self.active_competition = None
            return

        # Send correct winner text to client
        if winner_type_value == language.end_text_reasons.BELIEVERS.value:
            self.competition_history_collection.update_one({"_id" : self.active_competition.id}, {"$set" : {
                "believe.won" : True
            }})
            await interaction.response.send_message(text_controller.format_end_competition(self.active_competition, language.end_text_reasons.BELIEVERS))
        elif winner_type_value == language.end_text_reasons.DOUBTERS.value:
            self.competition_history_collection.update_one({"_id" : self.active_competition.id}, {"$set" : {
                "doubt.won" : True
            }})
            await interaction.response.send_message(text_controller.format_end_competition(self.active_competition, language.end_text_reasons.DOUBTERS))

        # Call Competition's helper functions to distribute the winnings of the competition
        self.active_competition.set_points_winnings(
            guild = self.discord_reference,
            betting_collection = self.betting_record_collection,
            user_points_collection = self.user_points_collection,
            winning_group = winner_type_value
        )

        self.competition_history_collection.update_one({"_id" : self.active_competition.id}, {"$set" : {"is_active" : False}})
        
        self.active_competition = None


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