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
	""" Receive data and break into complete messages on null byte
	delimiter. Block until at least one message received, then
	return received messages """
	bigOrLittleEndian = sock.read(1)
	version = sock.read(2)
	type = sock.read(2)
	length = sock.read(2)
	recvd = sock.read(int(length))			#Catches value error above in case this is empty, is this the best way to do it?

	receivedMessage = psMessage(bigOrLittleEndian, version, type, length, recvd)
	
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


	#Endian			1 Bit; 0 = Little, 1 = Big
	#Version		8 Bits;	0-255
	#Instruction	4 Bits; 0-15; 0 = Handshake, 1 = Pull, 2 = Push
	#Length			8 Bits
class psMessage:
	def __init__(self, endian, version, instruction, length, data):
		#Create object from either strings, or byte code. 
		#Essentially overloading the constructor
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
		print("Endian: {}".format(self.formatEndian()))
		print("Version: {}".format(self.formatVersion()))
		print("Instruction: {}".format(self.formatInstruction()))
		print("Length: {} Bytes".format(self.formatLength()))
		print("Data: {}".format(self.data))


	def getByteString(self):
		message = bytes()
		message += self.endian			#Endian Type
		message += self.version			#Version
		message += self.instruction		#Type of Message (New Client, Request Update, Push update)
		message += self.length		#Length of message
		message += self.data			#Message
		
		print(message)
		return message

	def formatInstruction(self):
		#00 Handshake
		#01 Request Update
		#02 Push Update
		i = str(self.instruction)
		i = i[2] + i[3]
		if i == '00':
			return "Handshake"
		elif i == '01':
			return "Pull"
		elif i == '02':
			return "Push"

	
	def formatLength(self):
		strVal = str(self.length)
		return strVal[2] + strVal[3]

	def formatVersion(self):
		strVal = str(self.version)
		return strVal[2] + '.' + strVal[3]

	def formatEndian(self):
		if self.endian == b'l':
			return "little"
		else:	# b'b'
			return "big"
