#!/bin/sh
# Set the current project version in __version__.py

mkdir -p build
version=$(poetry version -s)

if (git status --porcelain | grep -q .) ; then
    # Unchecked-in changes, so there's local edits
    tag=local
elif [ "$(git rev-parse HEAD)" = "$(git rev-parse v$version)" ] ; then
    # It matches the release tag exactly, so that's what we call it
    tag=release
else
    # Everything is checked in, so use the commit hash
    tag=$(git rev-parse --short HEAD)
fi

cat > bandcrash/__version__.py << EOF
""" Current git-based version """

__version__ = "$version-$tag"
EOF

echo "$version-$tag"

