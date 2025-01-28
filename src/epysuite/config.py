# src/epysuite/config.py

"""Configuration utilities for EPYSuite."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal


@dataclass
class STPConfig:
    """Configuration for STP calculations."""
    biowin: bool = True
    halflife_hr: float = 1.0
    
    def get_config_lines(self) -> List[str]:
        """Generate configuration lines for STP."""
        if self.biowin or self.halflife_hr == 10000:
            # Use default biowin values
            base_value = 10000
            values = [base_value] * 3  # Repeats the base_value three times
        else:
            # Calculate values based on halflife_hr
            values = [self.halflife_hr * 10, self.halflife_hr, self.halflife_hr]
        
        # Prepare the configuration lines with proper formatting
        config_lines = [f"{val:.2f}\n" for val in values]
        header = " 1\n" if self.biowin else " 2\n"
        return [header] + config_lines


@dataclass
class EPySuiteConfig:
    """Main configuration for EPY Suite."""
    es_dir: Path = field(default_factory=lambda: Path("C:/EPISUITE41"))
    timeout: int = 20
    data_format: Literal["polars", "pandas"] = "polars"
    use_tabout: bool = True  # Whether to use tabout.txt instead of sumbrief.epi
    
    def __post_init__(self):
        """Convert string path to Path object if necessary."""
        if isinstance(self.es_dir, str):
            self.es_dir = Path(self.es_dir).resolve()
            
    @property
    def app_path(self) -> Path:
        """Get the path to the EPI Suite executable."""
        return self.es_dir / "epiwin1.exe"
    
    @property
    def stpwin_path(self) -> Path:
        """Get the path to the STPWIN executable."""
        return self.es_dir / "STPWIN32.exe"
    
    @property
    def input_path(self) -> Path:
        """Get the path to the input file."""
        return self.es_dir / "epi_inp.txt"
    
    @property
    def stp_path(self) -> Path:
        """Get the path to the STP configuration file."""
        return self.es_dir / "stpvalsx"
    
    @property
    def summary_path(self) -> Path:
        """Get the path to the summary file."""
        return self.es_dir / "sumbrief.epi"
    
    @property
    def tabout_path(self) -> Path:
        """Get the path to the tabout file."""
        return self.es_dir / "tabout.txt"