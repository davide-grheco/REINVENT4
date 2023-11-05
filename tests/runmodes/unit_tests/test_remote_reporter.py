import pytest

from reinvent.runmodes.reporter.remote import (
    setup_reporter,
    get_reporter,
    NoopReporter,
    RemoteJSONReporter,
)


def test_noop_reporter_without_setup():
    remote_reporter = get_reporter()

    assert type(remote_reporter) == NoopReporter

    remote_reporter.send()


def test_noop_reporter_with_setup():
    setup_reporter(url=None, token=None)
    remote_reporter = get_reporter()

    assert type(remote_reporter) == NoopReporter

    remote_reporter.send()


def test_reporter_is_json_reporter():
    setup_reporter(url="http://example.org", token=None)
    remote_reporter = get_reporter()

    assert type(remote_reporter) == RemoteJSONReporter

    remote_reporter.send({"test": 1})


def test_reporter_fails_when_wrong_type():
    setup_reporter(url="http://example.org", token=None)
    remote_reporter = get_reporter()

    assert type(remote_reporter) == RemoteJSONReporter

    with pytest.raises(TypeError):
        remote_reporter.send("Invalid data type")
