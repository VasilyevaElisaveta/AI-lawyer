"""
Узлы графа обработки ClaimsAgent.

Организация:
- classification/       — классификация дела
- document_generation/  — генерация документов
- validation/           — валидация

"""

from .classification.classification import classification_node
from .validation.validation import validation_node
from .document_generation.intake import intake_node
from .document_generation.research import research_node
from .document_generation.calc import calculator_node
from .document_generation.generator import generator_node
from .document_generation.qa import qa_node
from .continue_task import evaluate_continue_task


__all__ = [
    "classification_node",
    "intake_node",
    "validation_node",
    "research_node",
    "calculator_node",
    "generator_node",
    "qa_node",
    "evaluate_continue_task"
]