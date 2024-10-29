import os
from dotenv import load_dotenv
import telebot

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Crear un objeto bot
TOKEN = os.getenv('MYTOKEN')
if TOKEN is None:
    raise ValueError("El token no se encontró en las variables de entorno")

bot = telebot.TeleBot(TOKEN)

# Manejador de Estados
user_data = {}