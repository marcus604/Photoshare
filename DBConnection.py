import pymysql
import configparser
import logging
from User import user
import time

logging.basicConfig(filename='photoshare.log',level=logging.DEBUG)
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
        self.executeSQL('CREATE TABLE `photoshare`.`users` ( `UserName` VARCHAR(255) NOT NULL , `Hash` VARCHAR(255) NOT NULL , `Salt` VARCHAR(255) NOT NULL , `DateCreated` INT(11) NOT NULL , `LastSignedIn` INT(11) NULL , `LastSync` INT(11) NULL , PRIMARY KEY (`UserName`(255)));')
        logger.info("User table created")

    def createPhotoTable(self):
        self.executeSQL('CREATE TABLE `photoshare`.`photos` ( `md5Hash` VARCHAR(255) NOT NULL , `Make` VARCHAR(255) , `Model` VARCHAR(255) , `LensModel` VARCHAR(255) , `Flash` VARCHAR(255) , `DateTime` VARCHAR(255) , `ISO` VARCHAR(255) , `Aperture` VARCHAR(255) , `FocalLength` VARCHAR(255) , `Width` VARCHAR(255) , `Height` VARCHAR(255) , `ExposureTime` VARCHAR(255) , `Sharpness` VARCHAR(255) , `Type` VARCHAR(255) , `Dir` VARCHAR(255) NOT NULL , PRIMARY KEY (`md5Hash`(255)));')
        logger.info("Photo table created")

    #Could be compressed to single line
    def insertUser(self, user):
        userName = user.getUserName()
        salt = user.getSalt()
        hash = user.getHash()
        dateCreated = int(time.time())
        sql = 'INSERT INTO `photoshare`.`users` (`UserName`, `Hash`, `Salt`, `DateCreated`) VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\');'.format(userName, hash, salt, dateCreated)
        self.executeSQL(sql)
        logger.info("Successfully created user {}".format(userName))

    

    def executeSQL(self, sql):
        try:
            with self.SQL_CONNECTION.cursor() as cursor:
                cursor.execute(sql)
                self.SQL_CONNECTION.commit()
                result = cursor.fetchall()
                cursor.close ()
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


	
