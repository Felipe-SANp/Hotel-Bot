#Con Base de Datos (MySQL)
from telebot import types
from resources.conectDB import *
from resources.sources_bot import *
from resources.config import *

# Variable para el Mensaje de Bienvenida
msg_start = """
	<b>Welcome to Hot-Bot!</b>

	I'm your assistant to book rooms at <b>The Frailes Hotel</b>. Use the following options to interact with me:

	<b>🛎 Book Room</b>.
	Use the option to view a list of available rooms and make a reservation.

	<b>View my reservations 🗒</b>.
	Use the option to view the reservations you have made. You can also <b>cancel a reservation</b>.

	<b>☎️ View Hotel Contacts</b>
	Use the option to view the Hotel contacts.

	"""

# Comando de Inicio
@bot.message_handler(commands=['start'])
def command_start(message):
	user_data[message.chat.id] = {}
	user_data[message.chat.id]['state'] = 'start'
	bot.send_message(message.chat.id, msg_start, parse_mode='HTML') # Enviar Mensaje de Bienvenida

	# Verificamos si el usuario ya existe en la base de datos y si no cambia al estado SIGNUP
	cursor.execute(f"SELECT user_id, username FROM users WHERE user_id = {message.chat.id}")
	result = cursor.fetchone()
	db.commit()

	if not result:
		bot.send_message(message.chat.id, "What is your name?")
		user_data[message.chat.id]['state'] = 'SIGNUP'
	else:
		# Saludar
		user_id, username = result
		bot.send_message(message.chat.id, f"!Hi {username}!")
		show_options(message.chat.id)


# Manejador para capturar el nombre del usuario
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('state') == 'SIGNUP')
def handle_name(message):
	user_name = message.text
	user_id = message.chat.id
	
	# Guardar el nombre del usuario a la base de datos
	cursor.execute(f"INSERT INTO users (user_id, username) VALUES ({user_id}, '{user_name}')")
	db.commit()
	
	bot.send_message(user_id, f"!Thanks, {user_name}!") # Saludar con un mensaje personalizado
	show_options(user_id)

# Muestra las habitaciones disponibles y permite al usuario seleccionar una
@bot.callback_query_handler(func=lambda call: call.data == 'book_room')
def callback_book_room(call):
    user_id = call.message.chat.id
    user_data[user_id]['state'] = 'ROOM_SELECTION'

    # Consultar las habitaciones disponibles
    cursor.execute(
        """
        SELECT r.room_id, r.room_type, r.price, r.capacity, r.image_url FROM rooms r
        WHERE availability = 1 AND r.hotel_id = 1;
        """
    )
    rooms = cursor.fetchall()
    db.commit()

    if not rooms:
        bot.send_message(user_id, "Sorry! There are no rooms available at this time.")
        show_options(user_id)
        return  # Terminar la función si no hay habitaciones disponibles

    bot.send_message(user_id, "<b>The following rooms are available</b>", parse_mode='HTML')
    # Enviar cada habitación con su imagen, información y botón de selección
    for room in rooms:
        room_id, room_type, price, capacity, image_url = room
        room_info = f"<b>🏨 {room_type}</b> (Capacity: {capacity}) - <b>${price:.2f} 💵 per night 🌙</b>\n"
        
        # Llamar a la función que envía imagen, información y botón
        send_room_with_button(user_id, image_url, room_info, room_id)


# Manejador de Callback room_{room_id} para seleccionar la habitación
@bot.callback_query_handler(func=lambda call: call.data.startswith('room_'))
def handle_room_selection(call):
	room_id = int(call.data.split("_")[1])
	user_data[call.message.chat.id]['room_id'] = room_id
	user_data[call.message.chat.id]['state'] = 'CONFIRMATION'

	# Consultar la habitación seleccionada
	cursor.execute("SELECT room_type, price FROM rooms WHERE room_id = %s", (room_id,))
	room = cursor.fetchone()
	room_type, price = room

	# Crear un mensaje con la habitación seleccionada y botones para confirmar o cancelar
	response = f"<b>🟢 Please confirm your reservation 🟢</b>\n\n<b> Room</b>: {room_type}\n<b> Total price</b>: ${price:.2f}"
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("Confirm", callback_data="confirm"))
	markup.add(types.InlineKeyboardButton("Cancel", callback_data="cancel"))

	bot.send_message(call.message.chat.id, response, parse_mode='HTML', reply_markup=markup) # Mostrar el mensaje de confirmación


# Manejador de Callback confirm para confirmar la reservación
@bot.callback_query_handler(func=lambda call: call.data == 'confirm')
def handle_confirmation(call):
	user_id = call.from_user.id
	room_id = user_data[call.message.chat.id]['room_id']

	# Guardar la reservación en la base de datos
	cursor.execute(
		"INSERT INTO bookings (room_id, user_id, status) VALUES (%s, %s, 'confirmed')",
		(room_id, user_id)
	)
	db.commit()

	# Actualizar la disponibilidad de la habitación
	cursor.execute(
		"UPDATE rooms SET availability = 0 WHERE room_id = %s",
		(room_id,)
	)
	db.commit()

	# Crear un mensaje de confirmación con el número de reservación
	response = f"""
	<b>Reservation confirmed!</b> Your reservation number is #123{room_id}A. <b>
	We look forward to seeing you at the Hotel!</b>"
	"""
	bot.send_message(call.message.chat.id, response , parse_mode='HTML') # Mostrar mensaje de confirmación
	show_options(call.message.chat.id) # Mostrar las opciones de inicio


# Manejador de Callback cancel para cancelar el proceso de la reservación
@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def handle_cancellation(call):
	bot.send_message(call.message.chat.id, "Reservation <b>canceled.</b>", parse_mode='HTML') # Mostrar mensaje de cancelación
	show_options(call.message.chat.id) # Mostrar las opciones de inicio


# Manejador de Callback view_bookings para ver las reservaciones
@bot.callback_query_handler(func=lambda call: call.data == 'view_bookings')
def handl_view_bk(call):
	user_id = call.from_user.id
	user_data[call.message.chat.id]['state'] = 'SHOW_BOOKING'

	# consultar las reservaciones relacionadas al usuario
	cursor.execute(
		f"""
		SELECT r.room_type, r.price, r.capacity
		FROM bookings b JOIN rooms r ON b.room_id = r.room_id
    	WHERE b.user_id = {user_id};
		"""
	)
	bookings = cursor.fetchall()
	db.commit()

	if not bookings:
		bot.send_message(user_id, "<b>No reservations at this moment</b>", parse_mode='HTML')
		show_options(user_id)
		return # Terminar AQUI la función si no hay reservaciones

	# Crear un mensaje con las reservaciones
	response = "<b>Your bookings:</b>\n\n"
	for booking in bookings:
		room_type, price, capacity = booking
		response += f"<b>✅ {room_type}</b> (Capacity: {capacity}) - <b>${price:.2f}</b>\n"

	# opciones para cancelar o regresar
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("Cancel Reservation", callback_data="cancel_booking"))
	markup.add(types.InlineKeyboardButton("Back", callback_data="back"))

	bot.send_message(user_id, response, parse_mode='HTML', reply_markup=markup) # Mostrar el mensaje de reservaciones


# Manejador de Callback cancel_booking para visualizar las reservaciones y cancelar
@bot.callback_query_handler(func=lambda call: call.data == 'cancel_booking')
def handle_cancel_booking(call):
	user_data[call.message.chat.id]['state'] = 'CANCEL_BOOKING'
	user_id = call.from_user.id

	# Consultar las reservaciones relacionadas al usuario y mostrarlas
	cursor.execute(
		f"""
		SELECT b.booking_id, r.room_type, r.price
		FROM bookings b JOIN rooms r ON b.room_id = r.room_id
		WHERE b.user_id = {user_id};
		"""
	)
	bookings = cursor.fetchall()

	# Crear un mensaje con las reservaciones y un botón para cancelar
	response = "<b>Select the reservation you want to cancel:</b>\n\n"
	markup = types.InlineKeyboardMarkup()
	for booking in bookings:
		booking_id, room_type, price = booking
		response += f"<b>❗️ {room_type}</b> <b>${price:.2f}</b>\n"
		markup.add(types.InlineKeyboardButton(f"Cancel {room_type}", callback_data=f"cancel_{booking_id}"))
	
	bot.send_message(user_id, response, parse_mode='HTML', reply_markup=markup) # Mostrar las reservaciones y botón para cancelar


# Manejador de Callback cancel_{booking_id} para cancelar una reservación específica
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel(call):
	booking_id = int(call.data.split("_")[1]) # Obtener el id de la reservación
	user_id = call.from_user.id

	# Habilitar disponibilidad de la habitación a cancelar antes de borrar la reservación
	cursor.execute(
		f"""
		UPDATE rooms r JOIN bookings b ON r.room_id = b.room_id
		SET r.availability = 1
		WHERE b.user_id = {user_id} AND b.booking_id = {booking_id};
		"""
	)

	# Eliminar la reservación
	cursor.execute(f"DELETE FROM bookings b WHERE b.booking_id = %s", (booking_id,))
	cursor.fetchall()
	db.commit()

	bot.send_message(call.message.chat.id, "<b>Reservation canceled.</b>", parse_mode='HTML') # Mostrar mensaje de cancelación
	show_options(call.message.chat.id) # Mostrar las opciones de inicio


# Manejador de Callback back para regresar a las opciones >> show_options
@bot.callback_query_handler(func=lambda call: call.data == 'back')
def handle_back(call):
	show_options(call.message.chat.id)

# Manejador de Callback view_contact para ver los contactos del hotel
@bot.callback_query_handler(func=lambda call: call.data == 'view_contact')
def handle_contact(call):
	user_id = call.from_user.id
	user_data[call.message.chat.id]['state'] = 'SHOW_CONTACT'

	# Consultar los datos del hotel
	cursor.execute("SELECT name, address, phone, email, image_url FROM hotels WHERE hotel_id = 1")
	hotel = cursor.fetchone()
	db.commit()
	name, address, phone, email, image_url = hotel

	# Crear un mensaje con los datos del hotel
	response = f"""
			<b>Hotel "{name}"</b> 🏨

			<b>Address</b>: {address} 📍
			<b>Contact</b>: {phone} 📞
			<b>Email</b>: {email} 📧
			"""	
	bot.send_photo(user_id, image_url, caption=response, parse_mode='HTML')
	show_options(user_id)

# Iniciar el bot con las funciones de manejo de mensajes y callbacks
bot.polling()

# Cerrar base de Datos
db.close()