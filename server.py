from PSMessage import *
from photoshare import psUtil
from DBConnection import dbConnection
from FileHandler import *
from Connection import ServerConnection
from User import User
import photoshare
import ssl
import threading, queue
from argon2 import PasswordHasher
import argon2
import pymysql
import os, errno
import secrets
import time
import logging
import csv
import gzip
import shutil
import cProfile
import configparser
import pdb
import random
from io import BytesIO

ENDIAN = 'b'
VERSION = 1
ps = ''
HOST = ''
PORT = 1428
sendQueues = {}
lock = threading.Lock()
userName = 'Marcus'
passwd = 'hi'
TOKEN_SIZE = 8
SQL_USERNAME = 'root'
SQL_PASSWORD = 'thisIsMySQLPassword'
BUFFER_SIZE = 16384 #32768 
pr = cProfile.Profile()
dbConn = ''
msgFactory = PSMsgFactory(VERSION, ENDIAN)





#logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename='photoshare.log',level=logging.INFO)
logger = logging.getLogger(__name__)



def clientConnected(connection, dbConn):
        pr.enable()
        startTime = time.time()
        """ Client Session """
        clientIP = connection.getClientAddress()
        clientAddress = connection.getClientAddress()
        token = ''
        loggedInUser = ''
        try:
                while True:
                        try:
                                msg = connection.receiveMessage()
                        except (EOFError, ConnectionError, ValueError, ConnectionResetError):
                                logger.info("Connection Error")
                                clientDisconnected(connection)
                                break
                        if msg.instruction == 0:                #Handshake
                                user = verifyUser(msg.data, dbConn)             ###################
                                if not user:             #Failed Login           
                                        msg = msgFactory.generateError('0')
                                        addMsgToQueue(msg)      
                                        time.sleep(1) #Ensures that rejection packet goes out before reset
                                        dbConn.ipFailedAttempt(connection.getClientAddress())                 
                                        clientDisconnected(connection)
                                        break
                                #Valid User
                                #Generate Token to send back to user
                                loggedInUser = user
                                token = secrets.token_hex(TOKEN_SIZE)
                                dbConn.userSignedIn(loggedInUser, token)
                                msg = msgFactory.generateMessage(0, token)
                                addMsgToQueue(msg)
                                photoshare.timerCheckpoint("Authenticating user")
                                continue
                        
                        else:   #If its not trying to handshake it must already have a valid connection
                                if clientAddress[0] != clientIP and msg.data[:(TOKEN_SIZE * 2)] != token:        #Grabs the token stored at the beginning of the data
                                        logger.info("Unauthorized Connection")
                                        clientDisconnected(connection)
                                else:
                                        msg.stripToken()                #Dont need it now, can throw away token
                
                        if msg.instruction == 1:                #Sync
                                sync(connection, loggedInUser, dbConn, msg.data)
                                dbConn.userSynced(loggedInUser)                                 
                        if msg.instruction == 10:               #Client requesting specific image
                                retrievePhoto(dbConn, msg.data)
                        if msg.instruction == 20:               #Incoming new photo
                                receivePhoto(dbConn, msg.data)
                                dbConn.userSynced(loggedInUser) 
                        if msg.instruction == 30:               #incoming edited photo
                                updatePhoto(dbConn, msg.data)
                        
        except Exception as e:
                print(e)
                clientDisconnected(connection)

def updatePhoto(dbConn, photoHash):
        fileSizeMsg = connection.receiveMessage()
        fileSizeMsg.stripToken()
        fileSize = int(fileSizeMsg.data)
        print("new file size {}".format(fileSize))
        photoPath, photoName = dbConn.getPhotoNameandPath(photoHash)
        tmpPath = fileHandler.getTempFilePath(photoName)
        tmpFile = open(tmpPath, "wb")
        try:
                connection.receivePhoto(tmpFile, fileSize)
                tmpFile.close()
                fileHandler.updatePhoto(tmpPath, photoPath)
                msg = msgFactory.generateMessage(30, 0)
                logger.info("Updated photo from client")
        except ImportErrorPhotoInvalid:
                msg = msgFactory.generateMessage(30, 1)
        except:
                msg = msgFactory.generateMessage(30, 1)
        os.remove(tmpPath)
        addMsgToQueue(msg)
        


def receivePhoto(dbConn, photoName):
        timeStampMsg = connection.receiveMessage()
        timeStampMsg.stripToken()
        fileSizeMsg = connection.receiveMessage()
        fileSizeMsg.stripToken()
        
        timeStamp = timeStampMsg.data
        fileSize = int(fileSizeMsg.data)
        tmpPath = fileHandler.getTempFilePath(photoName)
        tmpFile = open(tmpPath, "wb")
        connection.receivePhoto(tmpFile, fileSize)
        tmpFile.close()
        try:            #Import photo, true is added to tell method to generate all previous hashes
                fileHandler.importPhoto(dbConn, tmpPath, timeStamp, True)
                msg = msgFactory.generateMessage(20, 0)
                logger.info("Imported Photo from client")
        except ImportErrorDuplicate:
                msg = msgFactory.generateMessage(20, 1)
                logger.info("Rejected duplicate photo from client")
        except ImportErrorPhotoInvalid:
                msg = msgFactory.generateMessage(20, 2)
                logger.info("Rejected invalid photo from client")
        os.remove(tmpPath)
        addMsgToQueue(msg)
        
        
        

def retrievePhoto(dbConn, hash):
        path = dbConn.getPhotoPath(hash)
        fullPath = fileHandler.getPhotoPath(path)
        sizeOfPhoto = os.path.getsize(fullPath)
        msg = msgFactory.generateMessage(3, sizeOfPhoto)
        addMsgToQueue(msg)
        with open(fullPath, 'rb') as infile:
                l = infile.read(BUFFER_SIZE)
                count = 0
                while l:
                        try:
                                count += 1
                                addMsgToQueue(l)
                        except (ConnectionError):
                                clientDisconnected(connection)
                                break
                        l = infile.read(BUFFER_SIZE)
        logger.info("Sent photo with size {}".format(sizeOfPhoto))




def sync(connection, user, dbConn, compressionEnabled):
        lastSync = dbConn.getLastSync(user)
        if lastSync is None:            #First sync, sets as time, jan 1 2017
                lastSync = 1483228800
        #lastSync = 1483228800  
        photosToSend = dbConn.getRangeOfPhotoPaths(lastSync)
        #print(photosToSend)
        if photosToSend:
                numOfPhotos = len(photosToSend)
                numOfPhotosMsg = msgFactory.generateMessage(2, numOfPhotos)
                addMsgToQueue(numOfPhotosMsg) 
                photoshare.timerCheckpoint("Starting Sync")
                for localPath in photosToSend:
                        fullPath = fileHandler.getPhotoPath(localPath['Dir'])
                        #print(fullPath)
                        #print("Original size: {}".format(os.path.getsize(fullPath)))
                        if compressionEnabled == "1":              #Need to compress photos
                                thumbnailPath = fileHandler.getThumbnailPath(localPath['Dir'])
                                fullPath = thumbnailPath
                                
                                
                        
                        sizeOfPhoto = os.path.getsize(fullPath)
                        
                        msg = msgFactory.generateMessage(3, sizeOfPhoto)
                        addMsgToQueue(msg)
                        fileName = fileHandler.getPhotoName(localPath['Dir'])
                        msg = msgFactory.generateMessage(4, fileName)
                        addMsgToQueue(msg)
                        photoHash = dbConn.getHash(localPath['Dir'])
                        msg = msgFactory.generateMessage(5, photoHash)
                        addMsgToQueue(msg)
                        timestamp = dbConn.getTimeStamp(localPath['Dir'])
                        msg = msgFactory.generateMessage(6, timestamp)
                        addMsgToQueue(msg)
                        with open(fullPath, 'rb') as infile:
                                l = infile.read(BUFFER_SIZE)
                                count = 0
                                while l:
                                        try:
                                                count += 1
                                                #if count % 32 == 0:
                                                #        time = photoshare.timerCheckpoint("1 Mb")               
                                                #        print ('{:.5}MB/s'.format(1 / time)) 
                                                #sock.sendall(l)
                                                addMsgToQueue(l)
                                        except (ConnectionError):
                                                clientDisconnected(connection)
                                                break
                                        l = infile.read(BUFFER_SIZE)
                        photoshare.timerCheckpoint("Sending Photo")
                logger.info("Sent {} photos to {}".format(numOfPhotos, user.USERNAME))
        else:
                numOfPhotosMsg = msgFactory.generateMessage(2, 0)
                addMsgToQueue(numOfPhotosMsg) 
                logger.info("No Photos to send")                        
 
        #photosToRecieve = 

        print("stop")


                      
       



def convert_to_bytes(no):
    result = bytearray()
    result.append(no & 255)
    for i in range(3):
        no = no >> 8
        result.append(no & 255)
    return result       

def handle_client_send(connection, q):
        """ Monitor queue for new messages, send them to client as they arrive """
        while True:
                msg = q.get()
                if msg == None: break
                try:
                        connection.sendMessage(msg)
                        #print("sent message {}".format(random.randint(1,9)))
                except ConnectionError as e:
                        clientDisconnected(connection)
                        break

""" def handleSessions():
        #Monitor  """


def verifyUser(data, dbConn):
        #Parse Username and password from given data
        #Connect to database and 
        parts = data.split(':', maxsplit=1)
        userName = parts[0]
        password = parts[1]
        #Connect to DB and find given user
        user = dbConn.getUser(userName)
        if not user:
                #No user found
                logger.info("Invalid credentials for user: {}".format(userName))
                return False
        ph = PasswordHasher()
        try:
                ph.verify(user.getHash(), password + user.getSalt())
        except argon2.exceptions.VerifyMismatchError:
                logger.info("Invalid credentials for user: {}".format(userName))               
                return False
        logger.info("User {} connected".format(userName))
        return user
        

def scrubSQL(toScrub):
        #scrub text of any invalid characters to prevent SQL injection attacks
        print(toScrub)


def addMsgToQueue(msg):
        with lock:
                for q in sendQueues.values():
                        #print("added msg to q {}".format(random.randint(1,9)))
                        q.put(msg)




def clientDisconnected(connection):
        """ Ensure queue is cleaned up and socket closed when a client
        disconnects """
        clientSock = connection.getClientSocket()
        if clientSock == "":
                return
        fd = clientSock.fileno()
        with lock:
                # Get send queue for this client
                q = sendQueues.get(fd, None)
        # If we find a queue then this disconnect has not yet
        # been handled
        if q:
                del sendQueues[fd]
                q.put(None)
        connection.close()
                





def closeApp():
        logger.info("Exiting Photoshare")
        photoshare.totalTime()
        pr.disable()
        pr.dump_stats('server.profile')
        os._exit(0)


#FOR DEBUGGING ONLY
def finishFirstRun(settings):
        settingsFile = "Settings.ini"
        settingsFP = open(settingsFile, "w")
        settings.set('MAIN', 'firstRun', 'False')
        settings.write(settingsFP)
        settingsFP.close()
        logger.info("Finished First Run")


def isIPBanned(dbConn, ip):
        failedAttempts = dbConn.getIPFailedAttempts(ip)
        if failedAttempts:
                if failedAttempts > 5:
                        return True
        return False
        



if __name__ == '__main__':
        
        

        photoshare.startTimer()
        logger.info('Starting PhotoShare')

        #Read Settings .ini file
        #Extented Interpolation allow for use of variables within settings
        #Makes setting directories easier and cleaner
        settings = configparser.ConfigParser()
        settings._interpolation = configparser.ExtendedInterpolation()
        settingsSet = settings.read('settings.ini')
        if settingsSet == []:
                logger.error("Settings file not found")
                closeApp()

        VERSION = settings.get('MAIN', 'version')
        ENDIAN = settings.get('MAIN', 'endian')
        port = settings.get('Network', 'port')
        host = settings.get('Network', 'host')

        #FOR DEBUGGING ONLY
        #port = int(port) + 1
        #increasePortNumber(port, settings)

        


        #Connect to DB host with provided username and password
        #Create database and tables if first run of app
        try:
                dbConn = dbConnection(settings)
                dbConn.connect()
                fileHandler = FileHandler(settings.get('DIR', 'Library'), settings.get('DIR', 'Import'), settings.get('DIR', 'Temp'))
                if settings.getboolean('MAIN', 'firstRun'):
                        fileHandler.createDirectories()
                        dbConn.createDatabase()
                        dbConn.createUserTable()
                        dbConn.createPhotoTable()
                        dbConn.createIPAddressTable()
                        dbConn.insertUser(User())
                        createAnother = input("Create another user: y/n? ")
                        while createAnother is "y":
                                dbConn.insertUser(User())
                                createAnother = input("Create another user: y/n?")
                        finishFirstRun(settings)
        except configparser.Error as e:
                logger.error("Settings malformed: " + e.message)
                closeApp()
        except pymysql.err.Error as e:
                closeApp()
        except LibraryPathNotEmptyError:
                logger.error("Library folder is not empty")
                closeApp()
        
        #Start photo directory service
        fileHandler.importPhotos(dbConn)
                
       
        
        connection = ServerConnection(VERSION, ENDIAN, port, host)
        if connection.prepareConnection() is False:
                closeApp()
        

        while True:
                photoshare.timerCheckpoint("Creating socket")
                connectionSuccess = connection.processNewConnection()
                if isIPBanned(dbConn, connection.getClientAddress()):
                        logger.info("Banned IP: {}".format(connection.getClientAddress()))
                        connection.close()
                        continue
                if connectionSuccess is False:
                        dbConn.ipFailedAttempt(connection.getClientAddress())
                        connection.close()
                        continue
               

                photoshare.timerCheckpoint("Connection")
                q = queue.Queue()
                with lock:
                        sendQueues[connection.getClientSocket().fileno()] = q
                recv_thread = threading.Thread(target=clientConnected,args=[connection, dbConn],daemon=True)
                send_thread = threading.Thread(target=handle_client_send,args=[connection, q],daemon=True)
                recv_thread.start()
                send_thread.start()
                print('Connection from {}'.format(connection.getClientAddress()))
                photoshare.timerCheckpoint("Spawned threads")



       
                        
                

                
        
        
        

""" #Opens DB, creates a zipped CSV of contents
#Need to split up sync to smaller peices to help if/when connection is interupted in initial sync
#Need to see what compression level is being asked
def initialSync(sock, sqlConnection):

        filename = 'photosCSV.gz'
        #filename = 'Testing/Files/1G'

        #Is the database populated?
        logger.info("Starting Initial Sync")

        #Are we resuming syncing
        #Has the database changed since we started the initial sync

        #Generate CSV file of Photos table
        try:
                with sqlConnection.cursor() as cursor:
                        sql = "SELECT * FROM photos"
                        results = cursor.execute(sql)
                        if cursor.rowcount == 0:        #Database is empty      
                                logger.info("No Photos in Database")
                        photoshare.timerCheckpoint("Retrieving {0} photos".format(results))     
                        logger.debug("Syncing {} photos".format(results))
                        with gzip.open('photosCSV.gz', 'wt') as fileIn:
                                writer = csv.writer(fileIn)
                                writer.writerow([x[0] for x in cursor.description])  # column headers                           
                                writer.writerows(cursor._result.rows)
                        photoshare.timerCheckpoint("Creating Zip of DB")
        except pymysql.err.ProgrammingError as e:
                logger.error('SQL Table doesnt exist')
        except pymysql.err.DatabaseError as e:
                logger.error('SQL Error')
        finally:
                cursor.close ()

        #Check if file needs to be split up to send over network
        if os.path.exists(filename):
                length = os.path.getsize(filename)
                sock.send(convert_to_bytes(length))
        with open(filename, 'rb') as infile:
                l = infile.read(BUFFER_SIZE)
                count = 0
                while l:
                        try:
                                count += 1
                                if count % 32 == 0:
                                        time = photoshare.timerCheckpoint("1 Mb")               
                                        print ('{:.5}MB/s'.format(1 / time)) 
                                sock.sendall(l)
                        except (ConnectionError):
                                clientDisconnected(connection)
                                break
                        l = infile.read(BUFFER_SIZE) 
        

        photoshare.timerCheckpoint("Transfering DB Table")
        os.remove(filename)

        #Collect files to sync
        fileHandles = photoshare.getFileHandles("Library/")

        #Assume for now that we want full quality sync
        #Bundle 10 photos together
        if fileHandles != False:
                numOfPhotos = convert_to_bytes(len(fileHandles))
                sock.send(numOfPhotos)
                #count = 0
                for file in fileHandles:
                        
                        length = os.path.getsize(file)
                        sock.send(convert_to_bytes(length))
                        with open(file, 'rb') as infile:
                                l = infile.read(BUFFER_SIZE)
                                count = 0
                                while l:
                                        try:
                                                count += 1
                                                if count % 32 == 0:
                                                        time = photoshare.timerCheckpoint("1 Mb")               
                                                        print ('{:.5}MB/s'.format(1 / time)) 
                                                sock.sendall(l)
                                        except (ConnectionError):
                                                clientDisconnected(connection)
                                                break
                                        l = infile.read(BUFFER_SIZE) """