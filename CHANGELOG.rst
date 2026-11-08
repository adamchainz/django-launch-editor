=========
Changelog
=========

Unreleased
----------

* Reduce import cost when the library is installed but not in use, by lazily importing ``LaunchEditorExceptionReporter`` and only defining the URL when ``DEBUG`` is on.

  `PR #5 <https://github.com/adamchainz/django-launch-editor/pull/5>`__.

* Reduce import cost further on Python 3.15+ by lazily importing ``launch_editor`` in the views module.

  `PR #6 <https://github.com/adamchainz/django-launch-editor/pull/6>`__.

1.0.0 (2026-11-05)
------------------

* Initial release.
