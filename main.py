import telebot

import json

import requests

from googletrans import Translator

from random import randint

from config import TELEGRAM_TOKEN, TRAINING_URL, CALORIE_URL, RECIPE_URL

translator = Translator()

src = 'en'
dest = 'ru'

bot = telebot.TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(commands=['start', 'calorie', 'recipe', 'training'])
def send_welcome(message):
    if message.text == '/start':
        bot.send_message(
            message.chat.id, "Приветствую. У данного бота есть несколько функций. \
            \n/calorie - Позволяет получить калории потребленного продукта на 100г. \
            \n/recipe - Позволяет получить рецепты и способы приготовления. \
            \n/training - Позволяет получить советы по тренировкам и разным активностям \
            \n/products - Позволяет получить список потребленных продуктов \
            \n/total - Позволяет получить общее количество потребленных калорий\
            \n/delete - Позволяет удалить данные потребленных продуктов")
    elif message.text == '/recipe':
        bot.send_message(message.chat.id, 'Введите название блюда')
        bot.register_next_step_handler(message, get_recipe)
    elif message.text == '/calorie':
        bot.send_message(message.chat.id, 'Введите полное наименование продукта')
        bot.register_next_step_handler(message, get_calorie)
    elif message.text == '/training':
        bot.send_message(
            message.chat.id, 'Введите уровень интенсивности упражнений от 1 до 9')
        bot.register_next_step_handler(message, get_training)
    else:
        bot.send_message(
            message.chat.id, 'Возможно вы ввели что-то неправильно, попробуйте снова.')


@bot.message_handler(commands=['training'])
def get_training(message):
    global calorie
    training = message.text

    url = TRAINING_URL

    querystring = {"intensitylevel": {training}}

    headers = {
        "X-RapidAPI-Key": "967c982515msha50cd70afb16f44p129c58jsn6d1391c9dc10",
        "X-RapidAPI-Host": "fitness-calculator.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        data = response.json()
        number_train = randint(1, 10)
        activity = data["data"][number_train]["activity"]
        metValue = str(data["data"][number_train]["metValue"])
        description = data["data"][number_train]["description"]
        intensityLevel = str(data["data"][number_train]["intensityLevel"])
        activity_ru = translator.translate(activity, src=src, dest=dest).text
        description_ru = translator.translate(
            description, src=src, dest=dest).text
        rate = "<b>Название упражнения: </b> " + activity_ru + "\n" + \
            "<b>Время выполнения (в минутах): </b> " + metValue + "\n" + \
            "<b>Описание: </b> " + description_ru + "\n" + \
            "<b>Уровень интенсивности: </b> " + intensityLevel
        bot.reply_to(message, rate, parse_mode="HTML")
    else:
        bot.send_message(
            message.chat.id, 'Возможно вы ввели что-то неправильно, попробуйте снова.')


@bot.message_handler(commands=['products'])
def get_products(message):
    if message.text == '/products':
        with open('total_ccal.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            products = [d["name"] for d in data]
        rate = "<b>Потребленные продукты:</b> " + \
            str(', '.join(products))
        bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['delete'])
def get_products(message):
    if message.text == '/delete':
        with open('total_ccal.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        data = [item for item in data if not isinstance(item, dict)]

        with open('total_ccal.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

        rate = "<b>Все продукты из списка успешно удалены.</b> "
        bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['total'])
def get_calories_total(message):
    if message.text == '/total':
        with open('total_ccal.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            calories = [d["calories"] for d in data]
            total_calories = sum(calories)
        rate = "<b>Общее количество калорий:</b> " + \
            str(total_calories)
        bot.reply_to(message, rate, parse_mode="HTML")


@bot.message_handler(commands=['calorie'])
def get_calorie(message):
    global calorie
    calorie = message.text
    url = CALORIE_URL
    calorie_en = translator.translate(calorie, src="ru", dest="en").text

    querystring = {"query": {calorie_en}, "pageSize": "1",
                   "pageNumber": "1", "brandOwner": "Kar Nut Products Company"}

    headers = {
        "X-RapidAPI-Key": "967c982515msha50cd70afb16f44p129c58jsn6d1391c9dc10",
        "X-RapidAPI-Host": "food-nutrition-information.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        data = response.json()
        squirrels = data["foods"][0]["foodNutrients"][0]["value"]
        fats = data["foods"][0]["foodNutrients"][1]["value"]
        carbohyd = data["foods"][0]["foodNutrients"][2]["value"]
        calories_result = float(((squirrels + carbohyd) * 4) + (fats * 9))
        with open('total_ccal.json', 'r+', encoding='utf-8') as f:
            file_data = json.load(f)
            calorie_dict = {"name": calorie,
                            "calories": calories_result}
            file_data.append(calorie_dict)
            f.seek(0)
            json.dump(file_data, f, indent=4, ensure_ascii=False)
        rate = "<b>Содержание калорий в 100г продукта:</b> " + \
            str(calories_result)
        bot.reply_to(message, rate, parse_mode="HTML")
    else:
        bot.send_message(
            message.chat.id, 'Возможно вы ввели что-то неправильно, попробуйте снова.')


@bot.message_handler(commands=['recipe'])
def get_recipe(message):
    global name_dish
    name_dish = message.text
    url = RECIPE_URL
    name_dish_en = translator.translate(name_dish, src="ru", dest="en").text

    querystring = {"query": {name_dish_en}}

    headers = {
        "X-RapidAPI-Key": "967c982515msha50cd70afb16f44p129c58jsn6d1391c9dc10",
        "X-RapidAPI-Host": "recipe-by-api-ninjas.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        data = response.json()
        title = data[0]["title"]
        ingredients = data[0]["ingredients"]
        instructions = data[0]["instructions"]
        title_ru = translator.translate(title, src=src, dest=dest).text
        ingredients_ru = translator.translate(
            ingredients, src=src, dest=dest).text
        instructions_ru = translator.translate(
            instructions, src=src, dest=dest).text
        rate = "<b>Название блюда:</b> " + title_ru + "\n" + \
            "<b>Ингредиенты:</b> " + ingredients_ru + "\n" + \
            "<b>Способ приготовления:</b> " + instructions_ru
        bot.reply_to(message, rate, parse_mode="HTML")
    else:
        bot.send_message(
            message.chat.id, 'Возможно вы ввели что-то неправильно, попробуйте снова.')


def main():
    bot.infinity_polling()


if __name__ == '__main__':
    main()
