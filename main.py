import time, datetime, random
from threading import Timer

import setting, language
from language import Language
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
    language_controller = Language()

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
            logger.info(bot.language_controller.output_string("polling_checker").format(name = guild.name))
            for voice_channel in guild.voice_channels:
                if len(voice_channel.members) > 0:
                    for member in voice_channel.members:
                        points = random.randint(15, 45)
                        mongo_client.insert_points_record(guild, member, points)
                        logger.info(bot.language_controller.output_string("activity_reward").format(
                            name = member.display_name or member.name,
                            id = member.id,
                            points = points,
                            guild_name = guild.name
                        ))
        
        this = Timer(60 * 15, check_server_member_status)
        this.start()

    @bot.event
    async def on_ready():
        logger.info(bot.language_controller.output_string("bot_login").format(user = bot.user, id = bot.user.id))
        await bot.tree.sync()

        # Registers the Discord Server into the DB
        mongo_client.register_guilds(bot.guilds)

        logger.info(f"Finished registering guilds")
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
        title = bot.language_controller.output_string("predict_title_description"),
        duration = bot.language_controller.output_string("predict_duration_description"),
        believe_reason = bot.language_controller.output_string("predict_believe_description"),
        doubt_reason = bot.language_controller.output_string("predict_doubt_description")
    )
    @bot.tree.command(
        name="predict",
        description=bot.language_controller.output_string("predict_command_description"),
    )
    async def predict(interaction: discord.Interaction, title: str, duration: int, believe_reason: str = "Yes", doubt_reason: str = "No"):
        if not bot.active_competition:
            bot.active_competition = Competition(title, believe_reason, doubt_reason, interaction.guild)
            bot.Timer = duration
            bot.end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration) # Tracker of the time duration of the prediction
            minutes, seconds = divmod(duration, 60)
            await interaction.response.send_message(bot.language_controller.output_string("predict_start").format(
                competition_title = bot.active_competition.title,
                believe = bot.active_competition.believe.title,
                doubt = bot.active_competition.doubt.title,
                duration = bot.active_competition.format_time(minutes, seconds)
            ))

            while bot.active_competition and bot.Timer >= 0:
                time.sleep(1)
                minutes, seconds = divmod(bot.Timer, 60)
                bot.Timer -= 1
                await interaction.edit_original_response(content = bot.language_controller.output_string("predict_start").format(
                    competition_title = bot.active_competition.title,
                    believe = bot.active_competition.believe.title,
                    doubt = bot.active_competition.doubt.title,
                    duration = bot.active_competition.format_time(minutes, seconds)
                ))
        else:
            await interaction.response.send_message(bot.language_controller.output_string("predict_in_progress_description"), ephemeral = True)
    @predict.error
    async def predict_error(interaction: discord.Interaction, error):
        #TODO: Specific error handling
        logger.error(bot.language_controller.output_string("logging_error").format(
            display_name = interaction.user.display_name,
            id = interaction.user.id,
            error = error
        ))
        await interaction.response.send_message(bot.language_controller.output_string("generic_error"), ephemeral = True)

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
        member_points_collection = mongo_client.get_guild_points_collection(interaction.guild)
        member_point_data = member_points_collection.find_one({"_id": interaction.user.id})
        
        if bot.active_competition and bot.Timer > -1:
            for user in bot.active_competition.doubt.users:
                if interaction.user.id == user['_id']:
                    await interaction.response.send_message(bot.language_controller.output_string("betting_side_error").format(
                        mention = interaction.user.mention
                    ), ephemeral = True)
                    return
            if 0 >= member_point_data['points'] or amount >= member_point_data['points'] or 0 >= amount:
                await interaction.response.send_message(bot.language_controller.output_string("betting_amount_error").format(
                    mention = interaction.user.mention
                ), ephemeral = True)
                return
            else:
                bot.active_competition.add_user_to_pool(interaction, mongo_client, False, amount)
                value = member_point_data["points"] - amount
                member_points_collection.replace_one({"_id" : interaction.user.id}, {"name" : member_point_data['name'], "points" : value}, True)
                await interaction.response.send_message(bot.language_controller.output_string("betting_believe_result").format(
                    name = interaction.user.display_name,
                    amount = amount,
                    title = bot.active_competition.title
                ), ephemeral = False)
                
                logger.info(bot.language_controller.output_string("logging_betting_positive").format(
                    guild = interaction.guild,
                    name = member_point_data['name'],
                    id = member_point_data['_id'],
                    amount = amount
                ))
        elif bot.active_competition and bot.Timer == -1:
            await interaction.response.send_message(bot.language_controller.output_string("betting_over_error").format(
                mention = interaction.user.mention
            ), ephemeral = True)
        else:
            await interaction.response.send_message(bot.language_controller.output_string("betting_prediction_over_error").format(
                mention = interaction.user.mention
            ), ephemeral = True)
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
        member_points_collection = mongo_client.get_guild_points_collection(interaction.guild)
        member_point_data = member_points_collection.find_one({"_id": interaction.user.id})

        if bot.active_competition and bot.Timer > -1:
            for user in bot.active_competition.believe.users:
                if interaction.user.id == user['_id']:
                    await interaction.response.send_message(bot.language_controller.output_string("betting_side_error").format(
                        mention = interaction.user.mention
                    ), ephemeral = True)
                    return
            if 0 >= member_point_data['points'] or amount >= member_point_data['points'] or 0 >= amount:
                await interaction.response.send_message(bot.language_controller.output_string("betting_amount_error").format(
                    mention = interaction.user.mention
                ), ephemeral = True)
                return
            else:
                bot.active_competition.add_user_to_pool(interaction, mongo_client, True, amount)
                value = member_point_data["points"] - amount
                member_points_collection.replace_one({"_id" : interaction.user.id}, {"name" : member_point_data['name'], "points" : value}, True)
                await interaction.response.send_message(bot.language_controller.output_string("betting_doubt_result").format(
                    name = interaction.user.display_name,
                    amount = amount,
                    title = bot.active_competition.title
                ), ephemeral = False)

                logger.info(bot.language_controller.output_string("logging_betting_negative").format(
                    guild = interaction.guild,
                    name = member_point_data['name'],
                    id = member_point_data['_id'],
                    amount = amount
                ))
        elif bot.active_competition and bot.Timer == -1:
            await interaction.response.send_message(bot.language_controller.output_string("betting_over_error").format(
                mention = interaction.user.mention
            ), ephemeral = True)
        else:
            await interaction.response.send_message(bot.language_controller.output_string("betting_prediction_over_error").format(
                mention = interaction.user.mention
            ), ephemeral = True)
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
        if bot.active_competition:
            await interaction.response.send_message(bot.language_controller.get_prediction_end(bot.active_competition, language.end_text_reasons.REFUND), ephemeral = False)
            bot.Timer = -1
            bot.end_time = -1
            bot.active_competition.clear_competition(mongo_client, True)
            bot.active_competition = None
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
        if bot.active_competition:
            if bot.active_competition.believe.amount == 0 and bot.active_competition.doubt.amount == 0:
                await interaction.response.send_message(bot.language_controller.output_string("winner_empty"))
                bot.Timer = -1
                bot.end_time = -1
                bot.active_competition.clear_competition(mongo_client)
                bot.active_competition = None
                return
            if winner_type.value == language.end_text_reasons.BELIEVERS.value:
                await interaction.response.send_message(bot.language_controller.get_prediction_end(bot.active_competition, language.end_text_reasons.BELIEVERS))
            elif winner_type.value == language.end_text_reasons.DOUBTERS.value:
                await interaction.response.send_message(bot.language_controller.get_prediction_end(bot.active_competition, language.end_text_reasons.DOUBTERS))
            else:
                raise ValueError()
                
            bot.active_competition.declare_winner(mongo_client, winner_type.value)
            bot.active_competition.clear_competition(mongo_client)
            bot.active_competition = None
            pass
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
        collection = mongo_client.get_guild_points_collection(interaction.guild)
        data = collection.find_one({"_id" : interaction.user.id })

        await interaction.response.send_message(bot.language_controller.output_string("points_result").format(
            mention = interaction.user.mention,
            amount = round(data["points"])
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
        collection = mongo_client.get_guild_betting_pool_collection(interaction.guild)
        data = collection.find_one({"_id" : interaction.user.id })

        if data:
            await interaction.response.send_message(bot.language_controller.output_string("check_bet_result").format(
                mention = interaction.user.mention,
                amount = round(data["points"])
            ), ephemeral = True)
        else:
            await interaction.response.send_message(bot.language_controller.output_string("check_bet_empty").format(
                mention = interaction.user.mention
            ), ephemeral = True)

    bot.run(setting.DISCORD_API_TOKEN, root_logger = True)

if __name__ == "__main__":
    run()