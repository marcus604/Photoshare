import sys, threading, queue
import tincanchat
import ssl

HOST = tincanchat.HOST
PORT = tincanchat.PORT
send_queues = {}
lock = threading.Lock()

CERTFILE = sys.argv[1] if len(sys.argv) > 1 else 'server.crt'
KEYFILE = sys.argv[2] if len(sys.argv) > 2 else 'server.key'

def handle_client_recv(ssl_conn, sock, addr):
	""" Receive messages from client and broadcast them to
	other clients until client disconnects """
	rest = bytes()
	while True:
		try:
			(msgs, rest) = tincanchat.recv_msgs(ssl_conn, rest)
		except (EOFError, ConnectionError):
			handle_disconnect(ssl_conn, sock, addr)
			break
		for msg in msgs:
			msg = '{}: {}'.format(addr, msg)
			print(msg)
			broadcast_msg(msg)

def handle_client_send(ssl_conn, sock, q, addr):
	""" Monitor queue for new messages, send them to client as
	they arrive """
	while True:
		msg = q.get()
		if msg == None: break
		try:
			tincanchat.send_msg(ssl_conn, msg)
		except (ConnectionError, BrokenPipe):
			handle_disconnect(ssl_conn, sock, addr)
			break

def broadcast_msg(msg):
	""" Add message to each connected client's send queue """
	with lock:
		for q in send_queues.values():
			q.put(msg)

def handle_disconnect(ssl_conn, sock, addr):
	""" Ensure queue is cleaned up and socket closed when a client
	disconnects """
	fd = ssl_conn.fileno()
	with lock:
		# Get send queue for this client
		q = send_queues.get(fd, None)
	# If we find a queue then this disconnect has not yet
	# been handled
	if q:
		q.put(None)
		del send_queues[fd]
		addr = ssl_conn.getpeername()
		print('Client {} disconnected'.format(addr))
		ssl_conn.close()
		sock.close()

if __name__ == '__main__':
	listen_sock = tincanchat.create_listen_socket(HOST, PORT)
	addr = listen_sock.getsockname()
	print('Listening on {}'.format(addr))
	while True:
		client_sock,addr = listen_sock.accept()
		# Generate your server's public certificate and private key	pairs.
		ssl_conn = ssl.wrap_socket(client_sock,server_side=True,certfile=CERTFILE,keyfile=KEYFILE, ssl_version=ssl.PROTOCOL_SSLv23)
		print(ssl_conn.read())
		q = queue.Queue()
		with lock:
			send_queues[client_sock.fileno()] = q
		recv_thread = threading.Thread(target=handle_client_recv,args=[ssl_conn, client_sock, addr],daemon=True)
		send_thread = threading.Thread(target=handle_client_send,args=[ssl_conn, client_sock, q, addr],daemon=True)
		recv_thread.start()
		send_thread.start()
		print('Connection from {}'.format(addr))
