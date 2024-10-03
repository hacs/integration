Changelog
=========

1.14.0 (2023-11-01)
-------------------

* Added support for Python 3.11 and 3.12.
* Support for Python 3.7 has been deprecated and will be removed in the next
  scheduled release.
* Dropped support for Python 3.6.
* Added a new valid PGP key for signing our PyPI packages with the fingerprint
  F2871B4152AE13C49519111F447BF683AA3B26C3

1.13.0 (2022-03-10)
-------------------

* Support for Python 3.6 has been deprecated and will be removed in the next
  scheduled release.
* Corrected some type annotations.

1.12.0 (2022-01-11)
-------------------

* Corrected some type annotations.
* Dropped support for cryptography<1.5.
* Added the top level attributes josepy.JWKEC, josepy.JWKOct, and
  josepy.ComparableECKey for convenience and consistency.

1.11.0 (2021-11-17)
-------------------

* Added support for Python 3.10.
* We changed the PGP key used to sign the packages we upload to PyPI. Going
  forward, releases will be signed with one of three different keys. All of
  these keys are available on major key servers and signed by our previous PGP
  key. The fingerprints of these new keys are:
    - BF6BCFC89E90747B9A680FD7B6029E8500F7DB16
    - 86379B4F0AF371B50CD9E5FF3402831161D1D280
    - 20F201346BF8F3F455A73F9A780CC99432A28621

1.10.0 (2021-09-27)
-------------------

* josepy is now compliant with PEP-561: type checkers will fetch types from the inline
  types annotations when josepy is installed as a dependency in a Python project.
* Added a `field` function to assist in adding type annotations for Fields in classes.
  If the field function is used to define a `Field` in a `JSONObjectWithFields` based
  class without a type annotation, an error will be raised.
* josepy's tests can no longer be imported under the name josepy, however, they are still
  included in the package and you can run them by installing josepy with "tests" extras and
  running `python -m pytest`.

1.9.0 (2021-09-09)
------------------

* Removed pytest-cache testing dependency.
* Fixed a bug that sometimes caused incorrect padding to be used when
  serializing Elliptic Curve keys as JSON Web Keys.

1.8.0 (2021-03-15)
------------------

* Removed external mock dependency.
* Removed dependency on six.
* Deprecated the module josepy.magic_typing.
* Fix JWS/JWK generation with EC keys when keys or signatures have leading zeros.

1.7.0 (2021-02-11)
------------------

* Dropped support for Python 2.7.
* Added support for EC keys.

1.6.0 (2021-01-26)
------------------

* Deprecated support for Python 2.7.

1.5.0 (2020-11-03)
------------------

* Added support for Python 3.9.
* Dropped support for Python 3.5.
* Stopped supporting running tests with ``python setup.py test`` which is
  deprecated in favor of ``python -m pytest``.

1.4.0 (2020-08-17)
------------------

* Deprecated support for Python 3.5.

1.3.0 (2020-01-28)
------------------

* Deprecated support for Python 3.4.
* Officially add support for Python 3.8.

1.2.0 (2019-06-28)
------------------

* Support for Python 2.6 and 3.3 has been removed.
* Known incompatibilities with Python 3.8 have been resolved.

1.1.0 (2018-04-13)
------------------

* Deprecated support for Python 2.6 and 3.3.
* Use the ``sign`` and ``verify`` methods when they are available in
  ``cryptography`` instead of the deprecated methods ``signer`` and
  ``verifier``.

1.0.1 (2017-10-25)
------------------

Stop installing mock as part of the default but only as part of the
testing dependencies.

1.0.0 (2017-10-13)
-------------------

First release after moving the josepy package into a standalone library.
