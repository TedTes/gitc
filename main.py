import hashlib
import zlib
import os 
from pathlib import Path 

def init_repo():
    os.makedir('.mygit/objects',exist_ok=True)
    os.makedir('.mygit/refs/heads', exist_ok=True)


def hash_object(data, obj_type):
    """Create hash from object data"""
    header = f"{obj_type} {len(data)}".encode()
    full_data = header + b'\0' + data
    return hashlib.sha256(full_data).hexdigest()


def write_object(data, obj_type):
    """Write object to .mygit/objects/"""
    obj_hash = hash_object(data, obj_type)
    header = f"{obj_type} {len(data)}".encode()
    full_data = header + b'\0' + data
    compressed = zlib.compress(full_data)

    obj_dir = f".mygit/objects/{obj_hash[:2]}"
    os.makedirs(obj_dir, exist_ok=True)
    obj_path = f"{obj_dir}/{obj_hash[2:]}"

    with open(obj_path, 'wb') as f:
        f.write(compressed)
    return obj_hash


def read_object(obj_hash):
    """Read object from .mygit/objects/"""
    obj_path = f".mygit/objects/{obj_hash[:2]}/{obj_hash[2:]}"
    with open(obj_path, 'rb') as f:
        compressed = f.read()
    full_data = zlib.decompress(compressed)

    null_idx = full_data.index(b'\0')
    header = full_data[:null_idx].decode()
    content = full_data[null_idx + 1:]
    obj_type, size = header.split()
    return obj_type, content



def hash_blob(filepath):
    """Create blob object from file"""
    with open(filepath, 'rb') as f:
        data = f.read()
    return write_object(data, 'blob')



def create_tree(directory='.'):
    """Create tree object from directory"""
    entries = []
    
    for item in sorted(os.listdir(directory)):
        if item == '.mygit':  # Skip our git directory
            continue
        path = os.path.join(directory, item)

    if os.path.isfile(path):
        # File: create blob
        blob_hash = hash_blob(path)
        mode = '100644'
        entries.append((mode, item, blob_hash))
    elif os.path.isdir(path):
         tree_hash = create_tree(path)
         mode = '040000'
         entries.append((mode, item, tree_hash))

    # Build tree content
    tree_content = b''
    for mode, name, obj_hash in entries:
        tree_content += mode.encode() + b' '
        tree_content += name.encode() + b'\0'
        tree_content += bytes.fromhex(obj_hash)  # Binary hash
   
    # Write tree object
    return write_object(tree_content, 'tree')


import time

def create_commit(tree_hash, parent_hash, message, author="User <user@example.com>"):
    """Create commit object"""
    timestamp = int(time.time())
    timezone = "+0000"
    author_line = f"{author} {timestamp} {timezone}"