=========
Changelog
=========

Unreleased
----------

* Reduce import cost when the library is installed but not in use, by lazily importing ``LaunchEditorExceptionReporter`` and only defining the URL when ``DEBUG`` is on.

1.0.0 (2026-11-05)
------------------

* Initial release.
