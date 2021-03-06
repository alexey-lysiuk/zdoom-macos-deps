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

from .base import *
from ..state import BuildState


class DumbTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='dumb'):
        super().__init__(name)

        opts = self.options
        opts['BUILD_ALLEGRO4'] = 'NO'
        opts['BUILD_EXAMPLES'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/kode54/dumb/archive/2.0.3.tar.gz',
            '99bfac926aeb8d476562303312d9f47fd05b43803050cd889b44da34a9b2a4f9')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'include/dumb.h')

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        return 'Libs: -L${libdir} -ldumb\n' if line.startswith('Libs:') else line


class ExpatTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='expat'):
        super().__init__(name)

        opts = self.options
        opts['EXPAT_BUILD_EXAMPLES'] = 'NO'
        opts['EXPAT_BUILD_TESTS'] = 'NO'
        opts['EXPAT_BUILD_TOOLS'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/libexpat/libexpat/releases/download/R_2_4_1/expat-2.4.1.tar.xz',
            'cf032d0dba9b928636548e32b327a2d66b1aab63c4f4a13dd132c2d1d2f2fb6a')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'expat.pc.in')


class FmtTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='fmt'):
        super().__init__(name)

        opts = self.options
        opts['FMT_DOC'] = 'NO'
        opts['FMT_TEST'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/fmtlib/fmt/archive/refs/tags/7.1.3.tar.gz',
            '5cae7072042b3043e12d53d50ef404bbb76949dad1de368d7f993a15c8c05ecc')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'include/fmt/format.h')


class FreeImageTarget(MakeTarget):
    def __init__(self, name='freeimage'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/freeimage/Source%20Distribution/3.18.0/FreeImage3180.zip',
            'f41379682f9ada94ea7b34fe86bf9ee00935a3147be41b6569c9605a53e438fd',
            patches='freeimage-fix-arm64')

    HEADER_FILE = 'Source/FreeImage.h'

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + self.HEADER_FILE)

    def configure(self, state: BuildState):
        super().configure(state)

        # These flags are copied from Makefile.gnu
        common_flags = ' -O3 -fPIC -fexceptions -fvisibility=hidden'

        env = self.environment
        env['CFLAGS'] += common_flags + ' -std=gnu89 -Wno-implicit-function-declaration'
        env['CXXFLAGS'] += common_flags + ' -Wno-ctor-dtor-privacy'

        for option in ('-f', 'Makefile.gnu', 'libfreeimage.a'):
            self.options[option] = None

    def post_build(self, state: BuildState):
        include_path = state.install_path + 'include'
        os.makedirs(include_path, exist_ok=True)
        shutil.copy(state.build_path + self.HEADER_FILE, include_path)

        lib_path = state.install_path + 'lib'
        os.makedirs(lib_path, exist_ok=True)
        shutil.copy(state.build_path + 'libfreeimage.a', lib_path)

        self.write_pc_file(state, version='3.18.0', libs='-lfreeimage -lc++')


class FreeTypeTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='freetype'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/freetype/freetype2/2.10.4/freetype-2.10.4.tar.xz',
            '86a854d8905b19698bbc8f23b860bc104246ce4854dcea8e3b0fb21284f75784')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'include/freetype/freetype.h')

    def post_build(self, state: BuildState):
        super().post_build(state)

        bin_path = state.install_path + 'bin'
        os.makedirs(bin_path)
        shutil.copy(state.patch_path + 'freetype-config', bin_path)


class FtglTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='ftgl'):
        super().__init__(name)

        opts = self.options
        opts['--with-glut-inc'] = '/dev/null'
        opts['--with-glut-lib'] = '/dev/null'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/ftgl/FTGL%20Source/2.1.3~rc5/ftgl-2.1.3-rc5.tar.gz',
            '5458d62122454869572d39f8aa85745fc05d5518001bcefa63bd6cbb8d26565b',
            patches='ftgl-support-arm64')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'ftgl.pc.in')


class GlewTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='glew'):
        super().__init__(name)

        self.src_root = 'build/cmake'
        self.options['BUILD_UTILS'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/nigels-com/glew/releases/download/glew-2.2.0/glew-2.2.0.tgz',
            'd4fc82893cfb00109578d0a1a2337fb8ca335b3ceccf97b97e5cc7f08e4353e1')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'glew.pc.in')

    LINKER_FLAGS = '-framework OpenGL'

    def post_build(self, state: BuildState):
        super().post_build(state)

        def update_linker_flags(line: str):
            link_var = '  INTERFACE_LINK_LIBRARIES '

            if line.startswith(link_var):
                return f'{link_var}"{GlewTarget.LINKER_FLAGS}"\n'

            return line

        cmake_module = state.install_path + 'lib/cmake/glew/glew-targets.cmake'
        self.update_text_file(cmake_module, update_linker_flags)

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        libs = 'Libs:'

        if line.startswith(libs):
            return libs + ' -L${libdir} -lGLEW ' + GlewTarget.LINKER_FLAGS + os.linesep

        return line


class LuaTarget(MakeTarget):
    def __init__(self, name='lua'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://www.lua.org/ftp/lua-5.4.3.tar.gz',
            'f8612276169e3bfcbcfb8f226195bfc6e466fe13042f1076cbde92b7ec96bbfb')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'src/lua.h')

    def post_build(self, state: BuildState):
        self.options['INSTALL_TOP'] = state.install_path
        self.install(state, self.options)


class LzmaTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='lzma'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://tukaani.org/xz/xz-5.2.5.tar.gz',
            'f6f4910fd033078738bd82bfba4f49219d03b17eb0794eb91efbae419f4aba10',
            patches='lzma-add-cmake')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'src/liblzma/liblzma.pc.in')

    def post_build(self, state: BuildState):
        super().post_build(state)

        self.write_pc_file(state, 'liblzma.pc', name='liblzma',
                           description='General purpose data compression library',
                           version='5.2.5', libs='-llzma')


class MadTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='mad'):
        super().__init__(name)
        self.options['--enable-fpm'] = '64bit'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/mad/libmad/0.15.1b/libmad-0.15.1b.tar.gz',
            'bbfac3ed6bfbc2823d3775ebb931087371e142bb0e9bb1bee51a76a6e0078690',
            patches='mad-support-arm64')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'mad.h')

    def post_build(self, state: BuildState):
        super().post_build(state)
        self.write_pc_file(state, description='MPEG Audio Decoder', version='0.15.1b')


class MikmodTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='mikmod'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/mikmod/libmikmod/3.3.11.1/libmikmod-3.3.11.1.tar.gz',
            'ad9d64dfc8f83684876419ea7cd4ff4a41d8bcd8c23ef37ecb3a200a16b46d19')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'libmikmod.pc.in')

    def post_build(self, state: BuildState):
        super().post_build(state)
        self.update_config_script(state.install_path + '/bin/libmikmod-config')


class ModPlugTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='modplug'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/modplug-xmms/libmodplug/0.8.9.0/libmodplug-0.8.9.0.tar.gz',
            '457ca5a6c179656d66c01505c0d95fafaead4329b9dbaa0f997d00a3508ad9de')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'libmodplug.pc.in')

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        libs_private = 'Libs.private:'

        if line.startswith(libs_private):
            return libs_private + ' -lc++\n'

        return line


class OpusFileTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='opusfile'):
        super().__init__(name)
        self.options['--enable-http'] = 'no'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://ftp.osuosl.org/pub/xiph/releases/opus/opusfile-0.12.tar.gz',
            '118d8601c12dd6a44f52423e68ca9083cc9f2bfe72da7a8c1acb22a80ae3550b')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'opusfile.pc.in')


class PngTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='png'):
        super().__init__(name)

        opts = self.options
        opts['PNG_ARM_NEON'] = 'on'
        opts['PNG_SHARED'] = 'OFF'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/libpng/libpng-1.6.37.tar.xz',
            '505e70834d35383537b6491e7ae8641f1a4bed1876dbfe361201fc80868d88ca')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'libpng.pc.in')

    def post_build(self, state: BuildState):
        super().post_build(state)
        self.update_config_script(state.install_path + '/bin/libpng16-config')


class PortMidiTarget(CMakeTarget):
    def __init__(self, name='portmidi'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://downloads.sourceforge.net/project/portmedia/portmidi/217/portmidi-src-217.zip',
            '08e9a892bd80bdb1115213fb72dc29a7bf2ff108b378180586aa65f3cfd42e0f',
            patches='portmidi-modernize-cmake')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'pm_common/portmidi.h')

    def post_build(self, state: BuildState):
        if os.path.exists(state.install_path):
            shutil.rmtree(state.install_path)

        include_path = state.install_path + os.sep + 'include'
        os.makedirs(include_path)
        shutil.copy(state.source + 'pm_common/portmidi.h', include_path)
        shutil.copy(state.source + 'porttime/porttime.h', include_path)

        lib_path = state.install_path + os.sep + 'lib' + os.sep
        os.makedirs(lib_path)
        shutil.copy(state.build_path + 'libportmidi_s.a', lib_path + 'libportmidi.a')


class SamplerateTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='samplerate'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/libsndfile/libsamplerate/releases/download/0.2.1/libsamplerate-0.2.1.tar.bz2',
            'f6323b5e234753579d70a0af27796dde4ebeddf58aae4be598e39b3cee00c90a',
            patches='samplerate-support-arm64')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'samplerate.pc.in')


class Sdl2Target(CMakeStaticDependencyTarget):
    def __init__(self, name='sdl2'):
        super().__init__(name)

        # Need to have uniform settings for x86_64 and arm64 because of linking with Metal framework
        # TODO: Remove this when default target for x64 will become 10.11+
        opts = self.options
        opts['VIDEO_VULKAN'] = 'NO'
        opts['VIDEO_METAL'] = 'NO'
        opts['RENDER_METAL'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://libsdl.org/release/SDL2-2.0.14.tar.gz',
            'd8215b571a581be1332d2106f8036fcb03d12a70bae01e20f424976d275432bc')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'sdl2.pc.in')

    FRAMEWORKS = '-framework AudioToolbox -framework AVFoundation -framework Carbon -framework Cocoa' \
        ' -framework CoreAudio -framework CoreFoundation -framework CoreVideo' \
        ' -framework ForceFeedback -framework Foundation -framework IOKit'
    LINKER_FLAGS = ' -L${libdir} -lSDL2 ' + FRAMEWORKS + os.linesep

    def post_build(self, state: BuildState):
        super().post_build(state)

        self.make_platform_header(state, 'SDL2/SDL_config.h')

        def update_sdl2_config(line: str):
            if line.startswith('      echo -L${exec_prefix}/lib'):
                return '      echo' + Sdl2Target.LINKER_FLAGS

            return line

        self.update_config_script(state.install_path + '/bin/sdl2-config', update_sdl2_config)

        def update_targets_cmake(line: str):
            if line.startswith('  INTERFACE_LINK_LIBRARIES '):
                return f'  INTERFACE_LINK_LIBRARIES "{Sdl2Target.FRAMEWORKS}"\n'
            else:
                line = line.replace('SDL2::SDL2-static', 'SDL2::SDL2')

            return line

        for suffix in ('', '-release'):
            file_path = f'{state.install_path}/lib/cmake/SDL2/SDL2Targets{suffix}.cmake'
            self.update_text_file(file_path, update_targets_cmake)

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        libs = 'Libs:'

        if line.startswith(libs):
            return libs + Sdl2Target.LINKER_FLAGS

        return line


class Sdl2ImageTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='sdl2_image'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://www.libsdl.org/projects/SDL_image/release/SDL2_image-2.0.5.tar.gz',
            'bdd5f6e026682f7d7e1be0b6051b209da2f402a2dd8bd1c4bd9c25ad263108d0')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'SDL2_image.pc.in')

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        return line + 'Requires.private: libwebp\n' if line.startswith('Requires:') else line


class Sdl2MixerTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='sdl2_mixer'):
        super().__init__(name)
        self.options['--enable-music-mod-mikmod'] = 'yes'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://www.libsdl.org/projects/SDL_mixer/release/SDL2_mixer-2.0.4.tar.gz',
            'b4cf5a382c061cd75081cf246c2aa2f9df8db04bdda8dcdc6b6cca55bede2419',
            patches='sdl2_mixer-fix-fluidsynth')

    def configure(self, state: BuildState):
        # Set LDFLAGS explicitly to help with FluidSynth and FLAC detection
        self.environment['LDFLAGS'] = state.run_pkg_config('--libs', 'fluidsynth')

        super().configure(state)

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'SDL2_mixer.pc.in')

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        if line.startswith('Requires:'):
            return line + 'Requires.private: fluidsynth libmikmod libmodplug libmpg123 opusfile vorbisfile\n'

        return line


class Sdl2NetTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='sdl2_net'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://www.libsdl.org/projects/SDL_net/release/SDL2_net-2.0.1.tar.gz',
            '15ce8a7e5a23dafe8177c8df6e6c79b6749a03fff1e8196742d3571657609d21')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'SDL2_net.pc.in')


class Sdl2TtfTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='sdl2_ttf'):
        super().__init__(name)
        self.options['VERSION'] = '2.0.15'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-2.0.15.tar.gz',
            'a9eceb1ad88c1f1545cd7bd28e7cbc0b2c14191d40238f531a15b01b1b22cd33',
            patches='sdl2_ttf-fix-cmake')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'SDL2_ttf.pc.in')

    def post_build(self, state: BuildState):
        super().post_build(state)
        shutil.move(state.install_path + 'SDL2_ttf.framework/Resources', state.install_path + 'lib/cmake/SDL2_ttf')

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        return line + 'Requires.private: freetype2\n' if line.startswith('Requires:') else line


class SodiumTarget(ConfigureMakeStaticDependencyTarget):
    def __init__(self, name='sodium'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://download.libsodium.org/libsodium/releases/libsodium-1.0.18.tar.gz',
            '6f504490b342a4f8a4c4a02fc9b866cbef8622d5df4e5452b46be121e46636c1')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'libsodium.pc.in')


class SfmlTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='sfml'):
        super().__init__(name)

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://www.sfml-dev.org/files/SFML-2.5.1-sources.zip',
            'bf1e0643acb92369b24572b703473af60bac82caf5af61e77c063b779471bb7f',
            patches='sfml-support-arm64')

    def configure(self, state: BuildState):
        opts = self.options
        opts['CMAKE_OSX_ARCHITECTURES'] = state.architecture()
        opts['SFML_USE_SYSTEM_DEPS'] = 'YES'
        opts['SFML_MISC_INSTALL_PREFIX'] = state.install_path + 'share/SFML'
        # Use OpenAL Soft instead of Apple's framework
        opts['OPENAL_INCLUDE_DIR'] = state.include_path + 'AL'
        opts['OPENAL_LIBRARY'] = state.lib_path + 'libopenal.a'

        super(SfmlTarget, self).configure(state)

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'libtiff-4.pc.in')


class TiffTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='tiff'):
        super().__init__(name)

        opts = self.options
        opts['cxx'] = 'NO'
        opts['lzma'] = 'YES'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://download.osgeo.org/libtiff/tiff-4.3.0.tar.gz',
            '0e46e5acb087ce7d1ac53cf4f56a09b221537fc86dfc5daaad1c2e89e1b37ac8',
            patches='tiff-remove-useless')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'libtiff-4.pc.in')

    @staticmethod
    def _process_pkg_config(pcfile: str, line: str) -> str:
        version = 'Version:'
        cflags = 'Cflags:'
        libs = 'Libs:'

        if line.startswith(version):
            return version + ' 4.3.0\n'
        elif line.startswith(cflags):
            return cflags + ' -I${includedir}\nRequires.private: libjpeg liblzma libwebp libzstd zlib\n'
        elif line.startswith(libs):
            return libs + ' -L${libdir} -ltiff\n'

        return line


class WebpTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='webp'):
        super().__init__(name)

        opts = self.options
        opts['WEBP_BUILD_ANIM_UTILS'] = 'NO'
        opts['WEBP_BUILD_CWEBP'] = 'NO'
        opts['WEBP_BUILD_DWEBP'] = 'NO'
        opts['WEBP_BUILD_GIF2WEBP'] = 'NO'
        opts['WEBP_BUILD_IMG2WEBP'] = 'NO'
        opts['WEBP_BUILD_VWEBP'] = 'NO'
        opts['WEBP_BUILD_WEBPINFO'] = 'NO'
        opts['WEBP_BUILD_WEBPMUX'] = 'NO'
        opts['WEBP_BUILD_EXTRAS'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-1.2.0.tar.gz',
            '2fc8bbde9f97f2ab403c0224fb9ca62b2e6852cbc519e91ceaa7c153ffd88a0c')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'src/libwebp.pc.in')

    def post_build(self, state: BuildState):
        super().post_build(state)

        shutil.copytree(state.install_path + 'share/WebP/cmake', state.install_path + 'lib/cmake/WebP')
        self.keep_module_target(state, 'WebP::webp')


class WxWidgetsTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='wxwidgets'):
        super().__init__(name)

        self.os_version['x86_64'] = StrictVersion('10.10')
        self.sdk_version['x86_64'] = StrictVersion('10.11')

        opts = self.options
        opts['wxBUILD_SHARED'] = 'NO'
        opts['wxUSE_LIBLZMA'] = 'YES'
        opts['wxUSE_LIBSDL'] = 'NO'
        opts['wxUSE_LIBJPEG'] = 'sys'
        opts['wxUSE_LIBPNG'] = 'sys'
        opts['wxUSE_LIBTIFF'] = 'sys'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/wxWidgets/wxWidgets/releases/download/v3.1.5/wxWidgets-3.1.5.tar.bz2',
            'd7b3666de33aa5c10ea41bb9405c40326e1aeb74ee725bb88f90f1d50270a224',
            patches='wxwidgets-library-suffix')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'wx-config.in')

    def post_build(self, state: BuildState):
        super().post_build(state)

        # Replace prefix in setup.h
        def patch_setup_h(line: str):
            prefix = '#define wxINSTALL_PREFIX '
            return f'{prefix}"/usr/local"\n' if line.startswith(prefix) else line

        setup_h_path = state.install_path + 'lib/wx/include/osx_cocoa-unicode-static-3.1/wx/setup.h'
        self.update_text_file(setup_h_path, patch_setup_h)

        # Fix a few wx-config entries
        def patch_wx_config(line: str):
            prefix = 'prefix=${input_option_prefix-${this_prefix:-'
            is_cross_func = 'is_cross() '
            is_cross_test = 'is_cross && target='
            output_option_cc = '[ -z "$output_option_cc" '
            output_option_cxx = '[ -z "$output_option_cxx" '
            output_option_ld = '[ -z "$output_option_ld" '
            ldlibs_gl = 'ldlibs_gl='

            if line.startswith(prefix):
                return prefix + '$(cd "${0%/*}/.."; pwd)}}\n'
            elif line.startswith(is_cross_func):
                return is_cross_func + '{ false; }\n'
            elif line.startswith(is_cross_test):
                return is_cross_test + '""\n'
            elif line.startswith(output_option_cc):
                return output_option_cc + '] || echo "gcc"\n'
            elif line.startswith(output_option_cxx):
                return output_option_cxx + '] || echo "g++"\n'
            elif line.startswith(output_option_ld):
                return output_option_ld + '] || echo "g++ -o"\n'
            elif line.startswith(ldlibs_gl):
                return ldlibs_gl + '"-lwx_baseu-3.1 -lwx_osx_cocoau_core-3.1 -framework OpenGL"\n'

            return line

        wx_config_path = state.install_path + 'bin/wx-config'
        self.update_text_file(wx_config_path, patch_wx_config)


class ZstdTarget(CMakeStaticDependencyTarget):
    def __init__(self, name='zstd'):
        super().__init__(name)
        self.src_root = 'build/cmake'

        opts = self.options
        opts['ZSTD_BUILD_PROGRAMS'] = 'NO'
        opts['ZSTD_BUILD_SHARED'] = 'NO'

    def prepare_source(self, state: BuildState):
        state.download_source(
            'https://github.com/facebook/zstd/releases/download/v1.5.0/zstd-1.5.0.tar.gz',
            '5194fbfa781fcf45b98c5e849651aa7b3b0a008c6b72d4a0db760f3002291e94')

    def detect(self, state: BuildState) -> bool:
        return os.path.exists(state.source + 'lib/libzstd.pc.in')
