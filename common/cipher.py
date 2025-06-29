from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64

# for mac 
# python3 -m venv venv
# source venv/bin/activate
# pip install pycryptodome

class AESCipher:
    def __init__(self, key: bytes):
        """ 注意 key 的長度 16/24/32 bytes """
        self.key = key

    def encrypt(self, raw: str) -> str:
        raw_bytes = raw.encode('utf-8')
        cipher = AES.new(self.key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(raw_bytes, AES.block_size))
        return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')

    def decrypt(self, enc: str) -> str:
        enc_bytes = base64.b64decode(enc)
        iv = enc_bytes[:16]
        ct = enc_bytes[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        raw_bytes = unpad(cipher.decrypt(ct), AES.block_size)
        return raw_bytes.decode('utf-8')