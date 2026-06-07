import logging
from logging.handlers import RotatingFileHandler

from wpt.logging import configure_logging


def test_configure_logging_default():
    # Calling configure_logging without options should reset/default the logger
    configure_logging(quiet=False, debug=False)

    logger = logging.getLogger('wpt')
    assert logger.level == logging.INFO

    # Check that StreamHandler is back to level INFO with standard formatter
    stream_handlers = [
        h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    ]
    assert len(stream_handlers) > 0
    for handler in stream_handlers:
        assert handler.level == logging.INFO
        # Format a dummy record to verify it uses standard message-only formatting
        record = logging.LogRecord('wpt', logging.INFO, 'pathname', 1, 'Test message', None, None)
        assert handler.formatter.format(record) == 'Test message'


def test_configure_logging_debug():
    # Calling configure_logging with debug=True should elevate all handlers to DEBUG
    configure_logging(quiet=False, debug=True)

    logger = logging.getLogger('wpt')
    assert logger.level == logging.DEBUG

    for handler in logger.handlers:
        assert handler.level == logging.DEBUG
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            # Check detailed formatter includes metadata like levelname and name
            record = logging.LogRecord('wpt', logging.DEBUG, 'pathname', 1, 'Test debug message', None, None)
            formatted = handler.formatter.format(record)
            assert 'DEBUG' in formatted
            assert 'wpt' in formatted
            assert 'Test debug message' in formatted


def test_configure_logging_quiet():
    # Calling configure_logging with quiet=True should silence stream handlers
    configure_logging(quiet=True, debug=False)

    logger = logging.getLogger('wpt')

    stream_handlers = [
        h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    ]
    for handler in stream_handlers:
        assert handler.level > logging.CRITICAL
