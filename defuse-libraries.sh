#!/bin/sh
# Generate the latest local universal2 wheels

mkdir -p build/fuse-universal2 dist
cd build/fuse-universal2

poetry run devpi use https://m.devpi.net/fluffy/prod
poetry run devpi login fluffy

pkg="$1"
rm -f $pkg-*.whl
for platform in macosx_10_10_x86_64 macosx_11_0_arm64 ; do
    poetry run pip download --only-binary=:all: --platform $platform $pkg
done
mkdir -p tmp
poetry run delocate-fuse -w tmp  $pkg-*.whl
outfile=../../dist/$(basename $pkg-*_arm64.whl arm64.whl)universal2.whl
mv tmp/$pkg-*.whl $outfile

poetry run devpi use fluffy/prod
poetry run devpi upload --formats=bdist_wheel $outfile
