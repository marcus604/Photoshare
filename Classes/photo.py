


class Photo:

    EXIF_TAGS=["Image Make", "Image Model", "EXIF LensModel", "Exif Flash", "Image DateTime", "EXIF ISOSpeedRatings",
            "EXIF MaxApertureValue", "EXIF FocalLength", "EXIF ExifImageWidth", 
            "EXIF ExifImageLength", "EXIF ExposureTime", "EXIF Sharpness", "Image Orientation"]
    
    IMAGE_MAKE = ''
    IMAGE_MODEL = ''
    LENS_MODEL = ''
    FLASH = ''
    DATETIME = ''
    ISO = ''
    APERTURE = ''
    FOCAL_LENGTH = ''
    WIDTH = ''
    LENGTH = ''
    EXPOSURE_TIME = ''
    SHARPNESS = ''
    ORIENTATION = ''
    FILE_NAME = ''

    def __init__(self, fileName):
        self.FILE_NAME = fileName
