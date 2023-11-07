from datetime import datetime, timedelta
from decouple import config
from pathlib import Path
import os

def get_date() -> (str, str):
    '''Generate the start date and end date'''
    today = datetime.today()
    # start date for last week
    start_date = (today - timedelta(days=today.weekday()) - timedelta(days = 7)).date()
    end_date = start_date + timedelta(days=6)
    return str(start_date), str(end_date)

def get_environment_variables() -> dict:
    '''
        Return a dictionary with key as the environment vairable name and 
    '''
    return {"reddit_client_id" : config("reddit_client_id"),
            "reddit_secret":    config("reddit_client_secret"),
            "gcp_project_id" :  config("gcp_project_id")}

def get_json_path() -> str:
    '''Check if the json file exists and Return the json path'''
    json_path = Path("/opt/airflow/gcp/gcp_key.json")
    if not json_path.exists():
        raise FileNotFoundError("the json file does not exists")
    return "/opt/airflow/gcp/gcp_key.json"

def data_path_initialization(data_path : str, start_date : datetime.date, end_date : datetime.date) -> (str, str, str, str):
    """_summary_
    Initialize the data path
    Args:
        data_path (Path): the data path 
        start_date (datetime.date): _description_
        end_date (datetime.date): _description_

    Raises:
        FileNotFoundError: _description_
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError("directory file not exixists")
    storage_dir_str = f"{str(start_date)}-{str(end_date)}"
    storage_dir_path = data_path / storage_dir_str
    comments_path = storage_dir_path / "comments"
    post_path = storage_dir_path / "posts"
    user_path = storage_dir_path / "users"
    if not comments_path.exists():
        comments_path.mkdir(parents=True)
    if not post_path.exists():
        post_path.mkdir(parents=True)
    if not user_path.exists():
        user_path.mkdir(parents=True)
    return str(storage_dir_path), str(post_path), str(comments_path), str(user_path)


def parameter_generation() -> dict:
    """
    Generate the parameters and output a dictionary 
    """
    start_date, end_date = get_date()
    env_vars = get_environment_variables()
    # initialize the start date and end date
    env_vars.update(
        {"start_date": start_date, "end_date" : end_date}
    )
    # initialize the data path 
    data_path = Path("./temp/data")
    if not data_path.exists():
        data_path.mkdir(parents = True)
    data_path, post_path, comment_path, user_path = data_path_initialization(data_path, start_date, end_date)
    env_vars.update(
        {"data_path" : data_path, "post_path" : post_path, "comment_path" : comment_path, "user_path" : user_path}
    )
    return env_vars

def project_init() -> dict:
    '''initialize the datapath and project given the environment variable'''
    env_vars = parameter_generation()
    # initialize the data directory
    env_vars.update({"gcp_key_path" : get_json_path()})
    return env_vars
    
