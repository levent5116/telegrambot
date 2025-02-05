import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import API_TOKEN, STEAM_API_KEY

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Привет! Напиши /help, чтобы узнать о моих функциях!")

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

#обработчик команды /help
@dp.message_handler(commands=['help'])
async def fetch_steam_user(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply('Напишите /steam {Ваш Steam ID} нужного аккаунта, а затем получите информацию об играх или /track {Ваш Steam ID}, чтобы начать отслеживать активность.\n'
                            'Чтобы найти ID:\n'
                            '1. Зайдите в steam\n'
                            '2. Нажмите "Об аккаунте"\n'
                            '3. Скопируйте Steam ID в левом верхнем углу')
        return
    steam_id = args.strip()
    


tracked_users = {}
async def fetch_steam_status(steam_id):
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&format=json&steamids={steam_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data and "response" in data and "players" in data["response"]:
                    return data["response"]["players"][0]
            return None

async def track_user_activity(steam_id, chat_id):
    last_game = None

    while steam_id in tracked_users:  # Отслеживаем, пока пользователь есть в списке
        status = await fetch_steam_status(steam_id)
        if status:
            game_name = status.get("gameextrainfo")
            if game_name and game_name != last_game:
                last_game = game_name
                await bot.send_message(chat_id, f"Пользователь Steam ID {steam_id} начал играть в {game_name}.")
            elif not game_name and last_game:
                await bot.send_message(chat_id, f"Пользователь Steam ID {steam_id} больше не играет.")
                last_game = None
        await asyncio.sleep(30)  # Задержка между проверками (30 секунд)

# Обработчик команды /track {steam_id}
@dp.message_handler(commands=['track'])
async def start_tracking(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("Пожалуйста, укажите Steam ID после команды. Пример: /track 76561197960435530")
        return
    steam_id = args.strip()

    if not steam_id.isdigit():
        await message.reply("Неверный формат Steam ID. Steam ID должен состоять только из цифр.")
        return

    if steam_id in tracked_users:
        await message.reply(f"Отслеживание пользователя Steam ID {steam_id} уже включено.")
        return

    tracked_users[steam_id] = message.chat.id
    await message.reply(f"Начинаю отслеживать активность пользователя Steam ID {steam_id}.")

    # Запускаем отслеживание активности
    asyncio.create_task(track_user_activity(steam_id, message.chat.id))

# Обработчик команды /untrack {steam_id}
@dp.message_handler(commands=['untrack'])
async def stop_tracking(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("Пожалуйста, укажите Steam ID после команды. Пример: /untrack 76561197960435530")
        return
    steam_id = args.strip()

    if steam_id not in tracked_users:
        await message.reply(f"Пользователь Steam ID {steam_id} не отслеживается.")
        return

    del tracked_users[steam_id]  # Удаляем пользователя из списка отслеживаемых
    await message.reply(f"Отслеживание пользователя Steam ID {steam_id} остановлено.")

@dp.message_handler()
async def some_message(msg: types.Message):
    # Создаем инлайн-кнопку
    steam_button = InlineKeyboardButton("Отслеживать активность Steam", callback_data="track_steam_activity")
    keyboard = InlineKeyboardMarkup().add(steam_button)

    await msg.reply("Нажмите кнопку ниже, чтобы начать отслеживать активность Steam.", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'track_steam_activity')
async def process_callback_track_steam(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите команду /track {Ваш Steam ID}, чтобы начать отслеживать активность.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
