# tests/test_utils.py

"""Test utility functions."""

import pytest
from pathlib import Path
import polars as pl
import pandas as pd
from epysuite.utils import read_file, write_file, parse_summary, clean_outputs
from epysuite.exceptions import FileHandlingError

def test_read_file(tmp_path):
    """Test reading a file."""
    test_file = tmp_path / "test.txt"
    test_content = ["line1\n", "line2\n"]
    test_file.write_text("".join(test_content))
    
    assert read_file(test_file) == test_content

def test_read_file_not_found():
    """Test reading a non-existent file."""
    with pytest.raises(FileHandlingError):
        read_file(Path("nonexistent.txt"))

def test_write_file(tmp_path):
    """Test writing a file."""
    test_file = tmp_path / "test.txt"
    test_content = ["line1\n", "line2\n"]
    
    write_file(test_file, test_content)
    assert test_file.read_text() == "line1\nline2\n"

def test_parse_summary_polars(tmp_path):
    """Test parsing summary file to polars DataFrame."""
    test_file = tmp_path / "summary.txt"
    test_content = "Key1: 42.0\nKey2: value\nKey3: 3.14\n"
    test_file.write_text(test_content)
    
    df = parse_summary(test_file, format="polars")
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 3
    assert df.shape[1] == 2

def test_parse_summary_pandas(tmp_path):
    """Test parsing summary file to pandas DataFrame."""
    test_file = tmp_path / "summary.txt"
    test_content = "Key1: 42.0\nKey2: value\nKey3: 3.14\n"
    test_file.write_text(test_content)
    
    df = parse_summary(test_file, format="pandas")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert df.shape[1] == 2

def test_clean_outputs(tmp_path):
    """Test cleaning output files."""
    # Create test files
    (tmp_path / "file1.epi").touch()
    (tmp_path / "file2.epi").touch()
    (tmp_path / "tabout.txt").touch()
    (tmp_path / "other.txt").touch()
    
    clean_outputs(tmp_path)
    
    # Check that .epi files and tabout.txt are removed
    assert not list(tmp_path.glob("*.epi"))
    assert not (tmp_path / "tabout.txt").exists()
    # Check that other files remain
    assert (tmp_path / "other.txt").exists()