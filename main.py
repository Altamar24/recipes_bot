from random import randint

from googletrans import Translator
import requests
import telebot
from sqlalchemy import text, exc

from config import (
    TELEGRAM_TOKEN,
    TRAINING_URL,
    CALORIE_URL,
    RECIPE_URL,
    TRAINING_API,
    RECIPE_API,
    CALORIE_API
)
from db_connect import db

translator = Translator()

src = 'en'
dest = 'ru'

bot = telebot.TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Функция при вводе /start возвращает следующее сообщение с командами"""

    start_msg = (
        f"Приветствую. У данного бота есть несколько функций:\n"
        f"/calorie - Позволяет получить калории потребленного продукта на 100г.\n"
        f"/recipe - Позволяет получить рецепты и способы приготовления.\n"
        f"/training - Позволяет получить советы по тренировкам и разным активностям.\n"
        f"/products - Позволяет получить список потребленных продуктов.\n"
        f"/total - Позволяет получить общее количество потребленных калорий.\n"
        f"/delete - Позволяет удалить данные потребленных продуктов."
    )

    bot.send_message(message.chat.id, start_msg)


@bot.message_handler(commands=['recipe'])
def recipe_com(message):
    """Функция при вводе /recipe запрашивает название блюда"""

    bot.send_message(message.chat.id, 'Введите название блюда')
    bot.register_next_step_handler(message, get_recipe)


@bot.message_handler(commands=['calorie'])
def calorie_com(message):
    """Функция при вводе /calorie запрашивает название продукта"""

    message_error = 'Введите полное наименование продукта'
    bot.send_message(message.chat.id, message_error)
    bot.register_next_step_handler(message, get_calorie)


@bot.message_handler(commands=['training'])
def training_com(message):
    """Функция при вводе /training запрашивает уровень интенсивности тренировки"""

    message_error = 'Введите уровень интенсивности упражнений от 1 до 9'
    bot.send_message(
        message.chat.id, message_error)
    bot.register_next_step_handler(message, get_training)


@bot.message_handler(commands=['training'])
def get_training(message):
    """Функция возвращает тренировку = введенному уровню."""

    try:
        training = int(message.text)
    except ValueError:
        bot.reply_to(
            message, (f'Ошибка. Вы ввели не число.'))

    querystring = {"intensitylevel": {training}}

    try:
        response = requests.get(
            TRAINING_URL, headers=TRAINING_API, params=querystring)
    except requests.ConnectionError as e:
        bot.reply_to(
            message, (f'Ошибка {e}! Невозможно связаться с сервером.'))

    if response.status_code == 200:
        data = response.json()
    else:
        bot.reply_to(
            message, (f'Ошибка: {response.status_code}'))

    number_train = randint(1, 10)

    try:
        activity = data["data"][number_train]["activity"]
        met_value = data["data"][number_train]["metValue"]
        description = data["data"][number_train]["description"]
        intensity_level = data["data"][number_train]["intensityLevel"]
        activity_ru = translator.translate(
            activity, src=src, dest=dest).text
        description_ru = translator.translate(
            description, src=src, dest=dest).text
        rate = (
            f"<b>Название упражнения: </b> {activity_ru}\n"
            f"<b>Время выполнения (в минутах): </b> {met_value}\n"
            f"<b>Описание: </b> {description_ru}\n"
            f"<b>Уровень интенсивности: </b> {intensity_level}"
        )
        bot.reply_to(message, rate, parse_mode="HTML")
    except (KeyError, UnboundLocalError, IndexError):
        bot.reply_to(
            message, (f"Ошибка. Введите уровень от 1 до 9."))


@bot.message_handler(commands=['calorie'])
def get_calorie(message):
    """Функция возвращает количество калорий введенного продукта и добавляет его в базу данных"""

    user_id = message.from_user.id
    calorie = message.text
    calorie_en = translator.translate(calorie, src="ru", dest="en").text
    querystring = {"query": {calorie_en}, "pageSize": "1",
                   "pageNumber": "1", "brandOwner": "Kar Nut Products Company"}

    try:
        response = requests.get(
            CALORIE_URL, headers=CALORIE_API, params=querystring)
    except requests.ConnectionError as e:
        bot.reply_to(
            message, (f"Ошибка {e}! Невозможно связаться с сервером."))

    if response.status_code == 200:
        data = response.json()
    else:
        bot.reply_to(
            message, (f"Ошибка: {response.status_code}"))

    try:
        foods_dict = data["foods"][0]["foodNutrients"]
        squirrels = foods_dict[0]["value"]
        fats = foods_dict[1]["value"]
        carbohyd = foods_dict[2]["value"]
        calories_result = float(((squirrels + carbohyd) * 4) + (fats * 9))
    except (KeyError, UnboundLocalError, IndexError):
        bot.reply_to(
            message, (f"Возможно вы допустили ошибку в названии, попробуйте снова."))
    try:
        db.execute(
            text(
                f"INSERT INTO products_list (user_id, name, calories)"
                f"VALUES ('{user_id}', '{calorie}', '{calories_result}');"
            )
        )
        db.commit()

        rate = (
            f"<b>Содержание калорий в 100г продукта: </b>" +
            f"{str(calories_result)}"
        )
        bot.reply_to(message, rate, parse_mode="HTML")
    except DBAPIerrors as e:
        bot.reply_to(
            message, (f"Ошибка {e}."))


@bot.message_handler(commands=['products'])
def get_products(message):
    """Функция возвращает список продуктов из базы данных"""

    user_id = message.from_user.id

    try:
        user_products = db.execute(
            text(
                f"SELECT * "
                f"FROM products_list "
                f"WHERE user_id = {user_id};"
            )
        ).fetchall()
    except exc.SQLAlchemyError as e:
        bot.reply_to(
            message, (f"Ошибка {e}."))

    if user_products:
        rate = "<b>Потребленные продукты: </b>\n"
        for product in user_products:
            rate += f"Название: {product.name}, Калории: {product.calories}\n"
        bot.reply_to(message, rate, parse_mode="HTML")
    else:
        bot.reply_to(message, 'Список пуст.')


@bot.message_handler(commands=['total'])
def get_calories_total(message):
    """Функция возвращает общее количество калорий продуктов из базы данных"""

    user_id = message.from_user.id
    total_calories = 0

    try:
        user_products = db.execute(
            text(
                f"SELECT * "
                f"FROM products_list "
                f"WHERE user_id = {user_id};"
            )
        ).fetchall()
    except exc.SQLAlchemyError as e:
        bot.reply_to(
            message, (f"Ошибка {e}."))

    if user_products:
        for product in user_products:
            total_calories += sum({product.calories})
        rate = f"<b>Общее количество калорий:</b> {total_calories}"
        bot.reply_to(message, rate, parse_mode="HTML")
    else:
        bot.reply_to(message, 'Список пуст.')


@bot.message_handler(commands=['delete'])
def delete_products(message):
    """Функция удаляет продукты из базы данных"""

    user_id = message.from_user.id

    try:
        user_products = db.execute(
            text(
                f"SELECT COUNT(*) "
                f"FROM products_list "
                f"WHERE user_id = {user_id};"
            )
        )
    except exc.SQLAlchemyError as e:
        bot.reply_to(
            message, (f"Ошибка {e}."))

    count = user_products.fetchone()[0]

    if count == 0:
        bot.reply_to(message, "Список пуст.")
    else:
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
    """Функция возвращает рецепт введенного блюда."""

    name_dish = message.text
    name_dish_en = translator.translate(
        name_dish, src="ru", dest="en").text
    querystring = {"query": {name_dish_en}}

    try:
        response = requests.get(
            RECIPE_URL, headers=RECIPE_API, params=querystring)
    except requests.ConnectionError as e:
        bot.reply_to(
            message, (f"Ошибка {e}! Невозможно связаться с сервером."))

    if response.status_code == 200:
        data = response.json()
    else:
        bot.reply_to(
            message, (f"Ошибка: {response.status_code}"))

    try:
        title = data[0]["title"]
        ingredients = data[0]["ingredients"]
        instructions = data[0]["instructions"]
        title_ru = translator.translate(title, src=src, dest=dest).text
        ingredients_ru = translator.translate(
            ingredients, src=src, dest=dest).text
        instructions_ru = translator.translate(
            instructions, src=src, dest=dest).text
        rate = (
            f"<b>Название блюда:</b> {title_ru}\n"
            f"<b>Ингредиенты:</b> {ingredients_ru}\n"
            f"<b>Способ приготовления:</b> {instructions_ru}"
        )
        bot.reply_to(message, rate, parse_mode="HTML")
    except (KeyError, UnboundLocalError, IndexError):
        bot.reply_to(
            message, "Возможно вы ввели что-то неправильно, попробуйте снова.")


def main():
    bot.infinity_polling()


if __name__ == '__main__':
    main()
