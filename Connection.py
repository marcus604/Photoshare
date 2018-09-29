import socket
import ssl
import logging
from PSMessage import PSMessage

logging.basicConfig(filename='photoshare.log',level=logging.INFO)
logger = logging.getLogger(__name__)

class ServerConnection:

    VERSION = ''
    ENDIAN = ''
    PORT = ''
    HOST = ''
    listenSock = ''
    clientSock = ''
    clientAddress = ''
   

    def __init__(self, version, endian, port, host):
        self.VERSION = version
        self.ENDIAN = endian
        self.PORT = int(port)
        self.HOST = host
        
        
		
    def prepareConnection(self):
        try:
            listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listenSock.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
            listenSock.bind((self.HOST, self.PORT))
            listenSock.listen(100)

        except OSError as e:
            if e.args[0] == 98 or 48:
                        logger.error("Failed to create socket: Address already in use")
                        return False
            if e.args[0] == 13:
                        logger.error("Failed to create socket: Permission Denied")
                        return False
      
        addr = listenSock.getsockname()
        logger.info('Listening on {}'.format(addr))
        self.listenSock = listenSock
                        
    def processNewConnection(self):
        clientSock, clientAddress = self.listenSock.accept()
        try:
            clientSock = self.sslWrap(clientSock)
        except ssl.SSLEOFError as e:
            logger.info('Rejected NoSSL {0} {1}'.format(clientAddress[0], clientAddress[1]))
        self.clientSock = clientSock
        self.clientAddress = clientAddress
        print("hi")

    def close(self):
        self.clientSock.close()
        logger.info('Client {} disconnected'.format(self.clientAddress))

    

    def sendMessage(self, msg):
        sock = self.clientSock
        try: 
            sock.sendall(msg)
            print("message sent")
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
        return self.clientAddress

    #Wraps socket with protocol SSLv23. Supports TLS1.2-1.0
    #Doesnt handle being port scanned
    def sslWrap(self, sock):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_OPTIONAL
        context.load_cert_chain(certfile="server.crt", keyfile="server.key")
        #Useful when I want to see unecrypted on the wire traffic
        #Cant decrypt otherwise as it uses diffie helman and encrypts session data with a different key
        context.set_ciphers('RSA')		
        return context.wrap_socket(sock, server_side=True)
    

    
    #def fromString(self, rawMsg):
        

    #def receiveMessage(self):
