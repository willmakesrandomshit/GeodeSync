"""Domain data models and immutable structures for GeodeSync."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class GameInstallation:
    path: str
    is_steam: bool = False
    version: Optional[str] = None
    manifest_locked: bool = False
    geode_installed: bool = False
    geode_version: Optional[str] = None


@dataclass
class ModInfo:
    id: str
    name: str
    version: str
    developer: str = "Unknown"
    enabled: bool = True
    path: str = ""
    is_incompatible: bool = False
    incompatibility_reason: str = ""
    description: str = ""


@dataclass
class DiagnosticResult:
    title: str
    status: str  # PASS, WARN, FAIL, INFO
    details: str
    color: str
    action_label: Optional[str] = None


@dataclass
class SaveSnapshot:
    name: str
    folder_path: str
    timestamp: float
    size_bytes: int
    is_healthy: bool = True
    summary: str = ""
