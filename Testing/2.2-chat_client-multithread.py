import sys, socket, threading
import tincanchat
import ssl
from pprint import pprint

HOST = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
PORT = tincanchat.PORT
CA_CERT_PATH = sys.argv[2] if len(sys.argv) > 2 else 'server.crt'
print(HOST)
print(CA_CERT_PATH)

def handle_input(sock):
	""" Prompt user for message and send it to server """ 
	print("Type messages, enter to send. 'q' to quit")
	while True:
		msg = input() #Blocks
		if msg == 'q':
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()
			break
		try:
			tincanchat.send_msg(sock, msg) #Blocks unti sent
		except (BrokenPipeError, ConnectionError):
			break

if __name__ == '__main__':
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	ssl_conn = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED,
	ssl_version=ssl.PROTOCOL_SSLv23, ca_certs=CA_CERT_PATH)
	ssl_conn.connect((HOST, int(PORT)))# get remote cert
	cert = ssl_conn.getpeercert()
	print("Checking server certificate")
	pprint(cert)
	if not cert or ssl.match_hostname(cert, HOST):
		raise Exception("Invalid SSL cert for host %s. Check if	this is a man-in-the-middle attack!" %HOST )
	print("Server certificate OK.\n Sending some custom request...	GET ")
	
	print('Connected to {}:{}'.format(HOST, PORT))

	#Create thread for handling user input and message sending
	thread = threading.Thread(target=handle_input, args=[ssl_conn], daemon=True)
	thread.start()
	rest = bytes()
	#Loop indefinitely to receive messages from server
	while True:
		try:
			#blocks
			(msgs, rest) = tincanchat.recv_msgs(ssl_conn, rest)
			for msg in msgs:
				print(msg)
		except ConnectionError:
			print('Connection to server closed')
			sock.close()
			break


