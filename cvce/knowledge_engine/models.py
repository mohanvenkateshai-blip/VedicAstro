from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class InvalidationReason(str, Enum):
    STALE = "stale"
    CONFLICT = "conflict"
    ERROR_IN_SOURCE = "error_in_source"
    MANUAL = "manual"
    SUPERSEDED = "superseded"


@dataclass
class GraphVersion:
    version: str
    node_count: int
    link_count: int
    loaded_at: datetime
    source: str = "knowledge-graph/graphify-out/graph.json"


@dataclass
class KnowledgeValidity:
    node_id: str
    is_valid: bool
    reason: Optional[InvalidationReason] = None
    details: str = ""
    invalidated_at: Optional[datetime] = None
