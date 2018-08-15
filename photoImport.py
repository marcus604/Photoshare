#Photo Importer

import pymysql
import exifread
import time
import datetime
import os, errno
import shutil
import ntpath
import sys
import hashlib
from pathlib import Path
from multiprocessing import Pool 
from PIL import Image
from enum import Enum


class NoFilesToImport(Exception):
    pass

class DuplicatePhotoFound(Exception):
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

#splits it in case its a large file (ie. video)
def md5Hash(filename):
    h = hashlib.md5()
    with open(filename, 'rb', buffering=0) as f:
        for b in iter(lambda : f.read(128*1024), b''):
            h.update(b)
    return h.hexdigest()

#Requests all rows from current db, returns list of just md5 hash values
def getExistingHashes(sqlConnection):
    hashes = []
    try:
        with connection.cursor() as cursor:
            sql = "SELECT `md5Hash` FROM `photos`"
            cursor.execute(sql)
            result = cursor.fetchall()
            for row in result:
                hashes.append(row['md5Hash'])
            cursor.close ()
    except BaseException:
        pass
    finally:
        return hashes
    

    
        

def connectSQL():
    return pymysql.connect(host='localhost',
                             user='root',
                             password='thisIsMySQLPassword',
                             db='photoshare',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


startTime = time.time()

#CONSTANTS
imageExtensions=[".jpg", ".png", ".tiff", ".gif", ".jpeg"]
videoExtensions=[".mp4", ".mov", ".avi", ".mkv"]

#Logging Variables
photosImported = 0
duplicatesSkipped = 0
importErrors = 0
nonSupportedFilesSkipped = 0

#Should split up tags for videos
exifTags=["Image Make", "Image Model", "EXIF LensModel", "Exif Flash", "Image DateTime", "EXIF ISOSpeedRatings",
            "EXIF MaxApertureValue", "EXIF FocalLength", "EXIF ExifImageWidth", 
            "EXIF ExifImageLength", "EXIF ExposureTime", "EXIF Sharpness", "Image Orientation"]

#need to scan whole folder
#ask user/grab from config, the directory to use to store photos
libraryDir = Path("Library/")

#Do I have permission, is there enough space, need to catch this
if not os.path.exists(libraryDir):
    os.makedirs(libraryDir)

#ask user/grab from config, the directory to use to auto import photos

try:
    file_list = collectFilesToImport('Import/')
except NoFilesToImport:
    print('No files found to import')
    print ('The script took {0} second !'.format(time.time() - startTime))
    os._exit(0)


    



#Need to catch this
#Connect to sql host
#Need to move this to a config file
try:
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='thisIsMySQLPassword',
                             db='photoshare',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
#Need to handle when no database named photos
except:
    print("Could not connect to mysql")
    os._exit(0)


exifValues=[]


#should test to see if its faster to grab all hashes and compare OR OR OR
    #go through all the processing first (grab exif, thumbnail) and then try to insert it and catch duplicate primary key
hashes = getExistingHashes(connection)

for photoPath in file_list:
    if photoPath.suffix.lower() in imageExtensions:
        mediaType=MediaType.IMG
    elif photoPath.suffix.lower() in videoExtensions:       #Need to test other video extensions
        mediaType=MediaType.VID
    else:
        nonSupportedFilesSkipped += 1
        continue
    

    currentPhotoHash = md5Hash(photoPath)

    #Check for duplicates
    if hashes:  #Skip if no previous photos
        duplicate = False
        for i in hashes:
            if i == currentPhotoHash:
                duplicate = True
                break

        if duplicate == True:
            duplicatesSkipped += 1
            continue
    
    
    #Check if trying to import duplicates
    hashes.append(currentPhotoHash)
    

    f = open(photoPath, "rb")

    try:
        tags = exifread.process_file(f)
    except OSError as e:
        print(e)
        print(photoPath)
    
    #Collect necessary EXIF Data, cast all of it to a string
    photoPath = str(photoPath)
    

    #loop through tags, if null, add empty string
    for tag in exifTags:
        try:
            exifValues.append(str(tags[tag]))
        except (KeyError, NameError):
            exifValues.append("")
    
    #Extract year/month/day from exif data, if no date available, use todays
    if exifValues[4] != '':
        date = exifValues[4].split(" ", 1)
        year,month,day = date[0].split(":")
        
    else:
        now = datetime.datetime.now()
        year = str(now.year)
        month = '{:02d}'.format(now.month)
        day = '{:02d}'.format(now.day)


    newDirPath = Path(str(libraryDir) + "/" + year + "/" + month + "/" + day + "/")
    newThumbnailPath = Path(str(libraryDir) + "/thumbnails/" + year + "/" + month + "/" + day + "/")

    #Do I have permission, is there enough space, need to catch this
    if not os.path.exists(newDirPath):
        os.makedirs(newDirPath)
        os.makedirs(newThumbnailPath)

    shutil.copy2(photoPath, newDirPath)

    #Only works with windows, probably
    newFilePath = Path(str(libraryDir) + "/" + year + "/" + month + "/" + day + "/" + str(path_leaf(photoPath)))
    thumbnailPath = Path(str(libraryDir) + "/thumbnails/" + year + "/" + month + "/" + day + "/" + str(path_leaf(photoPath)))


    
    #Determines orientation and creates thumbnail of image in mirrored dir structure
    if mediaType.value == 1:
        image = Image.open(photoPath)
        #print(str(path_leaf(photoPath)))
        #print(exifValues[12])
        
        image.thumbnail((400, 400))

        #Should throw more photos through this
        if exifValues[12] == "Rotated 90 CW":
            image = image.rotate(270, expand=True)
        elif exifValues[12] == "Rotated 90 CCW":
            image = image.rotate(90, expand=True)
        elif exifValues[12] == "Rotated 180":
            image = image.rotate(180, expand=True)
        elif exifValues[12] == "Mirrored horizontal":
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        elif exifValues[12] == "Mirrored vertical":
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
        elif exifValues[12] == "Mirrored horizontal then rotated 90 CCW":
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
            image = image.rotate(90, expand=True)
        elif exifValues[12] == "Mirrored horizontal then rotated 90 CW":
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
            image = image.rotate(270, expand=True)
            
            
        image.save(thumbnailPath)

    newFilePath = year + "/" + month + "/" + day + "/" + str(path_leaf(photoPath))
    
    try:

        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `photos` (`md5Hash`, `make`, `model`, `lensModel`, `flash`, `dateTime`, `ISO`, `aperture`, `focalLength`, `width`, `height`, `exposureTime`, `sharpness`, `type`, `dir`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (currentPhotoHash, exifValues[0], exifValues[1], exifValues[2], exifValues[3], exifValues[4], exifValues[5], exifValues[6], exifValues[7], exifValues[8], exifValues[9], exifValues[10], exifValues[11], mediaType.value, newFilePath))

            # connection is not autocommit by default. So you must commit to save
            # your changes.
            connection.commit()
            photosImported += 1
    except pymysql.err.DataError:   #Data too long
        importErrors += 1
        pass
    except pymysql.err.IntegrityError:  #Duplicate Primary Key
        importErrors += 1
        pass
    except pymysql.err.ProgrammingError: #Table doesnt exist
        importErrors += 1
        pass
    #except BaseException:
    #    pass
    finally:
        exifValues = []
        

    
        
#Need to close open file

connection.close()
#tags = exifread.process_file(f, details=False) Process less

print('Imported {0} photos'.format(photosImported))
print('Skipped {0} photos'.format(duplicatesSkipped))
print('Error with {0} photos'.format(importErrors))
print('Skipped {0} non supported files'.format(nonSupportedFilesSkipped))
print ('The script took {0} second !'.format(time.time() - startTime))













