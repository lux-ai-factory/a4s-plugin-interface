from typing import Any
from abc import ABC, abstractmethod


class BaseModelProvider(ABC):
    def __init__(self, *args, **kwargs):
        self._model = None
        self._model_args = args
        self._model_kwargs = kwargs

    @abstractmethod
    def load_model(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        pass

    @property
    def model(self):
        if self._model is None:
            self._model = self.load_model(*self._model_args, **self._model_kwargs)
        return self._model
