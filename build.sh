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
MPG123_DIR=${DEPS_DIR}mpg123/
SNDFILE_DIR=${DEPS_DIR}sndfile/
FSYNTH_DIR=${DEPS_DIR}fluidsynth/
FSYNTH_LIB_PREFIX=${FSYNTH_DIR}lib/lib
FSYNTH_LIBS=${FSYNTH_LIB_PREFIX}fluidsynth.a\;${DEPS_DIR}quasig/lib/libquasig.a
JPEG_DIR=${DEPS_DIR}jpeg/
OTHER_LIBS=-liconv\ -L${DEPS_DIR}ogg/lib\ -logg\ -L${DEPS_DIR}vorbis/lib\ -lvorbis\ -lvorbisenc\ -L${DEPS_DIR}flac/lib\ -lFLAC
FRAMEWORKS=-framework\ AudioUnit\ -framework\ AudioToolbox\ -framework\ CoreAudio\ -framework\ CoreMIDI
LINKER_FLAGS=${OTHER_LIBS}\ ${FRAMEWORKS}

cd build
export PATH=$PATH:/Applications/CMake.app/Contents/bin

cmake                                                    \
	-DCMAKE_BUILD_TYPE="Release"                         \
	-DCMAKE_OSX_DEPLOYMENT_TARGET="10.9"                 \
	-DCMAKE_EXE_LINKER_FLAGS="${LINKER_FLAGS}"           \
	-DDYN_OPENAL=NO                                      \
	-DDYN_MPG123=NO                                      \
	-DDYN_SNDFILE=NO                                     \
	-DDYN_FLUIDSYNTH=NO                                  \
	-DFORCE_INTERNAL_ZLIB=YES                            \
	-DFORCE_INTERNAL_BZIP2=YES                           \
	-DFORCE_INTERNAL_GME=YES                             \
	-DPK3_QUIET_ZIPDIR=YES                               \
	-DOPENAL_INCLUDE_DIR="${OPENAL_DIR}include"          \
	-DOPENAL_LIBRARY="${OPENAL_DIR}lib/libopenal.a"      \
	-DMPG123_INCLUDE_DIR="${MPG123_DIR}include"          \
	-DMPG123_LIBRARIES="${MPG123_DIR}lib/libmpg123.a"    \
	-DSNDFILE_INCLUDE_DIR="${SNDFILE_DIR}include"        \
	-DSNDFILE_LIBRARY="${SNDFILE_DIR}lib/libsndfile.a"   \
	-DFLUIDSYNTH_INCLUDE_DIR="${FSYNTH_DIR}include"      \
	-DFLUIDSYNTH_LIBRARIES="${FSYNTH_LIBS}"              \
	-DJPEG_INCLUDE_DIR="${JPEG_DIR}include"              \
	-DJPEG_LIBRARY="${JPEG_DIR}lib/libjpeg.a"            \
	..
make -j2

cp "${DEPS_DIR}moltenvk/lib/libMoltenVK.dylib" "gzdoom.app/Contents/MacOS/"
