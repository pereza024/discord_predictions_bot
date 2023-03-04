import random
from threading import Timer

import setting, language
from setting import logger
from predictions import (Guild, Competition)

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import (commands)

from pymongo import MongoClient

class Prediction_Bot(commands.Bot):
    guilds_instances: dict = {}
    Timer: int = -1
    end_time: int = -1
    active_competition: Competition = None
    language_controller = language.Language()

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

    bot: Prediction_Bot = Prediction_Bot(command_prefix="$$", intents=intents)

    def check_server_member_status():
        for guild in bot.guilds_instances.values():
            logger.info(language.Language().output_string("polling_checker").format(name = guild.discord_reference.name))
            for voice_channel in guild.discord_reference.voice_channels:
                if len(voice_channel.members) > 0:
                    for member in voice_channel.members:
                        points = 0
                        if member.voice.deaf or member.voice.self_deaf:
                            points = random.randint(1 , 5)
                        else:
                            points = random.randint(20 , 30)
                        # guild.add_user_points() # Function does not work
                        logger.info(bot.language_controller.output_string("activity_reward").format(
                            name = member.display_name or member.name,
                            id = member.id,
                            points = points,
                            guild_name = guild.discord_reference.name
                        ))
        
        this = Timer(60 * 15, check_server_member_status)
        this.start()

    @bot.event
    async def on_connect():
        logger.info("Bot connected to client")
        
    @bot.event
    async def on_ready():
        logger.info(bot.language_controller.output_string("bot_login").format(user = bot.user, id = bot.user.id))
        await bot.tree.sync()

        # Registers the Discord Servers into the DB
        for guild in bot.guilds:
            logger.info(f"Attempting to initialize an instance of the Guild() class for {guild.name}")
            bot.guilds_instances[guild.id] = Guild(guild, MongoClient(setting.CLUSTER_LINK))
            
            # Look and recreate active predictions
            guild_instance: Guild = bot.guilds_instances.get(guild.id)
            guild_instance.__lookup_active_competition__()

        logger.info(f"Finished registering guilds")
        
        # Scan for active users and give them points
        check_server_member_status()

    @bot.event
    async def on_member_join(member: discord.Member):
        logger.info(f"Adding in {member.display_name or member.name} (ID: {member.id}) to the {member.guild} collection")
        mongo_client.register_new_member(member)

    ###
    ### Discord Bot Command - /predict
    ### Starts the prediction for the discord server
    ###
    @app_commands.check(is_owner and is_channel)
    @app_commands.describe(
        title = language.Language().output_string("predict_title_description"),
        duration = language.Language().output_string("predict_duration_description"),
        believe_reason = language.Language().output_string("predict_believe_description"),
        doubt_reason = language.Language().output_string("predict_doubt_description"),
        is_anonymous = language.Language().output_string("predict_is_anonymous_description"),
        bet_minimum = language.Language().output_string("predict_bet_minimum_description")
    )
    @bot.tree.command(
        name="predict",
        description=bot.language_controller.output_string("predict_command_description"),
    )
    async def predict(
        interaction: discord.Interaction,
        title: str,
        duration: int,
        believe_reason: str = "Yes",
        doubt_reason: str = "No",
        is_anonymous: bool = False,
        bet_minimum: int = 1
    ):
        if bot.is_ready():
            guild_instance: Guild = bot.guilds_instances[interaction.guild.id]
            if not guild_instance.active_competition:
                await interaction.response.send_message(content = guild_instance.start_competition(title, duration, believe_reason, doubt_reason, is_anonymous, bet_minimum),ephemeral = False)
                    
                while guild_instance.active_competition and guild_instance.active_competition.timer >= 0:
                    await interaction.edit_original_response(content = guild_instance.check_betting_session_status())
            else:
                await interaction.response.send_message(Language().output_string("predict_in_progress_description"), ephemeral = True)
        else:
            await interaction.response.send_message("Error: Bot is not ready", ephemeral=True)
    @predict.error
    async def predict_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(Language().output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(Language().output_string("generic_error"), ephemeral = True)

    ###
    ### Discord Bot Command - /believe
    ### Allows the user to bet on the positive outcome
    ###
    @bot.tree.command(
        name="believe",
        description=bot.language_controller.output_string("believe_command_description")
    )
    @app_commands.describe(
        amount = bot.language_controller.output_string("betting_amount_description")
    )
    @app_commands.check(is_channel)
    async def believe(interaction: discord.Interaction, amount: int):
        guild_instance: Guild = bot.guilds_instances[interaction.guild.id]
        await guild_instance.set_user_bet(interaction, amount, False)
    @believe.error
    async def believe_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(bot.language_controller.output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(bot.language_controller.output_string("generic_error"), ephemeral = True)
    
    ###
    ### Discord Bot Command - /doubt
    ### Allows the user to bet on the negative outcome
    ###  
    @bot.tree.command(
        name="doubt",
        description=bot.language_controller.output_string("doubt_command_description")
    )
    @app_commands.describe(
        amount = bot.language_controller.output_string("betting_amount_description")
    )
    @app_commands.check(is_channel)
    async def doubt(interaction: discord.Interaction, amount: int):
        guild_instance: Guild = bot.guilds_instances[interaction.guild.id]
        await guild_instance.set_user_bet(interaction, amount, True) 
    @doubt.error
    async def doubt_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(bot.language_controller.output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(bot.language_controller.output_string("generic_error"), ephemeral = True)

    ###
    ### Discord Bot Command - /refund
    ### Allows a competition admin to issue a refund to all or a specific user
    ###  
    @bot.tree.command(
        name="refund",
        description=bot.language_controller.output_string("refund_command_description")
    )
    @app_commands.default_permissions()
    @app_commands.check(is_owner and is_channel)
    async def refund(interaction: discord.Interaction, user: discord.User = None):
        guild_instance: Guild = bot.guilds_instances[interaction.guild.id]
        if guild_instance.active_competition:
            await guild_instance.end_competition(interaction, language.end_text_reasons.REFUND.value)
        else:
            await interaction.response.send_message(bot.language_controller.output_string("refund_prediction_over"), ephemeral = True)
    @refund.error
    async def refund_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(bot.language_controller.output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(bot.language_controller.output_string("generic_error"), ephemeral = True)

    ###
    ### Discord Bot Command - /winner
    ### Declares a winner for the prediction
    ###  
    @bot.tree.command(
        name="winner",
        description=bot.language_controller.output_string("winner_command_description")
    )
    @app_commands.check(is_owner and is_channel)
    @app_commands.describe(
        winner_type = bot.language_controller.output_string("winner_type_description")
    )
    @app_commands.choices(winner_type =[
        Choice(name="Believer", value=1),
        Choice(name="Doubter", value=2)
    ])
    async def winner(interaction: discord.Interaction, winner_type: discord.app_commands.Choice[int]):
        guild_instance: Guild = bot.guilds_instances[interaction.guild.id]
        if guild_instance.active_competition:
            await guild_instance.end_competition(interaction, winner_type.value)
        else:
            await interaction.response.send_message(bot.language_controller.output_string("winner_prediction_over"), ephemeral = True)
    @winner.error
    async def winner_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(bot.language_controller.output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(bot.language_controller.output_string("generic_error"), ephemeral = True)

    ###
    ### Discord Bot Command - /points
    ### Checks the total points for the user
    ###  
    @bot.tree.command(
        name="points",
        description=bot.language_controller.output_string("points_command_description")
    )
    @app_commands.check(is_channel)
    async def points(interaction: discord.Interaction):
        guild_instance: Guild = bot.guilds_instances[interaction.guild.id]
        await interaction.response.send_message(language.Language().output_string("points_result").format(
            mention = interaction.user.mention,
            amount = guild_instance.get_user_points(interaction.user)
        ), ephemeral = True)

    @points.error
    async def points_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(bot.language_controller.output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(bot.language_controller.output_string("generic_error"), ephemeral = True)

    ###
    ### Discord Bot Command - /check_bet
    ### Checks the total points for the user
    ###  
    @bot.tree.command(
        name="check_bet",
        description=bot.language_controller.output_string("check_bet_command_description")
    )
    @app_commands.check(is_channel)
    async def check_bet(interaction: discord.Interaction):
        guild_instance: Guild= bot.guilds_instances[interaction.guild.id]
        if guild_instance.active_competition:
            await guild_instance.active_competition.get_user_bet(interaction, guild_instance.betting_record_collection)
        # TODO: Add a message for when betting closed
        # TODO: Add which side the user bet for
        else: 
            await interaction.response.send_message(language.Language().output_string("check_bet_empty").format(
                mention = interaction.user.mention
            ), ephemeral = True)

    ###
    ### Discord Bot Command - /leaderboard
    ### Shows the channel's top 5 points leaders
    ###  
    @bot.tree.command(
        name="leaderboard",
        description=bot.language_controller.output_string("leaderboard_command_description")
    )
    async def leaderboard(interaction: discord.Interaction):
        results: list = mongo_client.get_guild_points_leaderboard(interaction.guild)
        await interaction.response.send_message(bot.language_controller.format_leaderboard(interaction.guild, results))
    
    bot.run(setting.DISCORD_API_TOKEN, root_logger = True)

if __name__ == "__main__":
    run()