"""
Pytest configuration for fixtures package.

This conftest.py makes fixtures available to all tests in the package
and subpackages.
"""

# Import fixtures from interface_fixtures module
# Pytest automatically discovers fixtures in modules imported by conftest.py
from tests.fixtures.interface_fixtures import *
