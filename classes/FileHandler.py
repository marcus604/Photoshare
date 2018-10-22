from pathlib import Path
import os
import pdb
import logging
import hashlib
import exifread
from datetime import *
from classes.DBConnection import dbConnection
from utils.log import getConsoleHandler, getFileHandler, getLogger
import time
import shutil
import ntpath
import fnmatch
from PIL import Image
from pathlib import Path

psLogger = getLogger(__name__, "logs/photoshare.log")
psLogger.debug("Loading Server class")
logging.getLogger('PIL.Image').setLevel(logging.WARNING)
logging.getLogger('exifread').setLevel(logging.WARNING)

class FileHandler:
	

	#CONSTANTS
	IMAGE_EXTENSIONS = 	[".jpg", ".png", ".jpeg"]
	#VIDEO_EXTENSIONS = 	[".mp4", ".mov", ".avi", ".mkv"]
	ALL_EXTENSIONS = 	IMAGE_EXTENSIONS #+ VIDEO_EXTENSIONS

	#Ensures case insesitivity
	numOfExtensions = len(ALL_EXTENSIONS)	
	for i in range(0, numOfExtensions):
		ALL_EXTENSIONS.append(ALL_EXTENSIONS[i].upper())

	

	
	EXIF_TAGS=["Image Make", "Image Model", "EXIF LensModel", "Exif Flash", "Image DateTime", "EXIF ISOSpeedRatings",
            "EXIF MaxApertureValue", "EXIF FocalLength", "EXIF ExifImageWidth", 
            "EXIF ExifImageLength", "EXIF ExposureTime", "EXIF Sharpness", "Image Orientation"]
	
	LIBRARY_DIR = ''
	IMPORT_DIR = ''
	TEMP_DIR = ''

	def __init__(self, libraryDir, importDir, tempDir):
		self.LIBRARY_DIR = Path(libraryDir)
		self.IMPORT_DIR = Path(importDir)
		self.TEMP_DIR = Path(tempDir)


	#Very likely user could already have folders created
	#Library folder should be empty to start
	#def createDirectories(self):
		#if not os.path.exists(self.LIBRARY_DIR):
		#	os.makedirs(self.LIBRARY_DIR)
		#if os.listdir(self.LIBRARY_DIR):
		#	raise LibraryPathNotEmptyError
		#if not os.path.exists(self.IMPORT_DIR):
		#	os.makedirs(self.IMPORT_DIR)
		#if not os.path.exists(self.TEMP_DIR):
		#	os.makedirs(self.TEMP_DIR)


	def importPhoto(self, dbConn, photoPath, timeStamp, hashes):

		exifValues=[]
		photoHash = self.md5Hash(photoPath)

		if hashes == True:		#Used for receiving individual photos from client
			#Get existing hashes to check for duplicates
			hashes = dbConn.getAllExistingHashes()

		if hashes:	#Anything to check against
				duplicate = False
				for h in hashes:
					if h == photoHash:
						raise ImportErrorDuplicate

		hashes.append(photoHash)
		
		photoFile = open(photoPath, "rb")
			
		exifValues = self.getExifValues(photoFile)

		if timeStamp:
			year, month, day, time = self.getPhotoDateFromClient(timeStamp)
		else:
			year, month, day, time = self.getPhotoDate(exifValues)

		photoPath = str(photoPath)

		newDirPath = Path(str(self.LIBRARY_DIR) + "/masters/" + year + "/" + month + "/" + day + "/")
		newThumbnailPath = Path(str(self.LIBRARY_DIR) + "/thumbnails/" + year + "/" + month + "/" + day + "/")
		
		thumbnail = self.generateImageThumbnail(photoPath, exifValues)#.save(thumbnailPath)
		if not thumbnail:
			raise ImportErrorPhotoInvalid

		#Do I have permission, is there enough space, need to catch this
		if not os.path.exists(newDirPath):
			os.makedirs(newDirPath)
			os.makedirs(newThumbnailPath)

		#Creates thumbnail with proper orientation
		thumbnailPath = Path(str(self.LIBRARY_DIR) + "/thumbnails/" + year + "/" + month + "/" + day + "/" + str(self.path_leaf(photoPath)))
		

		#Copies file to proper library location
		shutil.copy2(photoPath, newDirPath)

		
		thumbnail.save(thumbnailPath)

		newFilePath = year + "/" + month + "/" + day + "/" + str(self.path_leaf(photoPath))
		dbConn.insertPhoto(photoHash, newFilePath, exifValues, year, month, day, time)

		return hashes

	def updatePhoto(self, tmpPath, originalPath):
		fullPath = Path(str(self.LIBRARY_DIR) + "/masters/" + originalPath)
		thumbnailPath = Path(str(self.LIBRARY_DIR) + "/thumbnails/" + originalPath)
		
		thumbnail = self.updateImageThumbnail(tmpPath)
		if not thumbnail:
			raise ImportErrorPhotoInvalid		

		#Copies file to proper library location
		shutil.copy2(tmpPath, fullPath)		
		thumbnail.save(thumbnailPath)

	
	def importPhotos(self, settings):
		while True:
			dbConn = dbConnection(settings)
			dbConn.connect()
			#Logging Variables
			photosImported = 0
			duplicatesSkipped = 0
			invalidFiles = 0
			filesToImport = self.collectFilesToImport()
			if not filesToImport:
				time.sleep(10)
				continue
			
			#Get existing hashes to check for duplicates
			hashes = dbConn.getAllExistingHashes()

			progressCount = 1
			#Loop through all supported files
			for currentPhotoPath in filesToImport:
				#print("Processing file {} of {}".format(progressCount, len(filesToImport)))
				progressCount += 1
				try:
					hashes = self.importPhoto(dbConn, currentPhotoPath, None, hashes)
					photosImported += 1
				except ImportErrorDuplicate:
					duplicatesSkipped +=1
				except ImportErrorPhotoInvalid:
					invalidFiles += 1
				

			if photosImported != 0:
				psLogger.info("Imported {} photos".format(photosImported))
			if duplicatesSkipped != 0:
				psLogger.debug("Skipped {} duplicates".format(duplicatesSkipped))
			if invalidFiles != 0:
				psLogger.info("Skipped {} invalid files".format(invalidFiles))
			
			time.sleep(10)

	def resetLibrary(self):
		foldersToDelete = [self.TEMP_DIR, self.LIBRARY_DIR, self.IMPORT_DIR]
		for folder in foldersToDelete:
			for the_file in os.listdir(folder):
				file_path = os.path.join(folder, the_file)
				try:
					if os.path.isfile(file_path):
						os.unlink(file_path)
					elif os.path.isdir(file_path): shutil.rmtree(file_path)
				except Exception as e:
					print(e)

	def getTempFilePath(self, name):
		return str(self.TEMP_DIR) + "/" + name

	
	def getPhotoPath(self, localPath):
		return str(self.LIBRARY_DIR) + "/masters/" + localPath

	def getThumbnailPath(self, localPath):
		return str(self.LIBRARY_DIR) + "/thumbnails/" + localPath

	def getPhotoName(self, localPath):
		year,month,day,name = localPath.split("/")
		return name
	
	

	#Opens file and creates array for all tags supported
	def getExifValues(self, photo):
		try:
			tags = exifread.process_file(photo)
		except OSError as e:
			logging.error("Cannot open file")	
		
		exifValues = []

		#loop through tags, if null, add empty string
		for tag in self.EXIF_TAGS:
			try:
				exifValues.append(str(tags[tag]))
			except (KeyError, NameError):	
				exifValues.append("")
		
		return exifValues

	#Ex. 2018-09-13, 8:55 PM
	#Parses, strips comma, and converts to 24 hour
	def getPhotoDateFromClient(self, timeStamp):
		date = timeStamp.split(" ", 1)
		year,month,day = date[0].split("-")
		day = day[:-1]
		time = date[1]
		time = datetime.strptime(time, '%I:%M %p')
		time = time.strftime("%H:%M:%S")
		return year, month, day, time

	def getPhotoDate(self, exifValues):
		#Extract year/month/day from exif data, if no date available, use todays
		if exifValues[4] != '':
			date = exifValues[4].split(" ", 1)
			year,month,day = date[0].split(":")
			time = date[1]
			
		else:
			now = datetime.now()
			year = str(now.year)
			month = '{:02d}'.format(now.month)
			day = '{:02d}'.format(now.day)
			time = now.strftime("%H:%M:%S")
			

		return year, month, day, time

	def compressPhoto(self, path):
		photoFile = open(path, "rb")
			
		exifValues = self.getExifValues(photoFile)
		
		try:
			image = Image.open(path)
		except OSError:			#File is not an image
			return False

		image = self.keepPhotoOrientation(image, exifValues)

		return image

	def deletePhoto(self, localPath):
		fullPath = Path(str(self.LIBRARY_DIR) + "/masters/" + localPath)
		thumbnailPath = Path(str(self.LIBRARY_DIR) + "/thumbnails/" + localPath)
		try:
			os.remove(fullPath)
			os.remove(thumbnailPath)
		except OSError:
			return False
		return True

		
		
	def generateImageThumbnail(self, photo, exifValues):
		try:
			image = Image.open(photo)
		except OSError:			#File is not an image
			return False
		image.thumbnail((2400, 2400))

		image = self.keepPhotoOrientation(image, exifValues)
		
		return image
	
	def updateImageThumbnail(self, photo):
		try:
			image = Image.open(photo)
		except OSError:
			return False
		image.thumbnail((800, 800))

		return image

	def keepPhotoOrientation(self, image, exifValues):
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

		return image


	def path_leaf(self, path):
		head, tail = ntpath.split(path)
		return tail or ntpath.basename(head)

	#splits it in case its a large file (ie. video)
	def md5Hash(self, filename):
		h = hashlib.md5()
		with open(filename, 'rb', buffering=0) as f:
			for b in iter(lambda : f.read(128*1024), b''):
				h.update(b)
		return h.hexdigest()

	#Recursively finds files in IMPORT_DIR with supported extensions	
	def collectFilesToImport(self):
		return [os.path.join(r, fn) for r, ds, fs in os.walk(self.IMPORT_DIR) for fn in fs if any(fn.endswith(ext) for ext in self.ALL_EXTENSIONS)]


class ImportErrorPhotoInvalid(Exception):
	pass

class ImportErrorDuplicate(Exception):
	pass

class LibraryPathNotEmptyError(Exception):
	pass

class NoPhotosToImport(Exception):
	pass
