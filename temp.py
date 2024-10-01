import subprocess
import pandas as pd
import polars as pl
from pathlib import Path
import logging
import pickle
from tqdm import tqdm
from skimpy import clean_columns

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define paths for the EPI Suite application and working directories
ES_DIR = Path("C:/EPISUITE41").resolve()

def update_stp_configuration(biowin, halflife_hr=None):
    """
    Updates the STP configuration based on the biowin flag and halflife hour.
    
    :param biowin: A boolean indicating if the default biowin values should be used.
    :param halflife_hr: The activated sludge half-life in hours.
    :return: A list of configuration strings.
    """
    if biowin or halflife_hr == 10000:
        # Use default biowin values
        base_value = 10000
        values = [base_value] * 3  # Repeats the base_value three times
    else:
        # Calculate values based on halflife_hr
        values = [halflife_hr * 10, halflife_hr, halflife_hr]

    # Prepare the configuration lines with proper formatting
    config_lines = [f"{val:.2f}\n" for val in values]
    header = " 2\n" if not biowin else " 1\n"
    return [header] + config_lines


def get_episuite_data(cas_rn, smiles):
    es_dir = Path(ES_DIR).resolve()
    app_path = es_dir / "epiwin1.exe"
    input_fname = "epi_inp.txt"
    
    # Read the existing input configuration file
    with open(input_fname, 'r') as file:
        input_config = file.readlines()

    # Set SMILES and CAS directly
    input_config[1] = f"{smiles}\n"
    input_config[2] = f"{cas_rn}\n"

    # Write the updated configuration back to the file
    with open(es_dir / input_fname, 'w') as file:
        file.writelines(input_config)
    
    # Read default STP configuration file ('stpvalsx')
    with open("stpvalsx", 'r') as file:
        stp_config = file.readlines()

    # Update STP configuration for biowin
    stp_config[0:3] = update_stp_configuration(biowin=True)
    
    with open(es_dir / "stpvalsx", 'w') as file:
        file.writelines(stp_config)

    # Run the main EPI Suite application for biowin
    try:
        subprocess.run([str(app_path), str(input_fname)], cwd=str(es_dir), timeout=10, check=True)
    except subprocess.TimeoutExpired:
        logging.warning(f"Timeout retrieving data for: {cas_rn if smiles is None else smiles}")
        return None
    except subprocess.CalledProcessError as e:
        logging.error("Error during EPI Suite execution for data processing")
        return None
    
    # Define path for the tabout file
    tabout_file_path = es_dir / "tabout.txt"
    
    # Check if the tabout file exists
    if not tabout_file_path.exists():
        logging.error(f"File not found: {tabout_file_path}")
        return None
    
    # Read the TSV file using Polars
    tabout_data_df = pl.read_csv(tabout_file_path, separator='\t', truncate_ragged_lines=True)
    
    # Define path for the summary file
    summary_file_path = es_dir / "sumbrief.epi"
    
    # Open the file and count lines one by one
    line_count = 0
    with open(summary_file_path, 'r') as file:
        for _ in file:
            line_count += 1
    
    # Run EPI Suite for multiple halflives
    hls = [1, 3, 10, 30, 100, 10000]
    
    # Run the rest of the halflives
    for hl in hls:
        stp_config[0:3] = update_stp_configuration(biowin=False, halflife_hr=hl)
        with open(es_dir / "stpvalsx", 'w') as file:
            file.writelines(stp_config)
        
        try:
            subprocess.run([es_dir / "STPWIN32.exe"], cwd=str(es_dir), timeout=10, check=True)
        except subprocess.TimeoutExpired:
            logging.warning(f"Timeout retrieving data for: {cas_rn if smiles is None else smiles}")
            return None
        except subprocess.CalledProcessError as e:
            logging.error("Error during EPI Suite execution for data processing")
            return None

    # Read the summary file
    with open(summary_file_path, 'r') as file:
        lines = file.readlines()
    
    # Initialize a list to hold dictionaries for each half-life
    summary_data_list = []

    # Process the output
    for idx, i in enumerate(range(line_count, len(lines), 8)):  # Process in groups of 8 lines
        # Create a dictionary for the current half-life
        summary_data = {}
        
        # Collect the selected lines in groups of 4 (as per your logic)
        selected_lines = lines[i:i+4]
        for line in selected_lines:
            key, value = line.strip().split(":")
            # Remove "STP Total " from beginning of key name and " (percent)" from end of key name
            key = key.replace("STP Total ", "").replace(" (percent)", "")
            summary_data[key] = value
        
        # Add the dictionary to the list, each dictionary corresponds to a half-life
        summary_data_list.append({f"hl-{hls[idx]}": summary_data})
    
    return tabout_data_df, summary_data_list

def main():
    tabout_path = Path(ES_DIR).resolve() / "tabout.txt"
    
    # Check if the tabout file exists
    if not tabout_path.exists():
        logging.error(f"File not found: {tabout_path}")
        return
    else:
        # Delete the tabout file
        tabout_path.unlink()
    
    # Define file name for smile-cas data
    smile_cas_fname = "smile_cas.csv"

    # Check if the file exists
    if not Path(smile_cas_fname).exists():
        logging.error(f"File not found: {smile_cas_fname}")
        return

    # Read in list of SMILES and CAS RNs from a file
    df = pd.read_csv(smile_cas_fname)
    
    # Log number of records read
    logging.info(f"Read {len(df)} records from {smile_cas_fname}.")
    
    # Define file name for CAS RNs to filter (if available)
    cas_rns_fname = "cas_rns.txt"

    # Check if the file exists
    if Path(cas_rns_fname).exists():
        # Read in line separated list of CAS RNs from a file (without the line breaks) (cas_rns.txt)
        with open(cas_rns_fname, 'r') as file:
            cas_rns = file.read().splitlines()
        
        # Display logging message
        logging.info(f"List of CAS RNs to filter found: {cas_rns_fname}; {len(cas_rns)} records.")

        # Pad the CAS RNs with leading zeros to ensure they are 11 characters long
        cas_rns = [cas.rjust(11, '0') for cas in cas_rns]

        # Filter the data to only include the CAS RNs in the list and drop dups
        df = df[df['CASNO'].isin(cas_rns)]
        df = df.drop_duplicates()

    # Log the number of records to process
    logging.info(f"Processing {len(df)} records.")

    cas_list = df['CASNO'].tolist()
    smiles_list = df['SMILES'].tolist()

    # Run on multiple records with progress bar
    meta_list = []
    stp_list = []
    for cas, smiles in tqdm(zip(cas_list, smiles_list), total=len(cas_list), desc="Processing EPI Suite Data"):
        meta, stp = get_episuite_data(cas_rn=cas, smiles=smiles)
        meta_list.append(meta)
        stp_list.append(stp)

    logging.info("Finished processing EPI Suite data.")

    # Save the final DataFrames to pickle files
    # metadata.to_pickle('output/episuite_meta.pkl')
    # stp_data.to_pickle('output/episuite_stp.pkl')

    # # Save the final DataFrames to CSV files
    # metadata.to_csv('output/episuite_meta.csv', index=False)
    # stp_data.to_csv('output/episuite_stp.csv', index=False)

    # Example usage
    # data = get_episuite_data(cas_rn="000000-00-2", smiles="N1C(C)=C(N(=O)=O)N=C1")
    # print(data)

if __name__ == "__main__":
    main()