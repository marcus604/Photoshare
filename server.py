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


sendQueues = {}
lock = threading.Lock()
TOKEN_SIZE = 8
BUFFER_SIZE = 32768 
pr = cProfile.Profile()
dbConn = ''






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
                        if msg.instruction == PSMessage.Instruction.HANDSHAKE:                #Handshake
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
                                msg = msgFactory.generateMessage(PSMessage.Instruction.HANDSHAKE.value, token)
                                addMsgToQueue(msg)
                                photoshare.timerCheckpoint("Authenticating user")
                                continue
                        
                        else:   #If its not trying to handshake it must already have a valid connection
                                if clientAddress[0] != clientIP and msg.data[:(TOKEN_SIZE * 2)] != token:        #Grabs the token stored at the beginning of the data
                                        logger.info("Unauthorized Connection")
                                        clientDisconnected(connection)
                                else:
                                        msg.stripToken()                #Dont need it now, can throw away token
                        
                        if msg.instruction == PSMessage.Instruction.SYNC:                #Sync
                                sync(connection, loggedInUser, dbConn, msg.data)
                                dbConn.userSynced(loggedInUser)                                 
                        if msg.instruction == PSMessage.Instruction.PHOTO_REQUEST:               #Client requesting specific image
                                retrievePhoto(dbConn, msg.data)
                        if msg.instruction == PSMessage.Instruction.PHOTO_UPLOAD:               #Incoming new photo
                                receivePhoto(dbConn, msg.data)
                                dbConn.userSynced(loggedInUser) 
                        if msg.instruction == PSMessage.Instruction.PHOTO_EDIT:               #incoming edited photo
                                updatePhoto(dbConn, msg.data)
                        if msg.instruction == PSMessage.Instruction.CREATE_ALBUM:               #Create new album
                                createAlbum(dbConn, msg.data)
                        if msg.instruction == PSMessage.Instruction.ADD_TO_ALBUM:               #Add photo to album
                                addPhotoToAlbum(dbConn, msg.data)
                        if msg.instruction == PSMessage.Instruction.PHOTO_DELETE:               #Delete photo
                                deletePhoto(dbConn, msg.data)
                        
        except Exception as e:
                logger.info("Unknown Error: {}".format(e))
                clientDisconnected(connection)

def createAlbum(dbConn, name):
        userCreatedMsg = connection.receiveMessage()
        userCreatedMsg.stripToken()
        userCreated = int(userCreatedMsg.data)
        if dbConn.insertAlbum(name, userCreated):
                msg = msgFactory.generateMessage(PSMessage.Instruction.CREATE_ALBUM.value, 0) #Success
                print("create success")
                logger.info("Created album: {}".format(name))
        else:
                msg = msgFactory.generateMessage(PSMessage.Instruction.CREATE_ALBUM.value, 10)   #Failure
                logger.error("Could not create album: {}".format(name))

        addMsgToQueue(msg)

def addPhotoToAlbum(dbConn, album):
        photoToAddMsg = connection.receiveMessage()
        photoToAddMsg.stripToken()
        photoHash = photoToAddMsg.data
        if dbConn.insertPhotoIntoAlbum(photoHash, album):
                msg = msgFactory.generateMessage(PSMessage.Instruction.ADD_TO_ALBUM.value, 0) #Success
                print("succecss")
                logger.info("Added photo to album {}".format(album))
        else:
                msg = msgFactory.generateMessage(PSMessage.Instruction.ADD_TO_ALBUM.value, 10)   #Failure
                logger.error("Could not add to album: {}".format(album))

        addMsgToQueue(msg)

def deletePhoto(dbConn, hash):
        localPath = dbConn.deletePhoto(hash)

        if localPath and fileHandler.deletePhoto(localPath):
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_DELETE.value, 0) #Success
                logger.info("Deleted Photo at {}".format(localPath))
        else:
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_DELETE.value, 10)   #Failure
                logger.error("Could not delete photo: {}".format(hash))

        addMsgToQueue(msg)
        
        
def updatePhoto(dbConn, photoHash):
        fileSizeMsg = connection.receiveMessage()
        fileSizeMsg.stripToken()
        fileSize = int(fileSizeMsg.data)
        photoPath, photoName = dbConn.getPhotoNameandPath(photoHash)
        tmpPath = fileHandler.getTempFilePath(photoName)
        tmpFile = open(tmpPath, "wb")
        try:
                connection.receivePhoto(tmpFile, fileSize)
                tmpFile.close()
                fileHandler.updatePhoto(tmpPath, photoPath)
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_EDIT.value, 0)
                logger.info("Updated photo from client")
        except ImportErrorPhotoInvalid:
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_EDIT.value, 1)
        except:
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_EDIT.value, 1)
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
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_UPLOAD.value, 0)
                logger.info("Imported Photo from client")
        except ImportErrorDuplicate:
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_UPLOAD.value, 1)
                logger.info("Rejected duplicate photo from client")
        except ImportErrorPhotoInvalid:
                msg = msgFactory.generateMessage(PSMessage.Instruction.PHOTO_UPLOAD.value, 2)
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
 
        logger.info("Waiting for request...")


                      
       





# Monitor queue for new messages, send them to client as they arrive
def handleClientSend(connection, q):
        while True:
                msg = q.get()
                if msg == None: break
                try:
                        connection.sendMessage(msg)
                        #print("sent message {}".format(random.randint(1,9)))  Helpful to know when q is empty
                except ConnectionError as e:
                        clientDisconnected(connection)
                        break



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
        




def addMsgToQueue(msg):
        with lock:
                for q in sendQueues.values():
                        #print("added msg to q {}".format(random.randint(1,9)))
                        q.put(msg)



#For when connection should be closed immediatly
def disconnectClient(connection):
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
        connection.disconnectClient()
        
#Client disconnected for non nefarious reasons
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
        
        print(PSMessage.Instruction.SYNC.value)
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
        BUFFER_SIZE = int(settings.get('Network', 'buffersize'))
        
        

        #Connect to DB host with provided username and password
        #Create database and tables if first run of app
        try:
                dbConn = dbConnection(settings)
                dbConn.connect()
                logger.info("Connected to DB")
                fileHandler = FileHandler(settings.get('DIR', 'Library'), settings.get('DIR', 'Import'), settings.get('DIR', 'Temp'))
                if settings.getboolean('MAIN', 'firstRun'):
                        fileHandler.createDirectories()
                        dbConn.createDatabase()
                        dbConn.createUserTable()
                        dbConn.createPhotoTable()
                        dbConn.createAlbumTable()
                        dbConn.createPhotoAlbumsTable()
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
        
        logger.info("Starting import background task")
        importThread = threading.Thread(target=fileHandler.importPhotos, args=[settings], daemon=True)
        importThread.start()
        
                
        connection = ServerConnection(VERSION, ENDIAN, port, host)
        connection.BUFFER_SIZE = BUFFER_SIZE
        if connection.prepareConnection() is False:
                closeApp()
        
        msgFactory = PSMsgFactory(VERSION, ENDIAN)
        while True:
                #photoshare.timerCheckpoint("Creating socket")
                logger.info("Waiting for connection...")
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
                send_thread = threading.Thread(target=handleClientSend,args=[connection, q],daemon=True)
                recv_thread.start()
                send_thread.start()
                print('Connection from {}'.format(connection.getClientAddress()))
                photoshare.timerCheckpoint("Spawned threads")



       
                        
                

                
        
        