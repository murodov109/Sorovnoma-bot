import telebot

TOKEN = "BOT_TOKENINGNI_QO'Y"
bot = telebot.TeleBot(TOKEN)
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Savolni kiriting:")
    user_data[message.chat.id] = {"step": "question"}

@bot.message_handler(func=lambda msg: msg.chat.id in user_data)
def poll_setup(message):
    step = user_data[message.chat.id]["step"]
    if step == "question":
        user_data[message.chat.id]["question"] = message.text
        user_data[message.chat.id]["options"] = []
        user_data[message.chat.id]["step"] = "option"
        bot.send_message(message.chat.id, "Variant 1 ni kiriting:")
    elif step == "option":
        user_data[message.chat.id]["options"].append(message.text)
        if len(user_data[message.chat.id]["options"]) < 3:
            bot.send_message(message.chat.id, f"Variant {len(user_data[message.chat.id]['options'])+1} ni kiriting:")
        else:
            bot.send_message(message.chat.id, f"Savol: {user_data[message.chat.id]['question']}\nVariantlar: {', '.join(user_data[message.chat.id]['options'])}\nTasdiqlash uchun /confirm yozing")
            user_data[message.chat.id]["step"] = "confirm"

@bot.message_handler(commands=['confirm'])
def confirm(message):
    bot.send_message(message.chat.id, "Kanal username’ini kiriting:")
    user_data[message.chat.id]["step"] = "channel"

@bot.message_handler(func=lambda msg: user_data.get(msg.chat.id, {}).get("step") == "channel")
def set_channel(message):
    user_data[message.chat.id]["channel"] = message.text
    bot.send_message(message.chat.id, "Boshlash uchun /startpoll yozing")
    user_data[message.chat.id]["step"] = "ready"

@bot.message_handler(commands=['startpoll'])
def start_poll(message):
    q = user_data[message.chat.id]["question"]
    opts = user_data[message.chat.id]["options"]
    channel = user_data[message.chat.id]["channel"]
    bot.send_poll(channel, q, opts, is_anonymous=False)
    bot.send_message(message.chat.id, f"So‘rovnoma {channel} kanaliga joylandi!")

bot.polling()
