# The GPLv3 License (GPLv3)

# Copyright © 2024 @rasulovk authors.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module defines the command handlers for the Telegram bot using aiogram.
"""

from aiogram import Bot
from aiogram.types import Message, BotCommand
from aiogram.filters import Command, CommandStart
from aiogram import Router
from ollama import Client
import constants as constants
import re
import time
import aiohttp
from dataclasses import dataclass


@dataclass
class OllamaState:
    """
    Arguments
    ==========
    ollama_client: The Ollama client to use for sending messages.
    model: The model to use for inference.
    message_chunk_size: The number of words to be sent at a time.
    """

    client: Client
    model: str
    message_chunk_size: int

ollama_state: OllamaState = None
administrator_user_ids: list[int] = []
approved_users: list[int] = []
ollama_host: str = ""

def get_content(raw_query) -> str:
    """
    Remove the command from query.

    Arguments:
    ==========
    raw_query: the raw query from telegram.
    """
    query: list[str] = re.split(" ", raw_query, 1)
    return query[1] if len(query) > 1 else None

def get_main_menu_commands(is_admin: bool) -> list[BotCommand]:
    """
    Returns the main menu commands for the bot.

    Arguments:
    ==========
    is_admin: Boolean indicating if the user is an admin.
    """
    main_menu_commands = [
        BotCommand(command='/help', description='Help on using the bot'),
        BotCommand(command='/start', description='Start the bot'),
        BotCommand(command='/infer', description='Chat with the bot'),
        BotCommand(command='/echo', description='Get status of the bot'),
        BotCommand(command='/list_models', description='List models'),
        BotCommand(command='/change_model', description='Change model'),
    ]

    if is_admin:
        main_menu_commands.extend([
            BotCommand(command='/pull_model', description='Pull model'),
            BotCommand(command='/remove_model', description='Remove model'),
        ])

    return main_menu_commands


def escape_md(text: str) -> str:
    """Escape Markdown special characters in Aiogram messages."""
    return re.sub(r"([_*[\]()~`>#+-=|{}.!])", r"\\\1", text)

# Normal Command Handlers
# class NormalCommandHandlers:

# Initialize module-level router
router = Router()

def __init__(ollama_state: OllamaState, approved_users: list[int]):
    ollama_state = ollama_state
    approved_users = approved_users

def is_approved(self, message: Message):
    """
    Check if the current user is an approved user.

    Arguments:
    ==========
    message: The message to be processed.
    """
    return (message.from_user.id in self.approved_users)

# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def start(self, message: Message):
    """
    Informs the user about its version.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not self.is_approved(message):
        await message.reply("You are not an Approved!")
        return None

    await message.answer(
        text=constants.WELCOME_MESSAGE,
        parse_mode="Markdown",
    )

# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands='help'))
async def help(self, message: Message):
    """
    Informs the user about its commands.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not self.is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return None

    await message.answer(
        text=constants.HELP_MESSAGE,
        parse_mode="Markdown",
    )

async def basic_inference(self, message: Message):
    """
    Performs inference on the given message.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not self.is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return None

    # Ignore messages that start with a '/'
    if message.text.startswith('/'):
        return

    query: str = get_content(message.text)

    if query is None:
        print(f"[Log] Received mistaken click. {query}")
        await message.reply(
            text=constants.MISTAKEN_CLICK,
            parse_mode="Markdown"
        )
        return

    response_message: Message = await message.reply(
        text="wait...", parse_mode="Markdown"
    )

    response_text = self.ollama_state.client.chat(
        model=self.ollama_state.model,
        messages=[
            {
                "role": "user",
                "content": query,
            },
        ],
    )["message"]["content"]

    # Escape special characters for Markdown
    response_text = escape_md(response_text)

    await response_message.edit_text(
        text=response_text,
        parse_mode="MarkdownV2",
    )

async def stream_inference(self, message: Message):
    """
    Performs inference on the given message.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not self.is_approved(message):
        await message.reply("You are not an Approved!")
        return None

    prev_msg_size: int = 0
    query: str = get_content(message.text)

    if query is None:
        await message.reply(
            text=constants.MISTAKEN_CLICK,
            parse_mode="Markdown"
        )
        return

    response_message: Message = await message.reply(
        text="wait...", parse_mode="Markdown"
    )
    message_stream: list[str] = []
    for message_chunk in self.ollama_state.client.chat(
        model=self.ollama_state.model,
        messages=[
            {
                "role": "user",
                "content": query,
            },
        ],
        stream=True,
    ):
        message_stream.append(message_chunk["message"]["content"])
        cur_msg_size = len(message_stream)

        # avoid BadRequest
        if cur_msg_size == prev_msg_size:
            continue

        is_message_rounded: bool = (
            cur_msg_size % self.ollama_state.message_chunk_size == 0
        )

        is_last_chunk: bool = (
            message_chunk["done"]
        )

        if is_message_rounded or is_last_chunk:
            prev_msg_size = cur_msg_size
            await response_message.edit_text(
                text="".join(message_stream), parse_mode="Markdown"
            )
            time.sleep(2)

# Administration Command Handlers
class AdministrationCommandHandlers:
    def __init__(self, ollama_state: OllamaState, administrator_user_ids: list[int], ollama_host: str):
        self.ollama_state = ollama_state
        self.administrator_user_ids = administrator_user_ids
        self.ollama_host = ollama_host

    def is_admin(self, message: Message):
        """
        Check if the current user is an administrator.

        Arguments:
        ==========
        message: The message to be processed.
        """
        return (message.from_user.id in self.administrator_user_ids)

    async def echo(self, message: Message):
        """
        Tests the connection with another URL.

        This function sends a simple HTTP request to another URL and returns the response.

        Arguments:
        ==========
        message: The message to be processed.
        """
        if not self.is_admin(message):
            await message.reply("You are not an Admin!")
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(self.ollama_host) as response:
                status = response.status
                await message.answer(
                    text=f"Connection test to another URL returned status code: {status}",
                    parse_mode="Markdown",
                )

    async def list_models(self, message: Message):
        """
        List the available models in Ollama.

        Arguments:
        ==========
        message: The message to be processed.
        """
        if not self.is_admin(message):
            await message.reply("You are not an Admin!")
            return None

        try:
            models_response = self.ollama_state.client.list()
            model_list: list[str] = [
                model["model"] for model in models_response.get("models", [])
            ]
        except Exception as e:
            await message.reply(
                f"Failed to retrieve models: {str(e)}",
                parse_mode="Markdown"
            )
            return None

        if len(model_list) == 0:
            await message.reply(
                "No models available. Pull some using the `/pull_model` command.",
                parse_mode="Markdown"
            )
            return None

        models_text = "\n".join(model_list)

        await message.reply(f"Available models is below: \n\n{models_text}", parse_mode="Markdown")

    async def change_model(self, message: Message):
        """
        Change the model used by Ollama.

        Arguments:
        ==========
        message: The message to be processed.
        """
        if not self.is_admin(message):
            await message.reply("You are not an Admin!")
            return None
        model: str = get_content(message.text)
        self.ollama_state.model = model
        await message.reply(
            f"Alright! changing to *{model}*.", parse_mode="Markdown"
        )

    async def pull_model(self, message: Message):
        """
        Pull the model used by Ollama.

        Arguments:
        ==========
        message: The message to be processed.
        """
        if not self.is_admin(message):
            await message.reply("You are not an Admin!")
            return None
        model: str = get_content(message.text)
        if len(model) == 0:
            await message.reply(
                "We don't have any models!\nTry pulling them."
            )
            return None
        await message.reply(f"Pulling {model}!")
        self.ollama_state.client.pull(model)
        await message.reply(f"Done pulling {model}!")

    async def remove_model(self, message: Message):
        """
        Delete the model used by Ollama.

        Arguments:
        ==========
        message: The message to be processed.
        """
        if not self.is_admin(message):
            await message.reply("You are not an Admin!")
            return None
        model: str = get_content(message.text)
        await message.reply(f"Deleting {model}!")
        self.ollama_state.client.delete(model)
        await message.reply(f"Done deleting {model}!")
