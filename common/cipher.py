from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import uuid

# for mac
# python3 -m venv venv
# source venv/bin/activate
# pip install pycryptodome


class AESCipher:
    def __init__(self, key: bytes):
        """注意 key 的長度 16/24/32 bytes"""
        self.key = key

    def encrypt(self, raw: str) -> str:
        raw_bytes = raw.encode("utf-8")
        cipher = AES.new(self.key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(raw_bytes, AES.block_size))
        encode = base64.urlsafe_b64encode(cipher.iv + ct_bytes).decode("ascii")

        return encode.rstrip("=")

    def decrypt(self, enc: str) -> str:
        padding = "=" * (-len(enc) % 4)
        enc_bytes = base64.urlsafe_b64decode(enc + padding)
        iv = enc_bytes[:16]
        ct = enc_bytes[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        raw_bytes = unpad(cipher.decrypt(ct), AES.block_size)

        return raw_bytes.decode("utf-8")


class UUIDBase62Cipher:
    BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    LENGTH = 22  # UUID 128 bit = 22 base62 digits

    @classmethod
    def int_to_base62(cls, n):
        arr = []
        for _ in range(cls.LENGTH):
            n, r = divmod(n, 62)
            arr.append(cls.BASE62[r])
        return "".join(reversed(arr))

    @classmethod
    def base62_to_int(cls, s):
        n = 0
        for c in s:
            n = n * 62 + cls.BASE62.index(c)
        return n

    @classmethod
    def encode(cls, uuid_str):
        n = int(uuid.UUID(uuid_str))
        return cls.int_to_base62(n)

    @classmethod
    def decode(cls, base62_str):
        n = cls.base62_to_int(base62_str)
        return str(uuid.UUID(int=n))
