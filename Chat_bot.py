import telebot
from urllib.parse import urlparse
from telebot import types
from validator_collection import checkers
from OPD_lib_new import ChatBotFunc

chat_bot = ChatBotFunc()
bot = telebot.TeleBot('6454458030:AAGxB7OIxR4TLMoWQdZstJVnPCrQk4Dmdyw')

@bot.message_handler(commands=['start'])
def start(chat):
    bot.send_message(chat.chat.id, f'Привет, {chat.from_user.first_name}, добро пожаловать в наш чат-бот для предоставления '
                                   'краткого описания видео с видеохостинга <b>YouTube</b>\n'
                                   'Введите ссылку для конкретного видео и мы сделаем краткий пересказ\n'
                                   '\n'
                                   'Или для поиска нужной ссылки на видео, воспользуйтесь командой <b>Vid</b>\n'
                                   '\n'
                                   'Вам нужно написать символ @, затем написать слово Vid и ввести название видео, которое хотите найти.\n'
                                   'Далее в появившейся всплывающей панеле, выберите нужное вам видео и начните его обработку!\n'
                                   '\n'
                                   'Наш бот расчитан на видео до 15 минут, так как пока есть определенные проблемы с оптимизацией кода. Наша команда надеется'
                                   ' на ваше понимание! Спасибо!', parse_mode='html')
    bot.register_next_step_handler(chat, url_text)

@bot.message_handler(commands=['team'])
def team_message(chat):
    button = types.InlineKeyboardMarkup()
    bot.send_message(chat.chat.id, '<b>Тимлид</b> - Данил Моисеенко\n'
                                   '<b>Дизайнер</b> - Илья Самошин\n'
                                   '<b>Разработчик</b> - Михаил Филиппов\n'
                                   '<b>Аналитик, разработчик</b> - Андрей Арсланов\n'
                                   '<b>Разработчик</b> - Григорий Шабельников', parse_mode='html', reply_markup=button)

@bot.message_handler(commands=['help'])
def help_message(chat):
    bot.send_message(chat.chat.id, '<b>Вот список всех команд, которые тут есть</b>:\n'
                                   '<em>/start</em> - Начать работу\n'
                                   '<em>/help</em> - Список команд\n'
                                   '<em>/team</em> - Список создателей проекта', parse_mode='html')

@bot.message_handler(content_types=['text'])
def url_text(chat):
    '''
    Функция для определения того, какой текст был отправлен в чат
    Если это ссылка на видео с YouTube, появляется сообещние о принятии ссылки
    И 3 кнопки, с которыми в дальнейшем можно взаимодействовать

    Если это не ссылка на видео или любой неподходящий текст, выведится предупреждение и следует ввести корректную ссылку

    При нажатии кнопки начнется работа со статичным методом отработки нажатия
    '''
    url = chat.text.strip()
    if checkers.is_url(url) == True and urlparse(url).netloc + urlparse(url).path == "www.youtube.com/watch":
        markup = types.InlineKeyboardMarkup(row_width=1)
        button1 = types.InlineKeyboardButton('Краткое описание', callback_data='short_desc')
        button2 = types.InlineKeyboardButton('Тайм-коды', callback_data='time_code')
        button3 = types.InlineKeyboardButton('Поменять ссылку', callback_data='change_url')
        markup.add(button1, button2, button3)
        bot.send_message(chat.chat.id, 'Мы приняли вашу ссылку, для предоставления краткого описания нажмите кнопку <b>"Краткое описание"</b>\n'
                                       '\n'
                                       'Для определения нужных вам тайм-кодов данного видео, нажмите кнопку <b>"Тайм-коды"</b>\n'
                                       '\n'
                                       'Если вам нужно поменять ссылку, вы можете нажать на кнопку <b>"Поменять ссылку"</b>',parse_mode='html',reply_markup=markup)
        chat_bot.get_url(url)
    else:
        bot.send_message(chat.chat.id, 'Введена некорректная ссылка, попробуйте еще раз!')
        bot.register_next_step_handler(chat, url_text)

def reset(chat):
    '''
    Функция для перезапуска после успешного выполнения Краткого описания или Тайм-кодов
    Нажимаем кнопку, после этого бот предлагает вновь отправить ссылку
    '''
    markup = types.InlineKeyboardMarkup(row_width=1)
    button_reset = types.InlineKeyboardButton('Начать заново', callback_data='reset')
    markup.add(button_reset)
    bot.send_message(chat.message.chat.id,'Если хотите продолжить пользоваться нашим сервисом и узнавать краткое описание благодаря нам'
                                          ', нажмите на кнопку <b>"Начать заново!"</b>', parse_mode='html',reply_markup=markup)

def chat_bot_callback(chat):
    bot.send_message(chat.message.chat.id, 'Принято, идет обработка вашего запроса. Пожалуйста, подождите!')
    bot.delete_message(chat.message.chat.id, chat.message.message_id)
    chat_bot.get_chat_id(chat.from_user.id)
    chat_bot.download_audio()

@bot.callback_query_handler(func=lambda call:True)
def callback_message(call):
    '''
    Здесь мы обращаемся к названиям наших кнопок, которые мы указали в параметре callback_data
    'short-desc' - Краткое описание
    'time-code' - Тайм-коды
    'change_url' - Поменять ссылку
    'reset' - Начать заново
    '''
    if call.data == 'short_desc':
        bot.callback_query_handler(chat_bot_callback(call))
        chat_bot.do_short()
        # Функция описания
        desc = open(f'short_description_{call.from_user.id}.txt').read()
        bot.send_message(call.message.chat.id, f'Ваше краткое описание: {desc}')
        bot.callback_query_handler(reset(call))
    if call.data == 'time_code':
        bot.callback_query_handler(chat_bot_callback(call))
        chat_bot.do_scribe()
        scribe = open(f'scribe_video_{call.from_user.id}.txt').read()
        bot.send_message(call.message.chat.id, f'Ваши тайм коды: {scribe}')
        bot.callback_query_handler(reset(call))
    if call.data == 'change_url':
        bot.send_message(call.message.chat.id, 'Хорошо, введите другой адрес вашей ссылки')
        bot.delete_message(call.message.chat.id, call.message.message_id)
    if call.data == 'reset':
        bot.send_message(call.message.chat.id, 'Введите новую ссылку для работы с нашим ботом!')
        bot.delete_message(call.message.chat.id, call.message.message_id)

bot.infinity_polling()