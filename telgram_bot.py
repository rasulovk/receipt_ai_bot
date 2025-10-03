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
This module defines the Telegram bot functionality using aiogram.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
import httpx
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from aiogram.dispatcher.router import Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from ollama import Client
from functools import partial
from handlers import  user_handlers, admin_handlers
from handlers.user_handlers import get_main_menu_commands
from ollama_client import OllamaState, init_ollama_state

# Инициализируем логгер
logger = logging.getLogger(__name__)



# Define a handler function to process the /start command
# async def start_command_handler(message: Message, bot: Bot, administrator_user_ids: list[int]):
#     user_id = message.from_user.id
#     is_admin_user = user_id in administrator_user_ids
#     print("[Info] User id: " + str(user_id))
#     await set_main_menu(bot, administrator_user_ids,user_id)
#     await message.answer(f"Welcome Admin status: {is_admin_user}")

def create_bot(
    ollama_host: str,
    bot_token: str,
    default_model: str,
    administrator_user_ids: list[int],
    approved_users: list[int],
    message_chunk_size: int,
) -> Bot:
    """
    Initializes and returns a Telegram bot application using aiogram.

    Arguments:
    ==========
    ollama_host: Host address of the `ollama` service.
    bot_token: Bot token for telegram.
    default_model: The default model to load when the bot is initialized.
    administrator_user_ids: Telegram user ids of the administrators.
    message_chunk_size: The number of words to be sent at a time.
    """
    # Initialize Ollama state
    ollama_state: OllamaState = OllamaState(
        Client(host=ollama_host,timeout=httpx.Timeout(130.0)), default_model, message_chunk_size
    )
    # Set the global ollama_state for ollama_client.py
    init_ollama_state(ollama_state.client, ollama_state.model, ollama_state.message_chunk_size)
    
    # Initialize command handlers
    normal_command_handlers = user_handlers.__init__(approved_users, administrator_user_ids, ollama_host)
    # normal_command_handlers.inference = normal_command_handlers.basic_inference

    administrative_command_handlers = admin_handlers.__init__(
        ollama_state, administrator_user_ids, ollama_host
    )

    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info('Starting bot')

    # Initialize bot and dispatcher
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
    dp = Dispatcher()
    
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    
    return bot, dp


async def set_main_menu(bot: Bot, administrator_user_ids: list[int], bot_id: int):
    """
    Set the main menu for the bot.
    """
    is_admin = bot_id in administrator_user_ids
    print("[Info] declared admin user for main menu: " + str(is_admin))
    main_menu_commands = get_main_menu_commands(is_admin)
    await bot.set_my_commands(main_menu_commands)

async def run_bot(bot: Bot, dp: Dispatcher, administrator_user_ids: list[int], approved_users: list[int]):
    """
    Run the bot with polling.
    """
    await bot.delete_webhook(drop_pending_updates=True)
    await set_main_menu(bot, administrator_user_ids, bot_id=0)
    await dp.start_polling(bot)