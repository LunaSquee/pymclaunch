import requests
import os
import re
import json
import zipfile
import time
import shutil
import subprocess
import lzma
from common import ensure_dir, save_to_file, platform, save_to_file_sha1

lib_url = 'https://libraries.minecraft.net/{package}/{name}/{version}/{name}-{version}.jar'

class MinecraftClient(object):
    """Launch a vanilla Minecraft client"""
    def __init__(self, clientRoot, mcVersion, gamedir, authentication = None, jvm = None):
        super(MinecraftClient, self).__init__()
        self.mcver = mcVersion
        self.client_root = clientRoot
        self.version_name = mcVersion
        self.version_directory = '%s/versions/%s' % (clientRoot, self.version_name)
        self.game_dir = gamedir
        self.metadata = None
        self.natives = None
        self.library_paths = []

        if not jvm:
            self.jvm = '-Xmx1G -XX:+UseConcMarkSweepGC -XX:+CMSIncrementalMode -XX:-UseAdaptiveSizePolicy -Xmn128M'
        else:
            self.jvm = jvm

        self.authentication = authentication

    def get_meta(self):
        ensure_dir(self.version_directory)
        metafile = os.path.join(self.version_directory, '%s.json' % self.version_name)

        if not os.path.exists(metafile):
            print('Grabbing metadata from Minecraft Downloads CDN...')

            # Get version metadata
            r = requests.get('https://s3.amazonaws.com/Minecraft.Download/versions/%s/%s.json' % (self.mcver, self.mcver), stream=True)

            # Save the file
            save_to_file(metafile, r)

        with open(metafile) as json_data:
            self.metadata = json.load(json_data)

    def install(self):
        if not self.metadata:
            self.get_meta()

        rfile = os.path.join(self.version_directory, '%s.jar' % (self.version_name))

        print(self.metadata['downloads'])

        if not os.path.exists(rfile):
            print('Downloading version jar...')
            rv = requests.get(self.metadata['downloads']['client']['url'], stream=True)

            save_to_file(rfile, rv)
        else:
            print('Skipping version jar download..')

        self.get_libraries()
        self.get_assets()

    def load_profile(self):
        pass

    def get_assets(self):
        if self.metadata:
            self.get_meta()

        print('Verifying assets..')

        assets_dir = os.path.join(self.client_root, 'assets')
        assets_versions = os.path.join(assets_dir, 'indexes')
        ensure_dir(assets_versions)

        asset_index = self.metadata['assetIndex']
        assets_file = os.path.join(assets_versions, '%s.json' % (asset_index['id']))

        if not os.path.exists(assets_file):
            r = requests.get(asset_index['url'], stream=True)

            try:
                save_to_file_sha1(assets_file, r, asset_index['sha1'])
            except Exception:
                print('Failed to download assets!')
                raise

        with open(assets_file) as json_data:
            assets = json.load(json_data)

        for key, data in assets['objects'].items():
            first = data['hash'][0:2]
            asset_url = 'http://resources.download.minecraft.net/%s/%s' % (first, data['hash'])
            asset_dir = os.path.join(assets_dir, 'objects', first)

            ensure_dir(asset_dir)

            asset_file = os.path.join(asset_dir, data['hash'])
            
            if os.path.exists(asset_file):
                continue

            r = requests.get(asset_url, stream=True)

            try:
                save_to_file(asset_file, r)
            except Exception as e:
                print('Failed to download asset %s!' % (key))
                raise e

        print('All assets verified.')

    def artifact(self, artifact, backup = None):
        lib_directory = os.path.join(self.client_root, 'libraries')
        artifact_path = os.path.join(lib_directory, artifact['path'])

        # Ensure the directory exists
        directory = artifact_path.split('/')
        del directory[-1]
        directory = '/'.join(directory)

        ensure_dir(directory)

        # Make sure it doesn't already exist
        if os.path.exists(artifact_path):
            print('Artifact %s exists, skipping..' % artifact['path'])
            return True

        print('Downloading artifact %s' % (artifact['path']))

        url_dl = artifact['url']
        if 'lzma' in artifact and artifact['lzma'] == True:
            url_dl += '.pack.xz'
            artifact_path += '.pack.xz'

        r = requests.get(url_dl, stream=True)

        if 'sha1' in artifact and not 'lzma' in artifact:
            f = save_to_file_sha1(artifact_path, r, artifact['sha1'])
        else:
            f = save_to_file(artifact_path, r)

        if 'lzma' in artifact and artifact['lzma'] == True:
            # Only unpack if we're a Forge client
            if getattr(self, "unpack_lzma", None):
                self.unpack_lzma(f)

        return artifact_path

    def get_libraries(self):
        if not self.metadata:
            self.get_meta()

        for lib in self.metadata['libraries']:
            lname = lib['name'].split(':')
            lurl = lib_url.format(package=lname[0], name=lname[1], version=lname[2])

            skiplib = False

            # Check Rules
            if 'rules' in lib:
                for rule in lib['rules']:
                    if 'action' in rule:
                        if rule['action'] == 'allow' and 'os' in rule:
                            if not rule['os']['name'] == platform():
                                skiplib = True
                        if rule['action'] == 'noallow' and 'os' in rule:
                            if rule['os']['name'] == platform():
                                skiplib = True
            if skiplib:
                continue

            # Skip non-download-included for now
            if not 'downloads' in lib:
                continue

            dl = lib['downloads']

            if 'natives' in lib:
                if platform() in lib['natives']:
                    platform_native = lib['natives'][platform()]

                    if platform_native in dl['classifiers']:
                        try:
                            self.artifact(dl['classifiers'][platform_native], lname)
                        except Exception as e:
                            print('Failed to download native library %s due to errors.' % (lib['name']))
                            raise e
            elif 'classifiers' in dl and 'natives-' + platform() in dl['classifiers']:
                self.library_paths.append(os.path.join(os.path.join(self.client_root, 'libraries', 
                    dl['classifiers']['natives-' + platform()]['path'])))

            if not 'artifact' in dl:
                continue

            self.library_paths.append(os.path.join(os.path.join(self.client_root, 'libraries', dl['artifact']['path'])))

            try:
                self.artifact(dl['artifact'], lname)
            except Exception as e:
                print('Failed to download library %s due to errors.' % (lib['name']))
                raise e

    def extract_natives(self):
        if not self.metadata:
            self.get_meta()
        
        natives_tmpdir = os.path.join(self.version_directory, 'natives-' + str(int(time.time())))
        ensure_dir(natives_tmpdir)

        for lib in self.metadata['libraries']:
            skiplib = False

            # Check Rules
            if 'rules' in lib:
                for rule in lib['rules']:
                    if 'action' in rule:
                        if rule['action'] == 'allow' and 'os' in rule:
                            if not rule['os']['name'] == platform():
                                skiplib = True
                        if rule['action'] == 'noallow' and 'os' in rule:
                            if rule['os']['name'] == platform():
                                skiplib = True
            if skiplib:
                continue

            # Skip non-download-included for now
            if not 'downloads' in lib:
                continue

            dl = lib['downloads']

            if 'natives' in lib and 'extract' in lib:
                if platform() in lib['natives']:
                    platform_native = lib['natives'][platform()]

                    if platform_native in dl['classifiers']:
                        try:
                            zip_ref = zipfile.ZipFile(os.path.join(self.client_root, 'libraries', 
                                dl['classifiers'][platform_native]['path']), 'r')
                            zip_ref.extractall(natives_tmpdir)
                            zip_ref.close()
                        except Exception as e:
                            print('Failed to extract native library %s due to errors.' % (lib['name']))
                            raise e

        metainf = os.path.join(natives_tmpdir, 'META-INF')

        if os.path.exists(metainf):
            shutil.rmtree(metainf)

        self.natives = natives_tmpdir

    def cleanup(self):
        shutil.rmtree(self.natives)

    def init_mc(self):
        self.install()
        self.extract_natives()
        
        ensure_dir(self.game_dir)

        self.library_paths.append(os.path.join(self.version_directory, '%s.jar' % (self.version_name)))

        launchargs_version = self.metadata['minecraftArguments']
        launchargs_class = self.metadata['mainClass']
        launchargs_libs = ':'.join(self.library_paths)
        launchargs_jvm = self.jvm + ' -Djava.library.path=%s -cp %s %s ' % (self.natives, launchargs_libs, launchargs_class)

        launchargs = re.sub(r'\${', '{', launchargs_version)
        launchargs = launchargs.format(version_name=self.version_name, game_directory=self.game_dir, 
            assets_root=os.path.join(self.client_root, 'assets'), assets_index_name=self.metadata['assets'], 
            auth_uuid=self.authentication.uuid, auth_access_token=self.authentication.access_token, user_type="legacy", 
            auth_player_name=self.authentication.player_name, version_type=self.metadata['type'])

        launchargs_jvm += launchargs

        process = subprocess.Popen(launchargs_jvm.split(' '), cwd=self.game_dir, executable="java", 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        for line in iter(process.stdout.readline, b''):
            print(">>> " + line.rstrip().decode('utf-8'))

        self.cleanup()
