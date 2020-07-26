#!/usr/bin/env python3

#
#    Helper module to build macOS version of various source ports
#    Copyright (C) 2020 Alexey Lysiuk
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

import sys

if sys.hexversion < 0x3070000:
    print('Build module requires Python 3.7 or newer')
    exit(1)

import argparse
import re
import os
import shutil
import subprocess


class Target:
    def __init__(self: str):
        self.name = None
        self.url = None
        self.src_root = ''
        self.cmake_options = {}
        self.post_build = None

    def _assign_common_linker_flags(self, builder: 'Builder'):
        extra_libs = (
            'mpg123',

            # FluidSynth with dependencies
            'fluidsynth',
            'instpatch-1.0',
            'glib-2.0',
            'gobject-2.0',
            'intl',
            'ffi',
            'pcre',

            # Sndfile with dependencies
            'sndfile',
            'ogg',
            'vorbis',
            'vorbisenc',
            'FLAC',
            'opus',
        )

        linker_args = '-framework AudioUnit -framework AudioToolbox -framework Carbon ' \
                      '-framework CoreAudio -framework CoreMIDI -framework CoreVideo -liconv'

        for lib in extra_libs:
            linker_args += f' {builder.lib_path}lib{lib}.a'

        self.cmake_options['CMAKE_EXE_LINKER_FLAGS'] = linker_args


class ZDoomBaseTarget(Target):
    def __init__(self):
        super().__init__()

    def configure(self, builder: 'Builder'):
        self._assign_common_linker_flags(builder)

        opts = self.cmake_options
        opts['PK3_QUIET_ZIPDIR'] = 'YES'
        opts['DYN_OPENAL'] = 'NO'
        # Explicit OpenAL configuration to avoid selection of Apple's framework
        opts['OPENAL_INCLUDE_DIR'] = builder.include_path
        opts['OPENAL_LIBRARY'] = builder.lib_path + 'libopenal.a'


class GZDoomTarget(ZDoomBaseTarget):
    def __init__(self):
        super().__init__()
        self.name = 'gzdoom'
        self.url = 'https://github.com/coelckers/gzdoom.git'
        self.post_build = GZDoomTarget._copy_moltenvk

    @staticmethod
    def _copy_moltenvk(builder: 'Builder'):
        molten_lib = 'libMoltenVK.dylib'
        src_path = builder.lib_path + molten_lib
        dst_path = builder.build_path

        if builder.xcode:
            # TODO: Support other configurations
            dst_path += 'Debug' + os.sep

        dst_path += builder.target.name + '.app/Contents/MacOS' + os.sep
        os.makedirs(dst_path, exist_ok=True)

        dst_path += molten_lib

        if not os.path.exists(dst_path):
            copy_func = builder.xcode and os.symlink or shutil.copy
            copy_func(src_path, dst_path)


class QZDoomTarget(GZDoomTarget):
    def __init__(self):
        super().__init__()
        self.name = 'qzdoom'
        self.url = 'https://github.com/madame-rachelle/qzdoom.git'


class LZDoomTarget(ZDoomBaseTarget):
    def __init__(self):
        super().__init__()
        self.name = 'lzdoom'
        self.url = 'https://github.com/drfrag666/gzdoom.git'

    def configure(self, builder: 'Builder'):
        super().configure(builder)

        opts = self.cmake_options
        opts['DYN_FLUIDSYNTH'] = 'NO'
        opts['DYN_MPG123'] = 'NO'
        opts['DYN_SNDFILE'] = 'NO'


class RazeTarget(ZDoomBaseTarget):
    def __init__(self):
        super().__init__()
        self.name = 'raze'
        self.url = 'https://github.com/coelckers/Raze.git'


class ZandronumTarget(Target):
    def __init__(self):
        super().__init__()
        self.name = 'zandronum'
        self.url = 'https://github.com/TorrSamaho/zandronum.git'

    def configure(self, builder: 'Builder'):
        opts = self.cmake_options
        opts['CMAKE_EXE_LINKER_FLAGS'] = '-framework AudioUnit -framework Carbon -framework IOKit'
        # TODO: Linking to FluidSynth is disabled because Zandronum doesn't support FluidSynth 2.x
        # opts['DYN_FLUIDSYNTH'] = 'NO'
        opts['FMOD_INCLUDE_DIR'] = builder.include_path
        opts['FMOD_LIBRARY'] = builder.lib_path + 'libfmodex.dylib'


class PrBoomPlusTarget(Target):
    def __init__(self):
        super().__init__()
        self.name = 'prboom-plus'
        self.url = 'https://github.com/coelckers/prboom-plus.git'
        self.src_root = 'prboom2'

    def configure(self, builder: 'Builder'):
        self._assign_common_linker_flags(builder)

        extra_linker_args = ' -framework ForceFeedback -framework IOKit'

        extra_libs = (
            'mikmod',
            'modplug',
            'opusfile',
            'webp',
        )

        for lib in extra_libs:
            extra_linker_args += f' {builder.lib_path}lib{lib}.a'

        opts = self.cmake_options
        opts['CMAKE_C_FLAGS'] = '-D_FILE_OFFSET_BITS=64'
        opts['CMAKE_EXE_LINKER_FLAGS'] += extra_linker_args
        opts['CMAKE_POLICY_DEFAULT_CMP0056'] = 'NEW'


class ChocolateDoomTarget(Target):
    def __init__(self):
        super().__init__()
        self.name = 'chocolate-doom'
        self.url = 'https://github.com/chocolate-doom/chocolate-doom.git'

    def configure(self, builder: 'Builder'):
        self._assign_common_linker_flags(builder)

        extra_linker_args = ' -lc++ -framework Cocoa -framework ForceFeedback -framework IOKit'

        extra_libs = (
            'mikmod',
            'modplug',
            'opusfile',
            'vorbisfile',
        )

        for lib in extra_libs:
            extra_linker_args += f' {builder.lib_path}lib{lib}.a'

        sdl2_include_dir = builder.include_path + 'SDL2'

        opts = self.cmake_options
        opts['SDL2_INCLUDE_DIR'] = sdl2_include_dir
        opts['SDL2_LIBRARY'] = builder.lib_path + 'libSDL2.a'
        opts['SDL2_MIXER_INCLUDE_DIR'] = sdl2_include_dir
        opts['SDL2_MIXER_LIBRARY'] = builder.lib_path + 'libSDL2_mixer.a'
        opts['SDL2_NET_INCLUDE_DIR'] = sdl2_include_dir
        opts['SDL2_NET_LIBRARY'] = builder.lib_path + 'libSDL2_net.a'
        opts['CMAKE_EXE_LINKER_FLAGS'] += extra_linker_args


class CrispyDoomTarget(ChocolateDoomTarget):
    def __init__(self):
        super().__init__()
        self.name = 'crispy-doom'
        self.url = 'https://github.com/fabiangreffrath/crispy-doom.git'


class DevilutionXTarget(Target):
    def __init__(self):
        super().__init__()
        self.name = 'devilutionx'
        self.url = 'https://github.com/diasurgical/devilutionX.git'

    def configure(self, builder: 'Builder'):
        self._assign_common_linker_flags(builder)

        extra_linker_args = ' -lbz2 -lz -framework Cocoa -framework ForceFeedback -framework IOKit'

        extra_libs = (
            'freetype',
            'mikmod',
            'modplug',
            'opusfile',
            'png',
            'vorbisfile',
        )

        for lib in extra_libs:
            extra_linker_args += f' {builder.lib_path}lib{lib}.a'

        opts = self.cmake_options
        opts['CMAKE_EXE_LINKER_FLAGS'] += extra_linker_args


class SladeTarget(Target):
    def __init__(self):
        super().__init__()
        self.name = 'slade'
        self.url = 'https://github.com/sirjuddington/SLADE.git'

    def configure(self, builder: 'Builder'):
        self._assign_common_linker_flags(builder)

        os.unlink(builder.include_path + 'dumb.h')

        # extra_linker_args = ' -lbz2 -lz -framework Cocoa -framework ForceFeedback -framework IOKit'
        #
        # extra_libs = (
        #     'freetype',
        #     'mikmod',
        #     'modplug',
        #     'opusfile',
        #     'png',
        #     'vorbisfile',
        # )
        #
        # for lib in extra_libs:
        #     extra_linker_args += f' {builder.lib_path}lib{lib}.a'
        #
        opts = self.cmake_options
        # opts['CMAKE_EXE_LINKER_FLAGS'] += extra_linker_args
        opts['SFML_STATIC'] = 'YES'


class Builder(object):
    def __init__(self, args: list):
        self._create_targets()

        self.root_path = os.path.dirname(os.path.abspath(__file__)) + os.sep
        self.deps_path = self.root_path + 'deps' + os.sep
        self.prefix_path = self.root_path + 'prefix' + os.sep
        self.bin_path = self.prefix_path + 'bin' + os.sep
        self.include_path = self.prefix_path + 'include' + os.sep
        self.lib_path = self.prefix_path + 'lib' + os.sep

        self._create_prefix_directory()

        arguments = self._parse_arguments(args)

        self.xcode = arguments.xcode
        self.checkout_commit = arguments.checkout_commit
        self.build_path = arguments.build_path
        self.sdk_path = arguments.sdk_path
        self.os_version = arguments.os_version

        if arguments.target:
            self.target = self.targets[arguments.target]
            self.source_path = self.root_path + 'source' + os.sep + self.target.name
        else:
            assert arguments.source_path
            self.source_path = arguments.source_path
            self._detect_target()

        if not self.build_path:
            self.build_path = self.root_path + 'build' + os.sep + self.target.name + \
                os.sep + (self.xcode and 'xcode' or 'make')

        self.source_path += os.sep
        self.build_path += os.sep

        self.target.configure(self)

    def run(self):
        self._prepare_source()
        self._generate_cmake()
        self._build_target()

    def _create_prefix_directory(self):
        os.makedirs(self.bin_path, exist_ok=True)
        os.makedirs(self.include_path, exist_ok=True)
        os.makedirs(self.lib_path, exist_ok=True)

        # Delete obsolete symbolic links
        for root, _, files in os.walk(self.prefix_path, followlinks=True):
            for filename in files:
                file_path = root + os.sep + filename

                if os.path.islink(file_path) and not os.path.exists(file_path):
                    os.remove(file_path)

        # Create symbolic links if needed
        for dep in os.scandir(self.deps_path):
            if not dep.is_dir():
                continue

            def symlink_deps(src_dir):
                src_path = dep.path + os.sep + src_dir + os.sep
                if not os.path.exists(src_path):
                    return

                dst_path = self.prefix_path + src_dir + os.sep

                for src in os.scandir(src_path):
                    dst_subpath = dst_path + src.name

                    if src.is_dir():
                        os.makedirs(dst_subpath, exist_ok=True)
                        symlink_deps(src_dir + os.sep + src.name)
                    elif not os.path.exists(dst_subpath):
                        os.symlink(src.path, dst_subpath)

            symlink_deps('bin')
            symlink_deps('include')
            symlink_deps('lib')

    def _prepare_source(self):
        if not os.path.exists(self.source_path):
            args = ('git', 'clone', '--recurse-submodules', self.target.url, self.source_path)
            subprocess.check_call(args, cwd=self.root_path)

        if self.checkout_commit:
            args = ['git', 'checkout', self.checkout_commit]
            subprocess.check_call(args, cwd=self.source_path)

    def _generate_cmake(self):
        environ = os.environ
        environ['PATH'] = environ['PATH'] \
            + os.pathsep + '/Applications/CMake.app/Contents/bin' \
            + os.pathsep + self.bin_path
        environ['PKG_CONFIG_PATH'] = self.lib_path + 'pkgconfig'

        os.makedirs(self.build_path, exist_ok=True)

        args = [
            'cmake',
            self.xcode and '-GXcode' or '-GUnix Makefiles',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + self.prefix_path,
            '-DCMAKE_OSX_DEPLOYMENT_TARGET=' + self.os_version,
        ]

        if self.sdk_path:
            args.append('-DCMAKE_OSX_SYSROOT=' + self.sdk_path)

        for cmake_arg_name, cmake_arg_value in self.target.cmake_options.items():
            args.append(f'-D{cmake_arg_name}={cmake_arg_value}')

        args.append(self.source_path + self.target.src_root)

        subprocess.check_call(args, cwd=self.build_path, env=environ)

    def _build_target(self):
        if self.xcode:
            # TODO: support case-sensitive file system
            args = ('open', self.target.name + '.xcodeproj')
        else:
            jobs = subprocess.check_output(['sysctl', '-n', 'hw.ncpu']).decode('ascii').strip()
            args = ('make', '-j', jobs)

        subprocess.check_call(args, cwd=self.build_path)

        if self.target.post_build:
            self.target.post_build(self)

    def _detect_target(self):
        cmakelists_path = None

        for target in self.targets.values():
            src_root = target.src_root and os.sep + target.src_root or ''
            probe_path = self.source_path + src_root + os.sep + 'CMakeLists.txt'

            if os.path.exists(probe_path):
                cmakelists_path = probe_path
                break

        assert cmakelists_path
        project_name = None

        for line in open(cmakelists_path).readlines():
            match = re.search(r'project\s*\(\s*"?(\w[\s\w-]+)"?', line, re.IGNORECASE)
            if match:
                project_name = match.group(1).lower()
                break

        assert project_name
        project_name = project_name.replace(' ', '-')
        self.target = self.targets[project_name]

    def _create_targets(self):
        targets = (
            GZDoomTarget(),
            QZDoomTarget(),
            LZDoomTarget(),
            RazeTarget(),
            ZandronumTarget(),
            PrBoomPlusTarget(),
            ChocolateDoomTarget(),
            CrispyDoomTarget(),
            DevilutionXTarget(),
            SladeTarget(),
        )

        self.targets = {target.name: target for target in targets}

    def _parse_arguments(self, args: list):
        assert self.targets

        parser = argparse.ArgumentParser(description='*ZDoom binary dependencies for macOS')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--target', choices=self.targets.keys(), help='target to build')
        group.add_argument('--source-path', metavar='path', help='path to target\'s source code')

        group = parser.add_argument_group()
        group.add_argument('--xcode', action='store_true', help='generate Xcode project instead of build')
        group.add_argument('--checkout-commit', metavar='commit',
                           help='target\'s source code commit or tag to checkout')
        group.add_argument('--build-path', metavar='path', help='target build path')
        group.add_argument('--sdk-path', metavar='path', help='path to macOS SDK')
        group.add_argument('--os-version', metavar='version', default='10.9', help='macOS deployment version')

        return parser.parse_args(args)


if __name__ == '__main__':
    Builder(sys.argv[1:]).run()
