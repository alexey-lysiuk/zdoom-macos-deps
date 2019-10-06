#!/bin/sh

cd "${0%/*}"

if [ ! -e lib ]; then
	mkdir lib
fi

g++ -std=c++11 -O3 -mmacosx-version-min=10.9 -c src/quasig.cpp
ar -crs lib/libquasig.a quasig.o
rm quasig.o
