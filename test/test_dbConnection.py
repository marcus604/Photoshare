import pytest
import configparser
import pymysql
from classes.DBConnection import dbConnection
from classes.User import User
from classes.PSAlbum import PSAlbum



@pytest.fixture
def validSettings():
    settings = configparser.ConfigParser()
    settings._interpolation = configparser.ExtendedInterpolation()
    settingsSet = settings.read('settings.ini')
    if settingsSet == []:
        return False
    return settings

@pytest.fixture
def validDBConnection(validSettings):
    return dbConnection(validSettings)

@pytest.fixture
def validUser():
    return User('test', 'hash', 'salt')

@pytest.fixture
def validAlbum():
    return PSAlbum("testAlbum", 1111, 1111, 1)




def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    #validDBConnection.connect()
    #validDBConnection.deleteUser(validUser.USERNAME)


def test_DBConnectionInit(validSettings):
    assert dbConnection(validSettings) is not None

def test_connectToDB(validDBConnection):
    validDBConnection.connect()
    assert validDBConnection.SQL_CONNECTION is not None


def test_ConnectToDBRaisesRejectedCredentials(validDBConnection):
    validDBConnection.PASSWORD = "Invalid Password"
    with pytest.raises(pymysql.err.OperationalError) as e:
        validDBConnection.connect()
    if (e.value.args[0] == 1045):
        assert True
    else:
        assert False

def test_ConnectToDBRaisesRejectedHost(validDBConnection):
    validDBConnection.HOST = "Invalid Host"
    with pytest.raises(pymysql.err.OperationalError) as e:
        validDBConnection.connect()
    if (e.value.args[0] == 2003):
        assert True
    else:
        assert False


def test_InsertUser(validDBConnection, validUser):
    validDBConnection.connect()
    validDBConnection.insertUser(validUser)
    insertedUser = validDBConnection.getUser(validUser.USERNAME)
    validDBConnection.deleteUser(validUser.USERNAME)
    assert insertedUser.USERNAME == validUser.USERNAME

def test_InsertAlbum(validDBConnection, validAlbum):
    validDBConnection.connect()
    validDBConnection.insertAlbum(validAlbum.title, validAlbum.userCreated)

    insertedAlbum = validDBConnection.getAlbum(validAlbum.title)
    validDBConnection.deleteAlbum(validAlbum.title)
    assert insertedAlbum.title == validAlbum.title

def test_IPInsertFailedAttempt(validDBConnection):
    ip = "1.1.1.1"
    validDBConnection.connect()
    validDBConnection.ipFailedAttempt(ip)
    numOfAttempts = validDBConnection.getIPFailedAttempts(ip)
    validDBConnection.deleteIP(ip)
    assert numOfAttempts == 1

def test_InsertPhotoIntoAlbum(validDBConnection, validAlbum):
    photoHash = "testPhotoHash"
    validDBConnection.connect()
    exifValues = ["" for x in range(12)]
    validDBConnection.insertAlbum(validAlbum.title, validAlbum.userCreated)
    validDBConnection.insertPhoto(photoHash, "/test/path", exifValues, "testYear", "testMonth", "testDay", 1111)
    validDBConnection.insertPhotoIntoAlbum(photoHash, validAlbum.title)
    
    photosInAlbum = validDBConnection.getAllPhotosInAlbum(validAlbum.title)
    validDBConnection.deleteAlbum(validAlbum.title)
    validDBConnection.deletePhotoFromDB(photoHash)
    assert len(photosInAlbum) == 1
    




def deleteUser(dbConn, user):
    dbConn.connect()
    validDBConnection.deleteUser(user.USERNAME)
