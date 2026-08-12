import os
import sys
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime

import database
import gemini_service

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN is not set in .env")
    sys.exit(1)

# Initialize database
database.init_db()

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# In-memory user states
USER_STATES = {}

# Constants for states
STATE_NORMAL = "normal"
STATE_WAITING_IMAGE = "waiting_for_image"

# Keyboards
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_scan = types.KeyboardButton("📷 Ovqatni scan qilish")
    btn_history = types.KeyboardButton("📋 Skan qilinganlar")
    btn_today = types.KeyboardButton("📅 Bugungi statistika")
    keyboard.add(btn_scan)
    keyboard.add(btn_history, btn_today)
    return keyboard

def get_clear_confirm_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn_yes = types.InlineKeyboardButton("✅ Ha, o'chirish", callback_data="clear_history_yes")
    btn_no = types.InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data="clear_history_no")
    keyboard.add(btn_yes, btn_no)
    return keyboard

def get_clear_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    btn_clear = types.InlineKeyboardButton("🗑 Tarixni tozalash", callback_data="clear_history_confirm")
    keyboard.add(btn_clear)
    return keyboard

def get_cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_back = types.KeyboardButton("⬅️ Ortga qaytish")
    keyboard.add(btn_back)
    return keyboard


# Handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    USER_STATES[user_id] = STATE_NORMAL
    
    welcome_text = (
        "Salom! Men **SnapCal** botiman. 🍕🤖\n\n"
        "Men siz yuborgan ovqat rasmini tahlil qilib, undagi kaloriya, oqsil, uglevod va yog' miqdorini aniqlab beraman.\n\n"
        "**Asosiy imkoniyatlarim:**\n"
        "1. 📷 **Ovqatni scan qilish** - Ovqat rasmini yuboring va ozuqaviy qiymatini bilib oling.\n"
        "2. 📋 **Skan qilinganlar** - Siz skan qilgan barcha yeguliklar tarixi.\n"
        "3. 📅 **Bugungi statistika** - Bugungi kun davomida skan qilingan taomlar va jami hisobot.\n\n"
        "Boshlash uchun quyidagi menyudan foydalaning:"
    )
    
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode="Markdown", 
        reply_markup=get_main_keyboard()
    )


@bot.message_handler(func=lambda msg: msg.text == "📷 Ovqatni scan qilish")
def prompt_for_image(message):
    user_id = message.from_user.id
    USER_STATES[user_id] = STATE_WAITING_IMAGE
    
    bot.send_message(
        message.chat.id, 
        "Iltimos, ovqatning rasmini yuboring yoki suratga olib tashlang... 📸",
        reply_markup=get_cancel_keyboard()
    )


@bot.message_handler(func=lambda msg: msg.text == "⬅️ Ortga qaytish")
def cancel_action(message):
    user_id = message.from_user.id
    USER_STATES[user_id] = STATE_NORMAL
    
    bot.send_message(
        message.chat.id,
        "Asosiy menyuga qaytdingiz. Boshlash uchun quyidagi menyudan foydalaning:",
        reply_markup=get_main_keyboard()
    )


@bot.message_handler(func=lambda msg: msg.text == "📋 Skan qilinganlar")
def show_scanned_foods(message):
    user_id = message.from_user.id
    USER_STATES[user_id] = STATE_NORMAL
    
    scans = database.get_user_scans(user_id, limit=10)
    
    if not scans:
        bot.send_message(
            message.chat.id,
            "Siz hali birorta ham ovqatni skan qilmadingiz. Rasm yuborish uchun **📷 Ovqatni scan qilish** tugmasini bosing.",
            parse_mode="Markdown"
        )
        return
        
    text = "📋 **Siz skan qilgan oxirgi yeguliklar ro'yxati:**\n\n"
    for i, scan in enumerate(scans, 1):
        # Format timestamp to show date and time nicely
        # Input format: 'YYYY-MM-DD HH:MM:SS'
        try:
            dt = datetime.strptime(scan['timestamp'], '%Y-%m-%d %H:%M:%S')
            time_str = dt.strftime('%d-%m-%Y %H:%M')
        except:
            time_str = scan['timestamp']
            
        text += f"{i}. **{scan['food_name']}**\n"
        text += f"   🔥 {scan['calories']} kcal | 💪 {scan['protein']}g | 🍞 {scan['carbs']}g | 🥑 {scan['fat']}g\n"
        text += f"   🕒 {time_str}\n\n"
        
    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=get_clear_keyboard()
    )


@bot.message_handler(func=lambda msg: msg.text == "📅 Bugungi statistika")
def show_today_stats(message):
    user_id = message.from_user.id
    USER_STATES[user_id] = STATE_NORMAL
    
    summary = database.get_daily_summary(user_id)
    
    # Format date nicely
    try:
        dt = datetime.strptime(summary['date'], '%Y-%m-%d')
        formatted_date = dt.strftime('%d-%m-%Y')
    except:
        formatted_date = summary['date']
        
    text = (
        f"📅 **Bugungi statistika ({formatted_date}, {summary['day_of_week']}):**\n\n"
        f"⏱ **Bugun iste'mol qilingan yeguliklar:**\n"
    )
    
    if not summary['scans']:
        text += "• _Bugun hali hech qanday ovqat skan qilinmadi._\n\n"
    else:
        for scan in summary['scans']:
            try:
                # Extract time part HH:MM
                dt_time = datetime.strptime(scan['timestamp'], '%Y-%m-%d %H:%M:%S')
                time_part = dt_time.strftime('%H:%M')
            except:
                time_part = scan['timestamp']
                
            text += f"• **{time_part}** - {scan['food_name']} ({scan['calories']} kcal)\n"
        text += "\n"
        
    totals = summary['totals']
    text += (
        f"📊 **Jami bugungi ozuqa miqdori:**\n"
        f"🔥 **Kaloriya:** {totals['total_calories']:.1f} kcal\n"
        f"💪 **Oqsil (protein):** {totals['total_protein']:.1f} g\n"
        f"🍞 **Uglevod (carbs):** {totals['total_carbs']:.1f} g\n"
        f"🥑 **Yog' (fat):** {totals['total_fat']:.1f} g\n"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


# Inline keyboard query handlers
@bot.callback_query_handler(func=lambda call: call.data == "clear_history_confirm")
def confirm_clear_history(call):
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_clear_confirm_keyboard()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "clear_history_yes")
def clear_history_yes(call):
    user_id = call.from_user.id
    database.clear_user_history(user_id)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗑 **Sizning barcha skan qilgan taomlaringiz tarixi muvaffaqiyatli o'chirildi!**",
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id, text="Tarix tozalandi!")

@bot.callback_query_handler(func=lambda call: call.data == "clear_history_no")
def clear_history_no(call):
    # Restore the history message layout (or just notify cancelled)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ **Amal bekor qilindi.** Tarix o'chirilgani yo'q.",
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id, text="Bekor qilindi")


# Photo handler
@bot.message_handler(content_types=['photo'])
def handle_food_photo(message):
    user_id = message.from_user.id
    
    # We process photos even if the user didn't explicitly click "Scan food"
    # This makes the UX much better.
    USER_STATES[user_id] = STATE_NORMAL
    
    # Check if Gemini API key is configured
    if not os.getenv("GEMINI_API_KEY"):
        error_msg = (
            "⚠️ **Tizim sozlamalari xatosi:**\n"
            "Gemini API kaliti topilmadi (`GEMINI_API_KEY` bo'sh).\n"
            "Iltimos, bot administratoriga murojaat qiling yoki `.env` faylini to'ldiring."
        )
        bot.send_message(message.chat.id, error_msg, parse_mode="Markdown")
        return

    # Inform user that we are analyzing
    processing_msg = bot.send_message(
        message.chat.id, 
        "Rasmni yuklab olyapman va tahlil qilyapman, iltimos kuting... ⏳",
        reply_markup=get_main_keyboard()
    )
    
    try:
        # Create temp folder if not exists
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download the largest photo size
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_file_path = os.path.join(temp_dir, f"temp_{user_id}.jpg")
        with open(temp_file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # Analyze using Gemini Service
        nutrition_data = gemini_service.analyze_food_image(temp_file_path)
        
        # Delete temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        if not nutrition_data:
            raise ValueError("Gemini returned invalid analysis.")
            
        # Save to DB
        database.save_scan(
            user_id=user_id,
            food_name=nutrition_data['food_name'],
            calories=nutrition_data['calories'],
            protein=nutrition_data['protein'],
            carbs=nutrition_data['carbs'],
            fat=nutrition_data['fat'],
            description=nutrition_data['description']
        )
        
        # Format and send success message
        success_text = (
            f"✅ **Muvaffaqiyatli skan qilindi!**\n\n"
            f"🍔 **Taom nomi:** {nutrition_data['food_name']}\n"
            f"📝 **Tavsif:** {nutrition_data['description']}\n\n"
            f"📊 **Ozuqaviy qiymati (Taxminiy porsiya bo'yicha):**\n"
            f"🔥 **Kaloriya:** {nutrition_data['calories']} kcal\n"
            f"💪 **Oqsil (protein):** {nutrition_data['protein']} g\n"
            f"🍞 **Uglevod (carbs):** {nutrition_data['carbs']} g\n"
            f"🥑 **Yog' (fat):** {nutrition_data['fat']} g\n\n"
            f"ℹ️ _Eslatma: Ma'lumotlar sun'iy intellekt tomonidan rasm asosida taxminiy hisoblangan._"
        )
        
        bot.delete_message(message.chat.id, processing_msg.message_id)
        bot.send_message(message.chat.id, success_text, parse_mode="Markdown")
        
    except Exception as e:
        print(f"Error handling photo: {e}")
        bot.delete_message(message.chat.id, processing_msg.message_id)
        
        error_reply = (
            "❌ **Rasm tahlilida xatolik yuz berdi.**\n\n"
            "Iltimos, quyidagilarni tekshiring:\n"
            "1. Rasmda ovqat aniq va yorug' joyda ko'ringanmi?\n"
            "2. Internet aloqasi yaxshimi?\n\n"
            "Iltimos, boshqa rasm yuborib qaytadan urinib ko'ring."
        )
        bot.send_message(message.chat.id, error_reply, parse_mode="Markdown")


# Catch-all text handler
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id, STATE_NORMAL)
    
    if state == STATE_WAITING_IMAGE:
        bot.send_message(
            message.chat.id,
            "Sizdan ovqatning rasmini kutyapman. Iltimos, faqat rasm yuboring yoki bekor qilish uchun **⬅️ Ortga qaytish** tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "Tushunarsiz buyruq. Boshlash uchun menyu tugmalaridan foydalaning yoki /start buyrug'ini yuboring.",
            reply_markup=get_main_keyboard()
        )


if __name__ == '__main__':
    print("Bot is starting...")
    bot.infinity_polling()
