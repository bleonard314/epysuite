# EPySuite

A Python interface for EPI Suite™, providing programmatic access to environmental fate and transport predictions. The included Python modules currently focus on providing an API to quickly retrieve model results from STPWin in order to facilitate the batch processing of chemical Sewage Treatment Plant (STP) model results with an emphasis on the default BIOWIN model.

## Installation

```bash
pip install git+https://github.com/bleonard314/epysuite.git
```

## Requirements

- Python 3.8 or later
- EPI Suite™ 4.1 (installed separately)
- pandas >= 1.5.0
- polars >= 0.19.0

## Quick Start

```python
from epysuite import EPySuiteRunner, STPConfig

# Initialize the runner with default configuration
runner = EPySuiteRunner()

# Get data for benzene using CAS RN
results = runner.get_data(
    cas_rn="71-43-2",
    smiles="c1ccccc1",  # Optional: provide SMILES directly
)

# Get data with custom STP configuration
custom_config = STPConfig(biowin=False, halflife_hr=24.0)
results = runner.get_data(
    cas_rn="71-43-2",
    stp_config=custom_config
)
```

## Features

- Simple, Pythonic interface to EPI Suite™
- Support for both pandas and polars DataFrames
- Automatic SMILES lookup from CAS RN
- Customizable STP calculations
- Comprehensive error handling

## Configuration Options

```python
from epysuite import EPySuiteConfig

# Configure data format and EPI Suite location
config = EPySuiteConfig(
    es_dir="C:/EPISUITE41",        # Custom installation directory
    data_format="pandas",          # Use pandas instead of polars
    use_tabout=True,              # Use detailed tabout.txt output
    timeout=30                     # Custom timeout in seconds
)
```

## Data Output

The package provides two output formats for STP results:

- Detailed format (tabout.txt) - **DEFAULT**
- Summary format (sumbrief.epi)

## Error Handling

EPySuite provides specific error types for common issues:

- `ConfigurationError`: EPI Suite installation or configuration issues
- `ExecutionError`: Problems running EPI Suite calculations
- `TimeoutError`: Calculation timeout issues
- `FileHandlingError`: Input/output file handling problems

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License. See LICENSE file for details.

## Disclaimer

This package is not affiliated with or endorsed by the US EPA or the developers of EPI Suite™. EPI Suite™ is a trademark of the US EPA.

## Notes

- EPI Suite™ must be installed separately
- Currently focuses on STPWin functionality
- Windows-only support (due to EPI Suite™ requirements)