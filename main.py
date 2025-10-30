# -*- coding: utf-8 -*-
import telebot
import os
import time  # টাইপিং এর জন্য
import re  # Placeholder রিপ্লেস করার জন্য
import threading  # ⭐️ নতুন: অটো-ডিলিটের জন্য থ্রেডিং
from telebot import types
from replit import db  # ডেটাবেস (মেমোরি)
import requests  # Error handling এর জন্য

# --- সেটিংস ---
try:
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    if not BOT_TOKEN:
        print("ত্রুটি: BOT_TOKEN খুঁজে পাওয়া যায়নি!")
        exit()  # টোকেন না থাকলে বট বন্ধ
except Exception as e:
    print(f"টোকেন লোড করার সময় ত্রুটি: {e}")
    exit()

# বট চালু করছি (Error handling সহ)
try:
    bot = telebot.TeleBot(BOT_TOKEN)
except Exception as e:
    print(f"বট চালু করার সময় ত্রুটি: {e}")
    exit()

# --- ওয়ার্নিং লিমিট ৫ করা হলো ---
MAX_WARNS = 5  # সর্বোচ্চ ওয়ার্নিং সংখ্যা
VALID_BLOCKLIST_MODES = ['nothing', 'ban', 'mute', 'kick',
                         'warn']  # ব্ল্যাকলিস্ট মোড
PURGE_LIMIT = 100  # একবারে সর্বোচ্চ মেসেজ ডিলিট
VALID_LOCK_TYPES = [
    'links', 'photos', 'videos', 'documents', 'stickers', 'audio', 'voice',
    'all', 'captcha'
]  # লক টাইপ

# ⭐️ অটো-ডিলিটের জন্য সেটিংস
MEDIA_TYPES_TO_DELETE = [
    'photo', 'video', 'document', 'sticker', 'voice', 'animation', 'audio'
]
MEDIA_DELETE_DELAY = 180  # ৩ মিনিট (১৮০ সেকেন্ড)
RULES_DELETE_DELAY = 180  # ৩ মিনিট (১৮০ সেকেন্ড)
WARN_DELETE_DELAY = 180  # ৩ মিনিট (১৮০ সেকেন্ড)
NOTICE_DELETE_DELAY = 10  # ⭐️ নতুন: ব্ল্যাকলিস্ট/লক নোটিশের জন্য ১০ সেকেন্ড

# বাংলা ডিফল্ট মেসেজ (শুদ্ধ বানান ও {mention} সহ)
DEFAULT_WELCOME = "স্বাগতম, {mention}! 🎉 আপনাকে আমাদের গ্রুপে পেয়ে ভালো লাগছে।"
DEFAULT_GOODBYE = "বিদায়, {mention}! 👋 ভালো থাকবেন।"
DEFAULT_WARN_MSG = "⚠️ {mention}, দয়া করে গ্রুপের নিয়ম মেনে চলুন। আপনাকে সতর্ক করা হলো।"
DEFAULT_BLOCKLIST_MSG = "🚫 {mention}, এই শব্দটি/বাক্যটি গ্রুপে নিষিদ্ধ।"
SUPPORT_GROUP_LINK = "https://t.me/+jrkUWKP2vStiNTJl"  # আপনার সাপোর্ট গ্রুপ লিঙ্ক
UPDATE_CHANNEL_LINK = "https://t.me/+WyCRnYoHPyE0ZmJl"  # আপনার আপডেট চ্যানেল লিঙ্ক
# ⭐️ নতুন ডিফল্ট মেসেজ
DEFAULT_LINK_MSG = "❌ {mention}, গ্রুপে লিঙ্ক দেওয়া নিষিদ্ধ। এখানে শুধু আড্ডা চলবে। লিঙ্ক নিয়ে ভাব মারতে আসবেন না! 😜"


# ----------------------------------------------------
# ⭐️ নতুন: মেসেজ ডিলিট করার থ্রেড ফাংশন
# ----------------------------------------------------
def delete_message_after_delay(chat_id, message_id, delay):
    """
    একটি নির্দিষ্ট সময় পর মেসেজ ডিলিট করার জন্য এই ফাংশনটি একটি নতুন থ্রেডে রান করবে।
    """
    try:
        time.sleep(delay)
        bot.delete_message(chat_id, message_id)
        print(
            f"অটো-ডিলিট: মেসেজ {message_id} চ্যাট {chat_id} থেকে {delay} সেকেন্ড পর ডিলিট করা হলো।"
        )
    except Exception as e:
        print(f"অটো-ডিলিট সম্ভব হয়নি {message_id}: {e}")


# ----------------------------------------------------
# হেল্পার ফাংশন: অ্যাডমিন চেক, সময় পার্স, রিপ্লেস
# ----------------------------------------------------
def is_admin(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ['administrator', 'creator']
    except Exception:
        return False


def parse_time(time_string):
    if not time_string:
        return 0
        seconds = 0
    try:
        time_string = time_string.lower()
        if 'd' in time_string:
            seconds += int(re.search(r'(\d+)d',
                                     time_string).group(1)) * 86400  # দিন
        if 'h' in time_string:
            seconds += int(re.search(r'(\d+)h',
                                     time_string).group(1)) * 3600  # ঘণ্টা
        if 'm' in time_string:
            seconds += int(re.search(r'(\d+)m',
                                     time_string).group(1)) * 60  # মিনিট
        if seconds == 0 and time_string.isdigit():
            seconds = int(time_string) * 60
        return seconds
    except Exception:
        return 0


def replace_placeholders(text, user, chat):
    try:
        chat_title = getattr(chat, 'title', '') or '' if chat else ''
        if not text or not user: return text or ""
        text = text.replace('{fname}', getattr(user, 'first_name', '') or '')
        text = text.replace('{lname}', getattr(user, 'last_name', '') or '')
        fullname = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip(
        )
        text = text.replace('{fullname}', fullname)
        username = getattr(user, 'username', None)
        text = text.replace('{username}',
                            f"@{username}" if username else 'ব্যবহারকারী')
        text = text.replace('{id}', str(getattr(user, 'id', '')))
        text = text.replace('{chatname}', chat_title)
        text = text.replace('{mention}',
                            f"[{fullname}](tg://user?id={user.id})")
        return text
    except Exception as e:
        print(f"Placeholder রিপ্লেস করার সময় ত্রুটি: {e}")
        return text


# ----------------------------------------------------
# ডেটাবেস Key জেনারেটর
# ----------------------------------------------------
def get_db_key(prefix, chat_id, suffix=""):
    try:
        chat_id_str = str(chat_id)
        if suffix:
            suffix_str = str(suffix).lower()
            return f"{prefix}_{chat_id_str}_{suffix_str}"
        else:
            return f"{prefix}_{chat_id_str}"
    except Exception as e:
        print(f"DB key তৈরিতে ত্রুটি: {e}")
        return f"{prefix}_error_{str(time.time())}"


def get_lock_key(chat_id):
    return get_db_key("locks", chat_id)


def get_warns_key(chat_id, user_id):
    return get_db_key("warns", chat_id, user_id)


def get_note_key(chat_id, notename):
    return get_db_key("note", chat_id, notename)


def get_config_key(chat_id, config_name):
    return get_db_key("config", chat_id, config_name)


def get_blocklist_key(chat_id):
    return get_db_key("blocklist", chat_id)


def get_filter_key(chat_id, keyword):
    return get_db_key("filter", chat_id, keyword)


def get_welcome_key(chat_id):
    return get_db_key("welcome", chat_id)


def get_goodbye_key(chat_id):
    return get_db_key("goodbye_msg", chat_id)


def get_warn_msg_key(chat_id):
    return get_db_key("warn_msg", chat_id)


def get_blocklist_msg_key(chat_id):
    return get_db_key("blocklist_msg", chat_id)


def get_link_msg_key(chat_id):
    return get_db_key("link_msg", chat_id)  # ⭐️ নতুন: লিঙ্ক মেসেজের Key


# ----------------------------------------------------
# '/start' কমান্ড (আপডেটেড মেসেজ)
# ----------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        chat_type = message.chat.type
        bot_info = bot.get_me()
        bot_name = bot_info.first_name
        bot_username = bot_info.username

        # ⭐️⭐️⭐️ START মেসেজ আপডেট ⭐️⭐️⭐️
        start_text = f"""
👋 হ্যালো! আমি **{bot_name}**। আপনার গ্রুপের বিশ্বস্ত 管理 (ম্যানেজমেন্ট) সহকারী।

আমাকে আপনার গ্রুপে অ্যাড করে **অ্যাডমিন** বানান, আর আমি গ্রুপকে রাখব সুরক্ষিত ও স্প্যাম-মুক্ত! ✨

**আমার প্রধান ক্ষমতাগুলো:**

👮 **অ্যাডমিন ও সুরক্ষা:**
    `Kick`, `Ban`, `Unban`, `Mute`, `Warn`, `Blocklist` (খারাপ শব্দ নিয়ন্ত্রণ) ইত্যাদি।

🧹 **অটো ক্লিনিং ও সেফটি (নতুন):**
    ✅ **Join/Leave মেসেজ** অটো ডিলিট হয়।
    ✅ **মিডিয়া অটো-ডিলিট** চালু আছে (৩ মিনিট পর ডিলিট, অ্যাডমিনদেরটা থাকবে)।
    ✅ **আপত্তিকর শব্দ/ইমোজি** ব্যবহার করলেই ডিলেট হয়ে যাবে।
    ✅ **কাস্টম লিঙ্ক মেসেজ** সেট করার সুবিধা আছে।

▶️ **অটোমেশন ও ইউটিলিটি:**
    `Filters` (অটো-রিপ্লাই), `Notes` (তথ্য সেভ), `Rules` (নিয়মাবলী)।

**উদাহরণ:**
    - লিঙ্ক মেসেজ সেট: `/setlinkmsg [আপনার মেসেজ]`
    - মিডিয়া ক্লিন বন্ধ: `/autodeletemedia off`

সম্পূর্ণ ব্যবহারবিধি জানতে, আমাকে গ্রুপে যুক্ত করার পর `/help` কমান্ড দিন।

👇 **এখনই আমাকে আপনার গ্রুপে যোগ করুন:**
"""
        # ⭐️⭐️⭐️ START মেসেজ আপডেট শেষ ⭐️⭐️⭐️

        if chat_type == 'private' or chat_type in ['group', 'supergroup']:
            markup = types.InlineKeyboardMarkup()
            add_to_group_button = types.InlineKeyboardButton(
                text="➕ আমাকে গ্রুপে যুক্ত করুন",
                url=f"https://t.me/{bot_username}?startgroup=true")
            markup.add(add_to_group_button)
            bot.reply_to(message,
                         start_text,
                         reply_markup=markup,
                         parse_mode="Markdown")

    except Exception as e:
        print(f"'/start' কমান্ডে ত্রুটি: {e}")


# ----------------------------------------------------
# নতুন সদস্যকে স্বাগত জানানো / বিদায় জানানো
# ----------------------------------------------------
@bot.chat_member_handler()
def handle_chat_member(message: types.ChatMemberUpdated):
    try:
        user = message.new_chat_member.user
        chat_id = message.chat.id
        status = message.new_chat_member.status
        chat = message.chat

        # ⭐️ FINAL: ডিফল্ট অটো-ক্লিন সেটিংস চালু করা হচ্ছে
        if status == "member":
            if db.get(get_config_key(chat_id, "cleanservice"), None) is None:
                db[get_config_key(chat_id, "cleanservice")] = True
                print(
                    f"চ্যাট {chat_id}-এ CleanService ডিফল্টভাবে চালু করা হলো।")
            if db.get(get_config_key(chat_id, "autodeletemedia"),
                      None) is None:
                db[get_config_key(chat_id, "autodeletemedia")] = True
                print(
                    f"চ্যাট {chat_id}-এ Media Auto-Delete ডিফল্টভাবে চালু করা হলো।"
                )
        # ⭐️ FINAL: ডিফল্ট অটো-ক্লিন সেটিংস শেষ

        if status == "member":
            current_locks = db.get(get_lock_key(chat_id), [])
            if 'captcha' in current_locks:
                try:
                    bot.restrict_chat_member(
                        chat_id,
                        user.id,
                        can_send_messages=False,
                        until_date=int(time.time() +
                                       600))  # ১০ মিনিটের জন্য মিউট
                    markup = types.InlineKeyboardMarkup()
                    verify_button = types.InlineKeyboardButton(
                        text="🤖 আমি রোবট নই (Verify)",
                        callback_data=f"verify_{user.id}")  # শুদ্ধ বানান
                    markup.add(verify_button)
                    captcha_msg = db.get(
                        get_config_key(chat_id, "captcha_text"),
                        f"স্বাগতম, {user.first_name}! \n\nগ্রুপে কথা বলার আগে, অনুগ্রহ করে নিচের বাটনে ক্লিক করে ভেরিফাই করুন (স্প্যাম রোধ করার জন্য)।"
                    )
                    bot.send_message(chat_id, captcha_msg, reply_markup=markup)
                except telebot.apihelper.ApiException as api_e:
                    if "not enough rights" in str(api_e).lower():
                        print(
                            f"CAPTCHA ত্রুটি চ্যাট {chat_id}: বটের 'Restrict Members' পারমিশন নেই।"
                        )
                    else:
                        print(f"CAPTCHA প্রক্রিয়ায় ত্রুটি: {api_e}")
                except Exception as e:
                    print(f"CAPTCHA তে সাধারণ ত্রুটি: {e}")
            else:
                welcome_template = db.get(get_welcome_key(chat_id),
                                          DEFAULT_WELCOME)
                welcome_text = replace_placeholders(welcome_template, user,
                                                    chat)
                if welcome_text:
                    bot.send_message(chat_id,
                                     welcome_text,
                                     parse_mode="Markdown",
                                     disable_web_page_preview=True)
        elif status == "left" or status == "kicked":
            if db.get(get_config_key(chat_id, "goodbye"), True):  # ডিফল্ট True
                goodbye_template = db.get(get_goodbye_key(chat_id),
                                          DEFAULT_GOODBYE)
                goodbye_text = replace_placeholders(goodbye_template, user,
                                                    chat)
                if goodbye_text:
                    bot.send_message(chat_id,
                                     goodbye_text,
                                     parse_mode="Markdown",
                                     disable_web_page_preview=True)
    except Exception as e:
        print(f"Chat Member আপডেটে ত্রুটি: {e}")


# ----------------------------------------------------
# কাস্টম Welcome/Goodbye কমান্ড
# ----------------------------------------------------
@bot.message_handler(commands=['setwelcome', 'setgoodbye'])
def set_custom_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0]
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        # --- ⭐️ ফিক্স: \n\n সমস্যা সমাধানের জন্য 'raw_text' ব্যবহার ---
        try:
            raw_text = message.json.get('text',
                                        message.json.get('caption', ''))
            custom_text = raw_text.split(maxsplit=1)[1]
        except (IndexError, AttributeError):
            bot.reply_to(
                message,
                f"❓ ব্যবহার: `{command} [আপনার মেসেজ এখানে লিখুন]`\nPlaceholder: {{fname}}, {{lname}}, {{fullname}}, {{username}}, {{id}}, {{chatname}}, {{mention}}"
            )
            return
        # --- ⭐️ ফিক্স শেষ ---

        if command == '/setwelcome':
            db[get_welcome_key(chat_id)] = custom_text
            bot.reply_to(message,
                         "✅ নতুন স্বাগত বার্তা সফলভাবে সেট করা হয়েছে。")
        elif command == '/setgoodbye':
            db[get_goodbye_key(chat_id)] = custom_text
            bot.reply_to(message,
                         "✅ নতুন বিদায় বার্তা সফলভাবে সেট করা হয়েছে。")
    except Exception as e:
        print(f"কাস্টম মেসেজ সেটে ত্রুটি ({command}): {e}")
        bot.reply_to(message, "⚠️ দুঃখিত, বার্তাটি সেভ করতে সমস্যা হয়েছে。")


@bot.message_handler(commands=['resetwelcome', 'resetgoodbye'])
def reset_custom_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0]
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        if command == '/resetwelcome':
            db_key = get_welcome_key(chat_id)
            msg = "স্বাগত"
        elif command == '/resetgoodbye':
            db_key = get_goodbye_key(chat_id)
            msg = "বিদায়"
        else:
            return
        if db_key in db: del db[db_key]
        bot.reply_to(message, f"✅ {msg} বার্তা ডিফল্টে রিসেট করা হয়েছে。")
    except Exception as e:
        print(f"কাস্টম মেসেজ রিসেটে ত্রুটি ({command}): {e}")
        bot.reply_to(message, "⚠️ দুঃখিত, রিসেট করতে সমস্যা হয়েছে。")


# ----------------------------------------------------
# অ্যাডমিন কমান্ড (Kick, Ban, Unban) (ID দিয়ে আনব্যান সহ)
# ----------------------------------------------------
@bot.message_handler(commands=['kick', 'ban', 'unban'])
def admin_actions(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0]
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if not bot_member.status in ['administrator', 'creator']:
            bot.reply_to(message, "❌ আমাকে প্রথমে এই গ্রুপে অ্যাডমিন বানান।")
            return

        target_user_id = None
        target_user_name = "User"  # ID দিয়ে আনব্যান করার জন্য ডিফল্ট নাম

        # --- ID দিয়ে আনব্যান ---
        if command == '/unban' and not message.reply_to_message:
            try:
                user_id_to_unban = int(message.text.split()[1])
                target_user_id = user_id_to_unban
                target_user_name = f"User ID ({user_id_to_unban})"  # ইউজারনেম যেহেতু জানা নেই
            except (IndexError, ValueError):
                bot.reply_to(
                    message,
                    f"❓ ব্যবহার: `/unban [User ID]` অথবা কোনো মেসেজে রিপ্লাই দিয়ে `/unban` লিখুন।"
                )
                return

        # --- রিপ্লাই-ভিত্তিক সিস্টেম ---
        elif message.reply_to_message:
            target_user = message.reply_to_message.from_user
            target_user_id = target_user.id
            target_user_name = target_user.first_name

            if target_user_id == bot.get_me().id:
                bot.reply_to(message, "😅 আমাকে কিক/ব্যান করতে পারবেন না।")
                return
            if is_admin(chat_id, target_user_id):
                bot.reply_to(message,
                             "❌ আমি অন্য অ্যাডমিনকে মডারেট করতে পারবো না।")
                return

        # --- যদি কোনো টার্গেট না পাওয়া যায় (e.g., /kick without reply) ---
        else:
            bot.reply_to(
                message,
                f"❓ ব্যবহার: যাকে `{command[1:]}` করতে চান, তার মেসেজে রিপ্লাই দিয়ে `{command}` লিখুন।",
                parse_mode="Markdown")
            return

        # --- Action Logic ---
        action_word_bn = ""
        success = False

        if command == '/kick':
            if not bot_member.can_restrict_members:
                bot.reply_to(message, "❌ কিক করার জন্য আমার পারমিশন নেই।")
                return
            bot.kick_chat_member(chat_id, target_user_id)
            bot.unban_chat_member(chat_id,
                                  target_user_id)  # Ensure they can rejoin
            action_word_bn = "কিক"
            success = True

        elif command == '/ban':
            if not bot_member.can_restrict_members:
                bot.reply_to(message, "❌ ব্যান করার জন্য আমার পারমিশন নেই।")
                return
            bot.ban_chat_member(chat_id, target_user_id)
            action_word_bn = "ব্যান"
            success = True

        elif command == '/unban':
            if not bot_member.can_restrict_members:
                bot.reply_to(message, "❌ আনব্যান করার জন্য আমার পারমিশন নেই।")
                return
            bot.unban_chat_member(chat_id,
                                  target_user_id)  # This works with the ID
            action_word_bn = "আনব্যান"
            success = True

        if success:
            bot.reply_to(
                message,
                f"✅ {target_user_name}-কে সফলভাবে {action_word_bn} করা হয়েছে।"
            )

    except telebot.apihelper.ApiException as api_e:
        if "user not found" in str(api_e).lower() or "member not found" in str(
                api_e).lower():
            bot.reply_to(
                message,
                "❌ ব্যবহারকারীকে খুঁজে পাওয়া যায়নি। তিনি কি গ্রুপ ছেড়ে চলে গেছেন বা ID'টি ভুল?"
            )
        elif "can't remove chat owner" in str(api_e).lower():
            bot.reply_to(message, "❌ গ্রুপের মালিককে কিক/ব্যান করা যায় না।")
        else:
            print(f"{command} কমান্ডে API ত্রুটি: {api_e}")
            bot.reply_to(
                message,
                "⚠️ কাজটি করতে সমস্যা হয়েছে। টেলিগ্রাম API থেকে একটি ত্রুটি এসেছে।"
            )
    except Exception as e:
        print(f"{command} কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message,
                     "⚠️ দুঃখিত, কাজটি করতে একটি অপ্রত্যাশিত সমস্যা হয়েছে।")


# ----------------------------------------------------
# Mute (মিউট) সিস্টেম
# ----------------------------------------------------
@bot.message_handler(commands=['mute', 'tmute', 'unmute'])
def mute_actions(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0]
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if not bot_member.status in ['administrator', 'creator'
                                     ] or not bot_member.can_restrict_members:
            bot.reply_to(
                message,
                "❌ আমি অ্যাডমিন নই অথবা সদস্যকে সীমাবদ্ধ করার ('Restrict Members') পারমিশন আমার নেই।"
            )
            return
        if not message.reply_to_message:
            bot.reply_to(
                message,
                f"❓ ব্যবহার: যাকে `{command[1:]}` করতে চান, তার মেসেজে রিপ্লাই দিয়ে `{command}` লিখুন।",
                parse_mode="Markdown")
            return
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        if target_user_id == bot.get_me().id:
            bot.reply_to(message, "😅 আমাকে মিউট করতে পারবেন না।")
            return
        if is_admin(chat_id, target_user_id):
            bot.reply_to(message, "❌ আমি অন্য অ্যাডমিনকে মিউট করতে পারব না।")
            return

        if command == '/unmute':
            bot.restrict_chat_member(chat_id,
                                     target_user_id,
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
            bot.reply_to(
                message,
                f"✅ {target_user.first_name}-কে আনমিউট করা হয়েছে। সে এখন কথা বলতে পারবে।"
            )
        elif command == '/mute':
            bot.restrict_chat_member(chat_id,
                                     target_user_id,
                                     can_send_messages=False)
            bot.reply_to(
                message,
                f"🔇 {target_user.first_name}-কে স্থায়ীভাবে মিউট করা হয়েছে। আনমিউট করার জন্য `/unmute` ব্যবহার করুন।"
            )
        elif command == '/tmute':
            try:
                parts = message.text.split(maxsplit=2)
                time_string = parts[1] if len(parts) > 1 else ""
                duration_seconds = parse_time(time_string)
                if duration_seconds <= 0:
                    bot.reply_to(
                        message,
                        "❓ ভুল সময় ফরম্যাট। ব্যবহার করুন: `/tmute [সময়]` (যেমন: ৩০মি, ১ঘ, ২দি)"
                    )
                    return
                until_date = int(time.time() + duration_seconds)
                bot.restrict_chat_member(chat_id,
                                         target_user_id,
                                         can_send_messages=False,
                                         until_date=until_date)
                bot.reply_to(
                    message,
                    f"🔇 {target_user.first_name}-কে {time_string} সময়ের জন্য মিউট করা হয়েছে।"
                )
            except IndexError:
                bot.reply_to(
                    message,
                    "❓ ব্যবহার: `/tmute [সময়]` (যেমন: ৩০মি, ১ঘ, ২দি)")
    except telebot.apihelper.ApiException as api_e:
        print(f"{command} কমান্ডে API ত্রুটি: {api_e}")
        bot.reply_to(message, "⚠️ কাজটি করতে সমস্যা হয়েছে। পারমিশন চেক করুন।")
    except Exception as e:
        print(f"{command} কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message,
                     "⚠️ দুঃখিত, কাজটি করতে একটি অপ্রত্যাশিত সমস্যা হয়েছে।")


# ----------------------------------------------------
# Rules (নিয়ম) সিস্টেম (আপডেটেড - \n\n দিয়ে ভাগ করা ফিক্সড)
# ----------------------------------------------------
@bot.message_handler(commands=['setrules'])
def set_rules(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        # --- ⭐️ ফিক্স: \n\n সমস্যা সমাধানের জন্য 'raw_text' ব্যবহার ---
        try:
            raw_text = message.json.get('text',
                                        message.json.get('caption', ''))
            rules_text = raw_text.split(maxsplit=1)[1]
        except (IndexError, AttributeError):
            bot.reply_to(
                message,
                "❓ ব্যবহার: `/setrules [আপনার নিয়মগুলো এখানে লিখুন]`")
            return
        # --- ⭐️ ফিক্স শেষ ---

        db[f"rules_{chat_id}"] = rules_text
        bot.reply_to(message, "✅ গ্রুপের নিয়ম সফলভাবে সেভ করা হয়েছে।")
    except Exception as e:
        print(f"'/setrules' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ সেভ করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['rules'])
def show_rules(message):
    try:
        chat_id = message.chat.id
        db_key = f"rules_{chat_id}"

        # --- ⭐️ নতুন: রুলস অটো-ডিলিট চেক ---
        autodelete_rules = db.get(get_config_key(chat_id, "autodeleterules"),
                                  False)
        bot_messages_to_delete = []
        # --- শেষ ---

        if db_key in db:
            full_text = db.get(db_key)  # The full text is already in the DB

            chunk = full_text

            sent_msg = None

            try:
                # ⭐️ FINAL FIX: এখানে আর ভাগ করা হচ্ছে না। যদি 4096 পার হয়, তবে নিচে এরর হ্যান্ডেল হবে।
                sent_msg = bot.reply_to(message, chunk, parse_mode="Markdown")

            except telebot.apihelper.ApiException as e:
                # ⭐️⭐️⭐️ CRITICAL FIX: Too Long বা Can't Parse এরর হলে ⭐️⭐️⭐️
                if "message is too long" in str(
                        e).lower() or "can't parse entities" in str(e).lower():
                    # যদি লম্বা হয়, তবে আমরা বাধ্য হয়ে মেসেজটিকে \n\n দিয়ে ভাগ করে পাঠাবো
                    print(
                        "⚠️ সতর্কতা: রুলস মেসেজটি খুব লম্বা, ভাগ করে পাঠানো হচ্ছে।"
                    )
                    chunks = full_text.split('\n\n')
                    is_first_chunk = True
                    for part in chunks:
                        if not part.strip(): continue
                        plain_text_part = part.replace("\\n", "\n")

                        if is_first_chunk:
                            sent_msg = bot.reply_to(message,
                                                    plain_text_part,
                                                    parse_mode=None)
                            is_first_chunk = False
                        else:
                            sent_msg = bot.send_message(chat_id,
                                                        plain_text_part,
                                                        parse_mode=None)

                        if sent_msg:
                            bot_messages_to_delete.append(sent_msg.message_id)
                        time.sleep(0.5)

                    # যদি একাধিক মেসেজে যায়, তবে /rules কমান্ড ডিলিট হয়ে যাবে
                    if autodelete_rules:
                        try:
                            bot.delete_message(chat_id, message.message_id)
                        except Exception:
                            pass
                    return  # Rules sent, exit function
                # ⭐️⭐️⭐️ CRITICAL FIX শেষ ⭐️⭐️⭐️
                else:
                    print(f"'/rules' পাঠাতে API ত্রুটি: {e}")
                    bot.reply_to(
                        message, "⚠️ নিয়মাবলী দেখাতে একটি API ত্রুটি হয়েছে।")

            if sent_msg and sent_msg.message_id not in bot_messages_to_delete:  # if not split, only one msg id
                bot_messages_to_delete.append(sent_msg.message_id)

        else:
            sent_msg = bot.reply_to(
                message, "❌ এই গ্রুপের জন্য এখনো কোনো নিয়ম সেট করা হয়নি।")
            if sent_msg:
                bot_messages_to_delete.append(sent_msg.message_id)

        # --- ⭐️ নতুন: রুলস ডিলিট লজিক ---
        if autodelete_rules:
            # ইউজারের /rules কমান্ড ডিলিট
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception as e:
                print(f"রুলস কমান্ড ডিলিট করতে পারিনি: {e}")

            # বটের পাঠানো সব মেসেজ ডিলিট
            for msg_id in bot_messages_to_delete:
                threading.Thread(target=delete_message_after_delay,
                                 args=(chat_id, msg_id,
                                       RULES_DELETE_DELAY)).start()
        # --- ⭐️ শেষ ---

    except Exception as e:
        print(f"'/rules' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ দেখাতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Warning (ওয়ার্নিং) সিস্টেম (একক মেসেজ)
# ----------------------------------------------------
def trigger_warn(message, target_user, chat):  # Chat অবজেক্ট যোগ করা হলো
    chat_id = message.chat.id
    target_user_id = target_user.id
    if is_admin(chat_id, target_user_id): return
    try:
        db_key = get_warns_key(chat_id, target_user_id)
        current_warns = db.get(db_key, 0) + 1
        db[db_key] = current_warns
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)

        # --- কাস্টম ওয়ার্ন মেসেজ (ফানি মেসেজটি এখান থেকে আসবে) ---
        warn_template = db.get(get_warn_msg_key(chat_id), DEFAULT_WARN_MSG)
        warn_text = replace_placeholders(warn_template, target_user, chat)

        # --- ওয়ার্নিং কাউন্ট একই মেসেজে যোগ করা হলো ---
        warn_text += f"\n\n🚨 **মোট ওয়ার্নিং:** {current_warns}/{MAX_WARNS}"

        sent_msg = None
        # --- ফিক্স: Markdown Error Handling (যদি ফানি মেসেজে \n থাকে) ---
        try:
            sent_msg = bot.send_message(chat_id,
                                        warn_text,
                                        parse_mode="Markdown")
        except telebot.apihelper.ApiException as e:
            if "can't parse entities" in str(e).lower():
                print(
                    "Markdown পার্সিং-এ ত্রুটি (ওয়ার্নিং)। প্লেইন টেক্সট হিসাবে পাঠানো হচ্ছে।"
                )
                # \n\n কে আসল লাইন ব্রেক-এ পরিণত করা
                plain_text = warn_text.replace("\\n", "\n")
                sent_msg = bot.send_message(chat_id,
                                            plain_text,
                                            parse_mode=None)
            else:
                print(f"ওয়ার্নিং পাঠাতে API ত্রুটি: {e}")
        # --- ফিক্স শেষ ---

        # --- ⭐️ নতুন: ওয়ার্নিং মেসেজ ডিলিট লজিক ---
        if sent_msg:
            threading.Thread(target=delete_message_after_delay,
                             args=(chat_id, sent_msg.message_id,
                                   WARN_DELETE_DELAY)).start()
        # --- ⭐️ শেষ ---

        # --- ব্ল্যাকলিস্ট অ্যাকশনের নোটিশ (WARNING MODE ছাড়া) ---
        action_text = ""
        if current_warns >= MAX_WARNS:
            if bot_member.status in ['administrator', 'creator'
                                     ] and bot_member.can_restrict_members:
                bot.ban_chat_member(chat_id, target_user_id)
                action_text = f"🚨 {target_user.first_name} ওয়ার্নিং লিমিট ({MAX_WARNS}) পার করায় তাকে ব্যান করা হলো।"
                db[db_key] = 0  # ব্যান করার পর ওয়ার্নিং রিসেট
            else:
                action_text = f"🚨 {target_user.first_name} ওয়ার্নিং লিমিট পার করেছে, কিন্তু ব্যান করার পারমিশন আমার নেই।"

        # ⭐️ উন্নতি: এটিকেও অটো-ডিলিট থ্রেডে পাঠানো হলো।
        if action_text:
            action_msg = bot.send_message(chat_id, action_text)
            threading.Thread(target=delete_message_after_delay,
                             args=(chat_id, action_msg.message_id,
                                   NOTICE_DELETE_DELAY)).start()

    except Exception as e:
        print(f"ওয়ার্নিং ট্রিগারে ত্রুটি: {e}")


@bot.message_handler(commands=['warn'])
def warn_user(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        if not is_admin(chat_id, bot.get_me().id):
            bot.reply_to(message,
                         "❌ আমি অ্যাডমিন নই অথবা মিউট করার পারমিশন আমার নেই।")
            return
        if not message.reply_to_message:
            bot.reply_to(
                message,
                "❓ ব্যবহার: যাকে ওয়ার্নিং দিতে চান, তার মেসেজে রিপ্লাই দিয়ে `/warn` লিখুন।"
            )
            return

        # --- ⭐️ নতুন: ইউজারদের /warn কমান্ড ডিলিট করা হচ্ছে ---
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        # --- ⭐️ শেষ ---

        trigger_warn(message, message.reply_to_message.from_user,
                     message.chat)  # Chat অবজেক্ট পাঠানো হলো
    except Exception as e:
        print(f"'/warn' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ ওয়ার্নিং দিতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['warns'])
def check_warns(message):
    try:
        if not message.reply_to_message:
            bot.reply_to(
                message,
                "❓ ব্যবহার: যার ওয়ার্নিং দেখতে চান, তার মেসেজে রিপ্লাই দিয়ে `/warns` লিখুন।"
            )
            return
        target_user = message.reply_to_message.from_user
        db_key = get_warns_key(message.chat.id, target_user.id)
        current_warns = db.get(db_key, 0)
        bot.reply_to(
            message,
            f"ℹ️ {target_user.first_name}-এর মোট ওয়ার্নিং সংখ্যা: {current_warns}/{MAX_WARNS}"
        )
    except Exception as e:
        print(f"'/warns' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ দেখাতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['resetwarns'])
def reset_warns(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        if not message.reply_to_message:
            bot.reply_to(
                message,
                "❓ ব্যবহার: যার ওয়ার্নিং রিসেট করতে চান, তার মেসেজে রিপ্লাই দিয়ে `/resetwarns` লিখুন।"
            )
            return
        target_user = message.reply_to_message.from_user
        db_key = get_warns_key(chat_id, target_user.id)
        if db_key in db: del db[db_key]
        bot.reply_to(
            message,
            f"✅ {target_user.first_name}-এর সব ওয়ার্নিং রিসেট করা হয়েছে।")
    except Exception as e:
        print(f"'/resetwarns' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ রিসেট করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# কাস্টম Warn/Blocklist মেসেজ সেট করার কমান্ড (\n ফিক্সড)
# ----------------------------------------------------
@bot.message_handler(commands=['setwarnmsg', 'setblocklistmsg'])
def set_custom_action_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0]
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        # --- ⭐️ ফিক্স: \n\n সমস্যা সমাধানের জন্য 'raw_text' ব্যবহার ---
        try:
            # message.text ব্যবহার না করে message.json ব্যবহার করা হচ্ছে
            raw_text = message.json.get('text',
                                        message.json.get('caption', ''))
            custom_text = raw_text.split(maxsplit=1)[1]
        except (IndexError, AttributeError):
            bot.reply_to(
                message,
                f"❓ ব্যবহার: `{command} [আপনার মেসেজ]`\n(মেসেজে {{mention}}, {{fname}} ইত্যাদি ব্যবহার করুন)"
            )
            return
        # --- ⭐️ ফিক্স শেষ ---

        if command == '/setwarnmsg':
            db[get_warn_msg_key(chat_id)] = custom_text
            bot.reply_to(message,
                         "✅ নতুন ওয়ার্নিং মেসেজ সফলভাবে সেট করা হয়েছে।")
        elif command == '/setblocklistmsg':
            db[get_blocklist_msg_key(chat_id)] = custom_text
            bot.reply_to(message,
                         "✅ নতুন ব্ল্যাকলিস্ট নোটিশ সফলভাবে সেট করা হয়েছে।")

    except Exception as e:
        print(f"কাস্টম অ্যাকশন মেসেজ সেটে ত্রুটি ({command}): {e}")
        bot.reply_to(message, "⚠️ দুঃখিত, বার্তাটি সেভ করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['resetwarnmsg', 'resetblocklistmsg'])
def reset_custom_action_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0]
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        if command == '/resetwarnmsg':
            db_key = get_warn_msg_key(chat_id)
            msg = "ওয়ার্নিং"
        elif command == '/resetblocklistmsg':
            db_key = get_blocklist_msg_key(chat_id)
            msg = "ব্ল্যাকলিস্ট"
        else:
            return

        if db_key in db: del db[db_key]
        bot.reply_to(message, f"✅ {msg} মেসেজ ডিফল্টে রিসেট করা হয়েছে।")
    except Exception as e:
        print(f"কাস্টম অ্যাকশন মেসেজ রিসেটে ত্রুটি ({command}): {e}")
        bot.reply_to(message, "⚠️ দুঃখিত, রিসেট করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Notes (নোটস) সিস্টেম (\n ফিক্সড)
# ----------------------------------------------------
@bot.message_handler(commands=['save'])
def save_note(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        # --- ⭐️ ফিক্স: \n\n সমস্যা সমাধানের জন্য 'raw_text' ব্যবহার ---
        try:
            raw_text = message.json.get('text',
                                        message.json.get('caption', ''))
            parts = raw_text.split(maxsplit=2)
            if len(parts) < 3:
                bot.reply_to(
                    message, "❓ ব্যবহার: `/save [নোটের_নাম] [নোটের কন্টেন্ট]`")
                return
            notename = parts[1]
            content = parts[2]
        except (IndexError, AttributeError):
            bot.reply_to(message,
                         "❓ ব্যবহার: `/save [নোটের_নাম] [নোটের কন্টেন্ট]`")
            return
        # --- ⭐️ ফিক্স শেষ ---

        db[get_note_key(chat_id, notename)] = content
        bot.reply_to(message, f"✅ নোট '{notename}' সফলভাবে সেভ করা হয়েছে।")
    except Exception as e:
        print(f"'/save' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ সেভ করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['notes'])
def list_notes(message):
    try:
        chat_id = message.chat.id
        prefix = f"note_{chat_id}_"
        note_keys = db.prefix(prefix)
        if not note_keys:
            bot.reply_to(message, "❌ এই গ্রুপে কোনো নোট সেভ করা নেই।")
            return
        note_names = sorted([key.replace(prefix, "") for key in note_keys])
        note_list_text = "🗒️ **সেভ করা নোটসমূহ:**\n" + "\n".join(
            f"- `{name}`"
            for name in note_names) + "\n\nনোট দেখতে `#নোটের_নাম` টাইপ করুন।"
        bot.reply_to(message, note_list_text, parse_mode="Markdown")
    except Exception as e:
        print(f"'/notes' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ তালিকা দেখাতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['clear'])
def clear_note(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        notename = message.text.split(maxsplit=1)[1]
        db_key = get_note_key(chat_id, notename)
        if db_key in db:
            del db[db_key]
            bot.reply_to(message, f"✅ নোট '{notename}' ডিলিট করা হয়েছে।")
        else:
            bot.reply_to(message,
                         f"❌ '{notename}' নামে কোনো নোট খুঁজে পাওয়া যায়নি।")
    except IndexError:
        bot.reply_to(message, "❓ ব্যবহার: `/clear [নোটের_নাম]`")
    except Exception as e:
        print(f"'/clear' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ ডিলিট করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Blocklist (ব্ল্যাকলিস্ট) সিস্টেম
# ----------------------------------------------------
@bot.message_handler(commands=['addblocklist'])
def add_blocklist(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        word = message.text.split(maxsplit=1)[1].lower()
        db_key = get_blocklist_key(chat_id)
        current_list = db.get(db_key, [])
        if word not in current_list:
            current_list.append(word)
            db[db_key] = current_list
            bot.reply_to(message,
                         f"✅ শব্দ '{word}' ব্ল্যাকলিস্টে যোগ করা হয়েছে।")
        else:
            bot.reply_to(message, "ℹ️ এই শব্দটি আগে থেকেই ব্ল্যাকলিস্টে আছে।")
    except IndexError:
        bot.reply_to(message, "❓ ব্যবহার: `/addblocklist [নিষিদ্ধ শব্দ]`")
    except Exception as e:
        print(f"'/addblocklist' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ যোগ করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['rmblocklist'])
def rm_blocklist(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        word = message.text.split(maxsplit=1)[1].lower()
        db_key = get_blocklist_key(chat_id)
        current_list = db.get(db_key, [])
        if word in current_list:
            current_list.remove(word)
            db[db_key] = current_list
            bot.reply_to(
                message,
                f"✅ শব্দ '{word}' ব্ল্যাকলিস্ট থেকে মুছে ফেলা হয়েছে।")
        else:
            bot.reply_to(
                message,
                f"❌ '{word}' শব্দটি ব্ল্যাকলিস্টে খুঁজে পাওয়া যায়নি।")
    except IndexError:
        bot.reply_to(message, "❓ ব্যবহার: `/rmblocklist [নিষিদ্ধ শব্দ]`")
    except Exception as e:
        print(f"'/rmblocklist' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ মুছতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['blocklist'])
def list_blocklist(message):
    try:
        chat_id = message.chat.id
        db_key = get_blocklist_key(chat_id)
        current_list = db.get(db_key, [])
        if not current_list:
            bot.reply_to(message,
                         "❌ এই গ্রুপে কোনো শব্দ ব্ল্যাকলিস্ট করা নেই।")
            return
        list_text = "🚫 **নিষিদ্ধ শব্দের তালিকা:**\n" + "\n".join(
            f"- `{word}`" for word in current_list)
        bot.reply_to(message, list_text, parse_mode="Markdown")
    except Exception as e:
        print(f"'/blocklist' কমান্ডে {e}")
        bot.reply_to(message, "⚠️ তালিকা দেখাতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['blocklistmode'])
def set_blocklist_mode(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        mode = message.text.split(maxsplit=1)[1].lower()
        if mode not in VALID_BLOCKLIST_MODES:
            bot.reply_to(
                message,
                f"❌ ভুল মোড। সঠিক মোডগুলো হলো: `{', '.join(VALID_BLOCKLIST_MODES)}`"
            )
            return
        db[get_config_key(chat_id, "blocklist_mode")] = mode
        bot.reply_to(message, f"✅ ব্ল্যাকলিস্ট মোড '{mode}'-এ সেট করা হয়েছে।")
    except IndexError:
        bot.reply_to(
            message,
            f"❓ ব্যবহার: `/blocklistmode [মোড]` ({', '.join(VALID_BLOCKLIST_MODES)})"
        )
    except Exception as e:
        print(f"'/blocklistmode' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ মোড সেট করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Filters (ফিল্টার) সিস্টেম (\n ফিক্সড)
# ----------------------------------------------------
@bot.message_handler(commands=['filter'])
def add_filter(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        # --- ⭐️ ফিক্স: \n\n সমস্যা সমাধানের জন্য 'raw_text' ব্যবহার ---
        try:
            raw_text = message.json.get('text',
                                        message.json.get('caption', ''))
            parts = raw_text.split(maxsplit=2)
            if len(parts) < 3:
                bot.reply_to(
                    message,
                    "❓ ব্যবহার: `/filter [শব্দ] [বট যা রিপ্লাই দেবে]`\nরিপ্লাইয়ে {fname}, {lname}, {fullname}, {username}, {id} ব্যবহার করতে পারেন।"
                )
                return
            keyword = parts[1].lower()
            reply_text = parts[2]
        except (IndexError, AttributeError):
            bot.reply_to(
                message,
                "❓ ব্যবহার: `/filter [শব্দ] [বট যা রিপ্লাই দেবে]`\nরিপ্লাইয়ে {fname}, {lname}, {fullname}, {username}, {id} ব্যবহার করতে পারেন।"
            )
            return
        # --- ⭐️ ফিক্স শেষ ---

        db[get_filter_key(chat_id, keyword)] = reply_text
        bot.reply_to(message, f"✅ ফিল্টার '{keyword}' সফলভাবে সেভ করা হয়েছে।")
    except Exception as e:
        print(f"'/filter' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ সেভ করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['stop'])
def stop_filter(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        keyword = message.text.split(maxsplit=1)[1].lower()
        db_key = get_filter_key(chat_id, keyword)
        if db_key in db:
            del db[db_key]
            bot.reply_to(message, f"✅ ফিল্টার '{keyword}' ডিলিট করা হয়েছে।")
        else:
            bot.reply_to(
                message,
                f"❌ '{keyword}' নামে কোনো ফিল্টার খুঁজে পাওয়া যায়নি।")
    except IndexError:
        bot.reply_to(message, "❓ ব্যবহার: `/stop [ফিল্টার শব্দ]`")
    except Exception as e:
        print(f"'/stop' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ ডিলিট করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['filters'])
def list_filters(message):
    try:
        chat_id = message.chat.id
        prefix = f"filter_{chat_id}_"
        filter_keys = db.prefix(prefix)
        if not filter_keys:
            bot.reply_to(message, "❌ এই গ্রুপে কোনো ফিল্টার সেভ করা নেই।")
            return
        filter_names = sorted([key.replace(prefix, "") for key in filter_keys])
        filter_list_text = "▶️ **সেভ করা ফিল্টারসমূহ:**\n" + "\n".join(
            f"- `{name}`" for name in filter_names)
        bot.reply_to(message, filter_list_text, parse_mode="Markdown")
    except Exception as e:
        print(f"'/filters' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ তালিকা দেখাতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# ⭐️ নতুন: Link Message সেট করার কমান্ড
# ----------------------------------------------------
@bot.message_handler(commands=['setlinkmsg'])
def set_custom_link_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return

        try:
            raw_text = message.json.get('text',
                                        message.json.get('caption', ''))
            custom_text = raw_text.split(maxsplit=1)[1]
        except (IndexError, AttributeError):
            bot.reply_to(
                message,
                f"❓ ব্যবহার: `/setlinkmsg [আপনার ফানি মেসেজ]`\n(মেসেজে {{mention}}, {{fname}} ইত্যাদি ব্যবহার করুন)"
            )
            return

        db[get_link_msg_key(chat_id)] = custom_text
        bot.reply_to(message,
                     "✅ নতুন লিঙ্ক ব্লক মেসেজ সফলভাবে সেট করা হয়েছে।")

    except Exception as e:
        print(f"কাস্টম লিঙ্ক মেসেজ সেটে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ দুঃখিত, বার্তাটি সেভ করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Locks (লক) সিস্টেম (লিঙ্ক মেসেজ সহ)
# ----------------------------------------------------
@bot.message_handler(commands=['lock'])
def lock_command(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if not bot_member.status in ['administrator', 'creator'
                                     ] or not bot_member.can_delete_messages:
            bot.reply_to(
                message,
                "❌ বট অ্যাডমিন নয় অথবা মেসেজ ডিলিট করার পারমিশন নেই।")
            return
        lock_type = message.text.split(maxsplit=1)[1].lower()
        if lock_type not in VALID_LOCK_TYPES:
            bot.reply_to(
                message,
                f"❌ ভুল লক টাইপ। সঠিক টাইপগুলো হলো: `{', '.join(VALID_LOCK_TYPES)}`",
                parse_mode="Markdown")
            return
        db_key = get_lock_key(chat_id)
        current_locks = db.get(db_key, [])
        if lock_type not in current_locks:
            current_locks.append(lock_type)
            db[db_key] = current_locks
            bot.reply_to(message,
                         f"🔒 `{lock_type}` সফলভাবে লক করা হয়েছে।",
                         parse_mode="Markdown")
        else:
            bot.reply_to(message,
                         f"ℹ️ `{lock_type}` আগে থেকেই লক করা আছে।",
                         parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message,
                     f"❓ ব্যবহার: `/lock [লক_টাইপ]` (যেমন: links, captcha)")
    except Exception as e:
        print(f"'/lock' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ লক করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['unlock'])
def unlock_command(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        lock_type = message.text.split(maxsplit=1)[1].lower()
        if lock_type not in VALID_LOCK_TYPES:
            bot.reply_to(
                message,
                f"❌ ভুল লক টাইপ। সঠিক টাইপগুলো হলো: `{', '.join(VALID_LOCK_TYPES)}`",
                parse_mode="Markdown")
            return
        db_key = get_lock_key(chat_id)
        current_locks = db.get(db_key, [])
        if lock_type in current_locks:
            current_locks.remove(lock_type)
            db[db_key] = current_locks
            bot.reply_to(message,
                         f"🔓 `{lock_type}` সফলভাবে আনলক করা হয়েছে।",
                         parse_mode="Markdown")
        else:
            bot.reply_to(message,
                         f"ℹ️ `{lock_type}` লক করা নেই।",
                         parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, f"❓ ব্যবহার: `/unlock [লক_টাইপ]`")
    except Exception as e:
        print(f"'/unlock' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ আনলক করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['locks'])
def list_locks(message):
    try:
        chat_id = message.chat.id
        db_key = get_lock_key(chat_id)
        current_locks = db.get(db_key, [])
        if not current_locks:
            bot.reply_to(message, "ℹ️ এই গ্রুপে কোনো লক করা নেই।")
            return
        lock_list_text = "🔒 **লক করা আইটেমসমূহ:**\n" + "\n".join(
            f"- `{lock}`" for lock in current_locks)
        bot.reply_to(message, lock_list_text, parse_mode="Markdown")
    except Exception as e:
        print(f"'/locks' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ তালিকা দেখাতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# ⭐️ Config কমান্ড (AutoDelete সহ)
# ----------------------------------------------------
@bot.message_handler(
    commands=['goodbye', 'cleanservice', 'autodeletemedia', 'autodeleterules'])
def config_commands(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        command = message.text.split()[0].replace("/", "")
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        arg = message.text.split(maxsplit=1)[1].lower()

        config_name_bn = ""
        if command == "goodbye":
            config_name_bn = "বিদায় বার্তা"
        elif command == "cleanservice":
            config_name_bn = "সার্ভিস মেসেজ ক্লিনিং"
        elif command == "autodeletemedia":  # ⭐️ মিডিয়া ডিলিট
            config_name_bn = "মিডিয়া অটো-ডিলিট"
        elif command == "autodeleterules":  # ⭐️ রুলস ডিলিট
            config_name_bn = "রুলস অটো-ডিলিট"

        if arg in ['on', 'yes']:
            db[get_config_key(chat_id, command)] = True
            bot.reply_to(message,
                         f"✅ `{config_name_bn}` সিস্টেমটি চালু করা হয়েছে।",
                         parse_mode="Markdown")
        elif arg in ['off', 'no']:
            db[get_config_key(chat_id, command)] = False
            bot.reply_to(message,
                         f"❌ `{config_name_bn}` সিস্টেমটি বন্ধ করা হয়েছে।",
                         parse_mode="Markdown")
        else:
            bot.reply_to(message, "❓ ব্যবহার: `on` অথবা `off` লিখুন।")

    except IndexError:
        bot.reply_to(message, f"❓ ব্যবহার: `/{command} <on/off>`")
    except Exception as e:
        print(f"`/{command}` কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ সেট করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Reports (রিপোর্ট) সিস্টেম
# ----------------------------------------------------
@bot.message_handler(commands=['report'])
def report_message(message):
    try:
        chat_id = message.chat.id
        if not message.reply_to_message:
            bot.reply_to(
                message,
                "❓ ব্যবহার: যে মেসেজটি রিপোর্ট করতে চান, সেটিতে রিপ্লাই দিয়ে `/report` লিখুন।"
            )
            return
        reported_msg = message.reply_to_message
        reporter = message.from_user
        admins = bot.get_chat_administrators(chat_id)
        admin_mentions = [
            f"[{admin.user.first_name}](tg://user?id={admin.user.id})"
            for admin in admins if not admin.user.is_bot
        ]
        if not admin_mentions:
            bot.reply_to(
                message,
                "❌ এই গ্রুপে কোনো (মানুষ) অ্যাডমিন খুঁজে পাওয়া যায়নি।")
            return
        link_chat_id = str(chat_id).replace("-100", "")
        report_text = f"🚨 **রিপোর্ট!**\n\n" \
                      f"**রিপোর্টার:** [{reporter.first_name}](tg://user?id={reporter.id})\n" \
                      f"**অভিযুক্ত:** [{reported_msg.from_user.first_name}](tg://user?id={reported_msg.from_user.id})\n\n" \
                      f"**বার্তা:** [এখানে ক্লিক করুন](https://t.me/c/{link_chat_id}/{reported_msg.message_id})\n\n" \
                      f"**অ্যাডমিনবৃন্দ:** {', '.join(admin_mentions)}"
        bot.send_message(chat_id,
                         report_text,
                         parse_mode="Markdown",
                         disable_web_page_preview=True)
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
    except Exception as e:
        print(f"'/report' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ রিপোর্ট পাঠাতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Purge (মেসেজ ডিলিট) সিস্টেম
# ----------------------------------------------------
@bot.message_handler(commands=['purge'])
def purge_messages(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if not bot_member.status in ['administrator', 'creator'
                                     ] or not bot_member.can_delete_messages:
            bot.reply_to(
                message,
                "❌ বট অ্যাডমিন নয় অথবা মেসেজ ডিলিট করার পারমিশন নেই।")
            return
        if not message.reply_to_message:
            bot.reply_to(
                message,
                "❓ ব্যবহার: যে মেসেজ থেকে ডিলিট শুরু করতে চান, সেটিতে রিপ্লাই দিয়ে `/purge` লিখুন।"
            )
            return

        start_message_id = message.reply_to_message.message_id
        end_message_id = message.message_id
        message_ids_to_delete = list(
            range(start_message_id, end_message_id + 1))

        if len(message_ids_to_delete) <= 1:
            bot.delete_message(chat_id, message.message_id)
            return

        if len(message_ids_to_delete) > PURGE_LIMIT + 1:
            original_count = len(message_ids_to_delete) - 1
            message_ids_to_delete = message_ids_to_delete[-(PURGE_LIMIT + 1):]
            bot.reply_to(
                message,
                f"⚠️ লিমিট! আপনি {original_count}টি মেসেজ ডিলিট করতে চেয়েছেন, কিন্তু আমি একবারে সর্বোচ্চ {PURGE_LIMIT} টি ডিলিট করতে পারি। শেষ {PURGE_LIMIT}টি ডিলিট করা হচ্ছে...",
                disable_notification=True)
            time.sleep(3)

        deleted_count = 0
        chunk_size = 100
        for i in range(0, len(message_ids_to_delete), chunk_size):
            chunk = message_ids_to_delete[i:i + chunk_size]
            try:
                deleted_count += bot.delete_messages(chat_id, chunk)
            except telebot.apihelper.ApiException as api_e:
                print(f"Purge করার সময় কিছু মেসেজ ডিলিট করা যায়নি: {api_e}")
            except Exception as e:
                print(f"Purge করার সময় অপ্রত্যাশিত ত্রুটি: {e}")
                break

        if deleted_count > 0:
            final_deleted = deleted_count - 1 if end_message_id in message_ids_to_delete else deleted_count
            if final_deleted > 0:
                confirm_msg = bot.send_message(
                    chat_id,
                    f"✅ {final_deleted} টি মেসেজ ডিলিট করা হয়েছে।",
                    disable_notification=True)
                time.sleep(5)
                bot.delete_message(chat_id, confirm_msg.message_id)
        else:
            bot.reply_to(message,
                         "⚠️ কোনো মেসেজ ডিলিট করা সম্ভব হয়নি।",
                         disable_notification=True)

    except Exception as e:
        print(f"'/purge' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ মেসেজ ডিলিট করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# Pin/Unpin (পিন) সিস্টেম
# ----------------------------------------------------
@bot.message_handler(commands=['pin'])
def pin_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if not bot_member.status in ['administrator', 'creator'
                                     ] or not bot_member.can_pin_messages:
            bot.reply_to(message,
                         "❌ বট অ্যাডমিন নয় অথবা মেসেজ পিন করার পারমিশন নেই।")
            return
        if not message.reply_to_message:
            bot.reply_to(
                message,
                "❓ ব্যবহার: যে মেসেজটি পিন করতে চান, সেটিতে রিপ্লাই দিয়ে `/pin` লিখুন।"
            )
            return
        bot.pin_chat_message(chat_id,
                             message.reply_to_message.message_id,
                             disable_notification=True)
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
    except Exception as e:
        print(f"'/pin' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ মেসেজ পিন করতে সমস্যা হয়েছে।")


@bot.message_handler(commands=['unpin'])
def unpin_message(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not is_admin(chat_id, user_id):
            bot.reply_to(
                message,
                "❌ দুঃখিত, শুধু অ্যাডমিনরাই এই কমান্ড ব্যবহার করতে পারবে।")
            return
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if not bot_member.status in ['administrator', 'creator'
                                     ] or not bot_member.can_pin_messages:
            bot.reply_to(message,
                         "❌ বট অ্যাডমিন নয় অথবা মেসেজ পিন করার পারমিশন নেই।")
            return
        bot.unpin_chat_message(chat_id)
        confirm = bot.reply_to(message,
                               "✅ সর্বশেষ পিন করা মেসেজটি আনপিন করা হয়েছে।",
                               disable_notification=True)
        time.sleep(5)
        bot.delete_message(chat_id, confirm.message_id)
        bot.delete_message(chat_id, message.message_id)
    except telebot.apihelper.ApiException as e:
        if "message to unpin not found" in str(e).lower():
            bot.reply_to(message, "ℹ️ এই গ্রুপে কোনো মেসেজ পিন করা নেই।")
        else:
            print(f"'/unpin' কমান্ডে ত্রুটি: {e}")
            bot.reply_to(message, "⚠️ মেসেজ আনপিন করতে সমস্যা হয়েছে।")
    except Exception as e:
        print(f"'/unpin' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ মেসেজ আনপিন করতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# ID (আইডি) সিস্টেম
# ----------------------------------------------------
@bot.message_handler(commands=['id'])
def get_id(message):
    try:
        chat_id = message.chat.id
        user_to_check = message.from_user
        target_text = "আপনার"
        if message.reply_to_message:
            user_to_check = message.reply_to_message.from_user
            target_text = "রিপ্লাই করা ইউজারের"
        user_id = user_to_check.id
        first_name = user_to_check.first_name
        last_name = user_to_check.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        username = f"@{user_to_check.username}" if user_to_check.username else "নেই"
        user_link = f"[{full_name}](tg://user?id={user_id})"
        text = f"🗣️ **{target_text} তথ্য:**\n\n" \
               f"🔹 **আইডি:** `{user_id}`\n" \
               f"🔹 **প্রথম নাম:** {first_name}\n" \
               f"🔹 **শেষ নাম:** {last_name if last_name else 'নেই'}\n" \
               f"🔹 **ইউজারনেম:** {username}\n" \
               f"➡️ **প্রোফাইল:** {user_link}\n\n" \
               f"💬 **এই চ্যাটের আইডি:** `{chat_id}`"
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"'/id' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ আইডি দেখাতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# '/info' কমান্ড
# ----------------------------------------------------
@bot.message_handler(commands=['info'])
def get_user_info(message):
    try:
        chat_id = message.chat.id
        user_to_check = message.from_user
        target_text = "আপনার"
        if message.reply_to_message:
            user_to_check = message.reply_to_message.from_user
            target_text = "রিপ্লাই করা ইউজারের"
        user_id = user_to_check.id
        first_name = user_to_check.first_name
        last_name = user_to_check.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        username = f"@{user_to_check.username}" if user_to_check.username else "নেই"
        user_link = f"[{full_name}](tg://user?id={user_id})"
        warn_key = get_warns_key(chat_id, user_id)
        warn_count = db.get(warn_key, 0)
        text = f"👤 **{target_text} তথ্য:**\n\n" \
               f"**আইডি:** `{user_id}`\n" \
               f"**পুরো নাম:** {full_name}\n" \
               f"**ইউজারনেম:** {username}\n" \
               f"**মেনশন:** {user_link}\n" \
               f"**ওয়ার্নিং:** {warn_count}/{MAX_WARNS}"
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"'/info' কমান্ডে ত্রুটি: {e}")
        bot.reply_to(message, "⚠️ তথ্য দেখাতে সমস্যা হয়েছে।")


# ----------------------------------------------------
# '/help' বাটন মেন্যু
# ----------------------------------------------------
@bot.message_handler(commands=['help'])
def send_help_menu(message):
    try:
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton(text="👮 অ্যাডমিন",
                                       callback_data="grp_admin_help"),
            types.InlineKeyboardButton(text="🔇 মিউট",
                                       callback_data="grp_mute_help"),
            types.InlineKeyboardButton(text="📌 পিন",
                                       callback_data="grp_pin_help"),
            types.InlineKeyboardButton(text="🆔 আইডি",
                                       callback_data="grp_id_help"),
            types.InlineKeyboardButton(text="🔒 লক",
                                       callback_data="grp_locks_help"),
            types.InlineKeyboardButton(text="🤖 ক্যাপচা",
                                       callback_data="grp_captcha_help"),
            types.InlineKeyboardButton(text="🚫 ব্ল্যাকলিস্ট",
                                       callback_data="grp_blocklist_help"),
            types.InlineKeyboardButton(text="▶️ ফিল্টার",
                                       callback_data="grp_filters_help"),
            types.InlineKeyboardButton(text="📜 নিয়মাবলী",
                                       callback_data="grp_rules_help"),
            types.InlineKeyboardButton(text="⚠️ ওয়ার্নিং",
                                       callback_data="grp_warn_help"),
            types.InlineKeyboardButton(text="🗒️ নোটস",
                                       callback_data="grp_notes_help"),
            types.InlineKeyboardButton(text="👋 স্বাগতম/বিদায়",
                                       callback_data="grp_welcome_help"),
            types.InlineKeyboardButton(text="🚨 রিপোর্ট",
                                       callback_data="grp_report_help"),
            types.InlineKeyboardButton(text="🧹 ডিলিট (Purge)",
                                       callback_data="grp_purge_help"),
            types.InlineKeyboardButton(
                text="🗑️ অটো-ডিলিট",
                callback_data="grp_autodelete_help")  # ⭐️ নতুন বাটন
        ]
        markup.add(*buttons)
        help_text = f"⚙️ **{bot.get_me().first_name} সাহায্য মেন্যু** ⚙️\n\n"
        help_text += f"হ্যালো {message.from_user.first_name}! আমি কিভাবে আপনাকে সাহায্য করতে পারি?"
        help_text += "\n\nআমার বিভিন্ন ফিচার সম্পর্কে জানতে নিচের বাটনগুলো ব্যবহার করুন:"
        help_text += f"\n\n🆘 প্রশ্ন আছে? [আমাদের সাপোর্ট গ্রুপে যোগ দিন]({SUPPORT_GROUP_LINK})"
        help_text += f"\n📣 নতুন আপডেট পেতে? [আমাদের আপডেট চ্যানেল দেখুন]({UPDATE_CHANNEL_LINK})"
        bot.send_message(message.chat.id,
                         help_text,
                         reply_markup=markup,
                         parse_mode="Markdown",
                         disable_web_page_preview=True)
    except Exception as e:
        print(f"'/help' কমান্ডে ত্রুটি: {e}")


# ----------------------------------------------------
# বাটন ক্লিকের জবাব দেওয়া
# ----------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_button_clicks(call):
    try:
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        # --- CAPTCHA Verification ---
        if call.data.startswith("verify_"):
            target_user_id = int(call.data.split("_")[1])
            if user_id == target_user_id:
                try:
                    bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
                    if bot_member.status in [
                            'administrator', 'creator'
                    ] and bot_member.can_restrict_members:
                        bot.restrict_chat_member(
                            chat_id,
                            user_id,
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True)
                        bot.delete_message(chat_id, call.message.message_id)
                        bot.answer_callback_query(
                            call.id, "✅ ধন্যবাদ! আপনি ভেরিফায়েড।")
                    else:
                        bot.delete_message(chat_id, call.message.message_id)
                        bot.answer_callback_query(
                            call.id,
                            "✅ ভেরিফিকেশন সম্পন্ন। (বটের পারমিশন চেক করুন)")
                except Exception as e:
                    print(f"ভেরিফিকেশনে ত্রুটি: {e}")
                    bot.answer_callback_query(call.id, "সমস্যা হয়েছে।")
            else:
                bot.answer_callback_query(call.id,
                                          "❌ এটি আপনার জন্য নয়।",
                                          show_alert=True)
            return

        # --- বাংলা হেল্প টেক্সট ---
        help_texts_bn = {
            "admin_help":
            "👮 *অ্যাডমিন সংক্রান্ত*\n\n`/kick`: কাউকে গ্রুপ থেকে বের করতে রিপ্লাই দিয়ে এই কমান্ড ব্যবহার করুন।\n`/ban`: কাউকে স্থায়ীভাবে ব্যান করতে রিপ্লাই দিন।\n`/unban`: ব্যান করা কাউকে আনব্যান করতে তার পুরনো মেসেজে **রিপ্লাই** দিন **অথবা** `/unban [User ID]` লিখুন।",
            "mute_help":
            "🔇 *মিউট সংক্রান্ত*\n\n`/mute`: কাউকে স্থায়ীভাবে চুপ করাতে রিপ্লাই দিন।\n`/tmute [সময়]`: নির্দিষ্ট সময়ের জন্য মিউট করতে রিপ্লাই দিন (যেমন: ৩০মি, ১ঘ, ২দি)।\n`/unmute`: কাউকে আনমিউট করতে রিপ্লাই দিন।",
            "pin_help":
            "📌 *পিন সংক্রান্ত*\n\n`/pin`: কোনো গুরুত্বপূর্ণ মেসেজ পিন করতে রিপ্লাই দিন (নোটিফিকেশন ছাড়া)।\n`/unpin`: সর্বশেষ পিন করা মেসেজ আনপিন করুন।",
            "id_help":
            "🆔 *আইডি ও তথ্য*\n\n`/id`: আপনার নিজের আইডি ও চ্যাট আইডি দেখুন।\n`/id`: কারো মেসেজে রিপ্লাই দিয়ে তার আইডি দেখুন。\n`/info`: কারো মেসেজে রিপ্লাই দিয়ে তার আইডি, নাম ও ওয়ার্নিং সংখ্যা দেখুন。",
            "locks_help":
            f"🔒 *লক সেটিংস*\n\n`/lock [টাইপ]`: নির্দিষ্ট ধরনের মেসেজ (যেমন: links, photos, stickers, all) পাঠানো বন্ধ করুন।\n`/unlock [টাইপ]`: আনলক করুন।\n`/locks`: দেখুন কী কী লক করা আছে।\n*উপলব্ধ টাইপ:* `{', '.join(VALID_LOCK_TYPES)}`",
            "captcha_help":
            "🤖 *ক্যাপচা ভেরিফিকেশন*\n\n`/lock captcha`: নতুন সদস্যদের জন্য যোগদানের পর ভেরিফিকেশন চালু করুন।\n`/unlock captcha`: ভেরিফিকেশন বন্ধ করুন।\n*(বটের 'Restrict Members' পারমিশন লাগবে)*",
            "blocklist_help":
            f"🚫 *ব্ল্যাকলিস্ট (নিষিদ্ধ শব্দ)*\n\n`/addblocklist [শব্দ]`: একটি শব্দ বা বাক্য নিষিদ্ধ করুন।\n`/rmblocklist [শব্দ]`: তালিকা থেকে বাদ দিন।\n`/blocklist`: নিষিদ্ধ শব্দের তালিকা দেখুন।\n`/blocklistmode [মোড]`: নিষিদ্ধ শব্দ ব্যবহার করলে কী অ্যাকশন নেওয়া হবে (মোড: `{', '.join(VALID_BLOCKLIST_MODES)}`)\n`/setblocklistmsg [মেসেজ]`: কাস্টম ব্ল্যাকলিস্ট নোটিশ সেট করুন।\n`/resetblocklistmsg`: রিসেট করুন。",
            "filters_help":
            "▶️ *ফিল্টার (অটো-রিপ্লাই)*\n\n`/filter [শব্দ] [রিপ্লাই]`: একটি অটো-রিপ্লাই সেট করুন। রিপ্লাইয়ের মধ্যে `{fname}`, `{lname}`, `{fullname}`, `{username}`, `{id}` ব্যবহার করা যাবে।\n`/stop [শব্দ]`: ফিল্টার ডিলিট করুন।\n`/filters`: সব ফিল্টারের তালিকা দেখুন。",
            "rules_help":
            "📜 *গ্রুপের নিয়মাবলী*\n\n`/setrules [নিয়ম]`: গ্রুপের নিয়ম সেট করুন।\n`/rules`: গ্রুপের নিয়ম দেখুন।",
            "warn_help":
            f"⚠️ *ওয়ার্নিং সিস্টেম*\n\n`/warn`: নিয়ম ভাঙলে কাউকে সতর্ক করতে রিপ্লাই দিন।\n`/warns`: কারো মোট ওয়ার্নিং সংখ্যা দেখতে রিপ্লাই দিন।\n`/resetwarns`: কারো সব ওয়ার্নিং মুছে ফেলতে রিপ্লাই দিন।\n`/setwarnmsg [মেসেজ]`: কাস্টম ওয়ার্নিং মেসেজ সেট করুন।\n`/resetwarnmsg`: রিসেট করুন।\n*({MAX_WARNS} টি ওয়ার্নিং পেলে অটো-ব্যান)*",
            "notes_help":
            "🗒️ *নোটস (তথ্য সেভ)*\n\n`/save [নাম] [কন্টেন্ট]`: প্রয়োজনীয় তথ্য বা মেসেজ সেভ করুন।\n`/notes`: সেভ করা সব নোটের তালিকা দেখুন।\n`/clear [নাম]`: নোট ডিলিট করুন।\n\n*সেভ করা নোট দেখতে গ্রুপে `#নাম` লিখে মেসেজ দিন।*",
            "welcome_help":
            "👋 *স্বাগতম ও বিদায় বার্তা*\n\nস্বাগত বার্তা ডিফল্টভাবে চালু থাকে (CAPTCHA চালু থাকলে দেখাবে না)।\n`/setwelcome [মেসেজ]`: নিজের মতো স্বাগত বার্তা সেট করুন।\n`/resetwelcome`: ডিফল্ট বার্তায় ফিরে যান।\n\n`/goodbye <on/off>`: এটি চালু বা বন্ধ করুন।\n`/setgoodbye [মেসেজ]`: নিজের মতো বিদায় বার্তা সেট করুন।\n`/resetgoodbye`: ডিফল্ট বার্তায় ফিরে যান।\n\n`/cleanservice <on/off>`: গ্রুপে \"User joined/left\" মেসেজ অটো-ডিলিট করুন।",
            "report_help":
            "🚨 *রিপোর্ট টু অ্যাডমিন*\n\n`/report`: কোনো আপত্তিকর মেসেজে রিপ্লাই দিয়ে এই কমান্ড ব্যবহার করলে গ্রুপের অ্যাডমিনদের কাছে একটি নোটিফিকেশন যাবে।",
            "purge_help":
            "🧹 *মেসেজ ডিলিট (Purge)*\n\n`/purge`: কোনো মেসেজে রিপ্লাই দিয়ে এই কমান্ড ব্যবহার করলে রিপ্লাই করা মেসেজটি থেকে শুরু করে আপনার কমান্ড পর্যন্ত সব মেসেজ ডিলিট হয়ে যাবে।",
            "autodelete_help":
            f"🗑️ *অটো-ডিলিট*\n\n`/autodeletemedia <on/off>`: চালু করলে, সাধারণ সদস্যদের পাঠানো সব মিডিয়া (ছবি, ভিডিও, স্টিকার, ভয়েস) {MEDIA_DELETE_DELAY} সেকেন্ড পর অটো-ডিলিট হয়ে যাবে। (**অ্যাডমিনদের মিডিয়া ডিলিট হবে না**)।\n\n`/autodeleterules <on/off>`: চালু করলে, `/rules` কমান্ড এবং বটের পাঠানো নিয়মাবলী {RULES_DELETE_DELAY} সেকেন্ড পর অটো-ডিলিট হয়ে যাবে।"
        }
        callback_key = call.data.replace("pvt_", "").replace("grp_", "")
        text = help_texts_bn.get(callback_key, "")
        if text:
            try:
                if call.message.chat.type == 'private':
                    if call.message.text != text:
                        bot.edit_message_text(
                            text,
                            chat_id,
                            call.message.message_id,
                            reply_markup=call.message.reply_markup,
                            parse_mode="Markdown",
                            disable_web_page_preview=True)
                    bot.answer_callback_query(call.id)
                else:
                    bot.send_message(chat_id, text, parse_mode="Markdown")
                    bot.answer_callback_query(call.id)
            except telebot.apihelper.ApiException as api_e:
                if "message is not modified" in str(api_e).lower():
                    bot.answer_callback_query(call.id)
                else:
                    print(f"হেল্প বাটন পাঠাতে/এডিট করতে ত্রুটি: {api_e}")
                    bot.send_message(chat_id, text)
                    bot.answer_callback_query(call.id)
            except Exception as e:
                print(f"হেল্প বাটন পাঠাতে/এডিট করতে ত্রুটি: {e}")
                bot.send_message(chat_id, text)
                bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"বাটন ক্লিকে ত্রুটি: {e}")
        bot.answer_callback_query(call.id, "⚠️ একটি সমস্যা হয়েছে।")


# ----------------------------------------------------
# ফাইনাল মেসেজ হ্যান্ডলার (অটো-ডিলিট সহ)
# ----------------------------------------------------
@bot.message_handler(content_types=[
    'text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice',
    'animation', 'new_chat_members', 'left_chat_member'
])
def handle_all_messages(message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        user = message.from_user
        chat = message.chat

        # --- CleanService Check ---
        if message.content_type == 'new_chat_members' or message.content_type == 'left_chat_member':
            # ⭐️ FINAL: CleanService ডিফল্টভাবে চালু থাকবে
            if db.get(get_config_key(chat_id, "cleanservice"),
                      True):  # ডিফল্ট True
                try:
                    bot.delete_message(chat_id, message.message_id)
                except Exception as e:
                    print(f"সার্ভিস মেসেজ ডিলিটে ত্রুটি: {e}")
            return  # Stop processing for service messages

        # --- Admin Check (Admin Immunity Logic) ---
        is_user_admin = is_admin(chat_id, user_id)

        # ---------------------------------
        # --- সাধারণ সদস্যদের জন্য ---
        # ---------------------------------

        # --- 1. Blocklist Check (18+ content) ---
        if message.content_type == 'text':
            text_lower = message.text.lower()
            blocklist_key = get_blocklist_key(chat_id)
            current_blocklist = db.get(blocklist_key, [])
            for word in current_blocklist:
                if word in text_lower:
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        mode = db.get(
                            get_config_key(chat_id, "blocklist_mode"),
                            "nothing")

                        blocklist_template = db.get(
                            get_blocklist_msg_key(chat_id),
                            DEFAULT_BLOCKLIST_MSG)
                        notice_text = replace_placeholders(
                            blocklist_template, user, chat)

                        action_text = ""
                        if mode == 'ban':
                            bot.ban_chat_member(chat_id, user_id)
                            action_text = f"🚨 {user.first_name}-কে ব্যান করা হলো।"
                        elif mode == 'kick':
                            bot.kick_chat_member(chat_id, user_id)
                            bot.unban_chat_member(chat_id, user_id)
                            action_text = f"🚨 {user.first_name}-কে কিক করা হলো।"
                        elif mode == 'mute':
                            bot.restrict_chat_member(chat_id,
                                                     user_id,
                                                     can_send_messages=False)
                            action_text = f"🚨 {user.first_name}-কে মিউট করা হলো।"
                        elif mode == 'warn':
                            trigger_warn(message, user, chat)
                            action_text = ""

                        full_notice = f"{notice_text}\n{action_text}".strip()

                        # ⭐️ উন্নতি: নোটিশ ডিলিট করার কাজটি থ্রেডে পাঠানো হলো
                        if full_notice and mode != 'warn':
                            sent_notice = bot.send_message(
                                chat_id, full_notice, parse_mode="Markdown")
                            threading.Thread(
                                target=delete_message_after_delay,
                                args=(chat_id, sent_notice.message_id,
                                      NOTICE_DELETE_DELAY)).start()

                        return
                    except Exception as e:
                        print(f"ব্ল্যাকলিস্ট অ্যাকশনে ত্রুটি: {e}")

        # --- 2. Locks Check (Link/Media/Other Types) ---
        db_key = get_lock_key(chat_id)
        current_locks = db.get(db_key, [])
        if current_locks:
            msg_deleted = False
            locked_item_bn = None
            content_type = message.content_type

            # --- ⭐️ LINK LOCK CUSTOM MESSAGE LOGIC ---
            link_msg_to_send = None
            if 'links' in current_locks and message.entities and any(
                    e.type in ['url', 'text_link'] for e in message.entities):
                msg_deleted = True
                locked_item_bn = 'লিঙ্ক'
                link_template = db.get(get_link_msg_key(chat_id),
                                       DEFAULT_LINK_MSG)
                link_msg_to_send = replace_placeholders(
                    link_template, user, chat)
            # --- ⭐️ LINK LOCK CUSTOM MESSAGE LOGIC END ---

            elif 'all' in current_locks:
                msg_deleted = True
                locked_item_bn = 'সব ধরনের মেসেজ'
            elif 'photos' in current_locks and content_type == 'photo':
                msg_deleted = True
                locked_item_bn = 'ছবি'
            elif 'videos' in current_locks and content_type == 'video':
                msg_deleted = True
                locked_item_bn = 'ভিডিও'
            elif 'documents' in current_locks and content_type == 'document':
                msg_deleted = True
                locked_item_bn = 'ফাইল/ডকুমেন্ট'
            elif 'stickers' in current_locks and content_type == 'sticker':
                msg_deleted = True
                locked_item_bn = 'স্টিকার'
            elif 'audio' in current_locks and content_type == 'audio':
                msg_deleted = True
                locked_item_bn = 'অডিও'
            elif 'voice' in current_locks and content_type == 'voice':
                msg_deleted = True
                locked_item_bn = 'ভয়েস মেসেজ'

            if msg_deleted:
                try:
                    bot.delete_message(chat_id, message.message_id)
                    if link_msg_to_send:
                        notice_text = link_msg_to_send  # Use custom link message
                    elif locked_item_bn:
                        notice_text = f"❌ {user.first_name}, গ্রুপে **{locked_item_bn}** পাঠানো নিষিদ্ধ।"

                    if notice_text:
                        sent_notice = bot.send_message(chat_id,
                                                       notice_text,
                                                       parse_mode="Markdown")
                        # ⭐️ উন্নতি: নোটিশ ডিলিট করার কাজটি থ্রেডে পাঠানো হলো
                        threading.Thread(target=delete_message_after_delay,
                                         args=(chat_id, sent_notice.message_id,
                                               NOTICE_DELETE_DELAY)).start()
                    return
                except Exception as e:
                    print(f"লক করা মেসেজ ডিলিট/নোটিশে ত্রুটি: {e}")

        # --- ⭐️ 3. Auto-Delete Media Logic (Media Only - No Admin Delete) ---
        autodelete_media = db.get(get_config_key(chat_id, "autodeletemedia"),
                                  True)

        # যদি অটো-ডিলিট চালু থাকে AND মেসেজটি মিডিয়া হয় AND ইউজার অ্যাডমিন না হয়
        if autodelete_media and message.content_type in MEDIA_TYPES_TO_DELETE and not is_user_admin:
            # এটি সাধারণ ইউজারের মিডিয়া, ডিলিট টাইমার চালু করুন
            threading.Thread(target=delete_message_after_delay,
                             args=(chat_id, message.message_id,
                                   MEDIA_DELETE_DELAY)).start()
            return  # মিডিয়া ডিলিট হলেও নিচের ফিল্টার/নোট চেক করার দরকার নেই
        # --- ⭐️ অটো-ডিলিট শেষ ---

        # --- 4. Filters Check (টাইপিং একশন সহ) ---
        if message.content_type == 'text':
            text_lower = message.text.lower()
            prefix = f"filter_{chat_id}_"
            filter_keys = db.prefix(prefix)
            for key in filter_keys:
                keyword = key.replace(prefix, "")
                if keyword in text_lower:
                    try:
                        bot.send_chat_action(chat_id, 'typing')
                        time.sleep(0.7)

                        reply_text_template = db[key]
                        reply_text = replace_placeholders(
                            reply_text_template, user, chat)

                        # --- ⭐️ ফিক্স: Markdown Error Handling ---
                        try:
                            bot.reply_to(message,
                                         reply_text,
                                         parse_mode="Markdown",
                                         disable_web_page_preview=True)
                        except telebot.apihelper.ApiException as e:
                            if "can't parse entities" in str(e).lower():
                                print(
                                    "Markdown পার্সিং-এ ত্রুটি (ফিল্টার)। প্লেইন টেক্সট হিসাবে পাঠানো হচ্ছে।"
                                )
                                plain_text = reply_text.replace("\\n", "\n")
                                bot.reply_to(message,
                                             plain_text,
                                             parse_mode=None,
                                             disable_web_page_preview=True)
                            else:
                                print(f"ফিল্টার পাঠাতে API ত্রুটি: {e}")
                        # --- ⭐️ ফিক্স শেষ ---

                    except Exception as e:
                        print(f"ফিল্টার রিপ্লাই পাঠাতে সাধারণ ত্রুটি: {e}")
                    return  # Stop processing, filter found

        # --- 5. Notes Check (টাইপিং একশন সহ) ---
        if message.content_type == 'text' and message.text.startswith('#'):
            # (অ্যাডমিনরা এটি উপরেই পার করে এসেছে, এটা শুধু সাধারণ ইউজারদের জন্য)
            if not is_user_admin:
                try:
                    notename = message.text[1:].lower()
                    db_key = get_note_key(chat_id, notename)
                    if not notename: return
                    if db_key in db:
                        bot.send_chat_action(chat_id, 'typing')
                        time.sleep(0.7)

                        reply_text = replace_placeholders(
                            db[db_key], user, chat)

                        # --- ⭐️ ফিক্স: Markdown Error Handling ---
                        try:
                            bot.reply_to(message,
                                         reply_text,
                                         parse_mode="Markdown",
                                         disable_web_page_preview=True)
                        except telebot.apihelper.ApiException as e:
                            if "can't parse entities" in str(e).lower():
                                print(
                                    "Markdown পার্সিং-এ ত্রুটি (নোট)। প্লেইন টেক্সট হিসাবে পাঠানো হচ্ছে।"
                                )
                                plain_text = reply_text.replace("\\n", "\n")
                                bot.reply_to(message,
                                             plain_text,
                                             parse_mode=None,
                                             disable_web_page_preview=True)
                            else:
                                print(f"নোট পাঠাতে API ত্রুটি: {e}")
                        # --- ⭐️ ফিক্স শেষ ---
                except Exception as e:
                    print(f"নোট দেখাতে ত্রুটি: {e}")

    except Exception as e:
        print(f"প্রধান মেসেজ হ্যান্ডলারে ত্রুটি: {e}")


# ----------------------------------------------------
# বট পোলিং শুরু করা (FINAL CRITICAL STEP)
# ----------------------------------------------------

print("🤖 টেলিগ্রাম বট চালু হচ্ছে...")

# bot.infinity_polling() ব্যবহার করা অপরিহার্য, এটি ছাড়া বটটি ১ সেকেন্ডে বন্ধ হয়ে যাবে।
try:
    # none_stop=True: কোনো এরর হলেও বট বন্ধ হবে না
    # skip_pending=True: বট বন্ধ থাকার সময়কার পুরোনো মেসেজ এড়িয়ে যাবে
    bot.infinity_polling(none_stop=True, skip_pending=True)

except Exception as e:
    # এটি নিশ্চিত করে যে বট যদি বন্ধ হয়েও যায়, তবে ডেভেলপার সেই ত্রুটিটি দেখতে পাবে।
    print(f"প্রধান পোলিং লুপে মারাত্মক ত্রুটি: {e}")
    print(
        "⚠️ নিশ্চিত করুন: ১. BOT_TOKEN সঠিক আছে। ২. শুধু একটি বট ইনস্ট্যান্স চলছে।"
    )
