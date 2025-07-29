import re
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass(frozen=True)
class RoboId:
    """Representation of a RoboID address."""

    node_type: str
    role: str
    place: str
    instance: Optional[str] = None

    def __str__(self) -> str:
        base = f"{self.node_type}.{self.role}@{self.place}"
        if self.instance:
            base += f"#{self.instance}"
        return base

    @classmethod
    def parse(cls, addr: str) -> "RoboId":
        """Parse a RoboID string into an instance."""
        match = re.fullmatch(r"([^@]+)@([^#]+)#?(.*)", addr)
        if not match:
            raise ValueError(f"Invalid RoboID format: {addr}")
        type_role, place, instance = match.groups()
        type_match = re.fullmatch(r"([^\.]+)\.(.+)", type_role)
        if not type_match:
            raise ValueError(f"Invalid type.role in RoboID: {addr}")
        node_type, role = type_match.groups()
        instance = instance or None
        if instance == "":
            instance = None
        return cls(node_type=node_type, role=role, place=place, instance=instance)

    def compare(self, other: "RoboId") -> Dict[str, object]:
        """Compare this RoboID with another and return similarity info."""
        differences: List[str] = []
        score = 0

        if self.node_type == other.node_type:
            score += 1
        else:
            differences.append("type")

        if self.role == other.role:
            score += 1
        else:
            differences.append("role")

        if self.place == other.place:
            score += 1
        else:
            differences.append("place")

        if self.instance == other.instance:
            score += 1
        else:
            differences.append("instance")

        similarity = score / 4.0
        return {"similarity": similarity, "differences": differences}
