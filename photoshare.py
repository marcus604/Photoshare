from flask import Flask, render_template, url_for, flash, redirect, send_from_directory, g
from forms import AddDeviceForm
import os
from classes.DBConnection import dbConnection
import configparser
from argon2 import PasswordHasher
import argon2
from utils.log import getConsoleHandler, getFileHandler, getLogger

import logging
import logging.handlers as handlers
import time

app = Flask(__name__)

psLogger = getLogger(__name__)

app.config['SECRET_KEY'] = "138652676d4f2563fba469a798a4186c"
LIBRARY_DIR = "Library/thumbnails/"
ALL_EXTENSIONS = [".jpg", ".png", ".jpeg"]

#Recursively finds files in IMPORT_DIR with supported extensions	
def collectLibraryThumbnails():
    return [os.path.join(r, fn) for r, ds, fs in os.walk(LIBRARY_DIR) for fn in fs if any(fn.endswith(ext) for ext in ALL_EXTENSIONS)]

def getDBConnection(settings):
    try:
        db = dbConnection(settings)
        db.connect()
    except Exception as e:
        psLogger.error("Couldnt connect to database")
        return False
    return db
     

def getSettings():
    psLogger.debug("Getting settings")
    settings = configparser.ConfigParser()
    settings._interpolation = configparser.ExtendedInterpolation()
    settingsSet = settings.read('settings.ini')
    if settingsSet == []:
        psLogger.error("Settings file not found")
        return False
    return settings

@app.before_first_request
def _run_on_start():
    psLogger.debug("First request")
    

@app.route("/")
@app.route("/home")
def home():
    psLogger.debug("Loaded home page")
    settings = getSettings()
    if settings is False:
        return render_template('error.html', error="No settings file")
    dbConnection = getDBConnection(settings)
    if dbConnection is False:
        return render_template('error.html', error="Failed to connect to database")
    
    imagePaths = dbConnection.getAllPhotoPaths()   #Get all photos
    # for image in imagePaths:
    #     print(image)
    return render_template('home.html', imagePaths=imagePaths)


@app.route("/thumbnails/<path:filename>")
def getImageThumbnail(filename):
    return send_from_directory("Library/thumbnails/", filename)

@app.route("/masters/<path:filename>")
def getImageMaster(filename):
    return send_from_directory("Library/masters/", filename)

@app.route("/albums/<title>")
def getAlbum(title):
    return render_template('admin.html', title="Admin")

@app.route("/albums")
def albums():
    psLogger.debug("Loaded albums page")
    settings = getSettings()
    if settings is False:
        return render_template('error.html', error="No settings file")
    dbConnection = getDBConnection(settings)
    if dbConnection is False:
        return render_template('error.html', error="Failed to connect to database")
    
    albums = dbConnection.getAllAlbums()   #Get all photos
    covers = dbConnection.getAlbumCovers(albums)
    index = 0
    for album in albums:
        album['coverPhoto'] = covers[index]
        index += 1
    return render_template('albums.html', title="Albums", albums=albums, covers=covers)

@app.route("/admin")
def admin():
    psLogger.debug("Loaded admin page")
    return render_template('admin.html', title="Admin")

@app.route("/add_device", methods=['GET', 'POST'])
def addDevice():
    form = AddDeviceForm()
    if form.validate_on_submit():
        flash(f'Device added with name {form.devicename.data}!', 'success')
        psLogger.debug("Added device")
        return redirect(url_for('home'))
    return render_template("add_device.html", title="Add Device", form=form)



    

if __name__ == "__main__":

    app.run(debug=True)
    





    

