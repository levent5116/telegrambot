import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import API_TOKEN, STEAM_API_KEY

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


# Функция для получения данных об играх пользователя
async def fetch_steam_games(steam_id):
    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={steam_id}&include_appinfo=true&format=json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                return None

# Обработчик команды /steam {steam_id}
@dp.message_handler(commands=['steam'])
async def fetch_steam_user(message: types.Message):
    # Получаем аргументы команды (Steam ID)
    args = message.get_args()
    if not args:
        await message.reply("Пожалуйста, укажите Steam ID после команды. Пример: /steam 76561197960435530")
        return
    steam_id = args.strip()

    # Проверяем, что Steam ID состоит только из цифр
    if not steam_id.isdigit():
        await message.reply("Неверный формат Steam ID. Steam ID должен состоять только из цифр.")
        return

    # Получаем данные о играх пользователя
    games_data = await fetch_steam_games(steam_id)
    print(games_data)
    if games_data and 'response' in games_data and 'games' in games_data['response'] and 'game_count' in games_data['response']:
        games = games_data['response']['games']
        game_count = games_data['response']['game_count']

        games = sorted(games, key=lambda x: x['playtime_forever'], reverse=True)
        top_games = games[:5]  # Берём только топ-5 игр

        reply_message = f'Всего игр на аккаунте пользователя с ID {steam_id}: {game_count}\n'

        reply_message += f"\nТоп-5 игр по часам:\n"
        for game in top_games:
            name = game.get('name', 'Неизвестная игра')
            playtime = game.get('playtime_forever', 0) // 60  # Время в часах
            reply_message += f"• {name}: {playtime} ч.\n"

        await message.reply(reply_message)
    else:
        await message.reply("Не удалось получить список игр. Возможно, профиль Steam закрыт или у пользователя нет игр.")


@dp.message_handler(commands=['help'])
async def fetch_steam_user(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply('Напишите /steam и ID нужного аккаунта, а затем получите информацию об играх.\n'
                            'Чтобы найти ID:\n'
                            '1. Зайдите в steam\n'
                            '2. Нажмите "Об аккаунте"\n'
                            '3. Скопируйте Steam ID в левом верхнем углу')
        return
    steam_id = args.strip()
    

# Обработчик произвольного сообщения с инлайн-кнопкой для вызова команды /steam
@dp.message_handler()
async def some_message(msg: types.Message):
    # Создаем инлайн-кнопку с командой /steam (в данном случае, Steam ID нужно будет ввести вручную)
    steam_button = InlineKeyboardButton("Получить информацию об играх на аккаунте", callback_data="get_steam_games")
    keyboard = InlineKeyboardMarkup().add(steam_button)

    # Отправляем сообщение с инлайн-клавиатурой
    await msg.reply("Нажмите кнопку ниже для получения статистики из игр аккаунта Steam.", reply_markup=keyboard)


# Обработчик нажатия на инлайн-кнопку
@dp.callback_query_handler(lambda c: c.data == 'get_steam_games')
async def process_callback_get_steam_games(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите команду /steam {Ваш Steam ID}, чтобы получить список игр.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
