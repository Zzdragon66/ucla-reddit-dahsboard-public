from google.cloud import bigquery
from google.oauth2 import service_account
from pathlib import Path

table_names = ["post_dashboard", "user_dashboard", "post_comment_dashboard", "fact_dashboard"]

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

def sql_statement_generation(output_type : str, dataset_id : str) -> str:
    '''Generate the SQL statement based on output type'''
    match output_type:
        case "user_dashboard":
            return f'''
                SELECT user.user_name, CONCAT("https://www.reddit.com/user/", user.user_name) as user_url, IFNULL(t1.n_posts, 0) as n_posts, IFNULL(t2.n_comments, 0) as n_comments, (IFNULL(n_posts, 0) + IFNULL(n_comments, 0)) as n_interactions
                FROM 
                    `{dataset_id}.user` as user
                Left join
                    (SELECT post.user_id, count(1) AS n_posts
                    FROM `{dataset_id}.post` as post
                    WHERE user_id is not null
                    GROUP BY post.user_id) as t1
                on user.user_id = t1.user_id
                Left join 
                    (SELECT comment.user_id, count(1) AS n_comments
                    FROM `{dataset_id}.comment` as comment
                    WHERE comment.user_id is not null
                    GROUP BY comment.user_id) as t2
                on user.user_id = t2.user_id
                order by n_interactions DESC, n_posts DESC, n_comments DESC
            '''
        case "post_comment_dashboard":
            return f'''
                SELECT 
                    t1.created_date, t1.n_posts, t2.n_comments
                FROM
                    (select post.created_utc as created_date, count(1) n_posts
                    from `{dataset_id}.post` as post
                    group by post.created_utc) as t1
                LEFT JOIN 
                    (select comment.created as created_date, count(1) as n_comments
                    from `{dataset_id}.comment` as comment
                    group by comment.created) as t2
                on t1.created_date = t2.created_date
                ORDER BY t1.created_date
            '''
        case "fact_dashboard":
            return f""" 
                select "Number of posts" as fact, count(distinct post.id) as N
                from `{dataset_id}.post` as post
                UNION ALL
                select "Number of comments" as fact, count(distinct comment.id) as N
                from `{dataset_id}.comment` as comment
                UNION ALL 
                select "Number of active users" as fact, count(1) as N
                from `{dataset_id}.user` as user
                where user.user_id is not null
            """
        case "post_dashboard":
            return f"""
            SELECT distinct title, url, score, num_comments as comments, upvote_ratio 
            FROM `{dataset_id}.post` as post
            ORDER BY post.score DESC, upvote_ratio DESC
            LIMIT 100
            """
        case _:
            raise KeyError("the table type is not found")
    return None

#TODO(Change the parameter)
def table_generation_to_cloud(client, dataset_id: str, bucket_name : str, table_name:str):
    '''
    Generate the tables for the cloud dashboard
    - client: the bigquery client
    - dataset_id: the dataset_id
    - bucket_name: the bucket name for the orginal bucket storage 
    - table_name: the table name for the dashboard
    '''
    sql_statement = sql_statement_generation(table_name,dataset_id)
    dataset_ref = client.dataset(dataset_id)
    bigquery_table = dataset_ref.table(table_name)
    print(dataset_ref)
    print(bigquery_table)
    # Use big query to transform the table 
    job_config = bigquery.QueryJobConfig()
    job_config.destination = bigquery_table
    query_job = client.query(sql_statement, job_config=job_config)
    query_job.result()
    # upload the table to the original bucket 
    original_bucket_uri = f"gs://{bucket_name}/report/"
    original_bucket_uri = original_bucket_uri + f"{table_name}.csv"
    # Upload to the cloud storage for the dashboard
    report_uri= f"gs://ucla-reddit-data/latest_report_folder/"
    report_uri = report_uri + f"{table_name}.csv"
    # Extract the table to the report folder
    extract_job = client.extract_table(bigquery_table, report_uri, location="US")
    extract_job.result()
    # Extract the table to the original bucket
    extract_job = client.extract_table(bigquery_table, original_bucket_uri, location="US")
    extract_job.result()

def report_generation(gcp_key_path : str, project_id:str, dataset_id:str, bucket_name:str):
    '''Generate the report for the dashboard'''
    client = create_client(gcp_key_path, project_id)

    for table_name in table_names:
        table_generation_to_cloud(client, dataset_id, bucket_name, table_name)

def main():
    '''Do nothing when called directly'''
    return None

if __name__ == "__main__":
    main()
