"""
Test for the ingredients API
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


@pytest.fixture
def detail_url():
    def _detail_url(ingredient_id):
        """Create and return an ingredient detail URL"""
        return reverse('recipe:ingredient-detail', args=[ingredient_id])
    return _detail_url


@pytest.fixture
def create_user(db):
    def _create_user(email='user@example.com', password='testpass123'):
        """Create and return user"""
        return get_user_model().objects.create_user(email=email,
                                                    password=password)
    return _create_user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def create_ingredient():
    def _create_ingredient(user, name):
        return Ingredient.objects.create(user=user, name=name)
    return _create_ingredient


@pytest.fixture
def create_recipe():
    def _create_recipe(user, title, time_minutes, price):
        return Recipe.objects.create(
            user=user,
            title=title,
            time_minutes=time_minutes,
            price=price,
        )
    return _create_recipe


@pytest.mark.django_db
class TestPublicIngredientApi:
    """Test unauthenticated API request"""

    def test_auth_required(self, api_client):
        """Test auth is required for retrieving ingredients"""
        res = api_client.get(INGREDIENTS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPrivateIngredientsApi:
    """Test authenticated API request"""

    def test_retrieve_ingredients(self, authenticated_client,
                                  create_ingredient):
        """Test retrieving ingredients"""
        client, user = authenticated_client
        create_ingredient(user=user, name='Salt')
        create_ingredient(user=user, name='Pepper')

        res = client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        assert res.status_code == status.HTTP_200_OK
        assert res.data == serializer.data

    def test_ingredients_limited_to_user(self, authenticated_client,
                                         create_user, create_ingredient):
        """Test list of ingredients is limited to authenticated user"""
        client, user = authenticated_client
        user1 = create_user(email='user1@example.com')
        create_ingredient(user=user1, name='Salt')
        ingredient = create_ingredient(user=user, name='Pepper')

        res = client.get(INGREDIENTS_URL)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]['name'] == ingredient.name
        assert res.data[0]['id'] == ingredient.id

    def test_update_ingredient(self, create_ingredient,
                               authenticated_client, detail_url):
        """Test updating an ingredient"""
        client, user = authenticated_client
        ingredient = create_ingredient(user=user, name='Cilantro')
        payload = {'name': 'Coriander'}

        url = detail_url(ingredient.id)
        res = client.patch(url, payload)

        assert res.status_code == status.HTTP_200_OK
        ingredient.refresh_from_db()
        assert ingredient.name == payload['name']

    def test_delete_ingredient(self, create_ingredient,
                               authenticated_client, detail_url):
        """Test deleting an ingredient"""
        client, user = authenticated_client
        ingredient = create_ingredient(user=user, name='Lettuce')

        url = detail_url(ingredient.id)
        res = client.delete(url)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        ingredients = Ingredient.objects.filter(user=user)
        assert not ingredients.exists()

    def test_filter_ingredient_assigned_to_recipe(self, create_ingredient,
                                                  authenticated_client,
                                                  create_recipe):
        """Test listing ingredients by those assigned to recipes"""
        client, user = authenticated_client
        ing1 = create_ingredient(user=user, name='Apples')
        ing2 = create_ingredient(user=user, name='Turkey')
        recipe = create_recipe(
            user=user,
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'),
            )
        recipe.ingredients.add(ing1)

        res = client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)

        assert s1.data in res.data
        assert s2.data not in res.data

    def test_filtered_ingredients_unique(self, create_ingredient,
                                         authenticated_client,
                                         create_recipe):
        """Test filtered ingredients returns a unique value"""
        client, user = authenticated_client
        ing = create_ingredient(user=user, name='Eggs')
        create_ingredient(user=user, name='Lentils')
        recipe1 = create_recipe(
            user=user,
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
        )
        recipe2 = create_recipe(
            user=user,
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
        )

        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = client.get(INGREDIENTS_URL, {'assigned_only': 1})

        assert len(res.data) == 1
