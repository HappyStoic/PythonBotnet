import hashlib
import logging


def hash_sha256(password: str) -> str:
    return hashlib.sha256(bytes(password, encoding='utf-8')).hexdigest()


def is_num(x: str):
    try:
        return isinstance(int(x), int)
    except Exception:
        return False


def configure_logging():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger('websockets').setLevel(logging.ERROR)
    logging.getLogger('asyncio').setLevel(logging.ERROR)


class Id:
    idx = 1

    @staticmethod
    def next():
        cur = Id.idx
        Id.idx += 1
        return cur
