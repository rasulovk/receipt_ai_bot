from telgram_bot import create_bot, run_bot, set_main_menu
from dotenv import load_dotenv
# from handlers import other_handlers, user_handlers
import logging
import os
import asyncio
import noco_client


def main():
    load_dotenv()
    # Initialize the NoCo client to monitor data changes
    noco_client.start_data_monitor_thread()

    # Setup logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(filename)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Check if the token has been given.
    required_values: list[str] = [
        "TELEGRAM_BOT_TOKEN",
    ]
    missing_values: list[str] = [
        value for value in required_values if os.environ.get(value) is None
    ]
    if len(missing_values) > 0:
        logging.error(
            f'The following environment values are missing in your .env: {", ".join(missing_values)}'
        )
        exit()

    # Run the bot.
    asyncio.run(run_bot_instance())


async def run_bot_instance():
    administrator_user_ids = [
        int(user_id) for user_id in os.environ.get("ADMIN_ID", 0).split(",")
    ]
    approved_users = [
        int(user_id) for user_id in os.environ.get("APPROVED_USERS", 0).split(",")
    ]
    bot, dp = create_bot(
        ollama_host=os.environ.get("OLLAMA_HOST", "localhost:11434"),
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        default_model=os.environ.get("DEFAULT_MODEL", "llama3.2:latest"),
        administrator_user_ids=administrator_user_ids,
        message_chunk_size=int(os.environ.get("MESSAGE_CHUNK_SIZE", 5)),
        approved_users=approved_users,
    )
    print("[Info] declared admin user is: " + str(administrator_user_ids))
    # Регистриуем роутеры в диспетчере
    # dp.include_router(user_handlers.router)
    # dp.include_router(other_handlers.router)

    # await set_main_menu(bot, administrator_user_ids,bot_id=bot.id)
    await run_bot(bot, dp, administrator_user_ids,approved_users)


if __name__ == "__main__":
    main()
