import photoshare
import ssl
import threading, queue

VERSION = photoshare.VERSION
HOST = ''
PORT = 1428
sendQueues = {}
lock = threading.Lock()


def handleClientConnect(sock, addr):
	""" Receive messages from client and broadcast them to
	other clients until client disconnects """
	rest = bytes()
	while True:
		try:
			msgs = photoshare.receiveMessages(sock)
		except (EOFError, ConnectionError):
			handle_disconnect(sock, addr)
			break
		if msgs.instruction == '00':
			print("handshake")
			
		elif msgs.instruction == '01':
			print("Pull")
		



		

def broadcast_msg(msg):
	""" Add message to each connected client's send queue """
	with lock:
		for q in sendQueues.values():
			q.put(msg)

def handle_client_send(sock, q, addr):
	""" Monitor queue for new messages, send them to client as they arrive """
	while True:
		msg = q.get()
		if msg == None: break
		try:
			photoshare.send_msg(sock, msg)
		except (ConnectionError, BrokenPipe):
			handle_disconnect(sock, addr)
			break


def handle_disconnect(sock, addr):
	""" Ensure queue is cleaned up and socket closed when a client
	disconnects """
	fd = sock.fileno()
	with lock:
		# Get send queue for this client
		q = sendQueues.get(fd, None)
	# If we find a queue then this disconnect has not yet
	# been handled
	if q:
		q.put(None)
		del sendQueues[fd]
		addr = sock.getpeername()
		print('Client {} disconnected'.format(addr))
		sock.close()

if __name__ == '__main__':
	#Do I have an internet connection?
		
	listenSock = photoshare.createListenSocket(HOST, PORT)
	addr = listenSock.getsockname()
	print('Listening on {}'.format(addr))
	while True:
		clientSock, addr = listenSock.accept()
		clientSock = photoshare.sslWrap(clientSock)

		q = queue.Queue()
		with lock:
			sendQueues[clientSock.fileno()] = q
		recv_thread = threading.Thread(target=handleClientConnect,args=[clientSock, addr],daemon=True)
		send_thread = threading.Thread(target=handle_client_send,args=[clientSock, q,addr],daemon=True)
		recv_thread.start()
		send_thread.start()
		print('Connection from {}'.format(addr))
	
	
	
