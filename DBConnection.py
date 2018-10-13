import pymysql
import configparser
import logging
from argon2 import PasswordHasher
from User import User
import time

logging.basicConfig(filename='photoshare.log',level=logging.INFO)
logger = logging.getLogger(__name__)

class dbConnection:

    USERNAME = ''
    PASSWORD = ''
    HOST = ''
    DATABASE_NAME = ''
    CHARSET = ''
    SQL_CONNECTION = ''


    def __init__(self, settings):
        self.HOST           = settings.get('SQL', 'host')
        self.USERNAME       = settings.get('SQL', 'user')
        self.PASSWORD       = settings.get('SQL', 'password')
        self.DATABASE_NAME  = settings.get('SQL', 'dbName')
        self.CHARSET        = settings.get('SQL', 'charset')


    
    def connect(self):
        try:
            self.SQL_CONNECTION = pymysql.connect(host=self.HOST, user=self.USERNAME, password=self.PASSWORD, charset=self.CHARSET, cursorclass=pymysql.cursors.DictCursor)
            logger.info("Connected to DB")
        except pymysql.err.OperationalError as e: 
            if (e.args[0] == 1045):		#Doesnt catch on ubuntu
                logger.error("Rejected Credentials SQL")
                raise e
            elif (e.args[0] == 2003):
                logger.error("Rejected SQL Host")
                raise e

    def createDatabase(self):
        self.executeSQL('CREATE DATABASE photoshare COLLATE utf8_general_ci;')
        logger.info("Database created")

    def createUserTable(self):
        self.executeSQL('CREATE TABLE `photoshare`.`users` ( `UserName` VARCHAR(255) NOT NULL , `Hash` VARCHAR(255) NOT NULL , `Salt` VARCHAR(255) NOT NULL , `DateCreated` INT(11) NOT NULL , `LastSignedIn` INT(11) NULL , `LastSync` INT(11) NULL , `Token` VARCHAR(16) NULL , `CompressionLevel` INT(1) , PRIMARY KEY (`UserName`(255)));')
        logger.info("User table created")

    def createPhotoTable(self):
        self.executeSQL('CREATE TABLE `photoshare`.`photos` ( `md5Hash` VARCHAR(255) NOT NULL , `Dir` VARCHAR(255) NOT NULL , `DateAdded` VARCHAR(255) NOT NULL , `Make` VARCHAR(255) , `Model` VARCHAR(255) , `LensModel` VARCHAR(255) , `Flash` VARCHAR(255) , `DateTime` VARCHAR(255) , `ISO` VARCHAR(255) , `Aperture` VARCHAR(255) , `FocalLength` VARCHAR(255) , `Width` VARCHAR(255) , `Height` VARCHAR(255) , `ExposureTime` VARCHAR(255) , `Sharpness` VARCHAR(255) , PRIMARY KEY (`md5Hash`(255)));')
        logger.info("Photo table created")

    def createIPAddressTable(self):
         self.executeSQL('CREATE TABLE `photoshare`.`ipaddresses` ( `Address` VARCHAR(16) NOT NULL , `FailedAttempts` INT(1) NOT NULL , PRIMARY KEY (`Address`(16)));')
         logger.info("IPAddress table created")

    #Could be compressed to single line
    def insertUser(self, user):
        userName = user.getUserName()
        salt = user.getSalt()
        hash = user.getHash()
        dateCreated = int(time.time())
        sql = 'INSERT INTO `photoshare`.`users` (`UserName`, `Hash`, `Salt`, `DateCreated`) VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\');'.format(userName, hash, salt, dateCreated)
        self.executeSQL(sql)
        logger.info("Successfully created user {}".format(userName))

    def insertPhoto(self, hash, path, exifValues, year, month, day, ptime):
        # Create a new record
            currentTime = time.time()
            fileDateTime = "{}:{}:{} {}".format(year, month, day, ptime)
            sql = "INSERT INTO `photoshare`.`photos` (`md5Hash`, `dir`, `dateadded`, `make`, `model`, `lensModel`, `flash`, `dateTime`, `ISO`, `aperture`, `focalLength`, `width`, `height`, `exposureTime`, `sharpness`) VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\', \'{4}\', \'{5}\', \'{6}\', \'{7}\', \'{8}\', \'{9}\', \'{10}\', \'{11}\', \'{12}\', \'{13}\', \'{14}\');".format(hash, path, currentTime, exifValues[0], exifValues[1], exifValues[2], exifValues[3], fileDateTime, exifValues[5], exifValues[6], exifValues[7], exifValues[8], exifValues[9], exifValues[10], exifValues[11])
            self.executeSQL(sql)

            # connection is not autocommit by default. So you must commit to save
            # your changes.
            #connection.commit()
            #photosImported += 1
            """ except pymysql.err.DataError:   #Data too long
                importErrors += 1
                pass
            except pymysql.err.IntegrityError:  #Duplicate Primary Key
                importErrors += 1
                pass
            except pymysql.err.ProgrammingError: #Table doesnt exist
                importErrors += 1
                pass """
            #except BaseException:
            #    pass
    
    def getRangeOfPhotoPaths(self, lastSync):
        currentTime = time.time()
        sql = "SELECT `Dir` FROM `photoshare`.`photos` WHERE `DateAdded` BETWEEN '{}' AND '{}'".format(lastSync, currentTime)
        return self.executeSQL(sql)
        
    def getHash(self, photoDir):
        sql = "SELECT `md5Hash` FROM `photoshare`.`photos` WHERE `Dir` = '{}'".format(photoDir)
        result = self.executeSQL(sql)
        return result[0].get('md5Hash')
        
    def getTimeStamp(self, photoDir):
        sql = "SELECT `DateTime` FROM `photoshare`.`photos` WHERE `Dir` = '{}'".format(photoDir)
        result = self.executeSQL(sql)
        return result[0].get('DateTime')
    
    def getPhotoPath(self, hash):
        sql = "SELECT `Dir` FROM `photoshare`.`photos` WHERE `md5Hash` = '{}'".format(hash)
        result = self.executeSQL(sql)
        if result:
            return result[0].get('Dir')
        

    def getPhotoNameandPath(self, hash):
        photoPath = self.getPhotoPath(hash)
        year,month,day,name = photoPath.split("/")
        return photoPath, name
            
    def getAllExistingHashes(self):
        hashes = []
        sql = "SELECT `md5Hash` FROM `photoshare`.`photos`"
        result = self.executeSQL(sql)
        if result:
            for row in result:
                hashes.append(row['md5Hash'])
        return hashes

    #Returns file path if successfully removed from database
    def deletePhoto(self, hash):
        localPath = self.getPhotoPath(hash)
        if localPath:
            sql = "DELETE FROM `photoshare`.`photos` WHERE `md5Hash` = '{}'".format(hash)
            result = self.executeSQLReturnRowCount(sql)
            if result:
                return localPath
        

    def getUser(self, userName):
        sql = "SELECT `Hash`, `Salt`, `LastSignedIn`, `LastSync` FROM `photoshare`.`users` WHERE `UserName` = '{}'".format(userName)
        result = self.executeSQL(sql)
        if result is None:  #No user found
            return False
        return User(userName, result[0].get('Hash'), result[0].get('Salt'), result[0].get('LastSignedIn'), result[0].get('LastSync'))

    def getIPFailedAttempts(self, ip):
        sql = "SELECT `failedAttempts` FROM `photoshare`.`IPAddresses` WHERE `address` = '{}'".format(ip)
        result = self.executeSQL(sql)
        if result is None:
            return result
        return result[0].get('failedAttempts')

    def ipFailedAttempt(self, ip):
        numOfAttempts = self.getIPFailedAttempts(ip)
        if numOfAttempts is None:
            sql = "INSERT INTO `photoshare`.`ipaddresses` (`Address`, `FailedAttempts`) VALUES (\'{0}\', \'{1}\');".format(ip, 1)
        else:
            numOfAttempts = numOfAttempts + 1
            sql = "UPDATE `photoshare`.`ipaddresses` SET `FailedAttempts` = '{}' WHERE `Address` = '{}'".format(numOfAttempts, ip)
        self.executeSQL(sql)

    def userSignedIn(self, user, token):
        currentTime = time.time()
        sql = "UPDATE `photoshare`.`users` SET `LastSignedIn` = '{}' , `Token` = '{}' WHERE UserName = '{}'".format(currentTime, token, user.getUserName())
        self.executeSQL(sql)
    
    def userSynced(self, user):
        currentTime = time.time()
        sql = "UPDATE `photoshare`.`users` SET `LastSync` = '{}' WHERE `UserName` = '{}'".format(currentTime, user.getUserName())
        self.executeSQL(sql)

    def getLastSync(self, user):
        sql = "SELECT `LastSync` FROM `photoshare`.`users` WHERE `UserName` = '{}'".format(user.USERNAME)
        result = self.executeSQL(sql)
        return result[0].get('LastSync')


    #Used for DELETE statements as rowcount only way to determine success
    def executeSQLReturnRowCount(self, sql):
        try:
            with self.SQL_CONNECTION.cursor() as cursor:
                cursor.execute(sql)
                self.SQL_CONNECTION.commit()
                result = cursor.rowcount
                cursor.close()
                if result:
                    return result
        except pymysql.err.ProgrammingError as e:
            logger.error(e.args[1])
            raise e
        except pymysql.err.InternalError as e:
            logger.error(e.args[1])
            raise e
        except pymysql.err.Error as e:
            logger.error(e.args[1])
            raise e

    #Need to scrub for sql injection    
    def executeSQL(self, sql):
        try:
            with self.SQL_CONNECTION.cursor() as cursor:
                cursor.execute(sql)
                self.SQL_CONNECTION.commit()
                result = cursor.fetchall()
                cursor.close()
                if result:
                    return result
        except pymysql.err.ProgrammingError as e:
            logger.error(e.args[1])
            raise e
        except pymysql.err.InternalError as e:
            logger.error(e.args[1])
            raise e
        except pymysql.err.Error as e:
            logger.error(e.args[1])
            raise e


	
