import hashlib
import zlib
import os 
from pathlib import Path 

def init_repo():
    os.makedirs('.mygit/objects',exist_ok=True)
    os.makedirs('.mygit/refs/heads', exist_ok=True)


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
    commit_content = f"tree {tree_hash}\n"
    if parent_hash:
        commit_content += f"parent {parent_hash}\n"
    commit_content += f"author {author_line}\n"
    commit_content += f"committer {author_line}\n\n{message}\n"
    # Write commit object
    return write_object(commit_content.encode(), 'commit')


def get_current_branch():
    """Get name of current branch from HEAD"""
    head_path = '.mygit/HEAD'
    if not os.path.exists(head_path):
        return None
    with open(head_path, 'r') as f:
        ref = f.read().strip()
    
    # HEAD contains "ref: refs/heads/main"
    if ref.startswith('ref: '):
        return ref[16:]  # Strip "ref: refs/heads/"
    return None  # Detached HEAD


def get_current_commit():
    """Get hash of current commit"""
    branch = get_current_branch()
    if not branch:
        return None
    branch_path = f'.mygit/refs/heads/{branch}'
    if not os.path.exists(branch_path):
        return None
    
    with open(branch_path, 'r') as f:
        return f.read().strip()

def update_branch(branch, commit_hash):
    """Update branch to point to commit"""
    branch_path = f'.mygit/refs/heads/{branch}'
    with open(branch_path, 'w') as f:
        f.write(commit_hash)


def commit(message):
    """Create a commit from current directory"""
    tree_hash = create_tree('.')
    parent_hash = get_current_commit()
    commit_hash = create_commit(tree_hash, parent_hash, message)
    branch = get_current_branch() or 'main'
    update_branch(branch, commit_hash)
    return commit_hash


def init():
    """Initialize repository"""
    init_repo()
    # Set HEAD to point to main branch
    with open('.mygit/HEAD', 'w') as f:
        f.write('ref: refs/heads/main')
    print("Initialized empty repository in .mygit/")


def create_branch(branch_name, commit_hash=None):
    """Create a new branch"""
    if commit_hash is None:
        commit_hash = get_current_commit()
    if not commit_hash:
        print("No commits yet")
        return
    update_branch(branch_name, commit_hash)
    print(f"Created branch '{branch_name}'")




def checkout(branch_name):
    """Switch to a branch"""
    branch_path = f'.mygit/refs/heads/{branch_name}'
    if not os.path.exists(branch_path):
        print(f"Branch '{branch_name}' does not exist")
        return
    with open('.mygit/HEAD', 'w') as f:
        f.write(f'ref: refs/heads/{branch_name}')
    print(f"Switched to branch '{branch_name}'")



if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python mygit.py <command> [args]")
        sys.exit(1)
    
    cmd = sys.argv[1]

    if cmd == 'init':
        init()
    elif cmd == 'commit':
        msg = sys.argv[2] if len(sys.argv) > 2 else "No message"
        commit(msg)
        print(f"Committed")
    elif cmd == 'branch':
        create_branch(sys.argv[2])
    elif cmd == 'checkout':
        checkout(sys.argv[2])
    elif cmd == 'log':
        log()


def log():
    """Show commit history"""
    commit_hash = get_current_commit()
    if not commit_hash:
        print("No commits yet")
        return
    
    while commit_hash:
        obj_type, content = read_object(commit_hash)
        lines = content.decode().split('\n')
        print(f"commit {commit_hash}")
        for line in lines:
            if line.startswith('parent '):
                commit_hash = line.split()[1]
            elif line.startswith('author '):
                print(f"Author: {line[7:]}")
            elif line and not line.startswith(('tree', 'committer')):
                print(f"    {line}")
        print()
        if 'parent ' not in content.decode():
            break