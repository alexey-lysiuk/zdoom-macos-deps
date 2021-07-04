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

import copy
from distutils.version import StrictVersion
import os
from platform import machine
import re
import shutil
import subprocess
import typing

from ..utility import CommandLineOptions, symlink_directory, OS_VERSION_X86_64, OS_VERSION_ARM64
from ..state import BuildState


class Target:
    DESTINATION_DEPS = 0
    DESTINATION_OUTPUT = 1

    def __init__(self, name=None):
        self.name = name
        self.destination = self.DESTINATION_DEPS

        self.multi_platform = False
        self.unsupported_architectures = ()

    def prepare_source(self, state: BuildState):
        pass

    def detect(self, state: BuildState) -> bool:
        return False

    def configure(self, state: BuildState):
        pass

    def build(self, state: BuildState):
        pass

    def post_build(self, state: BuildState):
        pass


class BuildTarget(Target):
    def __init__(self, name=None):
        super().__init__(name)

        self.src_root = ''
        self.environment = os.environ.copy()
        self.options = CommandLineOptions()
        self.multi_platform = True

        self.os_version = dict()
        self.os_version['x86_64'] = OS_VERSION_X86_64
        self.os_version['arm64'] = OS_VERSION_ARM64

        self.sdk_version = dict()
        self.sdk_version['x86_64'] = OS_VERSION_X86_64
        self.sdk_version['arm64'] = OS_VERSION_ARM64

    def configure(self, state: BuildState):
        os_version = state.os_version()
        if os_version and os_version < self.os_version[state.architecture()]:
            raise RuntimeError('Minimum OS version requirement is not met')

        sdk_path = state.sdk_path()
        if sdk_path:
            match = re.search(r'/MacOSX(\d+.\d+).sdk', str(sdk_path), re.IGNORECASE)
            if match and StrictVersion(match[1]) < self.sdk_version[state.architecture()]:
                raise RuntimeError('Minimum SDK version requirement is not met')

        os.makedirs(state.build_path, exist_ok=True)

        env = self.environment
        env['PATH'] = os.pathsep.join([
            str(state.bin_path),
            env['PATH'],
            '/Applications/CMake.app/Contents/bin'
        ])

        if state.xcode:
            return

        env['CC'] = state.c_compiler()
        env['CXX'] = state.cxx_compiler()

        for prefix in ('CPP', 'C', 'CXX', 'OBJC', 'OBJCXX'):
            varname = f'{prefix}FLAGS'

            self._update_env(varname, f'-I{state.include_path}')
            self._set_sdk(state, varname)
            self._set_os_version(state, varname)

        ldflags = 'LDFLAGS'

        self._update_env(ldflags, f'-L{state.lib_path}')
        self._set_sdk(state, ldflags)
        self._set_os_version(state, ldflags)

    def _update_env(self, name: str, value: str):
        env = self.environment
        env[name] = env[name] + ' ' + value if name in env else value

    def _set_sdk(self, state: BuildState, varname: str):
        sdk_path = state.sdk_path()
        if sdk_path:
            self._update_env(varname, f'-isysroot {sdk_path}')

    def _set_os_version(self, state: BuildState, varname: str):
        os_version = state.os_version()
        if os_version:
            self._update_env(varname, '-mmacosx-version-min=' + str(os_version))

    def install(self, state: BuildState, options: CommandLineOptions = None, tool: str = 'gmake'):
        if state.xcode:
            return

        if os.path.exists(state.install_path):
            shutil.rmtree(state.install_path)

        args = [tool, 'install']
        args += options and options.to_list() or []

        subprocess.check_call(args, cwd=state.build_path, env=self.environment)

        self.update_pc_files(state)

    @staticmethod
    def update_text_file(path: str, processor: typing.Callable = None):
        with open(path, 'r') as f:
            content = f.readlines()

        patched_content = []

        for line in content:
            patched_line = processor(line) if processor else line

            if patched_line:
                patched_content.append(patched_line)

        with open(path, 'w') as f:
            f.writelines(patched_content)

    @staticmethod
    def _update_variables_file(path: str, prefix_value: str, processor: typing.Callable = None, quotes: bool = True):
        prefix = 'prefix='
        exec_prefix = 'exec_prefix='
        includedir = 'includedir='
        libdir = 'libdir='

        def quote(value: str) -> str:
            return f'"{value}"' if quotes else value

        def patch_proc(line: str) -> str:
            patched_line = line

            if line.startswith(prefix):
                patched_line = prefix + quote(prefix_value) + os.linesep
            elif line.startswith(exec_prefix):
                patched_line = exec_prefix + quote('${prefix}') + os.linesep
            elif line.startswith(includedir):
                patched_line = includedir + quote('${prefix}/include') + os.linesep
            elif line.startswith(libdir):
                patched_line = libdir + quote('${exec_prefix}/lib') + os.linesep

            if processor:
                patched_line = processor(path, patched_line)

            return patched_line

        BuildTarget.update_text_file(path, patch_proc)

    @staticmethod
    def update_config_script(path: str, processor: typing.Callable = None):
        BuildTarget._update_variables_file(path, r'$(cd "${0%/*}/.."; pwd)', processor)

    @staticmethod
    def update_pc_file(path: str, processor: typing.Callable = None):
        BuildTarget._update_variables_file(path, '', processor, quotes=False)

    def update_pc_files(self, state: BuildState):
        for root, _, files in os.walk(state.install_path, followlinks=True):
            for filename in files:
                if filename.endswith('.pc'):
                    file_path = root + os.sep + filename
                    BuildTarget.update_pc_file(file_path, self._process_pkg_config)

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        assert pcfile
        return line

    def write_pc_file(self, state: BuildState,
                      filename=None, name=None, description=None, version='',
                      requires='', requires_private='', libs='', libs_private='', cflags=''):
        pkgconfig_path = state.install_path + '/lib/pkgconfig/'
        os.makedirs(pkgconfig_path, exist_ok=True)

        if not filename:
            filename = self.name + '.pc'
        if not name:
            name = self.name
        if not description:
            description = self.name
        if not libs:
            libs = '-l' + self.name

        pc_content = f'''prefix=
exec_prefix=${{prefix}}
libdir=${{exec_prefix}}/lib
includedir=${{prefix}}/include

Name: {name}
Description: {description}
Version: {version}
Requires: {requires}
Requires.private: {requires_private}
Libs: -L${{libdir}} {libs}
Libs.private: {libs_private}
Cflags: -I${{includedir}} {cflags}
'''
        with open(pkgconfig_path + filename, 'w') as f:
            f.write(pc_content)

    @staticmethod
    def make_platform_header(state: BuildState, header: str):
        include_path = state.install_path + os.sep + 'include' + os.sep
        header_parts = header.rsplit(os.sep, 1)

        if len(header_parts) == 1:
            header_parts.insert(0, '')

        common_header = include_path + header
        platform_header = f'{include_path}{header_parts[0]}/_aedi_{state.architecture()}_{header_parts[1]}'
        shutil.move(common_header, platform_header)

        with open(common_header, 'w') as f:
            f.write(f'''
#pragma once

#if defined(__x86_64__)
#   include "_aedi_x86_64_{header_parts[1]}"
#elif defined(__aarch64__)
#   include "_aedi_arm64_{header_parts[1]}"
#else
#   error Unknown architecture
#endif
''')

    def copy_to_bin(self, state: BuildState, filename: str = None, new_filename: str = None):
        bin_path = state.install_path + '/bin/'
        os.makedirs(bin_path, exist_ok=True)

        if not filename:
            filename = self.name
        if not new_filename:
            new_filename = filename

        src_path = state.build_path + filename
        dst_path = bin_path + new_filename
        shutil.copy(src_path, dst_path)


class MakeTarget(BuildTarget):
    def __init__(self, name=None):
        super().__init__(name)
        self.tool = 'gmake'

    def configure(self, state: BuildState):
        super().configure(state)

        symlink_directory(state.source, state.build_path)

    def build(self, state: BuildState):
        assert not state.xcode

        args = [
            self.tool,
            '-j', state.jobs,
            'CC=' + state.c_compiler(),
            'CXX=' + state.cxx_compiler(),
        ]
        args += self.options.to_list()

        work_path = state.build_path + self.src_root
        subprocess.check_call(args, cwd=work_path, env=self.environment)


class ConfigureMakeTarget(BuildTarget):
    def __init__(self, name=None):
        super().__init__(name)
        self.make = MakeTarget(name)

    def configure(self, state: BuildState):
        super().configure(state)
        self.make.configure(state)

        work_path = state.build_path + self.src_root
        configure_path = work_path + os.sep + 'configure'

        common_args = [
            configure_path,
            '--prefix=' + state.install_path,
        ]
        common_args += self.options.to_list()

        disable_dependency_tracking = '--disable-dependency-tracking'
        host = '--host=' + state.host()

        args = copy.copy(common_args)
        args.append(host)
        args.append(disable_dependency_tracking)

        try:
            # Try with host and disabled dependency tracking first
            subprocess.check_call(args, cwd=work_path, env=self.environment)
        except subprocess.CalledProcessError:
            # If it fails, try with disabled dependency tracking only
            args = copy.copy(common_args)
            args.append(disable_dependency_tracking)

            try:
                subprocess.check_call(args, cwd=work_path, env=self.environment)
            except subprocess.CalledProcessError:
                # Use only common command line arguments
                subprocess.check_call(common_args, cwd=work_path, env=self.environment)

    def build(self, state: BuildState):
        assert not state.xcode
        self.make.build(state)


class CMakeTarget(BuildTarget):
    def __init__(self, name=None):
        super().__init__(name)

    def detect(self, state: BuildState) -> bool:
        src_root = self.src_root and os.sep + self.src_root or ''
        cmakelists_path = state.source + src_root + os.sep + 'CMakeLists.txt'

        if not os.path.exists(cmakelists_path):
            return False

        for line in open(cmakelists_path).readlines():
            project_name = CMakeTarget._extract_project_name(line)
            if project_name:
                project_name = project_name.lower()
                project_name = project_name.replace(' ', '-')
                break
        else:
            return False

        return project_name == self.name

    @staticmethod
    def _extract_project_name(line: str):
        project_name = None

        # Try to get project name without whitespaces in it
        match = re.search(r'project\s*\(\s*(\w[\w-]+)', line, re.IGNORECASE)

        if not match:
            # Try to get project name that contains whitespaces
            match = re.search(r'project\s*\(\s*"?(\w[\s\w-]+)"?', line, re.IGNORECASE)

        if match:
            project_name = match.group(1)

        return project_name

    def configure(self, state: BuildState):
        super().configure(state)

        args = [
            'cmake',
            '-DCMAKE_BUILD_TYPE=Release',
            f'-DCMAKE_INSTALL_PREFIX={state.install_path}',
            f'-DCMAKE_PREFIX_PATH={state.prefix_path}',
        ]

        if state.xcode:
            args.append('-GXcode')
        else:
            args.append('-GUnix Makefiles')
            args.append(f'-DCMAKE_C_COMPILER={state.c_compiler()}')
            args.append(f'-DCMAKE_CXX_COMPILER={state.cxx_compiler()}')

            architecture = state.architecture()
            if architecture != machine():
                args.append('-DCMAKE_SYSTEM_NAME=Darwin')
                args.append('-DCMAKE_SYSTEM_PROCESSOR=' + 'aarch64' if architecture == 'arm64' else architecture)

        os_version = state.os_version()
        if os_version:
            args.append('-DCMAKE_OSX_DEPLOYMENT_TARGET=' + str(os_version))

        sdk_path = state.sdk_path()
        if sdk_path:
            args.append(f'-DCMAKE_OSX_SYSROOT={sdk_path}')

        args += self.options.to_list(CommandLineOptions.CMAKE_RULES)
        args.append(state.source / self.src_root)

        subprocess.check_call(args, cwd=state.build_path, env=self.environment)

    def build(self, state: BuildState):
        if state.xcode:
            args = ('cmake', '--open', '.')
        else:
            args = ['gmake', '-j', state.jobs]

            if state.verbose:
                args.append('VERBOSE=1')

        subprocess.check_call(args, cwd=state.build_path, env=self.environment)


class ConfigureMakeDependencyTarget(ConfigureMakeTarget):
    def __init__(self, name=None):
        super().__init__(name)

    def post_build(self, state: BuildState):
        self.install(state)


class ConfigureMakeStaticDependencyTarget(ConfigureMakeDependencyTarget):
    def __init__(self, name=None):
        super().__init__(name)

        self.options['--enable-shared'] = 'no'


class CMakeStaticDependencyTarget(CMakeTarget):
    def __init__(self, name=None):
        super().__init__(name)

        # Set commonly used variables for static libraries
        opts = self.options
        opts['BUILD_SHARED_LIBS'] = 'NO'
        opts['ENABLE_SHARED'] = 'NO'
        opts['LIBTYPE'] = 'STATIC'

    def post_build(self, state: BuildState):
        self.install(state)

    def keep_module_target(self, state: BuildState, target: str):
        import_patterns = (
            r'list\s*\(APPEND\s+_IMPORT_CHECK_TARGETS\s+(?P<target>\w+::\w+)[\s)]',
            r'list\s*\(APPEND\s+_IMPORT_CHECK_FILES_FOR_(?P<target>\w+::\w+)\s',
        )
        import_regexes = [re.compile(regex, re.IGNORECASE) for regex in import_patterns]

        def _keep_target(line: str):
            for regex in import_regexes:
                match = regex.match(line)

                if not match:
                    continue
                else:
                    if match.group('target') != target:
                        return None

            return line

        module = 'targets-release.cmake'

        for probe_module in (module, self.name + module):
            module_path = f'{state.install_path}/lib/cmake/{self.name}/{probe_module}'

            if os.path.exists(module_path):
                self.update_text_file(module_path, _keep_target)
