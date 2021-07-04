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

import argparse
import copy
import os
from pathlib import Path
from platform import machine
import shutil
import subprocess
import typing

from .state import BuildState
from .target import Target, targets, DOWNLOAD_CMAKE_TARGET_NAME
from .utility import CaseInsensitiveDict, TargetPlatform, symlink_directory, OS_VERSION_X86_64, OS_VERSION_ARM64


class Builder(object):
    def __init__(self, args: list):
        self._targets = CaseInsensitiveDict({target.name: target for target in targets()})

        arguments = self._parse_arguments(args)

        state = self._state = BuildState()
        state.xcode = arguments.xcode
        state.verbose = arguments.verbose

        self._platforms = []
        self._populate_platforms(arguments)

        state.platform = self._platforms[0]

        if arguments.source_path:
            state.source_path = Path(arguments.source_path).absolute()

        if arguments.target:
            self._target = self._targets[arguments.target]
            state.source = state.source_path / self._target.name
            state.external_source = False
        else:
            assert arguments.source
            state.source = Path(arguments.source).absolute()
            state.external_source = True
            self._detect_target()

        del self._targets

        if arguments.build_path:
            state.build_path = Path(arguments.build_path).absolute()
        else:
            state.build_path = state.root_path / 'build' / self._target.name / ('xcode' if state.xcode else 'make')

        if arguments.output_path:
            state.output_path = Path(arguments.output_path).absolute()
        else:
            state.output_path = state.root_path / 'output'

        state.jobs = arguments.jobs and arguments.jobs or \
            subprocess.check_output(['sysctl', '-n', 'hw.ncpu']).decode('ascii').strip()

    def _populate_platforms(self, arguments):
        state = self._state

        def adjust_sdk_path(path: Path) -> Path:
            if path:
                return path.absolute()

            sdk_probe_path = state.root_path / 'sdk' / f'MacOSX{os_version}.sdk'
            return sdk_probe_path if sdk_probe_path.exists() else None

        if not arguments.disable_x64:
            os_version = arguments.os_version_x64 if arguments.os_version_x64 else OS_VERSION_X86_64
            sdk_path = adjust_sdk_path(arguments.sdk_path_x64)
            platform = TargetPlatform('x86_64', 'x86_64-apple-darwin', os_version, sdk_path, state.prefix_path)
            self._platforms.append(platform)

        if not arguments.disable_arm:
            os_version = arguments.os_version_arm if arguments.os_version_arm else OS_VERSION_ARM64
            sdk_path = adjust_sdk_path(arguments.sdk_path_arm)
            platform = TargetPlatform('arm64', 'aarch64-apple-darwin', os_version, sdk_path, state.prefix_path)
            self._platforms.append(platform)

        assert len(self._platforms) > 0

        # Put native platform first in the list of platforms
        if self._platforms[0].architecture == machine():
            return

        for platform in self._platforms:
            if platform.architecture == machine():
                native_platform = platform
                self._platforms.remove(platform)
                self._platforms.insert(0, native_platform)
                break

    def run(self):
        state = self._state
        target = self._target
        target.prepare_source(state)

        if target.destination == Target.DESTINATION_DEPS:
            state.install_path = state.deps_path / target.name
        elif target.destination == Target.DESTINATION_OUTPUT:
            state.install_path = state.output_path / target.name

        assert state.install_path

        if not state.xcode and state.install_path.exists():
            shutil.rmtree(state.install_path)

        if target.name != DOWNLOAD_CMAKE_TARGET_NAME:
            Builder(['--target=' + DOWNLOAD_CMAKE_TARGET_NAME]).run()

        self._create_prefix_directory()

        if target.multi_platform and not state.xcode:
            self._build_multiple_platforms(target)
        else:
            self._build(target)

    def _build(self, target: Target):
        state = self._state

        target.configure(state)
        target.build(state)
        target.post_build(state)

    def _build_multiple_platforms(self, base_target: Target):
        assert base_target.multi_platform

        state = self._state
        base_build_path = state.build_path
        base_install_path = state.install_path
        install_paths = []

        for platform in self._platforms:
            if platform.architecture in base_target.unsupported_architectures:
                continue

            state.platform = platform
            state.build_path = base_build_path / ('build_' + platform.architecture)

            if platform.architecture == machine():
                state.native_build_path = state.build_path

            target = copy.deepcopy(base_target)
            state.install_path = base_build_path / ('install_' + platform.architecture)

            self._build(target)

            install_paths.append(state.install_path)

        Builder._merge_install_paths(install_paths, base_install_path)

    @staticmethod
    def _compare_files(paths: typing.Sequence[Path]) -> bool:
        content = None

        for path in paths:
            if not path.exists():
                return False

            with path.open('rb') as f:
                if content:
                    if content != f.read():
                        return False
                else:
                    content = f.read()

        return True

    @staticmethod
    def _merge_file(src: Path, src_sub_paths: typing.Sequence[Path], dst_path: Path):
        with open(src, 'rb') as f:
            header = f.read(8)

        is_executable = header[:4] == b'\xcf\xfa\xed\xfe'
        is_library = header == b'!<arch>\n'

        if is_executable or is_library:
            # Merge executable and library files
            dst_file = dst_path / src.name

            args = ['lipo']
            args += src_sub_paths
            args += ['-create', '-output', dst_file]
            subprocess.check_call(args)

            # Apply ad-hoc code signing on executable files outside of application bundles
            if is_executable and '.app/Contents/' not in str(src):
                args = ('codesign', '--sign', '-', dst_file)
                subprocess.check_call(args)
        else:
            if not Builder._compare_files(src_sub_paths):
                print(f'WARNING: Source files for {dst_path / src.name} don\'t match')
            shutil.copy(src_sub_paths[0], dst_path)

    @staticmethod
    def _merge_missing_files(src_paths: typing.Sequence[Path], dst_path: Path):
        shifted_src_paths = [path for path in src_paths]
        last_path_index = len(src_paths) - 1

        for _ in range(last_path_index):
            shifted_src_paths.append(shifted_src_paths[0])
            del shifted_src_paths[0]

            if not shifted_src_paths[0].exists():
                continue

            Builder._merge_install_paths(shifted_src_paths, dst_path, missing_files_only=True)

    @staticmethod
    def _merge_install_paths(src_paths: typing.Sequence[Path], dst_path: Path, missing_files_only=False):
        if len(src_paths) == 0:
            return

        if not missing_files_only:
            if dst_path.exists():
                shutil.rmtree(dst_path)

        os.makedirs(dst_path, exist_ok=True)

        for src in src_paths[0].iterdir():
            src_sub_paths = [path / src.name for path in src_paths]

            if src.is_dir():
                Builder._merge_install_paths(src_sub_paths, dst_path / src.name, missing_files_only)
            elif src.name.endswith('.la'):
                # Skip libtool files
                continue
            elif missing_files_only:
                for src_sub_path in src_sub_paths[1:]:
                    if not src_sub_path.exists():
                        shutil.copy(src_sub_paths[0], dst_path)
            else:
                Builder._merge_file(src, src_sub_paths, dst_path)

        if not missing_files_only:
            Builder._merge_missing_files(src_paths, dst_path)

    def _create_prefix_directory(self):
        state = self._state
        os.makedirs(state.prefix_path, exist_ok=True)

        cleanup = True

        for dep in state.deps_path.iterdir():
            if dep.is_dir():
                symlink_directory(dep, state.prefix_path, cleanup)

                # Do symlink cleanup only once
                cleanup = False

    def _detect_target(self):
        for name, target in self._targets.items():
            if target.detect(self._state):
                self._target = self._targets[name]
                break

        assert self._target

    def _parse_arguments(self, args: list):
        assert self._targets

        parser = argparse.ArgumentParser(description='*ZDoom binary dependencies for macOS')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--target', choices=self._targets.keys(), help='target to build')
        group.add_argument('--source', metavar='path', help='path to target\'s source code')

        group = parser.add_argument_group()
        group.add_argument('--xcode', action='store_true', help='generate Xcode project instead of build')
        group.add_argument('--source-path', metavar='path',
                           help='path to store downloaded and checked out source code')
        group.add_argument('--build-path', metavar='path', help='target build path')
        group.add_argument('--output-path', metavar='path', help='output path for main targets')
        group.add_argument('--sdk-path-x64', metavar='path', help='path to macOS SDK for x86_64')
        group.add_argument('--sdk-path-arm', metavar='path', help='path to macOS SDK for ARM64')
        group.add_argument('--os-version-x64', metavar='version', help='macOS deployment version for x86_64')
        group.add_argument('--os-version-arm', metavar='version', help='macOS deployment version for ARM64')
        group.add_argument('--verbose', action='store_true', help='enable verbose build output')
        group.add_argument('--jobs', help='number of parallel compilation jobs')

        group = parser.add_mutually_exclusive_group()
        group.add_argument('--disable-x64', action='store_true', help='disable x86_64 support')
        group.add_argument('--disable-arm', action='store_true', help='disable ARM64 support')

        return parser.parse_args(args)
