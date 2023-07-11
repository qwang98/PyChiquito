import threading

uuid_gen = threading.Lock()
_uuid = 0

def uuid() -> int:
    global _uuid
    with uuid_gen:
        _uuid += 1
        return _uuid
