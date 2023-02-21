import time, datetime, random
from threading import Timer

import setting, language
from setting import logger
from competition import Competition
from database import Database

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import (commands)

class Prediction_Bot(commands.Bot):
    Timer: int = -1
    end_time: int = -1
    active_competition: Competition = None

def is_owner(interaction: discord.Interaction):
    allowed_user_ids = [
        116977532573581314, 185202327119069184, 158040090566852609
    ]

    for user_id in allowed_user_ids:
        if interaction.user.id == user_id:
            return True
    return False

def run():
    #NOTE: Discord Bot Intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True


    mongo_client = Database(setting.CLUSTER_LINK, setting.DB_NAME)
    bot: Prediction_Bot = Prediction_Bot(command_prefix="$$", intents=intents)

    def check_server_member_status():
        for guild in bot.guilds:
            logger.info(f"Polling for points: {guild.name}")

            collection = mongo_client.get_guild_points_collection(guild)
            for voice_channel in guild.voice_channels:
                if len(voice_channel.members) > 0:
                    for member in voice_channel.members:
                        points = random.randint(90, 125)
        
        this = Timer(60, check_server_member_status)
        this.start()

    @bot.event
    async def on_ready():
        logger.info(f"Logging in: {bot.user} (ID: {bot.user.id})")
        await bot.tree.sync()

        #Registers the Discord Server into the DB
        mongo_client.register_guilds(bot.guilds)
        logger.info(f"Finished registering guilds")
        check_server_member_status()

    @bot.tree.command()
    @app_commands.check(is_owner)
    async def predict(interaction: discord.Interaction, title: str, duration: int, believe_reason: str = "Yes", doubt_reason: str = "No"):
        if not bot.active_competition:
            bot.active_competition = Competition(title, believe_reason, doubt_reason, interaction.guild)
            bot.Timer = duration
            bot.end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration) # Tracker of the time duration of the prediction
            minutes, seconds = divmod(duration, 60)
            await interaction.response.send_message(language.startText(bot.active_competition.title, bot.active_competition.believe.title, bot.active_competition.doubt.title, bot.active_competition.format_time(minutes, seconds)))

            while bot.active_competition and bot.Timer >= 0:
                time.sleep(1)
                minutes, seconds = divmod(bot.Timer, 60)
                bot.Timer -= 1
                await interaction.edit_original_response(content=language.startText(bot.active_competition.title, bot.active_competition.believe.title, bot.active_competition.doubt.title, bot.active_competition.format_time(minutes, seconds)))
        else:
            #TODO: String Library
            await interaction.response.send_message("Prediction currently running, please wait for it to finish, terminate it early, or refund the amount", ephemeral = True)
    @predict.error
    async def predict_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
    @bot.tree.command()
    async def believe(interaction: discord.Interaction, amount: int):
        print(f"{bool(bot.active_competition)} & {bot.Timer}")
        member_points_collection = mongo_client.get_guild_points_collection(interaction.guild)
        member_point_data = member_points_collection.find_one({"_id": interaction.user.id})

        logger.info(f"Guild: {interaction.guild}, Finding this user: {member_point_data['name']} (ID: {member_point_data['_id']})")
        
        if bot.active_competition and bot.Timer > -1:
            for user in bot.active_competition.doubt.users:
                if interaction.user.id == user['_id']:
                    #TODO: String Library
                    await interaction.response.send_message(f"{interaction.user.mention} you have already chosen your side for this prediction", ephemeral=True)
                    return
            if 0 >= member_point_data['points'] or amount >= member_point_data['points'] or 0 >= amount:
                await interaction.response.send_message(f"{interaction.user.mention} you don't have enough points to make that bet", ephemeral=True)
                return
            else:
                bot.active_competition.add_user_to_pool(interaction, mongo_client, False, amount)
                value = member_point_data["points"] - amount
                member_points_collection.replace_one({"_id" : interaction.user.id}, {"name" : member_point_data['name'], "points" : value}, True)
                await interaction.response.send_message(f"{interaction.user.display_name} has bet {amount} in favor of \"{bot.active_competition.title}\"", ephemeral=False)
        elif bot.active_competition and bot.Timer == -1:
            await interaction.response.send_message(f"{interaction.user.mention} the prediction submission have ended! Waiting on outcome.", ephemeral=True)
        else:
            #TODO: String Library
            await interaction.response.send_message(f"{interaction.user.mention} the prediction hasn't started! Either start a prediction or ask an admin in the channel to start one.", ephemeral=True)
    
    @bot.tree.command()
    async def doubt(interaction: discord.Interaction, amount: int):
        member_points_collection = mongo_client.get_guild_points_collection(interaction.guild)
        member_point_data = member_points_collection.find_one({"_id": interaction.user.id})

        logger.info(f"Guild: {interaction.guild}, Finding this user: {member_point_data['name']} (ID: {member_point_data['_id']})")
        
        if bot.active_competition and bot.Timer > -1:
            for user in bot.active_competition.believe.users:
                if interaction.user.id == user['_id']:
                    #TODO: String Library
                    await interaction.response.send_message(f"{interaction.user.mention} you have already chosen your side for this prediction", ephemeral=True)
                    return
            if 0 >= member_point_data['points'] or amount >= member_point_data['points'] or 0 >= amount:
                await interaction.response.send_message(f"{interaction.user.mention} you don't have enough points to make that bet", ephemeral=True)
                return
            else:
                bot.active_competition.add_user_to_pool(interaction, mongo_client, True, amount)
                value = member_point_data["points"] - amount
                member_points_collection.replace_one({"_id" : interaction.user.id}, {"name" : member_point_data['name'], "points" : value}, True)
                await interaction.response.send_message(f"{interaction.user.display_name} has bet {amount} against of \"{bot.active_competition.title}\"", ephemeral=False)
        elif bot.active_competition and bot.Timer == -1:
            await interaction.response.send_message(f"{interaction.user.mention} the prediction submittions have ended! Waiting on outcome.", ephemeral=True)
        else:
            #TODO: String Library
            await interaction.response.send_message(f"{interaction.user.mention} the prediction hasn't started! Either start a prediction or ask an admin in the channel to start one.", ephemeral=True)

    @bot.tree.command()
    @app_commands.check(is_owner)
    async def refund(interaction: discord.Interaction, user: discord.User = None):
        if bot.active_competition:
            await interaction.response.send_message(language.endText(bot.active_competition.title, language.end_text_reasons.REFUND), ephemeral = False)
            bot.Timer = -1
            bot.end_time = -1
            bot.active_competition.clear_competition(mongo_client, True)
            bot.active_competition = None
        else:
            #TODO: Create a dictionary of strings
            await interaction.response.send_message("Nothing to refund! No prediction running.", ephemeral = True)
    @refund.error
    async def refund_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)

    @bot.tree.command()
    @app_commands.check(is_owner)
    @app_commands.choices(winner_type =[
        Choice(name="Believer", value=0),
        Choice(name="Doubter", value=1)
    ])
    async def winner(interaction: discord.Interaction, winner_type: discord.app_commands.Choice[int]):
        if bot.active_competition:
            if bot.active_competition.believe.amount == 0 and bot.active_competition.doubt.amount == 0:
                await interaction.response.send_message("Ending contest. Nothing to declare a winner on! No bets made")
                bot.Timer = -1
                bot.end_time = -1
                bot.active_competition.clear_competition(mongo_client)
                bot.active_competition = None
                return
            await interaction.response.send_message(language.winning_text(bot.active_competition, winner_type.value))
            bot.active_competition.declare_winner(mongo_client, winner_type.value)
            await bot.active_competition.clear_competition(mongo_client)
            bot.active_competition = None
            pass
        else:
            #TODO: Create a dictionary of strings
            await interaction.response.send_message("Nothing to declare a winner on! No prediction running.", ephemeral = True)
    @winner.error
    async def say_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
    bot.run(setting.DISCORD_API_TOKEN, root_logger = True)

if __name__ == "__main__":
    run()