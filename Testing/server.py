from photoshare import psMessage
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


VERSION = photoshare.VERSION
HOST = ''
PORT = 1428
sendQueues = {}
lock = threading.Lock()
userName = 'Marcus'
passwd = 'hi'

#logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename='photoshare.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)



def NoUserFoundError(Exception):
	pass


def handleClientConnect(sock, addr, sqlConnection):
	""" Receive messages from client and broadcast them to
	other clients until client disconnects """
	rest = bytes()
	while True:
		try:
			msgs = photoshare.receiveMessages(sock)
		except (EOFError, ConnectionError):
			handle_disconnect(sock, addr)
			break
		if msgs.formatInstruction() == 'Handshake':		#00
			if not verifyUser(msgs.data, sqlConnection):
				handle_disconnect(sock, addr)
				break
			#Valid User
		elif msgs.formatInstruction() == 'Pull':		#01
			print("Pull")
		elif msgs.formatInstruction() == 'Push':		#02
			print("push")
		

#NEED TO SCRUB SQL
def verifyUser(data, sqlConnection):
	#Parse Username and password from given data
	#Connect to database and 
	str = data.decode('utf-8')
	parts = str.split(':', maxsplit=1)
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
	except pymysql.err.DatabaseError as e:
		print("sql error in verifyUser")
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
			for row in result:
				print("found a row")
			cursor.close ()
	except BaseException as e:
		print("something went wrong")

#Will need to catch this
def createDBandTables(sqlConnection):
	executeSQL(sqlConnection, 'CREATE DATABASE photoshare COLLATE utf8_general_ci;')
	executeSQL(sqlConnection, 'CREATE TABLE `photoshare`.`users` ( `UserName` VARCHAR(255) NOT NULL , `Password` VARCHAR(255) NOT NULL , `Salt` VARCHAR(255) NOT NULL , `LastSignedIn` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP , PRIMARY KEY (`UserName`(255)));')
	executeSQL(sqlConnection, 'CREATE TABLE `photoshare`.`photos` ( `md5Hash` VARCHAR(255) NOT NULL , `Make` VARCHAR(255) , `Model` VARCHAR(255) , `LensModel` VARCHAR(255) , `Flash` VARCHAR(255) , `DateTime` VARCHAR(255) , `ISO` VARCHAR(255) , `Aperture` VARCHAR(255) , `FocalLength` VARCHAR(255) , `Width` VARCHAR(255) , `Height` VARCHAR(255) , `ExposureTime` VARCHAR(255) , `Sharpness` VARCHAR(255) , `Type` VARCHAR(255) , `Dir` VARCHAR(255) NOT NULL , PRIMARY KEY (`md5Hash`(255)));')

#Need to check for SQL injection
def createNewUser(sqlConnection):
	ph = PasswordHasher()
	print("Create a New User:")
	userName = input("Name: ")
	passwordMatch = False
	password = None
	while not passwordMatch:
		password = input("Password: ")
		passwordVerify = input("Enter Password Again: ")
		if password == passwordVerify:
			passwordMatch = True
		else:
			print("Passwords Do Not Match")
	salt = secrets.token_hex(32)
	hash = ph.hash(password + salt)
	try:
		with sqlConnection.cursor() as cursor:
			sql = 'INSERT INTO `photoshare`.`users` (`UserName`, `Password`, `Salt`) VALUES (%s, %s, %s)'
			cursor.execute(sql, (userName, hash, salt,))
			logger.info('New user {0}'.format(userName))
	except pymysql.err.IntegrityError:
		print("User {0} already exists".format(userName))
		logger.debug("Rejected DuplicateUser {0}".format(userName))
		createNewUser(sqlConnection)
	except pymysql.err as e:
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
			sqlConnection = pymysql.connect(host='localhost', user='root', password='Idagl00w',	db='photoshare', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			logger.info('Connected to database')
			return sqlConnection
		elif (type == 'Setup'):
			sqlConnection = pymysql.connect(host='localhost', user='root', password='Idagl00w',	charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
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
		else:
			closeApp()


if __name__ == '__main__':
	logger.info('Starting PhotoShare')
	#Do I have an internet connection?
	
	sqlConnection = handleDatabaseConnect("Connect")
	#Start import process
	#createNewUser(sqlConnection)

	listenSock = photoshare.createListenSocket(HOST, PORT)
	addr = listenSock.getsockname()
	print('Listening on {}'.format(addr))
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
			
		

		
	
	
	
