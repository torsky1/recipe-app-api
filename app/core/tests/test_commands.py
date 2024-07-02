"""
Test custom Django management commands
"""
import pytest
from unittest.mock import patch
from psycopg2 import OperationalError as Psycopg2Error
from django.core.management import call_command
from django.db.utils import OperationalError


@pytest.fixture
def patched_check():
    with patch('core.management.commands.wait_for_db.Command.check') as pc:
        yield pc


@pytest.fixture
def patched_sleep():
    with patch('time.sleep') as ps:
        yield ps


def test_wait_for_db_ready(patched_check):
    """Test waiting for database if database ready"""
    patched_check.return_value = True
    call_command('wait_for_db')
    patched_check.assert_called_once_with(databases=['default'])


def test_wait_for_db_delay(patched_check, patched_sleep):
    """Test waiting for database when getting OperationalError"""
    patched_check.side_effect = (
        [Psycopg2Error] * 2 + [OperationalError] * 3 + [True])
    call_command('wait_for_db')
    assert patched_check.call_count == 6
    patched_check.assert_called_with(databases=['default'])
