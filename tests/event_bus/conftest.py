"""Event Bus test root — load .env before any imports."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")
