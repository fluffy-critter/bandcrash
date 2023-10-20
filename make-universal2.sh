#!/bin/sh
# Generate the latest local universal2 wheels

mkdir -p build
cd build

for pkg in Pillow ; do
    rm $pkg-*.whl
    for platform in macosx_10_10_x86_64 macosx_11_0_arm64 ; do
        poetry run pip download --only-binary=:all: --platform $platform $pkg
    done
    mkdir -p tmp
    poetry run delocate-fuse -w tmp  $pkg-*.whl
    outfile=$(basename $pkg-*_arm64.whl arm64.whl)universal2.whl
    mv tmp/$pkg-*.whl $outfile
done


