import setting
from setting import logger
from database import Database

import discord
from discord import app_commands
from discord.ext import (commands)

def run():
    #NOTE: Discord Bot Intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="$$", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"Logging in: {bot.user} (ID: {bot.user.id})")
        await bot.tree.sync()

        #Registers the Discord Server into the DB
        mongo_client = Database(setting.CLUSTER_LINK, setting.DB_NAME)
        mongo_client.register_guilds(bot.guilds)
        logger.info(f"Finished registering guilds")

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