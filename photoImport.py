#Photo Importer

import pymysql
import exifread
import time
import datetime
import os, errno
import shutil
import ntpath
import sys
from pathlib import Path
from multiprocessing import Pool 
from PIL import Image
from enum import Enum


class NoFilesToImport(Exception):
    pass

class MediaType(Enum):
    IMG = 1
    VID = 2

#this should work cross platform
#grabs just file name, used to create new file path
def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def collectFilesToImport(dirToScan):
    rootDir = Path(dirToScan)
    #rootDir = Path("ImportTest/")
    #Need to specify only photos, and to traverse through other folders
    file_list = [f for f in rootDir.glob('**/*') if f.is_file()]

    #Nothing to import
    if not file_list:
        raise NoFilesToImport('There are no files to be imported')
    return file_list

def connectSQL():
    return pymysql.connect(host='localhost',
                             user='root',
                             password='Idagl00w',
                             db='photos',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)



#CONSTANTS
imageExtensions=[".jpg", ".png", ".tiff", ".gif"]
videoExtensions=[".mp4", ".mov", ".avi", ".mkv"]

#Should split up tags for videos
exifTags=["Image Make", "Image Model", "EXIF LensModel", "Exif Flash", "Image DateTime", "EXIF ISOSpeedRatings",
            "EXIF MaxApertureValue", "EXIF FocalLength", "EXIF ExifImageWidth", 
            "EXIF ExifImageLength", "EXIF ExposureTime", "EXIF Sharpness"]

#need to scan whole folder
#ask user/grab from config, the directory to use to store photos
libraryDir = Path("Library/")

#Do I have permission, is there enough space, need to catch this
if not os.path.exists(libraryDir):
    os.makedirs(libraryDir)

#ask user/grab from cofnig, the directory to use to auto import photos

file_list = collectFilesToImport('Import/')


    

#if file list empty, should quit

#Connect to sql host
#Need to move this to a config file
connection = pymysql.connect(host='localhost',
                             user='root',
                             password='Idagl00w',
                             db='photos',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


exifValues=[]

for photoPath in file_list:
    if photoPath.suffix.lower() in imageExtensions:
        mediaType=MediaType.IMG
    elif photoPath.suffix.lower() in videoExtensions:       #Need to test other video extensions
        mediaType=MediaType.VID
    else:
        continue
    
    print(mediaType.value)
    
    f = open(photoPath, "rb")

    tags = exifread.process_file(f)
    
    #Collect necessary EXIF Data, cast all of it to a string
    photoPath = str(photoPath)
    

    #loop through tags, if null, add empty string
    for tag in exifTags:
        try:
            exifValues.append(str(tags[tag]))
        except KeyError:
            exifValues.append("")
    
    #Extract year/month/day from exif data, if no date available, use todays
    if exifValues[4] != '':
        date = exifValues[4].split(" ", 1)
        year,month,day = date[0].split(":")
        
    else:
        now = datetime.datetime.now()
        year,month,day = str(now.year),str(now.month),str(now.day)

    newDirPath = Path(str(libraryDir) + "/" + year + "/" + month + "/" + day + "/")

    #Do I have permission, is there enough space, need to catch this
    if not os.path.exists(newDirPath):
        os.makedirs(newDirPath)

    shutil.copy2(photoPath, newDirPath)

    #Only works with windows, probably
    newFilePath = Path(str(libraryDir) + "/" + year + "/" + month + "/" + day + "/" + str(path_leaf(photoPath)))

    if mediaType.value == 1:
        #screws up portrait photos, puts them as landscape
        image = Image.open(photoPath)
        image.thumbnail((400, 400))
        image.save(newFilePath)

    newFilePath = year + "/" + month + "/" + day + "/" + str(path_leaf(photoPath))
    
    

    

    

    try:

        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `photos` (`dir`, `make`, `model`, `lensModel`, `flash`, `dateTime`, `ISO`, `aperture`, `focalLength`, `width`, `height`, `exposureTime`, `sharpness`, `type`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (newFilePath, exifValues[0], exifValues[1], exifValues[2], exifValues[3], exifValues[4], exifValues[5], exifValues[6], exifValues[7], exifValues[8], exifValues[9], exifValues[10], exifValues[11], mediaType.value))

            # connection is not autocommit by default. So you must commit to save
            # your changes.
            connection.commit()
    except pymysql.err.DataError:   #Data too long
        pass
    except pymysql.err.IntegrityError:  #Duplicate Primary Key
        pass
    #except BaseException:
    #    pass
    finally:
        exifValues = []

    
        
#Need to close open file

connection.close()
#tags = exifread.process_file(f, details=False) Process less

print("DONE DONE DONE")












