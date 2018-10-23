from flask import Flask, render_template, url_for, flash, redirect, send_from_directory, g
from forms import AddDeviceForm
import os
from classes.DBConnection import dbConnection
from classes.Server import Server
from classes.ServerConnection import ServerStoppedByUser
from classes.User import User
from classes.FileHandler import FileHandler
import configparser
from argon2 import PasswordHasher
from utils.log import getConsoleHandler, getFileHandler, getLogger
import argon2
import threading
import multiprocessing
import logging
import sys


#from utils.log import getConsoleHandler, getFileHandler, getLogger

import logging
import logging.handlers as handlers
import time

app = Flask(__name__)



app.config['SECRET_KEY'] = "138652676d4f2563fba469a798a4186c"
LIBRARY_DIR = "Library/thumbnails/"
ALL_EXTENSIONS = [".jpg", ".png", ".jpeg"]

psLogger = getLogger(__name__, "logs/photoshare.log")
psLogger.debug("Starting")



def getSettings():
    settings = configparser.ConfigParser()
    settings._interpolation = configparser.ExtendedInterpolation()
    settingsSet = settings.read('settings.ini')
    if settingsSet == []:
        return False
    return settings

def getDBConnection(settings):
    try:
        db = dbConnection(settings)
        db.connect()
    except Exception as e:
        print("heree")
        return False
    return db
     

settings = getSettings()    #Should verify settings
if settings is False:
    psLogger.error("Could not find settings")
    #Should stop and quit
psLogger.debug("Loaded settings")
dbConnection = getDBConnection(settings)
if dbConnection is False:
    psLogger.error("Could not connect to database")
    #Should stop and quit
if settings.getboolean('MAIN', 'firstRun'):
    dbConnection.createUserTable()
    dbConnection.createPhotoTable()
    dbConnection.createAlbumTable()
    dbConnection.createPhotoAlbumsTable()
    dbConnection.createIPAddressTable()
    settingsFile = "settings.ini"
    settingsFP = open(settingsFile, "w")
    settings.set('MAIN', 'firstRun', 'False')
    settings.write(settingsFP)
    settingsFP.close()

psLogger.debug("Connected to database")

#Instantiate server | Allows control from flask of server object (ie, starting, stopping, restarting)
#Server handles the socket server and file importing
server = None

userRequestedStop = False


def serverWorker():
    while True:
        global server
        global settings
        global userRequestedStop
        time.sleep(1)
        psLogger.debug("New server worker")
        try:
            if userRequestedStop is False:
                settings = getSettings()    #Should verify settings
                if settings is False:
                    psLogger.error("Could not find settings")
                    break
                server = Server(settings)
                server.run()
        except ServerStoppedByUser:
            psLogger.debug("Server stopped by user")
        except Exception as e:
            psLogger.error("Server encountered error: {}".format(e))
        server = None
        time.sleep(5)

t = threading.Thread(target=serverWorker)
t.start()

#Recursively finds files in IMPORT_DIR with supported extensions	
def collectLibraryThumbnails():
    return [os.path.join(r, fn) for r, ds, fs in os.walk(LIBRARY_DIR) for fn in fs if any(fn.endswith(ext) for ext in ALL_EXTENSIONS)]



def displayStatus(newStatus=None):
    status = (f'Server Status: Not Running')
    if server:
        if server.connection:
            if server.connection.listenSock != '':
                status = (f'Server Status: Waiting for connection')
            if server.connection.clientSock != '':
                status = (f'Client {server.connection.clientAddress[0]} connected')
    flash(f'{status}', 'secondary')




@app.before_first_request
def _run_on_start():
    psLogger.debug("First request")
    

@app.route("/")
@app.route("/home")
def home():
    psLogger.debug("Loaded home page")
    
    if settings is False:
        return render_template('error.html', error="No settings file")
    
    if dbConnection is False:
        return render_template('error.html', error="Failed to connect to database")
    
    imagePaths = dbConnection.getAllPhotoPaths()   #Get all photos
    # for image in imagePaths:
    #     print(image)
    return render_template('home.html', imagePaths=imagePaths)


@app.route("/thumbnails/<path:filename>")
def getImageThumbnail(filename):
    return send_from_directory("Library/photos/thumbnails/", filename)

@app.route("/masters/<path:filename>")
def getImageMaster(filename):
    return send_from_directory("Library/photos/masters/", filename)

@app.route("/albums/<title>")
def getAlbum(title):
    imagePaths = dbConnection.getAllPhotosInAlbum(title)  #Get all photos
    return render_template('album.html', title=title, imagePaths=imagePaths)

@app.route("/albums")
def albums():
    psLogger.debug("Loaded albums page")
    #settings = getSettings()
    #if settings is False:
        #return render_template('error.html', error="No settings file")
    #dbConnection = getDBConnection(settings)
    if dbConnection is False:
        return render_template('error.html', error="Failed to connect to database")
    
    albums = dbConnection.getAllAlbums()   #Get all photos
    covers = dbConnection.getAlbumCovers(albums)
    if len(albums) is not len(covers):
        return render_template('error.html', error="Album database corrupt")
    index = 0
    for album in albums:
        album['coverPhoto'] = covers[index]
        index += 1
    return render_template('albums.html', title="Albums", albums=albums, covers=covers)



@app.route("/admin")
def admin():
    psLogger.debug("Loaded admin page")
    displayStatus()
    return render_template('admin.html', title="Admin")

@app.route("/startServer")
def startServer():
    psLogger.debug("Start server button clicked")
    global userRequestedStop
    if userRequestedStop is False:
        psLogger.debug("Server already running")
        status = (f'Server already running')
        flash(f'{status}', 'info')
        return redirect(url_for('admin', title="Admin"))
    userRequestedStop = False
    status = (f'Starting Server')
    flash(f'{status}', 'info')
    return redirect(url_for('admin', title="Admin"))

@app.route("/restartServer")
def restartServer():
    psLogger.debug("Restarting server")
    global userRequestedStop
    if userRequestedStop:
        psLogger.debug("Server already stopped")
        status = (f'Server already stopped')
        flash(f'{status}', 'warning')
        return redirect(url_for('admin', title="Admin"))
    server.userRequestedStop()
    status = (f'Restarting Server')
    flash(f'{status}', 'info') 
    return redirect(url_for('admin', title="Admin"))

@app.route("/stopServer")
def stopServer():
    global userRequestedStop
    psLogger.debug("Stopping server")
    if userRequestedStop or (server is None):
        psLogger.debug("Server already stopped")
        status = (f'Server already stopped')
        flash(f'{status}', 'warning')
        return redirect(url_for('admin', title="Admin"))
    server.userRequestedStop()
    userRequestedStop = True
    status = (f'Stopping Server')
    flash(f'{status}', 'warning')
    return redirect(url_for('admin', title="Admin"))

@app.route("/resetServer")
def resetServer():
    psLogger.debug("Reseting server")
    global userRequestedStop
    if server:
        server.fileHandler.resetLibrary()
        server.userRequestedStop()
        dbConnection.resetTables()
        userRequestedStop = True
        status = (f'Server Reset (Clients will need to be reset as well)')
        flash(f'{status}', 'danger')
    else:
        status = (f'Server Reset Failed')
        flash(f'{status}', 'danger')
    return redirect(url_for('admin', title="Admin"))

@app.route("/add_device", methods=['GET', 'POST'])
def addDevice():
    global dbConnection
    form = AddDeviceForm()
    if form.validate_on_submit():
        salt, hash = User.generateUserPassword(form.password.data)
        newDevice = User(form.devicename.data, hash, salt)
        dbConnection.insertUser(newDevice)
        flash(f'Device added with name {form.devicename.data}!', 'success')
        psLogger.debug("Added device")
        return redirect(url_for('admin'))
    return render_template("add_device.html", title="Add Device", form=form)



    

if __name__ == "__main__":
    app.run(debug=True)
    





    

