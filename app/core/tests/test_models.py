"""
Test for models
"""
from unittest.mock import patch
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from core import models


@pytest.fixture
def create_user(db):
    def _create_user(email='user@example.com', password='testpass123'):
        return get_user_model().objects.create_user(email, password)
    return _create_user


@pytest.mark.django_db
class TestModels:
    """Test models"""

    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful"""
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        assert user.email == email
        assert user.check_password(password)

    def test_new_user_email_normalized(self):
        """Test email is normalized for new users"""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            assert user.email == expected

    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises a ValueError"""
        with pytest.raises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating superuser"""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123',
        )

        assert user.is_superuser
        assert user.is_staff

    def test_create_recipe(self, create_user):
        """Test creating recipe is successful"""
        user = create_user()
        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description',
        )

        assert str(recipe) == recipe.title

    def test_create_tag(self, create_user):
        """Test creating a tag is successful"""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        assert str(tag) == tag.name

    def test_create_ingredient(self, create_user):
        """Test creating an ingredient is successful"""
        user = create_user()
        ingredient = models.Ingredient.objects.create(
            user=user,
            name='Ingredient1'
        )

        assert str(ingredient) == ingredient.name

    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path"""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        assert file_path == f'uploads/recipe/{uuid}.jpg'
