all: setup format

.PHONY: setup
setup:
	poetry install

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
	poetry run blamscamp -vvv tests/album test_output/album
	poetry run blamscamp -vvv --init tests/derived test_output/derived --json derived.json

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
build: preflight
	poetry build

.PHONY: clean
clean:
	rm -rf dist .mypy_cache .pytest_cache .coverage
	find . -name __pycache__ -print0 | xargs -0 rm -r

.PHONY: upload
upload: clean test build
	poetry publish
