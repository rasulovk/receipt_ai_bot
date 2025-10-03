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
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ollama import Client
import constants as constants
import re
import time
import aiohttp
from dataclasses import dataclass
from ollama_client import ollama_chat, ollama_vision, init_ollama_state
from ollama_client import OllamaState
import socket

# @dataclass
# class OllamaState:
#     """
#     Arguments
#     ==========
#     ollama_client: The Ollama client to use for sending messages.
#     model: The model to use for inference.
#     message_chunk_size: The number of words to be sent at a time.
#     """

#     client: Client
#     model: str
#     message_chunk_size: int

# ollama_state: OllamaState = None
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

    print("[Info] declared admin user for get main menu: " + str(is_admin))
    if is_admin:
        main_menu_commands.extend([
            BotCommand(command='/pull_model', description='Pull model'),
            BotCommand(command='/remove_model', description='Remove model'),
        ])

    return main_menu_commands


# def escape_md(text: str) -> str:
#     """Escape Markdown special characters in Aiogram messages."""
#     return re.sub(r"([_*[\]()~`>#+-=|{}.!])", r"\\\1", text)

def escape_md(text: str) -> str:
    """
    Escape Telegram MarkdownV2 special characters and remove dots from the message.
    """
    escape_chars = r"_*[]()~`>#+-=|{}!\\"
    # First, escape special characters
    escaped = re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    # Then, remove all dots from the message
    return escaped.replace('.', ',')

# Normal Command Handlers
# class NormalCommandHandlers:

# Initialize module-level router
router = Router()

# def __init__(ollama_state_param: OllamaState, approved_users_param: list[int]):
#     global ollama_state
#     global approved_users
#     ollama_state = ollama_state_param
#     approved_users = approved_users_param

# def is_approved(self, message: Message):
#     """
#     Check if the current user is an approved user.

#     Arguments:
#     ==========
#     message: The message to be processed.
#     """
#     return (message.from_user.id in self.approved_users)



# # Administration Command Handlers
# class AdministrationCommandHandlers:
def __init__(ollama_state_param: OllamaState, administrator_user_ids_param: list[int], ollama_host_param: str):
    global ollama_state
    global administrator_user_ids
    global ollama_host
    ollama_state = ollama_state_param
    administrator_user_ids = administrator_user_ids_param
    ollama_host = ollama_host_param

def is_admin(message: Message):
    """
    Check if the current user is an administrator.

    Arguments:
    ==========
    message: The message to be processed.
    """
    return (message.from_user.id in administrator_user_ids)

@router.message(Command(commands='echo'))
async def echo(message: Message):
    """
    Tests the connection with another URL.

    This function sends a simple HTTP request to another URL and returns the response.

    Arguments:
    ==========
    message: The message to be processed.
    """
    print("[Info] echo has been requested")
    if not is_admin(message):
        await message.reply("You are not an Admin!")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ollama_host) as response:
                status = response.status
                await message.answer(
                    text=f"Connection test to another URL returned status code: {status}",
                    parse_mode="Markdown",
                )
    except socket.gaierror as e:
        # # Cache/log DNS resolution error
        # with open("dns_errors.log", "a") as f:
        #     f.write(f"DNS resolution failed: {e}\n")
        await message.answer(
            text="DNS resolution failed. Error has been cached.",
            parse_mode="Markdown"
        )
    except Exception as e:
        # Cache/log any other error
        # with open("dns_errors.log", "a") as f:
        #     f.write(f"General connection error: {e}\n")
        await message.answer(
            text=f"Connection failed: {e}",
            parse_mode="Markdown"
        )

@router.message(Command(commands='list_models'))
async def list_models(message: Message):
    """
    List the available models in Ollama.

    Arguments:
    ==========
    message: The message to be processed.
    """
    print("[Info] Reqeusted for list models")
    if not is_admin(message):
        await message.reply("You are not an Admin!")
        return None

    try:
        models_response = ollama_state.client.list()
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

    await message.reply(f"Available models is below: \n\n{escape_md(models_text)}", parse_mode="Markdown")


# This function fetches the list of available LLM models from Ollama.
# It uses the `ollama_state.client.list()` method to get the models and returns a list of model names.
# It handles exceptions and prints an error message if the fetch fails.
async def fetch_llm_models() -> list[str]:
    """
    Fetch the list of available LLM models from Ollama.

    Returns:
    ==========
    A list of model names.
    """
    try:
        models_response = ollama_state.client.list()
        return [model["model"] for model in models_response.get("models", [])]
    except Exception as e:
        print(f"[Error] Failed to fetch models: {str(e)}")
        return []


# Function to create inline keyboards dynamically
def create_inline_kb(width: int, *args: str, last_btn: str | None = None, **kwargs: str) -> InlineKeyboardMarkup:
    """
    Generate an inline keyboard dynamically.

    Arguments:
    ==========
    width: Number of buttons per row.
    args: Button texts (callback_data will be the same as text).
    last_btn: Optional last button text with callback_data='last_btn'.
    kwargs: Button texts with custom callback_data.
    """
    kb_builder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = []

    # Add buttons from args
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=button,
                callback_data=f"change_model:{button}"
            ))

    # Add buttons from kwargs with custom callback_data
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=f"change_model:{button}"
            ))

    # Add buttons to the keyboard with the specified width
    kb_builder.row(*buttons, width=width)

    # Add the last button if provided
    if last_btn:
        kb_builder.row(InlineKeyboardButton(
            text=last_btn,
            callback_data='last_btn'
        ))

    return kb_builder.as_markup()

@router.message(Command(commands='change_model'))
async def change_model(message: Message):
    """
    Change the model used by Ollama.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not is_admin(message):
        await message.reply("You are not an Admin!")
        return None

    model_list = await fetch_llm_models()
    if not model_list:
        await message.reply(
            "No models available. Pull some using the `/pull_model` command.",
            parse_mode="Markdown"
        )
        return None

    # Use the create_inline_kb function to generate the keyboard
    keyboard = create_inline_kb(4, last_btn='Последняя кнопка', *model_list)

    await message.reply(
        "Select a model to switch to:",
        reply_markup=keyboard
    )

# Callback
@router.callback_query(lambda callback_query: callback_query.data.startswith("change_model:"))
async def handle_model_change(callback_query):
    """
    Handle the model change when a button is clicked.

    Arguments:
    ==========
    callback_query: The callback query triggered by the inline button.
    """
    model = callback_query.data.split(":", 1)[1]
    ollama_state.model = model
    await callback_query.message.edit_text(
        f"Model successfully changed to *{model}*.",
        parse_mode="Markdown"
    )

# @router.message(Command(commands='change_model'))
# async def change_model(message: Message):
#     """
#     Change the model used by Ollama.

#     Arguments:
#     ==========
#     message: The message to be processed.
#     """
#     if not is_admin(message):
#         await message.reply("You are not an Admin!")
#         return None
#     model: str = get_content(message.text)
#     ollama_state.model = model
#     await message.reply(
#         f"Alright! changing to *{model}*.", parse_mode="Markdown"
#     )

@router.message(Command(commands='pull_model'))
async def pull_model(message: Message):
    """
    Pull the model used by Ollama.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not is_admin(message):
        await message.reply("You are not an Admin!")
        return None
    model: str = get_content(message.text)
    if len(model) == 0:
        await message.reply(
            "We don't have any models!\nTry pulling them."
        )
        return None
    await message.reply(f"Pulling {model}!")
    ollama_state.client.pull(model)
    await message.reply(f"Done pulling {model}!")

@router.message(Command(commands='rm_model'))
async def remove_model(message: Message):
    """
    Delete the model used by Ollama.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not is_admin(message):
        await message.reply("You are not an Admin!")
        return None
    model: str = get_content(message.text)
    await message.reply(f"Deleting {model}!")
    ollama_state.client.delete(model)
    await message.reply(f"Done deleting {model}!")
