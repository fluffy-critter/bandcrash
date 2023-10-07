""" main CLI entry point """

import collections
import concurrent.futures
import itertools
import json
import logging
import os

from . import parse_args, populate_json_file, process

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def main(args=None):
    """ Main entry point """
    # pylint:disable=too-many-branches,too-many-statements,too-many-locals
    options = parse_args(False, args)

    logging.basicConfig(level=LOG_LEVELS[min(
        options.verbosity, len(LOG_LEVELS) - 1)],
        format='%(message)s')

    json_path = os.path.join(options.input_dir, options.json)

    if options.init:
        album = populate_json_file(options.input_dir, json_path)
        if not options.output_dir:
            return

    options = parse_args(True)
    with open(json_path, 'r', encoding='utf8') as json_file:
        album = json.load(json_file)

    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=options.num_threads)

    futures = collections.defaultdict(list)

    process(options, album, pool, futures)

    all_tasks = list(itertools.chain(*futures.values()))
    remaining_tasks = [f for f in all_tasks if not f.done()]
    LOGGER.info("Waiting for all tasks to complete... (%d/%d pending)",
                len(remaining_tasks), len(all_tasks))

    for task in concurrent.futures.as_completed(all_tasks):
        try:
            task.result()
        except Exception:  # pylint:disable=broad-exception-caught
            LOGGER.exception("Background task generated an exception")

    LOGGER.info("Done")


if __name__ == '__main__':
    main()
