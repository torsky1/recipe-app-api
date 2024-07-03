"""
Test for recipe API
"""
from venv import create
import pytest

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def detail_url():
    def _detail_url(recipe_id):
        """Create and return an ingredient detail URL"""
        return reverse('recipe:recipe-detail', args=[recipe_id])
    return _detail_url


@pytest.fixture
def image_upload_url():
    def _image_upload_url(recipe_id):
        """Create and return an image detail URL"""
        return reverse('recipe:recipe-upload-image', args=[recipe_id])
    return _image_upload_url


@pytest.fixture
def create_recipe():
    def _create_recipe(user, **params):
        """Create and return sample recipe"""
        defaults = {
            'title': 'Sample recipe title',
            'time_minutes': 22,
            'price': Decimal('5.25'),
            'description': 'Sample description',
            'link': 'http://example.com/recipe.pdf',
        }
        defaults.update(params)
        return Recipe.objects.create(user=user, **defaults)
    return _create_recipe


@pytest.fixture
def create_user(db):
    def _create_user(email='user@example.com', password='testpass123'):
        """Create and return user"""
        return get_user_model().objects.create_user(email=email,
                                                    password=password)
    return _create_user


@pytest.fixture
def authenticated_client(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestPublicRecipeAPI:
    """Test unauthenticated API request"""

    def test_auth_required(self, api_client):
        """Test auth is required for retrieving ingredients"""
        res = api_client.get(RECIPES_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPrivateRecipeApi:
    """Test authenticated API request"""

    def test_retrieve_recipes(self, authenticated_client, create_recipe):
        """Test retrieveing a list of recipes"""
        client, user = authenticated_client
        create_recipe(user=user)
        create_recipe(user=user)

        res = client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        assert res.status_code == status.HTTP_200_OK
        assert res.data == serializer.data

    def test_recipe_list_limited_to_user(self, authenticated_client,
                                         create_user, create_recipe):
        """Test list of recipes is limited to authenticated user"""
        client, user = authenticated_client
        other_user = create_user(email='other@example.com',
                                 password='otherpass123')
        create_recipe(user=other_user)
        create_recipe(user=user)

        res = client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=user)
        serializer = RecipeSerializer(recipes, many=True)
        assert res.status_code == status.HTTP_200_OK
        assert res.data == serializer.data

    def test_get_recipe_detail(self, authenticated_client,
                               create_recipe, detail_url):
        """Test get recipe detail"""
        client, user = authenticated_client
        recipe = create_recipe(user=user)

        url = detail_url(recipe.id)
        res = client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        assert res.data == serializer.data

    def test_create_recipe(self, authenticated_client):
        """Test crating a recipe"""
        client, user = authenticated_client
        payload = {
            'title': 'Sample title',
            'time_minutes': 30,
            'price': Decimal('2.50'),
        }
        res = client.post(RECIPES_URL, payload)
        assert res.status_code == status.HTTP_201_CREATED

        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            assert getattr(recipe, k) == v
        assert recipe.user == user

    def test_partial_update(self, authenticated_client,
                            create_recipe, detail_url):
        """Test partial update of a recipe"""
        client, user = authenticated_client
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=user,
            title='Sample recipe title',
            link=original_link,
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = client.patch(url, payload)

        assert res.status_code == status.HTTP_200_OK
        recipe.refresh_from_db()
        assert recipe.title == payload['title']
        assert recipe.link == original_link
        assert recipe.user == user

    def test_full_update(self, authenticated_client,
                         create_recipe, detail_url):
        """Test full update of recipe"""
        client, user = authenticated_client
        recipe = create_recipe(
            user=user,
            title='Sample recipe title',
            link='https://example.com/recipe.pdf',
            description='Sample recipe descriprtion',
        )
        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50')
        }
        url = detail_url(recipe.id)
        res = client.put(url, payload)

        assert res.status_code == status.HTTP_200_OK
        recipe.refresh_from_db()
        for k, v in payload.items():
            assert getattr(recipe, k) == v
        assert recipe.user == user

    def test_update_user_returns_error(self, authenticated_client,
                                       create_user, create_recipe, detail_url):
        """Test changing the recipe user results in an error"""
        client, user = authenticated_client
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        client.patch(url, payload)

        recipe.refresh_from_db()
        assert recipe.user == user

    def test_delete_recipe(self, authenticated_client,
                           create_recipe, detail_url):
        """Test deleting a recipe successful"""
        client, user = authenticated_client
        recipe = create_recipe(user=user)

        url = detail_url(recipe.id)
        res = client.delete(url)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not Recipe.objects.filter(id=recipe.id).exists()

    def test_delete_other_user_recipe(self, authenticated_client,
                                      create_recipe, create_user, detail_url):
        """Test trying to delete another user recipe gives an error"""
        client, user = authenticated_client
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = client.delete(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert Recipe.objects.filter(id=recipe.id).exists()

    def test_create_recipe_with_new_tags(self, authenticated_client):
        """Test creating a recipe with new tags"""
        client, user = authenticated_client
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = client.post(RECIPES_URL, payload, format='json')

        assert res.status_code == status.HTTP_201_CREATED
        recipes = Recipe.objects.filter(user=user)
        assert recipes.count() == 1
        recipe = recipes[0]
        assert recipe.tags.count() == 2
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=user
            ).exists()
            assert exists

    def test_create_recipe_with_existing_tags(self, authenticated_client):
        """Test creating a recipe with existing tag"""
        client, user = authenticated_client
        tag_indian = Tag.objects.create(user=user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('6.99'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}],
        }
        res = client.post(RECIPES_URL, payload, format='json')

        assert res.status_code == status.HTTP_201_CREATED
        recipes = Recipe.objects.filter(user=user)
        assert recipes.count() == 1
        recipe = recipes[0]
        assert recipe.tags.count() == 2
        assert tag_indian in recipe.tags.all()
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=user,
            ).exists()
            assert exists

    def test_create_tag_on_update(self, authenticated_client,
                                  create_recipe, detail_url):
        """Test creating tag when updating a recipe"""
        client, user = authenticated_client
        recipe = create_recipe(user=user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = client.patch(url, payload, format='json')

        assert res.status_code == status.HTTP_200_OK
        new_tag = Tag.objects.get(user=user, name='Lunch')
        assert new_tag in recipe.tags.all()

    def test_update_recipe_assign_tag(self, authenticated_client,
                                      create_recipe, detail_url):
        """Test assigning an existing tag when updating a recipe"""
        client, user = authenticated_client
        tag_breakfast = Tag.objects.create(user=user, name='Breakfast')
        recipe = create_recipe(user=user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = client.patch(url, payload, format='json')

        assert res.status_code == status.HTTP_200_OK
        assert tag_lunch in recipe.tags.all()
        assert tag_breakfast not in recipe.tags.all()

    def test_clear_recipe_tags(self, authenticated_client,
                               create_recipe, detail_url):
        """Test clearing a recipes tags"""
        client, user = authenticated_client
        tag = Tag.objects.create(user=user, name='Desert')
        recipe = create_recipe(user=user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = client.patch(url, payload, format='json')

        assert res.status_code == status.HTTP_200_OK
        assert recipe.tags.count() == 0

    def test_crate_recipe_with_new_ingredient(self, authenticated_client):
        """Test creating a recipe with new ingredients"""
        client, user = authenticated_client
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}],
        }
        res = client.post(RECIPES_URL, payload, format='json')

        assert res.status_code == status.HTTP_201_CREATED
        recipes = Recipe.objects.filter(user=user)
        assert recipes.count() == 1
        recipe = recipes[0]
        assert recipe.ingredients.count() == 2
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=user,
            ).exists()
            assert exists

    def test_create_recipe_with_existing_ingredient(self,
                                                    authenticated_client):
        """Test creating a new recipe with existing ingredient"""
        client, user = authenticated_client
        ingredient = Ingredient.objects.create(user=user, name='Lemon')
        payload = {
            'title': 'Vietnamese Soup',
            'time_minutes': 26,
            'price': '2.55',
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish Sauce'}]
        }
        res = client.post(RECIPES_URL, payload, format='json')

        assert res.status_code == status.HTTP_201_CREATED
        recipes = Recipe.objects.filter(user=user)
        assert recipes.count() == 1
        recipe = recipes[0]
        assert recipe.ingredients.count() == 2
        assert ingredient in recipe.ingredients.all()
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=user
            ).exists()
            assert exists

    def test_create_ingredient_on_update(self, authenticated_client,
                                         create_recipe, detail_url):
        """Test creating an ingredient when updating a recipe"""
        client, user = authenticated_client
        recipe = create_recipe(user=user)

        payload = {'ingredients': [{'name': 'Limes'}]}
        url = detail_url(recipe.id)
        res = client.patch(url, payload, format='json')

        assert res.status_code == status.HTTP_200_OK
        new_ingredient = Ingredient.objects.get(user=user, name='Limes')
        assert new_ingredient in recipe.ingredients.all()

    def test_update_recipe_assign_ingredient(self, authenticated_client,
                                             create_recipe, detail_url):
        """Test assigning an existing ingredient when updating a recipe"""
        client, user = authenticated_client
        ingredient1 = Ingredient.objects.create(user=user, name='Pepper')
        recipe = create_recipe(user=user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=user, name='Salt')
        payload = {'ingredients': [{'name': 'Salt'}]}
        url = detail_url(recipe.id)
        res = client.patch(url, payload, format='json')

        assert res.status_code == status.HTTP_200_OK
        assert ingredient2 in recipe.ingredients.all()
        assert ingredient1 not in recipe.ingredients.all()

    def test_clear_recipe_ingredients(self, authenticated_client,
                                      create_recipe, detail_url):
        """Test clearing a recipes ingredients"""
        client, user = authenticated_client
        ingredient = Ingredient.objects.create(user=user, name='Garlic')
        recipe = create_recipe(user=user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = client.patch(url, payload, format='json')

        assert res.status_code == status.HTTP_200_OK
        assert recipe.ingredients.count() == 0

    def test_filter_by_tags(self, authenticated_client,
                            create_recipe):
        """Test filtering recipes by tags"""
        client, user = authenticated_client
        r1 = create_recipe(user=user, title='Thai vegetable curry')
        r2 = create_recipe(user=user, title='Aubergine with tahini')
        tag1 = Tag.objects.create(user=user, name='Vegan')
        tag2 = Tag.objects.create(user=user, name='Vegetarian')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=user, title='Fish and chips')

        params = {'tags': f'{tag1.id}, {tag2.id}'}
        res = client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        assert s1.data in res.data
        assert s2.data in res.data
        assert s3.data not in res.data

    def test_filter_by_ingredients(self, authenticated_client, create_recipe):
        """Test filtering recipes by ingredients"""
        client, user = authenticated_client
        r1 = create_recipe(user=user, title='Posh beans on toast')
        r2 = create_recipe(user=user, title='Chicken Cacciatiore')
        in1 = Ingredient.objects.create(user=user, name='Feta cheese')
        in2 = Ingredient.objects.create(user=user, name='Chicken')
        r1.ingredients.add(in1)
        r2.ingredients.add(in2)
        r3 = create_recipe(user=user, title='Red Lentil daal')

        params = {'ingredients': f'{in1.id}, {in2.id}'}
        res = client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        assert s1.data in res.data
        assert s2.data in res.data
        assert s3.data not in res.data


class TestImageUpload:
    """Test for the image upload API"""

    def test_upload_image(self, authenticated_client,
                          create_recipe, image_upload_url):
        """Test uploading an image to a recipe"""
        client, user = authenticated_client
        recipe = create_recipe(user=user)
        url = image_upload_url(recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = client.post(url, payload, format='multipart')

        recipe.refresh_from_db()
        assert res.status_code == status.HTTP_200_OK
        assert 'image' in res.data
        assert os.path.exists(recipe.image.path)

    def test_upload_image_bad_request(self, authenticated_client,
                                      image_upload_url, create_recipe):
        """Test uploading invalid image"""
        client, user = authenticated_client
        recipe = create_recipe(user=user)
        url = image_upload_url(recipe.id)
        payload = {'image': 'notanimage'}
        res = client.post(url, payload, format='multipart')

        assert res.status_code == status.HTTP_400_BAD_REQUEST
