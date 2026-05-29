import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# AES key from password using PBKDF2
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

# Encrypt a single password string (AES-CBC)
def encrypt_password(plain: str, key: bytes) -> str:
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plain.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    ct = enc.update(padded) + enc.finalize()
    return base64.b64encode(iv + ct).decode()

# Decrypt a single password string
def decrypt_password(enc_b64: str, key: bytes) -> str:
    raw = base64.b64decode(enc_b64)
    iv, ct = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode()

# Encrypt entire file with AES
def encrypt_file(filepath: str, key: bytes):
    with open(filepath, 'rb') as f:
        data = f.read()
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc = cipher.encryptor()
    ct = enc.update(padded) + enc.finalize()
    with open(filepath + '.enc', 'wb') as f:
        f.write(iv + ct)
    os.remove(filepath)

# Decrypt entire file with AES
def decrypt_file(filepath_enc: str, key: bytes):
    with open(filepath_enc, 'rb') as f:
        raw = f.read()
    iv, ct = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()
    out = filepath_enc.replace('.enc', '')
    with open(out, 'wb') as f:
        f.write(data)
    os.remove(filepath_enc)
    return out