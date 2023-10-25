Using the library
=================

Basic flow:

1. Construct a Python `dict` to contain the :doc:`album metadata <metadata>`
2. Construct a :py:class:`bandcrash.options.Options` with the encoding and output options
3. Initialize a :py:class:`concurrent.futures.ThreadPoolExecutor` to run the tasks, and a :py:class:`collections.defaultdict(list)` to hold its futures
4. Call :py:func:`bandcrash.process` with the above

API documentation
-----------------


.. autofunction:: bandcrash.process

.. autoclass:: bandcrash.options.Options
   :members:
