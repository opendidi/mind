"""
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-09-19 09:34:03
LastEditors: htang
LastEditTime: 2024-09-19 09:34:12
"""

# -*- coding: UTF-8 -*-

import io
import logging
import os
import sys


def _ensure_utf8_stream(stream):
    """Wrap a stream to ensure UTF-8 encoding, to avoid UnicodeEncodeError
    on Windows where the default console encoding is GBK/cp936."""
    try:
        return io.TextIOWrapper(
            stream.buffer,
            encoding="utf-8",
            errors="replace",
        )
    except AttributeError:
        return stream


def setup_logging(
    log_file="app.log", level=logging.DEBUG, log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
):
    # Create log directory if needed
    log_directory = os.path.dirname(log_file)
    if log_directory and not os.path.exists(log_directory):
        os.makedirs(log_directory)

    logger = logging.getLogger()
    logger.setLevel(level)

    # File handler with explicit UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)

    # Stream handler with UTF-8 wrapped stderr (Windows-safe)
    utf8_stream = _ensure_utf8_stream(sys.stderr)
    stream_handler = logging.StreamHandler(utf8_stream)
    stream_handler.setLevel(level)

    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Suppress noisy OpenAI SDK debug logging (logs full request bodies)
    logging.getLogger("openai").setLevel(logging.WARNING)

    return logger
