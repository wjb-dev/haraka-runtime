import abc
from typing import Protocol


class Adapter(abc.ABC):
    name: str

    @abc.abstractmethod
    async def startup(self): ...

    @abc.abstractmethod
    async def shutdown(self): ...


class DocsProvider(Protocol):
    docs_url: str
    openapi_url: str
