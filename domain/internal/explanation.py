from typing import Any, Dict

class Explanation():
    def __init__(self, explanation_type: str, params: Dict[str, Any]):
        self.explanation_type: str = explanation_type
        self.params: Dict[str, Any] = params
