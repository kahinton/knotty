"""
The __init__ file for Knotty is responsible initiating the monitors handled by the Knotty object in the core module
"""

from knotty import core


__all__ = ["core", "exporters", "meters", "registry"]

core.Knotty.initiate_monitors()
