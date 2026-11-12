Logging Handler
===============

Rich supplies a :ref:`logging handler<logging>` which will format and colorize text written by Python's logging module.

Here's an example of how to set up a rich logger::

    import logging
    from rich.logging import RichHandler

    FORMAT = "%(message)s"
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    log = logging.getLogger("rich")
    log.info("Hello, World!")

Rich logs won't render :ref:`console_markup` in logging by default as most libraries won't be aware of the need to escape literal square brackets, but you can enable it by setting ``markup=True`` on the handler. Alternatively you can enable it per log message by supplying the ``extra`` argument as follows::

    log.error("[bold red blink]Server is shutting down![/]", extra={"markup": True})

Similarly, the highlighter may be overridden per log message::

    log.error("123 will not be highlighted", extra={"highlighter": None})


Handle exceptions
-------------------

The :class:`~rich.logging.RichHandler` class may be configured to use Rich's :class:`~rich.traceback.Traceback` class to format exceptions, which provides more context than a built-in exception. To get beautiful exceptions in your logs set ``rich_tracebacks=True`` on the handler constructor::


    import logging
    from rich.logging import RichHandler

    logging.basicConfig(
        level="NOTSET",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )

    log = logging.getLogger("rich")
    try:
        print(1 / 0)
    except Exception:
        log.exception("unable print!")


There are a number of other options you can use to configure logging output, see the :class:`~rich.logging.RichHandler` reference for details.

Suppressing Frames
------------------

If you are working with a framework (click, django etc), you may only be interested in seeing the code from your own application within the traceback. You can exclude framework code by setting the `suppress` argument on `Traceback`, `install`, and `Console.print_exception`, which should be a list of modules or str paths.

Here's how you would exclude `click <https://click.palletsprojects.com/en/8.0.x/>`_ from Rich exceptions:: 

    import click
    import logging
    from rich.logging import RichHandler

    logging.basicConfig(
        level="NOTSET",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_suppress=[click])]
    )

Suppressed frames will show the line and file only, without any code.

Logging and live displays
-------------------------

If you log to ``sys.stdout`` or ``sys.stderr`` with a standard
:class:`logging.StreamHandler` while a :ref:`live display <live>` (such as a
:class:`~rich.progress.Progress` bar) is active, the log lines will be
written directly to the terminal and will break the live display. This is
because Rich redirects ``sys.stdout`` and ``sys.stderr`` while a live display
is running, but logging handlers hold on to a reference to the original
stream they were created with.

If you can, use a :class:`~rich.logging.RichHandler` for logging, which
writes via the console and is unaffected by live displays. If you can't
control how logging is configured (for instance when a library configures
its own logging), you can wrap your live display in the
:func:`~rich.logging.logging_redirect_stdout_stderr` context manager, which
temporarily replaces any handler that writes directly to ``sys.stdout`` or
``sys.stderr`` with a Rich handler, so that log messages are displayed
*above* the live display::

    import logging
    import sys

    from rich.logging import logging_redirect_stdout_stderr
    from rich.progress import Progress

    logging.basicConfig(level="INFO", stream=sys.stderr)
    log = logging.getLogger("app")

    with logging_redirect_stdout_stderr():
        with Progress() as progress:
            task = progress.add_task("working", total=10)
            for i in range(10):
                log.info("step %d", i)
                progress.advance(task)

The original logging handlers are restored when the context manager exits.