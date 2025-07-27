import logging
import json
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = set(map(int, os.getenv("ADMIN_IDS", "").split(",")))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
DATA_FILE = "data.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_action(action):
    data = load_data()
    data["logs"].append(action)
    save_data(data)

async def auto_unmute():
    while True:
        data = load_data()
        to_unmute = [uid for uid, time in data["muted"].items() if time <= asyncio.get_event_loop().time()]
        for uid in to_unmute:
            del data["muted"][uid]
            log_action(f"Авторазмут пользователя {uid}")
        save_data(data)
        await asyncio.sleep(30)

@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("👋 Добро пожаловать в Emergency Hamburg RP Help Bot!")

@dp.message_handler(commands=["mute"])
async def mute_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if len(args) < 3:
        return await message.reply("Используй: /mute user_id время(в минутах) причина")
    user_id, minutes = int(args[0]), int(args[1])
    reason = " ".join(args[2:])
    data = load_data()
    data["muted"][str(user_id)] = asyncio.get_event_loop().time() + minutes * 60
    log_action(f"Мут {user_id} на {minutes} мин. Причина: {reason}")
    save_data(data)
    await message.reply(f"✅ Пользователь {user_id} получил мут на {minutes} минут.")

@dp.message_handler(commands=["warn"])
async def warn_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if len(args) < 2:
        return await message.reply("Используй: /warn user_id причина")
    user_id, reason = int(args[0]), " ".join(args[1:])
    data = load_data()
    data["warns"].setdefault(str(user_id), []).append(reason)
    log_action(f"Варн {user_id}. Причина: {reason}")
    save_data(data)
    await message.reply(f"⚠️ Варн для {user_id}: {reason}")

@dp.message_handler(commands=["ban"])
async def ban_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if len(args) < 2:
        return await message.reply("Используй: /ban user_id причина")
    user_id, reason = int(args[0]), " ".join(args[1:])
    data = load_data()
    if user_id not in data["banned"]:
        data["banned"].append(user_id)
    log_action(f"Бан {user_id}. Причина: {reason}")
    save_data(data)
    await message.reply(f"🚫 Бан пользователя {user_id}.")

@dp.message_handler(commands=["unban"])
async def unban_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if not args:
        return await message.reply("Используй: /unban user_id")
    user_id = int(args[0])
    data = load_data()
    if user_id in data["banned"]:
        data["banned"].remove(user_id)
        log_action(f"Разбан {user_id}")
        save_data(data)
        await message.reply(f"✅ Разбан пользователя {user_id}.")
    else:
        await message.reply("Этот пользователь не в бане.")

@dp.message_handler(commands=["coin"])
async def coin_check(message: types.Message):
    args = message.get_args().split()
    user_id = int(args[0]) if args else message.from_user.id
    data = load_data()
    balance = data["coins"].get(str(user_id), 0)
    await message.reply(f"💰 Баланс пользователя {user_id}: {balance} eh-coin")

@dp.message_handler(commands=["addcoin"])
async def add_coin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if len(args) != 2:
        return await message.reply("Используй: /addcoin user_id amount")
    user_id, amount = int(args[0]), int(args[1])
    data = load_data()
    data["coins"][str(user_id)] = data["coins"].get(str(user_id), 0) + amount
    log_action(f"Выдано {amount} монет пользователю {user_id}")
    save_data(data)
    await message.reply(f"✅ Выдано {amount} eh-coin пользователю {user_id}.")

@dp.message_handler(commands=["treasury"])
async def treasury_check(message: types.Message):
    data = load_data()
    await message.reply(f"🏛 В казне: {data['treasury']} eh-coin")

@dp.message_handler(commands=["takefromtreasury"])
async def take_from_treasury(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args().split()
    if not args:
        return await message.reply("Используй: /takefromtreasury amount")
    amount = int(args[0])
    data = load_data()
    if user_id not in data["bankers"]:
        return await message.reply("⛔ Только банкиры могут брать из казны.")
    if amount > data["treasury"]:
        return await message.reply("Недостаточно средств в казне.")
    data["treasury"] -= amount
    data["coins"][str(user_id)] = data["coins"].get(str(user_id), 0) + amount
    log_action(f"Банкир {user_id} забрал {amount} из казны")
    save_data(data)
    await message.reply(f"✅ {amount} eh-coin выдано из казны.")

@dp.message_handler(commands=["addbanker"])
async def add_banker(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if not args:
        return await message.reply("Используй: /addbanker user_id")
    user_id = int(args[0])
    data = load_data()
    if user_id not in data["bankers"]:
        data["bankers"].append(user_id)
    log_action(f"Добавлен банкир {user_id}")
    save_data(data)
    await message.reply(f"✅ Пользователь {user_id} теперь банкир.")

@dp.message_handler(commands=["removebanker"])
async def remove_banker(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Нет доступа.")
    args = message.get_args().split()
    if not args:
        return await message.reply("Используй: /removebanker user_id")
    user_id = int(args[0])
    data = load_data()
    if user_id in data["bankers"]:
        data["bankers"].remove(user_id)
        log_action(f"Удалён банкир {user_id}")
        save_data(data)
    await message.reply(f"✅ Банкир {user_id} удалён.")

@dp.message_handler(commands=["stats"])
async def user_stats(message: types.Message):
    args = message.get_args().split()
    user_id = int(args[0]) if args else message.from_user.id
    data = load_data()
    balance = data["coins"].get(str(user_id), 0)
    warns = len(data["warns"].get(str(user_id), []))
    is_muted = str(user_id) in data["muted"]
    is_banned = user_id in data["banned"]
    await message.reply(f"📊 Статистика пользователя {user_id}:
💰 Баланс: {balance}
⚠️ Варнов: {warns}
🔇 Мут: {'да' if is_muted else 'нет'}
🚫 Бан: {'да' if is_banned else 'нет'}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dp.loop.create_task(auto_unmute())
    executor.start_polling(dp)
