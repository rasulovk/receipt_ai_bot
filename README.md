# Receipt AI Bot

Telegram bot for receipt OCR and expense tracking using Ollama AI and NocoDB.

## Features

- 📸 Receipt OCR with AI vision models
- 💾 Automatic expense storage in NocoDB
- 📊 Daily/weekly/monthly reports
- 🤖 AI chat integration
- ➕ Manual item entry
- 🔐 Secure production deployment

## Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.ai) with `llama3.2:latest` and `llama3.2-vision:latest`
- [NocoDB](https://nocodb.com) instance
- Telegram Bot Token from [@BotFather](https://t.me/botfather)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/rasulovk/receipt_ai_bot.git
cd receipt_ai_bot
```

### 2. Configure Environment

Create `.env` file:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
APPROVED_USERS=comma,separated,user,ids

# Ollama
OLLAMA_HOST=http://your-ollama-host:11434
DEFAULT_MODEL=llama3.2:latest
OLLAMA_KEEP_ALIVE=30m

# NocoDB
NOCODB_API_URL=https://your-nocodb.com
NOCODB_API_TOKEN=your_token
NOCODB_BASE_ID=your_base_id

# Docker extra hosts (optional)
EXTRA_HOST_DOMAIN_1=ollama.local
EXTRA_HOST_IP_1=192.168.1.100
EXTRA_HOST_DOMAIN_2=nocodb.local
EXTRA_HOST_IP_2=192.168.1.101
```

### 3. Build & Run

```bash
# Build image
docker compose build --no-cache

# Start container
docker compose up -d

# View logs
docker compose logs -f
```

## NocoDB Setup

1. Create a new base in NocoDB
2. Tables are auto-created monthly as `items_YYYY_MM`
3. Required columns:
   - `uuid` (Primary Key, SingleLineText)
   - `unique_id` (SingleLineText)
   - `name` (SingleLineText)
   - `quantity` (SingleLineText)
   - `unit_price` (Currency, AZN)
   - `total_price` (Currency, AZN)
   - `date` (SingleLineText)

4. Get API token: Settings → API Tokens → Create Token

## Usage

### Commands

- `/start` - Initialize bot
- `/today_total` - Today's expenses
- `/week_total` - Weekly summary
- `/month_total` - Monthly total
- `/last_expenses` - Recent 10 expenses
- `/add_item Coca Cola 2.5AZN` - Add item manually

### Receipt Processing

1. Send receipt photo to bot
2. AI extracts items automatically
3. Review and approve/reject
4. Data stored in NocoDB

## Docker Configuration

**Security Features:**
- Read-only filesystem
- No root privileges (`user: 0:1002`)
- Dropped capabilities
- Tmpfs for temporary files

**Network:**
- Custom bridge network
- DNS configuration support
- Extra hosts mapping

## Development

```bash
# Install dependencies locally
pip install -r requirements.txt

# Run without Docker
python main.py
```

## Tech Stack

- **aiogram** - Telegram Bot framework
- **Ollama** - Local AI inference
- **NocoDB** - Database backend
- **Python 3.10** - Runtime
- **Docker** - Containerization

## License

GPL-3.0 - see LICENSE file

## Author

[rasulovk](https://github.com/rasulovk)

---

⭐ Star this repo if you find it useful!