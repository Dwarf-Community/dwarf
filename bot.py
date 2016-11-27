"""A Discord bot by AileenLumina, based on Red-DiscordBot, written on top of discord.py."""

import discord
from discord.ext import commands
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from .api import BaseAPI
from .core.api import CoreAPI
from .models import Guild, Channel
from . import strings

import sys
import logging
import logging.handlers


base = BaseAPI()
core = CoreAPI()

def force_input(msg):
    entered_input = input(msg)
    if entered_input:
        return entered_input
    return force_input(msg)


def get_answer():
    choices = ("yes", "y", "no", "n")
    c = ""
    while c not in choices:
        c = input(">").lower()
    if c is choices[0] or c is choices[1]:
        return True
    else:
        return False


def is_configured():
    if base.get_token() is None:
        return False
    else:
        return True


def initial_config():
    print(strings.setup_greeting)

    entered_token = input("> ")

    if len(entered_token) >= 50:  # Assuming token
        base.set_token(entered_token)
    else:
        print(strings.not_a_token)
        exit(1)

    confirmation = False
    while not confirmation:
        print(strings.choose_prefix)
        new_prefix = force_input("\n> ").strip()
        print(strings.confirm_prefix.format(new_prefix))
        if input("> ") in ['y', 'yes']:
            core.add_prefix(new_prefix)
            confirmation = True

    print(strings.setup_finished)
    input("\n")


def _load_cogs(bot):
    def load_cog(cogname):
        bot.load_extension('dwarf.' + cogname + '.commands')

    load_cog('core')

    management_cog = bot.get_cog('Core')
    if management_cog is None:
        raise ImportError("Could not find the Core cog.")

    failed = []
    cogs = base.get_extensions()
    for cog in cogs:
        try:
            load_cog(cog)
        except Exception as e:
            print("{}: {}".format(e.__class__.__name__, str(e)))
            bot.logger.exception(e)
            failed.append(cog)

    if failed:
        print("\nFailed to load: ", end="")
        for m in failed:
            print(m + " ", end="")
        print("\n")

    return management_cog


bot = commands.Bot(command_prefix=core.get_prefixes(), description=__doc__, pm_help=core.is_help_private())


@bot.event
async def on_command(command, ctx):
    author = ctx.message.author
    user = get_user_model().objects.get_or_create(id=author.id)[0]
    user.command_count += 1
    user.save()
    bot.send_message(author, strings.user_registered.format(author.name))


@bot.event
async def on_message(message):
    if user_allowed(message):
        try:
            user = core.get_user(message.author.id)[0]
            user.message_count += 1
            user.save()
        except ObjectDoesNotExist:
            pass
        await bot.process_commands(message)


@bot.event
async def on_command_error(error, ctx):
    channel = ctx.message.channel
    if isinstance(error, commands.MissingRequiredArgument):
        await send_command_help(ctx)
    elif isinstance(error, commands.BadArgument):
        await send_command_help(ctx)
    elif isinstance(error, commands.DisabledCommand):
        await bot.send_message(channel, strings.command_disabled)
    elif isinstance(error, commands.CommandInvokeError):
        logger.exception(strings.exception_in_command.format(
            ctx.command.qualified_name), exc_info=error.original)
        oneliner = strings.error_in_command.format(
            ctx.command.qualified_name, type(error.original).__name__,
            str(error.original))
        await ctx.bot.send_message(channel, oneliner)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, commands.NoPrivateMessage):
        await bot.send_message(channel, strings.not_available_in_dm)
    else:
        logger.exception(type(error).__name__, exc_info=error)


async def send_command_help(ctx):
    if ctx.invoked_subcommand:
        pages = bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)
    else:
        pages = bot.formatter.format_help_for(ctx, ctx.command)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)


def user_allowed(message):

    # bots are not allowed to interact with other bots
    if message.author.bot:
        return False

    if core.get_owner_id() == message.author.id:
        return True

    return True


async def get_oauth_url():
    try:
        data = await bot.application_info()
    except AttributeError:
        return strings.update_the_api
    return discord.utils.oauth_url(data.id)


async def set_bot_owner():
    try:
        data = await bot.application_info()
        core.set_owner_id(data.owner.id)
    except AttributeError:
        print(strings.update_the_api)
        return
    print(strings.owner_recognized.format(data.owner.name))


def set_logger():
    global logger
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)

    logger = logging.getLogger('dwarf')
    logger.setLevel(logging.INFO)

    red_format = logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)
    stdout_handler.setLevel(logging.INFO)

    logger.addHandler(stdout_handler)


# TODO Module system


@bot.event
async def on_ready():
    if core.get_owner_id() is None:
        await set_bot_owner()
    print('------')
    print(strings.bot_is_online.format(bot.user.name))
    print('------')
    print(strings.connected_to)
    print(strings.connected_to_servers.format(Guild.objects.count()))
    print(strings.connected_to_channels.format(Channel.objects.count()))
    print(strings.connected_to_users.format(get_user_model().objects.count()))
    print("\n{} active cogs".format(len(base.get_extensions())))
    prefix_label = strings.prefix_singular
    if len(core.get_prefixes()) > 1:
        prefix_label = strings.prefix_plural
    print("{}: {}\n".format(prefix_label, " ".join(list(core.get_prefixes()))))
    print("------")
    print(strings.use_this_url)
    url = await get_oauth_url()
    bot.oauth_url = url
    print(url)
    print("------")


def main():
    set_logger()
    _load_cogs(bot)
    if core.get_prefixes():
        bot.command_prefix = list(core.get_prefixes())
    else:
        print(strings.no_prefix_set)
        bot.command_prefix = ["!"]

    print(strings.logging_into_discord)
    print(strings.keep_updated)
    print(strings.official_server.format(strings.invite_link))

    try:
        yield from bot.login(base.get_token())
    except TypeError as e:
        print(e)
        sys.exit(strings.update_the_api)

    yield from bot.connect()
