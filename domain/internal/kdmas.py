from dataclasses import dataclass


@dataclass
class KDMA:
    id_: str
    value: float

    def __str__(self):
        return f"{self.id_}: {self.value}"

    def __repr__(self):
        return f"{self.id_}: {self.value}"


class KDMAs:
    def __init__(self, kdmas: list[KDMA]):
        self.kdmas: list[KDMA] = kdmas
        self.kdma_map: dict[str, float] = {kdma.id_: kdma.value for kdma in kdmas}

    def __getitem__(self, kdma_id: str) -> float:
        return self.kdma_map[kdma_id]

    def __str__(self):
        return str([kdma for kdma in self.kdmas])

    def __repr__(self):
        return str([kdma for kdma in self.kdmas])
