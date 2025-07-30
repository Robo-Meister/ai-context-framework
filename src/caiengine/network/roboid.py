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

    def distance(self, other: "RoboId") -> float:
        """Return numeric distance between two RoboIDs.

        This is defined as ``1 - similarity`` of the compared attributes.
        """
        return 1.0 - self.compare(other)["similarity"]

    def is_visible_to(self, other: "RoboId") -> bool:
        """Check if this RoboID should be considered visible to ``other``.

        Currently nodes are visible to each other when they share the same
        ``place`` value.
        """
        return self.place == other.place
