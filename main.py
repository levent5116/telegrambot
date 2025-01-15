import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
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

        reply_message = f'Всего игр на аккаунте пользователя Steam ID {steam_id}: {game_count}\n'

        reply_message += f"Топ-5 игр по часам:\n"
        for game in top_games:
            name = game.get('name', 'Неизвестная игра')
            playtime = game.get('playtime_forever', 0) // 60  # Время в часах
            reply_message += f"• {name}: {playtime} ч.\n"

        await message.reply(reply_message)
    else:
        await message.reply("Не удалось получить список игр. Возможно, профиль Steam закрыт или у пользователя нет игр.")


@dp.message_handler()
async def echo_message(msg: types.Message):
    await msg.reply(msg.text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)