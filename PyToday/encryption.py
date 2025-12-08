from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from PyToday import config

def get_encryption_key():
    key = config.ENCRYPTION_KEY.encode()
    salt = b'telegram_adbot_salt'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(key))
    return derived_key

def encrypt_data(data: str) -> str:
    if not data:
        return ""
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(data.encode())
    return encrypted.decode()

def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data:
        return ""
    try:
        fernet = Fernet(get_encryption_key())
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception:
        return encrypted_data
