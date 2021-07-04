#
#    Helper module to build macOS version of various source ports
#    Copyright (C) 2020-2021 Alexey Lysiuk
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from distutils.version import StrictVersion
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request


class BuildState:
    def __init__(self):
        self_path = Path(__file__)
        self.root_path = self_path.parent.parent
        self.deps_path = self.root_path / 'deps'
        self.prefix_path = self.root_path / 'prefix'
        self.bin_path = self.prefix_path / 'bin'
        self.include_path = self.prefix_path / 'include'
        self.lib_path = self.prefix_path / 'lib'
        self.patch_path = self.root_path / 'patch'
        self.source_path = self.root_path / 'source'

        self.source = Path()
        self.external_source = True

        self.build_path = None
        self.native_build_path = None

        self.output_path = None
        self.install_path = None

        self.platform = None
        self.xcode = False
        self.verbose = False
        self.jobs = 1

    def architecture(self) -> str:
        return self.platform.architecture if self.platform else ''

    def host(self) -> str:
        return self.platform.host if self.platform else ''

    def os_version(self) -> StrictVersion:
        return self.platform.os_version if self.platform else None

    def sdk_path(self) -> str:
        return self.platform.sdk_path if self.platform else ''

    def c_compiler(self) -> str:
        return self.platform.c_compiler if self.platform else ''

    def cxx_compiler(self) -> str:
        return self.platform.cxx_compiler if self.platform else ''

    def checkout_git(self, url: str, branch: str = None):
        if os.path.exists(self.source):
            return

        args = ('git', 'clone', '--recurse-submodules', url, self.source)
        subprocess.run(args, cwd=self.root_path, check=True)

        if branch:
            args = ('git', 'checkout', '-b', branch, 'origin/' + branch)
            subprocess.run(args, cwd=self.source, check=True)

    def download_source(self, url: str, checksum: str, patches: [tuple, list, str] = None):
        if self.external_source:
            return

        os.makedirs(self.source, exist_ok=True)

        data, filepath = self._read_source_package(url)
        self._verify_checksum(checksum, data, filepath)

        first_path_component, extract_path = self._unpack_source_package(filepath)

        if not patches:
            pass
        elif isinstance(patches, str):
            self._apply_source_patch(extract_path, patches)
        elif isinstance(patches, (tuple, list)):
            for patch in patches:
                self._apply_source_patch(extract_path, patch)
        else:
            assert False

        # Adjust source and build paths according to extracted source code
        self.source = extract_path
        self.build_path = self.build_path / first_path_component

    def _read_source_package(self, url: str) -> (bytes, Path):
        filename = url.rsplit(os.sep, 1)[1]
        filepath = self.source / filename

        if filepath.exists():
            # Read existing source package
            with open(filepath, 'rb') as f:
                data = f.read()
        else:
            # Download package with source code
            print(f'Downloading {filename}')

            response = urllib.request.urlopen(url)

            try:
                with open(filepath, 'wb') as f:
                    data = response.read()
                    f.write(data)

            except IOError:
                os.unlink(filepath)
                raise

        return data, filepath

    @staticmethod
    def _verify_checksum(checksum: str, data: bytes, filepath: Path) -> None:
        file_hasher = hashlib.sha256()
        file_hasher.update(data)
        file_checksum = file_hasher.hexdigest()

        if file_checksum != checksum:
            filepath.unlink()
            raise Exception(f'Checksum of {filepath} does not match, expected: {checksum}, actual: {file_checksum}')

    def _unpack_source_package(self, filepath: Path) -> (str, Path):
        filepaths = subprocess.check_output(['tar', '-tf', filepath]).decode("utf-8")
        filepaths = filepaths.split('\n')
        first_path_component = None

        for path in filepaths:
            if os.sep in path:
                first_path_component = path[:path.find(os.sep)]
                break

        if not first_path_component:
            raise Exception(f'Failed to figure out source code path for {filepath}')

        extract_path = self.source / first_path_component

        if not extract_path.exists():
            # Extract source code package
            try:
                subprocess.check_call(['tar', '-xf', filepath], cwd=self.source)
            except (IOError, subprocess.CalledProcessError):
                shutil.rmtree(extract_path, ignore_errors=True)
                raise

        return first_path_component, extract_path

    def _apply_source_patch(self, extract_path: Path, patch: str):
        patch_path = self.patch_path / (patch + '.diff')
        assert patch_path.exists()

        # Check if patch is already applied
        test_arg = '--dry-run'
        args = ['patch', test_arg, '--strip=1', '--input=' + str(patch_path)]

        if subprocess.call(args, cwd=extract_path) == 0:
            # Patch wasn't applied yet, do it now
            args.remove(test_arg)
            subprocess.check_call(args, cwd=extract_path)

    def run_pkg_config(self, *args) -> str:
        os.makedirs(self.build_path, exist_ok=True)

        args = (self.bin_path / 'pkg-config',) + args
        result = subprocess.check_output(args, cwd=self.build_path)

        return result.decode('utf-8').rstrip('\n')
