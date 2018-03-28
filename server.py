
import socket

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = socket.gethostname()

port = 9876

serverSocket.bind((host, port))

serverSocket.listen(5)

while True:
    clientSocket,addr = serverSocket.accept()

    print("hi hi %s" % str(addr))

    msg = 'thanks bitch' + "\r\n"
    clientSocket.send(msg.encode('ascii'))
    clientSocket.close()