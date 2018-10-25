import pytest
import time
import threading
import socket
import ssl
from classes.ServerConnection import ServerConnection, ServerStoppedByUser


@pytest.fixture
def validConnection():
    '''Returns a valid connection'''
    return ServerConnection('1', 'b', 1428, 'localhost')

def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    print("ofkdaofka")

def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    method.
    """

def test_createConnection(validConnection):
    assert validConnection is not None


def test_prepareConnection(validConnection):
    validConnection.prepareConnection()
    assert validConnection.listenSock is not None

def test_PrepareConnectionReturnsFalseOnFailure(validConnection):
    validConnection.PORT = 1    #Cant bind to port 1
    result = validConnection.prepareConnection()
    assert result is False


def test_ProcessConnectionRaisesError(validConnection):
    validConnection.prepareConnection()
    connectThread = threading.Thread(target=clientNoSSL, args=[], daemon=True)
    connectThread.start()
    
    with pytest.raises(OSError) as e:
        validConnection.processNewConnection()
        assert False
    assert True

def test_ProcessConnectionCompletes(validConnection):
    validConnection.prepareConnection()
    connectThread = threading.Thread(target=clientValid, args=[], daemon=True)
    connectThread.start()

    validConnection.processNewConnection()
    assert validConnection.clientSock is not None



        

def clientValid():
    time.sleep(1)
    CA_CERT_PATH = 'certs/server.crt'
    sock = socket.socket()
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sslSock = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv23, ca_certs=CA_CERT_PATH)	#SSLv23 supports 
	
    targetHost = "localhost"
    targetPort = 1428

    sslSock.connect((targetHost, targetPort))


def clientNoSSL():
    time.sleep(1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        #Server thread is blocked waiting for connection
    sock.connect(("localhost", 1428))                       
    sock.sendall(b'0')
    time.sleep(1)
    sock.close()

