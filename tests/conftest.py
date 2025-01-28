# tests/conftest.py

import pytest
from pathlib import Path
from epysuite.config import EPySuiteConfig

@pytest.fixture
def mock_episuite_dir(tmp_path):
    """Create a mock EPI Suite directory structure."""
    es_dir = tmp_path / "EPISUITE41"
    es_dir.mkdir()
    
    # Create mock executable
    (es_dir / "epiwin1.exe").touch()
    (es_dir / "STPWIN32.exe").touch()
    
    # Create mock input/output files
    (es_dir / "epi_inp.txt").write_text("DEFAULT\n\n\n")
    (es_dir / "sumbrief.epi").touch()
    
    return es_dir

@pytest.fixture
def mock_config(mock_episuite_dir):
    """Create a mock configuration."""
    return EPySuiteConfig(
        es_dir=mock_episuite_dir,
        timeout=1,
        data_format="pandas"
    )