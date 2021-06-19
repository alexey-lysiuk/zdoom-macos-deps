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

from .library_tier1 import *
from .library_tier2 import *
from .main import *
from .special import *
from .tools import *


def targets():
    return (
        GZDoomTarget(),
        QZDoomTarget(),
        LZDoomTarget(),
        LZDoom3Target(),
        RazeTarget(),
        AccTarget(),
        SladeTarget(),
        PrBoomPlusTarget(),
        DsdaDoom(),
        ChocolateDoomTarget(),
        CrispyDoomTarget(),
        RudeTarget(),
        WoofTarget(),
        DoomRetroTarget(),
        Doom64EXTarget(),
        DevilutionXTarget(),
        EDuke32Target(),
        NBloodTarget(),
        QuakespasmTarget(),
        VkQuake2Target(),

        # Libraries needed for GZDoom and Raze
        Bzip2Target(),
        FfiTarget(),
        FlacTarget(),
        FluidSynthTarget(),
        GlibTarget(),
        IconvTarget(),
        InstPatchTarget(),
        IntlTarget(),
        JpegTurboTarget(),
        MoltenVKTarget(),
        Mpg123Target(),
        OggTarget(),
        OpenALTarget(),
        OpusTarget(),
        PcreTarget(),
        SndFileTarget(),
        VorbisTarget(),
        VpxTarget(),
        ZlibNgTarget(),
        ZMusicTarget(),

        # Libraries needed for other targets
        DumbTarget(),
        ExpatTarget(),
        FmtTarget(),
        FreeImageTarget(),
        FreeTypeTarget(),
        FtglTarget(),
        GlewTarget(),
        LuaTarget(),
        LzmaTarget(),
        MadTarget(),
        MikmodTarget(),
        ModPlugTarget(),
        OpusFileTarget(),
        PngTarget(),
        PortMidiTarget(),
        SamplerateTarget(),
        Sdl2Target(),
        Sdl2ImageTarget(),
        Sdl2MixerTarget(),
        Sdl2NetTarget(),
        Sdl2TtfTarget(),
        SfmlTarget(),
        SodiumTarget(),
        TiffTarget(),
        WebpTarget(),
        WxWidgetsTarget(),
        ZstdTarget(),

        # Tools
        GmakeTarget(),
        MesonTarget(),
        NasmTarget(),
        NinjaTarget(),
        P7ZipTarget(),
        PkgConfigTarget(),
        UnrarTarget(),
        YasmTarget(),
        ZipTarget(),

        # Special
        CleanAllTarget(),
        CleanDepsTarget(),
        DownloadCMakeTarget(),
        TestDepsTarget(),
    )
