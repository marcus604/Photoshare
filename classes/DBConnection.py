import pymysql
import configparser
import logging
from argon2 import PasswordHasher
from classes.User import User
from utils.log import getConsoleHandler, getFileHandler, getLogger
import time

logging.basicConfig(filename='photoshare.log',level=logging.INFO)
logger = logging.getLogger(__name__)

psLogger = getLogger(__name__)

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

    def createAlbumTable(self):
        self.executeSQL('CREATE TABLE `photoshare`.`albums` ( `title` varchar(255) NOT NULL , `dateCreated` varchar(255) NOT NULL , `dateUpdated` varchar(255) DEFAULT NULL, `userCreated` tinyint(1) NOT NULL, `photos` varchar(255), `coverPhoto` varchar(255), PRIMARY KEY (`title`));')
        logger.info("Albums table created")

    def createPhotoAlbumsTable(self):
        self.executeSQL('CREATE TABLE `photoshare`.`photoAlbums` ( `id` int(11) unsigned NOT NULL AUTO_INCREMENT, `photo_id` VARCHAR(255) NOT NULL, `album_id` VARCHAR(255) NOT NULL, PRIMARY KEY (`id`), FOREIGN KEY (`photo_id`) REFERENCES `photoshare`.`photos`(`md5Hash`) ON DELETE CASCADE, FOREIGN KEY (`album_id`) REFERENCES `photoshare`.`albums`(`title`) ON DELETE CASCADE);')
        logger.info("PhotoAlbums table created")

    #Could be compressed to single line
    def insertUser(self, user):
        userName = user.getUserName()
        salt = user.getSalt()
        hash = user.getHash()
        dateCreated = int(time.time())
        sql = 'INSERT INTO `photoshare`.`users` (`UserName`, `Hash`, `Salt`, `DateCreated`) VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\');'.format(userName, hash, salt, dateCreated)
        self.executeSQL(sql)
        logger.info("Created user {}".format(userName))

    def insertAlbum(self, title, userCreated):
        currentTime = time.time()
        sql = "INSERT INTO `photoshare`.`albums` (`title`, `dateCreated`, `dateUpdated`, `userCreated`) VALUES (\'{}\', \'{}\', \'{}\', \'{}\');".format(title, currentTime, currentTime, userCreated)
        result = self.executeSQLReturnRowCount(sql)
        if result:
            return True  
        return False #Failed to create album

    def insertPhotoIntoAlbum(self, photo, album):
        sql = "INSERT INTO `photoshare`.`photoAlbums` (`photo_id`, `album_id`) VALUES (\'{}\', \'{}\');".format(photo, album)
        result = self.executeSQLReturnRowCount(sql)
        if result:
            return True  
        return False #Failed to add photo

    

    def insertPhoto(self, hash, path, exifValues, year, month, day, ptime):
        # Create a new record
            currentTime = time.time()
            fileDateTime = "{}:{}:{} {}".format(year, month, day, ptime)
            sql = "INSERT INTO `photoshare`.`photos` (`md5Hash`, `dir`, `dateadded`, `make`, `model`, `lensModel`, `flash`, `dateTime`, `ISO`, `aperture`, `focalLength`, `width`, `height`, `exposureTime`, `sharpness`) VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\', \'{4}\', \'{5}\', \'{6}\', \'{7}\', \'{8}\', \'{9}\', \'{10}\', \'{11}\', \'{12}\', \'{13}\', \'{14}\');".format(hash, path, currentTime, exifValues[0], exifValues[1], exifValues[2], exifValues[3], fileDateTime, exifValues[5], exifValues[6], exifValues[7], exifValues[8], exifValues[9], exifValues[10], exifValues[11])
            self.executeSQL(sql)

    def getAllPhotoPaths(self):
        sql = "SELECT `Dir` FROM `photoshare`.`photos` ORDER BY `DateTime`"
        results = self.executeSQL(sql)
        paths = []
        if results:
            for result in results:
                paths.append(result.get('Dir'))
        return paths

    def getAlbumCovers(self, albums):
        covers = []
        for album in albums:
            sql = "SELECT * FROM `photoshare`.`photoAlbums` HAVING `album_id` = '{}' LIMIT 1".format(album.get('title'))
            firstPhoto = self.executeSQL(sql)
            if firstPhoto[0]:
                covers.append(self.getPhotoPath(firstPhoto[0].get('photo_id')))   
        return covers
        


    def getAllAlbums(self):
        sql = "SELECT * FROM `photoshare`.`albums` ORDER BY `dateUpdated`"
        results = self.executeSQL(sql)
        
        if results is None:
            return []   #Expects an iterable object
        return results

        


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

    #Uses execute to scrub sql   
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


	
