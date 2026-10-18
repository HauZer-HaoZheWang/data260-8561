from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient

from .config import MONGODB_DB, MONGODB_URI


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1500)


def get_db():
    return get_client()[MONGODB_DB]


def collection(name: str):
    return get_db()[name]


def close_client() -> None:
    get_client.cache_clear()
