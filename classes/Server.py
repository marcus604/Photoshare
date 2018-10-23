from classes.PSMessage import PSMessage, PSMsgFactory
from classes.DBConnection import dbConnection
from classes.FileHandler import *
from classes.ServerConnection import ServerConnection
from classes.User import User
from utils.log import getConsoleHandler, getFileHandler, getLogger
import ssl
import threading, queue
import socket
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

psLogger = getLogger(__name__, "logs/photoshare.log")
psLogger.debug("Loading Server class")

class Server:


        sendQueues = {}
        lock = threading.Lock()
        TOKEN_SIZE = 8
        BUFFER_SIZE = 32768 
        pr = cProfile.Profile()
        dbConn = None
        msgFactory = None
        fileHandler = None
        connection = None
        settings = None
        port = None
        host = None
        


        

        def __init__(self, settings):
                self.settings = settings
                

        #User initiated stoppage of the server
        #Attempt to clean up any remaining messages in q, and close the socket with a RST
        #Errors are likely to be produced if the socket is already disconnected
        #Can safely eat errors
        #Server thread is blocked waiting for socket.accept()
        #Unblock by connecting
        def userRequestedStop(self):
                psLogger.info("Stopping Server")
                try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        #Server thread is blocked waiting for connection
                        sock.connect((self.host, int(self.port)))                       
                        sock.sendall(b'0')
                        sock.close()
                        self.disconnectClient(self.connection)  #Clear any messages waiting in Q
                        self.connection.forceClose()            #Close socket and send RST
                except Exception as e:
                        print(e)
                        psLogger.debug("Consumed error when stopping server")   #Abo
                self.dbConn = None
                self.msgFactory = None
                self.fileHandler = None
                self.connection = None
                self.settings = None

        def stop(self):
                psLogger.debug("Server error")
                


        def run(self):
        
                
        
                psLogger.info('Starting PhotoShare')

                

                VERSION = self.settings.get('MAIN', 'version')
                ENDIAN = self.settings.get('MAIN', 'endian')
                self.port = self.settings.get('Network', 'port')
                self.host = self.settings.get('Network', 'host')
                BUFFER_SIZE = int(self.settings.get('Network', 'buffersize'))
                
                
                #UBUNTU FAILS HERE

                #Connect to DB host with provided username and password
                #Create database and tables if first run of app
                try:
                        dbConn = dbConnection(self.settings)
                        dbConn.connect()
                        psLogger.info("Connected to DB")
                        self.fileHandler = FileHandler(self.settings.get('DIR', 'photos'), self.settings.get('DIR', 'import'), self.settings.get('DIR', 'tmp'))
                        # if self.settings.getboolean('MAIN', 'firstRun'):
                        #         #fileHandler.createDirectories()
                        #         dbConn.createDatabase()
                        #         dbConn.createUserTable()
                        #         dbConn.createPhotoTable()
                        #         dbConn.createAlbumTable()
                        #         dbConn.createPhotoAlbumsTable()
                        #         dbConn.createIPAddressTable()
                        #         dbConn.insertUser(User())
                        #         createAnother = input("Create another user: y/n? ")
                        #         while createAnother is "y":
                        #                 dbConn.insertUser(User())
                        #                 createAnother = input("Create another user: y/n?")
                        #         self.finishFirstRun(self.settings)
                except configparser.Error as e:
                        psLogger.error("Settings malformed: " + e.message)
                        self.stop()
                        return
                except pymysql.err.Error as e:
                        self.stop()
                        return
                except LibraryPathNotEmptyError:
                        psLogger.error("Library folder is not empty")
                        self.stop()
                        return
                   
                        
                self.connection = ServerConnection(VERSION, ENDIAN, self.port, self.host)
                self.connection.BUFFER_SIZE = BUFFER_SIZE
                if self.connection.prepareConnection() is False:
                        self.stop()
                        return
                        
                
                psLogger.info("Starting import background task")
                importThread = threading.Thread(target=self.fileHandler.importPhotos, args=[self.settings], daemon=True)
                importThread.start()
                       
                
                self.msgFactory = PSMsgFactory(VERSION, ENDIAN)
                while True:
                        #photoshare.timerCheckpoint("Creating socket")
                        psLogger.info("Waiting for connection...")
                        
                        connectionSuccess = self.connection.processNewConnection()
                        if self.isIPBanned(dbConn, self.connection.getClientAddress()):
                                psLogger.info("Banned IP: {}".format(self.connection.getClientAddress()))
                                self.connection.close()
                                continue
                        if connectionSuccess is False:
                                dbConn.ipFailedAttempt(self.connection.getClientAddress())
                                self.connection.close()
                                continue
                

                        
                        q = queue.Queue()
                        with self.lock:
                                self.sendQueues[self.connection.getClientSocket().fileno()] = q
                        recv_thread = threading.Thread(target=self.clientConnected,args=[self.connection, dbConn],daemon=True)
                        send_thread = threading.Thread(target=self.handleClientSend,args=[self.connection, q],daemon=True)
                        recv_thread.start()
                        send_thread.start()
                        
                        



        def clientConnected(self, connection, dbConn):
               
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
                                        psLogger.info("Connection Error")
                                        self.clientDisconnected(connection)
                                        break
                                if msg.instruction == PSMessage.Instruction.HANDSHAKE:                #Handshake
                                        user = self.verifyUser(msg.data, dbConn)             ###################
                                        if not user:             #Failed Login           
                                                msg = self.msgFactory.generateError('0')
                                                self.addMsgToQueue(msg)      
                                                time.sleep(1) #Ensures that rejection packet goes out before reset
                                                dbConn.ipFailedAttempt(connection.getClientAddress())                 
                                                self.clientDisconnected(connection)
                                                break
                                        #Valid User
                                        #Generate Token to send back to user
                                        loggedInUser = user
                                        token = secrets.token_hex(self.TOKEN_SIZE)
                                        dbConn.userSignedIn(loggedInUser, token)
                                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.HANDSHAKE.value, token)
                                        self.addMsgToQueue(msg)
                                        continue
                                
                                else:   #If its not trying to handshake it must already have a valid connection
                                        if clientAddress[0] != clientIP and msg.data[:(self.TOKEN_SIZE * 2)] != token:        #Grabs the token stored at the beginning of the data
                                                psLogger.info("Unauthorized Connection")
                                                self.clientDisconnected(connection)
                                        else:
                                                msg.stripToken()                #Dont need it now, can throw away token
                                
                                if msg.instruction == PSMessage.Instruction.SYNC:                #Sync
                                        self.sync(connection, loggedInUser, dbConn, msg.data)
                                        dbConn.userSynced(loggedInUser)                                 
                                if msg.instruction == PSMessage.Instruction.PHOTO_REQUEST:               #Client requesting specific image
                                        self.retrievePhoto(dbConn, msg.data)
                                if msg.instruction == PSMessage.Instruction.PHOTO_UPLOAD:               #Incoming new photo
                                        self.receivePhoto(dbConn, msg.data)
                                        dbConn.userSynced(loggedInUser) 
                                if msg.instruction == PSMessage.Instruction.PHOTO_EDIT:               #incoming edited photo
                                        self.updatePhoto(dbConn, msg.data)
                                if msg.instruction == PSMessage.Instruction.CREATE_ALBUM:               #Create new album
                                        self.createAlbum(dbConn, msg.data)
                                if msg.instruction == PSMessage.Instruction.ADD_TO_ALBUM:               #Add photo to album
                                        self.addPhotoToAlbum(dbConn, msg.data)
                                if msg.instruction == PSMessage.Instruction.PHOTO_DELETE:               #Delete photo
                                        self.deletePhoto(dbConn, msg.data)
                                
                except Exception as e:
                        psLogger.info("Unknown Error: {}".format(e))
                        self.clientDisconnected(connection)

        def createAlbum(self, dbConn, name):
                userCreatedMsg = self.connection.receiveMessage()
                userCreatedMsg.stripToken()
                userCreated = int(userCreatedMsg.data)
                if dbConn.insertAlbum(name, userCreated):
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.CREATE_ALBUM.value, 0) #Success
                        print("create success")
                        psLogger.info("Created album: {}".format(name))
                else:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.CREATE_ALBUM.value, 10)   #Failure
                        psLogger.error("Could not create album: {}".format(name))

                self.addMsgToQueue(msg)

        def addPhotoToAlbum(self, dbConn, album):
                photoToAddMsg = self.connection.receiveMessage()
                photoToAddMsg.stripToken()
                photoHash = photoToAddMsg.data
                if dbConn.insertPhotoIntoAlbum(photoHash, album):
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.ADD_TO_ALBUM.value, 0) #Success
                        print("succecss")
                        psLogger.info("Added photo to album {}".format(album))
                else:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.ADD_TO_ALBUM.value, 10)   #Failure
                        psLogger.error("Could not add to album: {}".format(album))

                self.addMsgToQueue(msg)

        def deletePhoto(self, dbConn, hash):
                localPath = dbConn.deletePhoto(hash)

                if localPath and self.fileHandler.deletePhoto(localPath):
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_DELETE.value, 0) #Success
                        psLogger.info("Deleted Photo at {}".format(localPath))
                else:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_DELETE.value, 10)   #Failure
                        psLogger.error("Could not delete photo: {}".format(hash))

                self.addMsgToQueue(msg)
                
                
        def updatePhoto(self, dbConn, photoHash):
                fileSizeMsg = self.connection.receiveMessage()
                fileSizeMsg.stripToken()
                fileSize = int(fileSizeMsg.data)
                photoPath, photoName = dbConn.getPhotoNameandPath(photoHash)
                tmpPath = self.fileHandler.getTempFilePath(photoName)
                tmpFile = open(tmpPath, "wb")
                try:
                        self.connection.receivePhoto(tmpFile, fileSize)
                        tmpFile.close()
                        self.fileHandler.updatePhoto(tmpPath, photoPath)
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_EDIT.value, 0)
                        psLogger.info("Updated photo from client")
                except ImportErrorPhotoInvalid:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_EDIT.value, 1)
                except:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_EDIT.value, 1)
                os.remove(tmpPath)
                self.addMsgToQueue(msg)
                


        def receivePhoto(self, dbConn, photoName):
                timeStampMsg = self.connection.receiveMessage()
                timeStampMsg.stripToken()
                fileSizeMsg = self.connection.receiveMessage()
                fileSizeMsg.stripToken()
                
                timeStamp = timeStampMsg.data
                fileSize = int(fileSizeMsg.data)
                tmpPath = self.fileHandler.getTempFilePath(photoName)
                tmpFile = open(tmpPath, "wb")
                self.connection.receivePhoto(tmpFile, fileSize)
                tmpFile.close()
                try:            #Import photo, true is added to tell method to generate all previous hashes
                        self.fileHandler.importPhoto(dbConn, tmpPath, timeStamp, True)
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_UPLOAD.value, 0)
                        psLogger.info("Imported Photo from client")
                except ImportErrorDuplicate:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_UPLOAD.value, 1)
                        psLogger.info("Rejected duplicate photo from client")
                except ImportErrorPhotoInvalid:
                        msg = self.msgFactory.generateMessage(PSMessage.Instruction.PHOTO_UPLOAD.value, 2)
                        psLogger.info("Rejected invalid photo from client")
                os.remove(tmpPath)
                self.addMsgToQueue(msg)
                
                
                

        def retrievePhoto(self, dbConn, hash):
                path = dbConn.getPhotoPath(hash)
                fullPath = self.fileHandler.getPhotoPath(path)
                sizeOfPhoto = os.path.getsize(fullPath)
                msg = self.msgFactory.generateMessage(3, sizeOfPhoto)
                self.addMsgToQueue(msg)
                with open(fullPath, 'rb') as infile:
                        l = infile.read(self.BUFFER_SIZE)
                        count = 0
                        while l:
                                try:
                                        count += 1
                                        self.addMsgToQueue(l)
                                except (ConnectionError):
                                        self.clientDisconnected(self.connection)
                                        break
                                l = infile.read(self.BUFFER_SIZE)
                psLogger.info("Sent photo with size {}".format(sizeOfPhoto))




        def sync(self, connection, user, dbConn, compressionEnabled):
                lastSync = dbConn.getLastSync(user)
                if lastSync is None:            #First sync, sets as time, jan 1 2017
                        lastSync = 1483228800 
                photosToSend = dbConn.getRangeOfPhotoPaths(lastSync)
                if photosToSend:
                        numOfPhotos = len(photosToSend)
                        numOfPhotosMsg = self.msgFactory.generateMessage(2, numOfPhotos)
                        self.addMsgToQueue(numOfPhotosMsg) 
                        for localPath in photosToSend:
                                fullPath = self.fileHandler.getPhotoPath(localPath['Dir'])
                                if compressionEnabled == "1":        #Compress Photos
                                        thumbnailPath = self.fileHandler.getThumbnailPath(localPath['Dir'])
                                        fullPath = thumbnailPath
                                        
                                        
                                
                                sizeOfPhoto = os.path.getsize(fullPath)
                                
                                msg = self.msgFactory.generateMessage(3, sizeOfPhoto)
                                self.addMsgToQueue(msg)
                                fileName = self.fileHandler.getPhotoName(localPath['Dir'])
                                msg = self.msgFactory.generateMessage(4, fileName)
                                self.addMsgToQueue(msg)
                                photoHash = dbConn.getHash(localPath['Dir'])
                                msg = self.msgFactory.generateMessage(5, photoHash)
                                self.addMsgToQueue(msg)
                                timestamp = dbConn.getTimeStamp(localPath['Dir'])
                                msg = self.msgFactory.generateMessage(6, timestamp)
                                self.addMsgToQueue(msg)
                                with open(fullPath, 'rb') as infile:
                                        l = infile.read(self.BUFFER_SIZE)
                                        count = 0
                                        while l:
                                                try:
                                                        count += 1
                                                        self.addMsgToQueue(l)
                                                except (ConnectionError):
                                                        self.clientDisconnected(connection)
                                                        break
                                                l = infile.read(self.BUFFER_SIZE)
                        psLogger.info("Sent {} photos to {}".format(numOfPhotos, user.USERNAME))
                else:
                        numOfPhotosMsg = self.msgFactory.generateMessage(2, 0)
                        self.addMsgToQueue(numOfPhotosMsg) 
                        psLogger.info("No Photos to send")                        
        
                psLogger.info("Waiting for request...")


                        
        





        # Monitor queue for new messages, send them to client as they arrive
        def handleClientSend(self, connection, q):
                while True:
                        msg = q.get()
                        if msg == None: break
                        try:
                                connection.sendMessage(msg)
                                #print("sent message {}".format(random.randint(1,9)))  Helpful to know when q is empty
                        except ConnectionError as e:
                                self.clientDisconnected(connection)
                                break



        def verifyUser(self, data, dbConn):
                #Parse Username and password from given data
                #Connect to database and 
                parts = data.split(':', maxsplit=1)
                userName = parts[0]
                password = parts[1]
                #Connect to DB and find given user
                user = dbConn.getUser(userName)
                if not user:
                        #No user found
                        psLogger.info("Invalid credentials for user: {}".format(userName))
                        return False
                ph = PasswordHasher()
                try:
                        ph.verify(user.getHash(), password + user.getSalt())
                except argon2.exceptions.VerifyMismatchError:
                        psLogger.info("Invalid credentials for user: {}".format(userName))               
                        return False
                psLogger.info("User {} connected".format(userName))
                return user
                




        def addMsgToQueue(self, msg):
                with self.lock:
                        for q in self.sendQueues.values():
                                #print("added msg to q {}".format(random.randint(1,9)))
                                q.put(msg)



        #For when connection should be closed immediatly
        def disconnectClient(self, connection):
                clientSock = connection.getClientSocket()
                if clientSock == "":
                        return
                fd = clientSock.fileno()
                with self.lock:
                        # Get send queue for this client
                        q = self.sendQueues.get(fd, None)
                # If we find a queue then this disconnect has not yet
                # been handled
                if q:
                        del self.sendQueues[fd]
                        q.put(None)
                connection.disconnectClient()
                
        #Client disconnected for non nefarious reasons
        def clientDisconnected(self, connection):
                """ Ensure queue is cleaned up and socket closed when a client
                disconnects """
                clientSock = connection.getClientSocket()
                if clientSock == "":
                        return
                fd = clientSock.fileno()
                with self.lock:
                        # Get send queue for this client
                        q = self.sendQueues.get(fd, None)
                # If we find a queue then this disconnect has not yet
                # been handled
                if q:
                        del self.sendQueues[fd]
                        q.put(None)
                connection.close()
                


        #FOR DEBUGGING ONLY
        def finishFirstRun(self, settings):
                settingsFile = "Settings.ini"
                settingsFP = open(settingsFile, "w")
                settings.set('MAIN', 'firstRun', 'False')
                settings.write(settingsFP)
                settingsFP.close()
                psLogger.info("Finished First Run")


        def isIPBanned(self, dbConn, ip):
                failedAttempts = dbConn.getIPFailedAttempts(ip)
                if failedAttempts:
                        if failedAttempts > 5:
                                return True
                return False
        





       
                        
                

                
        
        
