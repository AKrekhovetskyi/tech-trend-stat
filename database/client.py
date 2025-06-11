from typing import Any

from pymongo import MongoClient


class MongoClientSingleton(MongoClient):
    """Singleton class for MongoDB connection using MongoClient."""

    _instance = None

    def __init__(
        self,
        *,
        is_test: bool,
        cluster_host: str | None,
        **kwargs: Any,
    ) -> None:
        """
        Connect to a local MongoDB if `is_test` is `True`.
        Otherwise, connect to a Mongo cloud.
        """
        if not is_test:
            self._validate_production_params(cluster_host=cluster_host, **kwargs)
            client_kwargs = kwargs | dict(
                host=f"mongodb+srv://{kwargs.pop('username')}:"
                f"{kwargs.pop('password')}@{cluster_host}.mongodb.net/?"
                "retryWrites=true&w=majority",
            )
        else:
            client_kwargs = kwargs
        super().__init__(**client_kwargs)

    def __new__(cls, **_: Any) -> "MongoClientSingleton":
        """
        Create a new instance if it doesn't exist,
        otherwise return the existing one.
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _validate_production_params(**kwargs: Any) -> None:
        """Validate required parameters for the production environment."""
        if "username" not in kwargs or "password" not in kwargs or "cluster_host" not in kwargs:
            raise ValueError("`username`, `password`, and `cluster_host` are required in a production environment.")

    def close(self) -> None:
        """Close the MongoDB connection and reset the instance."""
        self._instance = None
        return super().close()
