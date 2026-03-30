import string
import random

ALPHABET = string.ascii_letters + string.digits

def generate_short_code(length=6):
    return ''.join(random.choices(ALPHABET, k=length))

import hashlib

def hash_ip(ip: str):
    return hashlib.sha256(ip.encode()).hexdigest()