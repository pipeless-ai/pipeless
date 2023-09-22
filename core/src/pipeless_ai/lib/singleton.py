from typing import Generic, Type, TypeVar, Any

T = TypeVar('T')

class Singleton(type, Generic[T]):
    _instances: dict[Type[T], T] = {}
    def __call__(cls: Any, *args, **kwargs) -> T:
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
