import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import requests
import sys

# --- Configuration ---
# WARNING: Do not share this token publicly.
BOT_TOKEN = "8264539179:AAHjBO3nfMY1RMhtrNJFdEE_2vEGxnnAHGA"

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Dictionary to store user states and data temporarily
user_states = {}

def create_start_keyboard():
    """Creates a persistent keyboard with a single /start button."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(KeyboardButton('/start'))
    return markup

def get_family_owner_details(username, password):
    """
    This function contains the core logic from your original script.
    It takes a username and password, performs the API calls, and returns the results.
    """
    # 1. Get Access Token
    auth_url = 'https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token'
    auth_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'okhttp/4.11.0'
    }
    auth_data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_secret': '95fd95fb-7489-4958-8ae6-d31a525cd20a',
        'client_id': 'ana-vodafone-app'
    }

    try:
        r = requests.post(auth_url, headers=auth_headers, data=auth_data, timeout=10)
        
        if r.status_code != 200:
            return False, f"فشل المصادقة. كود الحالة: {r.status_code}. يرجى التحقق من بياناتك."

        token_data = r.json()
        access_token = token_data.get('access_token')
        if not access_token:
            return False, "فشل في الحصول على توكن الدخول من الاستجابة."

    except requests.exceptions.RequestException as e:
        return False, f"حدث خطأ في الشبكة أثناء المصادقة: {e}"
    except Exception as e:
        return False, f"حدث خطأ غير متوقع أثناء المصادقة: {e}"

    # 2. Get Family Group Details
    family_url = 'https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup?type=Family'
    family_headers = {
        'Accept': 'application/json',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip',
        'User-Agent': 'okhttp/4.11.0',
        'channel': 'MOBILE',
        'useCase': 'Promo',
        'Authorization': 'Bearer ' + access_token,
        'api-version': 'v2',
        'x-agent-operatingsystem': '11',
        'clientId': 'AnaVodafoneAndroid',
        'x-agent-device': 'OPPO CPH2059',
        'x-agent-version': '2024.3.3',
        'x-agent-build': '593',
        'msisdn': username,
        'Host': 'mobile.vodafone.com.eg'
    }

    try:
        r2 = requests.get(family_url, headers=family_headers, timeout=10)

        if r2.status_code != 200:
            return False, f"فشل في جلب تفاصيل العائلة. كود الحالة: {r2.status_code}."

        data = r2.json()
        owner_number = ""
        member_numbers = []

        if not data:
            return False, "لم يتم العثور على بيانات. قد لا تكون مشتركًا في مجموعة عائلة."

        members = data[0].get('parts', {}).get('member', [])
        
        for member in members:
            member_type = member.get('type')
            member_id_list = member.get('id', [])
            
            if member_id_list:
                member_id = member_id_list[0].get('value')
                if member_type == 'Owner':
                    owner_number = member_id
                elif member_type == 'Member':
                    member_numbers.append(member_id)

        if not owner_number and not member_numbers:
             return False, "تعذر العثور على معلومات المالك أو الأعضاء. قد لا تكون جزءًا من مجموعة عائلة."

        return True, {"owner": owner_number, "members": member_numbers}

    except (KeyError, IndexError) as e:
        return False, f"تعذر تحليل استجابة الواجهة البرمجية. قد يكون هيكل البيانات قد تغير. الخطأ: {e}"
    except requests.exceptions.RequestException as e:
        return False, f"حدث خطأ في الشبكة أثناء جلب تفاصيل العائلة: {e}"
    except Exception as e:
        return False, f"حدث خطأ غير متوقع أثناء جلب تفاصيل العائلة: {e}"


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles the /start and /help commands, and resets the user's state."""
    chat_id = message.chat.id
    # Clear any previous state for this user
    user_states.pop(chat_id, None)

    welcome_text = (
        "🔥 أهلاً بك في بوت معرفة رقم الأونر!\n\n"
        "فضلاً ادعوا وقولوا:\n\n"
        "(يارب شادي يتجوز مريم) ❤️\n\n"
        "لبدء الاستخدام، من فضلك أرسل رقم الهاتف."
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=create_start_keyboard())
    bot.register_next_step_handler_by_chat_id(chat_id, process_username_step)

def process_username_step(message):
    """Asks for the user's password after getting the username."""
    try:
        if message.text == '/start':
            send_welcome(message)
            return

        chat_id = message.chat.id
        username = message.text

        # Store the username in the state dictionary
        user_states[chat_id] = {'username': username}
        
        bot.send_message(chat_id, "تمام! الآن، من فضلك أرسل كلمة المرور.", reply_markup=create_start_keyboard())
        bot.register_next_step_handler_by_chat_id(chat_id, process_password_step)
    except Exception as e:
        bot.send_message(message.chat.id, 'عفوًا! حدث خطأ ما. يرجى المحاولة مرة أخرى باستخدام /start.', reply_markup=create_start_keyboard())

def process_password_step(message):
    """Processes the credentials and sends the result."""
    try:
        if message.text == '/start':
            send_welcome(message)
            return
            
        chat_id = message.chat.id
        password = message.text
        
        # Retrieve username from state
        user_data = user_states.get(chat_id)
        if not user_data or 'username' not in user_data:
            bot.send_message(chat_id, "حدث خطأ ما، يرجى البدء من جديد بالضغط على /start.", reply_markup=create_start_keyboard())
            return
            
        username = user_data['username']

        # Clear state after use
        user_states.pop(chat_id, None)

        bot.send_message(chat_id, "🔍 جاري التحقق من بياناتك... برجاء الانتظار.", reply_markup=create_start_keyboard())

        success, result = get_family_owner_details(username, password)

        if success:
            owner = result.get("owner", "غير موجود")
            members = result.get("members", [])
            
            if owner.startswith('2'):
                owner = owner[1:]

            processed_members = [m[1:] if m.startswith('2') else m for m in members]
            members_text = ", ".join(processed_members) if processed_members else "لا يوجد أعضاء."
            
            response_text = (
                f"✅ **تم بنجاح!**\n\n"
                f"👑 **رقم الأونر:**\n`{owner}`\n\n"
                f"👥 **الأعضاء:**\n`{members_text}`"
            )
            bot.send_message(chat_id, response_text, parse_mode="Markdown", reply_markup=create_start_keyboard())
        else:
            error_message = f"❌ **خطأ:**\n\n{result}"
            bot.send_message(chat_id, error_message, parse_mode="Markdown", reply_markup=create_start_keyboard())

    except Exception as e:
        bot.send_message(message.chat.id, f'حدث خطأ غير متوقع: {e}. يرجى المحاولة مرة أخرى باستخدام /start.', reply_markup=create_start_keyboard())

if __name__ == "__main__":
    print("البوت قيد التشغيل...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"حدث خطأ أثناء التشغيل: {e}", file=sys.stderr)

# python family.py
