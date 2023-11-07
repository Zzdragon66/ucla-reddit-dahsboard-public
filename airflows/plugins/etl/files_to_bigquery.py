import os
import pandas as pd 
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account

def get_credentials(gcp_key_path : str) -> Path:
    """Get the credential from the gcp_key_path"""
    credential_path = Path(gcp_key_path)
    
    if not credential_path.exists():
        print(f"credential file not found: {credential_path}")
        raise FileNotFoundError("credential file not found")
    return credential_path

def create_client(gcp_key_path:str, gcp_project_id:str):
    """create the client"""
    credential_path = get_credentials(gcp_key_path)
    credentials = service_account.Credentials.from_service_account_file(credential_path)
    client = bigquery.Client(credentials=credentials, project=gcp_project_id)
    return client

def upload_files_big_query(client, dataset_id:str, data_path:str):
    '''upload the files into big query'''
    tables_dir = Path(data_path) / "combine_all"
    comment_dir = tables_dir / "comment"
    post_dir = tables_dir / "post"
    user_dir = tables_dir / "user"
    # start uploading the files
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        autodetect=True,
    )
    
    for comment_file in os.listdir(comment_dir):
        if comment_file.endswith(".parquet"):
            upload_file_path = (Path(comment_dir / comment_file))
            table_id = f"{dataset_id}.comment"
            with open(upload_file_path, "rb") as source_file:
                job = client.load_table_from_file(source_file, table_id, job_config=job_config)
            job.result()  # Waits for table load to complete.
            table = client.get_table(table_id)  # Make an API request.
            print(
                "Loaded {} rows and {} columns to {}".format(
                    table.num_rows, len(table.schema), table_id
                )
            )
            break
    for post_file in os.listdir(post_dir):
        if post_file.endswith(".parquet"):
            upload_file_path = (Path(post_dir / post_file))
            table_id = f"{dataset_id}.post"
            with open(upload_file_path, "rb") as source_file:
                job = client.load_table_from_file(source_file, table_id, job_config=job_config)
            job.result()
            table = client.get_table(table_id)  # Make an API request.
            print(
                "Loaded {} rows and {} columns to {}".format(
                    table.num_rows, len(table.schema), table_id
                )
            )
            break 
    for user_file in os.listdir(user_dir):
        if user_file.endswith(".parquet"):
            upload_file_path = (Path(user_dir / user_file))
            table_id = f"{dataset_id}.user"
            with open(upload_file_path, "rb") as source_file:
                job = client.load_table_from_file(source_file, table_id, job_config=job_config)
            job.result()
            table = client.get_table(table_id)
            print(
                "Loaded {} rows and {} columns to {}".format(
                    table.num_rows, len(table.schema), table_id
                )
            )
            break
    return None


def create_data_set(client, gcp_project_id:str, start_date:str, end_date:str) -> str:
    """Create the dataset if the dataset not exists, return the datasetname"""
    start_date=pd.to_datetime(start_date).date()
    end_date=pd.to_datetime(end_date).date()
    data_set_name = f'''ucla_reddit_data_{str(start_date).replace("-", "_")}_{str(end_date).replace("-", "_")}'''
    dataset_id = f"""{gcp_project_id}.{data_set_name}"""
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    try:
        dataset = client.get_dataset(dataset)  # Make an API request.
    except Exception as e:
        dataset = client.create_dataset(dataset, timeout=30)  # Make an API request.
    print("Created dataset {}.{}".format(client.project, dataset.dataset_id))
    return data_set_name

def upload_file_to_big_query(gcp_key_path:str, gcp_project_id:str, start_date:str, end_date:str, data_path:str):
    """upload the files to big query"""
    client = create_client(gcp_key_path, gcp_project_id)
    dataset_id = create_data_set(client, gcp_project_id, start_date, end_date)
    upload_files_big_query(client, dataset_id, data_path)
    return dataset_id 

def main():
    '''Do nothing when called directly'''
    return None

if __name__ == "__main__":
    main()