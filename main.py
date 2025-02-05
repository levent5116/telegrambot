import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import API_TOKEN, STEAM_API_KEY

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения профилей пользователей
user_profiles = {}

# Максимальное количество профилей на пользователя
MAX_PROFILES_PER_USER = 5

# обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Привет! Напиши /help, чтобы узнать о моих функциях!")

# Обработчик команды /register
@dp.message_handler(commands=['register'])
async def register_user(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("Пожалуйста, укажите имя профиля и Steam ID через пробел. Пример: /register Иван 76561197960435530")
        return

    try:
        profile_name, steam_id = args.split(maxsplit=1)
        if not steam_id.isdigit():
            await message.reply("Неверный формат Steam ID. Steam ID должен состоять только из цифр.")
            return

        user_id = message.from_user.id
        if user_id not in user_profiles:
            user_profiles[user_id] = {}

        if len(user_profiles[user_id]) >= MAX_PROFILES_PER_USER:
            await message.reply(f"Вы можете зарегистрировать не более {MAX_PROFILES_PER_USER} профилей.")
            return

        # Проверка Steam ID через Steam API
        if not await validate_steam_id(steam_id):
            await message.reply("Неверный Steam ID. Пожалуйста, проверьте правильность ввода.")
            return

        user_profiles[user_id][profile_name] = steam_id
        await message.reply(f"Профиль успешно создан! Имя: {profile_name}, Steam ID: {steam_id}.")
    except ValueError:
        await message.reply("Неверный формат команды. Пример: /register Иван 76561197960435530")

# Функция для проверки Steam ID через Steam API
async def validate_steam_id(steam_id):
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("response", {}).get("players", []) != []
            return False

# Обработчик команды /list
@dp.message_handler(commands=['list'])
async def list_profiles(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles or not user_profiles[user_id]:
        await message.reply("У вас нет зарегистрированных профилей.")
        return

    reply_message = "Ваши зарегистрированные профили:\n"
    for profile_name, steam_id in user_profiles[user_id].items():
        reply_message += f"• {profile_name}: {steam_id}\n"

    await message.reply(reply_message)

# Обработчик команды /delete
@dp.message_handler(commands=['delete'])
async def delete_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles or not user_profiles[user_id]:
        await message.reply("У вас нет зарегистрированных профилей.")
        return

    args = message.get_args()
    if not args:
        await message.reply("Пожалуйста, укажите имя профиля для удаления. Пример: /delete Иван")
        return

    profile_name = args.strip()
    if profile_name not in user_profiles[user_id]:
        await message.reply(f"Профиль с именем {profile_name} не найден.")
        return

    del user_profiles[user_id][profile_name]
    await message.reply(f"Профиль {profile_name} успешно удалён.")

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

# Обработчик команды /steam
@dp.message_handler(commands=['steam'])
async def fetch_steam_user(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles or not user_profiles[user_id]:
        await message.reply("Сначала зарегистрируйте хотя бы один Steam ID с помощью команды /register.")
        return

    # Создаем клавиатуру для выбора профиля
    keyboard = InlineKeyboardMarkup(row_width=1)
    for profile_name in user_profiles[user_id]:
        button = InlineKeyboardButton(profile_name, callback_data=f"steam_{profile_name}")
        keyboard.add(button)

    await message.reply("Выберите профиль для получения информации об играх:", reply_markup=keyboard)

# Обработчик выбора профиля для /steam
@dp.callback_query_handler(lambda c: c.data.startswith('steam_'))
async def process_steam_profile(callback_query: types.CallbackQuery):
    profile_name = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    steam_id = user_profiles[user_id][profile_name]

    # Получаем данные о играх пользователя
    games_data = await fetch_steam_games(steam_id)
    if games_data and 'response' in games_data and 'games' in games_data['response'] and 'game_count' in games_data['response']:
        games = games_data['response']['games']
        game_count = games_data['response']['game_count']
        total_playtime = sum(game.get('playtime_forever', 0) for game in games) // 60  # Общее время в часах

        games = sorted(games, key=lambda x: x['playtime_forever'], reverse=True)
        top_games = games[:5]  # Берём только топ-5 игр

        reply_message = f'📊 Статистика для профиля {profile_name}:\n'
        reply_message += f"• Всего игр: {game_count}\n"
        reply_message += f"• Общее время в играх: {total_playtime} ч.\n"
        reply_message += f"\n🎮 Топ-5 игр по времени:\n"
        for game in top_games:
            game_name = game.get('name', 'Неизвестная игра')
            playtime = game.get('playtime_forever', 0) // 60  # Время в часах
            reply_message += f"• {game_name}: {playtime} ч.\n"

        await bot.send_message(callback_query.from_user.id, reply_message)
    else:
        await bot.send_message(callback_query.from_user.id, "Не удалось получить список игр. Возможно, профиль Steam закрыт или у пользователя нет игр.")

# Обработчик команды /help
@dp.message_handler(commands=['help'])
async def fetch_steam_user(message: types.Message):
    await message.reply(
        'Доступные команды:\n'
        '/register {Имя профиля} {Steam ID} - Зарегистрировать новый Steam ID.\n'
        '/list - Показать список всех профилей.\n'
        '/delete {Имя профиля} - Удалить профиль.\n'
        '/steam - Получить информацию об играх.\n'
        '/track - Начать отслеживание активности.\n'
        '/untrack - Остановить отслеживание активности.\n'
        '/info - Показать информацию о профиле.\n'
        'Чтобы найти Steam ID:\n'
        '1. Зайдите в Steam.\n'
        '2. Нажмите "Об аккаунте".\n'
        '3. Скопируйте Steam ID в левом верхнем углу.'
    )

# Обработчик команды /info
@dp.message_handler(commands=['info'])
async def show_profile_info(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles or not user_profiles[user_id]:
        await message.reply("У вас нет зарегистрированных профилей.")
        return

    args = message.get_args()
    if not args:
        await message.reply("Пожалуйста, укажите имя профиля. Пример: /info Иван")
        return

    profile_name = args.strip()
    if profile_name not in user_profiles[user_id]:
        await message.reply(f"Профиль с именем {profile_name} не найден.")
        return

    steam_id = user_profiles[user_id][profile_name]
    games_data = await fetch_steam_games(steam_id)
    if games_data and 'response' in games_data and 'games' in games_data['response'] and 'game_count' in games_data['response']:
        games = games_data['response']['games']
        game_count = games_data['response']['game_count']
        total_playtime = sum(game.get('playtime_forever', 0) for game in games) // 60  # Общее время в часах

        reply_message = f'📋 Информация о профиле {profile_name}:\n'
        reply_message += f"• Steam ID: {steam_id}\n"
        reply_message += f"• Всего игр: {game_count}\n"
        reply_message += f"• Общее время в играх: {total_playtime} ч.\n"

        await message.reply(reply_message)
    else:
        await message.reply("Не удалось получить информацию о профиле.")

# Отслеживание активности
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

async def track_user_activity(steam_id, chat_id, profile_name):
    last_game = None

    while steam_id in tracked_users:  # Отслеживаем, пока пользователь есть в списке
        status = await fetch_steam_status(steam_id)
        if status:
            game_name = status.get("gameextrainfo")
            if game_name and game_name != last_game:
                last_game = game_name
                await bot.send_message(chat_id, f"🎮 Пользователь {profile_name} начал играть в {game_name}.")
            elif not game_name and last_game:
                await bot.send_message(chat_id, f"🛑 Пользователь {profile_name} больше не играет.")
                last_game = None
        await asyncio.sleep(30)  # Задержка между проверками (30 секунд)

# Обработчик команды /track
@dp.message_handler(commands=['track'])
async def start_tracking(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles or not user_profiles[user_id]:
        await message.reply("Сначала зарегистрируйте хотя бы один Steam ID с помощью команды /register.")
        return

    # Создаем клавиатуру для выбора профиля
    keyboard = InlineKeyboardMarkup(row_width=1)
    for profile_name in user_profiles[user_id]:
        button = InlineKeyboardButton(profile_name, callback_data=f"track_{profile_name}")
        keyboard.add(button)

    await message.reply("Выберите профиль для отслеживания активности:", reply_markup=keyboard)

# Обработчик выбора профиля для /track
@dp.callback_query_handler(lambda c: c.data.startswith('track_'))
async def process_track_profile(callback_query: types.CallbackQuery):
    profile_name = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    steam_id = user_profiles[user_id][profile_name]

    if steam_id in tracked_users:
        await bot.send_message(callback_query.from_user.id, f"Отслеживание профиля {profile_name} уже включено.")
        return

    tracked_users[steam_id] = callback_query.from_user.id
    await bot.send_message(callback_query.from_user.id, f"Начинаю отслеживать активность профиля {profile_name}.")

    # Запускаем отслеживание активности
    asyncio.create_task(track_user_activity(steam_id, callback_query.from_user.id, profile_name))

# Обработчик команды /untrack
@dp.message_handler(commands=['untrack'])
async def stop_tracking(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles or not user_profiles[user_id]:
        await message.reply("Сначала зарегистрируйте хотя бы один Steam ID с помощью команды /register.")
        return

    # Создаем клавиатуру для выбора профиля
    keyboard = InlineKeyboardMarkup(row_width=1)
    for profile_name in user_profiles[user_id]:
        button = InlineKeyboardButton(profile_name, callback_data=f"untrack_{profile_name}")
        keyboard.add(button)

    await message.reply("Выберите профиль для остановки отслеживания:", reply_markup=keyboard)

# Обработчик выбора профиля для /untrack
@dp.callback_query_handler(lambda c: c.data.startswith('untrack_'))
async def process_untrack_profile(callback_query: types.CallbackQuery):
    profile_name = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    steam_id = user_profiles[user_id][profile_name]

    if steam_id not in tracked_users:
        await bot.send_message(callback_query.from_user.id, f"Профиль {profile_name} не отслеживается.")
        return

    del tracked_users[steam_id]  # Удаляем пользователя из списка отслеживаемых
    await bot.send_message(callback_query.from_user.id, f"Отслеживание профиля {profile_name} остановлено.")

@dp.message_handler()
async def some_message(msg: types.Message):
    # Создаем инлайн-кнопку
    steam_button = InlineKeyboardButton("Отслеживать активность Steam", callback_data="track_steam_activity")
    keyboard = InlineKeyboardMarkup().add(steam_button)

    await msg.reply("Нажмите кнопку ниже, чтобы начать отслеживать активность Steam.", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'track_steam_activity')
async def process_callback_track_steam(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите команду /track, чтобы начать отслеживать активность.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
