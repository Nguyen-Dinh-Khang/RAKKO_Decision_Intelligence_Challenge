"""
tactical_playbook - Gói Sách lược Chiến thuật (Tactical Playbook Package)
Được cấu trúc modular theo chuẩn đặc tả Word/Function_md/tactical_playbook_engine.md
"""

from .engine import TacticalPlaybookEngine, run_tactical_playbook
from .config import *

__all__ = ["TacticalPlaybookEngine", "run_tactical_playbook"]
