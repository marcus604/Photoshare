import logging
import sys
from logging.handlers import TimedRotatingFileHandler

FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def getConsoleHandler():
	consoleHandler = logging.StreamHandler(sys.stdout)
	consoleHandler.setFormatter(FORMATTER)
	return consoleHandler

def getFileHandler(logPath):
	file_handler = TimedRotatingFileHandler(logPath, when='midnight')
	file_handler.setFormatter(FORMATTER)
	return file_handler


def getLogger(loggerName, logPath):
	logger = logging.getLogger(loggerName)

	logger.setLevel(logging.DEBUG) # better to have too much log than not enough

	logger.addHandler(getConsoleHandler())
	logger.addHandler(getFileHandler(logPath))

	# with this pattern, it's rarely necessary to propagate the error up to parent
	logger.propagate = False

	return logger