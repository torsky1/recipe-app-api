"""
Test for the user API
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


@pytest.fixture
def create_user(db):
    def _create_user(email='user@example.com',
                     password='testpass123', name='TestName', **params):
        """Create and return user"""
        return get_user_model().objects.create_user(email=email,
                                                    password=password,
                                                    name=name, **params)
    return _create_user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestPublicUserApi:
    """Test the public features of the user API"""
    def test_create_user_success(self, api_client):
        """Test creating a user i successful"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test name',
        }

        res = api_client.post(CREATE_USER_URL, payload)

        assert res.status_code == status.HTTP_201_CREATED
        user = get_user_model().objects.get(email=payload['email'])
        assert user.check_password(payload['password'])
        assert 'password' not in res.data

    def test_user_with_email_exists_error(self, api_client, create_user):
        """Test error returned if user with email exists"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }
        create_user(**payload)
        res = api_client.post(CREATE_USER_URL, payload)

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_too_short_error(self, api_client):
        """Test and error is returned if password less then 5 chars"""
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'Test Name',
        }
        res = api_client.post(CREATE_USER_URL, payload)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        assert not user_exists

    def test_create_token_for_user(self, create_user, api_client):
        """Test generates token for valid credentials"""
        user_details = {
            'name': 'Test Name',
            'email': 'test@example.com',
            'password': 'test-user-password123',
        }
        create_user(**user_details)
        payload = {
            'email': user_details['email'],
            'password': user_details['password'],
        }
        res = api_client.post(TOKEN_URL, payload)

        assert 'token' in res.data
        assert res.status_code == status.HTTP_200_OK

    def test_create_token_bad_credentials(self, create_user, api_client):
        """Test returnms error if credentials invalid"""
        create_user(email='test@example.com', password='testpass123')
        payload = {'email': 'test@example.com', 'password': 'badpass'}
        res = api_client.post(TOKEN_URL, payload)

        assert 'token' not in res.data
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_token_blank_password(self, api_client):
        """Test posting a blank password return an error"""
        payload = {'email': 'test@example.com', 'password': ''}
        res = api_client.post(TOKEN_URL, payload)

        assert 'token' not in res.data
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_user_authorized(self, api_client):
        """Test authentication is required for users"""
        res = api_client.get(ME_URL)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestPrivateUserApi:
    """Test API request that require authentication"""

    def test_retrieve_profile_success(self, authenticated_client):
        """Test retrieving profile for logged in user"""
        client, user = authenticated_client
        res = client.get(ME_URL)

        assert res.status_code == status.HTTP_200_OK
        assert res.data == {'name': user.name, 'email': user.email, }

    def test_post_me_not_allowed(self, authenticated_client):
        """Test post is not allowed for the me endpoint"""
        client, user = authenticated_client
        res = client.post(ME_URL, {})

        assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_user_profile(self, authenticated_client):
        """Test updating the user profile for the authenticated user"""
        client, user = authenticated_client
        payload = {'name': 'Updated name', 'password': 'newpassword123'}

        res = client.patch(ME_URL, payload)

        user.refresh_from_db()
        assert user.name == payload['name']
        assert user.check_password(payload['password'])
        assert res.status_code == status.HTTP_200_OK
