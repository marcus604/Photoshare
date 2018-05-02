import socket
import ssl
SSL_SERVER_PORT = 8000

if __name__ == '__main__':
	server_socket = socket.socket()
	server_socket.bind(('', SSL_SERVER_PORT))
	server_socket.listen(5)
	print("Waiting for ssl client on port %s" %SSL_SERVER_PORT)
	newsocket, fromaddr = server_socket.accept()
	# Generate your server's public certificate and private key	pairs.
	ssl_conn = ssl.wrap_socket(newsocket,server_side=True,certfile="server.crt",keyfile="server.key", ssl_version=ssl.PROTOCOL_SSLv23)
	print(ssl_conn.read())
	ssl_conn.write('200 OK\r\n\r\n'.encode())
	print("Served ssl client. Exiting...")
	ssl_conn.close()
	server_socket.close()