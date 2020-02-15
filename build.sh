#!/bin/sh

set -o errexit

DEPS_DIR=$(cd "${0%/*}"; pwd)/

cd "${DEPS_DIR}"

if [ ! -e gzdoom ]; then
	git clone --depth 1 https://github.com/coelckers/gzdoom.git
fi

cd gzdoom
git pull

if [ ! -e build ]; then
	mkdir build
fi

OPENAL_DIR=${DEPS_DIR}openal/
ZMUSIC_DIR=${DEPS_DIR}zmusic/
OPENAL_DIR=${DEPS_DIR}openal/
JPEG_DIR=${DEPS_DIR}jpeg/
SDL_DIR=${DEPS_DIR}sdl/
FLUIDSYNTH_LIBS=${DEPS_DIR}fluidsynth/lib/libfluidsynth.a\ ${DEPS_DIR}fluidsynth/lib/libglib-2.0.a\ ${DEPS_DIR}fluidsynth/lib/libintl.a
SNDFILE_LIBS=${DEPS_DIR}ogg/lib/libogg.a\ ${DEPS_DIR}vorbis/lib/libvorbis.a\ ${DEPS_DIR}vorbis/lib/libvorbisenc.a\ ${DEPS_DIR}flac/lib/libFLAC.a\ ${DEPS_DIR}sndfile/lib/libsndfile.a
EXTRA_LIBS=-liconv\ ${DEPS_DIR}mpg123/lib/libmpg123.a\ ${FLUIDSYNTH_LIBS}\ ${SNDFILE_LIBS}
FRAMEWORKS=-framework\ AudioUnit\ -framework\ AudioToolbox\ -framework\ Carbon\ -framework\ CoreAudio\ -framework\ CoreMIDI\ -framework\ CoreVideo\ -framework\ ForceFeedback
LINKER_FLAGS=${EXTRA_LIBS}\ ${FRAMEWORKS}

cd build
export PATH=$PATH:/Applications/CMake.app/Contents/bin

cmake                                                 \
	-DCMAKE_BUILD_TYPE="Release"                      \
	-DCMAKE_OSX_DEPLOYMENT_TARGET="10.9"              \
	-DCMAKE_EXE_LINKER_FLAGS="${LINKER_FLAGS}"        \
	-DDYN_OPENAL=NO                                   \
	-DDYN_MPG123=NO                                   \
	-DDYN_SNDFILE=NO                                  \
	-DDYN_FLUIDSYNTH=NO                               \
	-DFORCE_INTERNAL_ZLIB=YES                         \
	-DFORCE_INTERNAL_BZIP2=YES                        \
	-DPK3_QUIET_ZIPDIR=YES                            \
	-DOPENAL_INCLUDE_DIR="${OPENAL_DIR}include"       \
	-DOPENAL_LIBRARY="${OPENAL_DIR}lib/libopenal.a"   \
	-DZMUSIC_INCLUDE_DIR="${ZMUSIC_DIR}include"       \
	-DZMUSIC_LIBRARIES="${ZMUSIC_DIR}lib/libzmusic.a" \
	-DJPEG_INCLUDE_DIR="${JPEG_DIR}include"           \
	-DJPEG_LIBRARY="${JPEG_DIR}lib/libjpeg.a"         \
	..
make -j2

cp "${DEPS_DIR}moltenvk/lib/libMoltenVK.dylib" "gzdoom.app/Contents/MacOS/"
