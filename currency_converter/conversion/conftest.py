import pytest


@pytest.fixture
def user(django_user_model):
    yield django_user_model.objects.create_user(
        email="some@email.com", password="something"
    )
    django_user_model.objects.all().delete()
