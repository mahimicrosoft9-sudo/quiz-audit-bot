import os
import sys
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

import config
import db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("audit_bot")

# Admin Bot Token
AUDIT_BOT_TOKEN = os.getenv("AUDIT_BOT_TOKEN", "8886544302:AAG9u_Xcv_n4mwOSTQzg4i66_F41QpNgN5Y").strip()
OWNER_ID = config.OWNER_ID or 6416451659

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def get_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📊 Latest Quiz Report", callback_data="aud_latest"),
        ],
        [
            InlineKeyboardButton("🟢 Present", callback_data="aud_present"),
            InlineKeyboardButton("⏰ Late Joiners", callback_data="aud_late")
        ],
        [
            InlineKeyboardButton("⚠️ Left Mid-way", callback_data="aud_left"),
            InlineKeyboardButton("🔴 Absent", callback_data="aud_absent")
        ],
        [
            InlineKeyboardButton("📜 Recent Quizzes History", callback_data="aud_history")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_owner(user.id):
        await update.message.reply_text("⛔ You are not authorized to access this Audit Bot.")
        return

    welcome_text = (
        f"👋 **Namaste {user.first_name}!**\n\n"
        f"🤖 **Quiz Audit & Attendance Bot Control Panel**\n"
        f"Yahan aap apne Quiz group ke members ki live attendance, late joiners, "
        f"aur beech me quiz chhorne walo ka pura audit dekh sakte hain.\n\n"
        f"Niche diye buttons se option select karein 👇"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if not user or not is_owner(user.id):
        return

    data = query.data
    reports = db.get_latest_quiz_reports(limit=5)
    latest_report = reports[0] if reports else None

    if data == "aud_menu":
        await query.edit_message_text(
            "🤖 **Quiz Audit & Attendance Bot Control Panel**\n\nNiche diye buttons se option select karein 👇",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        return

    if not latest_report:
        no_data_text = (
            "⚠️ **Abhi koi Quiz Report database me available nahi hai!**\n\n"
            "Jab main bot se koi quiz complete hoga, attendance report automatic yahan aa jayegi."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="aud_menu")]])
        await query.edit_message_text(no_data_text, reply_markup=back_kb, parse_mode="Markdown")
        return

    rep_data = latest_report.get("report_data", {})
    quiz_name = latest_report.get("quiz_name", "Quiz")
    total_q = latest_report.get("total_q", 0)
    ts = latest_report.get("timestamp", 0)
    date_str = datetime.fromtimestamp(ts).strftime("%d %b %Y, %I:%M %p") if ts else "Recent"

    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="aud_menu")]])

    if data == "aud_latest":
        present = rep_data.get("present", [])
        late = rep_data.get("late", [])
        left = rep_data.get("left_midway", [])
        absent = rep_data.get("absent", [])

        text = (
            f"📊 *LATEST QUIZ ATTENDANCE OVERVIEW*\n"
            f"────────────────────────────\n"
            f"📝 *Quiz:* {quiz_name}\n"
            f"🕒 *Date:* {date_str}\n"
            f"❓ *Questions:* {total_q}\n\n"
            f"🟢 *Present (Full):* {len(present)} members\n"
            f"⏰ *Late Joiners:* {len(late)} members\n"
            f"⚠️ *Left Mid-way:* {len(left)} members\n"
            f"🔴 *Absent:* {len(absent)} members\n\n"
            f"_Kisi category ki poori list dekhne ke liye menu se button select karein._"
        )
        await query.edit_message_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")

    elif data == "aud_present":
        present = rep_data.get("present", [])
        lines = [f"🟢 *PRESENT MEMBERS ({len(present)})*", f"📝 *Quiz:* {quiz_name}", "────────────────────────────"]
        if present:
            lines.extend(present)
        else:
            lines.append("• Koi nahi")
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb, parse_mode="Markdown")

    elif data == "aud_late":
        late = rep_data.get("late", [])
        lines = [f"⏰ *LATE JOINERS ({len(late)})*", f"📝 *Quiz:* {quiz_name}", "────────────────────────────"]
        if late:
            lines.extend(late)
        else:
            lines.append("• Koi member late nahi aaya! 🎉")
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb, parse_mode="Markdown")

    elif data == "aud_left":
        left = rep_data.get("left_midway", [])
        lines = [f"⚠️ *LEFT MID-WAY ({len(left)})*", f"📝 *Quiz:* {quiz_name}", "────────────────────────────"]
        if left:
            lines.extend(left)
        else:
            lines.append("• Kisi ne bhi bich me quiz nahi chhora! 👏")
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb, parse_mode="Markdown")

    elif data == "aud_absent":
        absent = rep_data.get("absent", [])
        lines = [f"🔴 *ABSENT MEMBERS ({len(absent)})*", f"📝 *Quiz:* {quiz_name}", "────────────────────────────"]
        if absent:
            lines.extend(absent)
        else:
            lines.append("• Sabhi members ne attend kiya! 🌟")
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb, parse_mode="Markdown")

    elif data == "aud_history":
        lines = ["📜 *RECENT QUIZZES HISTORY*", "────────────────────────────"]
        for idx, r in enumerate(reports, 1):
            q_name = r.get("quiz_name", "Quiz")
            r_ts = r.get("timestamp", 0)
            d_str = datetime.fromtimestamp(r_ts).strftime("%d/%m %I:%M%p") if r_ts else "N/A"
            r_data = r.get("report_data", {})
            p_cnt = len(r_data.get("present", [])) + len(r_data.get("late", []))
            lines.append(f"{idx}. *{q_name}* ({d_str}) - {p_cnt} attended")
        lines.append("\n_Latest quiz report dekhne ke liye Main Menu jayein._")
        await query.edit_message_text("\n".join(lines), reply_markup=back_kb, parse_mode="Markdown")

def main():
    print("🚀 Starting Audit & Attendance Bot...")
    app = ApplicationBuilder().token(AUDIT_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("report", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
