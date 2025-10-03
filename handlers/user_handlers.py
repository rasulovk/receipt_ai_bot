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
import aiohttp
from aiogram.types import Message, BotCommand, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import Command, CommandStart
from aiogram import Router
from ollama import Client
import constants as constants
import re
import time
import aiohttp
import base64
from aiogram import F
from dataclasses import dataclass
from lexicon.lexicon import LEXICON_RU
from uuid import uuid4
from aiogram.types import Message, BotCommand, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from promtps.vision_prompt import RECEIPT_PARSER_PROMPT, DEFAULT_CHAT_PROMPT
import httpx
import json
import os
from dotenv import load_dotenv

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from noco_client import store_receipt_items, get_monthly_data, get_today_total_price, get_last_expenses
from ollama_client import ollama_chat, ollama_vision, init_ollama_state, get_current_model #  ollama_chat_mem


# Load environment variables for Telegram bot admin user IDs
# load_dotenv()
# admin_ids_str = os.getenv("ADMIN_ID", "")
# administrator_user_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()]
# print(f"[Info] Loaded admin user IDs: {administrator_user_ids}")


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
# Temporary storage for parsed items, keyed by response message ID
parsed_response_cache = {}

def is_admin(message: Message):
    """
    Check if the current user is an administrator.

    Arguments:
    ==========
    message: The message to be processed.
    """
    print(f"[Info] This is user id by is_admin function from mesagge : {message.from_user.id} and Admin stored Admin ids {administrator_user_ids}")
    return (message.from_user.id in administrator_user_ids)


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
    print(f"[Info] get main menu function receive status: {is_admin}")
    main_menu_commands = [
        BotCommand(command='/start', description='Start the bot'),
        # BotCommand(command='/infer', description='Chat with the bot'),

    ]
    print(f"[Info] get main menu function receive status: {is_admin}")
    if is_admin:
        main_menu_commands.extend([
            BotCommand(command='/help', description='Help on using the bot'),
            BotCommand(command='/echo', description='Get status of the bot'),
            BotCommand(command='/list_models', description='List models'),
            BotCommand(command='/change_model', description='Change model'),
            BotCommand(command='/pull_model', description='Pull model'),
            BotCommand(command='/remove_model', description='Remove model'),
            BotCommand(command='/month_total', description='Show total spent for the current month'),
            BotCommand(command='/week_total', description='Show total spent for the current week'),
            BotCommand(command='/today_total', description='Show total spent for today'),
            BotCommand(command='/last_expenses', description='Show last 10 expenses'),
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


def __init__( approved_users_param: list[int], administrator_user_ids_param: list[int], ollama_host_param: str):
    # global ollama_state
    global approved_users
    global administrator_user_ids
    global ollama_host
    # ollama_state = ollama_state_param
    approved_users = approved_users_param
    administrator_user_ids = administrator_user_ids_param
    ollama_host = ollama_host_param


# Initialize module-level router
router = Router()


def is_approved(message: Message):
    """
    Check if the current user is an approved user.

    Arguments:
    ==========
    message: The message to be processed.
    """
    return (message.from_user.id in approved_users)

# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def start(message: Message,bot: Bot):
    """
    Informs the user about its version.

    Arguments:
    ==========
    message: The message to be processed.
    """
    response_text = escape_md("You are not an Approved!")
    if not is_approved(message):
        await message.reply(response_text)
        return None

    # await get_main_menu_commands(is_admin)
    main_menu_commands = get_main_menu_commands(is_admin(message))
    await bot.set_my_commands(main_menu_commands)
    # print (f"[Info] this is status of is_admin from start {is_admin(message)}")
    await message.answer(escape_md(f"Welcome! Admin status has been accepted, please close application and open again to see the all options.\n\n"
                                  f"Current model: {get_current_model()}\n"),)
    # await message.answer(
    #     # text=LEXICON_RU['/start'],
    #     text=constants.WELCOME_MESSAGE,
    #     parse_mode="Markdown",
    # )

# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands='help'))
async def help(message: Message):
    """
    Informs the user about its commands.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return None

    await message.answer(
        # text=LEXICON_RU['/help'],
        text=constants.HELP_MESSAGE,
        parse_mode="Markdown",
    )


from datetime import datetime
# Parse receipt items from the response content
# and format them for Telegram.
# If the date is missing or 'N/A', it uses the current timestamp in 'YYYY-MM-DD HH:MM' format.
# It also stores the parsed items in a global cache for later use, keyed by message ID.
# Unwanted item names are filtered out based on a predefined list.
# The function returns a formatted string of items, or an error message if parsing fails.
def parse_receipt_items(response_content: str, message_id: int = None) -> str:
    """
    Extract JSON from a string, parse, and format items for Telegram.
    Adds 'Azn' currency to each total_price.
    If date is missing or 'N/A', uses current timestamp in 'YYYY-MM-DD HH:MM' format.
    Also stores the parsed items in parsed_response_cache[message_id] if message_id is provided.
    Filters out unwanted item names.
    """
    import json
    # Import the unwanted item names in responce to user from a separate module
    from .unwanted_names import UNWANTED_ITEM_NAMES
    global parsed_response_cache
    try:
        # Find the first '{' and last '}'
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in response.")
        json_str = response_content[start:end+1]
        data = json.loads(json_str)
        items = data.get("items", [])

        # Filter out unwanted items by name (case-insensitive, strip spaces)
        filtered_items = [
            item for item in items
            if item.get("name", "").strip().upper() not in UNWANTED_ITEM_NAMES
        ]

        # Store filtered items for later use (for NocoDB)
        if message_id is not None:
            parsed_response_cache[message_id] = filtered_items

        if not filtered_items:
            return "No items found in receipt."
        lines = ["Items found:"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in filtered_items:
            name = item.get("name", "")
            total_price = item.get("total_price", "")
            date = item.get("date", "")
            if not date or date == "N/A":
                date = now_str
            if total_price:
                total_price = f"{total_price} AZN"
            lines.append(f"- {name}: {total_price} -- {date}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not parse JSON: {str(e)}\n\nRaw response:\n{response_content}"


@router.callback_query(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
async def handle_approval_callback(callback_query, bot: Bot):
    # Expecting: action_responseMsgId_photoMsgId
    action, response_msg_id, photo_msg_id = callback_query.data.split("_", 2)
    chat_id = callback_query.message.chat.id
    global parsed_response_cache

    if action == "approve":
        items = parsed_response_cache.pop(int(response_msg_id), None)
        if items:
            try:
                from datetime import datetime
                total_sum = 0.0
                for item in items:
                    # Ensure date is present
                    if not item.get("date") or item.get("date") == "N/A":
                        item["date"] = datetime.now().strftime("%d-%m-%Y %H:%M")
                    # Replace dots with dashes in date
                    item["date"] = item["date"].replace('.', '-')
                    # Remove seconds if present (keep only up to minutes)
                    if len(item["date"]) > 16 and ":" in item["date"]:
                        # e.g. "13-06-2025 14:03:49" -> "13-06-2025 14:03"
                        item["date"] = item["date"][:16]
                    # Set unique_id to day from date
                    try:
                        # Try to parse the date and extract the day
                        dt = datetime.strptime(item["date"], "%d-%m-%Y %H:%M")
                        item["unique_id"] = str(dt.day)
                    except Exception:
                        # Fallback: use today's day if parsing fails
                        item["unique_id"] = str(datetime.now().day)
                    # Safely add total_price if it's a number
                    try:
                        total_sum += float(item.get("total_price", 0))
                    except (ValueError, TypeError):
                        pass
                    store_receipt_items(item)
                await bot.send_message(
                    chat_id,
                    f"approved and stored in NocoDB\nTotal sum : {str(f'{total_sum:.2f}').replace('.', ',')} AZN"
                )
            except Exception as e:
                await bot.send_message(chat_id, f"Error storing items: {e}")
        else:
            await bot.send_message(chat_id, "No data found for approval")
        # delete the photo message after approval
        await bot.delete_message(chat_id, int(photo_msg_id))
    elif action == "reject":
        parsed_response_cache.pop(int(response_msg_id), None)
        await bot.send_message(chat_id, "Rejected, please upload new picture")

    # Delete the bot's response message and the original photo message
    await bot.delete_message(chat_id, int(response_msg_id))
    # await bot.delete_message(chat_id, int(photo_msg_id))
    await callback_query.answer()

# Этот хэндлер срабатывает на команду /month_total и /week_total
from noco_client import get_month_total_price, get_week_total_price_list, get_table, BASE_ID

@router.message(Command(commands='month_total'))
async def month_total(message: Message, bot: Bot):
    if not is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return
    total = get_month_total_price()
    await message.reply(
        escape_md(f"Total for this month: {str(f'{total:.2f}').replace('.', ',')} AZN"),
        parse_mode="Markdown"
    )

@router.message(Command(commands='week_total'))
async def week_total(message: Message, bot: Bot):
    if not is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return
    # Get current month table name and id
    table_name = f"items_{datetime.now().strftime('%Y_%m')}"
    table = get_table(BASE_ID, table_name)
    if not table:
        await message.reply(escape_md("No data for this week."), parse_mode="Markdown")
        return
    table_id = table["id"]
    week_sum = get_week_total_price_list(table_id)
    await message.reply(
        escape_md(f"Total for this week: {str(f'{week_sum:.2f}').replace('.', ',')} AZN"),
        parse_mode="Markdown"
    )

@router.message(Command(commands='today_total'))
async def today_total(message: Message, bot: Bot):
    if not is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return
    # total = get_today_total_price()
    today_total1 = get_today_total_price()
    today_date = datetime.now().strftime('%Y-%m-%d')

    if today_total1 == 0:
        await message.reply(escape_md(f"Today ({today_date}) no expenses yet"), parse_mode="Markdown")
        return

    month_total = get_month_total_price()

    result_message = (f"Today's expenses ({today_date}):\n"
            f"Total — {today_total1:.2f} AZN\n\n"
            f"This month total: {month_total:.2f} AZN\n"
            f"Use /week_total for weekly stats")

    await message.reply(
        escape_md(result_message),
        parse_mode="Markdown"
    )

@router.message(Command(commands='last_expenses'))
async def last_expenses(message: Message, bot: Bot):
    """Handler for /last command to show recent expenses"""
    if not is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return
    
    expenses = get_last_expenses(10)
    
    if not expenses:
        await message.reply(escape_md("No recent expenses found."), parse_mode="MarkdownV2")
        return
    
    # Format the expenses for display
    lines = ["Last 10 expenses:"]
    for expense in expenses:
        name = expense.get("name", "Unknown")
        amount = expense.get("amount", 0)
        date = expense.get("date", "No date")
        lines.append(f"• {name}: {amount:.2f} AZN - {date}")
    
    result_message = "\n".join(lines)
    
    await message.reply(
        escape_md(result_message),
        parse_mode="MarkdownV2"
    )


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    """Handle photo messages and process them with vision model"""
    if not is_approved(message):
        await message.reply(escape_md("You are not an Approved!"))
        return None

    # Get the largest photo
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_stream = await bot.download(file.file_id)
    image_bytes = image_stream.read()
    global ollama_state, parsed_response_cache

    # Save image to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name


    # 1. Inform user that connection is being checked
    response_message = await message.reply("Checking Ollama connection...", parse_mode="Markdown")
    # 2. Check if Ollama is reachable
    async with aiohttp.ClientSession() as session:
        async with session.get(ollama_host, timeout=10) as response:
            status = response.status
            # await message.answer(
            #     text=f"Ollama connection test returned status code: {status}",
            #     parse_mode="Markdown",
            # )
            # 3. Edit the "Please wait..." message with the parsed bill
            await bot.edit_message_text(
                chat_id=response_message.chat.id,
                message_id=response_message.message_id,
                text=f"Ollama connection test returned status code: {status}",
                parse_mode="Markdown",
            )
            time.sleep(2)  # Give some time for the user to read the message
            await bot.edit_message_text(
                chat_id=response_message.chat.id,
                message_id=response_message.message_id,
                text="Please wait, processing your bill it could take couple minutes depend on the task...\n AI could make mistakes, please check the result carefully.",
                # text="Please wait, processing your bill it could take couple minutes depend on the task...",
                parse_mode="Markdown",
            )
    # 1. Immediately reply with a "Please wait..." message
    # response_message = await message.reply("Please wait, processing your bill it could take couple minutes depend on the task...", parse_mode="Markdown")
    try:
        response = ollama_vision(RECEIPT_PARSER_PROMPT, tmp_path)

        # 2. Do your processing (e.g., OCR, parsing, etc.)
        parsed_text = parse_receipt_items(response["message"]["content"], response_message.message_id)
        response_text = escape_md(parsed_text)
        print (f"[! Info] this is response from ollama {response_text}")
        # 3. Delete the temporary file
        os.remove(tmp_path)

        # Build inline keyboard, which will delete image and approve/reject the response
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Approve",
                        callback_data=f"approve_{response_message.message_id}_{message.message_id}"
                    ),
                    InlineKeyboardButton(
                        text="Reject",
                        callback_data=f"reject_{response_message.message_id}_{message.message_id}"
                    ),
                ]
            ]
        )

        # Edit the response message with the parsed text and keyboard
        await bot.edit_message_text(
            chat_id=response_message.chat.id,
            message_id=response_message.message_id,
            text=parsed_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except httpx.ReadTimeout:
        await response_message.edit_text(
            text="⏰ Ollama server timed out, try again later or with a smaller image",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        # Use MarkdownV2 and escape_md for error text
        await response_message.edit_text(
            text=f"Error while sending processing message:\n{escape_md(str(e))}",
            parse_mode="MarkdownV2"
        )

# Build the LLM prompt for the user question
def build_llm_prompt(user_question, data):
    summary_prompt =  (
        "You are an expert assistant. Here is the purchase data for this month in JSON format:\n\n"
        f"{json.dumps(data, indent=2)}\n\n"
        "Analyze this data and answer the following question:\n"
        f"{user_question}\n"
        "If you need to calculate totals, group by item, or find trends, do so using the provided data only."
    )

    summary = ollama_state.client.chat(
        model=ollama_state.model,
        messages=[
            {"role": "user", "content": summary_prompt},
        ],
    )["message"]["content"]

    return summary

@router.message()
# @router.message(Command(commands='think'))
async def basic_inference(message: Message):
    """
    Performs inference on the given message.

    Arguments:
    ==========
    message: The message to be processed.
    """
    if not is_approved(message):
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
        text="Please wait, GenAI now processing your query...", parse_mode="Markdown"
    )

    # 1. Ask LLM to return a JSON action if it detects a data request
    # llm_prompt = (
    #     "If the user asks for report or data of items total price, respond ONLY with a JSON object like "
    #     '{"action": "get_week_total_price"} or {"action": "get_month_total_price"}. or {"action": "custome_request"}. '
        #  "If the user provides item data in this format, respond ONLY with a JSON object like "
        # '{"action": "add_item", "item": {...}}. '
    #     "Otherwise, answer normally. User message: " + query
    # )
    llm_prompt = (
        "If the user asks to add an item manually, respond ONLY with a JSON object like "
        '{"action": "add_item_example", "example": "name: Cola, \nquantity: 2, \nunit_price: 1.5, \ndate: 22-06-2025 14:30, \ntotal_price: 3.0" }. '
        "If the user asks for a report or data about total price for the week, respond ONLY with a JSON object like "
        '{"action": "get_week_total_price"}. '
        "If the user asks for a report or data about total price for the month, respond ONLY with a JSON object like "
        '{"action": "get_month_total_price"}. '
        "If the user asks for a custom analysis (for example: top items by price, most purchased items, spending trends, etc.), "
        "respond ONLY with a JSON object like "
        '{"action": "custom_request", "request": "<user_request_description>"}. '
        "Otherwise, answer normally. User message: " + query
    )

    llm_response = ollama_chat(llm_prompt)
    # chat_id = message.chat.id
    # response_text = ollama_chat_mem(query, str(chat_id))
    # llm_response = response_text


    # 2. Try to parse as JSON action
    try:
        action_obj = json.loads(llm_response)
        if isinstance(action_obj, dict) and "action" in action_obj:
            action = action_obj["action"]
            # print(f"[Info] This is action object from LLM: {action}")
            if action == "get_week_total_price":
                # Call your NocoDB function
                table_name = f"items_{datetime.now().strftime('%Y_%m')}"
                table = get_table(BASE_ID, table_name)
                if not table:
                    await response_message.edit_text(
                        escape_md("No data for this week."), parse_mode="MarkdownV2"
                    )
                    return
                table_id = table["id"]
                week_sum = get_week_total_price_list(table_id)
                # week_sum = sum(prices)
                # Ask LLM to summarize
                summary_prompt = (
                    f"Summarize in one short sentence: The total price for this week is {week_sum:.2f} AZN."
                )
                summary = ollama_chat(summary_prompt)
                await response_message.edit_text(
                    escape_md(summary), parse_mode="MarkdownV2"
                )
                # print(f"[Info] This is week total price: {week_sum}")
                return
            elif action == "get_month_total_price":
                total = get_month_total_price()
                summary_prompt = (
                    f"Summarize in one short sentence: The total price for this month is {total:.2f} AZN."
                )
                summary = ollama_chat(summary_prompt)
                await response_message.edit_text(
                    escape_md(summary), parse_mode="MarkdownV2"
                )
                # print(f"[Info] This is month total price: {total}")
                return
            elif action == "custom_request":
                data = get_monthly_data()
                request = action_obj.get("request", "No specific request provided")
                # print(f"[Info] This is data from get_monthly_data function: {request}", data)
                report = build_llm_prompt(request, data)
                await response_message.edit_text(
                    escape_md(report), parse_mode="MarkdownV2"
                )
                return
            elif action == "add_item_example":
                # Show the user the example JSON for manual entry
                instruction = "Please provide the item data in this format:\n" + action_obj['example']
                await response_message.edit_text( 
                    escape_md(instruction), parse_mode="MarkdownV2"
                )
                print(f"[Info] This is instruction for user: {instruction}")
                return
            # elif action == "add_item":
            #     item = action_obj["item"]
            #     store_receipt_items(item)
            #     await message.reply("Item added successfully!")
            #     return
            # Add more actions as needed
    except Exception:
        print(f"[Error] Failed to parse LLM response as JSON: {llm_response}")
        pass  # Not a JSON action, fall back to normal LLM response


    # Escape special characters for Markdown
    response_text = escape_md(llm_response)
    print(f"[Info] This is response from ollama: {response_text}")
    await response_message.edit_text(
        text=response_text,
        parse_mode="MarkdownV2",
    )


# async def stream_inference(message: Message):
#     """
#     Performs inference on the given message.

#     Arguments:
#     ==========
#     message: The message to be processed.
#     """
#     if not is_approved(message):
#         await message.reply("You are not an Approved!")
#         return None

#     prev_msg_size: int = 0
#     query: str = get_content(message.text)

#     if query is None:
#         await message.reply(
#             text=constants.MISTAKEN_CLICK,
#             parse_mode="Markdown"
#         )
#         return

#     response_message: Message = await message.reply(
#         text="wait...", parse_mode="Markdown"
#     )
#     message_stream: list[str] = []
#     for message_chunk in ollama_state.client.chat(
#         model=ollama_state.model,
#         messages=[
#             {
#                 "role": "user",
#                 "content": query,
#             },
#         ],
#         stream=True,
#     ):
#         message_stream.append(message_chunk["message"]["content"])
#         cur_msg_size = len(message_stream)

#         # avoid BadRequest
#         if cur_msg_size == prev_msg_size:
#             continue

#         is_message_rounded: bool = (
#             cur_msg_size % ollama_state.message_chunk_size == 0
#         )

#         is_last_chunk: bool = (
#             message_chunk["done"]
#         )

#         if is_message_rounded or is_last_chunk:
#             prev_msg_size = cur_msg_size
#             await response_message.edit_text(
#                 text="".join(message_stream), parse_mode="Markdown"
#             )
#             time.sleep(2)

# Inline query handler
@router.inline_query()
async def inline_query_handler(inline_query: InlineQuery, bot: Bot):
    """
    Handles inline queries.

    Arguments:
    ==========
    inline_query: The inline query to be processed.
    """
    query = inline_query.query
    # query = inline_query.query or "echo"
    
    # Perform inference using Ollama
    response_text = ollama_chat(query)


    # Escape special characters for Markdown
    response_text = escape_md(response_text)

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="AI Response",
            input_message_content=InputTextMessageContent(
                message_text=response_text
            ),
        )
    ]
    await bot.answer_inline_query(inline_query.id, results, cache_time=600, is_personal=True)
    # await bot.answer_inline_query(inline_query.id, results)