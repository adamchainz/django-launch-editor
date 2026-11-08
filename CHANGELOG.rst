=========
Changelog
=========

1.1.0 (2026-11-08)
------------------

* Reduce import cost by ~3ms when ``DEBUG`` is off, by lazily importing ``LaunchEditorExceptionReporter`` and skipping the URL definition.

  `PR #5 <https://github.com/adamchainz/django-launch-editor/pull/5>`__.

* Reduce import cost by ~1ms when ``DEBUG`` is on, on Python 3.15+, by lazily importing ``launch_editor`` in the views module.

  `PR #6 <https://github.com/adamchainz/django-launch-editor/pull/6>`__.

1.0.0 (2026-11-05)
------------------

* Initial release.
