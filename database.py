import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    """ Создать соединение с SQLite базой данных """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"Connected to SQLite, version {sqlite3.version}")
        return conn
    except Error as e:
        print(e)
    
    return conn

def create_tables(conn):
    """ Создать таблицы в базе данных """
    sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                    user_id INTEGER PRIMARY KEY,
                                    username TEXT,
                                    first_name TEXT,
                                    last_name TEXT,
                                    registration_date TEXT DEFAULT CURRENT_TIMESTAMP
                                ); """
    
    sql_create_profiles_table = """ CREATE TABLE IF NOT EXISTS profiles (
                                    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER NOT NULL,
                                    profile_name TEXT NOT NULL,
                                    steam_id TEXT NOT NULL,
                                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                                    UNIQUE (user_id, profile_name)
                                ); """
    
    sql_create_tracking_table = """ CREATE TABLE IF NOT EXISTS tracking (
                                    tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER NOT NULL,
                                    steam_id TEXT NOT NULL,
                                    profile_name TEXT NOT NULL,
                                    is_active INTEGER DEFAULT 1,
                                    last_check TEXT,
                                    last_game TEXT,
                                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                                ); """
    
    try:
        c = conn.cursor()
        c.execute(sql_create_users_table)
        c.execute(sql_create_profiles_table)
        c.execute(sql_create_tracking_table)
        conn.commit()
    except Error as e:
        print(e)

def initialize_database():
    """ Инициализировать базу данных """
    database = "steam_bot.db"
    
    # Создаем соединение с базой данных
    conn = create_connection(database)
    
    if conn is not None:
        # Создаем таблицы
        create_tables(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")

# Инициализируем базу данных при импорте
initialize_database()



def add_user(conn, user_id, username=None, first_name=None, last_name=None):
    """ Добавить нового пользователя в базу данных """
    sql = ''' INSERT OR IGNORE INTO users(user_id, username, first_name, last_name)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (user_id, username, first_name, last_name))
    conn.commit()
    return cur.lastrowid

def add_profile(conn, user_id, profile_name, steam_id):
    """ Добавить новый профиль Steam для пользователя """
    sql = ''' INSERT INTO profiles(user_id, profile_name, steam_id)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    try:
        cur.execute(sql, (user_id, profile_name, steam_id))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        # Профиль с таким именем уже существует для этого пользователя
        return None

def get_user_profiles(conn, user_id):
    """ Получить все профили пользователя """
    cur = conn.cursor()
    cur.execute("SELECT profile_name, steam_id FROM profiles WHERE user_id=?", (user_id,))
    return cur.fetchall()

def delete_profile(conn, user_id, profile_name):
    """ Удалить профиль пользователя """
    sql = ''' DELETE FROM profiles WHERE user_id=? AND profile_name=? '''
    cur = conn.cursor()
    cur.execute(sql, (user_id, profile_name))
    conn.commit()
    return cur.rowcount > 0

def start_tracking(conn, user_id, steam_id, profile_name):
    """ Начать отслеживание активности профиля """
    # Сначала проверяем, не отслеживается ли уже этот профиль
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM tracking WHERE user_id=? AND steam_id=? AND is_active=1", 
                (user_id, steam_id))
    if cur.fetchone():
        return False  # Уже отслеживается
    
    sql = ''' INSERT INTO tracking(user_id, steam_id, profile_name, is_active)
              VALUES(?,?,?,1) '''
    cur.execute(sql, (user_id, steam_id, profile_name))
    conn.commit()
    return True

def stop_tracking(conn, user_id, steam_id):
    """ Остановить отслеживание активности профиля """
    sql = ''' UPDATE tracking SET is_active=0 WHERE user_id=? AND steam_id=? AND is_active=1 '''
    cur = conn.cursor()
    cur.execute(sql, (user_id, steam_id))
    conn.commit()
    return cur.rowcount > 0

def get_active_tracking(conn):
    """ Получить список всех активных отслеживаний """
    cur = conn.cursor()
    cur.execute("SELECT user_id, steam_id, profile_name FROM tracking WHERE is_active=1")
    return cur.fetchall()

def update_tracking_status(conn, steam_id, last_game=None):
    """ Обновить статус отслеживания (последняя проверка, последняя игра) """
    sql = ''' UPDATE tracking SET last_check=CURRENT_TIMESTAMP, last_game=?
              WHERE steam_id=? AND is_active=1 '''
    cur = conn.cursor()
    cur.execute(sql, (last_game, steam_id))
    conn.commit()


# В начале файла добавьте:
from datetime import datetime
import sqlite3

# Замените инициализацию словарей на:
def get_db_connection():
    return sqlite3.connect("steam_bot.db")

# Пример изменения обработчика команды /register
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
        
        # Проверка Steam ID через Steam API
        if not await validate_steam_id(steam_id):
            await message.reply("Неверный Steam ID. Пожалуйста, проверьте правильность ввода.")
            return

        conn = get_db_connection()
        try:
            # Добавляем пользователя (если еще не существует)
            add_user(conn, user_id, message.from_user.username, 
                    message.from_user.first_name, message.from_user.last_name)
            
            # Проверяем количество профилей
            profiles = get_user_profiles(conn, user_id)
            if len(profiles) >= MAX_PROFILES_PER_USER:
                await message.reply(f"Вы можете зарегистрировать не более {MAX_PROFILES_PER_USER} профилей.")
                return
            
            # Добавляем профиль
            if add_profile(conn, user_id, profile_name, steam_id):
                await message.reply(f"Профиль успешно создан! Имя: {profile_name}, Steam ID: {steam_id}.")
            else:
                await message.reply(f"Профиль с именем {profile_name} уже существует.")
        finally:
            conn.close()
            
    except ValueError:
        await message.reply("Неверный формат команды. Пример: /register Иван 76561197960435530")
