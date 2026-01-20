import inspect
from abc import ABC, abstractmethod
from typing import Any, get_args, get_origin, Callable

from pydantic import BaseModel

from a4s_plugin_interface.models.measure import Measure
from a4s_plugin_interface.input_providers.dataset import BaseDatasetProvider
from a4s_plugin_interface.input_providers.model import BaseModelProvider


def metric(name: str):
    """
    Decorator to mark a method as a metric exporter.
    Methods decorated with this should return a list of Measure objects.
    """

    def decorator(func: Callable):
        func.metric_name = name
        return func

    return decorator


class BaseEvaluationPlugin[T: BaseModel](ABC):
    """
    Abstract Base Class for evaluation plugins.
    Plugins should inherit from this class and provide a Pydantic model for their configuration.

    Example:
        class MyPlugin(BaseEvaluationPlugin[MyConfigModel]):
            ...
    """

    # UI Schema for RJSF (react-jsonschema-form) to customize form appearance
    form_ui_schema: dict = {}
    dataset_input_provider: BaseDatasetProvider | None = None
    model_input_provider: BaseModelProvider | None = None

    @abstractmethod
    def predict(self, config_data: dict) -> Any:
        """
        Compute the predictions of the model on the dataset.
        Useful when calling several metrics as the predictions could be shared/stored.
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, config_data: dict) -> Any:
        """
        The main execution logic of the plugin.
        Developers should process the dataset/model here and return an intermediate result
        that will be passed to the metric methods.
        """
        raise NotImplementedError

    @property
    def config_type(self) -> type[T]:
        """
        Retrieves the Pydantic model type used for plugin configuration.
        """
        for base in getattr(self.__class__, "__orig_bases__", []):
            if get_origin(base) is BaseEvaluationPlugin:
                return get_args(base)[0]
        raise TypeError("Could not determine Config type T")

    def get_metrics(self) -> list[str]:
        """
        Returns a list of all metric names defined in this plugin via the @metric decorator.
        """
        metrics = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "metric_name"):
                metrics.append(method.metric_name)
        return metrics

    def export_metrics(self, *args, **kwargs) -> list[Measure]:
        """
        Executes all methods decorated with @metric and aggregates their results.
        """
        results: list[Measure] = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "metric_name"):
                metric_measures: list[Measure] = method(*args, **kwargs)
                results.extend(metric_measures)
        return results

    def set_dataset_input_provider(
        self, file_content: bytes | None
    ) -> BaseDatasetProvider:
        """
        Optional: Initialize and return a specific input provider for the dataset.
        """
        pass

    def set_model_input_provider(self, file_content: bytes | None) -> BaseModelProvider:
        """
        Optional: Initialize and return a specific input provider for the model.
        """
        pass

    # NOTE: it could be a property
    def get_dataset(self) -> Any:
        """
        Helper to retrieve parsed data from the dataset input provider.
        """
        if self.dataset_input_provider is None:
            raise Exception("Dataset input provider not set")
        return self.dataset_input_provider.dataset

    # NOTE: it could be a property
    def get_model(self) -> Any:
        """
        Helper to retrieve parsed data from the model input provider.
        """
        if self.model_input_provider is None:
            raise Exception("Model input provider not set")
        return self.model_input_provider.model

    def get_config_form_schema(self) -> dict:
        """
        Generates a JSON Schema from the Pydantic config model for the frontend UI.
        """
        return self.config_type.model_json_schema()

    def validate_config_form_data(self, config_form_data: dict) -> T:
        """
        Validates incoming form data from frontend UI/backend DB against the Pydantic config model.
        """
        return self.config_type.model_validate(config_form_data)

    def get_config_form_ui_schema(self) -> dict:
        """
        Returns the UI schema for form customization.
        """
        return self.form_ui_schema

    def form_schema_to_internal(self, form_schema: T) -> dict:
        """
        Optional: Converts the validated Pydantic model used for the UI form
                  into a dict for internal use
        This can be overridden to add/change the structure of the input config data
        for use in the evaluate method
        """
        return form_schema.model_dump()
