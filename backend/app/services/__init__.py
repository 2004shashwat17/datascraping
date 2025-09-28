"""
Services module for the OSINT platform.
Contains business logic and data processing services.
"""

from .no_api_collector import no_api_collector, NoAPIDataCollector

__all__ = ["no_api_collector", "NoAPIDataCollector"]