import hashlib


def hash_sha256(password: str):
    return hashlib.sha256(bytes(password, encoding='utf-8')).hexdigest()


def is_num(x: str):
    try:
        return isinstance(int(x), int)
    except Exception:
        return False

