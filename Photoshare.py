from flask import Flask, render_template, url_for, flash, redirect, send_from_directory
from forms import AddDeviceForm
import os
from DBConnection import dbConnection
import configparser
from argon2 import PasswordHasher
import argon2
import logging

app = Flask(__name__)

logging.basicConfig(filename='photoshare.log',level=logging.INFO)
logger = logging.getLogger(__name__)

app.config['SECRET_KEY'] = "138652676d4f2563fba469a798a4186c"
LIBRARY_DIR = "../../../Photos/Library/thumbnails/"
ALL_EXTENSIONS = [".jpg", ".png", ".jpeg"]

#Recursively finds files in IMPORT_DIR with supported extensions	
def collectLibraryThumbnails():
    return [os.path.join(r, fn) for r, ds, fs in os.walk(LIBRARY_DIR) for fn in fs if any(fn.endswith(ext) for ext in ALL_EXTENSIONS)]

@app.route("/")
@app.route("/home")
def home():
    settings = configparser.ConfigParser()
    settings._interpolation = configparser.ExtendedInterpolation()
    settingsSet = settings.read('settings.ini')
    if settingsSet == []:
            logger.error("Settings file not found")
    
    dbConn = dbConnection(settings)
    dbConn.connect()
    imagePaths = dbConn.getAllPhotoPaths()   #Get all photos
    # for image in imagePaths:
    #     print(image)
    return render_template('home.html', imagePaths=imagePaths)


@app.route("/thumbnails/<path:filename>")
def getImageThumbnail(filename):
    return send_from_directory("../../../Photos/Library/thumbnails/", filename)

@app.route("/masters/<path:filename>")
def getImageMaster(filename):
    return send_from_directory("../../../Photos/Library/masters/", filename)

@app.route("/albums/<title>")
def getAlbum(title):
    return render_template('admin.html', title="Admin")

@app.route("/albums")
def albums():
    settings = configparser.ConfigParser()
    settings._interpolation = configparser.ExtendedInterpolation()
    settingsSet = settings.read('settings.ini')
    if settingsSet == []:
            logger.error("Settings file not found")
    
    dbConn = dbConnection(settings)
    dbConn.connect()
    albums = dbConn.getAllAlbums()   #Get all photos
    covers = dbConn.getAlbumCovers(albums)
    index = 0
    for album in albums:
        album['coverPhoto'] = covers[index]
        index += 1
    return render_template('albums.html', title="Albums", albums=albums, covers=covers)

@app.route("/admin")
def admin():
    return render_template('admin.html', title="Admin")

@app.route("/add_device", methods=['GET', 'POST'])
def addDevice():
    form = AddDeviceForm()
    if form.validate_on_submit():
        flash(f'Account created for {form.devicename.data}!', 'success')
        return redirect(url_for('home'))
    return render_template("add_device.html", title="Add Device", form=form)



    

if __name__ == "__main__":    
    app.run(debug=True)
    

    

    

