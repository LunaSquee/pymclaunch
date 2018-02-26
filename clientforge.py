import client
import requests
import os
import io
import re
import json
import zipfile
import lzma
import shutil
import subprocess
from common import ensure_dir, save_to_file, platform, save_to_file_sha1

mvn = 'http://files.minecraftforge.net/maven/'
mclib = 'https://libraries.minecraft.net/'

class MinecraftClientForge(client.MinecraftClient):
    """Launch a Minecraft Forge-enabled client"""
    def __init__(self, clientRoot, mcVersion, forgeVersion, gameName, authentication = None, jvm = None):
        super(MinecraftClientForge, self).__init__(clientRoot, mcVersion, gameName, authentication, jvm)
        
        self.forge_version = forgeVersion
        self.forge_name = self.mcver + '-' + re.sub(r'^forge-', '', self.forge_version)
        self.version_name = self.mcver + '-' + self.forge_version
        self.version_directory = '%s/versions/%s' % (self.client_root, self.version_name)
        self.forge_metadata = None

    def install_forge(self):
        if os.path.exists(self.version_directory):
            return

        # Create a temporary files directory
        self.tmp_dir = 'tmp'
        ensure_dir(self.tmp_dir)

        # Make sure all the components are ready.
        self.install()

        forge_path = mvn + 'net/minecraftforge/forge/{name}/forge-{name}-universal.jar'.format(name = self.forge_name)
        forge_target = os.path.join(self.tmp_dir, forge_path.split('/')[-1])

        r = requests.get(forge_path, stream=True)
        save_to_file(forge_target, r)

        print('Extracting forge archive ...')
        zip_ref = zipfile.ZipFile(forge_target, 'r')
        zip_ref.extractall(self.tmp_dir)
        zip_ref.close()

        print('Reading forge metadata ...')
        metafile = os.path.join(self.tmp_dir, 'version.json')
        with open(metafile) as json_data:
            self.forge_metadata = json.load(json_data)

        print('Creating pretty libraries ...')
        libs = []
        # Make libraries readable by the MinecraftClient class.
        # Ensures that .pack.xz files get unpacked properly as well.
        for lib in self.forge_metadata['libraries']:
            nsplit = lib['name'].split(':')

            if 'serverreq' in lib and lib['serverreq'] == True and ('clientreq' in lib and lib['clientreq'] == False):
                continue
            if 'clientreq' in lib and lib['clientreq'] == False:
                continue

            # Lib Path builder
            fpath = nsplit[0].split('.')
            fpath.append(nsplit[1])
            fpath.append(nsplit[2])
            fpath.append(nsplit[1] + '-' + nsplit[2] + '.jar')
            fpath = '/'.join(fpath)

            # Lib URL builder
            url = None
            if 'url' in lib:
                if nsplit[1] == 'forge':
                  # A hack around, need to download the universal jar!
                  forgePath = nsplit[0].split('.')
                  forgePath.append(nsplit[1])
                  forgePath.append(nsplit[2])
                  forgePath.append(nsplit[1] + '-' + nsplit[2] + '-universal.jar')
                  url = lib['url'] + '/'.join(forgePath)
                else:
                  url = lib['url'] + fpath
            else:
                url = mclib + fpath

            # The artifacts with two checksums are .pack.xz files
            sha1 = None
            requiresLZMA = False

            if 'checksums' in lib:
                sha1 = lib['checksums']
                if len(sha1) > 1:
                  sha1 = None
                  requiresLZMA = True
                else:
                  sha1 = lib['checksums'][0]

            libs.append({
                "name": lib['name'],
                "downloads": {
                  "artifact": {
                    "lzma": requiresLZMA,
                    "url": url,
                    "path": fpath,
                    "sha1": sha1
                  }
                }
            })

        print('Library paths finished, saving to metadata ...')

        self.metadata['libraries'] += libs
        self.metadata['id'] = self.forge_metadata['id']
        self.metadata['minecraftArguments'] = self.forge_metadata['minecraftArguments']
        self.metadata['mainClass'] = self.forge_metadata['mainClass']

        self.save_metadata()
        self.get_libraries()

        print('Cleaning up ...')

        self.clean_up()

    def clean_up(self):
        shutil.rmtree(self.tmp_dir)

    def save_metadata(self):
        with open(os.path.join(self.version_directory, '%s.json' % (self.version_name)), 'w') as fp:
            json.dump(self.metadata, fp)

    def unpack_lzma(self, file):
        # Extract XZ
        pack_path = re.sub(r'\.xz', '', file)

        with lzma.open(file) as f:
            fdata = f.read()

        # Find checksums in the file
        x = len(fdata)
        signflag = fdata[x - 4:]
        lendata = ((fdata[x - 8] & 0xFF)) | ((fdata[x - 7] & 0xFF) << 8) | ((fdata[x - 6] & 0xFF) << 16) | ((fdata[x - 5] & 0xFF) << 24)
        
        if not signflag.decode('utf-8') == 'SIGN':
            raise ValueError('Invalid file.')

        # TODO: Checksum checking
        checksums = fdata[x - lendata - 8:x-8].decode('utf-8')

        # Remove the checksum bytes
        filedata = io.BytesIO(fdata[0 : x - lendata - 8])

        # Override the .pack
        with open(pack_path, 'wb') as fp:
            shutil.copyfileobj(filedata, fp, filedata.getbuffer().nbytes)

        # Unpack200
        jar = re.sub(r'\.pack', '', pack_path)
        ret = subprocess.run(['unpack200', pack_path, jar])
        if ret.returncode:
            raise Exception('unpack200 failed or is missing! Make sure java is installed and in your $PATH!')

        # Clean up
        os.remove(file)
        os.remove(pack_path)
