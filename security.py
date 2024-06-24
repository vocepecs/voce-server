import os
from cryptography.fernet import Fernet



class Criptography():
    def __init__(self):
        self.secret_key =  os.environ.get('FERNET_KEY')
        self.cipher_suite = Fernet(self.secret_key)
    
    def encrypt(self, text):
        return self.cipher_suite.encrypt(text.encode()).decode()
    
    def decrypt(self, text):
        return self.cipher_suite.decrypt(text.encode()).decode()


