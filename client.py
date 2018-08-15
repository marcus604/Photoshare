import sys, socket, threading, queue
import ssl
import photoshare
from photoshare import psUtil
import time
from argon2 import PasswordHasher
import logging
import os, errno
import cProfile
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

LOGINUSERNAME = 'andy'
LOGINPASSWORD = 'hi'

SESSION_TOKEN = ''

BUFFER_SIZE = 16384 #32768

pr = cProfile.Profile()

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
			handleClientDisconnect(sock)
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
		
	try:
		photoshare.send_msg(sslSock, msg)
	except (ConnectionError, BrokenPipe):
		print("WRONG")

	try:
		#blocks
		msg = photoshare.receiveMessages(sslSock)
		if msg.instruction == 99:
			logger.info("Rejected Credentials")
			return False
		elif msg.instruction == 0:
			global SESSION_TOKEN
			SESSION_TOKEN = msg.data			
			return True
		if msg == None:		#Needs to be handled
			print("no messages to be received")
	except ConnectionError:
		print('Connection to server closed')
		handleClientDisconnect(sock)
		
		
	
def handleClientDisconnect(sock):
	sock.close()
	photoshare.totalTime()
	pr.disable()
	pr.dump_stats('client.profile')
	os._exit(0)
	
def establishConnection():
	#Create and wraps socket for SSL
	#Verifies cert is matching
	#If credentials are wrong, prompts user to try again
	#Server should sever and refuse requests to avoid brute force
	#Need to make sure client handles being rejected ok
	#returns session token
	sock = socket.socket()
	sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
	""" sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1) """
	sslSock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv23, ca_certs=CA_CERT_PATH)	#SSLv23 supports 
	targetHost = TARGET_HOST
	targetPort = TARGET_PORT

	sslSock.connect((targetHost, int(targetPort)))

	cert = sslSock.getpeercert()
	#if not cert or ssl.match_hostname(cert, targetHost):
	#	raise Exception("Invalid host for cert")
	
	validLogin = loginToServer(sslSock)

	while not validLogin:
		print("Invalid Username/Password")
		if input("Try Again: y/n ") == 'y':
			global LOGINUSERNAME, LOGINPASSWORD
			LOGINUSERNAME = input("Enter Username: ")
			LOGINPASSWORD = input("Enter Password: ")
			establishConnection()
		else:
			handleClientDisconnect(sslSock)
	
	return sslSock, validLogin

def bytesToNumber(bytes):
    res = 0
    for i in range(4):
        res += bytes[i] << (i*8)
    return res

def bytestoMB(bytes):
	kb = bytes / 1024
	return ("{:.2f} MB".format((kb / 1024)))


#Creates and gets DB
#Need to see if sync is resuming
def initialSync(sock):
	
	f = openFile('Testing/clientDB.mov')			#Change this

	size = getSizeOfTransfer(sock)

	currentSize = 0
	
	modifier = 32

	while currentSize < size:
		
		data = receivePeice(sock, BUFFER_SIZE, currentSize, size)
		if data == 1:
			break			
		""" if currentSize == (BUFFER_SIZE * modifier):						#Testing
			modifier += 32
			photoshare.timerCheckpoint(bytestoMB(currentSize)) """
		
		f.write(data)
		currentSize += len(data)
		
	
	f.close()
	photoshare.timerCheckpoint("Initial Sync")

	numberOfPhotos = getSizeOfTransfer(sock)
	

	for count in range(numberOfPhotos):
		size = getSizeOfTransfer(sock)
		currentSize = 0
		while currentSize < size:
		
			data = receivePeice(sock, BUFFER_SIZE, currentSize, size)
			if data == 1:
				break			
			""" if currentSize == (BUFFER_SIZE * modifier):						#Testing
				modifier += 32
				photoshare.timerCheckpoint(bytestoMB(currentSize)) """
			
			f.write(data)
			currentSize += len(data)

	

	
	
	


def receivePeice(sock, BUFFER_SIZE, currentSize, size):
	data = sock.recv(BUFFER_SIZE)
	if not data:
		return 1
	if len(data) + currentSize > size:
		data = data[:size-currentSize]
	return data

def getSizeOfTransfer(sock):
	size = sock.recv(4)
	size = bytesToNumber(size)
	#print("Receiving file size of {}".format(bytestoMB(size)))
	return size

def openFile(filename):
	return open(filename, "wb")


if __name__ == '__main__':
	pr.enable()			#PROFILING
	

	photoshare.startTimer()
	#Am I configured to connect to a server?
	validLogin = False
	ps = psUtil(ENDIAN, VERSION)
	

	sock, token = establishConnection()
	

	data = SESSION_TOKEN  #Initial Handshake
	length = len(data)
	msg = ps.createMessage(1, length, data)

	#Move this to its own thread
	try:
		photoshare.send_msg(sock, msg)
	except ConnectionError as e:
		logger.info("Connection Error")
	
	initialSync(sock)
	
	#Loop indefinitely to receive messages from server
	while True:
		try:
			#blocks
			msgs = photoshare.receiveMessages(sock)
		except (EOFError, ConnectionError, ValueError):
			print('Connection to server closed')
			handleClientDisconnect(sock)
			break 
	
		
		#q = queue.Queue()
	#with lock:
	#	sendQueues[sslSock.fileno()] = q

	#sendThread = threading.Thread(target=handleClientSend, args=[sslSock, q], daemon=True)
	#sendThread.start()
	
	
	
	
		
	
	

	

	

	