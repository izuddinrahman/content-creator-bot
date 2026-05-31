# Content Creator Bot 🎨

AI-powered Telegram bot untuk content creation — Threads, TikTok, Instagram, dan social media posts. Disesuaikan untuk branding Klinik Etika oleh Dr. Izuddin Rahman.

## Commands

| Command | Fungsi |
|---|---|
| `/post [topik]` | Social media post generic |
| `/thread [topik]` | Threads post (pendek, catchy) |
| `/tiktok [topik]` | Skrip TikTok (timestamp + visual cues) |
| `/caption [deskripsi]` | Kapsyen + hashtag |
| `/idea [kategori]` | 5 idea content (weightloss/lelaki/std/umum) |
| `/tulis [format] [arahan]` | Custom — kau control format & content |

## Setup

1. `cp .env.example .env`
2. Isi `TELEGRAM_BOT_TOKEN` dari @BotFather
3. Isi `DEEPSEEK_API_KEY`
4. `pip install -r requirements.txt`
5. `python bot.py`

## Tech Stack

- Python 3.13+
- python-telegram-bot
- DeepSeek API (via OpenAI SDK)
- Private mode (ALLOWED_USER_ID)
