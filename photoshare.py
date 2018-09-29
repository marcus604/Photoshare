import socket
import ssl
import logging
import time
from PSMessage import PSMessage
from pathlib import Path

HOST = ''
PORT = 1428
VERSION = 1
logging.basicConfig(filename='photoshare.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

START_TIME = ''		#Testing speed 
TIME_ELAPSED = 0

def startTimer():
	global START_TIME 
	START_TIME = time.time()

def timerCheckpoint(checkpointName):
	global START_TIME
	global TIME_ELAPSED
	sinceCheckpoint = time.time() - START_TIME
	START_TIME = time.time()
	TIME_ELAPSED = sinceCheckpoint + TIME_ELAPSED
	print ('{0} took {1:.4f} second !'.format(checkpointName, sinceCheckpoint))
	return sinceCheckpoint

def totalTime():
	global START_TIME
	global TIME_ELAPSED
	TIME_ELAPSED = (time.time() - START_TIME) + TIME_ELAPSED
	print ('Total Time: {0:.4f}'.format(TIME_ELAPSED))

#Create TCP socket, to receive connection
def createListenSocket(host, port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
	sock.bind((host, port))
	sock.listen(100)
	return sock

#Wraps socket with protocol SSLv23. Supports TLS1.2-1.0
#Doesnt handle being port scanned
def sslWrap(sock):
	context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
	context.verify_mode = ssl.CERT_OPTIONAL
	context.load_cert_chain(certfile="server.crt", keyfile="server.key")
	#Useful when I want to see unecrypted on the wire traffic
	#Cant decrypt otherwise as it uses diffie helman and encrypts session data with a different key
	context.set_ciphers('RSA')		
	return context.wrap_socket(sock, server_side=True)

	#return context.wrap_socket(sock, server_side=True, certfile="server.crt", keyfile="server.key", ssl_version=ssl.PROTOCOL_SSLv23)

	
		
		


 #Protocol
 #2 Bytes for Big Endian or Little Endian
 #1 Byte for Version
def prepareMessage(header, message):
	message = bytes()
	message += b'l'			#Little Endian
	message += b'01'		#Version
	message += b'00'		#Type of Message (New Client, Request Update, Push update)
	message += b'64'		#Length of message
	message += b'FFFF FFF'	#Message


	#print(message)
	return message

def receiveMessage(sock):
	""" Receive data and parse into appropiate container """
	endian = sock.read(1).decode('utf-8')
	version = int(sock.read(2).decode('utf-8'))
	instruction = int(sock.read(2).decode('utf-8'))
	length = int(sock.read(2).decode('utf-8'))
	data = sock.read(length).decode('utf-8')		#Catches value error above in case this is empty, is this the best way to do it?

	receivedMessage = PSMessage(endian, version, instruction, length, data)
	
	#receivedMessage.print()
	if not receivedMessage:
		raise ConnectionError()
	return receivedMessage

def prep_msg(msg):
	""" Prepare a string to be sent as a message """
	msg = str(msg)
	msg += '\0'
	return msg.encode('utf-8')

def send_msg(sock, message):
	""" Send a string over a socket, preparing it first """
	#data = prepareMessage(header, message)
	#data = prep_msg(msg)
	try: 
		sock.sendall(message)
	except:
		raise ConnectionError

def getFileHandles(dirToScan):
	rootDir = Path(dirToScan)
	fileList = [f for f in rootDir.glob('**/*') if f.is_file()]

	if not fileList:
		return False
	return fileList

class psUtil:
	def __init__(self, endian, version):
		self.endian = endian			#String
		self.version = version			#Float

	def createMessage(self, instruction, length, data):
		newMsg = PSMessage(self.endian, self.version, instruction, length, data)	
		#newMsg.print()
		msg = newMsg.getByteString()
		return msg

	


