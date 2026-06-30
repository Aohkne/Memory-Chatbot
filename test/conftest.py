import sys
from unittest.mock import MagicMock

sys.modules.setdefault("langchain_nvidia_ai_endpoints", MagicMock())

import pytest
import config


@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path, monkeypatch):
    memory_dir = tmp_path / "memory"
    transcripts_dir = tmp_path / "transcripts"
    memory_dir.mkdir()
    transcripts_dir.mkdir()

    monkeypatch.setattr(config, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(config, "TRANSCRIPTS_DIR", transcripts_dir)
    monkeypatch.setattr(config, "INDEX_PATH", memory_dir / "MEMORY.md")
    monkeypatch.setattr(config, "LOCK_PATH", memory_dir / ".consolidation.lock")

    return tmp_path
