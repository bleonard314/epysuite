# tests/test_runner.py

"""Test EPYSuite runner."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from epysuite.config import EPySuiteConfig
from epysuite.exceptions import ConfigurationError, ExecutionError, TimeoutError
from epysuite.runner import EPySuiteRunner


def test_runner_initialization(mock_config):
    """Test runner initialization."""
    runner = EPySuiteRunner(mock_config)
    assert runner.config == mock_config

def test_runner_invalid_installation():
    """Test runner initialization with invalid installation."""
    config = EPySuiteConfig(es_dir="/nonexistent")
    with pytest.raises(ConfigurationError):
        EPySuiteRunner(config)

@patch('subprocess.run')
def test_get_data_with_smiles(mock_run, mock_config):
    """Test getting data with provided SMILES."""
    runner = EPySuiteRunner(mock_config)
    mock_run.return_value = Mock(returncode=0)
    
    # Create mock summary file
    runner.config.summary_path.write_text("Test: 42.0\n")
    
    df = runner.get_data("123-45-6", smiles="CC")
    assert len(df) == 1
    mock_run.assert_called_once()

@patch('subprocess.run')
def test_get_data_timeout(mock_run, mock_config):
    """Test timeout handling."""
    runner = EPySuiteRunner(mock_config)
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)
    
    with pytest.raises(TimeoutError):
        runner.get_data("123-45-6", smiles="CC")

@patch('subprocess.run')
def test_get_data_execution_error(mock_run, mock_config):
    """Test execution error handling."""
    runner = EPySuiteRunner(mock_config)
    mock_run.side_effect = subprocess.CalledProcessError(1, "test")
    
    with pytest.raises(ExecutionError):
        runner.get_data("123-45-6", smiles="CC")

@patch('subprocess.run')
def test_smiles_lookup(mock_run, mock_config):
    """Test SMILES lookup."""
    runner = EPySuiteRunner(mock_config)
    mock_run.return_value = Mock(returncode=0)
    
    # Create mock cas_res.txt
    (runner.config.es_dir / "cas_res.txt").write_text("CC\n")
    
    df = runner.get_data("123-45-6")
    assert mock_run.call_count == 2  # One for SMILES lookup, one for data