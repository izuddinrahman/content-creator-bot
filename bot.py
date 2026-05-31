"""
Content Creator Bot — AI content generation for Dr. Din's brand
Klinik Etika Kota Bharu | Weight Loss | Men's Health | STD
"""
import os
import logging
from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ─── Config ─────────────────────────────────────────────
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

deepseek = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"

# ─── Brand Persona ──────────────────────────────────────
BRAND = """Kau adalah content creator AI untuk Dr. Izuddin Rahman, doktor perubatan yang memiliki Klinik Etika di Kota Bharu, Kelantan.

**Personaliti Brand:**
- Nama klinik: Klinik Etika
- Doktor: Dr. Din (mesra, approachable, bukan formal)
- Bahasa: Rojak BM/EN natural — macam kawan cakap, bukan textbook

**Bidang kepakaran:**
1. Weight Loss / Kurus — Mounjaro (tirzepatide), Wegovy/Ozempic (semaglutide), Saxenda
2. Men's Health — Erectile Dysfunction (ED/mati pucuk), Premature Ejaculation (PE/pancut awal)
3. Kesihatan Seksual — STD screening & treatment

**Tone suara:**
- Santai, mesra, kadang lawak tapi professional
- Educate tanpa syok sendiri — macam kawan explain kat kedai kopi
- Gunakan istilah medical bila perlu, tapi explain dalam Bahasa biasa
- Jangan jual ubat secara direct — educate, bukan promote
- Mention "Klinik Etika" atau "Dr. Din" bila natural je, bukan setiap ayat
- Boleh guna emoji (😊💪🔥) sekali sekala

**Target audience:** Lelaki & perempuan Malaysia, umur 25-50, aktif media sosial, peduli kesihatan.

**Platform formats:**
- Threads: pendek, punchy, max 500 aksara, boleh thread (sambung)
- TikTok: script format — [0:00-0:03] aksi/visual → teks voiceover
- Instagram: caption panjang sikit, dengan call to action, hashtag
- Facebook/Generic: format biasa, educational
"""

# ─── Guard ──────────────────────────────────────────────
def is_allowed(update: Update) -> bool:
    if ALLOWED_USER_ID and update.effective_user.id != ALLOWED_USER_ID:
        return False
    return True

# ─── AI Call ────────────────────────────────────────────
async def generate(prompt: str, system: str = None) -> str:
    """Call DeepSeek API for content generation."""
    if not system:
        system = BRAND
    try:
        resp = deepseek.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return f"❌ Ralat AI: {e}"

# ─── Commands ───────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await update.message.reply_text(
        "🎨 *Content Creator Bot*\n\n"
        "Aku bantu kau hasilkan content untuk social media — Threads, TikTok, Instagram, semua!\n\n"
        "📋 *Commands:*\n"
        "/post \\[topik\\] — Social media post generic\n"
        "/thread \\[topik\\] — Threads post\n"
        "/tiktok \\[topik\\] — Skrip TikTok\n"
        "/caption \\[deskripsi\\] — Kapsyen + hashtag\n"
        "/idea \\[kategori\\] — Idea content (weight loss/men's health/STD/umum)\n"
        "/tulis \\[format\\] \\[topik\\] — Custom (bagi arahan spesifik)\n\n"
        "🔹 Contoh:\n"
        "`/thread tips turun berat lepas raya`\n"
        "`/tiktok bahaya STD tak rawat`\n"
        "`/caption sebelum selepas kurus 5kg`\n\n"
        "Guna `/help` untuk lebih detail.",
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await update.message.reply_text(
        "📖 *Content Creator Bot — Help*\n\n"
        "*/post [topik]*\n"
        "Post generic untuk mana-mana platform. Santai & edukatif.\n\n"
        "*/thread [topik]*\n"
        "Threads post — pendek, catchy, boleh bersiri. BM rojak.\n\n"
        "*/tiktok [topik]*\n"
        "Skrip TikTok dengan timestamp, visual cues, voiceover.\n\n"
        "*/caption [deskripsi]*\n"
        "Kapsyen + 5-10 hashtag relevan untuk posting.\n\n"
        "*/idea [kategori]*\n"
        "5 idea content fresh. Kategori: weightloss | lelaki | std | umum\n\n"
        "*/tulis [format] [arahan]*\n"
        "Custom — kau control sepenuhnya. Format: thread/tiktok/caption/post\n\n"
        "🔒 Bot ini private — hanya Dr. Din boleh guna.",
        parse_mode="Markdown"
    )

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text("❌ Nyatakan topik.\nContoh: `/post kebaikan minum air cukup`", parse_mode="Markdown")
        return
    await update.message.reply_text("✍️ Menulis post...")
    prompt = f'Tulis SATU social media post pasal: "{topic}". Format: catchy hook, body educative 2-3 paragraph pendek, call to action. Target: audience Malaysia. Panjang: 100-150 patah perkataan.'
    result = await generate(prompt)
    await update.message.reply_text(result, parse_mode="Markdown")

async def cmd_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text("❌ Nyatakan topik.\nContoh: `/thread mitos diet intermittent fasting`", parse_mode="Markdown")
        return
    await update.message.reply_text("🧵 Menulis Threads...")
    prompt = f'Tulis Threads post (Max 500 aksara) pasal: "{topic}". Style: rojak BM/EN casual, hook kuat kat awal, educate sikit, ending tanya soalan untuk engagement. 1 thread je, bukan siri. Gunakan emoji sekali sekala. Jangan formal.'
    result = await generate(prompt)
    await update.message.reply_text(result, parse_mode="Markdown")

async def cmd_tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text("❌ Nyatakan topik.\nContoh: `/tiktok kenapa lelaki malu jumpa doktor`", parse_mode="Markdown")
        return
    await update.message.reply_text("🎬 Menulis skrip TikTok...")
    prompt = f'''Tulis skrip TikTok (60-90 saat) pasal: "{topic}". Format:
[0:00-0:03] - Hook / perhatian
[masa] - Visual/aksi → Voiceover teks

Guna BM rojak, casual. Voiceover macam kawan cerita. End dengan call to action (follow/comment). Max 15 segmen.'''
    result = await generate(prompt)
    await update.message.reply_text(result, parse_mode="Markdown")

async def cmd_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    desc = " ".join(context.args) if context.args else None
    if not desc:
        await update.message.reply_text("❌ Describe gambar/video.\nContoh: `/caption sebelum selepas rawatan kurus 2 bulan`", parse_mode="Markdown")
        return
    await update.message.reply_text("📸 Menulis kapsyen...")
    prompt = f'Tulis kapsyen Instagram/Facebook untuk posting pasal: "{desc}". Format: kapsyen 2-3 ayat (BM rojak, mesra), diikuti 8-10 hashtag relevan (campur BM & EN). Buat hashtag spesifik, bukan generic (#kurus #sihat je).'
    result = await generate(prompt)
    await update.message.reply_text(result, parse_mode="Markdown")

async def cmd_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    cat = context.args[0].lower() if context.args else "umum"
    cats = {
        "weightloss": "weight loss / kurus / Mounjaro / diet",
        "lelaki": "men's health / ED / mati pucuk / PE / pancut awal",
        "std": "STD / penyakit kelamin / sexual health",
        "umum": "kesihatan umum / klinik / lifestyle"
    }
    if cat not in cats:
        await update.message.reply_text("❌ Kategori: weightloss | lelaki | std | umum\nContoh: `/idea weightloss`", parse_mode="Markdown")
        return
    await update.message.reply_text(f"💡 Jana idea untuk: {cat}...")
    topic = cats[cat]
    prompt = f'Bagi 5 idea content social media untuk klinik kesihatan, fokus pada topik: {topic}. Setiap idea: tajuk catchy + one-liner kenapa best. Format bernombor. Guna BM rojak. Fokus educative + relatable, bukan hard selling.'
    result = await generate(prompt)
    await update.message.reply_text(result, parse_mode="Markdown")

async def cmd_tulis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Guna: `/tulis [format] [arahan]`\n"
            "Format: thread | tiktok | caption | post\n"
            "Contoh: `/tulis thread explain mounjaro untuk beginner`",
            parse_mode="Markdown"
        )
        return
    fmt = args[0].lower()
    arahan = " ".join(args[1:])
    formats = {
        "thread": "Tulis THREADS post (max 500 aksara, BM rojak, catchy hook, educative):",
        "tiktok": "Tulis SKRIP TIKTOK (60-90 saat, format timestamp [0:00-0:03], BM rojak, voiceover santai):",
        "caption": "Tulis KAPSYEN + HASHTAG (2-3 ayat + 8-10 hashtag):",
        "post": "Tulis POST generic (100-150 patah perkataan, BM rojak, educative):"
    }
    prefix = formats.get(fmt, "Tulis content pasal:")
    await update.message.reply_text("✍️ Menulis...")
    prompt = f'{prefix} {arahan}'
    result = await generate(prompt)
    await update.message.reply_text(result, parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    text = update.message.text.strip()
    # If no command prefix, treat as /tulis post
    await update.message.reply_text("💡 Nak generate content? Guna:\n/post • /thread • /tiktok • /caption • /idea • /tulis\n\nAtau taip `/tulis post [arahan]`")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error}", exc_info=context.error)

# ─── Main ───────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("post", cmd_post))
    app.add_handler(CommandHandler("thread", cmd_thread))
    app.add_handler(CommandHandler("tiktok", cmd_tiktok))
    app.add_handler(CommandHandler("caption", cmd_caption))
    app.add_handler(CommandHandler("idea", cmd_idea))
    app.add_handler(CommandHandler("tulis", cmd_tulis))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("Content Creator Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
