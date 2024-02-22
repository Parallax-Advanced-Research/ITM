import hashlib

def hash_file(filePath):
    h = hashlib.sha256()
    with open(filePath, "rb") as f:
        data = f.read(2048)
        while data != b"":
            h.update(data)
            data = f.read(2048)
    return h.hexdigest()
    
    
def empty_hash():
    h = hashlib.sha256()
    return h.hexdigest()