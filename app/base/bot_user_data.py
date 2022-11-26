from aiogram import types


class FAQReader:

    def __init__(self, faq_dict: dict):
        self.faq_dict = faq_dict

    def get_questions(self):
        questions = []
        for num, data in self.faq_dict.items():
            questions.append(data[0])
        return questions

    async def get_keyboard(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

        for question in self.get_questions():
            button = types.KeyboardButton(text=question)
            keyboard.add(button)
        back_button = types.KeyboardButton(text="Назад")
        keyboard.add(back_button)
        return keyboard

    def get_answer(self, question):
        for num, data in self.faq_dict.items():
            if question == data[0]:
                return data[1]
        return False

    def add_question(self, question_data: list):
        last_value = len(self.faq_dict)
        self.faq_dict[last_value + 1] = question_data


def get_faq():
    faq = FAQReader(FAQ)
    return faq

FAQ = {1: ["Есть ли у вас доставка?", "Да, доставляем бесплатно с 10:00 до 20:00"],
       2: ["Способы оплаты", "Пока доступны только наличные в магазине или курьеру"]}

posts = ['шлифовщик', 'маляр', 'столяр']

months = {1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
         7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"}

