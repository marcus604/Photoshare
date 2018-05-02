import sys, socket, threading
import ssl
import photoshare

from pprint import pprint

VERSION = photoshare.VERSION
TARGET_HOST = sys.argv[-1] if len(sys.argv) > 1 else '10.10.10.5'
TARGET_PORT = photoshare.PORT
CA_CERT_PATH = 'server.crt'

def handleClientSend(sock):
	str = 'FFFFFFFF FFFF 0001'
	try:
		photoshare.send_msg(sock, str) #Blocks until sent
	except (BrokenPipeError, ConnectionError):
		print("WRONG")
		

if __name__ == '__main__':

	sock = socket.socket()
	sslSock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv23, ca_certs=CA_CERT_PATH)	#SSLv23 supports 

	targetHost = TARGET_HOST
	targetPort = TARGET_PORT

	sslSock.connect((targetHost, int(targetPort)))
	cert = sslSock.getpeercert()
	
	
	
	pprint(cert)
	if not cert or ssl.match_hostname(cert, targetHost):
		raise Exception("Invalid host for cert")

	thread = threading.Thread(target=handleClientSend, args=[sslSock], daemon=True)
	thread.start()
	rest = bytes()
	addr = sslSock.getsockname()

	#Loop indefinitely to receive messages from server
	while True:
		try:
			#blocks
			(msgs, rest) = photoshare.receiveMessages(sslSock, rest)
			for msg in msgs:
				print(msg)
		except ConnectionError:
			print('Connection to server closed')
			sock.close()
			break

	

	print(sslSock.read())
	sslSock.close()