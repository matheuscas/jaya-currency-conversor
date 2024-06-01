import os
from unittest import mock
import pytest
from conversion.models import Conversion  # type: ignore


@pytest.fixture
def user(django_user_model):
    yield django_user_model.objects.create_user(
        email="some@email.com", password="something"
    )
    django_user_model.objects.all().delete()


@pytest.fixture
def teardown_conversions():
    yield
    Conversion.objects.all().delete()


@pytest.fixture(autouse=True)
def setenvvar(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        envvars = {
            "EXCHANGE_API_KEY": "KEY",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield
