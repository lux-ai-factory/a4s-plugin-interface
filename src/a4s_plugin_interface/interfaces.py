from abc import ABC, abstractmethod

class EvaluationPluginInterface(ABC):

    @abstractmethod
    def evaluate(self, context: dict, payload: dict):
        """Implement this method to evaluate data."""
        pass

    @abstractmethod
    def get_config(self) -> dict:
        """Implement this method to evaluate data."""
        pass
