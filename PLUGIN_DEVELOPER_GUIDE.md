# A4S Plugin Developer Guide

This guide is for developers who want to create a new evaluation plugin for the A4S platform and do not already know how the platform is organized.

## 1. What A4S Is

A4S is split into several repositories that work together:

- `a4s-backend`: Django API, project management, plugin configuration storage, evaluation orchestration, result storage.
- `a4s-eval`: asynchronous worker that executes plugin code and posts measurements back to the backend.
- `a4s-webapp`: browser UI used to enable plugins, configure them, start evaluations, and inspect results.
- `a4s-plugin-interface`: the Python contract you implement when writing a plugin.
- `a4s-plugin-manager`: plugin discovery and loading logic.

As a plugin developer, the most important point is this:

- the backend loads your plugin to discover it and build its configuration form.
- the eval worker loads the same plugin to execute the evaluation.

That means your plugin code must be safe to import in both environments.

## 2. How Plugin Execution Works

The lifecycle of a plugin is:

1. Your plugin project is placed in the directory configured by `PLUGIN_PATH`.
2. The backend and eval worker both mount that directory as `/app/plugins`.
3. The plugin manager scans the plugin directories, imports plugin packages, and finds classes that inherit from `BaseEvaluationPlugin`.
4. In the web UI, a user enables the plugin for a project.
5. The backend loads the plugin class and turns its Pydantic config model into a JSON schema form.
6. The user saves a project-level plugin configuration.
7. When an evaluation is started, the backend creates an evaluation record and snapshots the plugin configuration into that run.
8. The eval worker loads the plugin, downloads the selected dataset and model files, calls your plugin, collects the emitted metrics, and posts them back to the backend.
9. The web UI fetches the measurements and renders them using the visualization metadata provided by the plugin.

Two consequences matter in practice:

- configuration is defined by your plugin class.
- evaluation results are defined by the metrics your plugin exports.

## 3. Discovery Rules

Your plugin is discovered by `a4s-plugin-manager`. The loader scans each top-level folder in `PLUGIN_PATH` and looks for one importable Python package in one of these layouts:

### `src` layout

```text
my-plugin-project/
├── pyproject.toml
└── src/
    └── my_plugin/
        ├── __init__.py
        └── plugin.py
```

### Direct package layout

```text
my-plugin-project/
├── pyproject.toml
└── my_plugin/
    ├── __init__.py
    └── plugin.py
```

The package must export the plugin class from `__init__.py`. The loader imports the package and registers every class that inherits from `BaseEvaluationPlugin`.

Important details:

- the name shown by the platform is the Python class name, for example `MyPlugin`.
- the plugin project folder can be named differently from the package.
- if import fails, the plugin will not appear in the platform.

## 4. Prerequisites

To develop a plugin locally, you need:

- Python 3.12+
- `uv`
- Docker and Docker Compose
- Git
- the sibling repositories checked out at the same directory level:

```text
your-workspace/
├── a4s-backend
├── a4s-eval
└── a4s-webapp
```

If the repositories use private Git dependencies, export a GitHub personal access token before building containers:

```bash
export GIT_PAT=<your_token>
```

## 5. Local Development Setup

### 5.1 Configure the plugin folder

In `a4s-backend/env.development`, set `PLUGIN_PATH` to an absolute path on your machine:

```dotenv
PLUGIN_PATH=/absolute/path/to/your/plugins
```

This path is mounted into both containers:

- backend: `${PLUGIN_PATH}:/app/plugins`
- eval worker: `${PLUGIN_PATH}:/app/plugins`

So if your local folder is:

```text
/absolute/path/to/your/plugins/
└── my-plugin-project/
```

then both services will be able to load it.

### 5.2 Start the full stack

From `a4s-backend`:

```bash
docker compose --env-file env.development \
  -f docker-compose-infra.development.yml \
  -f docker-compose.development.yml up
```

If you changed dependencies and need a rebuild:

```bash
docker compose --env-file env.development \
  -f docker-compose-infra.development.yml \
  -f docker-compose.development.yml up --build
```

The UI is served on `http://localhost:5173` and the backend on `http://localhost:8000`.

## 6. Create a Plugin Project

Create a new project in your plugin workspace:

```bash
mkdir -p /absolute/path/to/your/plugins
cd /absolute/path/to/your/plugins
mkdir my-a4s-plugin
cd my-a4s-plugin
uv init --lib
uv add git+https://github.com/lux-ai-factory/a4s-plugin-interface
```

Recommended structure:

```text
my-a4s-plugin/
├── pyproject.toml
├── README.md
├── src/
│   └── my_a4s_plugin/
│       ├── __init__.py
│       └── plugin.py
└── uv.lock
```

## 7. The Plugin Contract

Every plugin must inherit from `BaseEvaluationPlugin[T]`, where `T` is a Pydantic model representing the configuration form.

The core pieces are:

- `config_type`: derived from your generic type parameter.
- `evaluate(config_data)`: main execution logic.
- `@metric("...")`: declares metric exporters.
- `get_metric_visualizations(config_data)`: tells the UI how to render results.
- `set_dataset_input_provider(file_content)`: optional dataset parsing hook.
- `set_model_input_provider(file_content)`: optional model parsing hook.
- `parse_config_from_dataset()`: optional auto-configuration hook.
- `report_progress(TaskProgress(...))`: optional progress updates for long-running evaluations.

## 8. Minimal Example

This example reads a CSV dataset, computes an average score and a pass rate, and shows both metrics in the UI.

### `src/my_a4s_plugin/plugin.py`

```python
from typing import Any

from pydantic import BaseModel, Field

from a4s_plugin_interface import (
    BaseEvaluationPlugin,
    ChartType,
    Measure,
    MetricVisualization,
    PluginFeatureFlags,
    TaskProgress,
    metric,
)
from a4s_plugin_interface.input_providers.csv_input_provider import CsvInputProvider


class ConfigFormSchema(BaseModel):
    score_column: str = Field(
        ...,
        description="Name of the CSV column containing numeric scores.",
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Scores greater than or equal to this value count as passing.",
    )


class ExampleCsvPlugin(BaseEvaluationPlugin[ConfigFormSchema]):
    form_ui_schema = {
        "score_column": {
            "ui:placeholder": "for example: score"
        }
    }

    @property
    def feature_flags(self) -> PluginFeatureFlags:
        return PluginFeatureFlags(can_parse_config_from_dataset=True)

    @property
    def display_icon(self) -> str:
        return "analytics"

    def set_dataset_input_provider(self, file_content: bytes | None):
        if file_content is None:
            raise ValueError("This plugin requires a dataset file")
        self.dataset_input_provider = CsvInputProvider(file_content)
        return self.dataset_input_provider

    def evaluate(self, config_data: dict) -> Any:
        config = self.validate_config_form_data(config_data)
        rows = self.get_dataset()

        scores: list[float] = []
        total_rows = len(rows)

        for index, row in enumerate(rows):
            raw_value = row.get(config.score_column)
            if raw_value is None or raw_value == "":
                continue

            scores.append(float(raw_value))

            if total_rows:
                self.report_progress(
                    TaskProgress(
                        progress=(index + 1) / total_rows,
                        extra={"rows_processed": index + 1},
                    )
                )

        passing = [score for score in scores if score >= config.threshold]

        return {
            "scores": scores,
            "average_score": (sum(scores) / len(scores)) if scores else 0.0,
            "pass_rate": (len(passing) / len(scores)) if scores else 0.0,
        }

    @metric("Average score")
    def average_score_metric(self, evaluation_output: dict) -> list[Measure]:
        return [
            Measure(
                name="Average score",
                score=float(evaluation_output["average_score"]),
            )
        ]

    @metric("Pass rate")
    def pass_rate_metric(self, evaluation_output: dict) -> list[Measure]:
        return [
            Measure(
                name="Pass rate",
                score=float(evaluation_output["pass_rate"]),
                unit="ratio",
            )
        ]

    def get_metric_visualizations(self, config_data: dict) -> list[MetricVisualization]:
        return [
            MetricVisualization(
                chart_type=ChartType.TABLE,
                metrics=["Average score", "Pass rate"],
            ),
            MetricVisualization(
                chart_type=ChartType.BARS,
                metrics=["Average score", "Pass rate"],
            ),
        ]

    def parse_config_from_dataset(self) -> dict | None:
        rows = self.get_dataset()
        if not rows:
            return None

        first_row = rows[0]
        if "score" in first_row:
            return {
                "score_column": "score",
                "threshold": 0.5,
            }

        return None
```

### `src/my_a4s_plugin/__init__.py`

```python
from .plugin import ExampleCsvPlugin

__all__ = ["ExampleCsvPlugin"]
```

## 9. Configuration Forms

Your config model is a Pydantic model. The backend converts it into JSON schema using `model_json_schema(mode='validation')`. The frontend then renders it with `react-jsonschema-form`.

That means:

- field names become form fields.
- Pydantic constraints such as `ge`, `le`, and enum values become form validation rules.
- descriptions appear in the UI.

Example:

```python
class ConfigFormSchema(BaseModel):
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
```

This produces a numeric field constrained to the range `[0.0, 1.0]`.

### UI customization

You can customize the form with `form_ui_schema`:

```python
form_ui_schema = {
    "threshold": {
        "ui:widget": "range"
    }
}
```

The frontend sends the current config back to the backend as the user edits the form. Your plugin can react through `on_config_change`.

## 10. Dynamic Forms With `on_config_change`

Override `on_config_change` when the available options depend on previous user input or when you want to auto-fill values.

The method receives the current, possibly incomplete form data and returns:

- updated form data
- updated schema
- updated UI schema

Pattern:

```python
def on_config_change(self, form_data):
    schema, ui_schema = self.get_full_schema()

    if form_data and form_data.get("mode") == "advanced":
        schema["properties"]["advanced_option"] = {
            "title": "Advanced option",
            "type": "integer",
            "default": 10,
        }

    return form_data, schema, ui_schema
```

Use this when you need dynamic dropdowns, conditional fields, or auto-computed defaults.

## 11. Datasets and Models

The eval worker downloads dataset and model files from the backend and passes the raw bytes into your plugin.

If your plugin needs a dataset, override `set_dataset_input_provider`.

If your plugin needs a model file, override `set_model_input_provider`.

The base class provides:

- `get_dataset()`: returns parsed dataset data from your dataset provider.
- `get_model()`: returns parsed model data from your model provider.

### Built-in CSV provider

The interface package includes `CsvInputProvider`, which turns CSV bytes into `list[dict]`.

Example:

```python
def set_dataset_input_provider(self, file_content: bytes | None):
    if file_content is None:
        raise ValueError("Dataset required")
    self.dataset_input_provider = CsvInputProvider(file_content)
    return self.dataset_input_provider
```

### Custom input providers

If you need another format, create a subclass of `BaseInputProvider`.

Example skeleton:

```python
from a4s_plugin_interface.input_providers.base_input_provider import BaseInputProvider


class JsonInputProvider(BaseInputProvider):
    def _read_data(self, file_content: bytes):
        import json
        return json.loads(file_content.decode("utf-8"))
```

## 12. Metrics and Results

The `evaluate` method can return any intermediate Python object. That object is then passed to each method decorated with `@metric`.

Metric methods must return `list[Measure]`.

`Measure` fields are:

- `name`: metric name shown in the UI.
- `score`: numeric value.
- `description`: optional text.
- `unit`: optional unit.
- `time`: timestamp.
- `error`: optional error message.
- `feature_pid`: optional feature reference.

One plugin can export several metrics. For example:

```python
@metric("Accuracy")
def accuracy_metric(self, evaluation_output) -> list[Measure]:
    ...


@metric("F1")
def f1_metric(self, evaluation_output) -> list[Measure]:
    ...
```

If you do not override `get_metric_visualizations`, the frontend will display a single table containing all metrics returned by `get_metrics()`.

## 13. Visualizations

Use `get_metric_visualizations(config_data)` to describe how the UI should render results.

Supported chart types in the interface are:

- `table`
- `line`
- `radar`
- `scatter`
- `kde`
- `bars`
- `pie`

Example:

```python
def get_metric_visualizations(self, config_data: dict) -> list[MetricVisualization]:
    return [
        MetricVisualization(chart_type=ChartType.TABLE, metrics=["Accuracy", "F1"]),
        MetricVisualization(chart_type=ChartType.RADAR, metrics=["Accuracy", "F1"]),
    ]
```

The frontend filters measurements by the metric names you list here.

## 14. Feature Flags and Icons

Plugins can influence parts of the UI.

### Feature flags

Override `feature_flags` when you want the UI to expose extra capabilities.

Currently implemented:

- `can_parse_config_from_dataset`: when `True`, the configuration page shows a dataset dropdown and lets the user derive config values from the selected dataset.

Example:

```python
@property
def feature_flags(self) -> PluginFeatureFlags:
    return PluginFeatureFlags(can_parse_config_from_dataset=True)
```

### Display icon

Override `display_icon` to return a Material icon name:

```python
@property
def display_icon(self) -> str:
    return "analytics"
```

## 15. Automatic Config From Dataset

If your plugin can infer configuration from the input dataset, implement `parse_config_from_dataset` and enable the feature flag.

Flow:

1. User opens the plugin config page.
2. User selects a dataset.
3. Backend loads the plugin and calls `set_dataset_input_provider(file_content)`.
4. Backend calls `parse_config_from_dataset()`.
5. The returned config is passed through `on_config_change` and displayed in the form.

This is useful for:

- discovering field names from a CSV header
- suggesting label columns
- inferring task type from data
- pre-filling reasonable defaults

## 16. Progress Reporting

Long-running plugins can report progress during evaluation.

Use:

```python
self.report_progress(TaskProgress(progress=0.25, extra={"stage": "loading"}))
```

Rules:

- `progress` must be between `0.0` and `1.0`.
- `extra` can contain plugin-defined metadata.
- reporting progress is optional.

Do not override `_set_progress_callback`; that is managed by the evaluation runtime.

## 17. Dependency Management

This point is important.

The backend imports your plugin to build forms, even though it does not execute the evaluation logic. If your module imports heavy or optional runtime dependencies at module import time, plugin discovery can fail in the backend.

Recommended pattern:

- keep top-level imports lightweight.
- import heavy runtime dependencies inside `evaluate` or inside your input provider.

Example:

```python
def evaluate(self, config_data: dict):
    import numpy as np
    import onnxruntime as ort
    ...
```

If your plugin adds dependencies that must exist inside the containers, rebuild the stack with `--build`.

## 18. End-to-End Manual Test

Once your plugin is implemented, test it like this:

1. Place the plugin project under `PLUGIN_PATH`.
2. Start the A4S development stack.
3. Open the web UI.
4. Create or open a project.
5. Go to the plugin page and enable your plugin.
6. Open the plugin configuration page.
7. Confirm the form renders correctly.
8. Save a valid config.
9. Start an evaluation and select the dataset and model required by your plugin.
10. Wait for the worker to finish.
11. Open the evaluation results page and verify the measurements and charts.

What to verify:

- plugin is listed
- form loads
- validation behaves as expected
- config can be saved
- evaluation starts
- progress updates appear if implemented
- metrics are stored
- results render under the correct visualization types

## 19. Common Failure Modes

### Plugin does not appear in the UI

Check:

- the plugin project is inside `PLUGIN_PATH`
- `PLUGIN_PATH` is absolute and points to the correct folder
- the package has `__init__.py`
- the plugin class is exported from `__init__.py`
- the plugin class inherits from `BaseEvaluationPlugin`
- the plugin can be imported without raising an exception

### Form renders but evaluation fails

Likely causes:

- dataset or model provider was not implemented
- `evaluate` assumes a file was provided but none was selected
- heavy dependency missing in the eval image
- config validation passes, but runtime logic expects extra fields

### Plugin disappears after adding dependencies

Likely cause:

- a top-level import now requires a package that exists only in the eval environment or has not been rebuilt in the container image

Move that import inside `evaluate` or rebuild containers.

### Dynamic form logic behaves unexpectedly

Check:

- `on_config_change` returns a three-item tuple: config, schema, ui schema
- your returned schema is valid JSON schema
- you handle incomplete form data safely

### Results page is empty

Check:

- your metric methods are decorated with `@metric`
- metric methods return `list[Measure]`
- the metric names used in `get_metric_visualizations` match the names in the returned measures

### Evaluation uses an old config

The evaluation record snapshots the project plugin config when the run is created. Save the config first, then start a new evaluation.

## 20. Recommended Development Workflow

For a first implementation:

1. Start with a very small config model.
2. Use CSV as the dataset format if possible.
3. Return one or two metrics first.
4. Keep the default table visualization initially.
5. Add progress reporting only after the basic path works.
6. Add dynamic forms and dataset-derived config only when needed.

This keeps debugging simple.

## 21. Checklist Before Sharing a Plugin

- package exports the plugin class from `__init__.py`
- plugin imports cleanly in backend and eval environments
- config model has clear titles and descriptions
- invalid config is rejected cleanly
- dataset and model requirements are explicit
- metric names are stable and meaningful
- heavy dependencies are not imported at module import time
- manual end-to-end evaluation succeeds

## 22. Summary

To build an A4S plugin successfully, focus on five things:

1. make the package discoverable from `PLUGIN_PATH`
2. implement `BaseEvaluationPlugin[T]` with a clean config model
3. parse dataset and model files explicitly when needed
4. emit `Measure` objects through `@metric` methods
5. keep imports and dependencies safe for both backend discovery and eval execution

If those pieces are correct, the rest of the platform will be able to configure, execute, and display your plugin automatically.