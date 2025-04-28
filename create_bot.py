from aiogram import Bot, Dispatcher
import config
from states import storage

bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(storage=storage)