# src/epysuite/runner.py

"""Main module for running EPI Suite calculations."""

import importlib.resources
import subprocess
from typing import Optional, Union

import pandas as pd
import polars as pl

from . import templates
from .config import EPySuiteConfig, STPConfig
from .exceptions import ConfigurationError, ExecutionError, TimeoutError
from .utils import clean_outputs, parse_summary, parse_tabout, read_file, write_file


class EPySuiteRunner:
    """Main class for running EPI Suite calculations."""
    
    def __init__(self, config: Optional[EPySuiteConfig] = None):
        """Initialize the runner with configuration."""
        self.config = config or EPySuiteConfig()
        self._validate_installation()
        self._load_templates()
    
    def _validate_installation(self) -> None:
        """Validate EPI Suite installation."""
        if not self.config.app_path.exists():
            raise ConfigurationError(
                f"EPI Suite executable not found at {self.config.app_path}"
            )
    
    def _load_templates(self) -> None:
        """Load the EPI Suite template files."""
        try:
            with importlib.resources.path(templates, "epi_inp.txt") as template_path:
                self.input_template = read_file(template_path)
            with importlib.resources.path(templates, "stpvalsx") as template_path:
                self.stp_template = read_file(template_path)
        except Exception as err:
            raise ConfigurationError("Failed to load EPI Suite templates") from err
    
    def get_data(
        self,
        cas_rn: str,
        smiles: Optional[str] = None,
        stp_config: Optional[STPConfig] = None
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """
        Get EPI Suite data for a compound.
        
        Args:
            cas_rn: CAS Registry Number
            smiles: SMILES notation (optional)
            stp_config: STP configuration (optional)
            
        Returns:
            DataFrame containing EPI Suite results
        """
        stp_config = stp_config or STPConfig()
        
        # Clean previous output files
        clean_outputs(self.config.es_dir)
        
        # Handle SMILES lookup if needed
        if smiles is None:
            smiles = self._lookup_smiles(cas_rn)
        
        # Update input configuration
        self._update_input_config(cas_rn, smiles)
        self._update_stp_config(stp_config)
        
        # Run EPI Suite
        try:
            self._run_episuite()
        except subprocess.TimeoutExpired as err:
            raise TimeoutError(f"Execution timed out for CAS RN: {cas_rn}") from err
        except subprocess.CalledProcessError as err:
            raise ExecutionError(f"Execution failed for CAS RN: {cas_rn}") from err
        
        # Parse and return results based on configuration
        if self.config.use_tabout:
            return parse_tabout(
                self.config.tabout_path,
                format=self.config.data_format
            )
        else:
            return parse_summary(
                self.config.summary_path,
                format=self.config.data_format
            )
    
    def _update_stp_config(self, stp_config: STPConfig) -> None:
        """Update STP configuration."""
        config_lines = stp_config.get_config_lines()
        write_file(self.config.stp_path, config_lines)
    
    def _lookup_smiles(self, cas_rn: str) -> str:
        """Look up SMILES notation for a CAS RN."""
        input_lines = ["CAS", cas_rn]
        write_file(self.config.input_path, input_lines, lookup=True)
        
        try:
            subprocess.run(
                [str(self.config.app_path), str(self.config.input_path.name)],
                cwd=str(self.config.es_dir),
                timeout=self.config.timeout,
                check=True
            )
            
            cas_results = read_file(self.config.es_dir / "cas_res.txt")
            return cas_results[0].strip()
            
        except subprocess.TimeoutExpired as err:
            raise TimeoutError(f"SMILES lookup timed out for CAS RN: {cas_rn}") from err
        except subprocess.CalledProcessError as err:
            raise ExecutionError(f"SMILES lookup failed for CAS RN: {cas_rn}") from err
    
    def _update_input_config(self, cas_rn: str, smiles: str) -> None:
        """Update input configuration."""
        # Start with the template content
        config = self.input_template.copy()
        config[1] = f"{smiles}\n"
        config[2] = f"{cas_rn}\n"
        write_file(self.config.input_path, config)
    
    def _run_episuite(self) -> None:
        """Run EPI Suite with current configuration."""
        subprocess.run(
            [str(self.config.app_path), str(self.config.input_path.name)],
            cwd=str(self.config.es_dir),
            timeout=self.config.timeout,
            check=True
        )