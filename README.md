# A4S Plugin Interface

This project defines the base interface for creating evaluation plugins for the A4S system.

## Creating a New Plugin Project

To create a new plugin, follow these steps using `uv`.

### 1. Initialize the Project

Create a new directory for your plugin and initialize it as a Python project:

```
mkdir my-a4s-plugin
cd my-a4s-plugin
uv init --lib
```

### 2.

Add the a4s-plugin-interface dependency to your project:

```
uv add git+https://github.com/lux-ai-factory/a4s-plugin-interface
```
### 3. Implement the Plugin

Create your main plugin logic in `src/my_a4s_plugin/plugin.py`. You must implement the BaseEvaluationPlugin class.

#### Important Note on Dependencies
If your evaluation requires heavy dependencies (like `numpy`, `sklearn`, or `onnxruntime`), **do not import them at the top of the file**. Instead, import them inside the `evaluate` method.

This is because the `a4s-backend` discovers and loads the plugin classes to display configuration forms, but it does not run the evaluation. The heavy dependencies are only required by the `a4s-eval` module when the plugin is actually executed.
Evaluation dependencies will also need to be installed in the `a4s-eval` environment.


```python
# src/my_a4s_plugin/plugin.py
from a4s_plugin_interface.base_evaluation_plugin import BaseEvaluationPlugin


class MyPlugin(BaseEvaluationPlugin):
    def evaluate(self, config_data):
        # Heavy dependencies should be imported locally here
        import numpy as np
        
        # Your evaluation logic here
        return {"result": "success"}
```

### 4. Export the Plugin Class

Ensure your plugin class is properly exported in `src/my_a4s_plugin/__init__.py` so the plugin manager can discover it:

```python
# src/my_a4s_plugin/__init__.py
from .plugin import MyPlugin

__all__ = ["MyPlugin"]
```

### 5. Project Structure

Your project should now look like this:

```
my-a4s-plugin/
├── pyproject.toml
├── README.md
├── src/
│   └── my_a4s_plugin/
│       ├── __init__.py
│       └── plugin.py
└── uv.lock
```

### 6. Development

To install dependencies and prepare the environment:

```
uv sync
```