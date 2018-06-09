import sys, socket, threading, queue
import ssl
import photoshare
from photoshare import psUtil
import time
from argon2 import PasswordHasher
import logging
import os, errno

from pprint import pprint

ENDIAN = 'b'
VERSION = 0.1
ps = ''
TARGET_HOST = sys.argv[-1] if len(sys.argv) > 1 else 'localhost'
TARGET_PORT = photoshare.PORT
sendQueues = {}
lock = threading.Lock()
CA_CERT_PATH = 'server.crt'
POLLING_TIME = 60

logging.basicConfig(filename='client.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

LOGINUSERNAME = 'anddddy'
LOGINPASSWORD = 'hi'

def handleClientSend(sock, q):
	""" Monitor queue for new messages, send them to client as they arrive """
	while True:
		msg = q.get()
		newMessage = photoshare.psMessage(ENDIAN, VERSION, '00', '00', '00')
		print(newMessage)
		msg = newMessage.getBytes()
		
		
		if msg == None: 
			print("no messages to send")
			break
		try:
			photoshare.send_msg(sock, msg)
		except (ConnectionError, BrokenPipe):
			handle_disconnect(sock, addr)
			break

def handleClientReceive(sock):
	#Loop indefinitely to receive messages from server
	while True:
		try:
			#blocks
			msgs = photoshare.receiveMessages(sock)
			if msgs == None:
				print("no messages to be received")
				break
			for msg in msgs:
				print(msg)
		except ConnectionError:
			print('Connection to server closed')
			sock.close()
			break

def loginToServer(sslSock):
	#Get Username and password
	#Username cannot have ':' character
	
	
	
	userName = LOGINUSERNAME
	userNameLen = len(userName)
	if userNameLen > 40:
		logger.info("Rejected Username too long")
	
	password = LOGINPASSWORD
	passwordLen = len(password)
	if passwordLen > 64:
		logger.info("Rejected password too long")

	data = userName + ':' + password
	length = len(data)

	msg = ps.createMessage(0, length, data)
	

	#newMsg = photoshare.psMessage(ENDIAN, VERSION, '00', length, data)

	

	
	try:
		photoshare.send_msg(sslSock, msg)
	except (ConnectionError, BrokenPipe):
		print("WRONG")

	try:
		#blocks
		msg = photoshare.receiveMessages(sslSock)
		if msg.instruction == 99:
			logger.info("Rejected Credentials yeah")
			return False
		else:
			return True
		if msg == None:
			print("no messages to be received")
		for msg in msg:
			print(msg)
	except ConnectionError:
		print('Connection to server closed')
		sock.close()
		
	
def handleClientDisconnect(sock):
	sock.close()
	os._exit(0)
	
def establishConnection():
	sock = socket.socket()
	sslSock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv23, ca_certs=CA_CERT_PATH)	#SSLv23 supports 
	targetHost = TARGET_HOST
	targetPort = TARGET_PORT

	sslSock.connect((targetHost, int(targetPort)))

	cert = sslSock.getpeercert()
	#if not cert or ssl.match_hostname(cert, targetHost):
	#	raise Exception("Invalid host for cert")
	
	validToken = loginToServer(sslSock)

	while not validToken:
		print("Invalid Username/Password")
		if input("Try Again: y/n ") == 'y':
			LOGINUSERNAME = input("Enter Username: ")
			LOGINPASSWORD = input("Enter Password: ")
			establishConnection()
		else:
			handleClientDisconnect(sslSock)
	
	return sslSock, validToken

if __name__ == '__main__':
	#Am I configured to connect to a server?
	validToken = False
	ps = psUtil(ENDIAN, VERSION)
	

	sock, token = establishConnection()
	
	#newMessage = photoshare.psMessage(ENDIAN, VERSION, '00', 20, data)
	#msg = newMessage.getBytes()

	
		
	#Loop indefinitely to receive messages from server
	while True:
		try:
			#blocks
			msgs = photoshare.receiveMessages(sslSock)
			if msgs == None:
				print("no messages to be received")
			for msg in msgs:
				print(msg)
		except ConnectionError:
			print('Connection to server closed')
			sock.close()
			break
	
		
		#q = queue.Queue()
	#with lock:
	#	sendQueues[sslSock.fileno()] = q

	#sendThread = threading.Thread(target=handleClientSend, args=[sslSock, q], daemon=True)
	#sendThread.start()
	
	
	
	
		
	
	

	

	

	