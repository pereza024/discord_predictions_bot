import setting
import discord
from discord.ext import commands

logger = setting.logging.getLogger("bot")

def run():
    #NOTE: Discord Bot Intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="$$", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"Logging in: {bot.user} (ID: {bot.user.id})")

    @bot.command(
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