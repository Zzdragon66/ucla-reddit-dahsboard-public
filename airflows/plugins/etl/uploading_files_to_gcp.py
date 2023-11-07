from pathlib import Path
from google.oauth2 import service_account
from google.cloud import storage

def get_credentials(gcp_key_path : str) -> Path:
    """Get the credential from the gcp_key_path"""
    credential_path = Path(gcp_key_path)
    
    if not credential_path.exists():
        print(f"credential file not found: {credential_path}")
        raise FileNotFoundError("credential file not found")
    return credential_path

def get_create_bucket(gcp_key_path : str, gcp_project_id : str, start_date : str, end_date : str) -> None:
    bucket_name = f"reddit_data_{start_date.replace('-', '_')}_{end_date.replace('-', '_')}"
    credential_path = get_credentials(gcp_key_path)
    credentials = service_account.Credentials.from_service_account_file(credential_path)
    storage_client = storage.Client(credentials=credentials, project=gcp_project_id)
    if storage_client.lookup_bucket(bucket_name) is None: 
        bucket = storage_client.create_bucket(bucket_name)
    else:
        bucket = storage_client.get_bucket(bucket_name)
    return bucket

def upload_data_to_gcp(data_path : str, gcp_key_path : str, gcp_project_id : str, start_date : str, end_date : str) -> str:
    """Upload the data to gcp"""
    bucket = get_create_bucket(gcp_key_path, gcp_project_id, start_date, end_date)
    data_path = Path(data_path) # data path is a directory containing 
    if not data_path.exists():
        raise FileNotFoundError("directory file not exists")
    for dir in data_path.iterdir():
        if not (dir.name in ["posts", "comments", "users"]):
            continue
        for file in dir.iterdir():
            blob = bucket.blob(f"{dir.name}/{file.name}")
            print(f"uploading {file.name} to {dir.name}")
            blob.upload_from_filename(str(file))
    return bucket.name


if __name__ == "__main__":
    upload_data_to_gcp(
        data_path="/Users/allenzhang/temp/data/2023-10-16-2023-10-22",
        gcp_key_path="/Users/allenzhang/gcp/gcp_key.json",
        gcp_project_id="ucla-reddit-scr",
        start_date="2023-10-16",
        end_date="2023-10-22"
    )