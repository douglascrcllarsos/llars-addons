"""Hace importables los módulos de contadores/rootfs/app en los tests."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "contadores" / "rootfs" / "app"
sys.path.insert(0, str(APP))
