"""Centralized logger factory for AMS.

Usage::

    from core.utils.logger import get_logger
    logger = get_logger(__name__)
"""
import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger pre-configured by Django's LOGGING setting."""
    return logging.getLogger(name)
