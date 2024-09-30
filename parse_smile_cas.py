import re
import pandas as pd

def parse_db_file(file_path, encoding='iso-8859-1'):
    records = []
    with open(file_path, 'rb') as file:
        # Read the entire file content
        content = file.read()

    # Removing the header by locating the first record starting point
    start_index = content.find(b'\x00B') + 5
    content = content[start_index:]

    # Split records using the pattern that identifies end of one record and start of another
    record_pattern = re.compile(rb'[\x00].[\x00]')
    records_raw = record_pattern.split(content)

    # Process each record
    for idx, entry in enumerate(records_raw):
        # Split the fields based on null byte and remove the first field which is empty
        fields = entry.split(b'\x00')
        
        if len(fields) == 3: # Ensure all fields are present
            casno, chemname, smiles = fields
            record = {
                'CASNO': casno.decode(encoding),
                'CHEMNAME': chemname.decode(encoding),
                'SMILES': smiles.decode(encoding)
            }
            records.append(record)

    return records

def main():
    # Path to your .DB file
    file_path = 'C:\\EPISUITE41\\SMILECAS.DB'
    parsed_data = parse_db_file(file_path)

    # Create a DataFrame from the parsed data
    df = pd.DataFrame(parsed_data)

    # Write the DataFrame to a csv, an Excel, and a pickle file
    df.to_csv('smile_cas.csv', index=False)
    # df.to_excel('smile_cas.xlsx', index=False)
    # df.to_pickle('smile_cas.pkl')

if __name__ == "__main__":
    main()