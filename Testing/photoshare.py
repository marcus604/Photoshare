import socket
import ssl


HOST = ''
PORT = 1428
VERSION = 0.1

#Create TCP socket, to receive connection
def createListenSocket(host, port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((host, port))
	sock.listen(100)
	return sock

#Wraps socket with protocol SSLv23. Supports TLS1.2-1.0
def sslWrap(sock):
	return ssl.wrap_socket(sock, server_side=True, certfile="server.crt", keyfile="server.key", ssl_version=ssl.PROTOCOL_SSLv23)

def parse_recvd_data(data):
	 """ Break up raw received data into messages, delimited
	 by null byte """
	 parts = data.split(b'\0')
	 msgs = parts[:-1]
	 rest = parts[-1]
	 return (msgs, rest)


 #Protocol
 #2 Bytes for Big Endian or Little Endian
 #1 Byte for Version
def prepareMessage(msg, type):
	message = bytes()
	message += b'll'		#Little Endian
	message += b'01'		#Version
	message += b'00'		#Type of Message (New Client, Request Update, Push update)
	message += b'64'		#Length of message
	message += b'FFFF FFF'	#Message

	print(message)
	return message

def receiveMessages(sock, data=bytes()):
	""" Receive data and break into complete messages on null byte
	delimiter. Block until at least one message received, then
	return received messages """
	msgs = []
	while not msgs:		#Messages not empty
		bigOrLittleEndian = sock.read(2)
		version = sock.read(2)
		type = sock.read(2)
		length = sock.read(2)
		
		recvd = sock.read(int(length))
		if not recvd:
			raise ConnectionError()
		data = data + recvd
		(msgs, rest) = parse_recvd_data(data)
	msgs = [msg.decode('utf-8') for msg in msgs]
	return (msgs, rest)

def prep_msg(msg):
	""" Prepare a string to be sent as a message """
	msg = str(msg)
	msg += '\0'
	return msg.encode('utf-8')

def send_msg(sock, msg):
	""" Send a string over a socket, preparing it first """
	data = prepareMessage(msg)
	#data = prep_msg(msg)
	sock.sendall(data)