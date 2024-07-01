"""
Test for the Django admin modifications
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def admin_user(db):
    user = get_user_model().objects.create_superuser(
        email='admin@example.com',
        password='testpass123',
    )
    return user


@pytest.fixture
def logged_in_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def user(db):
    user = get_user_model().objects.create_user(
        email='user@example.com',
        password='testpass123',
        name='Test User'
    )
    return user


def test_users_list(logged_in_client, user):
    """Test that users are listed on page"""
    url = reverse('admin:core_user_changelist')
    res = logged_in_client.get(url)

    assert res.status_code == 200
    assert user.name in res.content.decode()
    assert user.email in res.content.decode()


def test_edit_user_page(logged_in_client, user):
    """Test the edit user page works"""
    url = reverse('admin:core_user_change', args=[user.id])
    res = logged_in_client.get(url)

    assert res.status_code == 200


def test_create_user_page(logged_in_client):
    """Test the create user page works"""
    url = reverse('admin:core_user_add')
    res = logged_in_client.get(url)

    assert res.status_code == 200
