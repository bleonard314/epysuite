# src/epysuite/utils.py

"""Utility functions for EPYSuite."""

from pathlib import Path
from typing import List, Union

import pandas as pd
import polars as pl

from .exceptions import FileHandlingError


def read_file(path: Path) -> List[str]:
    """Read a file and return its contents as a list of lines."""
    try:
        with open(path, 'r') as file:
            return file.readlines()
    except FileNotFoundError as err:
        raise FileHandlingError(f"File not found: {path}") from err
    except Exception as err:
        raise FileHandlingError(f"Error reading file: {path}") from err

def write_file(path: Path, content: List[str], lookup: bool = False) -> None:
    """Write content to a file."""
    try:
        with open(path, 'w') as file:
            if lookup:
                file.write("\n".join(content))
            else:
                file.writelines(content)
    except Exception as err:
        raise FileHandlingError(f"Error writing file: {path}") from err

def parse_tabout(path: Path, format: str = "polars") -> Union[pl.DataFrame, pd.DataFrame]:
    """Parse EPI Suite tabout file into a DataFrame, removing columns with all missing values.
    
    Args:
        path: Path to the tabout file
        format: Output format ("polars" or "pandas")
        
    Returns:
        DataFrame containing EPI Suite results with empty columns removed and proper types
        
    Raises:
        FileHandlingError: If the file cannot be read or parsed
    """
    try:
        if not path.exists():
            raise FileNotFoundError(f"Tabout file not found: {path}")
        
        if format == "polars":
            # Read with Polars as strings initially
            df = pl.read_csv(
                path,
                separator='\t',
                truncate_ragged_lines=True,
                infer_schema_length=0
            )
            
            # Get columns that are not entirely null
            valid_cols = [
                col for col in df.columns 
                if df.select(pl.col(col)).null_count().item() < len(df)
            ]
            
            # Function to convert to float if possible
            def try_float(s: str) -> Union[float, str]:
                s = s.strip() if isinstance(s, str) else s
                try:
                    return float(s) if s is not None else None
                except (ValueError, TypeError):
                    return s
            
            # Process each valid column
            exprs = []
            for col in valid_cols:
                # First get a sample of non-null values from the column
                sample = (
                    df.select(pl.col(col))
                    .filter(pl.col(col).is_not_null())
                    .limit(5)
                    .to_series()
                )
                
                # Try converting sample values to determine the return type
                sample_converted = [try_float(val) for val in sample if val is not None]
                is_numeric = all(isinstance(x, (int, float)) for x in sample_converted)
                
                expr = (
                    pl.col(col)
                    .cast(pl.String)
                    .str.strip()
                    .map_elements(
                        try_float,
                        return_dtype=pl.Float64 if is_numeric else pl.String
                    )
                )
                exprs.append(expr.alias(col))
            
            # Apply transformations
            df = df.select(exprs)
            
        else:
            # Read with Pandas (pandas code remains the same)
            df = pd.read_csv(
                path,
                sep='\t',
                on_bad_lines='skip',
                dtype=str  # Read all as strings initially
            )
            
            # Drop columns where all values are NA
            df = df.dropna(axis=1, how='all')
            
            # Function to convert series to appropriate type
            def convert_series(series: pd.Series) -> pd.Series:
                # Strip whitespace if string
                series = series.str.strip() if series.dtype == 'O' else series
                
                # Try converting to float
                try:
                    return pd.to_numeric(series, errors='coerce').fillna(series)
                except (ValueError, TypeError):
                    return series
            
            # Apply conversion to each column
            df = df.apply(convert_series)
            
        return df
        
    except FileNotFoundError as err:
        raise FileHandlingError(f"Tabout file not found: {path}") from err
    except Exception as err:
        raise FileHandlingError(f"Error parsing tabout file: {path}") from err

def parse_summary(path: Path, format: str = "polars") -> Union[pl.DataFrame, pd.DataFrame]:
    """Parse EPI Suite summary file into a wide-format DataFrame.
    
    Args:
        path: Path to the summary file
        format: Output format ("polars" or "pandas")
        
    Returns:
        DataFrame containing EPI Suite results with one column per parameter
        
    Raises:
        FileHandlingError: If the file cannot be read or parsed
    """
    try:
        with open(path, 'r') as file:
            lines = [line.strip() for line in file if line.strip()]
        
        # Create a dictionary for the single row
        data = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                # Try to convert to float if possible
                try:
                    value = float(value.strip())
                except ValueError:
                    value = value.strip()
                data[key] = value
        
        if format == "polars":
            return pl.DataFrame([data])
        return pd.DataFrame([data])
    
    except FileNotFoundError as err:
        raise FileHandlingError(f"Summary file not found: {path}") from err
    except Exception as err:
        raise FileHandlingError(f"Error parsing summary file: {path}") from err

def clean_outputs(output_dir: Path) -> None:
    """Clean up output files from previous runs."""
    try:
        for pattern in ["*.epi", "tabout.txt"]:
            for file in output_dir.glob(pattern):
                file.unlink()
    except Exception as err:
        raise FileHandlingError(f"Error cleaning output files in {output_dir}") from err