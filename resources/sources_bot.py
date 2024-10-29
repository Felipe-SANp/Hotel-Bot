from telebot import types
from resources.config import bot, user_data

def show_options(chat_id):
	"""Muestra las opciones principales, utilizada en varios metodos para regresar a las opciones principales."""
	user_data[chat_id]['state'] = 'VIEW_OPTIONS'
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton('🛎 Book Room', callback_data='book_room'))
	markup.add(types.InlineKeyboardButton('View my reservations 🗒', callback_data='view_bookings'))
	markup.add(types.InlineKeyboardButton('☎️ View Hotel Contacts', callback_data='view_contact'))
	bot.send_message(chat_id, "What would you like to do? 🤔", parse_mode='HTML', reply_markup=markup)


def send_room_with_button(user_id, image_url, room_info, room_id):
    """Envía una imagen de la habitación, su información, y un botón de selección al usuario."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Select this room", callback_data=f'room_{room_id}'))
    bot.send_photo(user_id, image_url, caption=room_info, parse_mode='HTML', reply_markup=markup)