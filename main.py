import time

import setting, language
from setting import logger
from competition import Competition
from database import Database

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import (commands)

class Prediction_Bot(commands.Bot):
    active_competition: Competition = None

def run():
    #NOTE: Discord Bot Intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True


    mongo_client = Database(setting.CLUSTER_LINK, setting.DB_NAME)
    bot: Prediction_Bot = Prediction_Bot(command_prefix="$$", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"Logging in: {bot.user} (ID: {bot.user.id})")
        await bot.tree.sync()

        #Registers the Discord Server into the DB
        mongo_client.register_guilds(bot.guilds)
        logger.info(f"Finished registering guilds")

    @bot.tree.command()
    async def predict(interaction: discord.Interaction, title: str, duration: int, believe_reason: str = "Yes", doubt_reason: str = "No"):
        if not bot.active_competition:
            bot.active_competition = Competition(title, believe_reason, doubt_reason, duration, interaction.guild)
            minutes, seconds = divmod(duration, 60)
            await interaction.response.send_message(language.startText(bot.active_competition.title, bot.active_competition.believe.title, bot.active_competition.doubt.title, bot.active_competition.format_time(minutes, seconds)))

            while bot.active_competition and bot.active_competition.Timer >= 0:
                time.sleep(1)
                minutes, seconds = divmod(bot.active_competition.Timer, 60)
                bot.active_competition.Timer -= 1
                await interaction.edit_original_response(content=language.startText(bot.active_competition.title, bot.active_competition.believe.title, bot.active_competition.doubt.title, bot.active_competition.format_time(minutes, seconds)))
                pass
            await interaction.delete_original_response()
        else:
            #TODO: String Library
            await interaction.response.send_message("Prediction currently running, please wait for it to finish, terminate it early, or refund the amount", ephemeral = True)
    
    @bot.tree.command()
    async def believe(interaction: discord.Interaction, amount: int):
        member_points_collection = mongo_client.get_guild_points_collection(interaction.guild)
        member_point_data = member_points_collection.find_one({"_id": interaction.user.id})

        logger.info(f"Guild: {interaction.guild}, Finding this user: {member_point_data['name']} (ID: {member_point_data['_id']})")
        
        if bot.active_competition:
        #TODO: Do not allow a negative bet
            for user in bot.active_competition.doubt.users:
                if interaction.user.id == user['_id']:
                    #TODO: String Library
                    await interaction.response.send_message(f"{interaction.user.mention} you have already chosen your side for this prediction", ephemeral=True)
                    return
            if 0 >= member_point_data['points'] or amount >= member_point_data['points']:
                await interaction.response.send_message(f"{interaction.user.mention} you don't have enough points to make that bet", ephemeral=True)
                return
            else:
                bot.active_competition.add_user_to_pool(interaction, mongo_client, False, amount)
                value = member_point_data["points"] - amount
                member_points_collection.replace_one({"_id" : interaction.user.id}, {"name" : member_point_data['name'], "points" : value}, True)
                await interaction.response.send_message(f"{interaction.user.display_name} has bet {amount} in favor of \"{bot.active_competition.title}\"", ephemeral=False)

        else:
            #TODO: String Library
            await interaction.response.send_message(f"{interaction.user.mention} the prediction hasn't started! Either start a prediction or ask an admin in the channel to start one.", ephemeral=True)
    
    @bot.tree.command()
    async def doubt(interaction: discord.Interaction, amount: int):
        member_points_collection = mongo_client.get_guild_points_collection(interaction.guild)
        member_point_data = member_points_collection.find_one({"_id": interaction.user.id})

        logger.info(f"Guild: {interaction.guild}, Finding this user: {member_point_data['name']} (ID: {member_point_data['_id']})")
        
        if bot.active_competition:
        #TODO: Do not allow a negative bet
            for user in bot.active_competition.believe.users:
                if interaction.user.id == user['_id']:
                    #TODO: String Library
                    await interaction.response.send_message(f"{interaction.user.mention} you have already chosen your side for this prediction", ephemeral=True)
                    return
            if 0 >= member_point_data['points'] or amount >= member_point_data['points']:
                await interaction.response.send_message(f"{interaction.user.mention} you don't have enough points to make that bet", ephemeral=True)
                return
            else:
                bot.active_competition.add_user_to_pool(interaction, mongo_client, True, amount)
                value = member_point_data["points"] - amount
                member_points_collection.replace_one({"_id" : interaction.user.id}, {"name" : member_point_data['name'], "points" : value}, True)
                await interaction.response.send_message(f"{interaction.user.display_name} has bet {amount} against of \"{bot.active_competition.title}\"", ephemeral=False)

        else:
            #TODO: String Library
            await interaction.response.send_message(f"{interaction.user.mention} the prediction hasn't started! Either start a prediction or ask an admin in the channel to start one.", ephemeral=True)

    @bot.tree.command()
    async def refund(interaction: discord.Interaction, user: discord.User = None):
        if bot.active_competition:
            await interaction.response.send_message(language.endText(bot.active_competition.title, language.end_text_reasons.REFUND), ephemeral = False)
            bot.active_competition.clear_competition(mongo_client, True)
            bot.active_competition = None
        else:
            #TODO: Create a dictionary of strings
            await interaction.response.send_message("Nothing to refund! No prediction running.", ephemeral = True)

    @bot.tree.command()
    @app_commands.choices(winner_type =[
        Choice(name="Believer", value=0),
        Choice(name="Doubter", value=1)
    ])
    async def winner(interaction: discord.Interaction, winner_type: discord.app_commands.Choice[int]):
        if bot.active_competition:
            await interaction.response.send_message(language.winning_text(bot.active_competition, winner_type.value))
            bot.active_competition.declare_winner(mongo_client, winner_type.value)
            bot.active_competition.clear_competition(mongo_client)
            bot.active_competition = None
            pass
        else:
            #TODO: Create a dictionary of strings
            await interaction.response.send_message("Nothing to declare a winner on! No prediction running.", ephemeral = True)

    bot.run(setting.DISCORD_API_TOKEN, root_logger = True)

if __name__ == "__main__":
    run()