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
        116977532573581314, 185202327119069184, 158040090566852609, 152237169551998976
    ]
    
    for user_id in allowed_user_ids:
        if interaction.user.id == user_id:
            return True
    return False

def is_channel(interaction: discord.Interaction):
    if interaction.guild.id == 184728713731112961:
        allowed_channel_ids = [
            1077450054031388804
        ]
        for channel_id in allowed_channel_ids:
            if interaction.channel.id == channel_id:
                return True
        return False
    else:
        return True

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
                        points = random.randint(15, 45)
                        mongo_client.insert_points_record(guild, member, points)
                        logger.info(f"Giving {member.display_name or member.name} (ID: {member.id}) {points} Points for being inside {guild.name}'s voice channels")
        
        this = Timer(60 * 15, check_server_member_status)
        this.start()

    @bot.event
    async def on_ready():
        logger.info(f"Logging in: {bot.user} (ID: {bot.user.id})")
        await bot.tree.sync()

        #Registers the Discord Server into the DB
        mongo_client.register_guilds(bot.guilds)
        logger.info(f"Finished registering guilds")
        check_server_member_status()

    @bot.event
    async def on_member_join(member: discord.Member):
        logger.info(f"Adding in {member.display_name or member.name} (ID: {member.id}) to the {member.guild} collection")
        mongo_client.register_new_member(member)

    @bot.tree.command()
    @app_commands.check(is_owner and is_channel)
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
        time.sleep(60)
        await interaction.delete_original_response()
        
    @bot.tree.command()
    @app_commands.check(is_channel)
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
    @believe.error
    async def believe_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
        time.sleep(60)
        await interaction.delete_original_response()
        
    @bot.tree.command()
    @app_commands.check(is_channel)
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
    @doubt.error
    async def doubt_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
        time.sleep(60)
        await interaction.delete_original_response()

    @bot.tree.command()
    @app_commands.check(is_owner and is_channel)
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
        time.sleep(60)
        await interaction.delete_original_response()

    @bot.tree.command()
    @app_commands.check(is_owner and is_channel)
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
    async def winner_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
        time.sleep(60)
        await interaction.delete_original_response()
    
    @bot.tree.command()
    @app_commands.check(is_channel)
    async def check_points(interaction: discord.Interaction):
        collection = mongo_client.get_guild_points_collection(interaction.guild)
        data = collection.find_one({"_id" : interaction.user.id })

        await interaction.response.send_message(language.check_points(interaction.user, data["points"]), ephemeral=True)
    @check_points.error
    async def check_points_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
        time.sleep(60)
        await interaction.delete_original_response()

    @bot.tree.command()
    @app_commands.check(is_channel)
    async def check_bet(interaction: discord.Interaction):
        collection = mongo_client.get_guild_betting_pool_collection(interaction.guild)
        data = collection.find_one({"_id" : interaction.user.id })

        if data:
            await interaction.response.send_message(language.check_bet(interaction.user, data["points"]), ephemeral=True)
        else:
            await interaction.response.send_message("You don't seem to have a bet.", ephemeral=True)
    @check_bet.error
    async def check_bet_error(interaction: discord.Interaction, error):
        logger.error(f"For user: {interaction.user.display_name} (ID: {interaction.user.id}) triggered the error: {error}")
        await interaction.response.send_message("Not Allowed!", ephemeral = True)
        time.sleep(60)
        await interaction.delete_original_response()

    bot.run(setting.DISCORD_API_TOKEN, root_logger = True)

if __name__ == "__main__":
    run()