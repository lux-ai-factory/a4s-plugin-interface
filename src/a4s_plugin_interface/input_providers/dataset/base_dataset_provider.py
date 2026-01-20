import math
import random
from abc import ABC, abstractmethod
from typing import Any, Iterator


def is_tensor(obj):
    return "tensor" in str(type(obj)).lower()


def is_numpy_array(obj):
    return "numpy" in str(type(obj)).lower() and "ndarray" in str(type(obj)).lower()


def is_pandas_dataframe_or_series(obj):
    return "pandas" in str(type(obj)).lower()


class BaseDatasetProvider(ABC):
    def __init__(
        self, shuffle: bool = False, batch_size: int | None = None, *args, **kwargs
    ):
        # dataset could be a indexible object or a tuple of such objects
        self._dataset = None
        self._read_args = args
        self._read_kwargs = kwargs

        self.shuffle = shuffle
        self.batch_size = batch_size or len(self)

    @abstractmethod
    def read_data(self, *args, **kwargs) -> Any:
        # this function should implement the logic to set the `dataset` property
        pass

    @property
    def dataset(self) -> Any:
        if self._dataset is None:
            self._dataset = self.read_data(*self._read_args, **self._read_kwargs)
        return self._dataset

    def __len__(self) -> int:
        if isinstance(self.dataset, tuple):
            return len(self.dataset[0])

        return len(self.dataset)

    def __getitem__(self, idx: int) -> Any:
        if isinstance(self.dataset, tuple):
            return tuple(d[idx] for d in self.dataset)

        return self.dataset[idx]

    def get_all(self):
        return self._batch_from_indices(range(len(self)))

    def get_batch(self, batch_idx: int):
        start = batch_idx * self.batch_size
        end = min(start + self.batch_size, len(self))
        return self._batch_from_indices(range(start, end))

    def __iter__(self) -> Iterator:
        indices = list(range(len(self)))
        if self.shuffle:
            random.shuffle(indices)

        for i in range(0, len(indices), self.batch_size):
            yield self._batch_from_indices(indices[i : i + self.batch_size])

    def _batch_from_indices(self, indices):
        return self._batch(self.dataset, indices)

    def _batch(self, dataset, indices):
        if isinstance(dataset, tuple):
            return tuple(self._batch(d, indices) for d in dataset)

        if is_numpy_array(dataset) or is_tensor(dataset):
            return dataset[list[indices]]
        if is_pandas_dataframe_or_series(dataset):
            return dataset.iloc[list[indices]]

        return [dataset[idx] for idx in indices]

    @property
    def num_batches(self) -> int:
        return math.ceil(len(self) / self.batch_size)
