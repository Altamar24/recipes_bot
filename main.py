import telebot
import requests

from sqlalchemy import text
from db_connect import db
from googletrans import Translator
from random import randint
from config import TELEGRAM_TOKEN, TRAINING_URL, CALORIE_URL, RECIPE_URL, TRAINING_API, RECIPE_API, CALORIE_API

translator = Translator()

src = 'en'
dest = 'ru'

bot = telebot.TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    start_msg = f"Приветствую. У данного бота есть несколько функций:"\
        f"\n/calorie - Позволяет получить калории потребленного продукта на 100г."\
        f"\n/recipe - Позволяет получить рецепты и способы приготовления."\
        f"\n/training - Позволяет получить советы по тренировкам и разным активностям."\
        f"\n/products - Позволяет получить список потребленных продуктов."\
        f"\n/total - Позволяет получить общее количество потребленных калорий."\
        f"\n/delete - Позволяет удалить данные потребленных продуктов."

    bot.send_message(
        message.chat.id, start_msg)


def keys():
    TRAINING_URL
    CALORIE_URL
    RECIPE_URL
    TRAINING_API
    RECIPE_API
    CALORIE_API


@bot.message_handler(commands=['recipe'])
def recipe_com(message):
    bot.send_message(message.chat.id, 'Введите название блюда')
    bot.register_next_step_handler(message, get_recipe)


@bot.message_handler(commands=['calorie'])
def calorie_com(message):
    bot.send_message(
        message.chat.id, 'Введите полное наименование продукта')
    bot.register_next_step_handler(message, get_calorie)


@bot.message_handler(commands=['training'])
def training_com(message):
    bot.send_message(
        message.chat.id, 'Введите уровень интенсивности упражнений от 1 до 9')
    bot.register_next_step_handler(message, get_training)


@bot.message_handler(commands=['training'])
def get_training(message):
    try:
        training = message.text
        querystring = {"intensitylevel": {training}}
        
        response = requests.get(
            TRAINING_URL, headers=TRAINING_API, params=querystring)
        
        data = response.json()
        number_train = randint(1, 10)
        activity = data["data"][number_train]["activity"]
        metValue = str(data["data"][number_train]["metValue"])
        description = data["data"][number_train]["description"]
        intensityLevel = str(data["data"][number_train]["intensityLevel"])
        activity_ru = translator.translate(activity, src=src, dest=dest).text
        description_ru = translator.translate(
            description, src=src, dest=dest).text
    except KeyError:
        bot.reply_to(
            message, 'Ошибка! Введите уровень от 1 до 9.')

    rate = f"<b>Название упражнения: </b> {activity_ru}"\
        f"\n<b>Время выполнения (в минутах): </b> {metValue}"\
        f"\n<b>Описание: </b> {description_ru}"\
        f"\n<b>Уровень интенсивности: </b> {intensityLevel}"
    bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['calorie'])
def get_calorie(message):
    user_id = message.from_user.id
    try:
        calorie = message.text
        calorie_en = translator.translate(calorie, src="ru", dest="en").text
        querystring = {"query": {calorie_en}, "pageSize": "1",
                       "pageNumber": "1", "brandOwner": "Kar Nut Products Company"}
        
        response = requests.get(
            CALORIE_URL, headers=CALORIE_API, params=querystring)

        data = response.json()
        foods_dict = data["foods"][0]["foodNutrients"]
        squirrels = foods_dict[0]["value"]
        fats = foods_dict[1]["value"]
        carbohyd = foods_dict[2]["value"]
        calories_result = float(((squirrels + carbohyd) * 4) + (fats * 9))

        db.execute(
            text(
                f'INSERT INTO products_list (user_id, name, calories)'
                f"VALUES ('{user_id}', '{calorie}', '{calories_result}');"
            )
        )
        db.commit()
    except (IndexError, UnboundLocalError):
        bot.reply_to(
            message, 'Возможно вы ввели что-то неправильно, попробуйте снова.')
        
    rate = f"<b>Содержание калорий в 100г продукта: </b>" + \
        f"{str(calories_result)}"
    bot.reply_to(message, rate, parse_mode="HTML")



@bot.message_handler(commands=['products'])
def get_products(message):
    user_id = message.from_user.id
    user_products = db.execute(
        text(
            f"SELECT * "
            f"FROM products_list "
            f"WHERE user_id = {user_id};"
        )
    ).fetchall()

    rate = "<b>Потребленные продукты: </b>\n"
    for product in user_products:
        rate += f"Название: {product.name}, Калории: {product.calories}\n"
    bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['total'])
def get_calories_total(message):
    user_id = message.from_user.id
    user_products = db.execute(
        text(
            f"SELECT * "
            f"FROM products_list "
            f"WHERE user_id = {user_id};"
        )
    ).fetchall()

    total_calories = 0
    for product in user_products:
        total_calories += sum({product.calories})
    rate = f"<b>Общее количество калорий:</b> {total_calories}"
    bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['delete'])
def get_products(message):
    user_id = message.from_user.id
    db.execute(
        text(
            f"DELETE "
            f"FROM products_list "
            f"WHERE user_id = {user_id};"
        )
    )
    db.commit()

    rate = "<b>Все продукты из списка успешно удалены.</b> "
    bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['recipe'])
def get_recipe(message):
    try:
        name_dish = message.text
        name_dish_en = translator.translate(
            name_dish, src="ru", dest="en").text
        querystring = {"query": {name_dish_en}}

        response = requests.get(
            RECIPE_URL, headers=RECIPE_API, params=querystring)

        data = response.json()
        title = data[0]["title"]
        ingredients = data[0]["ingredients"]
        instructions = data[0]["instructions"]
        title_ru = translator.translate(title, src=src, dest=dest).text
        ingredients_ru = translator.translate(
            ingredients, src=src, dest=dest).text
        instructions_ru = translator.translate(
            instructions, src=src, dest=dest).text
    except IndexError:
        bot.reply_to(
            message, 'Возможно вы ввели что-то неправильно, попробуйте снова.')
    rate = f"<b>Название блюда:</b> " + title_ru + "\n"\
        f"<b>Ингредиенты:</b> " + ingredients_ru + "\n"\
        f"<b>Способ приготовления:</b> " + instructions_ru
    bot.reply_to(message, rate, parse_mode="HTML")


def main():
    bot.infinity_polling()


if __name__ == '__main__':
    main()
