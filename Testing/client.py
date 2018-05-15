import sys, socket, threading, queue
import ssl
import photoshare
import time
from argon2 import PasswordHasher

from pprint import pprint

ENDIAN = 'b'
VERSION = photoshare.VERSION
TARGET_HOST = sys.argv[-1] if len(sys.argv) > 1 else '10.10.10.6'
TARGET_PORT = photoshare.PORT
sendQueues = {}
lock = threading.Lock()
CA_CERT_PATH = 'server.crt'
POLLING_TIME = 60

def handleClientSend(sock, q):
	""" Monitor queue for new messages, send them to client as they arrive """
	while True:
		msg = q.get()
		newMessage = photoshare.psMessage(ENDIAN, VERSION, '00', '00', '00')
		msg = newMessage.getBytes()
		print(newMessageByteString)
		
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
	#Hashes
	ph = PasswordHasher()
	
	userName = 'marcus'
	
	password = 'hi'
	#password = ph.hash(password)
	#print(password)

	data = userName + ':' + password
	length = len(data)
	if length < 10:
		length = (f'{length:02}')

	newMsg = photoshare.psMessage(ENDIAN, VERSION, '00', length, data)
	msg = newMsg.getByteString()

	
	try:
		photoshare.send_msg(sslSock, msg)
	except (ConnectionError, BrokenPipe):
		print("WRONG")

	


if __name__ == '__main__':
	#Am I configured to connect to a server?

	sock = socket.socket()
	sslSock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv23, ca_certs=CA_CERT_PATH)	#SSLv23 supports 

	targetHost = TARGET_HOST
	targetPort = TARGET_PORT
	
	sslSock.connect((targetHost, int(targetPort)))

	cert = sslSock.getpeercert()
	#if not cert or ssl.match_hostname(cert, targetHost):
	#	raise Exception("Invalid host for cert")


	loginToServer(sslSock)
	
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
	
	
	
	
		
	
	

	

	

	