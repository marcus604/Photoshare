

	#Endian			1 Byte; 0 = Little, 1 = Big
	#Version		8 Bytes;	0-255
	#Instruction	4 Bytes; 0 = Handshake, 1 = Pull, 2 = Push, 99 = Error
	#Length			8 Bytes
class psMessage:
	
    def __init__(self, endian, version, instruction, length, data):
        #Create object from either strings, or byte code. 
        #Essentially overloading the constructor
        self.endian = endian                #String
        self.version = version              #Int
        self.instruction = instruction      #Int
        self.length = length                #Int
        self.data = data                    #String
        
		

    def fromString(self, rawMsg):
        self.endian = rawMsg[0]
        self.version = rawMsg[1:2]
        self.instruction = rawMsg[3:4]
        self.length = rawMsg[5:6]
        self.data = rawMsg[7:]

    def fromByteString(self, endian, version, instruction, length, data):
        self.endian = endian
        self.version = version
        self.instruction = instruction
        self.data = data
        self.length = length

    def getByteString(self):
        version = self.padZero(self.version)
        instruction = self.padZero(self.instruction)
        length = self.padZero(self.length)
        
        message = self.endian               
        message += str(version)				       
        message += str(instruction)			           
        message += str(length)				            
        message += self.data			   
        return message.encode('utf-8')

    def stripToken(self):
        self.data = str(self.data)[16:]

    

    def formatLength(self):
        strVal = str(self.length)
        return strVal[2] + strVal[3]

    def formatVersion(self):
        strVal = str(self.version)
        return strVal[0] + strVal[2]

    def formatEndian(self):
        if self.endian == b'l':
            return "Little"
        else:	# b'b'
            return "Big"

    @staticmethod
    def padZero(data):
        if data < 10:
            return f'{data:02}'
        return str(data)