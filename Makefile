all: setup format mypy pylint

.PHONY: setup
setup:
	@echo "Current version: $(shell ./get-version.sh)"
	poetry install -E gui

.PHONY: format
format:
	poetry run isort .
	poetry run autopep8 -r --in-place .

.PHONY: test
test: setup
	# this really should be done using pytest but ugh
	rm -rf test_output
	mkdir -p test_output/album/mp3/dir_should_be_removed
	touch test_output/album/mp3/extraneous-file.txt
	touch test_output/album/mp3/dir_should_be_removed/extraneous-file.txt
	poetry run bandcrash -vvv tests/album test_output/album
	poetry run bandcrash tests/album/test-options.json test_output/test-options --no-butler
	poetry run bandcrash -vvv --init tests/derived test_output/derived --json derived.json

.PHONY: pylint
pylint:
	poetry run pylint bandcrash --extension-pkg-allow-list=PySide6

.PHONY: mypy
mypy:
	poetry run mypy -p bandcrash --ignore-missing-imports --check-untyped-defs

.PHONY: preflight
preflight:
	@echo "Checking commit status..."
	@git status --porcelain | grep -q . \
		&& echo "You have uncommitted changes" 1>&2 \
		&& exit 1 || exit 0
	@echo "Checking branch..."
	@[ "$(shell git rev-parse --abbrev-ref HEAD)" != "main" ] \
		&& echo "Can only build from main" 1>&2 \
		&& exit 1 || exit 0
	@echo "Checking upstream..."
	@git fetch \
		&& [ "$(shell git rev-parse main)" != "$(shell git rev-parse main@{upstream})" ] \
		&& echo "main branch differs from upstream" 1>&2 \
		&& exit 1 || exit 0

.PHONY: build
build: setup preflight pylint
	poetry build

.PHONY: clean
clean:
	rm -rf dist .mypy_cache .pytest_cache .coverage
	find . -name __pycache__ -print0 | xargs -0 rm -r

.PHONY: upload
upload: clean test build
	poetry publish

.PHONY: doc
doc:
	poetry run sphinx-build -b html docs/ docs/_build -D html_theme=alabaster

.PHONY: app
app: setup format pylint mypy
	poetry run pyInstaller Bandcrash.spec -y

.PHONY: upload-mac
upload-mac: preflight app doc
	rm -rf dist/macos
	mkdir -p dist/macos
	cp -a dist/Bandcrash.app dist/macos
	cp -a docs/_build dist/macos/docs
	butler push dist/macos fluffy/bandcrash:macos \
		--userversion=$(shell ./get-version.sh) \
		--fix-permissions

.PHONY: upload-win
upload-win: preflight app doc
	rm -rf dist/win
	mkdir -p dist/win
	cp dist/Bandcrash.exe dist/win
	cp -a docs/_build dist/win/docs
	butler push dist/win fluffy/bandcrash:win \
		--userversion=$(shell ./get-version.sh) \
		--fix-permissions
