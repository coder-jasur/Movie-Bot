from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

random_movies = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎬 Tasodifiy Film"),
            KeyboardButton(text="📺 Tasodifiy Serial")
        ],
        [
            KeyboardButton(text="🍿 Tasodifiy Epizodli Film")
        ],
        [
            KeyboardButton(text="🔝 Top Filmlar")
        ],
        [
            KeyboardButton(text="🎭 Janr bo'yicha Film")
        ]
    ],
    resize_keyboard=True
)
