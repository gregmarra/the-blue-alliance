import datetime
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fakeredis import FakeRedis
from flask import Flask
from flask_caching.backends.nullcache import NullCache
from flask_caching.backends.rediscache import RedisCache
from freezegun import freeze_time

from backend.common.decorators import cached_public
from backend.common.flask_cache import configure_flask_cache
from backend.common.redis import RedisClient


def test_no_cached_public(app: Flask) -> None:
    @app.route("/")
    def view():
        return "Hello!"

    resp = app.test_client().get("/")
    assert resp.headers.get("Cache-Control") is None
    assert resp.headers.get("ETag") is None


def test_no_cached_public_on_error(app: Flask) -> None:
    @app.route("/")
    @cached_public
    def view():
        return "Error", 401

    resp = app.test_client().get("/")
    assert resp.headers.get("Cache-Control") is None
    assert resp.headers.get("ETag") is None


def test_cached_public_default(app: Flask) -> None:
    @app.route("/")
    @cached_public
    def view():
        return "Hello!"

    resp = app.test_client().get("/")
    assert resp.headers.get("Cache-Control") == "public, max-age=61, s-maxage=61"


def test_cached_public_timeout(app: Flask) -> None:
    @app.route("/")
    @cached_public(timeout=3600)
    def view():
        return "Hello!"

    resp = app.test_client().get("/")
    assert resp.headers.get("Cache-Control") == "public, max-age=3600, s-maxage=3600"


def test_cached_public_etag(app: Flask) -> None:
    @app.route("/")
    @cached_public
    def view():
        return "Hello!"

    resp = app.test_client().get("/")
    etag = resp.headers.get("ETag")
    assert etag is not None

    # Check that a valid etag returns 304
    resp2 = app.test_client().get("/", headers={"If-None-Match": etag})
    assert resp2.status_code == 304
    assert resp2.get_data(as_text=True) == ""

    # Check that an invalid etag returns a normal response
    resp3 = app.test_client().get("/", headers={"If-None-Match": "bad-etag"})
    assert resp3.status_code == 200
    assert resp3.get_data(as_text=True) == "Hello!"


@pytest.mark.filterwarnings("ignore::UserWarning:flask_caching")
def test_flask_cache_null_cache_by_default(app: Flask) -> None:
    configure_flask_cache(app)

    @app.route("/")
    @cached_public
    def view():
        return "Hello!"

    assert hasattr(app, "cache")
    assert isinstance(app.cache.cache, NullCache)

    resp = app.test_client().get("/")
    assert resp.status_code == 200


def test_flask_cache_with_redis(monkeypatch: MonkeyPatch, app: Flask) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr(RedisClient, "get", MagicMock(return_value=fake_redis))
    configure_flask_cache(app)

    @app.route("/")
    @cached_public
    def view():
        return "Hello!"

    assert hasattr(app, "cache")
    assert isinstance(app.cache.cache, RedisCache)

    resp = app.test_client().get("/")
    assert resp.status_code == 200

    assert app.cache.get("view//") == resp.data.decode()


def test_flask_cache_with_redis_after_timeout(
    monkeypatch: MonkeyPatch, app: Flask
) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr(RedisClient, "get", MagicMock(return_value=fake_redis))
    configure_flask_cache(app)

    @app.route("/")
    @cached_public(timeout=10)
    def view():
        return "Hello!"

    assert hasattr(app, "cache")
    assert isinstance(app.cache.cache, RedisCache)

    with freeze_time() as frozen_time:
        resp = app.test_client().get("/")
        assert resp.status_code == 200

        assert app.cache.get("view//") == resp.data.decode()

        # Tick past the expiration, so the next get should return None
        frozen_time.tick(delta=datetime.timedelta(seconds=15))

        assert app.cache.get("view//") is None


def test_flask_cache_with_redis_skips_errors(
    monkeypatch: MonkeyPatch, app: Flask
) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr(RedisClient, "get", MagicMock(return_value=fake_redis))
    configure_flask_cache(app)

    @app.route("/")
    @cached_public
    def view():
        return "Hello!", 500

    assert hasattr(app, "cache")
    assert isinstance(app.cache.cache, RedisCache)

    resp = app.test_client().get("/")
    assert resp.status_code == 500
    assert app.cache.get("view//") is None