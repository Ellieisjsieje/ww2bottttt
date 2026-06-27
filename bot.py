import logging
import asyncio
import httpx
import random
import re
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError
from database import Database
from data import COUNTRIES, EQUIPMENT, INFANTRY, MISSILES, AIR_DEFENSE, INFRASTRUCTURE
from config import BOT_TOKEN, ADMIN_IDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

db = Database()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or db.is_admin(user_id)

def all_admin_ids() -> list:
    return db.get_all_admins()

async def send_long_message(bot, chat_id: int, text: str, parse_mode="Markdown", reply_markup=None):
    MAX = 4000
    parts = []
    while len(text) > MAX:
        split_at = text.rfind("\n", 0, MAX)
        if split_at == -1:
            split_at = MAX
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    parts.append(text)

    for i, part in enumerate(parts):
        try:
            kb = reply_markup if i == len(parts) - 1 else None
            await bot.send_message(
                chat_id=chat_id,
                text=part,
                parse_mode=parse_mode,
                reply_markup=kb
            )
            if len(parts) > 1:
                await asyncio.sleep(0.5)
        except TelegramError as e:
            logger.error(f"send_long_message error: {e}")

def _analyze_strategy(prompt):
    import re
    am = re.search(r"کشور مهاجم: (.+)", prompt)
    tm = re.search(r"کشور هدف: (.+)", prompt)
    sm = re.search(r"استراتژی مهاجم: (.+)", prompt)
    attacker = am.group(1).strip() if am else "مهاجم"
    target   = tm.group(1).strip() if tm else "هدف"
    strategy = sm.group(1).strip() if sm else ""
    strengths, weaknesses = [], []
    pos = [
        (r"هوایی|هواپیما|بمباران", "استفاده از نیروی هوایی مزیت بزرگی است"),
        (r"دریایی|کشتی|ناو",       "کنترل دریا خطوط تدارکاتی دشمن را قطع می‌کند"),
        (r"محاصره",                 "استراتژی محاصره دشمن را تضعیف می‌کند"),
        (r"شبانه|شب",              "حملات شبانه غافلگیری ایجاد می‌کند"),
        (r"متحد|اتحاد|همپیمان",   "داشتن متحد قدرت را چند برابر می‌کند"),
        (r"سریع|برق‌آسا|ناگهان",  "عملیات سریع مزیت تاکتیکی دارد"),
        (r"پشتیبانی|لجستیک",      "توجه به لجستیک نشانه برنامه‌ریزی خوب است"),
    ]
    neg = [
        (r"مستقیم|رویارویی مستقیم", "حمله مستقیم تلفات زیادی دارد"),
        (r"تنها|بدون کمک",           "نداشتن پشتیبانی ریسک بالایی دارد"),
    ]
    for pat, msg in pos:
        if re.search(pat, strategy): strengths.append(msg)
    for pat, msg in neg:
        if re.search(pat, strategy): weaknesses.append(msg)
    if len(strategy) < 30:
        weaknesses += ["استراتژی خیلی کلی و مبهم است", "جزئیات بیشتری نیاز است"]
    elif len(strategy) >= 50:
        strengths.append("استراتژی با جزئیات کافی ارائه شده")
    if not strengths: strengths = ["مهاجم ابتکار عمل را در دست دارد"]
    if not weaknesses: weaknesses = ["باید به واکنش دفاعی دشمن توجه شود"]
    verdict = "✅ این استراتژی منطقی و قابل اجرا است." if len(strengths) >= len(weaknesses) else "⚠️ این استراتژی نیاز به بازنگری دارد."
    out  = f"🎖️ *تحلیل استراتژی {attacker} برای حمله به {target}*\n\n{verdict}\n\n"
    out += "✅ *نقاط قوت:*\n" + "".join(f"• {s}\n" for s in strengths)
    out += "\n⚠️ *نقاط ضعف:*\n" + "".join(f"• {w}\n" for w in weaknesses)
    out += "\n💡 موفقیت به اجرای دقیق و انعطاف‌پذیری بستگی دارد."
    return out


def _analyze_war(prompt):
    import re, random
    am = re.search(r"🗡️ مهاجم: (.+)", prompt)
    dm = re.search(r"🛡️ مدافع: (.+)", prompt)
    attacker = am.group(1).strip() if am else "مهاجم"
    defender = dm.group(1).strip() if dm else "مدافع"

    def inv_score(text):
        nums = re.findall(r"(\d+)\s*(?:عدد|جوخه)", text)
        return max(sum(int(n) for n in nums), 1)

    def strat_score(text):
        kws = ["هوایی","دریایی","محاصره","شبانه","متحد","بمباران","پشتیبانی"]
        return len(text)//20 + sum(2 for k in kws if k in text)

    a_inv   = re.search(r"🗡️.*?موجودی نظامی:(.*?)استراتژی:", prompt, re.DOTALL)
    d_inv   = re.search(r"🛡️.*?موجودی نظامی:(.*?)استراتژی:", prompt, re.DOTALL)
    a_strat = re.search(r"🗡️.*?استراتژی:(.*?)🛡️", prompt, re.DOTALL)
    d_strat = re.search(r"🛡️.*?استراتژی:(.*?)(?:تمام|\Z)", prompt, re.DOTALL)

    a_score = inv_score(a_inv.group(1) if a_inv else "") + strat_score(a_strat.group(1) if a_strat else "") + random.randint(0,5)
    d_score = inv_score(d_inv.group(1) if d_inv else "") + strat_score(d_strat.group(1) if d_strat else "") + random.randint(0,5)

    if abs(a_score - d_score) <= 3:
        return (f"⚔️ *تحلیل نبرد: {attacker} vs {defender}*\n\n"
                f"📊 امتیاز:\n🗡️ {attacker}: {a_score}\n🛡️ {defender}: {d_score}\n\n"
                f"🤝 *نتیجه: مساوی!* هر دو طرف قدرت برابری داشتند.\n💀 خسارات سنگین برای هر دو طرف.")

    if a_score > d_score:
        winner, loser, side = attacker, defender, "🗡️ مهاجم"
        reasons = ["برتری تجهیزات نظامی", "استراتژی تهاجمی مؤثر", "اجرای موفق عملیات"]
    else:
        winner, loser, side = defender, attacker, "🛡️ مدافع"
        reasons = ["دفاع محکم و سازمان‌یافته", "مقاومت موفق در برابر تهاجم", "استفاده بهینه از موضع دفاعی"]

    cw, cl = random.randint(15,35), random.randint(45,75)
    out  = f"⚔️ *تحلیل نهایی: {attacker} vs {defender}*\n\n"
    out += f"📊 امتیاز:\n🗡️ {attacker}: {a_score}\n🛡️ {defender}: {d_score}\n\n"
    out += f"🏆 *برنده: {side} ({winner})*\n\n"
    out += "📋 دلایل پیروزی:\n" + "".join(f"• {r}\n" for r in reasons)
    out += f"\n💀 تلفات:\n• {winner}: {cw}%\n• {loser}: {cl}%\n🏳️ {loser} تسلیم شد."
    return out


async def call_gemini(prompt: str) -> str:
    """تحلیل محلی — بدون نیاز به API خارجی"""
    if "قاضی یک جنگ" in prompt:
        return _analyze_war(prompt)
    return _analyze_strategy(prompt)


async def notify_admins_war_ready(bot, war_id: int, war: dict):
    attacker = db.get_player(war["attacker_id"])
    defender = db.get_player(war["defender_id"])
    if not attacker or not defender:
        return
    a_info = COUNTRIES.get(attacker["country"], {})
    d_info = COUNTRIES.get(defender["country"], {})

    text = (
        f"✅ *جنگ #{war_id} آماده تحلیل است!*\n\n"
        f"🗡️ مهاجم: {a_info.get('flag','')} {a_info.get('name_fa','')}\n"
        f"📋 استراتژی مهاجم:\n{war['attacker_strategy']}\n\n"
        f"🛡️ مدافع: {d_info.get('flag','')} {d_info.get('name_fa','')}\n"
        f"📋 استراتژی مدافع:\n{war['defender_strategy']}\n\n"
        "برای تحلیل دکمه زیر را بزنید:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⚔️ تحلیل جنگ #{war_id}", callback_data=f"admin_analyze_direct_{war_id}")]
    ])
    for admin_id in all_admin_ids():
        try:
            await send_long_message(bot, admin_id, text, reply_markup=kb)
        except Exception:
            pass

def _get_country_name(player) -> str:
    if not player or not player.get("country"):
        return "ناشناس"
    return COUNTRIES.get(player["country"], {}).get("name_fa", "ناشناس")

def _get_country_flag(player) -> str:
    if not player or not player.get("country"):
        return ""
    return COUNTRIES.get(player["country"], {}).get("flag", "")

def _calc_spy_squads_needed(attacker_power: int, defender_power: int) -> tuple:
    """تعداد جوخه‌های لازم و درصد موفقیت"""
    if defender_power == 0 or defender_power < attacker_power:
        return 1, 70
    ratio = defender_power / max(attacker_power, 1)
    if ratio <= 2:
        return 3, 60
    elif ratio <= 5:
        return 7, 45
    else:
        return 15, 30

# ─────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    text = (
        "🌍 *به بازی جنگ جهانی دوم خوش آمدید!*\n\n"
        "📢 *ابتدا در کانال‌های ما عضو شوید:*\n"
        "• @your\\_channel\\_1\n"
        "• @your\\_channel\\_2\n\n"
        "بعد از عضویت دکمه زیر را بزنید 👇"
    )
    kb = [[InlineKeyboardButton("عضو شدم، ادامه بده", callback_data="joined")]]
    await update.message.reply_text(text, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))

async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_country_list(query)

# ─────────────────────────────────────────────
#  لیست کشورها
# ─────────────────────────────────────────────
async def show_country_list(query):
    user_id = query.from_user.id
    player  = db.get_player(user_id)
    taken   = db.get_taken_countries()

    allies_text   = "🟢 *متفقین (Allies):*\n"
    axis_text     = "\n🔴 *محور (Axis):*\n"
    neutral_text  = "\n⚪ *بی‌طرف (Neutral):*\n"
    occupied_text = "\n🟡 *اشغال‌شده (Occupied):*\n"

    for code, info in COUNTRIES.items():
        vip_mark = "💯" if info["vip"] else ""
        status   = "🔒" if code in taken else ""
        line     = f"{info['flag']} {info['name_fa']} {vip_mark} {status}\n"
        faction  = info["faction"]
        if faction == "allies":
            allies_text   += line
        elif faction == "axis":
            axis_text     += line
        elif faction == "neutral":
            neutral_text  += line
        else:
            occupied_text += line

    text  = allies_text + axis_text + neutral_text + occupied_text
    text += "\n💡 برای انتخاب کشور دکمه زیر را بزنید:"

    if player and player["country"]:
        text += f"\n\n🏳️ کشور فعلی شما: *{COUNTRIES[player['country']]['name_fa']}*"
        kb = [[InlineKeyboardButton("📊 داشبورد من", callback_data="dashboard")]]
    else:
        kb = [[InlineKeyboardButton("🌍 انتخاب کشور", callback_data="select_country")]]

    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

# ─────────────────────────────────────────────
#  انتخاب کشور
# ─────────────────────────────────────────────
async def select_country_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if player and player["country"]:
        await query.edit_message_text("❌ شما قبلاً کشور انتخاب کرده‌اید!")
        return

    taken        = db.get_taken_countries()
    vip_approved = db.is_vip_approved(user_id)
    buttons      = []

    for code, info in COUNTRIES.items():
        if code in taken:
            continue
        if info["vip"] and not vip_approved:
            continue
        btn_text = f"{info['flag']} {info['name_fa']} {'💯' if info['vip'] else ''}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"choose_{code}")])

    if not buttons:
        await query.edit_message_text("❌ هیچ کشور آزادی وجود ندارد!")
        return

    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="joined")])
    await query.edit_message_text("🌍 *کشور خود را انتخاب کنید:*",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    code    = query.data.replace("choose_", "")

    if code in db.get_taken_countries():
        await query.edit_message_text("❌ این کشور قبلاً انتخاب شده!")
        return

    info   = COUNTRIES[code]
    budget = 250_000_000 if info["vip"] else 200_000_000
    db.set_player_country(user_id, code, budget)

    # پیام خوشامد برای بازیکن جدید
    welcome_text = (
        f"🎖️ *{info['flag']} {info['name_fa']}* انتخاب شد!\n\n"
        f"💰 بودجه اولیه: *{budget:,}$*\n\n"
        f"{'─'*30}\n"
        "📖 *راهنمای سریع بازی:*\n"
        "🏗️ زیرساخت بسازید تا درآمد روزانه داشته باشید\n"
        "⚔️ تجهیزات نظامی بخرید تا قدرت بگیرید\n"
        "🤝 با کشورهای دیگر اتحاد بسازید\n"
        "⚔️ برای اعلام جنگ از داشبورد اقدام کنید\n"
        "🕵️ جوخه جاسوسی بخرید تا عملیات انجام دهید\n\n"
        "به داشبورد خوش آمدید! 🎮"
    )
    kb = [[InlineKeyboardButton("📊 داشبورد", callback_data="dashboard")]]
    await query.edit_message_text(welcome_text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

# ─────────────────────────────────────────────
#  داشبورد
# ─────────────────────────────────────────────
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    info = COUNTRIES[player["country"]]
    days = db.get_days_since_joined(user_id)
    alliance = db.get_player_alliance(user_id)
    alliance_text = f"🤝 اتحاد: *{alliance['name']}*\n" if alliance else ""
    spy_enabled = db.get_config("spy_enabled", "0") == "1"

    text = (
        f"🏛️ *داشبورد {info['flag']} {info['name_fa']}*\n"
        f"{'─'*30}\n"
        f"💰 بودجه: *{player['budget']:,}$*\n"
        f"📈 درآمد روزانه: *{player['daily_income']:,}$*\n"
        f"😊 رضایت مردم: *{player['satisfaction']}%*\n"
        f"📅 روزهای عضویت: *{days} روز*\n"
        f"{alliance_text}"
        f"{'─'*30}\n"
    )

    spy_btn = [InlineKeyboardButton("🕵️ جاسوسی", callback_data="spy_menu")] if spy_enabled else []

    rows = [
        [InlineKeyboardButton("🏗️ خرید زیرساخت",   callback_data="buy_infra"),
         InlineKeyboardButton("⚔️ خرید تجهیزات",   callback_data="buy_equip")],
        [InlineKeyboardButton("👥 خرید نیرو",        callback_data="buy_infantry"),
         InlineKeyboardButton("🚀 خرید موشک",        callback_data="buy_missile")],
        [InlineKeyboardButton("🛡️ خرید پدافند",     callback_data="buy_air_defense"),
         InlineKeyboardButton("📦 انبار من",          callback_data="my_inventory")],
        [InlineKeyboardButton("🌍 لیست کشورها",      callback_data="country_list"),
         InlineKeyboardButton("💸 انتقال",            callback_data="transfer_menu")],
        [InlineKeyboardButton("⚔️ اعلام جنگ",        callback_data="war_declare"),
         InlineKeyboardButton("🤝 دوستان",            callback_data="friends_menu")],
        [InlineKeyboardButton("🏆 رتبه‌بندی",         callback_data="leaderboard_menu"),
         InlineKeyboardButton("🛡️ اتحادها",           callback_data="alliance_menu")],
        [InlineKeyboardButton("🔒 استراتژی ضدجاسوسی", callback_data="set_antistrategy"),
         InlineKeyboardButton("📢 بیانیه",            callback_data="bayanie_start")],
    ]
    if spy_btn:
        rows.insert(5, spy_btn)

    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(rows))

# ─────────────────────────────────────────────
#  خرید زیرساخت
# ─────────────────────────────────────────────
async def buy_infra_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    buttons = []
    for item_id, item in INFRASTRUCTURE.items():
        owned = db.get_infra_count(user_id, item_id)
        limit = item["limit"]
        if owned >= limit:
            btn = f"✅ {item['name']} ({owned}/{limit})"
        else:
            btn = f"🏗️ {item['name']} | {item['cost']:,}$ ({owned}/{limit})"
        buttons.append([InlineKeyboardButton(btn, callback_data=f"infra_{item_id}")])

    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    await query.edit_message_text(
        "🏗️ *خرید زیرساخت:*\n💰 بودجه: {:,}$".format(player["budget"]),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def buy_infra_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_id = query.data.replace("infra_", "")
    item    = INFRASTRUCTURE.get(item_id)

    if not item:
        await query.answer("❌ آیتم یافت نشد!", show_alert=True)
        return

    player = db.get_player(user_id)
    owned  = db.get_infra_count(user_id, item_id)

    if owned >= item["limit"]:
        await query.answer("❌ به حداکثر رسیده‌اید!", show_alert=True)
        return
    if player["budget"] < item["cost"]:
        await query.answer(f"❌ بودجه کافی نیست! نیاز: {item['cost']:,}$", show_alert=True)
        return

    db.buy_infra(user_id, item_id, item["cost"], item["income"], item["satisfaction"])
    await query.answer(f"✅ {item['name']} خریداری شد!", show_alert=True)
    await buy_infra_menu(update, context)

# ─────────────────────────────────────────────
#  خرید تجهیزات نظامی
# ─────────────────────────────────────────────
async def buy_equip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    categories = [
        ("🚩 تجهیزات زمینی", "equip_cat_ground"),
        ("✈️ تجهیزات هوایی", "equip_cat_air"),
        ("⚓ تجهیزات دریایی", "equip_cat_naval"),
    ]
    buttons = [[InlineKeyboardButton(n, callback_data=cb)] for n, cb in categories]
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    await query.edit_message_text("⚔️ *دسته‌بندی تجهیزات:*",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def equip_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    cat     = query.data.replace("equip_cat_", "")
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    items   = {k: v for k, v in EQUIPMENT.items() if v["category"] == cat}
    buttons = []
    for item_id, item in items.items():
        owned = db.get_equip_count(user_id, item_id)
        buttons.append([InlineKeyboardButton(
            f"{item['name']} | {item['cost']:,}$ (دارم: {owned})",
            callback_data=f"eqbuy_{item_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="buy_equip")])
    await query.edit_message_text(
        f"⚔️ *لیست تجهیزات:*\n💰 بودجه: {player['budget']:,}$",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def buy_equip_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_id = query.data.replace("eqbuy_", "")
    item    = EQUIPMENT.get(item_id)
    if not item:
        await query.answer("❌ یافت نشد!", show_alert=True)
        return
    player = db.get_player(user_id)
    if player["budget"] < item["cost"]:
        await query.answer(f"❌ بودجه کافی نیست! نیاز: {item['cost']:,}$", show_alert=True)
        return
    db.buy_equipment(user_id, item_id, item["cost"])
    await query.answer(f"✅ {item['name']} خریداری شد!", show_alert=True)

# ─────────────────────────────────────────────
#  خرید نیرو
# ─────────────────────────────────────────────
async def buy_infantry_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)
    spy_enabled = db.get_config("spy_enabled", "0") == "1"
    buttons = []
    for item_id, item in INFANTRY.items():
        if item_id == "spy_squad" and not spy_enabled:
            continue
        owned = db.get_infantry_count(user_id, item_id)
        buttons.append([InlineKeyboardButton(
            f"{item['name']} | {item['cost']:,}$/جوخه (دارم: {owned})",
            callback_data=f"infbuy_{item_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    await query.edit_message_text(
        f"👥 *خرید نیرو:*\n💰 بودجه: {player['budget']:,}$",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def buy_infantry_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_id = query.data.replace("infbuy_", "")
    item    = INFANTRY.get(item_id)
    if not item:
        await query.answer("❌ یافت نشد!", show_alert=True)
        return
    player = db.get_player(user_id)
    if player["budget"] < item["cost"]:
        await query.answer(f"❌ بودجه کافی نیست! نیاز: {item['cost']:,}$", show_alert=True)
        return
    db.buy_infantry(user_id, item_id, item["cost"])
    await query.answer(f"✅ {item['name']} خریداری شد!", show_alert=True)

# ─────────────────────────────────────────────
#  خرید موشک
# ─────────────────────────────────────────────
async def buy_missile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)
    buttons = []
    for item_id, item in MISSILES.items():
        owned = db.get_equip_count(user_id, item_id)
        buttons.append([InlineKeyboardButton(
            f"{item['name']} | {item['cost']:,}$ (دارم: {owned})",
            callback_data=f"msbuy_{item_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    await query.edit_message_text(
        f"🚀 *خرید موشک:*\n💰 بودجه: {player['budget']:,}$",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def buy_missile_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_id = query.data.replace("msbuy_", "")
    item    = MISSILES.get(item_id)
    if not item:
        await query.answer("❌ یافت نشد!", show_alert=True)
        return
    player = db.get_player(user_id)
    if player["budget"] < item["cost"]:
        await query.answer("❌ بودجه کافی نیست!", show_alert=True)
        return
    db.buy_equipment(user_id, item_id, item["cost"])
    await query.answer(f"✅ {item['name']} خریداری شد!", show_alert=True)

# ─────────────────────────────────────────────
#  خرید پدافند
# ─────────────────────────────────────────────
async def buy_air_defense_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)
    buttons = []
    for item_id, item in AIR_DEFENSE.items():
        owned = db.get_equip_count(user_id, item_id)
        buttons.append([InlineKeyboardButton(
            f"{item['name']} | {item['cost']:,}$ (دارم: {owned})",
            callback_data=f"adbuy_{item_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    await query.edit_message_text(
        f"🛡️ *خرید پدافند هوایی:*\n💰 بودجه: {player['budget']:,}$",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def buy_air_defense_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    item_id = query.data.replace("adbuy_", "")
    item    = AIR_DEFENSE.get(item_id)
    if not item:
        await query.answer("❌ یافت نشد!", show_alert=True)
        return
    player = db.get_player(user_id)
    if player["budget"] < item["cost"]:
        await query.answer("❌ بودجه کافی نیست!", show_alert=True)
        return
    db.buy_equipment(user_id, item_id, item["cost"])
    await query.answer(f"✅ {item['name']} خریداری شد!", show_alert=True)

# ─────────────────────────────────────────────
#  انبار من
# ─────────────────────────────────────────────
async def my_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    inventory = db.get_full_inventory(user_id)
    days      = db.get_days_since_joined(user_id)
    power     = db.get_military_power(user_id)
    text      = f"📦 *انبار {COUNTRIES[player['country']]['name_fa']}:*\n{'─'*25}\n"

    if not inventory:
        text += "❌ انبار خالی است!\n"
    else:
        for item_name, count in inventory.items():
            text += f"• {item_name}: {count} عدد\n"

    text += f"\n💰 بودجه: {player['budget']:,}$"
    text += f"\n📈 درآمد روزانه: {player['daily_income']:,}$"
    text += f"\n😊 رضایت: {player['satisfaction']}%"
    text += f"\n⚔️ قدرت نظامی: {power:,}$"
    text += f"\n📅 روزهای عضویت: {days} روز"

    kb = [[InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")]]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

# ─────────────────────────────────────────────
#  انتقال پول/تجهیزات
# ─────────────────────────────────────────────
async def transfer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("💸 انتقال پول (آیدی عددی)",    callback_data="transfer_money")],
        [InlineKeyboardButton("💸 انتقال پول (نام کشور)",     callback_data="transfer_money_country")],
        [InlineKeyboardButton("💸 انتقال پول (یوزرنیم)",      callback_data="transfer_money_username")],
        [InlineKeyboardButton("⚔️ انتقال تجهیزات (آیدی)",    callback_data="transfer_equip")],
        [InlineKeyboardButton("⚔️ انتقال تجهیزات (نام کشور)", callback_data="transfer_equip_country")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")],
    ]
    await query.edit_message_text(
        "💸 *منوی انتقال:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def transfer_money_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data
    if mode == "transfer_money":
        context.user_data["transfer_step"] = "money_target_id"
        prompt = "💸 *انتقال پول*\n\nآیدی عددی تلگرام گیرنده را بفرستید:"
    elif mode == "transfer_money_country":
        context.user_data["transfer_step"] = "money_target_country"
        prompt = "💸 *انتقال پول*\n\nنام کشور گیرنده را به فارسی بفرستید (مثال: آلمان نازی):"
    else:
        context.user_data["transfer_step"] = "money_target_username"
        prompt = "💸 *انتقال پول*\n\nیوزرنیم گیرنده را بفرستید (مثال: @username):"
    await query.edit_message_text(prompt, parse_mode="Markdown")

async def transfer_equip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data
    if mode == "transfer_equip":
        context.user_data["transfer_step"] = "equip_target_id"
        prompt = "⚔️ *انتقال تجهیزات*\n\nآیدی عددی تلگرام گیرنده را بفرستید:"
    else:
        context.user_data["transfer_step"] = "equip_target_country"
        prompt = "⚔️ *انتقال تجهیزات*\n\nنام کشور گیرنده را بفرستید:"
    await query.edit_message_text(prompt, parse_mode="Markdown")

def _resolve_target(text: str, step: str):
    if "id" in step:
        try:
            return db.get_player(int(text))
        except ValueError:
            return None
    elif "country" in step:
        for code, info in COUNTRIES.items():
            if text.strip() in info["name_fa"]:
                return db.get_player_by_country(code)
        return None
    elif "username" in step:
        return db.get_player_by_username(text)
    return None

async def handle_transfer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step    = context.user_data.get("transfer_step")
    if not step:
        return

    text = update.message.text.strip()

    if step in ("money_target_id", "money_target_country", "money_target_username"):
        target = _resolve_target(text, step)
        if not target or not target["country"]:
            await update.message.reply_text("❌ کاربر/کشور یافت نشد یا کشور ندارد!")
            context.user_data.clear()
            return
        context.user_data["transfer_target"] = target["user_id"]
        context.user_data["transfer_step"]   = "money_amount"
        country_name = COUNTRIES[target["country"]]["name_fa"]
        await update.message.reply_text(f"گیرنده: *{country_name}*\n\nمقدار پول (دلار) را بفرستید:",
                                        parse_mode="Markdown")

    elif step == "money_amount":
        try:
            amount = int(text.replace(",", ""))
            player = db.get_player(user_id)
            if amount <= 0:
                await update.message.reply_text("❌ مقدار باید بیشتر از صفر باشد!")
                return
            if player["budget"] < amount:
                await update.message.reply_text(f"❌ بودجه کافی نیست! دارید: {player['budget']:,}$")
                return
            target_id = context.user_data["transfer_target"]
            db.transfer_money(user_id, target_id, amount)
            await update.message.reply_text(f"✅ {amount:,}$ با موفقیت انتقال یافت!")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ عدد اشتباه است!")

    elif step in ("equip_target_id", "equip_target_country"):
        target = _resolve_target(text, step)
        if not target or not target["country"]:
            await update.message.reply_text("❌ کاربر/کشور یافت نشد!")
            context.user_data.clear()
            return
        context.user_data["transfer_target"] = target["user_id"]
        context.user_data["transfer_step"]   = "equip_name"
        await update.message.reply_text("نام تجهیز را بفرستید (مثال: panzer4):")

    elif step == "equip_name":
        item_id = text.lower()
        owned   = db.get_equip_count(user_id, item_id)
        if owned == 0:
            await update.message.reply_text("❌ این تجهیز را ندارید!")
            context.user_data.clear()
            return
        context.user_data["transfer_equip_id"] = item_id
        context.user_data["transfer_step"]     = "equip_amount"
        await update.message.reply_text(f"دارید: {owned} عدد\nچند عدد انتقال دهید؟")

    elif step == "equip_amount":
        try:
            amount  = int(text)
            item_id = context.user_data["transfer_equip_id"]
            owned   = db.get_equip_count(user_id, item_id)
            if amount <= 0 or amount > owned:
                await update.message.reply_text(f"❌ مقدار اشتباه! دارید: {owned}")
                return
            target_id = context.user_data["transfer_target"]
            db.transfer_equipment(user_id, target_id, item_id, amount)
            await update.message.reply_text(f"✅ {amount} عدد {item_id} انتقال یافت!")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ عدد اشتباه!")

# ─────────────────────────────────────────────
#  رتبه‌بندی
# ─────────────────────────────────────────────
async def leaderboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("💰 بر اساس بودجه",      callback_data="rank_budget")],
        [InlineKeyboardButton("⚔️ بر اساس قدرت نظامی", callback_data="rank_military")],
        [InlineKeyboardButton("😊 بر اساس رضایت",       callback_data="rank_satisfaction")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")],
    ]
    await query.edit_message_text("🏆 *رتبه‌بندی کشورها:*\nنوع رتبه‌بندی را انتخاب کنید:",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

async def rank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💰 بر اساس بودجه",      callback_data="rank_budget")],
        [InlineKeyboardButton("⚔️ بر اساس قدرت نظامی", callback_data="rank_military")],
        [InlineKeyboardButton("😊 بر اساس رضایت",       callback_data="rank_satisfaction")],
    ]
    await update.message.reply_text("🏆 *رتبه‌بندی کشورها:*",
                                    parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))

async def show_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode  = query.data

    if mode == "rank_budget":
        players = db.get_leaderboard_by_budget()
        title = "💰 رتبه‌بندی بر اساس بودجه"
        def get_val(p): return f"{p['budget']:,}$"
    elif mode == "rank_satisfaction":
        players = db.get_leaderboard_by_satisfaction()
        title = "😊 رتبه‌بندی بر اساس رضایت"
        def get_val(p): return f"{p['satisfaction']}%"
    else:
        players = db.get_all_players()
        players.sort(key=lambda p: db.get_military_power(p["user_id"]), reverse=True)
        players = players[:15]
        title = "⚔️ رتبه‌بندی بر اساس قدرت نظامی"
        def get_val(p): return f"{db.get_military_power(p['user_id']):,}$"

    medals = ["🥇", "🥈", "🥉"]
    text = f"🏆 *{title}*\n{'─'*30}\n"
    for i, p in enumerate(players):
        info = COUNTRIES.get(p["country"], {})
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {info.get('flag','')} {info.get('name_fa','')}: {get_val(p)}\n"

    if not players:
        text += "❌ هیچ بازیکنی وجود ندارد!"

    kb = [
        [InlineKeyboardButton("💰 بودجه", callback_data="rank_budget"),
         InlineKeyboardButton("⚔️ نظامی", callback_data="rank_military"),
         InlineKeyboardButton("😊 رضایت", callback_data="rank_satisfaction")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

# ─────────────────────────────────────────────
#  سیستم جاسوسی
# ─────────────────────────────────────────────
async def spy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if db.get_config("spy_enabled", "0") != "1":
        await query.edit_message_text("❌ سیستم جاسوسی در حال حاضر غیرفعال است!",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")
                                      ]]))
        return

    player = db.get_player(user_id)
    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    spy_count = db.get_infantry_count(user_id, "spy_squad")
    text = (
        f"🕵️ *سیستم جاسوسی*\n{'─'*25}\n"
        f"🕵️ جوخه جاسوسی دارید: *{spy_count} جوخه*\n\n"
        "هر جوخه = ۱۰ جاسوس | هزینه: ۸۰,۰۰۰$\n\n"
        "📌 تعداد جوخه‌های لازم بسته به قدرت هدف:\n"
        "• هدف ضعیف‌تر → ۱ جوخه\n"
        "• هدف تا ۲× قوی‌تر → ۳ جوخه\n"
        "• هدف تا ۵× قوی‌تر → ۷ جوخه\n"
        "• هدف بیش از ۵× قوی‌تر → ۱۵ جوخه\n\n"
        "⚠️ جوخه‌ها در هر صورت مصرف می‌شوند!"
    )
    kb = [
        [InlineKeyboardButton("🎯 شروع عملیات جاسوسی", callback_data="spy_launch")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

async def spy_launch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        return

    taken   = db.get_taken_countries()
    buttons = []
    for code in taken:
        if code == player["country"]:
            continue
        info = COUNTRIES[code]
        buttons.append([InlineKeyboardButton(
            f"{info['flag']} {info['name_fa']}",
            callback_data=f"spy_target_{code}"
        )])

    if not buttons:
        await query.edit_message_text("❌ کشور دیگری وجود ندارد!")
        return

    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="spy_menu")])
    await query.edit_message_text("🎯 *هدف جاسوسی را انتخاب کنید:*",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def spy_target_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    user_id     = query.from_user.id
    target_code = query.data.replace("spy_target_", "")
    player      = db.get_player(user_id)
    target_player = db.get_player_by_country(target_code)

    if not target_player:
        await query.edit_message_text("❌ این کشور بازیکن ندارد!")
        return

    my_power     = db.get_military_power(user_id)
    target_power = db.get_military_power(target_player["user_id"])
    squads_needed, _ = _calc_spy_squads_needed(my_power, target_power)
    spy_count    = db.get_infantry_count(user_id, "spy_squad")
    target_info  = COUNTRIES[target_code]

    text = (
        f"🎯 *عملیات جاسوسی علیه {target_info['flag']} {target_info['name_fa']}*\n\n"
        f"🕵️ جوخه‌های شما: *{spy_count}*\n"
        f"📊 جوخه‌های مورد نیاز: *{squads_needed}*\n\n"
    )

    if spy_count < squads_needed:
        text += f"❌ جوخه کافی ندارید! باید {squads_needed} جوخه داشته باشید."
        kb = [[InlineKeyboardButton("🔙 برگشت", callback_data="spy_launch")]]
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(kb))
        return

    text += (
        f"⚠️ *{squads_needed} جوخه* مصرف می‌شود (بازگشت‌ناپذیر)\n\n"
        "آیا عملیات را تأیید می‌کنید؟"
    )
    context.user_data["spy_target_code"]   = target_code
    context.user_data["spy_squads_needed"] = squads_needed

    kb = [
        [InlineKeyboardButton("✅ تأیید عملیات", callback_data=f"spy_confirm_{target_code}")],
        [InlineKeyboardButton("❌ انصراف",        callback_data="spy_launch")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

async def spy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    user_id     = query.from_user.id
    target_code = query.data.replace("spy_confirm_", "")
    player      = db.get_player(user_id)
    target_player = db.get_player_by_country(target_code)

    squads_needed = context.user_data.pop("spy_squads_needed", 1)
    context.user_data.pop("spy_target_code", None)

    if not target_player:
        await query.edit_message_text("❌ کشور هدف پیدا نشد!")
        return

    spy_count = db.get_infantry_count(user_id, "spy_squad")
    if spy_count < squads_needed:
        await query.edit_message_text("❌ جوخه کافی ندارید!")
        return

    # مصرف جوخه‌ها
    db.set_infantry_count(user_id, "spy_squad", spy_count - squads_needed)

    # ثبت ماموریت
    mission_id = db.create_spy_mission(user_id, target_player["user_id"], squads_needed)

    # اطلاعات برای ادمین
    a_info    = COUNTRIES.get(player["country"], {})
    d_info    = COUNTRIES.get(target_code, {})
    anti_strat = db.get_anti_spy_strategy(target_player["user_id"])

    admin_text = (
        f"🕵️ *عملیات جاسوسی جدید - #{mission_id}*\n{'─'*30}\n"
        f"🗡️ مهاجم: {a_info.get('flag','')} {a_info.get('name_fa','')}\n"
        f"🎯 هدف: {d_info.get('flag','')} {d_info.get('name_fa','')}\n"
        f"📊 جوخه‌های مصرف‌شده: *{squads_needed}*\n\n"
        f"🛡️ *استراتژی ضدجاسوسی هدف:*\n"
        f"{anti_strat if anti_strat else '❌ تنظیم نشده'}\n\n"
        "نتیجه را اعلام کنید:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ عملیات موفق", callback_data=f"admin_spy_success_{mission_id}")],
        [InlineKeyboardButton("❌ عملیات ناموفق", callback_data=f"admin_spy_fail_{mission_id}")],
    ])
    for admin_id in all_admin_ids():
        try:
            await send_long_message(context.bot, admin_id, admin_text, reply_markup=kb)
        except Exception:
            pass

    await query.edit_message_text(
        "✅ *عملیات جاسوسی آغاز شد!*\n\n"
        f"🕵️ {squads_needed} جوخه اعزام شد.\n"
        "منتظر نتیجه باشید...",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")
        ]])
    )

async def spy_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ فقط ادمین!", show_alert=True)
        return

    parts      = query.data.split("_")
    mission_id = int(parts[-1])
    success    = "success" in query.data
    mission    = db.get_spy_mission(mission_id)

    if not mission:
        await query.edit_message_text("❌ ماموریت پیدا نشد!")
        return

    if mission["status"] != "pending_result":
        await query.edit_message_text("⚠️ این ماموریت قبلاً پردازش شده!")
        return

    db.set_spy_mission_status(mission_id, "success" if success else "failed")

    attacker  = db.get_player(mission["attacker_id"])
    defender  = db.get_player(mission["defender_id"])
    a_info    = COUNTRIES.get(attacker["country"] if attacker else "", {})
    d_info    = COUNTRIES.get(defender["country"] if defender else "", {})

    if success:
        # اطلاع به مهاجم با موجودی هدف
        inv_text = db.get_military_inventory_text(mission["defender_id"])
        msg_to_attacker = (
            f"✅ *عملیات جاسوسی موفق بود!*\n\n"
            f"🎯 موجودی نظامی {d_info.get('flag','')} {d_info.get('name_fa','')}:\n"
            f"{'─'*25}\n{inv_text}"
        )
        try:
            await send_long_message(context.bot, mission["attacker_id"], msg_to_attacker)
        except Exception:
            pass
        # اطلاع ناشناس به مدافع
        try:
            await context.bot.send_message(
                chat_id=mission["defender_id"],
                text="🚨 *هشدار امنیتی!*\nیک تلاش جاسوسی علیه کشور شما موفقیت‌آمیز بود!\n"
                     "(هویت جاسوس ناشناس است)",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"✅ ماموریت #{mission_id} موفق اعلام شد.\n"
            f"اطلاعات به {a_info.get('name_fa','')} ارسال شد."
        )
    else:
        # اطلاع به مهاجم
        try:
            await context.bot.send_message(
                chat_id=mission["attacker_id"],
                text="❌ *عملیات جاسوسی ناموفق بود.*\n\nجوخه‌های شما شناسایی و خنثی شدند.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        # اطلاع ناشناس به مدافع
        try:
            await context.bot.send_message(
                chat_id=mission["defender_id"],
                text="🛡️ *تلاش جاسوسی خنثی شد!*\nیک عملیات جاسوسی علیه کشور شما ناکام ماند.\n"
                     "(هویت جاسوس ناشناس است)",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"❌ ماموریت #{mission_id} ناموفق اعلام شد."
        )

# ─────────────────────────────────────────────
#  استراتژی ضدجاسوسی
# ─────────────────────────────────────────────
async def set_antistrategy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current = db.get_anti_spy_strategy(user_id)

    context.user_data["spy_step"] = "set_antistrategy"
    text = (
        "🔒 *استراتژی ضدجاسوسی*\n\n"
        f"استراتژی فعلی:\n_{current if current else 'تنظیم نشده'}_\n\n"
        "استراتژی جدید خود را بنویسید\n"
        "(این متن فقط توسط ادمین دیده می‌شود وقتی کشوری جاسوس می‌فرستد):"
    )
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")
                                  ]]))

async def handle_spy_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step    = context.user_data.get("spy_step")
    if not step:
        return

    text = update.message.text.strip()

    if step == "set_antistrategy":
        db.set_anti_spy_strategy(user_id, text)
        context.user_data.clear()
        await update.message.reply_text(
            "✅ *استراتژی ضدجاسوسی ذخیره شد!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")
            ]])
        )

# ─────────────────────────────────────────────
#  سیستم اتحاد
# ─────────────────────────────────────────────
async def alliance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    alliance = db.get_player_alliance(user_id)

    if alliance:
        members = db.get_alliance_members(alliance["id"])
        is_leader = alliance["leader_id"] == user_id
        leader_player = db.get_player(alliance["leader_id"])
        leader_name = _get_country_name(leader_player)

        text = (
            f"🛡️ *اتحاد: {alliance['name']}*\n{'─'*25}\n"
            f"👑 رهبر: {leader_name}\n"
            f"👥 اعضا: {len(members)}/{alliance['max_members']}\n\n"
            "📋 *اعضا:*\n"
        )
        for uid in members:
            mp = db.get_player(uid)
            flag = _get_country_flag(mp)
            cname = _get_country_name(mp)
            power = db.get_military_power(uid)
            leader_mark = " 👑" if uid == alliance["leader_id"] else ""
            text += f"• {flag} {cname} | ⚔️ {power:,}${leader_mark}\n"

        kb = []
        if is_leader:
            kb.append([InlineKeyboardButton("➕ دعوت بازیکن", callback_data="alliance_invite")])
            kb.append([InlineKeyboardButton("🦵 اخراج عضو",   callback_data="alliance_kick_menu")])
        kb.append([InlineKeyboardButton("🚪 خروج از اتحاد",  callback_data="alliance_leave_confirm")])
        kb.append([InlineKeyboardButton("🔙 برگشت",          callback_data="dashboard")])
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(kb))
    else:
        kb = [
            [InlineKeyboardButton("➕ ایجاد اتحاد",    callback_data="alliance_create")],
            [InlineKeyboardButton("🌐 لیست اتحادها",   callback_data="alliance_list")],
            [InlineKeyboardButton("🔙 برگشت",          callback_data="dashboard")],
        ]
        await query.edit_message_text(
            "🛡️ *اتحادها*\n\nشما عضو هیچ اتحادی نیستید!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

async def alliance_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["alliance_step"] = "create_name"
    await query.edit_message_text(
        "➕ *ایجاد اتحاد جدید*\n\nنام اتحاد را بفرستید:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 برگشت", callback_data="alliance_menu")
        ]])
    )

async def alliance_list_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    alliances = db.get_all_alliances()

    text = "🌐 *لیست همه اتحادها:*\n{'─'*25}\n"
    buttons = []
    for a in alliances:
        cnt = db.count_alliance_members(a["id"])
        text += f"🛡️ *{a['name']}* — {cnt}/{a['max_members']} عضو\n"
        if cnt < a["max_members"]:
            buttons.append([InlineKeyboardButton(
                f"🤝 پیوستن به {a['name']}",
                callback_data=f"alliance_join_{a['id']}"
            )])

    if not alliances:
        text += "❌ هیچ اتحادی وجود ندارد!"

    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="alliance_menu")])
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def alliance_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    user_id     = query.from_user.id
    alliance_id = int(query.data.replace("alliance_join_", ""))
    alliance    = db.get_alliance(alliance_id)

    if not alliance:
        await query.edit_message_text("❌ اتحاد پیدا نشد!")
        return

    existing = db.get_player_alliance(user_id)
    if existing:
        await query.answer("❌ شما قبلاً عضو اتحاد دیگری هستید!", show_alert=True)
        return

    cnt = db.count_alliance_members(alliance_id)
    if cnt >= alliance["max_members"]:
        await query.answer("❌ این اتحاد پر است!", show_alert=True)
        return

    db.join_alliance(alliance_id, user_id)
    await query.edit_message_text(
        f"✅ به اتحاد *{alliance['name']}* پیوستید!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🛡️ اتحاد من", callback_data="alliance_menu")
        ]])
    )

async def alliance_leave_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚠️ آیا مطمئنید که می‌خواهید از اتحاد خارج شوید؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data="alliance_leave_do")],
            [InlineKeyboardButton("❌ نه",  callback_data="alliance_menu")],
        ])
    )

async def alliance_leave_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    db.leave_alliance(user_id)
    await query.edit_message_text(
        "✅ از اتحاد خارج شدید.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")
        ]])
    )

async def alliance_invite_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["alliance_step"] = "invite_target"
    await query.edit_message_text(
        "➕ *دعوت به اتحاد*\n\nآیدی عددی یا یوزرنیم بازیکن:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 برگشت", callback_data="alliance_menu")
        ]])
    )

async def alliance_kick_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    alliance = db.get_player_alliance(user_id)

    if not alliance or alliance["leader_id"] != user_id:
        await query.answer("❌ فقط رهبر اتحاد!", show_alert=True)
        return

    members = db.get_alliance_members(alliance["id"])
    buttons = []
    for uid in members:
        if uid == user_id:
            continue
        mp = db.get_player(uid)
        cname = _get_country_name(mp)
        buttons.append([InlineKeyboardButton(
            f"🦵 اخراج {cname}",
            callback_data=f"alliance_kick_{uid}"
        )])
    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="alliance_menu")])
    await query.edit_message_text("🦵 *اخراج عضو:*\nانتخاب کنید:",
                                  parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def alliance_kick_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    leader_id  = query.from_user.id
    target_uid = int(query.data.replace("alliance_kick_", ""))
    alliance   = db.get_player_alliance(leader_id)

    if not alliance or alliance["leader_id"] != leader_id:
        await query.answer("❌ فقط رهبر اتحاد!", show_alert=True)
        return

    db.kick_from_alliance(alliance["id"], target_uid)
    target = db.get_player(target_uid)
    cname  = _get_country_name(target)
    await query.edit_message_text(
        f"✅ {cname} از اتحاد اخراج شد.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🛡️ اتحاد من", callback_data="alliance_menu")
        ]])
    )

async def handle_alliance_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step    = context.user_data.get("alliance_step")
    if not step:
        return

    text = update.message.text.strip()

    if step == "create_name":
        existing_alliance = db.get_player_alliance(user_id)
        if existing_alliance:
            await update.message.reply_text("❌ شما قبلاً عضو اتحادی هستید!")
            context.user_data.clear()
            return
        if db.get_alliance_by_name(text):
            await update.message.reply_text("❌ این نام قبلاً گرفته شده!")
            return
        if len(text) < 2 or len(text) > 30:
            await update.message.reply_text("❌ نام باید بین ۲ تا ۳۰ حرف باشد!")
            return
        db.create_alliance(text, user_id)
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ *اتحاد '{text}' ایجاد شد!*\nشما رهبر این اتحاد هستید.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛡️ اتحاد من", callback_data="alliance_menu")
            ]])
        )

    elif step == "invite_target":
        # پیدا کردن بازیکن با آیدی یا یوزرنیم
        target = None
        try:
            target = db.get_player(int(text))
        except ValueError:
            target = db.get_player_by_username(text)

        if not target or not target["country"]:
            await update.message.reply_text("❌ بازیکن پیدا نشد!")
            context.user_data.clear()
            return

        alliance = db.get_player_alliance(user_id)
        if not alliance or alliance["leader_id"] != user_id:
            await update.message.reply_text("❌ شما رهبر اتحاد نیستید!")
            context.user_data.clear()
            return

        if db.get_player_alliance(target["user_id"]):
            await update.message.reply_text("❌ این بازیکن قبلاً عضو اتحادی است!")
            context.user_data.clear()
            return

        cnt = db.count_alliance_members(alliance["id"])
        if cnt >= alliance["max_members"]:
            await update.message.reply_text("❌ اتحاد پر است!")
            context.user_data.clear()
            return

        # ارسال دعوتنامه
        try:
            await context.bot.send_message(
                chat_id=target["user_id"],
                text=(
                    f"🤝 *دعوتنامه اتحاد*\n\n"
                    f"اتحاد *{alliance['name']}* شما را دعوت کرده!\n"
                    f"رهبر: {_get_country_name(db.get_player(user_id))}"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ قبول",   callback_data=f"alliance_join_{alliance['id']}")],
                    [InlineKeyboardButton("❌ رد",     callback_data="dashboard")],
                ])
            )
            await update.message.reply_text("✅ دعوتنامه ارسال شد!")
        except Exception:
            await update.message.reply_text("❌ نتوانستیم پیام بفرستیم.")
        context.user_data.clear()

# ─────────────────────────────────────────────
#  سیستم جنگ
# ─────────────────────────────────────────────
async def war_declare_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    taken = db.get_taken_countries()
    buttons = []
    for code in taken:
        if code == player["country"]:
            continue
        info = COUNTRIES[code]
        buttons.append([InlineKeyboardButton(
            f"{info['flag']} {info['name_fa']}",
            callback_data=f"war_target_{code}"
        )])

    if not buttons:
        await query.edit_message_text("❌ هیچ کشور دیگری برای حمله وجود ندارد!")
        return

    buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")])
    await query.edit_message_text(
        "⚔️ *اعلام جنگ*\n\nبه کدام کشور حمله می‌کنید؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def war_target_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    user_id     = query.from_user.id
    target_code = query.data.replace("war_target_", "")
    target_info = COUNTRIES[target_code]

    context.user_data["war_target"] = target_code
    context.user_data["war_step"]   = "attacker_strategy"

    inv_text = db.get_military_inventory_text(user_id)
    await query.edit_message_text(
        f"⚔️ *حمله به {target_info['flag']} {target_info['name_fa']}*\n\n"
        f"📦 *تجهیزات نظامی شما:*\n{inv_text}\n\n"
        "🗒️ *استراتژی خود را بنویسید:*\n"
        "بنویسید چه تعدادی از کدام تجهیزات استفاده می‌کنید و نقشه حمله‌تان چیست:",
        parse_mode="Markdown"
    )

async def handle_war_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step    = context.user_data.get("war_step")
    if not step:
        return

    text   = update.message.text.strip()
    player = db.get_player(user_id)
    if not player:
        return

    # ── مهاجم استراتژی نوشت ──
    if step == "attacker_strategy":
        target_code = context.user_data["war_target"]
        target_info = COUNTRIES[target_code]

        wait_msg = await update.message.reply_text("⏳ در حال پردازش استراتژی با هوش مصنوعی...")

        prompt = (
            f"شما یک تحلیلگر نظامی در بازی جنگ جهانی دوم هستید.\n"
            f"کشور مهاجم: {COUNTRIES[player['country']]['name_fa']}\n"
            f"کشور هدف: {target_info['name_fa']}\n"
            f"استراتژی مهاجم: {text}\n\n"
            f"لطفاً این استراتژی را به فارسی تحلیل کنید و بگویید آیا منطقی است یا نه، "
            f"نقاط قوت و ضعف آن را بگویید. پاسخ را به فارسی بنویسید."
        )
        ai_analysis = await call_gemini(prompt)

        defender = db.get_player_by_country(target_code)
        if not defender:
            await wait_msg.edit_text("❌ این کشور بازیکن ندارد!")
            context.user_data.clear()
            return

        war_id = db.create_war(user_id, defender["user_id"], text)
        context.user_data.clear()

        attacker_text = (
            f"⚔️ *اعلام جنگ ثبت شد!*\n\n"
            f"🎯 هدف: {target_info['flag']} {target_info['name_fa']}\n"
            f"🆔 شناسه جنگ: #{war_id}\n\n"
            f"🤖 *تحلیل هوش مصنوعی از استراتژی شما:*\n\n{ai_analysis}"
        )
        kb = [[InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")]]
        await wait_msg.delete()
        await send_long_message(context.bot, user_id, attacker_text,
                                reply_markup=InlineKeyboardMarkup(kb))

        # اطلاع‌رسانی به مدافع
        attacker_info = COUNTRIES[player["country"]]
        defender_text = (
            f"🚨 *هشدار! به کشور شما حمله شد!*\n\n"
            f"⚔️ مهاجم: {attacker_info['flag']} {attacker_info['name_fa']}\n"
            f"🆔 شناسه جنگ: #{war_id}\n\n"
            "لطفاً استراتژی دفاعی خود را بنویسید:"
        )
        inv_def = db.get_military_inventory_text(defender["user_id"])
        defender_text += f"\n\n📦 *تجهیزات شما:*\n{inv_def}"

        kb_def = [
            [InlineKeyboardButton("🛡️ نوشتن استراتژی دفاع", callback_data=f"war_defend_{war_id}")],
            [InlineKeyboardButton("🤝 درخواست کمک", callback_data=f"war_help_{war_id}")],
        ]
        try:
            await send_long_message(context.bot, defender["user_id"], defender_text,
                                    reply_markup=InlineKeyboardMarkup(kb_def))
        except Exception:
            pass

        # اطلاع‌رسانی به ادمین‌ها
        admin_text = (
            f"⚔️ *جنگ جدید اعلام شد!*\n\n"
            f"🗡️ مهاجم: {attacker_info['flag']} {attacker_info['name_fa']}\n"
            f"🛡️ مدافع: {target_info['flag']} {target_info['name_fa']}\n"
            f"🆔 شناسه جنگ: #{war_id}\n\n"
            f"📋 *استراتژی مهاجم:*\n{text}\n\n"
            "⏳ منتظر استراتژی مدافع..."
        )
        for admin_id in all_admin_ids():
            try:
                await send_long_message(context.bot, admin_id, admin_text)
            except Exception:
                pass

    # ── مدافع استراتژی نوشت ──
    elif step.startswith("defend_"):
        war_id = int(step.replace("defend_", ""))
        war    = db.get_war(war_id)
        if not war:
            context.user_data.clear()
            return

        db.set_defender_strategy(war_id, text)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ *استراتژی دفاعی ثبت شد!*\n\nمی‌توانید از دوستانتان کمک بگیرید.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤝 درخواست کمک", callback_data=f"war_help_{war_id}")],
                [InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")],
            ])
        )

        # اطلاع به مهاجم که مدافع استراتژی داد
        war_updated = db.get_war(war_id)
        if war_updated:
            attacker_player = db.get_player(war_updated["attacker_id"])
            defender_info   = COUNTRIES.get(player["country"], {})
            try:
                await context.bot.send_message(
                    chat_id=war_updated["attacker_id"],
                    text=(
                        f"⚠️ *اطلاعیه جنگ #{war_id}*\n\n"
                        f"🛡️ {defender_info.get('flag','')} {defender_info.get('name_fa','')} "
                        f"استراتژی دفاعی خود را ثبت کرد!\n"
                        "ادمین به زودی جنگ را تحلیل خواهد کرد."
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        # اطلاع‌رسانی به ادمین که هر دو استراتژی آماده است
        war_updated["defender_strategy"] = text
        await notify_admins_war_ready(context.bot, war_id, war_updated)

    # ── متحد استراتژی نوشت ──
    elif step.startswith("ally_strategy_"):
        parts  = step.split("_")
        war_id = int(parts[2])
        side   = parts[3]

        db.add_war_ally(war_id, user_id, side, text)
        db.answer_ally_request(war_id, user_id)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ *استراتژی کمکی شما ثبت شد!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")]
            ])
        )

        ally_player = db.get_player(user_id)
        ally_info   = COUNTRIES.get(ally_player["country"], {})
        admin_text  = (
            f"🤝 *کمک متحد ثبت شد - جنگ #{war_id}*\n\n"
            f"متحد: {ally_info.get('flag','')} {ally_info.get('name_fa','')}\n"
            f"طرف: {'مهاجم' if side=='attacker' else 'مدافع'}\n\n"
            f"📋 *استراتژی:*\n{text}"
        )
        for admin_id in all_admin_ids():
            try:
                await send_long_message(context.bot, admin_id, admin_text)
            except Exception:
                pass

async def war_defend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    war_id = int(query.data.replace("war_defend_", ""))
    war    = db.get_war(war_id)

    if not war:
        await query.edit_message_text("❌ جنگ یافت نشد!")
        return

    inv_text = db.get_military_inventory_text(query.from_user.id)
    context.user_data["war_step"] = f"defend_{war_id}"
    await query.edit_message_text(
        f"🛡️ *استراتژی دفاع - جنگ #{war_id}*\n\n"
        f"📦 *تجهیزات شما:*\n{inv_text}\n\n"
        "استراتژی دفاعی و تجهیزات مورد استفاده را بنویسید:",
        parse_mode="Markdown"
    )

async def war_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    war_id  = int(query.data.replace("war_help_", ""))
    war     = db.get_player(user_id)
    war_obj = db.get_war(war_id)
    player  = db.get_player(user_id)

    if not war_obj or not player:
        await query.edit_message_text("❌ خطا!")
        return

    attacker = db.get_player(war_obj["attacker_id"])
    defender = db.get_player(war_obj["defender_id"])
    a_info   = COUNTRIES.get(attacker["country"] if attacker else "", {})
    d_info   = COUNTRIES.get(defender["country"] if defender else "", {})

    # لیست گیرندگان: دوستان + اعضای اتحاد
    friends = set(db.get_friends(user_id))
    alliance = db.get_player_alliance(user_id)
    if alliance:
        for uid in db.get_alliance_members(alliance["id"]):
            if uid != user_id:
                friends.add(uid)

    if not friends:
        await query.edit_message_text(
            "❌ شما هیچ دوست یا عضو اتحادی ندارید!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛡️ اتحادها", callback_data="alliance_menu")],
                [InlineKeyboardButton("🤝 دوستان",   callback_data="friends_menu")],
                [InlineKeyboardButton("🔙 برگشت",   callback_data="dashboard")],
            ])
        )
        return

    sent_count = 0
    for friend_id in friends:
        friend = db.get_player(friend_id)
        if not friend or not friend["country"]:
            continue
        db.add_ally_request(war_id, user_id, friend_id)
        try:
            kb = [
                [InlineKeyboardButton("✅ کمک می‌کنم", callback_data=f"ally_accept_{war_id}_defender")],
                [InlineKeyboardButton("❌ کمک نمی‌کنم", callback_data=f"ally_reject_{war_id}")],
            ]
            await context.bot.send_message(
                chat_id=friend_id,
                text=(
                    f"🤝 *درخواست کمک نظامی!*\n\n"
                    f"🛡️ {d_info.get('flag','')} {d_info.get('name_fa','')} درخواست کمک دارد!\n"
                    f"⚔️ مهاجم: {a_info.get('flag','')} {a_info.get('name_fa','')}\n\n"
                    f"🆔 جنگ #{war_id}\n\nآیا کمک می‌کنید؟"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            sent_count += 1
        except Exception:
            pass

    await query.edit_message_text(
        f"✅ درخواست کمک به *{sent_count}* نفر ارسال شد!\n\nمنتظر پاسخ باشید.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")]
        ])
    )

async def ally_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    parts   = query.data.split("_")
    war_id  = int(parts[2])
    side    = parts[3]

    db.answer_ally_request(war_id, user_id)
    inv_text = db.get_military_inventory_text(user_id)
    context.user_data["war_step"] = f"ally_strategy_{war_id}_{side}"

    await query.edit_message_text(
        f"✅ *کمک به جنگ #{war_id} پذیرفتید!*\n\n"
        f"📦 *تجهیزات شما:*\n{inv_text}\n\n"
        "استراتژی کمکی و تجهیزات مورد استفاده را بنویسید:",
        parse_mode="Markdown"
    )

async def ally_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    war_id = int(query.data.replace("ally_reject_", "").split("_")[0])
    db.answer_ally_request(war_id, query.from_user.id)
    await query.edit_message_text(
        "❌ درخواست کمک رد شد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")]
        ])
    )

# ─────────────────────────────────────────────
#  تحلیل نهایی جنگ + غنیمت
# ─────────────────────────────────────────────
async def _do_war_analysis(bot, war_id: int, reply_target):
    war = db.get_war(war_id)
    if not war:
        if hasattr(reply_target, "reply_text"):
            await reply_target.reply_text("❌ جنگ یافت نشد!")
        else:
            await reply_target.edit_message_text("❌ جنگ یافت نشد!")
        return

    attacker = db.get_player(war["attacker_id"])
    defender = db.get_player(war["defender_id"])
    allies   = db.get_war_allies(war_id)
    a_info   = COUNTRIES.get(attacker["country"] if attacker else "", {})
    d_info   = COUNTRIES.get(defender["country"] if defender else "", {})

    ally_texts = ""
    for ally in allies:
        ap = db.get_player(ally["ally_id"])
        if ap and ap["country"]:
            ci = COUNTRIES.get(ap["country"], {})
            side_fa = "مهاجم" if ally["side"] == "attacker" else "مدافع"
            ally_texts += f"\n- متحد {side_fa}: {ci.get('name_fa','')}\n  استراتژی: {ally['strategy']}\n"

    # موجودی نظامی طرفین
    a_inv = db.get_military_inventory_text(war["attacker_id"])
    d_inv = db.get_military_inventory_text(war["defender_id"])

    prompt = (
        f"شما قاضی یک جنگ در بازی جنگ جهانی دوم هستید.\n\n"
        f"🗡️ مهاجم: {a_info.get('name_fa','')}\n"
        f"موجودی نظامی: {a_inv}\n"
        f"استراتژی: {war['attacker_strategy']}\n\n"
        f"🛡️ مدافع: {d_info.get('name_fa','')}\n"
        f"موجودی نظامی: {d_inv}\n"
        f"استراتژی: {war.get('defender_strategy', 'ارائه نشده')}\n"
        f"{ally_texts}\n"
        "تمام استراتژی‌ها و موجودی‌ها را تحلیل کن و نتیجه نهایی را اعلام کن. فارسی بنویس."
    )

    if hasattr(reply_target, "reply_text"):
        wait_msg = await reply_target.reply_text("⏳ در حال تحلیل جنگ با هوش مصنوعی...")
    else:
        wait_msg = await reply_target.edit_message_text("⏳ در حال تحلیل جنگ با هوش مصنوعی...")

    result = await call_gemini(prompt)

    header = (
        f"⚔️ *نتیجه تحلیل جنگ #{war_id}*\n"
        f"🗡️ {a_info.get('flag','')} {a_info.get('name_fa','')} vs "
        f"🛡️ {d_info.get('flag','')} {d_info.get('name_fa','')}\n\n"
    )

    if hasattr(reply_target, "reply_text"):
        await wait_msg.delete()
        admin_uid = reply_target.from_user.id
    else:
        admin_uid = reply_target.from_user.id
        try:
            await wait_msg.delete()
        except Exception:
            pass

    loot_pct = int(db.get_config("war_loot_pct", "30"))
    winner_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🗡️ {a_info.get('name_fa','مهاجم')} برنده شد",
                              callback_data=f"war_winner_attacker_{war_id}")],
        [InlineKeyboardButton(f"🛡️ {d_info.get('name_fa','مدافع')} برنده شد",
                              callback_data=f"war_winner_defender_{war_id}")],
        [InlineKeyboardButton("🤝 مساوی",
                              callback_data=f"war_winner_draw_{war_id}")],
    ])
    full_text = (
        header + result +
        f"\n\n{'─'*30}\n"
        f"💰 *درصد غنیمت: {loot_pct}%*\n"
        "👑 *برنده را اعلام کنید:*"
    )
    await send_long_message(bot, admin_uid, full_text, reply_markup=winner_kb)

async def war_winner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ فقط ادمین!", show_alert=True)
        return

    parts  = query.data.split("_")
    war_id = int(parts[-1])
    side   = parts[2]  # attacker / defender / draw
    war    = db.get_war(war_id)

    if not war:
        await query.edit_message_text("❌ جنگ پیدا نشد!")
        return

    if war["status"] == "analyzed":
        await query.edit_message_text("⚠️ این جنگ قبلاً تحلیل شده!")
        return

    attacker = db.get_player(war["attacker_id"])
    defender = db.get_player(war["defender_id"])
    a_info   = COUNTRIES.get(attacker["country"] if attacker else "", {})
    d_info   = COUNTRIES.get(defender["country"] if defender else "", {})
    loot_pct = int(db.get_config("war_loot_pct", "30"))

    db.set_war_winner(war_id, side)

    result_text = ""
    if side == "attacker":
        winner_id = war["attacker_id"]
        loser_id  = war["defender_id"]
        result_text = f"🗡️ *{a_info.get('flag','')} {a_info.get('name_fa','')} برنده شد!*"
        db.apply_war_loot(winner_id, loser_id, loot_pct)
        win_msg  = f"🎉 *پیروزی!*\nشما جنگ #{war_id} را بردید!\n💰 {loot_pct}% از تجهیزات دشمن غنیمت گرفتید!"
        lose_msg = f"💔 *شکست!*\nجنگ #{war_id} را باختید.\n💸 {loot_pct}% از تجهیزات شما غنیمت گرفته شد."
    elif side == "defender":
        winner_id = war["defender_id"]
        loser_id  = war["attacker_id"]
        result_text = f"🛡️ *{d_info.get('flag','')} {d_info.get('name_fa','')} برنده شد!*"
        db.apply_war_loot(winner_id, loser_id, loot_pct)
        win_msg  = f"🎉 *پیروزی!*\nشما جنگ #{war_id} را دفع کردید!\n💰 {loot_pct}% از تجهیزات دشمن غنیمت گرفتید!"
        lose_msg = f"💔 *شکست!*\nحمله شما در جنگ #{war_id} دفع شد.\n💸 {loot_pct}% از تجهیزات شما غنیمت گرفته شد."
    else:
        result_text = "🤝 *نتیجه: مساوی!*"
        win_msg  = f"🤝 جنگ #{war_id} با مساوی به پایان رسید. تجهیزات تغییر نکرد."
        lose_msg = win_msg

    # اطلاع به طرفین
    for uid, msg in [(war["attacker_id"], win_msg if side == "attacker" else lose_msg),
                     (war["defender_id"], win_msg if side == "defender" else lose_msg)]:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=msg,
                parse_mode="Markdown"
            )
        except Exception:
            pass

    if side == "draw":
        for uid in [war["attacker_id"], war["defender_id"]]:
            try:
                await context.bot.send_message(chat_id=uid, text=lose_msg, parse_mode="Markdown")
            except Exception:
                pass

    await query.edit_message_text(
        f"✅ *جنگ #{war_id} بسته شد!*\n\n{result_text}\n"
        f"💰 درصد غنیمت: {loot_pct}%",
        parse_mode="Markdown"
    )

async def war_analyze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند این دستور را اجرا کنند!")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /analyze_war <war_id>")
        return

    try:
        war_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ شناسه جنگ اشتباه است!")
        return

    await _do_war_analysis(context.bot, war_id, update.message)

# ─────────────────────────────────────────────
#  /status — وضعیت جنگ‌های فعال
# ─────────────────────────────────────────────
async def war_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند این دستور را اجرا کنند!")
        return

    wars = db.get_all_active_wars()
    if not wars:
        await update.message.reply_text("✅ هیچ جنگ فعالی وجود ندارد!")
        return

    STATUS_LABEL = {
        "pending_defense": "⏳ منتظر استراتژی مدافع",
        "pending_allies":  "✅ آماده تحلیل",
    }

    lines = [f"⚔️ *جنگ‌های فعال ({len(wars)} جنگ):*\n{'─'*30}"]
    buttons = []

    for w in wars:
        attacker = db.get_player(w["attacker_id"])
        defender = db.get_player(w["defender_id"])
        a_info   = COUNTRIES.get(attacker["country"] if attacker else "", {})
        d_info   = COUNTRIES.get(defender["country"] if defender else "", {})
        status   = STATUS_LABEL.get(w["status"], w["status"])

        lines.append(
            f"\n🆔 جنگ *#{w['id']}*\n"
            f"🗡️ {a_info.get('flag','')} {a_info.get('name_fa','?')}\n"
            f"🛡️ {d_info.get('flag','')} {d_info.get('name_fa','?')}\n"
            f"📌 وضعیت: {status}"
        )

        if w["status"] == "pending_allies":
            buttons.append([InlineKeyboardButton(
                f"⚔️ تحلیل جنگ #{w['id']}",
                callback_data=f"admin_analyze_direct_{w['id']}"
            )])

    text = "\n".join(lines)
    kb   = InlineKeyboardMarkup(buttons) if buttons else None
    await send_long_message(context.bot, user_id, text, reply_markup=kb)

# ─────────────────────────────────────────────
#  /wars — تاریخچه جنگ‌ها
# ─────────────────────────────────────────────
async def wars_history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return

    wars = db.get_analyzed_wars(20)
    if not wars:
        await update.message.reply_text("❌ هیچ جنگ تحلیل‌شده‌ای وجود ندارد!")
        return

    text = f"📜 *تاریخچه جنگ‌ها ({len(wars)} جنگ):*\n{'─'*30}\n"
    for w in wars:
        attacker = db.get_player(w["attacker_id"])
        defender = db.get_player(w["defender_id"])
        a_info   = COUNTRIES.get(attacker["country"] if attacker else "", {})
        d_info   = COUNTRIES.get(defender["country"] if defender else "", {})
        winner   = w.get("winner_side", "نامشخص")
        winner_map = {"attacker": f"🗡️ {a_info.get('name_fa','مهاجم')}",
                      "defender": f"🛡️ {d_info.get('name_fa','مدافع')}",
                      "draw":     "🤝 مساوی"}
        text += (
            f"\n⚔️ جنگ *#{w['id']}*\n"
            f"  {a_info.get('flag','')} vs {d_info.get('flag','')}\n"
            f"  🏆 برنده: {winner_map.get(winner, winner)}\n"
        )

    await send_long_message(context.bot, user_id, text)

# ─────────────────────────────────────────────
#  /rank — رتبه‌بندی (دستوری)
# ─────────────────────────────────────────────
async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💰 بودجه",       callback_data="rank_budget")],
        [InlineKeyboardButton("⚔️ قدرت نظامی",  callback_data="rank_military")],
        [InlineKeyboardButton("😊 رضایت",        callback_data="rank_satisfaction")],
    ]
    await update.message.reply_text("🏆 *رتبه‌بندی:*",
                                    parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))

# ─────────────────────────────────────────────
#  /broadcast — پیام همگانی
# ─────────────────────────────────────────────
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    context.user_data["admin_step"] = "broadcast_text"
    await update.message.reply_text(
        "📢 *پیام همگانی*\n\nمتن پیامی که می‌خواهید به همه بازیکنان ارسال شود را بفرستید:\n"
        "(یا /cancel برای لغو)",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
#  بیانیه
# ─────────────────────────────────────────────
async def bayanie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player  = db.get_player(user_id)

    if not player or not player["country"]:
        await query.edit_message_text("❌ ابتدا کشور انتخاب کنید!")
        return

    context.user_data["bayanie_step"] = "waiting"
    await query.edit_message_text(
        "📢 *بیانیه*\n\n"
        "یک تصویر با کپشن (متن) بفرستید.\n"
        "این بیانیه برای همه ادمین‌ها ارسال می‌شود.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")]
        ])
    )

async def handle_bayanie_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("bayanie_step") != "waiting":
        return

    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً یک تصویر بفرستید!")
        return

    player = db.get_player(user_id)
    if not player or not player["country"]:
        return

    info    = COUNTRIES[player["country"]]
    caption = update.message.caption or ""
    photo   = update.message.photo[-1].file_id

    context.user_data.pop("bayanie_step", None)

    header = (
        f"📢 *بیانیه از {info['flag']} {info['name_fa']}*\n"
        f"👤 @{player['username']}\n\n"
        f"{caption}"
    )

    sent = 0
    for admin_id in all_admin_ids():
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption=header,
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ بیانیه شما به {sent} ادمین ارسال شد!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 داشبورد", callback_data="dashboard")]
        ])
    )

# ─────────────────────────────────────────────
#  مدیریت دوستان
# ─────────────────────────────────────────────
async def friends_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    friends = db.get_friends(user_id)

    text = "🤝 *مدیریت دوستان*\n\n"
    if friends:
        text += "دوستان شما:\n"
        for fid in friends:
            fp = db.get_player(fid)
            if fp and fp["country"]:
                fi = COUNTRIES.get(fp["country"], {})
                text += f"• {fi.get('flag','')} {fi.get('name_fa','')} (@{fp['username']})\n"
    else:
        text += "❌ هنوز دوستی ندارید!\n"

    kb = [
        [InlineKeyboardButton("➕ افزودن دوست (آیدی)", callback_data="friend_add_id")],
        [InlineKeyboardButton("➕ افزودن دوست (یوزرنیم)", callback_data="friend_add_username")],
        [InlineKeyboardButton("➖ حذف دوست", callback_data="friend_remove")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="dashboard")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(kb))

async def friend_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "friend_add_id":
        context.user_data["friend_step"] = "add_id"
        prompt = "آیدی عددی تلگرام دوست را بفرستید:"
    elif query.data == "friend_add_username":
        context.user_data["friend_step"] = "add_username"
        prompt = "یوزرنیم دوست را بفرستید (مثال: @username):"
    else:
        context.user_data["friend_step"] = "remove_id"
        prompt = "آیدی عددی دوستی که می‌خواهید حذف کنید را بفرستید:"
    await query.edit_message_text(prompt)

async def handle_friend_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step    = context.user_data.get("friend_step")
    if not step:
        return

    text = update.message.text.strip()

    if step == "add_id":
        try:
            friend_id = int(text)
            friend    = db.get_player(friend_id)
            if not friend:
                await update.message.reply_text("❌ کاربر یافت نشد!")
            elif friend_id == user_id:
                await update.message.reply_text("❌ نمی‌توانید خودتان را اضافه کنید!")
            else:
                db.add_friend(user_id, friend_id)
                await update.message.reply_text(f"✅ دوست اضافه شد: @{friend['username']}")
        except ValueError:
            await update.message.reply_text("❌ آیدی اشتباه!")
        context.user_data.clear()

    elif step == "add_username":
        friend = db.get_player_by_username(text)
        if not friend:
            await update.message.reply_text("❌ کاربر یافت نشد!")
        elif friend["user_id"] == user_id:
            await update.message.reply_text("❌ نمی‌توانید خودتان را اضافه کنید!")
        else:
            db.add_friend(user_id, friend["user_id"])
            await update.message.reply_text(f"✅ دوست اضافه شد: @{friend['username']}")
        context.user_data.clear()

    elif step == "remove_id":
        try:
            friend_id = int(text)
            db.remove_friend(user_id, friend_id)
            await update.message.reply_text("✅ دوست حذف شد!")
        except ValueError:
            await update.message.reply_text("❌ آیدی اشتباه!")
        context.user_data.clear()

# ─────────────────────────────────────────────
#  پنل ادمین
# ─────────────────────────────────────────────
def _admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید VIP",          callback_data="admin_vip"),
         InlineKeyboardButton("❌ لغو VIP",             callback_data="admin_revoke_vip")],
        [InlineKeyboardButton("🎁 هدیه تجهیزات",       callback_data="admin_gift_equip"),
         InlineKeyboardButton("💰 هدیه پول",            callback_data="admin_gift_money")],
        [InlineKeyboardButton("💰 واریز درآمد",        callback_data="admin_deposit_income"),
         InlineKeyboardButton("🏆 مدیر جدید",          callback_data="admin_add_admin")],
        [InlineKeyboardButton("📈 تنظیم درآمد کشور",   callback_data="admin_set_income"),
         InlineKeyboardButton("🔍 موجودی کشور",         callback_data="admin_view_country_equip")],
        [InlineKeyboardButton("🔄 ریست سیزن",          callback_data="admin_reset_season"),
         InlineKeyboardButton("📋 لیست بازیکنان",      callback_data="admin_players")],
        [InlineKeyboardButton("👥 لیست همه یوزرها",    callback_data="admin_all_users"),
         InlineKeyboardButton("🌍 VIP کشور",            callback_data="admin_vip_country")],
        [InlineKeyboardButton("⚔️ تحلیل جنگ",         callback_data="admin_war_analyze"),
         InlineKeyboardButton("📜 تاریخچه جنگ‌ها",     callback_data="admin_war_history")],
        [InlineKeyboardButton("🦵 اخراج بازیکن",       callback_data="admin_kick_player"),
         InlineKeyboardButton("💰 درصد غنیمت",          callback_data="admin_set_loot_pct")],
        [InlineKeyboardButton("🕵️ جاسوسی: روشن/خاموش", callback_data="admin_spy_toggle"),
         InlineKeyboardButton("📋 ماموریت‌های جاسوسی", callback_data="admin_spy_missions")],
        [InlineKeyboardButton("📢 پیام همگانی",         callback_data="admin_broadcast")],
    ])

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ دسترسی ندارید!")
        return
    await update.message.reply_text("🔧 *پنل مدیریت:*",
                                    parse_mode="Markdown",
                                    reply_markup=_admin_kb())

async def admin_panel_via_callback(query):
    await query.edit_message_text("🔧 *پنل مدیریت:*",
                                  parse_mode="Markdown",
                                  reply_markup=_admin_kb())

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ دسترسی ندارید!", show_alert=True)
        return
    await query.answer()
    action = query.data

    _back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]])

    if action == "admin_vip":
        context.user_data["admin_step"] = "vip_approve"
        await query.edit_message_text("آیدی عددی کاربر برای تایید VIP:", reply_markup=_back_kb)

    elif action == "admin_revoke_vip":
        context.user_data["admin_step"] = "vip_revoke"
        await query.edit_message_text("آیدی عددی کاربر برای لغو VIP:", reply_markup=_back_kb)

    elif action == "admin_gift_equip":
        context.user_data["admin_step"] = "gift_equip_target"
        await query.edit_message_text("آیدی کاربر گیرنده تجهیزات:", reply_markup=_back_kb)

    elif action == "admin_gift_money":
        context.user_data["admin_step"] = "gift_money_target"
        await query.edit_message_text("آیدی کاربر گیرنده پول:", reply_markup=_back_kb)

    elif action == "admin_deposit_income":
        context.user_data["admin_step"] = "deposit_target"
        await query.edit_message_text(
            "💰 *واریز درآمد*\n\nآیدی کاربر یا کد کشور را بفرستید (یا 'all' برای همه):",
            parse_mode="Markdown",
            reply_markup=_back_kb
        )

    elif action == "admin_add_admin":
        context.user_data["admin_step"] = "add_admin"
        await query.edit_message_text("آیدی کاربری که می‌خواهید مدیر شود:", reply_markup=_back_kb)

    elif action == "admin_set_income":
        context.user_data["admin_step"] = "set_income_target"
        await query.edit_message_text(
            "📈 *تنظیم درآمد روزانه*\n\nکد کشور یا آیدی کاربر:",
            parse_mode="Markdown",
            reply_markup=_back_kb
        )

    elif action == "admin_view_country_equip":
        players = db.get_all_players()
        buttons = []
        for p in players:
            info = COUNTRIES.get(p["country"], {})
            buttons.append([InlineKeyboardButton(
                f"{info.get('flag','')} {info.get('name_fa','')}",
                callback_data=f"admin_equip_view_{p['user_id']}"
            )])
        buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")])
        await query.edit_message_text("🔍 *موجودی کشور را انتخاب کنید:*",
                                      parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(buttons))

    elif action.startswith("admin_equip_view_"):
        target_uid = int(action.replace("admin_equip_view_", ""))
        target     = db.get_player(target_uid)
        if not target:
            await query.edit_message_text("❌ بازیکن پیدا نشد!")
            return
        inv_text = db.get_military_inventory_text(target_uid)
        power    = db.get_military_power(target_uid)
        info     = COUNTRIES.get(target["country"], {})
        text = (
            f"🔍 *موجودی {info.get('flag','')} {info.get('name_fa','')}*\n"
            f"{'─'*25}\n"
            f"💰 بودجه: {target['budget']:,}$\n"
            f"📈 درآمد روزانه: {target['daily_income']:,}$\n"
            f"😊 رضایت: {target['satisfaction']}%\n"
            f"⚔️ قدرت نظامی: {power:,}$\n\n"
            f"📦 *موجودی نظامی:*\n{inv_text}"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton("🔙 برگشت", callback_data="admin_view_country_equip")
                                      ]]))

    elif action == "admin_kick_player":
        context.user_data["admin_step"] = "kick_player"
        await query.edit_message_text(
            "🦵 *اخراج بازیکن*\n\nآیدی عددی یا کد کشور بازیکن:",
            parse_mode="Markdown",
            reply_markup=_back_kb
        )

    elif action == "admin_set_loot_pct":
        current = db.get_config("war_loot_pct", "30")
        context.user_data["admin_step"] = "set_loot_pct"
        await query.edit_message_text(
            f"💰 *درصد غنیمت جنگ*\n\nمقدار فعلی: *{current}%*\n\nمقدار جدید (عدد ۱ تا ۱۰۰):",
            parse_mode="Markdown",
            reply_markup=_back_kb
        )

    elif action == "admin_spy_toggle":
        current = db.get_config("spy_enabled", "0")
        new_val = "0" if current == "1" else "1"
        db.set_config("spy_enabled", new_val)
        status = "✅ روشن" if new_val == "1" else "❌ خاموش"
        await query.edit_message_text(
            f"🕵️ سیستم جاسوسی: *{status}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 برگشت به پنل", callback_data="admin_back")
            ]])
        )

    elif action == "admin_spy_missions":
        missions = db.get_pending_spy_missions()
        if not missions:
            await query.edit_message_text("✅ هیچ ماموریت جاسوسی در انتظار وجود ندارد!",
                                          reply_markup=_back_kb)
            return
        buttons = []
        text = f"📋 *ماموریت‌های جاسوسی در انتظار ({len(missions)}):*\n{'─'*25}\n"
        for m in missions:
            att = db.get_player(m["attacker_id"])
            dfd = db.get_player(m["defender_id"])
            a_name = _get_country_name(att)
            d_name = _get_country_name(dfd)
            text += f"\n🕵️ #{m['id']}: {a_name} → {d_name} ({m['squads_used']} جوخه)\n"
            buttons.append([
                InlineKeyboardButton(f"✅ موفق #{m['id']}", callback_data=f"admin_spy_success_{m['id']}"),
                InlineKeyboardButton(f"❌ ناموفق #{m['id']}", callback_data=f"admin_spy_fail_{m['id']}"),
            ])
        buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")])
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "admin_broadcast":
        context.user_data["admin_step"] = "broadcast_text"
        await query.edit_message_text(
            "📢 *پیام همگانی*\n\nمتن پیام را بفرستید:",
            parse_mode="Markdown",
            reply_markup=_back_kb
        )

    elif action == "admin_reset_season":
        kb = [
            [InlineKeyboardButton("✅ بله، ریست کن!", callback_data="confirm_reset")],
            [InlineKeyboardButton("❌ نه", callback_data="admin_back")],
        ]
        await query.edit_message_text(
            "⚠️ *آیا مطمئنید؟*\nاین عمل همه بازیکنان را ریست می‌کند!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif action == "confirm_reset":
        db.reset_season()
        await query.edit_message_text("✅ سیزن ریست شد!")

    elif action == "admin_players":
        players = db.get_all_players()
        text = "📋 *لیست بازیکنان:*\n\n"
        for p in players:
            country = COUNTRIES.get(p["country"], {}).get("name_fa", "ندارد") if p["country"] else "ندارد"
            text += f"👤 {p['username']} | 🌍 {country} | 💰 {p['budget']:,}$\n"
        if not players:
            text += "❌ هیچ بازیکنی وجود ندارد!"
        kb = [[InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]]
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(kb))

    elif action == "admin_all_users":
        users = db.get_all_users()
        text  = f"👥 *لیست همه کاربران ({len(users)} نفر):*\n\n"
        for u in users[:50]:
            text += f"• @{u['username']} (ID: {u['user_id']})\n"
        if len(users) > 50:
            text += f"\n... و {len(users)-50} نفر دیگر"
        kb = [[InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]]
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(kb))

    elif action == "admin_vip_country":
        context.user_data["admin_step"] = "vip_country_code"
        await query.edit_message_text("کد کشور را بفرستید (مثال: de، us، gb):", reply_markup=_back_kb)

    elif action == "admin_war_analyze":
        context.user_data["admin_step"] = "war_analyze_id"
        await query.edit_message_text(
            "⚔️ *تحلیل جنگ*\n\nشناسه جنگ را بفرستید:",
            parse_mode="Markdown",
            reply_markup=_back_kb
        )

    elif action == "admin_war_history":
        wars = db.get_analyzed_wars(15)
        text = f"📜 *تاریخچه جنگ‌ها ({len(wars)} جنگ):*\n{'─'*25}\n"
        for w in wars:
            att = db.get_player(w["attacker_id"])
            dfd = db.get_player(w["defender_id"])
            a_info = COUNTRIES.get(att["country"] if att else "", {})
            d_info = COUNTRIES.get(dfd["country"] if dfd else "", {})
            winner_map = {"attacker": f"🗡️ {a_info.get('name_fa','مهاجم')}",
                          "defender": f"🛡️ {d_info.get('name_fa','مدافع')}",
                          "draw":     "🤝 مساوی"}
            winner = winner_map.get(w.get("winner_side",""), "نامشخص")
            text += f"\n#{w['id']}: {a_info.get('flag','')} vs {d_info.get('flag','')} — 🏆 {winner}\n"
        if not wars:
            text += "❌ هیچ جنگی ثبت نشده!"
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")
                                      ]]))

    elif action.startswith("admin_analyze_direct_"):
        war_id = int(action.replace("admin_analyze_direct_", ""))
        await _do_war_analysis(context.bot, war_id, query)

    elif action == "admin_back":
        context.user_data.pop("admin_step", None)
        await admin_panel_via_callback(query)

async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    step = context.user_data.get("admin_step")
    if not step:
        return

    text = update.message.text.strip()

    if step == "vip_approve":
        try:
            db.set_vip_approved(int(text), True)
            await update.message.reply_text(f"✅ کاربر {text} تایید VIP شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "vip_revoke":
        try:
            db.set_vip_approved(int(text), False)
            await update.message.reply_text(f"✅ VIP کاربر {text} لغو شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "gift_equip_target":
        try:
            target = db.get_player(int(text))
            if not target:
                await update.message.reply_text("❌ کاربر یافت نشد!")
                context.user_data.clear()
                return
            context.user_data["gift_target"] = int(text)
            context.user_data["admin_step"]  = "gift_equip_name"
            await update.message.reply_text("نام تجهیز (مثال: panzer4):")
        except Exception:
            await update.message.reply_text("❌ خطا!")
            context.user_data.clear()

    elif step == "gift_equip_name":
        context.user_data["gift_equip_id"] = text.lower()
        context.user_data["admin_step"]    = "gift_equip_amount"
        await update.message.reply_text("چند عدد هدیه دهید؟")

    elif step == "gift_equip_amount":
        try:
            amount    = int(text)
            target_id = context.user_data["gift_target"]
            item_id   = context.user_data["gift_equip_id"]
            db.admin_gift_equip(target_id, item_id, amount)
            await update.message.reply_text(f"✅ {amount} عدد {item_id} هدیه داده شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "gift_money_target":
        try:
            context.user_data["gift_target"] = int(text)
            context.user_data["admin_step"]  = "gift_money_amount"
            await update.message.reply_text("مقدار پول را بفرستید:")
        except Exception:
            await update.message.reply_text("❌ خطا!")
            context.user_data.clear()

    elif step == "gift_money_amount":
        try:
            amount    = int(text.replace(",", ""))
            target_id = context.user_data["gift_target"]
            db.admin_gift_money(target_id, amount)
            await update.message.reply_text(f"✅ {amount:,}$ هدیه داده شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "deposit_target":
        context.user_data["deposit_target"] = text
        context.user_data["admin_step"]     = "deposit_amount"
        await update.message.reply_text("مقدار واریز (دلار) را بفرستید:")

    elif step == "deposit_amount":
        try:
            amount = int(text.replace(",", ""))
            target = context.user_data["deposit_target"]
            if target.lower() == "all":
                players = db.get_all_players()
                for p in players:
                    db.add_budget(p["user_id"], amount)
                await update.message.reply_text(f"✅ {amount:,}$ به همه {len(players)} بازیکن واریز شد!")
            else:
                try:
                    t_id = int(target)
                    db.add_budget(t_id, amount)
                except ValueError:
                    p = db.get_player_by_country(target)
                    if p:
                        db.add_budget(p["user_id"], amount)
                    else:
                        await update.message.reply_text("❌ کاربر یافت نشد!")
                        context.user_data.clear()
                        return
                await update.message.reply_text(f"✅ {amount:,}$ واریز شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "add_admin":
        try:
            db.add_admin(int(text))
            await update.message.reply_text(f"✅ کاربر {text} مدیر شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "set_income_target":
        # پیدا کردن کاربر با کد کشور یا آیدی
        target = None
        try:
            target = db.get_player(int(text))
        except ValueError:
            target = db.get_player_by_country(text.lower())
        if not target:
            await update.message.reply_text("❌ کاربر/کشور پیدا نشد!")
            context.user_data.clear()
            return
        context.user_data["set_income_uid"] = target["user_id"]
        context.user_data["admin_step"]     = "set_income_amount"
        cname = _get_country_name(target)
        await update.message.reply_text(
            f"📈 کشور: *{cname}*\n\nمقدار درآمد روزانه جدید (دلار):",
            parse_mode="Markdown"
        )

    elif step == "set_income_amount":
        try:
            amount = int(text.replace(",", ""))
            uid    = context.user_data["set_income_uid"]
            db.set_daily_income(uid, amount)
            await update.message.reply_text(f"✅ درآمد روزانه به {amount:,}$ تنظیم شد!")
        except Exception:
            await update.message.reply_text("❌ خطا!")
        context.user_data.clear()

    elif step == "kick_player":
        target = None
        try:
            target = db.get_player(int(text))
        except ValueError:
            target = db.get_player_by_country(text.lower())
        if not target:
            await update.message.reply_text("❌ بازیکن پیدا نشد!")
            context.user_data.clear()
            return
        cname = _get_country_name(target)
        db.kick_player(target["user_id"])
        try:
            await context.bot.send_message(
                chat_id=target["user_id"],
                text="⚠️ کشور شما توسط ادمین از بازی حذف شد.",
            )
        except Exception:
            pass
        await update.message.reply_text(f"✅ بازیکن {cname} از بازی اخراج شد!")
        context.user_data.clear()

    elif step == "set_loot_pct":
        try:
            pct = int(text)
            if not 1 <= pct <= 100:
                raise ValueError
            db.set_config("war_loot_pct", str(pct))
            await update.message.reply_text(f"✅ درصد غنیمت به *{pct}%* تنظیم شد!", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد باید بین ۱ تا ۱۰۰ باشد!")
        context.user_data.clear()

    elif step == "broadcast_text":
        players = db.get_all_players()
        sent    = 0
        for p in players:
            try:
                await context.bot.send_message(
                    chat_id=p["user_id"],
                    text=f"📢 *اطلاعیه ادمین:*\n\n{text}",
                    parse_mode="Markdown"
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        await update.message.reply_text(f"✅ پیام به *{sent}* بازیکن ارسال شد!", parse_mode="Markdown")
        context.user_data.clear()

    elif step == "vip_country_code":
        code = text.lower()
        if code not in COUNTRIES:
            await update.message.reply_text("❌ کد کشور یافت نشد!")
            context.user_data.clear()
            return
        context.user_data["vip_country_code"] = code
        context.user_data["admin_step"]       = "vip_country_action"
        kb = [
            [InlineKeyboardButton("VIP کن",       callback_data=f"set_country_vip_{code}_1")],
            [InlineKeyboardButton("از VIP دربیار", callback_data=f"set_country_vip_{code}_0")],
        ]
        await update.message.reply_text(
            f"کشور: {COUNTRIES[code]['name_fa']}\nاکشن:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif step == "war_analyze_id":
        try:
            war_id = int(text)
            await _do_war_analysis(context.bot, war_id, update.message)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {e}")
        context.user_data.clear()

async def set_country_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    parts  = query.data.split("_")
    code   = parts[3]
    is_vip = int(parts[4]) == 1
    COUNTRIES[code]["vip"] = is_vip
    status = "VIP" if is_vip else "عادی"
    await query.edit_message_text(
        f"✅ کشور {COUNTRIES[code]['name_fa']} اکنون {status} است!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ])
    )
    context.user_data.clear()

# ─────────────────────────────────────────────
#  لیست کشورها (callback)
# ─────────────────────────────────────────────
async def country_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_country_list(query)

# ─────────────────────────────────────────────
#  درآمد روزانه
# ─────────────────────────────────────────────
async def daily_income_job(context: ContextTypes.DEFAULT_TYPE):
    players = db.get_all_players()
    for player in players:
        if player["country"] and player["daily_income"] > 0:
            new_budget = player["budget"] + player["daily_income"]
            db.update_budget(player["user_id"], new_budget)
            try:
                country_name = COUNTRIES[player["country"]]["name_fa"]
                await context.bot.send_message(
                    chat_id=player["user_id"],
                    text=(
                        f"📈 *درآمد روزانه دریافت شد!*\n"
                        f"🌍 {country_name}\n"
                        f"💰 +{player['daily_income']:,}$\n"
                        f"💼 بودجه جدید: {new_budget:,}$"
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

# ─────────────────────────────────────────────
#  یادآوری به مدافع (هر ۱ ساعت چک می‌کند)
# ─────────────────────────────────────────────
async def defender_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    old_wars = db.get_pending_defense_wars_older_than(24)
    for war in old_wars:
        attacker = db.get_player(war["attacker_id"])
        a_info   = COUNTRIES.get(attacker["country"] if attacker else "", {})
        try:
            await context.bot.send_message(
                chat_id=war["defender_id"],
                text=(
                    f"⏰ *یادآوری جنگ #{war['id']}*\n\n"
                    f"⚔️ {a_info.get('flag','')} {a_info.get('name_fa','')} به شما حمله کرده!\n"
                    "هنوز استراتژی دفاعی ارائه نداده‌اید. لطفاً هر چه زودتر اقدام کنید!"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛡️ ثبت استراتژی دفاعی",
                                          callback_data=f"war_defend_{war['id']}")]
                ])
            )
        except Exception:
            pass

# ─────────────────────────────────────────────
#  Handler همه‌جانبه پیام متنی
# ─────────────────────────────────────────────
async def master_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    war_s     = context.user_data.get("war_step", "")
    admin_s   = context.user_data.get("admin_step", "")
    trans_s   = context.user_data.get("transfer_step", "")
    friend_s  = context.user_data.get("friend_step", "")
    spy_s     = context.user_data.get("spy_step", "")
    alliance_s = context.user_data.get("alliance_step", "")

    if war_s:
        await handle_war_messages(update, context)
    elif admin_s and is_admin(user_id):
        await admin_message_handler(update, context)
    elif trans_s:
        await handle_transfer_message(update, context)
    elif friend_s:
        await handle_friend_message(update, context)
    elif spy_s:
        await handle_spy_messages(update, context)
    elif alliance_s:
        await handle_alliance_messages(update, context)

# ─────────────────────────────────────────────
#  main
# ─────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("admin",        admin_panel))
    app.add_handler(CommandHandler("analyze_war",  war_analyze_cmd))
    app.add_handler(CommandHandler("status",       war_status_cmd))
    app.add_handler(CommandHandler("wars",         wars_history_cmd))
    app.add_handler(CommandHandler("rank",         rank_command))
    app.add_handler(CommandHandler("broadcast",    broadcast_cmd))

    # Callbacks — specific patterns BEFORE generic ^admin_
    app.add_handler(CallbackQueryHandler(joined_callback,        pattern="^joined$"))
    app.add_handler(CallbackQueryHandler(select_country_menu,    pattern="^select_country$"))
    app.add_handler(CallbackQueryHandler(choose_country,         pattern="^choose_"))
    app.add_handler(CallbackQueryHandler(dashboard,              pattern="^dashboard$"))
    app.add_handler(CallbackQueryHandler(buy_infra_menu,         pattern="^buy_infra$"))
    app.add_handler(CallbackQueryHandler(buy_infra_item,         pattern="^infra_"))
    app.add_handler(CallbackQueryHandler(buy_equip_menu,         pattern="^buy_equip$"))
    app.add_handler(CallbackQueryHandler(equip_category,         pattern="^equip_cat_"))
    app.add_handler(CallbackQueryHandler(buy_equip_item,         pattern="^eqbuy_"))
    app.add_handler(CallbackQueryHandler(buy_infantry_menu,      pattern="^buy_infantry$"))
    app.add_handler(CallbackQueryHandler(buy_infantry_item,      pattern="^infbuy_"))
    app.add_handler(CallbackQueryHandler(buy_missile_menu,       pattern="^buy_missile$"))
    app.add_handler(CallbackQueryHandler(buy_missile_item,       pattern="^msbuy_"))
    app.add_handler(CallbackQueryHandler(buy_air_defense_menu,   pattern="^buy_air_defense$"))
    app.add_handler(CallbackQueryHandler(buy_air_defense_item,   pattern="^adbuy_"))
    app.add_handler(CallbackQueryHandler(my_inventory,           pattern="^my_inventory$"))
    app.add_handler(CallbackQueryHandler(transfer_menu,          pattern="^transfer_menu$"))
    app.add_handler(CallbackQueryHandler(transfer_money_start,   pattern="^transfer_money"))
    app.add_handler(CallbackQueryHandler(transfer_equip_start,   pattern="^transfer_equip"))
    app.add_handler(CallbackQueryHandler(country_list_callback,  pattern="^country_list$"))
    app.add_handler(CallbackQueryHandler(war_declare_menu,       pattern="^war_declare$"))
    app.add_handler(CallbackQueryHandler(war_target_selected,    pattern="^war_target_"))
    app.add_handler(CallbackQueryHandler(war_defend_callback,    pattern="^war_defend_"))
    app.add_handler(CallbackQueryHandler(war_help_callback,      pattern="^war_help_"))
    app.add_handler(CallbackQueryHandler(ally_accept_callback,   pattern="^ally_accept_"))
    app.add_handler(CallbackQueryHandler(ally_reject_callback,   pattern="^ally_reject_"))
    app.add_handler(CallbackQueryHandler(war_winner_callback,    pattern="^war_winner_"))
    app.add_handler(CallbackQueryHandler(bayanie_start,          pattern="^bayanie_start$"))
    app.add_handler(CallbackQueryHandler(friends_menu,           pattern="^friends_menu$"))
    app.add_handler(CallbackQueryHandler(friend_add_start,       pattern="^friend_add_"))
    app.add_handler(CallbackQueryHandler(friend_add_start,       pattern="^friend_remove$"))
    # Leaderboard
    app.add_handler(CallbackQueryHandler(leaderboard_menu,       pattern="^leaderboard_menu$"))
    app.add_handler(CallbackQueryHandler(show_rank,              pattern="^rank_"))
    # Alliance
    app.add_handler(CallbackQueryHandler(alliance_menu,          pattern="^alliance_menu$"))
    app.add_handler(CallbackQueryHandler(alliance_create_start,  pattern="^alliance_create$"))
    app.add_handler(CallbackQueryHandler(alliance_list_view,     pattern="^alliance_list$"))
    app.add_handler(CallbackQueryHandler(alliance_join,          pattern="^alliance_join_"))
    app.add_handler(CallbackQueryHandler(alliance_leave_confirm, pattern="^alliance_leave_confirm$"))
    app.add_handler(CallbackQueryHandler(alliance_leave_do,      pattern="^alliance_leave_do$"))
    app.add_handler(CallbackQueryHandler(alliance_invite_start,  pattern="^alliance_invite$"))
    app.add_handler(CallbackQueryHandler(alliance_kick_menu,     pattern="^alliance_kick_menu$"))
    app.add_handler(CallbackQueryHandler(alliance_kick_member,   pattern="^alliance_kick_"))
    # Spy
    app.add_handler(CallbackQueryHandler(spy_menu,               pattern="^spy_menu$"))
    app.add_handler(CallbackQueryHandler(spy_launch,             pattern="^spy_launch$"))
    app.add_handler(CallbackQueryHandler(spy_target_selected,    pattern="^spy_target_"))
    app.add_handler(CallbackQueryHandler(spy_confirm,            pattern="^spy_confirm_"))
    app.add_handler(CallbackQueryHandler(set_antistrategy_start, pattern="^set_antistrategy$"))
    app.add_handler(CallbackQueryHandler(spy_result_callback,    pattern="^admin_spy_success_"))
    app.add_handler(CallbackQueryHandler(spy_result_callback,    pattern="^admin_spy_fail_"))
    # Admin (generic — must be AFTER specific patterns)
    app.add_handler(CallbackQueryHandler(admin_callback,         pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(admin_callback,         pattern="^confirm_reset$"))
    app.add_handler(CallbackQueryHandler(set_country_vip,        pattern="^set_country_vip_"))

    # Messages
    app.add_handler(MessageHandler(filters.PHOTO, handle_bayanie_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, master_text_handler))

    # Jobs
    app.job_queue.run_repeating(daily_income_job,    interval=86400, first=60)
    app.job_queue.run_repeating(defender_reminder_job, interval=3600, first=300)

    print("🤖 بات جنگ جهانی دوم شروع به کار کرد!")

    async def _run():
        async with app:
            await app.start()
            # حذف آپدیت‌های قدیمی
            try:
                await app.bot.delete_webhook(drop_pending_updates=True)
            except Exception:
                pass
            offset = None
            try:
                while True:
                    try:
                        updates = await app.bot.get_updates(
                            offset=offset,
                            timeout=30,
                        )
                        for update in updates:
                            await app.process_update(update)
                            offset = update.update_id + 1
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(f"❌ Polling error: {e}")
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await app.stop()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
