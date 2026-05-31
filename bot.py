"""
Content Creator Bot v2 — AI content generation + style learning
Klinik Etika Kota Bharu | Weight Loss | Men's Health | STD

New in v2:
- Writing style learning from Dr. Din's samples (text + screenshot)
- Supabase-backed sample storage
- Automatic style injection into all generations
"""
import os
import json
import logging
from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client, Client

# ─── Config ─────────────────────────────────────────────
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")  # For OCR from screenshots
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

deepseek = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
MODEL = "deepseek-chat"

# Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

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

# ─── Style Injection ────────────────────────────────────
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")

def get_style_samples(limit: int = 3) -> list[str]:
    """Fetch recent writing samples from Supabase. Falls back to local files."""
    # Try Supabase first
    if supabase:
        try:
            resp = supabase.table("writing_samples") \
                .select("content") \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            if resp.data:
                return [r["content"] for r in resp.data]
        except Exception as e:
            logger.warning(f"Supabase fetch failed: {e}")

    # Fallback: load from local samples/ directory
    if os.path.isdir(SAMPLES_DIR):
        files = sorted(
            [f for f in os.listdir(SAMPLES_DIR) if f.endswith('.txt')],
            reverse=True
        )[:limit]
        samples = []
        for f in files:
            path = os.path.join(SAMPLES_DIR, f)
            with open(path) as fh:
                content = fh.read().strip()
                if content:
                    samples.append(content)
        if samples:
            logger.info(f"Loaded {len(samples)} local samples")
            return samples

    return []

def build_system_prompt() -> str:
    """Build full system prompt: BRAND persona + Dr. Din's style samples."""
    samples = get_style_samples()
    if not samples:
        return BRAND

    # Format samples nicely
    samples_text = "\n\n---\n\n".join(
        f"**Contoh gaya penulisan Dr. Din (sample {i+1}):**\n\n{s}"
        for i, s in enumerate(samples)
    )

    return f"{BRAND}\n\n---\n\n## ⚡ GAYA PENULISAN DR. DIN (WAJIB IKUT)\n\nIni adalah contoh-contoh TULISAN SEBENAR Dr. Din. KAU WAJIB TULIS DENGAN GAYA YANG SAMA — phrasing, pacing, humor, word choice, sentence structure — semua kena match:\n\n{samples_text}\n\n---\n\n**ARAHAN PENTING:** Bila kau hasilkan content, TULIS MACAM DR. DIN TULIS sendiri. Bukan generic style, bukan formal. Match betul-betul cara dia susun ayat, pilih perkataan, timing lawak, dan cara dia explain benda complex secara casual."

# ─── Guard ──────────────────────────────────────────────
def is_allowed(update: Update) -> bool:
    if ALLOWED_USER_ID and update.effective_user.id != ALLOWED_USER_ID:
        return False
    return True

# ─── AI Call ────────────────────────────────────────────
async def generate(prompt: str) -> str:
    """Call DeepSeek API with brand persona + style samples injected."""
    system = build_system_prompt()
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

# ─── OCR via Gemini Flash ───────────────────────────────
async def ocr_image(image_url: str) -> str:
    """Extract text from screenshot using Gemini Flash (free tier)."""
    if not GEMINI_KEY:
        return ""
    
    gemini = OpenAI(
        api_key=GEMINI_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    try:
        resp = gemini.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract ALL the text content from this screenshot of a social media post. Return ONLY the extracted text in the original language (Malay/BM rojak). Do not add commentary, labels, or markdown formatting. Just the raw text from the post(s)."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            max_tokens=1000
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Gemini OCR error: {e}")
        return ""

# ─── Sample Management ──────────────────────────────────
async def save_sample(content: str, platform: str = "threads", source: str = "telegram") -> int | None:
    """Save a writing sample to Supabase. Returns the ID or None."""
    if not supabase:
        logger.warning("Supabase not configured — sample not saved")
        return None
    try:
        resp = supabase.table("writing_samples").insert({
            "content": content,
            "platform": platform,
            "source": source
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.error(f"Failed to save sample: {e}")
        return None

async def delete_sample(sample_id: int) -> bool:
    """Delete a writing sample by ID."""
    if not supabase:
        return False
    try:
        resp = supabase.table("writing_samples").delete().eq("id", sample_id).execute()
        return len(resp.data) > 0
    except Exception as e:
        logger.error(f"Failed to delete sample: {e}")
        return False

# ─── Commands ───────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    sample_count = len(get_style_samples(limit=50))
    await update.message.reply_text(
        f"🎨 *Content Creator Bot v2*\n\n"
        f"Aku bantu kau hasilkan content untuk social media — Threads, TikTok, Instagram, semua!\n\n"
        f"🧠 *Style Memory:* {sample_count} sample tulisan Dr. Din\n\n"
        f"📋 *Commands:*\n"
        f"/post \\[topik\\] — Social media post generic\n"
        f"/thread \\[topik\\] — Threads post\n"
        f"/tiktok \\[topik\\] — Skrip TikTok\n"
        f"/caption \\[deskripsi\\] — Kapsyen + hashtag\n"
        f"/idea \\[kategori\\] — Idea content (weight loss|lelaki|std|umum)\n"
        f"/tulis \\[format\\] \\[topik\\] — Custom\n\n"
        f"📝 *Sample Management:*\n"
        f"/sampel \\[teks\\] — Simpan sample tulisan (text)\n"
        f"/sampel_list — Senarai semua sample\n"
        f"/sampel_hapus \\[id\\] — Buang sample\n"
        f"📸 Hantar screenshot Threads/TikTok — Auto OCR & simpan\n\n"
        f"🔹 Contoh:\n"
        f"`/thread tips turun berat lepas raya`\n"
        f"`/sampel Kenapa saya selalu suruh buat resistance training...`\n"
        f"📸 Screenshot post kau → auto belajar gaya kau",
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await update.message.reply_text(
        "📖 *Content Creator Bot v2 — Help*\n\n"
        "*/post [topik]*\nPost generic untuk mana-mana platform.\n\n"
        "*/thread [topik]*\nThreads post — pendek, catchy, BM rojak.\n\n"
        "*/tiktok [topik]*\nSkrip TikTok dengan timestamp, visual cues.\n\n"
        "*/caption [deskripsi]*\nKapsyen + 5-10 hashtag relevan.\n\n"
        "*/idea [kategori]*\n5 idea content fresh. Kategori: weightloss | lelaki | std | umum\n\n"
        "*/tulis [format] [arahan]*\nCustom — kau control sepenuhnya.\n\n"
        "*/sampel [teks]*\nSimpan sample tulisan kau untuk bot belajar gaya.\n\n"
        "*/sampel_list*\nSenarai sample tersimpan.\n\n"
        "*/sampel_hapus [id]*\nBuang sample.\n\n"
        "📸 *Screenshot:* Hantar screenshot post Dr. Din → auto OCR & simpan sebagai sample.\n\n"
        "🔒 Bot ini private — hanya Dr. Din boleh guna.",
        parse_mode="Markdown"
    )

# ─── Content Commands ───────────────────────────────────
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
    prompt = f'Tulis kapsyen Instagram/Facebook untuk posting pasal: "{desc}". Format: kapsyen 2-3 ayat (BM rojak, mesra), diikuti 8-10 hashtag relevan (campur BM & EN). Hashtag spesifik, bukan generic (#kurus #sihat je).'
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

# ─── Sample Management Commands ─────────────────────────
async def cmd_sampel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a writing sample — either from args text or reply-to-message."""
    if not is_allowed(update): return

    content = None
    platform = "threads"
    source = "telegram-text"

    # Check if replying to a message
    if update.message.reply_to_message and update.message.reply_to_message.text:
        content = update.message.reply_to_message.text.strip()
        source = "telegram-reply"
    elif context.args:
        content = " ".join(context.args)
    else:
        await update.message.reply_text(
            "❌ *Cara guna /sampel:*\n\n"
            "1️⃣ Paste teks direct:\n`/sampel Kenapa saya selalu suruh buat resistance training...`\n\n"
            "2️⃣ Reply mesej:\nReply mesej yang ada sample tulisan, taip `/sampel`\n\n"
            "3️⃣ Hantar screenshot:\nUpload screenshot Threads/TikTok → auto OCR",
            parse_mode="Markdown"
        )
        return

    if len(content) < 20:
        await update.message.reply_text("❌ Sample terlalu pendek (min 20 aksara). Bagi content yang cukup supaya AI boleh belajar.")
        return

    sample_id = await save_sample(content, platform, source)
    if sample_id:
        await update.message.reply_text(
            f"✅ Sample #{sample_id} disimpan!\n\n"
            f"📝 *Preview:* {content[:150]}{'...' if len(content) > 150 else ''}\n\n"
            f"🧠 Bot sekarang akan belajar dari sample ni setiap kali generate content.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Gagal simpan sample. Check Supabase connection.")

async def cmd_sampel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all writing samples."""
    if not is_allowed(update): return
    if not supabase:
        await update.message.reply_text("❌ Supabase not connected.")
        return

    try:
        resp = supabase.table("writing_samples") \
            .select("id,content,platform,source,created_at") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()

        if not resp.data:
            await update.message.reply_text("📝 *Tiada sample lagi.*\n\nHantar sample guna:\n• `/sampel [teks]` — paste text\n• 📸 Screenshot post Dr. Din → auto OCR\n• Reply mesej + `/sampel`", parse_mode="Markdown")
            return

        lines = [f"📝 *Semua Sample ({len(resp.data)}):*\n"]
        for r in resp.data:
            date = r["created_at"][:10] if r.get("created_at") else "?"
            preview = r["content"][:80].replace("\n", " ")
            lines.append(f"`#{r['id']}` [{r.get('platform','?')}] {date}\n{preview}...\n")

        # Telegram has message length limit
        text = "\n".join(lines)
        if len(text) > 3800:
            text = text[:3800] + "\n\n... (too many samples, showing first few)"

        text += "\nGuna `/sampel` untuk tambah, `/sampel_hapus [id]` untuk buang."

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_sampel_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a writing sample by ID."""
    if not is_allowed(update): return
    if not context.args:
        await update.message.reply_text("❌ Nyatakan ID sample.\nContoh: `/sampel_hapus 1`\n\nGuna `/sampel_list` untuk tengok ID.", parse_mode="Markdown")
        return

    try:
        sample_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID mesti nombor.")
        return

    ok = await delete_sample(sample_id)
    if ok:
        await update.message.reply_text(f"🗑️ Sample #{sample_id} dibuang!")
    else:
        await update.message.reply_text(f"❌ Sample #{sample_id} tak jumpa atau gagal dibuang.")

# ─── Photo Handler (Screenshot → OCR → Sample) ──────────
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo upload: extract text via Gemini, save as writing sample."""
    if not is_allowed(update): return

    if not GEMINI_KEY:
        await update.message.reply_text(
            "❌ *OCR tak available.*\n\n"
            "Gemini API key belum setup. Untuk tambah sample dari screenshot:\n"
            "1. Dapatkan Gemini API key (free) dari https://aistudio.google.com\n"
            "2. Tambah `GEMINI_API_KEY=...` dalam `.env`\n"
            "3. Restart bot\n\n"
            "Alternatif: guna `/sampel [teks]` untuk paste manual.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("🔍 Mengekstrak teks dari screenshot...")

    # Get the largest photo (last in the array)
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Download the photo
    file_path = f"/tmp/sample_{update.message.message_id}.jpg"
    await file.download_to_drive(file_path)

    # Read and encode as base64 for Gemini
    import base64
    with open(file_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    image_url = f"data:image/jpeg;base64,{img_b64}"

    # OCR
    extracted = await ocr_image(image_url)

    # Clean up
    os.remove(file_path)

    if not extracted or len(extracted) < 20:
        await update.message.reply_text(
            f"❌ Gagal extract text dari screenshot. Result: \"{extracted}\"\n\n"
            f"Cuba lagi dengan gambar yang lebih jelas, atau guna `/sampel [teks]` untuk paste manual.",
            parse_mode="Markdown"
        )
        return

    # Save as sample
    sample_id = await save_sample(extracted, platform="threads", source="telegram-screenshot")
    if sample_id:
        await update.message.reply_text(
            f"✅ Sample #{sample_id} disimpan dari screenshot!\n\n"
            f"📝 *Extracted text:*\n{extracted[:300]}{'...' if len(extracted) > 300 else ''}\n\n"
            f"🧠 Bot sekarang akan belajar dari gaya penulisan ni.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Text berjaya diextract, tapi gagal simpan ke Supabase.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await update.message.reply_text(
        "💡 Nak generate content? Guna:\n"
        "/post • /thread • /tiktok • /caption • /idea • /tulis\n\n"
        "📝 Nak ajar bot gaya kau?\n"
        "/sampel • 📸 Screenshot → auto OCR",
        parse_mode="Markdown"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error}", exc_info=context.error)

# ─── Main ───────────────────────────────────────────────
def main():
    if not supabase:
        logger.warning("⚠️ Supabase NOT configured — writing samples disabled")
    if not GEMINI_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not set — screenshot OCR disabled")

    app = Application.builder().token(TOKEN).build()

    # Content commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("post", cmd_post))
    app.add_handler(CommandHandler("thread", cmd_thread))
    app.add_handler(CommandHandler("tiktok", cmd_tiktok))
    app.add_handler(CommandHandler("caption", cmd_caption))
    app.add_handler(CommandHandler("idea", cmd_idea))
    app.add_handler(CommandHandler("tulis", cmd_tulis))

    # Sample management
    app.add_handler(CommandHandler("sampel", cmd_sampel))
    app.add_handler(CommandHandler("sampel_list", cmd_sampel_list))
    app.add_handler(CommandHandler("sampel_hapus", cmd_sampel_hapus))

    # Photo handler for screenshot OCR
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Text fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_error_handler(error_handler)

    logger.info("Content Creator Bot v2 starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
