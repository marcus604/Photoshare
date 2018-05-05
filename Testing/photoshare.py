import socket
import ssl


HOST = ''
PORT = 1428
VERSION = '01'

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
	recvd = sock.read(int(length))
	message = psMessage(bigOrLittleEndian, version, type, length, recvd)
	
	message.print()
	if not message:
		raise ConnectionError()
	return message

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

class psMessage:
	def __init__(self, endian, version, instruction, length, data):
		self.endian = endian
		self.version = version
		self.instruction = instruction
		self.length = length
		self.data = data

	def print(self):
		print("Endian: {}".format(self.formatEndian()))
		print("Version: {}".format(self.formatVersion()))
		print("Instruction: {}".format(self.formatInstruction()))
		print("Length: {} Bytes".format(self.formatLength()))
		print("Data: {}".format(self.data))

	
	def getBytes(self):
		message = bytes()
		message += str.encode(self.endian)			#Endian Type
		message += str.encode(self.version)			#Version
		message += str.encode(self.instruction)		#Type of Message (New Client, Request Update, Push update)
		message += str.encode(str(self.length))			#Length of message
		message += self.data						#Message
		
		print(message)
		return message

	def formatInstruction(self):
		#00 Handshake
		#01 Request Update
		#02 Push Update
		if self.instruction == b'00':
			return "Handshake"
		elif self.instruction == b'01':
			return "Pull"
		elif self.instruction == b'02':
			return "Push"

	
	def formatLength(self):
		strVal = str(self.length)
		return strVal[2] + '.' + strVal[3]

	def formatVersion(self):
		strVal = str(self.version)
		return strVal[2] + '.' + strVal[3]

	def formatEndian(self):
		if self.endian == b'l':
			return "Little"
		else:	# b'b'
			return "Big"
