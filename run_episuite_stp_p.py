import subprocess
import pandas as pd
from pathlib import Path
import logging
import pickle
from tqdm import tqdm
from skimpy import clean_columns
import shutil
import concurrent.futures
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define paths for the EPI Suite application and working directories
ES_DIR = Path("C:/EPISUITE41").resolve()

def update_stp_configuration(biowin, halflife_hr):
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


def get_episuite_data(cas_rn="71-43-2", smiles=None, biowin=True, halflife_hr=1, return_df=True, work_dir=None):
    # Ensure a unique working directory is provided for each run
    if work_dir is None:
        raise ValueError("A working directory must be specified for each EPI Suite run to avoid file conflicts.")
    
    work_dir = Path(work_dir).resolve()
    app_path = ES_DIR / "epiwin1.exe"
    input_fname = work_dir / "epi_inp.txt"

    # Copy the default configuration files into the working directory
    shutil.copy(ES_DIR / "epi_inp.txt", input_fname)
    shutil.copy(ES_DIR / "stpvalsx", work_dir / "stpvalsx")
    
    # Read the existing input configuration file
    try:
        with open(input_fname, 'r') as file:
            input_config = file.readlines()
    except FileNotFoundError:
        logging.error(f"The input configuration file was not found: {input_fname}")
        return None

    # Modify the input configuration based on provided SMILES or CAS RN
    if smiles is None:
        # Handle CAS RN lookup for SMILES
        input_lines = ["CAS", cas_rn]
        with open(input_fname, 'w') as file:
            file.write("\n".join(input_lines))
        
        try:
            subprocess.run([str(app_path), str(input_fname)], cwd=str(work_dir), timeout=5, check=True)
        except subprocess.TimeoutExpired:
            logging.warning(f"Timeout retrieving SMILES for CAS RN: {cas_rn}")
            return None
        except subprocess.CalledProcessError as e:
            logging.error("Error during EPI Suite execution for CAS RN lookup")
            return None
        
        try:
            with open(work_dir / "cas_res.txt", 'r') as file:
                cas_res = file.readlines()
                input_config[1] = cas_res[0]
                input_config[2] = cas_res[1]
        except FileNotFoundError:
            logging.error("CAS results file not found.")
            return None
    else:
        # Set SMILES and CAS directly
        input_config[1] = f"{smiles}\n"
        input_config[2] = f"{cas_rn}\n"

    # Write the updated configuration back to the file
    with open(input_fname, 'w') as file:
        file.writelines(input_config)
    
    # Update STP configuration
    stp_config_file = work_dir / "stpvalsx"
    with open(stp_config_file, 'r') as file:
        stp_config = file.readlines()

    stp_config[0:3] = update_stp_configuration(biowin, halflife_hr)
    
    with open(stp_config_file, 'w') as file:
        file.writelines(stp_config)

    # Run the main EPI Suite application
    try:
        subprocess.run([str(app_path), str(input_fname)], cwd=str(work_dir), timeout=30, check=True)
    except subprocess.TimeoutExpired:
        logging.warning(f"Timeout retrieving data for: {cas_rn if smiles is None else smiles}")
        return None
    except subprocess.CalledProcessError as e:
        logging.error("Error during EPI Suite execution for data processing")
        return None

    # Process the output
    summary_file_path = work_dir / "sumbrief.epi"
    try:
        with open(summary_file_path, 'r') as file:
            summary_raw = [line.strip().split(":") for line in file if line.strip()]
            summary_data = {item[0]: item[1] for item in summary_raw if len(item) == 2}
    except FileNotFoundError:
        logging.error("Summary file not found.")
        return None

    # Convert to DataFrame if requested
    if return_df:
        df = pd.DataFrame([summary_data])
        return df

    return summary_data


# Process each CAS/SMILES pair with multiple halflives
def process_single_cas_smiles(cas, smiles):
    hls = [0, 1, 3, 10, 30, 100, 10000]
    # Create a unique working directory for this process
    work_dir = Path(f"./work_{cas}")
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        stp_data = pd.DataFrame()
        metadata = pd.DataFrame()

        for idx, hl in enumerate(hls):
            result = get_episuite_data(cas_rn=cas, smiles=smiles, biowin=(hl == 0), halflife_hr=hl, work_dir=work_dir)

            if result is None:
                continue  # Skip to the next loop if there was an error

            result = clean_columns(result)
            result.rename(columns={'chem': 'cas_rn'}, inplace=True)

            if idx == 0:
                metadata_cols = [col for col in result if not col.startswith('stp')]
                meta_result = result[metadata_cols]
                metadata = pd.concat([metadata, meta_result], ignore_index=True)

            stp_result = result[['cas_rn', 'smiles']].copy()
            stp_result['bio_p'] = hl * 10
            stp_result['bio_a'] = hl
            stp_result['bio_s'] = hl
            stp_result['stp_type'] = 'biowin' if hl == 0 else 'default' if hl == 10000 else 'custom'

            stp_cols = [col for col in result if col.startswith('stp') and 'percent' in col]
            result[stp_cols] = result[stp_cols].apply(pd.to_numeric, errors='coerce')

            stp_result = pd.concat([stp_result, result[stp_cols]], axis=1)
            stp_data = pd.concat([stp_data, stp_result], ignore_index=True)

    finally:
        # Clean up the working directory after processing
        shutil.rmtree(work_dir)

    return metadata, stp_data


def main():
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

    # Run the processing in parallel
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_single_cas_smiles, cas_list, smiles_list),
                            total=len(cas_list), desc="Processing EPI Suite Data"))

    # Collect results into final DataFrames
    metadata = pd.concat([result[0] for result in results if result], ignore_index=True)
    stp_data = pd.concat([result[1] for result in results if result], ignore_index=True)

    # Save the final DataFrames to pickle and CSV files
    metadata.to_pickle('output/episuite_meta.pkl')
    stp_data.to_pickle('output/episuite_stp.pkl')

    metadata.to_csv('output/episuite_meta.csv', index=False)
    stp_data.to_csv('output/episuite_stp.csv', index=False)

if __name__ == '__main__':
    main()
