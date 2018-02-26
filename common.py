import os, errno
import sys
import hashlib

def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def save_to_file(path, response):
    file_name = path.split('/')[-1]
    size = int(response.headers['content-length'].strip())
    bytesdl = 0

    with open(path, 'wb') as handle:
        for block in response.iter_content(1024):
            handle.write(block)
            bytesdl += len(block)

            sys.stdout.write('\rDownloading %s - %s MB of %s MB' % (
                file_name, str(round(bytesdl / 1024 / 1024, 2))[:4],
                str(round(size / 1024 / 1024, 2))[:4]))
            sys.stdout.flush()

    sys.stdout.write('\rDownloaded file %s successfully!' % (file_name) + ' ' * (len(file_name) + 10) + '\n')
    sys.stdout.flush()

    return path

def save_to_file_sha1(path, response, checksum):
    file_name = path.split('/')[-1]
    size = int(response.headers['content-length'].strip())
    bytesdl = 0
    hash_sha1 = hashlib.sha1()

    with open(path, 'wb') as handle:
        for block in response.iter_content(1024):
            handle.write(block)
            hash_sha1.update(block)
            bytesdl += len(block)

            sys.stdout.write('\rDownloading %s - %s MB of %s MB' % (
                file_name, str(round(bytesdl / 1024 / 1024, 2))[:4],
                str(round(size / 1024 / 1024, 2))[:4]))
            sys.stdout.flush()

    sys.stdout.write('\rDownloaded file %s successfully!' % (file_name) + ' ' * (len(file_name) + 10) + '\n')
    sys.stdout.flush()

    digest = hash_sha1.hexdigest()
    if not digest == checksum:
        os.remove(path)
        raise Warning('The checksum on this file DID NOT MATCH! Please try again later.')

    return path

def platform():
    pf = sys.platform
    if pf == 'linux' or pf == 'cygwin':
        return 'linux'
    elif pf == 'darwin':
        return 'osx'
    
    return 'windows'
