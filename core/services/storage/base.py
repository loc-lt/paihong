from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def save(self, source_path: str, storage_key: str) -> None:
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        pass

    @abstractmethod
    def get_url(self, storage_key: str) -> str:
        pass

    @abstractmethod
    def backend_type(self) -> int:
        pass
