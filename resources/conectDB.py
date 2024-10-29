import mysql.connector

# Conectarse a la base de datos
db = mysql.connector.connect(
	host='',
	user='',
	password='',
	database=''
)
cursor = db.cursor()