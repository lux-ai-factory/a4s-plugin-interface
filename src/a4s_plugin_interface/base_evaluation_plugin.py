import inspect
from abc import ABC, abstractmethod
from typing import Any, get_args, get_origin, Callable, Tuple

from pydantic import BaseModel, Field

from a4s_plugin_interface.input_providers.base_input_provider import BaseInputProvider
from a4s_plugin_interface.models.measure import Measure, MetricVisualization, ChartType


def metric(name: str):
    """
    Decorator to mark a method as a metric exporter.
    Methods decorated with this should return a list of Measure objects.
    """
    def decorator(func: Callable):
        func.metric_name = name
        return func
    return decorator


class PluginFeatureFlags(BaseModel):
    can_parse_config_from_dataset: bool = Field(False, description="Show the dataset dropdown")
    extra: dict = Field({}, description="Additional feature flags")


class BaseEvaluationPlugin[T:BaseModel](ABC):
    """
    Abstract Base Class for evaluation plugins.
    Plugins should inherit from this class and provide a Pydantic model for their configuration.

    Example:
        class MyPlugin(BaseEvaluationPlugin[MyConfigModel]):
            ...
    """
    # UI Schema for RJSF (react-jsonschema-form) to customize form appearance
    form_ui_schema: dict = {}
    dataset_input_provider: BaseInputProvider | None = None
    model_input_provider: BaseInputProvider | None = None

    @property
    def feature_flags(self) -> PluginFeatureFlags:
        """
        Controls UI behavior on the frontend.
        Override this property in your subclass to change defaults.
        """
        return PluginFeatureFlags()


    @property
    def display_icon(self) -> str:
        """
        Controls the icon displayed in the plugin list.
        Use a Material Design icon name
        https://fonts.google.com/icons
        """
        return "extension"


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


    def get_metric_visualizations(self) -> list[MetricVisualization]:
        """
        Returns a list of MetricVisualization objects to render a list of
        visualizations on the front end and the metrics to display for each

        By default, returns a single visualization (TABLE) with all metrics
        """
        return [MetricVisualization(chart_type=ChartType.TABLE, metrics=self.get_metrics())]


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


    @abstractmethod
    def evaluate(self, config_data: dict) -> Any:
        """
        The main execution logic of the plugin.
        Developers should process the dataset/model here and return an intermediate result
        that will be passed to the metric methods.
        """
        raise NotImplementedError


    def set_dataset_input_provider(self, file_content: bytes | None) -> BaseInputProvider:
        """
        Optional: Initialize and return a specific input provider for the dataset.
        """
        pass


    def set_model_input_provider(self, file_content: bytes | None) -> BaseInputProvider:
        """
        Optional: Initialize and return a specific input provider for the model.
        """
        pass


    def get_dataset(self) -> Any:
        """
        Helper to retrieve parsed data from the dataset input provider.
        """
        if self.dataset_input_provider is None:
            raise Exception("Dataset input provider not set")
        return self.dataset_input_provider.get_data()


    def get_model(self) -> Any:
        """
        Helper to retrieve parsed data from the model input provider.
        """
        if self.model_input_provider is None:
            raise Exception("Model input provider not set")
        return self.model_input_provider.get_data()


    def get_config_form_schema(self) -> dict:
        """
        Generates a JSON Schema from the Pydantic config model for the frontend UI.
        """
        return self.config_type.model_json_schema(mode='validation')


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
        Optional: Converts the validated Pydantic model used for the UI form into a dict for internal use
        This can be overridden to add/change the structure of the input config data for use in the evaluate method
        """
        return form_schema.model_dump()

    def get_full_schema(self) -> Tuple[dict, dict]:
        """Helper to get the fresh, static baseline."""
        return self.get_config_form_schema(), self.get_config_form_ui_schema()


    # form_data passed here may be incomplete, so we don't validate and use MyConfigModel
    # It is the developer's responsibility to check for and use data accordingly here
    def on_config_change(self, form_data: T | None) -> Tuple[T | None, dict, dict]:
        """
        Hook called whenever the user changes a form value.
        Allows the plugin to dynamically update the schema (e.g. drop downs),
        the data (e.g. auto-fill), or the UI (e.g. hide fields).
        """
        # Default: Do nothing, just return what came in
        schema, ui_schema = self.get_full_schema()
        return form_data, schema, ui_schema


    def parse_config_from_dataset(self) -> dict | None:
        """
        Optional: Try to parse a valid config from the dataset.
        """
        return None
