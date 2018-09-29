from pathlib import Path
import os
import pdb
import logging
import hashlib
import exifread
import datetime
import shutil
import ntpath
import fnmatch
from PIL import Image
from pathlib import Path

logging.basicConfig(filename='photoshare.log',level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('PIL.Image').setLevel(logging.WARNING)
logging.getLogger('exifread').setLevel(logging.WARNING)

class FileHandler:
	

	#CONSTANTS
	IMAGE_EXTENSIONS = 	[".jpg", ".png", ".tiff", ".gif", ".jpeg"]
	VIDEO_EXTENSIONS = 	[".mp4", ".mov", ".avi", ".mkv"]
	ALL_EXTENSIONS = 	IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

	#Ensures case insesitivity
	numOfExtensions = len(ALL_EXTENSIONS)	
	for i in range(0, numOfExtensions):
		ALL_EXTENSIONS.append(ALL_EXTENSIONS[i].upper())

	

	
	EXIF_TAGS=["Image Make", "Image Model", "EXIF LensModel", "Exif Flash", "Image DateTime", "EXIF ISOSpeedRatings",
            "EXIF MaxApertureValue", "EXIF FocalLength", "EXIF ExifImageWidth", 
            "EXIF ExifImageLength", "EXIF ExposureTime", "EXIF Sharpness", "Image Orientation"]
	
	LIBRARY_DIR = ''
	IMPORT_DIR = ''

	def __init__(self, libraryDir, importDir):
		self.LIBRARY_DIR = Path(libraryDir)
		self.IMPORT_DIR = Path(importDir)


	#Very likely user could already have folders created
	#Library folder should be empty to start
	def createDirectories(self):
		if not os.path.exists(self.LIBRARY_DIR):
			os.makedirs(self.LIBRARY_DIR)
		if os.listdir(self.LIBRARY_DIR):
			raise LibraryPathNotEmptyError
		if not os.path.exists(self.IMPORT_DIR):
			os.makedirs(self.IMPORT_DIR)



	def importPhotos(self, dbConn):
		logger.info("Starting photo import")
		#Logging Variables
		photosImported = 0
		duplicatesSkipped = 0
		corruptPhotos = 0

		filesToImport = self.collectFilesToImport()
		if not filesToImport:
			logger.info("No photos to import")
			return
		
		#Get existing hashes to check for duplicates
		hashes = dbConn.getAllExistingHashes()

		progressCount = 1
		#Loop through all supported files
		for currentPhotoPath in filesToImport:
			print("Processing file {} of {}".format(progressCount, len(filesToImport)))
			progressCount += 1
			exifValues=[]
			currentPhotoHash = self.md5Hash(currentPhotoPath)

			if hashes:	#Anything to check against
				duplicate = False
				for h in hashes:
					if h == currentPhotoHash:
						duplicate = True
						break
				if duplicate:				#Automatically skips duplicate, could add setting that would give user control
					duplicatesSkipped += 1
					continue
			
			#Check that batch of photos being imported doesnt have duplicates
			#Doesnt require asking db for hashes again
			hashes.append(currentPhotoHash)

			photoFile = open(currentPhotoPath, "rb")
			
			exifValues = self.getExifValues(photoFile)

			year, month, day = self.getPhotoDate(exifValues)

			photoPath = str(currentPhotoPath)

			newDirPath = Path(str(self.LIBRARY_DIR) + "/masters/" + year + "/" + month + "/" + day + "/")
			newThumbnailPath = Path(str(self.LIBRARY_DIR) + "/thumbnails/" + year + "/" + month + "/" + day + "/")
			

			#Do I have permission, is there enough space, need to catch this
			if not os.path.exists(newDirPath):
				os.makedirs(newDirPath)
				os.makedirs(newThumbnailPath)

			#Copies file to proper library location
			shutil.copy2(photoPath, newDirPath)

			#Creates thumbnail with proper orientation
			thumbnailPath = Path(str(self.LIBRARY_DIR) + "/thumbnails/" + year + "/" + month + "/" + day + "/" + str(self.path_leaf(photoPath)))
			thumbnail = self.generateImageThumbnail(currentPhotoPath, exifValues)#.save(thumbnailPath)
			if not thumbnail:
				corruptPhotos += 1
				continue
			thumbnail.save(thumbnailPath)

			newFilePath = year + "/" + month + "/" + day + "/" + str(self.path_leaf(photoPath))
			dbConn.insertPhoto(currentPhotoHash, newFilePath, exifValues)
			photosImported += 1

		logger.info("Imported {} photos".format(photosImported))
		logger.info("Skipped {} duplicates".format(duplicatesSkipped))
		logger.info("Found {} corrupt photos".format(corruptPhotos))

	
	def getPhotoPath(self, localPath):
		return str(self.LIBRARY_DIR) + "/masters/" + localPath
		

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

	def getPhotoDate(self, exifValues):
		#Extract year/month/day from exif data, if no date available, use todays
		if exifValues[4] != '':
			date = exifValues[4].split(" ", 1)
			year,month,day = date[0].split(":")
			
		else:
			now = datetime.datetime.now()
			year = str(now.year)
			month = '{:02d}'.format(now.month)
			day = '{:02d}'.format(now.day)

		return year, month, day

	def generateImageThumbnail(self, photo, exifValues):
		try:
			image = Image.open(photo)
		except OSError:			#File is not an image
			return False
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

		
		return image
	#this should work cross platform
	#grabs just file name, used to create new file path
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



class LibraryPathNotEmptyError(Exception):
	pass

class NoPhotosToImport(Exception):
	pass
