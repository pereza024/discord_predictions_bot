import time

import setting, language
from setting import logger
from competition import Competition
from database import Database

import discord
from discord import app_commands
from discord.ext import (commands)

class Prediction_Bot(commands.Bot):
    active_competition = None

def run():
    #NOTE: Discord Bot Intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True


    bot: Prediction_Bot = Prediction_Bot(command_prefix="$$", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"Logging in: {bot.user} (ID: {bot.user.id})")
        await bot.tree.sync()

        #Registers the Discord Server into the DB
        mongo_client = Database(setting.CLUSTER_LINK, setting.DB_NAME)
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

    @bot.hybrid_command(
        aliases = ['p'],
        help = "This is help",
        description = "This is description",
        brief = "This is brief"
    )
    async def ping(ctx):
        """" Answers with pong """
        await ctx.send("pong")

    bot.run(setting.DISCORD_API_TOKEN, root_logger = True)

if __name__ == "__main__":
    run()