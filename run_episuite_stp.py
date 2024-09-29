import subprocess
import pandas as pd
from pathlib import Path
import logging
import pickle
from tqdm import tqdm
from skimpy import clean_columns

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


def get_episuite_data(cas_rn="71-43-2", smiles=None, biowin=True, halflife_hr=1, return_df=True, es_dir="C:\\EPISUITE41"):
    es_dir = Path(es_dir).resolve()
    app_path = es_dir / "epiwin1.exe"
    input_fname = "epi_inp.txt"
    
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
        with open(es_dir / input_fname, 'w') as file:
            file.write("\n".join(input_lines))
        
        try:
            subprocess.run([str(app_path), str(input_fname)], cwd=str(es_dir),
                           timeout=3, check=True)
        except subprocess.TimeoutExpired:
            logging.warning(f"Timeout retrieving SMILES for CAS RN: {cas_rn}")
            return None
        except subprocess.CalledProcessError as e:
            logging.error("Error during EPI Suite execution for CAS RN lookup")
            return None
        
        # Assume 'cas_res.txt' contains the needed SMILES and additional data
        try:
            with open(es_dir / "cas_res.txt", 'r') as file:
                cas_res = file.readlines()
                input_config[1] = cas_res[0]
                input_config[2] = cas_res[1]
        except FileNotFoundError:
            logging.error("CAS results file not found.")
            return None
    elif cas_rn is None:
        # Set SMILES directly
        input_config[1] = f"{smiles}\n"
        input_config[2] = "(null)\n"
    else:
        # Set SMILES and CAS directly
        input_config[1] = f"{smiles}\n"
        input_config[2] = f"{cas_rn}\n"

    # Write the updated configuration back to the file
    with open(es_dir / input_fname, 'w') as file:
        file.writelines(input_config)
    
    # Read default STP configuration file ('stpvalsx')
    with open("stpvalsx", 'r') as file:
        stp_config = file.readlines()

    # Handle STP configuration changes
    stp_config[0:3] = update_stp_configuration(biowin, halflife_hr)
    
    with open(es_dir / "stpvalsx", 'w') as file:
        file.writelines(stp_config)

    # Run the main EPI Suite application
    try:
        subprocess.run([str(app_path), str(input_fname)], cwd=str(es_dir), timeout=10, check=True)
    except subprocess.TimeoutExpired:
        logging.warning(f"Timeout retrieving data for: {cas_rn if smiles is None else smiles}")
        return None
    except subprocess.CalledProcessError as e:
        logging.error("Error during EPI Suite execution for data processing")
        return None

    # Process the output
    summary_file_path = es_dir / "sumbrief.epi"
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

# Run EPI Suite for multiple halflives
hls = [0, 1, 3, 10, 30, 100, 10000]

# Read in list of SMILES and CAS RNs from a file (smile_cas.pkl)
df = pd.read_pickle('output/smile_cas.pkl')

cas_list = df['CASNO'].tolist()
smiles_list = df['SMILES'].tolist()

# Run on multiple records with progress bar
metadata = pd.DataFrame()
stp_data = pd.DataFrame()
for cas, smiles in tqdm(zip(cas_list, smiles_list), total=len(cas_list), desc="Processing EPI Suite Data"):
    for idx, hl in enumerate(hls):
        if hl == 0:
            result = get_episuite_data(cas_rn=cas, smiles=smiles, biowin=True)
        else:
            result = get_episuite_data(cas_rn=cas, smiles=smiles, biowin=False, halflife_hr=hl)
        
        # Clean column names
        result = clean_columns(result)
        
        # Rename 'chem' to 'cas_rn'
        result.rename(columns={'chem': 'cas_rn'}, inplace=True)
        
        # For the first index, extract all of the metadata
        if idx == 0:
            # Extract columns that do not start with "STP"
            metadata_cols = [col for col in result if not col.startswith('stp')]
            meta_result = result[metadata_cols]
            metadata = pd.concat([metadata, meta_result], ignore_index=True)
            
        # Extract just the 'cas_rn' and 'smiles' columns
        stp_result = result[['cas_rn', 'smiles']].copy()
        
        # Add value for bio_a, bio_b, and bio_c as halflife
        stp_result['bio_p'] = hl*10 # Bio P: the biodegradation half-life (in hours) in the primary clarifier of an STP.
        stp_result['bio_a'] = hl # Bio A: the biodegradation half-life (in hours) in the aeration vessel of an STP.
        stp_result['bio_s'] = hl # Bio S: the biodegradation half-life (in hours) in the final settling tank of an STP.
        
        # If halflife is 0, set `stp_type` to 'biowin', if halflife is 10000, then set `stp_type` to `default` otherwise `custom`
        stp_result['stp_type'] = 'biowin' if hl == 0 else 'default' if hl == 10000 else 'custom'
        
        # Extract columns that start with "STP" and contain the word "percent"
        stp_cols = [col for col in result if col.startswith('stp') and 'percent' in col]
        
        # Convert the columns to numeric
        result[stp_cols] = result[stp_cols].apply(pd.to_numeric, errors='coerce')
        
        # Add the STP columns to the DataFrame
        stp_result = pd.concat([stp_result, result[stp_cols]], axis=1)
        
        # Append the result to the DataFrame
        stp_data = pd.concat([stp_data, stp_result], ignore_index=True)

logging.info("Finished processing EPI Suite data.")

# Save the final DataFrames to pickle files
metadata.to_pickle('output/episuite_meta.pkl')
stp_data.to_pickle('output/episuite_stp.pkl')

# Save the final DataFrames to CSV files
metadata.to_csv('output/episuite_meta.csv', index=False)
stp_data.to_csv('output/episuite_stp.csv', index=False)

# Example usage
# data = get_episuite_data(cas_rn="000000-00-2", smiles="N1C(C)=C(N(=O)=O)N=C1")
# print(data)