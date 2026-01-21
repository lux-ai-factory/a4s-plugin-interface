from typing import Any
from abc import abstractmethod
from a4s_plugin_interface.input_providers.base_input_provider import BaseInputProvider


class BaseModelProvider(BaseInputProvider):
    def __init__(self, *args, **kwargs):
        self._data = None
        self._model_args = args
        self._model_kwargs = kwargs

    @abstractmethod
    def _read_data(self, *args, **kwargs):
        return self.load_model(*args, **kwargs)

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        pass

    @property
    def model(self):
        if self._data is None:
            self._data = self._read_data(*self._model_args, **self._model_kwargs)
        return self._data
