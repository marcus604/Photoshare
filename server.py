from photoshare import psMessage
from photoshare import psUtil
import photoshare
import ssl
import threading, queue
from argon2 import PasswordHasher
import argon2
import pymysql
import os, errno
import secrets
import time
import logging

ENDIAN = 'b'
VERSION = 0.1
ps = ''
HOST = ''
PORT = 1428
sendQueues = {}
lock = threading.Lock()
userName = 'Marcus'
passwd = 'hi'
TOKEN_SIZE = 8
SQL_USERNAME = 'root'
SQL_PASSWORD = 'thisIsMySQLPassword'


#logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename='photoshare.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)



def NoUserFoundError(Exception):
	pass


def handleClientConnect(sock, addr, sqlConnection):
	""" Client Session """
	rest = bytes()
	clientIP = addr[0]
	token = ''
	while True:
		try:
			msg = photoshare.receiveMessages(sock)
		except (EOFError, ConnectionError, ValueError):
			logger.info("Connection Error")
			handle_disconnect(sock, addr)
			break
		if msg.instruction == 0:		#Handshake
			if not verifyUser(msg.data, sqlConnection):		#Failed Login
				data = "Invalid Username/Password"
				length = len(data)
				msg = ps.createMessage(99, length, data)	
				broadcast_msg(msg)				
				handle_disconnect(sock, addr)
				break
			#Valid User
			#Generate Token to send back to user
			token = secrets.token_hex(TOKEN_SIZE)
			tokenLength = len(token)
			msg = ps.createMessage(0, tokenLength, token)
			broadcast_msg(msg)
			continue
		
		else:	#If its not trying to connect it must already have a valid connection
			if addr[0] != clientIP and msg.data[:(TOKEN_SIZE * 2)] != token:	#Grabs the token stored at the begenning of the data
				logger.info("Unauthorized Connection")
				handle_disconnect(sock, addr)
	
			
		if msg.instruction == 1:		#01
			print("first ask?")
			print("Pull")
		elif msg.instruction == 2:		#02
			print("push")

def handle_client_send(sock, q, addr):
	""" Monitor queue for new messages, send them to client as they arrive """
	while True:
		msg = q.get()
		if msg == None: break
		try:
			photoshare.send_msg(sock, msg)
		except (ConnectionError, BrokenPipe):
			handle_disconnect(sock, addr)
			break

""" def handleSessions():
	#Monitor  """

#NEED TO SCRUB SQL
def verifyUser(data, sqlConnection):
	#Parse Username and password from given data
	#Connect to database and 
	parts = data.split(':', maxsplit=1)
	userName = parts[0]
	password = parts[1]
	#Connect to DB and find given user
	try:
		with sqlConnection.cursor() as cursor:
			sql = "SELECT `Password`, `Salt` FROM `photoshare`.`users` WHERE `UserName` = '{0}'".format(userName)
			cursor.execute(sql)
			if cursor.rowcount == 0:	#No user found with that name	
				raise argon2.exceptions.VerifyMismatchError
			result = cursor._result.rows[0]
			sqlpass = result[0]
			salt = result[1]
			ph = PasswordHasher()
			ph.verify(sqlpass, password + salt)		#Throws verifyMismatchError
			logger.info("User {0} connected".format(userName))
			cursor.close ()
			return True
	except argon2.exceptions.VerifyMismatchError:
		#Toggle for logging passwords, this would only be incorrect passwords
		logger.info('Rejected Credentials {0} {1}'.format(userName, password))
	except pymysql.err.ProgrammingError as e:
		logger.error('SQL Table doesnt exist')
	except pymysql.err.DatabaseError as e:
		logger.error('SQL Error')
	finally:
		cursor.close ()


def scrubSQL(toScrub):
	#scrub text of any invalid characters to prevent SQL injection attacks
	print(toScrub)


def broadcast_msg(msg):
	""" Add message to each connected client's send queue """
	with lock:
		for q in sendQueues.values():
			q.put(msg)




def handle_disconnect(sock, addr):
	""" Ensure queue is cleaned up and socket closed when a client
	disconnects """
	fd = sock.fileno()
	with lock:
		# Get send queue for this client
		q = sendQueues.get(fd, None)
	# If we find a queue then this disconnect has not yet
	# been handled
	if q:
		q.put(None)
		del sendQueues[fd]
		addr = sock.getpeername()
		print('Client {} disconnected'.format(addr))
		logger.info('Client {} disconnected'.format(addr))
		sock.close()


def executeSQL(sqlConnection, sql):
	try:

		with sqlConnection.cursor() as cursor:
            # Create a new record
			cursor.execute(sql)

            # connection is not autocommit by default. So you must commit to save
            # your changes.
			sqlConnection.commit()
			result = cursor.fetchall()
			cursor.close ()
			if result:
				return result
	except BaseException as e:
		print("something went wrong")

#Will need to catch this
def createDBandTables(sqlConnection):
	executeSQL(sqlConnection, 'CREATE DATABASE photoshare COLLATE utf8_general_ci;')
	executeSQL(sqlConnection, 'CREATE TABLE `photoshare`.`users` ( `UserName` VARCHAR(255) NOT NULL , `Password` VARCHAR(255) NOT NULL , `Salt` VARCHAR(255) NOT NULL , `LastSignedIn` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP , PRIMARY KEY (`UserName`(255)));')
	executeSQL(sqlConnection, 'CREATE TABLE `photoshare`.`photos` ( `md5Hash` VARCHAR(255) NOT NULL , `Make` VARCHAR(255) , `Model` VARCHAR(255) , `LensModel` VARCHAR(255) , `Flash` VARCHAR(255) , `DateTime` VARCHAR(255) , `ISO` VARCHAR(255) , `Aperture` VARCHAR(255) , `FocalLength` VARCHAR(255) , `Width` VARCHAR(255) , `Height` VARCHAR(255) , `ExposureTime` VARCHAR(255) , `Sharpness` VARCHAR(255) , `Type` VARCHAR(255) , `Dir` VARCHAR(255) NOT NULL , PRIMARY KEY (`md5Hash`(255)));')

#Need to check for SQL injection
#Need to change print statements to log
def createNewUser(sqlConnection):
	ph = PasswordHasher()
	userNameValid = False
	passwordValid = False

	while not userNameValid:
		print("Create a New User:")
		userName = input("Name: ")
		if len(userName) > 40:
			print("Username cannot be longer than 40 characters")
		else:
			if ":" not in userName:
				userNameValid = True
			else:
				print("Username cannot contain the character ':'")
	
	while not passwordValid:
		password = input("Password: ")
		if len(password) > 64:
			print("Password cannot be longer than 64 characters")
		else:
			passwordVerify = input("Enter Password Again: ")
			if password == passwordVerify:
				passwordValid = True
			else:
				print("Passwords Do Not Match")
	salt = secrets.token_hex(32)
	hash = ph.hash(password + salt)
	try:
		with sqlConnection.cursor() as cursor:
			sql = 'INSERT INTO `photoshare`.`users` (`UserName`, `Password`, `Salt`) VALUES (%s, %s, %s);'
			cursor.execute(sql, (userName, hash, salt,))
			sqlConnection.commit()
			logger.info('New user {0}'.format(userName))
	except pymysql.err.IntegrityError:
		print("User {0} already exists".format(userName))
		logger.debug("Rejected DuplicateUser {0}".format(userName))
		createNewUser(sqlConnection)
	except pymysql.err.DataError as e:
		logger.error('Failed to create new user {0}'.format(userName))
	

	
def closeApp():
	logger.info("Exiting Photoshare")
	os._exit(0)

#After initial setup, should consistently connect with no errors
#Tries to connect to database and given table
#If unsuccesful will attempt to create database and table structure
def handleDatabaseConnect(type):
	#Valid and connected DB
	try:
		if (type == 'Connect'):
			sqlConnection = pymysql.connect(host='localhost', user=SQL_USERNAME, password=SQL_PASSWORD,	db='photoshare', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			#Check if both tables exist
			tables = executeSQL(sqlConnection, 'show tables')
			if (not tables) or (len(tables) != 2):			#Missing one or both tables
				logger.error('SQL Table doesnt exist')
				raise pymysql.err.InternalError
			logger.info('Connected to database')
			return sqlConnection
		elif (type == 'Setup'):
			sqlConnection = pymysql.connect(host='localhost', user=SQL_USERNAME, password=SQL_PASSWORD,	charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			logger.info("Creating Database")
			return sqlConnection
	
	#Need to handle when no database named photos
	except pymysql.err.OperationalError as e: #Couldnt connect to DB at host
		if (e.args[0] == 1045):
			logger.error("Rejected Credentials SQL")
		elif (e.args[0] == 2003):
			logger.error("Rejected SQL Host")
		closeApp()
	except pymysql.err.InternalError as e:	#No DB found; Create Database and two tables
		if (e.args[0] == 1049):
			sqlConnection = handleDatabaseConnect('Setup')
			createDBandTables(sqlConnection)
			createNewUser(sqlConnection)
			return sqlConnection
		else:
			closeApp()


if __name__ == '__main__':
	logger.info('Starting PhotoShare')
	#Do I have an internet connection?
	
	sqlConnection = handleDatabaseConnect("Connect")
	#Start import process
	#createNewUser(sqlConnection)

	ps = psUtil(ENDIAN, VERSION)
	""" data = "99ba68146beb85547d2344744020d833272a800ca66d0c7098cdbd76ccdb1bcf"
	length = len(data)
	msg = ps.createMessage(0, length, data)  """

	try:
		listenSock = photoshare.createListenSocket(HOST, PORT)
	except OSError as e:
		if e.args[0] == 98:
			logger.error("Address already in use")
			closeApp()
	addr = listenSock.getsockname()
	print('Listening on {}'.format(addr))
	logger.info('Listening on {}'.format(addr))
	while True:
		clientSock, addr = listenSock.accept()
		try:
			clientSock = photoshare.sslWrap(clientSock)
			q = queue.Queue()
			with lock:
				sendQueues[clientSock.fileno()] = q
			recv_thread = threading.Thread(target=handleClientConnect,args=[clientSock, addr, sqlConnection],daemon=True)
			send_thread = threading.Thread(target=handle_client_send,args=[clientSock, q,addr],daemon=True)
			recv_thread.start()
			send_thread.start()
			print('Connection from {}'.format(addr))
		except ssl.SSLEOFError as e:
			logger.info('Rejected NoSSL {0} {1}'.format(addr[0], addr[1]))
			
		

		
	
	
	
