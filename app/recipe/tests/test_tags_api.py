"""
Test for the tags API
"""
import pytest

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def detail_url():
    def _detail_url(recipe_id):
        """Create and return an ingredient detail URL"""
        return reverse('recipe:tag-detail', args=[recipe_id])
    return _detail_url


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
class TestPublicApi:
    """Test unanuthenticated API request"""
    def test_auth_required(self, api_client):
        """Test auth is required for retroeving tags"""
        res = api_client.get(TAGS_URL)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPrivateApi:
    """Test authenticated API rquest"""
    def test_retrieve_tags(self, authenticated_client):
        client, user = authenticated_client
        Tag.objects.create(user=user, name='Vegan')
        Tag.objects.create(user=user, name='Desert')

        res = client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        assert res.status_code == status.HTTP_200_OK
        assert res.data == serializer.data

    def test_tags_limited_to_user(self, create_user, authenticated_client):
        """Test list of tags is limited to authenticated user"""
        client, user = authenticated_client
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='Fruity')
        tag = Tag.objects.create(user=user, name='Comfort food')

        res = client.get(TAGS_URL)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]['name'] == tag.name
        assert res.data[0]['id'] == tag.id

    def test_update_tag(self, authenticated_client, detail_url):
        """Test updating a tag"""
        client, user = authenticated_client
        tag = Tag.objects.create(user=user, name='After Dinner')

        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        res = client.patch(url, payload)

        assert res.status_code == status.HTTP_200_OK
        tag.refresh_from_db()
        assert tag.name == payload['name']

    def test_delete_tag(self, authenticated_client, detail_url):
        """Test deleting a tag"""
        client, user = authenticated_client
        tag = Tag.objects.create(user=user, name='Breakfast')

        url = detail_url(tag.id)
        res = client.delete(url)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        tags = Tag.objects.filter(user=user)
        assert not tags.exists()

    def test_filter_tags_assigned_to_recipes(self, authenticated_client):
        """Test listing tags to those assigned to recipes"""
        client, user = authenticated_client
        tag1 = Tag.objects.create(user=user, name='Breakfast')
        tag2 = Tag.objects.create(user=user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Green eggs on toast',
            time_minutes=10,
            price=Decimal('2.20'),
            user=user,
        )
        recipe.tags.add(tag1)

        res = client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        assert s1.data in res.data
        assert s2.data not in res.data

    def test_filtered_tags_unique(self, authenticated_client):
        """Tests filtered tags return a unique list"""
        client, user = authenticated_client
        tag = Tag.objects.create(user=user, name='Breakfast')
        Tag.objects.create(user=user, name='Dinner')
        recipe1 = Recipe.objects.create(
            title='Pancakes',
            time_minutes=5,
            price=Decimal('5.00'),
            user=user,
        )
        recipe2 = Recipe.objects.create(
            title='Porridge',
            time_minutes=3,
            price=Decimal('2.00'),
            user=user,
        )
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = client.get(TAGS_URL, {'assigned_only': 1})

        assert len(res.data) == 1
