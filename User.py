from argon2 import PasswordHasher
import secrets      #Used to generate salt
import time

class user:

    USERNAME = ''
    HASH = ''
    SALT = ''
    lastLoggedIn = ''
    lastSync = ''
    token = ''

    def __init__(self):
        self.USERNAME = self.generateUserName()
        self.SALT, self.HASH = self.generatePassword()

    def generateUserName(self):
        userNameValid = False
        while not userNameValid:
            print("Create a New User:")
            userName = input("Name: ")
            if len(userName) > 40:
                print("Username cannot be longer than 40 characters")
            else:
                if ":" not in userName:
                    userNameValid = True
                else:
                    print("Username cannot contain the character ':'")
        return userName

    def generatePassword(self):
        ph = PasswordHasher()
        passwordValid = False
        while not passwordValid:
            password = input("Password: ")
            if len(password) > 64:
                print("Password cannot be longer than 64 characters")
            else:
                passwordVerify = input("Enter Password Again: ")
                if password == passwordVerify:
                    passwordValid = True
                else:
                    print("Passwords Do Not Match")
        salt = secrets.token_hex(32)
        hash = ph.hash(password + salt)
        return salt, hash
        
    def loggedIn(self, token):
        self.lastLoggedIn = time.time()
        self.token = token

    def synced(self):
        self.lastSync = time.time()

    def getUserName(self):
        return self.USERNAME

    def getSalt(self):
        return self.SALT
    
    def getHash(self):
        return self.HASH

    def getLastLoggedIn(self):
        return self.lastLoggedIn

    def getLastSync(self):
        return self.lastSync
    
    def getToken(self):
        return self.token

    
