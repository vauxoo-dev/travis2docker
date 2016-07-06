========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor|
        | |coveralls|
    * - package
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/travis2docker/badge/?style=flat
    :target: https://readthedocs.org/projects/travis2docker
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/moylop260/travis2docker.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/moylop260/travis2docker

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/moylop260/travis2docker?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/moylop260/travis2docker

.. |coveralls| image:: https://coveralls.io/repos/moylop260/travis2docker/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/moylop260/travis2docker

.. |version| image:: https://img.shields.io/pypi/v/travis2docker.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/travis2docker

.. |downloads| image:: https://img.shields.io/pypi/dm/travis2docker.svg?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/travis2docker

.. |wheel| image:: https://img.shields.io/pypi/wheel/travis2docker.svg?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/travis2docker

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/travis2docker.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/travis2docker

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/travis2docker.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/travis2docker


.. end-badges

Script to generate Dockerfile from .travis.yml file

* Free software: BSD license

Installation
============

::

    pip install travis2docker

Documentation
=============

https://travis2docker.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
