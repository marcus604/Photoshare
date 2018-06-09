import socket
import ssl
import logging


HOST = ''
PORT = 1428
VERSION = '01'
logging.basicConfig(filename='photoshare.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

#Create TCP socket, to receive connection
def createListenSocket(host, port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((host, port))
	sock.listen(100)
	return sock

#Wraps socket with protocol SSLv23. Supports TLS1.2-1.0
#Doesnt handle being port scanned
def sslWrap(sock):
	return ssl.wrap_socket(sock, server_side=True, certfile="server.crt", keyfile="server.key", ssl_version=ssl.PROTOCOL_SSLv23)
		
		


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


	print(message)
	return message

def receiveMessages(sock):
	""" Receive data and parse into appropiate container """
	endian = sock.read(1).decode('utf-8')
	version = float(sock.read(1).decode('utf-8') + "." + sock.read(1).decode('utf-8'))
	type = int(sock.read(2).decode('utf-8'))
	length = int(sock.read(2).decode('utf-8'))
	recvd = sock.read(length).decode('utf-8')		#Catches value error above in case this is empty, is this the best way to do it?

	receivedMessage = psMessage(endian, version, type, length, recvd)
	
	receivedMessage.print()
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
	sock.sendall(message)

class psUtil:
	def __init__(self, endian, version):
		self.endian = endian			#String
		self.version = version			#Float

	def createMessage(self, instruction, length, data):
		newMsg = psMessage(self.endian, self.version, instruction, length, data)	
		newMsg.print()
		msg = newMsg.getByteString()
		return msg

	

	#Endian			1 Byte; 0 = Little, 1 = Big
	#Version		8 Bytes;	0-255
	#Instruction	4 Bytes; 0 = Handshake, 1 = Pull, 2 = Push, 99 = Error
	#Length			8 Bytes
class psMessage:
	def __init__(self, endian, version, instruction, length, data):
		#Create object from either strings, or byte code. 
		#Essentially overloading the constructor
		self.endian = endian
		self.version = version
		self.instruction = instruction
		self.data = data
		self.length = length
		
		'''
		try:
			self.endian = endian.encode('utf-8')
			self.version = version.encode('utf-8')
			self.instruction = instruction.encode('utf-8')
			self.data = data.encode('utf-8')
			self.length = str(length).encode('utf-8')
		except AttributeError as e:		
			self.endian = endian
			self.version = version
			self.instruction = instruction
			self.data = data
			self.length = length
			'''
		

	def fromString(self, endian, version, instruction, data):
		self.endian = endian.encode('utf-8')
		self.version = version.encode('utf-8')
		self.instruction = instruction.encode('utf-8')
		self.data = data.encode('utf-8')
		self.length = str(len(self.data)).encode('utf-8')

	def fromByteString(self, endian, version, instruction, length, data):
		self.endian = endian
		self.version = version
		self.instruction = instruction
		self.data = data
		self.length = length

	def print(self):
		print("+================================================+")
		print("| 	Endian		|	{}		|".format(self.formatEndian()))
		print("| 	Version		|	{}		|".format(self.formatVersion()))
		print("| 	Instruction	|	{}	|".format(self.formatInstruction()))
		print("| 	Length		|	{} Bytes	|".format(self.length))
		print("+===========================================================================================================+")
		print("| 	Data		|	{}			".format(self.data))
		print("+===========================================================================================================+")


	def getByteString(self):
		version = self.formatVersion()
		instruction = self.padZero(self.instruction)
		length = self.padZero(self.length)
		
		message = bytes()
		message += self.endian.encode('utf-8')			#Endian Type
		message += version.encode('utf-8')				#Version
		message += instruction.encode('utf-8')			#Type of Message (New Client, Request Update, Push update, Error)
		message += length.encode('utf-8')				#Length of message
		message += self.data.encode('utf-8')			#Message
		return message

	def formatInstruction(self):
		#00 Handshake
		#01 Request Update
		#02 Push Update
		i = self.instruction
		
		if i == 0:
			return "Handshake"
		elif i == 1:
			return "Pull"
		elif i == 2:
			return "Push"
		elif i == 99:
			return "Error"

	def formatData(self):
		strVal = str(self.data)
		return strVal
	
	def formatLength(self):
		strVal = str(self.length)
		return strVal[2] + strVal[3]

	def formatVersion(self):
		strVal = str(self.version)
		return strVal[0] + strVal[2]

	def formatEndian(self):
		if self.endian == b'l':
			return "Little"
		else:	# b'b'
			return "Big"

	@staticmethod
	def padZero(data):
		if data < 10:
			return f'{data:02}'
		return str(data)
