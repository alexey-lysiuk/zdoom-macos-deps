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
import os
from platform import machine
import shutil
import subprocess

from .base import CMakeTarget, MakeTarget, Target
from ..state import BuildState
from ..utility import symlink_directory


class MakeMainTarget(MakeTarget):
    def __init__(self, name=None):
        super().__init__(name)

        self.destination = self.DESTINATION_OUTPUT


class CMakeMainTarget(CMakeTarget):
    def __init__(self, name=None):
        super().__init__(name)

        self.destination = self.DESTINATION_OUTPUT
        self.outputs = (self.name + '.app',)

    def post_build(self, state: BuildState):
        if state.xcode:
            return

        if os.path.exists(state.install_path):
            shutil.rmtree(state.install_path)

        os.makedirs(state.install_path)

        for output in self.outputs:
            src = state.build_path + output
            dst_sep_pos = output.rfind(os.sep)
            dst = state.install_path + os.sep + (output if dst_sep_pos == -1 else output[dst_sep_pos + 1:])

            copy_func = shutil.copytree if os.path.isdir(src) else shutil.copy
            copy_func(src, dst)

    def _force_cross_compilation(self, state: BuildState):
        if state.architecture() == machine():
            return

        opts = self.options
        opts['FORCE_CROSSCOMPILE'] = 'YES'
        opts['IMPORT_EXECUTABLES'] = state.native_build_path + 'ImportExecutables.cmake'


class ZDoomBaseTarget(CMakeMainTarget):
    def __init__(self, name=None):
        super().__init__(name)

    def configure(self, state: BuildState):
        opts = self.options
        opts['CMAKE_EXE_LINKER_FLAGS'] = state.run_pkg_config('--libs', 'fluidsynth', 'libmpg123')
        opts['CMAKE_MODULE_PATH'] = state.lib_path + 'cmake/ZMusic'
        opts['PK3_QUIET_ZIPDIR'] = 'YES'
        opts['DYN_OPENAL'] = 'NO'
        # Explicit OpenAL configuration to avoid selection of Apple's framework
        opts['OPENAL_INCLUDE_DIR'] = state.include_path + 'AL'
        opts['OPENAL_LIBRARY'] = state.lib_path + 'libopenal.a'

        self._force_cross_compilation(state)

        super().configure(state)


class ZDoomVulkanBaseTarget(ZDoomBaseTarget):
    def __init__(self, name=None):
        super().__init__(name)

    def post_build(self, state: BuildState):
        # Put MoltenVK library into application bundle
        molten_lib = 'libMoltenVK.dylib'
        src_path = state.lib_path + molten_lib
        dst_path = state.build_path

        if state.xcode:
            # TODO: Support other configurations
            dst_path += 'Debug' + os.sep

        dst_path += self.name + '.app/Contents/MacOS' + os.sep
        os.makedirs(dst_path, exist_ok=True)

        dst_path += molten_lib

        if not os.path.exists(dst_path):
            copy_func = state.xcode and os.symlink or shutil.copy
            copy_func(src_path, dst_path)

        super().post_build(state)


class GZDoomTarget(ZDoomVulkanBaseTarget):
    def __init__(self, name='gzdoom'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/coelckers/gzdoom.git')


class QZDoomTarget(ZDoomVulkanBaseTarget):
    def __init__(self, name='qzdoom'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/madame-rachelle/qzdoom.git')


class LZDoomTarget(ZDoomVulkanBaseTarget):
    def __init__(self, name='lzdoom'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/drfrag666/gzdoom.git')

    def detect(self, state: BuildState) -> bool:
        return super().detect(state) and not os.path.exists(state.source + 'libraries/zmusic')


class LZDoom3Target(ZDoomBaseTarget):
    def __init__(self, name='lzdoom3'):
        super().__init__(name)
        self.unsupported_architectures = ('arm64',)

        opts = self.options
        opts['DYN_FLUIDSYNTH'] = 'NO'
        opts['DYN_MPG123'] = 'NO'
        opts['DYN_SNDFILE'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/drfrag666/gzdoom.git', branch='g3.3mgw')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'ico_lzdoom.png') and os.path.exists(state.source + 'libraries/zmusic')


class RazeTarget(ZDoomVulkanBaseTarget):
    def __init__(self, name='raze'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/coelckers/Raze.git')


class AccTarget(CMakeMainTarget):
    def __init__(self, name='acc'):
        super().__init__(name)
        self.outputs = ('acc',)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/rheit/acc.git')


class SladeTarget(CMakeMainTarget):
    def __init__(self, name='slade'):
        super().__init__(name)

        # This should match the actual version of WxWidgets
        self.os_version['x86_64'] = StrictVersion('10.10')
        self.sdk_version['x86_64'] = StrictVersion('10.11')

    def prepare_source(self, state: BuildState):
        # TODO: support both stable and master branches
        state.checkout_git('https://github.com/sirjuddington/SLADE.git', branch='stable')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'SLADE-osx.icns')

    def configure(self, state: BuildState):
        opts = self.options
        opts['CMAKE_C_FLAGS'] = opts['CMAKE_CXX_FLAGS'] = '-DNOCURL -I' + state.include_path
        opts['CMAKE_EXE_LINKER_FLAGS'] = \
            state.run_pkg_config('--libs', 'fluidsynth', 'libtiff-4', 'openal', 'vorbisfile')
        opts['wxWidgets_USE_STATIC'] = 'YES'
        opts['WX_GTK3'] = 'NO'
        opts['SFML_STATIC'] = 'YES'

        super().configure(state)


class PrBoomPlusTarget(CMakeMainTarget):
    def __init__(self, name='prboom-plus'):
        super().__init__(name)
        self.src_root = 'prboom2'
        self.outputs = ('Launcher.app',)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/coelckers/prboom-plus.git')

    def configure(self, state: BuildState):
        opts = self.options
        opts['CMAKE_C_FLAGS'] = '-D_FILE_OFFSET_BITS=64'
        opts['CMAKE_EXE_LINKER_FLAGS'] = state.run_pkg_config('--libs', 'SDL2_mixer', 'SDL2_image')
        opts['CMAKE_POLICY_DEFAULT_CMP0056'] = 'NEW'

        self._force_cross_compilation(state)

        super().configure(state)


class DsdaDoom(PrBoomPlusTarget):
    def __init__(self, name='dsda-doom'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/kraflab/dsda-doom.git')


class ChocolateDoomBaseTarget(CMakeMainTarget):
    def __init__(self, name=None):
        super().__init__(name)

    def configure(self, state: BuildState):
        self.options['CMAKE_EXE_LINKER_FLAGS'] = state.run_pkg_config('--libs', 'SDL2_mixer')

        super().configure(state)

    def _fill_outputs(self, exe_prefix: str):
        self.outputs = (
            f'src/{exe_prefix}-doom',
            f'src/{exe_prefix}-heretic',
            f'src/{exe_prefix}-hexen',
            f'src/{exe_prefix}-server',
            f'src/{exe_prefix}-setup',
            f'src/{exe_prefix}-strife',
            f'src/midiread',
            f'src/mus2mid',
        )


class ChocolateDoomTarget(ChocolateDoomBaseTarget):
    def __init__(self, name='chocolate-doom'):
        super().__init__(name)
        self._fill_outputs('chocolate')

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/chocolate-doom/chocolate-doom.git')


class CrispyDoomTarget(ChocolateDoomBaseTarget):
    def __init__(self, name='crispy-doom'):
        super().__init__(name)
        self._fill_outputs('crispy')

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/fabiangreffrath/crispy-doom.git')


class RudeTarget(ChocolateDoomBaseTarget):
    def __init__(self, name='rude'):
        super().__init__(name)
        self._fill_outputs('rude')

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/drfrag666/RUDE.git')

    def post_build(self, state: BuildState):
        super().post_build(state)
        shutil.copy(state.source + '/data/rude.wad', state.install_path)


class WoofTarget(ChocolateDoomBaseTarget):
    def __init__(self, name='woof'):
        super().__init__(name)
        self.outputs = ('Source/woof',)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/fabiangreffrath/woof.git')


class DoomRetroTarget(CMakeMainTarget):
    def __init__(self, name='doomretro'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/bradharding/doomretro.git')


class Doom64EXTarget(CMakeMainTarget):
    def __init__(self, name='doom64ex'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/svkaiser/Doom64EX.git')

    def configure(self, state: BuildState):
        opts = self.options
        opts['ENABLE_SYSTEM_FLUIDSYNTH'] = 'YES'
        opts['CMAKE_EXE_LINKER_FLAGS'] = state.run_pkg_config('--libs', 'SDL2', 'fluidsynth')

        super().configure(state)


class DevilutionXTarget(CMakeMainTarget):
    def __init__(self, name='devilutionx'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/diasurgical/devilutionX.git')

    def configure(self, state: BuildState):
        self.options['CMAKE_EXE_LINKER_FLAGS'] = state.run_pkg_config('--libs', 'SDL2_mixer', 'SDL2_ttf')

        super().configure(state)

        # Remove version file that is included erroneously because of case-insensitive file system
        version_file = state.build_path + '_deps/libzt-src/ext/ZeroTierOne/ext/miniupnpc/VERSION'

        if os.path.exists(version_file):
            os.unlink(version_file)


class EDuke32Target(MakeMainTarget):
    def __init__(self, name='eduke32'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://voidpoint.io/terminx/eduke32.git')

    def detect(self, state: BuildState) -> bool:
        def has_bundle(name: str) -> bool:
            probe_path = f'{state.source}/platform/Apple/bundles/{name}.app'
            return os.path.exists(probe_path)

        return has_bundle('EDuke32') and not has_bundle('NBlood')

    def configure(self, state: BuildState):
        super().configure(state)

        # Fix missing definition when building with SDK older than 10.12
        self._update_env('CXXFLAGS', '-DCLOCK_MONOTONIC=0')


class NBloodTarget(EDuke32Target):
    def __init__(self, name='nblood'):
        super().__init__(name)
        self.tool = 'gmake'

        for target in ('duke3d', 'sw', 'blood', 'rr', 'exhumed', 'tools'):
            self.options[target] = None

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/nukeykt/NBlood.git')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + os.sep + 'nblood.pk3')


class QuakespasmTarget(MakeMainTarget):
    def __init__(self, name='quakespasm'):
        super().__init__(name)

        self.src_root = 'Quake'

        # TODO: Use macOS specific Makefile which requires manual application bundle creation
        opts = self.options
        opts['USE_SDL2'] = '1'
        opts['USE_CODEC_FLAC'] = '1'
        opts['USE_CODEC_OPUS'] = '1'
        opts['USE_CODEC_MIKMOD'] = '1'
        opts['USE_CODEC_UMX'] = '1'
        # Add main() alias to workaround executable linking without macOS launcher
        opts['COMMON_LIBS'] = '-framework OpenGL -Wl,-alias -Wl,_SDL_main -Wl,_main'

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://git.code.sf.net/p/quakespasm/quakespasm')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + os.sep + 'Quakespasm.txt')


# class VkQuake2Target(Target):
class VkQuake2Target(MakeMainTarget):
    def __init__(self, name='vkquake2'):
        super().__init__(name)

        self.destination = self.DESTINATION_OUTPUT
        self.options['release'] = None
        self.src_root = 'macos'

    def prepare_source(self, state: BuildState):
        state.checkout_git('https://github.com/kondrak/vkQuake2.git')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + os.sep + 'vkQuake2.png')

    def configure(self, state: BuildState):
        super().configure(state)

        # Prepare directory structure like in Vulkan SDK
        vulkan_path = state.build_path + 'vulkan_sdk' + os.sep
        vulkan_macos_path = vulkan_path + 'macOS' + os.sep
        vulkan_include_path = vulkan_macos_path + 'include'
        vulkan_lib_path = vulkan_macos_path + 'lib'

        os.makedirs(vulkan_macos_path, exist_ok=True)

        if not os.path.exists(vulkan_include_path):
            os.symlink(state.include_path, vulkan_include_path)

        if not os.path.exists(vulkan_lib_path):
            os.symlink(state.lib_path, vulkan_lib_path)

        self.environment['VULKAN_SDK'] = vulkan_path

        # os.makedirs(state.build_path, exist_ok=True)
        # symlink_directory(state.source, state.build_path)

    def build(self, state: BuildState):
        if state.xcode:
            args = ('open', state.build_path + 'macos/vkQuake2.xcworkspace')
            subprocess.run(args, check=True, env=self.environment)
        else:
            super().build(state)

        # # Prepare directory structure like in Vulkan SDK
        # vulkan_path = state.build_path + 'vulkan_sdk' + os.sep
        # vulkan_macos_path = vulkan_path + 'macOS' + os.sep
        # vulkan_include_path = vulkan_macos_path + 'include'
        # vulkan_lib_path = vulkan_macos_path + 'lib'
        #
        # os.makedirs(vulkan_macos_path, exist_ok=True)
        #
        # if not os.path.exists(vulkan_include_path):
        #     os.symlink(state.include_path, vulkan_include_path)
        #
        # if not os.path.exists(vulkan_lib_path):
        #     os.symlink(state.lib_path, vulkan_lib_path)

        # # Open or build Xcode project
        # environment = os.environ.copy()
        # environment['VULKAN_SDK'] = vulkan_path

        # if state.xcode:
        #     args = ('open', state.build_path + 'macos/vkQuake2.xcworkspace')
        # else:
        #     args = ('make', 'release-xcode')
        #
        # subprocess.run(args, check=True, cwd=state.build_path + 'macos', env=environment)

    def post_build(self, state: BuildState):
        if state.xcode:
            return

        if os.path.exists(state.install_path):
            shutil.rmtree(state.install_path)

        shutil.copytree(state.build_path + 'macOS/vkQuake2', state.install_path)
        shutil.copy(state.prefix_path + '/lib/libMoltenVK.dylib', state.install_path)

        executable = state.install_path + 'quake2'
        args = (
            'install_name_tool',
            '-add_rpath', '@loader_path"',
            executable
        )
        subprocess.run(args, check=True)
