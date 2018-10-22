import socket
import ssl
import logging
from classes.PSMessage import PSMessage, PSMsgFactory
from utils.log import getConsoleHandler, getFileHandler, getLogger

psLogger = getLogger(__name__, "logs/photoshare.log")
psLogger.debug("Loading Server class")


class ServerConnection:

    VERSION = ''
    ENDIAN = ''
    PORT = ''
    HOST = ''
    listenSock = ''
    clientSock = ''
    clientAddress = ''
    BUFFER_SIZE = ''
   

    def __init__(self, version, endian, port, host):
        self.VERSION = version
        self.ENDIAN = endian
        self.PORT = int(port)
        self.HOST = host
        
        
		
    def prepareConnection(self):
        try:
            listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listenSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listenSock.bind(('', self.PORT))
            listenSock.listen(100)

        except OSError as e:
            if e.args[0] == 98 or 48:
                        psLogger.error("Failed to create socket: Address already in use")
                        return False
            if e.args[0] == 13:
                        psLogger.error("Failed to create socket: Permission Denied")
                        return False
      
        addr = listenSock.getsockname()
        #psLogger.info('Listening on {}'.format(addr))
        self.listenSock = listenSock
                        
    def processNewConnection(self):
        clientSock, clientAddress = self.listenSock.accept()
        try:
            clientSock = self.sslWrap(clientSock)            
        except ssl.SSLEOFError as e:
            psLogger.info('Rejected NoSSL {0} {1}'.format(clientAddress[0], clientAddress[1]))
            data = clientSock.recv(1)
            if data == b'0':                    #Sent when user initiates stoppage
                raise ServerStoppedByUser()     #Not caught, cascades back to server thread where it restarts
        except OSError as e:
            psLogger.info('Connection Failed from: {}'.format(clientAddress[0]))
            self.clientAddress = clientAddress
            return False
        self.clientSock = clientSock
        self.clientAddress = clientAddress

    def forceClose(self):
        try:
            self.clientSock.shutdown(socket.SHUT_RD)
            self.clientSock.close()
            psLogger.info('Disconnected client: {}'.format(self.clientAddress))
        except:
            return

    def close(self):
        try:
            self.clientSock.close()
        except AttributeError as e:
            psLogger.info('Client {} already disconnected'.format(self.clientAddress))
            return
        psLogger.info('Client {} disconnected'.format(self.clientAddress))
        

    def receivePhoto(self, file, size):
        currentSize = 0
	
        while currentSize < size:

            data = self.receivePeice(currentSize, size)
            if data == 1:
                break

            file.write(data)
            currentSize += len(data)
            

            
    def receivePeice(self, currentSize, size):
        data = self.clientSock.recv(self.BUFFER_SIZE)
        if not data:
            return 1
        if len(data) + currentSize > size:
            data = data[:size-currentSize]
        return data

    def sendMessage(self, msg):
        sock = self.clientSock
        try: 
            sock.sendall(msg)
        except Exception as e:
            print(e)
            raise ConnectionError

    def receiveMessage(self):
        """ Receive data and parse into appropiate container """
        sock = self.clientSock
        endian = sock.read(1).decode('utf-8')
        version = int(sock.read(2).decode('utf-8'))
        instruction = int(sock.read(2).decode('utf-8'))
        length = int(sock.read(2).decode('utf-8'))
        data = sock.read(length).decode('utf-8')		#Catches value error above in case this is empty, is this the best way to do it?

        receivedMessage = PSMessage(endian, version, instruction, length, data)
        
        #receivedMessage.print()
        if not receivedMessage:
            raise ConnectionError()
        return receivedMessage

    def getClientSocket(self):
        return self.clientSock

    def getClientAddress(self):
        return self.clientAddress[0]

    #Wraps socket with protocol SSLv23. Supports TLS1.2-1.0
    #Doesnt handle being port scanned
    def sslWrap(self, sock):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_OPTIONAL
        context.load_cert_chain(certfile="certs/server.crt", keyfile="certs/server.key")
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        #Useful when I want to see unecrypted on the wire traffic
        #Cant decrypt otherwise as it uses diffie helman and encrypts session data with a different key
        context.set_ciphers('RSA')		
        return context.wrap_socket(sock, server_side=True)


class ServerStoppedByUser(Exception):
        pass
    
