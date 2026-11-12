"""Tests for logging_redirect_stdout_stderr, see
https://github.com/Textualize/rich/issues/4235"""

from __future__ import annotations

import io
import logging
import re
import sys

import pytest

import rich
from rich.console import Console
from rich.logging import RichHandler, logging_redirect_stdout_stderr
from rich.progress import Progress

re_ansi = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x1b]*\x1b\\")


def strip_ansi(render: str) -> str:
    """Strip ANSI escape codes (highlighting inserts codes within text)."""
    return re_ansi.sub("", render)


@pytest.fixture(autouse=True)
def preserve_root_logger():
    """Preserve and restore the state of the root logger around each test."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    yield
    root.handlers = handlers
    root.setLevel(level)


def test_console_handler_replaced_and_restored(monkeypatch):
    """A handler writing to stdout should be replaced with a RichHandler
    inside the context manager, and restored on exit."""
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    other_handler = logging.StreamHandler(io.StringIO())
    root.handlers = [console_handler, other_handler]

    with logging_redirect_stdout_stderr():
        assert console_handler not in root.handlers
        assert other_handler in root.handlers
        redirected = [h for h in root.handlers if isinstance(h, RichHandler)]
        assert len(redirected) == 1

    assert console_handler in root.handlers
    assert other_handler in root.handlers
    assert not [h for h in root.handlers if isinstance(h, RichHandler)]


def test_log_messages_rendered_via_console(monkeypatch):
    """Log records should be rendered via the rich console (above any live
    display) rather than written directly to the original stream."""
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    console = Console(
        file=io.StringIO(),
        force_terminal=True,
        width=80,
        color_system="truecolor",
        _environ={},
    )
    old_console = rich._console
    rich._console = console

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root.handlers = [handler]

    try:
        with logging_redirect_stdout_stderr():
            logger = logging.getLogger("app")
            with Progress(console=console) as progress:
                task = progress.add_task("working", total=2)
                for i in range(2):
                    logger.info("step %d", i)
                    progress.advance(task)

        rendered = strip_ansi(console.file.getvalue())
        assert stdout.getvalue() == ""
        # The message is rendered via the console (above the progress bar)
        assert "step 0" in rendered
        assert "step 1" in rendered
        assert "app: step 0" in rendered  # formatter is preserved
        assert "working" in rendered
    finally:
        rich._console = old_console


def test_no_console_handlers_is_noop():
    """If there are no stdout / stderr handlers, the context manager should
    do nothing."""
    root = logging.getLogger()
    root.handlers = []

    with logging_redirect_stdout_stderr():
        assert root.handlers == []


def test_level_of_replaced_handler_is_preserved(monkeypatch):
    """The RichHandler replacing the console handler should keep the level
    of the original handler."""
    monkeypatch.setattr(sys, "stdout", io.StringIO())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.ERROR)
    root.handlers = [handler]

    with logging_redirect_stdout_stderr():
        redirected = [h for h in root.handlers if isinstance(h, RichHandler)]
        assert len(redirected) == 1
        assert redirected[0].level == logging.ERROR


def test_handlers_restored_on_error(monkeypatch):
    """Original handlers should be restored even if an exception is raised
    inside the context manager."""
    monkeypatch.setattr(sys, "stdout", io.StringIO())

    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    root.handlers = [handler]

    try:
        with logging_redirect_stdout_stderr():
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert root.handlers == [handler]


def test_multiple_console_handlers(monkeypatch):
    """All handlers writing to stdout / stderr should be redirected."""
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    root = logging.getLogger()
    root.handlers = [
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr),
        logging.StreamHandler(io.StringIO()),
    ]

    with logging_redirect_stdout_stderr():
        redirected = [h for h in root.handlers if isinstance(h, RichHandler)]
        assert len(redirected) == 2

    assert len(root.handlers) == 3
    assert not [h for h in root.handlers if isinstance(h, RichHandler)]
