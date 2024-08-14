import os
import uuid
import pandas as pd
import azure.cosmos.exceptions as exceptions
import azure.cosmos.cosmos_client as cosmos_client
from azure.cosmos.partition_key import PartitionKey
from decouple import config

# Azure Cosmos DB connection details
COSMOS_ENDPOINT = config("AZURE_COSMOS_ENDPOINT")
COSMOS_KEY = config("AZURE_COSMOS_KEY")
DATABASE_NAME = config("AZURE_COSMOS_DATABASE_NAME")
CONTAINER_NAME = config("AZURE_COSMOS_CONTAINER_NAME")
CWD = config("CWD")
OUTPUT_CSV_FOLDER = config("OUTPUT_CSV_FOLDER")
OUTPUT_CSV_NAME = config("OUTPUT_CSV_NAME")
CSV_FILE_PATH = f"{OUTPUT_CSV_FOLDER}/{OUTPUT_CSV_NAME}"
IGNORE_HEADERS = ["HASH_ID", "GET", "COSMOS_DB", "SELECTED_THERMAL_IMAGE_FILE"]

def upload_data_to_cosmos():
    # Initialize Cosmos Client
    client = cosmos_client.CosmosClient(COSMOS_ENDPOINT, {'masterKey': COSMOS_KEY})

    # Setup database
    try:
        db = client.create_database(id=DATABASE_NAME)
        print(f'Database with id \'{DATABASE_NAME}\' created')

    except exceptions.CosmosResourceExistsError:
        db = client.get_database_client(DATABASE_NAME)
        print(f'Database with id \'{DATABASE_NAME}\' was found')
    
    # Setup container for this sample
    try:
        container = db.create_container(id=CONTAINER_NAME, partition_key=PartitionKey(path='/partitionKey'))
        print(f'Container with id \'{CONTAINER_NAME}\' created')

    except exceptions.CosmosResourceExistsError:
        container = db.get_container_client(CONTAINER_NAME)
        print(f'Container with id \'{CONTAINER_NAME}\' was found')

    # Read CSV file
    df = pd.read_csv(CSV_FILE_PATH)
    
    # Upload data to Cosmos DB
    for index, row in df.iterrows():
        # Check if the row should be uploaded (COSMOS_DB column is 'N' and inferencing is done)
        if row['COSMOS_DB'] == 'N' and pd.notna(row['SELECTED_THERMAL_IMAGE_FILE']) and row['SELECTED_THERMAL_IMAGE_FILE'] != '':
            # Create a dictionary for the row
            data = row.to_dict()
            data = {k: ('' if pd.isna(v) else v) for k, v in data.items()}
            data['id'] = data.get("HASH_ID")  # Assign a unique ID for each document
            data['partitionKey'] = 'URL'

            # Remove ignored headers
            data = {k: v for k, v in data.items() if k not in IGNORE_HEADERS}
            
            try:
                container.create_item(body=data)
                # Set COSMOS_DB column to 'Y' for the current row
                df.at[index, 'COSMOS_DB'] = 'Y'
            except exceptions.CosmosHttpResponseError as e:
                print(f"An error occurred while inserting the item: {e.message}")

    # Save the updated DataFrame back to the CSV file
    df.sort_values(by='PUBLISHED_DATE', ascending=False).to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
    print(f"Data from {CSV_FILE_PATH} uploaded to Cosmos DB in {DATABASE_NAME}/{CONTAINER_NAME} and updated in CSV.")

if __name__ == "__main__":
    # Get the current working directory
    current_dir = os.getcwd()

    # Extract the actual directory name from the current path
    current_dir_name = os.path.basename(current_dir)

    # Check if the current directory name matches the expected name
    if current_dir_name != CWD:
        print(f"Incorrect working directory. Please cd into {CWD}")
    else:
        upload_data_to_cosmos()
