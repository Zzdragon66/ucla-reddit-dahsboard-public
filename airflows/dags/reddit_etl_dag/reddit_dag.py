from datetime import datetime
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from etl.project_init import project_init
from etl.reddit_scraping import reddit_scraping
from etl.uploading_files_to_gcp import upload_data_to_gcp
from etl.files_to_bigquery import upload_file_to_big_query
from etl.report_generation import report_generation

def project_init_wrapper(ti):
    result = project_init()
    ti.xcom_push(key='project_init_result', value=result)
    print(result)

def reddit_scraping_wrapper(ti):
    project_init_result = ti.xcom_pull(task_ids='initialization', key='project_init_result')
    reddit_scraping(
        client_id=project_init_result["reddit_client_id"],
        client_secret=project_init_result["reddit_secret"],
        date_lower=project_init_result["start_date"],
        date_upper=project_init_result["end_date"],
        post_path=project_init_result["post_path"],
        comment_path=project_init_result["comment_path"],
        user_path=project_init_result["user_path"],
    )

def upload_data_to_gcp_wrapper(ti):
    project_init_result = ti.xcom_pull(task_ids='initialization', key='project_init_result')
    bucket_name = upload_data_to_gcp(
        data_path=project_init_result["data_path"],
        gcp_key_path=project_init_result["gcp_key_path"],
        gcp_project_id=project_init_result["gcp_project_id"],
        start_date=project_init_result["start_date"],
        end_date=project_init_result["end_date"]
    )
    ti.xcom_push(key='bucket_name', value=bucket_name)
    
def upload_files_to_bigquery_wrapper(ti):
    project_init_result = ti.xcom_pull(task_ids='initialization', key='project_init_result')
    dateset_id = upload_file_to_big_query(
        gcp_key_path=project_init_result["gcp_key_path"],
        gcp_project_id=project_init_result["gcp_project_id"],
        start_date=project_init_result["start_date"],
        end_date=project_init_result["end_date"],
        data_path=project_init_result["data_path"]
    )
    ti.xcom_push(key='dateset_id', value=dateset_id)
    
def report_generation_wrapper(ti):
    project_init_result = ti.xcom_pull(task_ids='initialization', key='project_init_result')
    dataset_id = ti.xcom_pull(task_ids='data_to_bigquery', key='dateset_id')
    bucket_name = ti.xcom_pull(task_ids='upload_data_to_gcp', key='bucket_name')
    report_generation(
        gcp_key_path=project_init_result["gcp_key_path"],
        project_id=project_init_result["gcp_project_id"],
        dataset_id=dataset_id,
        bucket_name=bucket_name
    )
        

with DAG(
    dag_id="reddit-data-dashboard",
    start_date=datetime(year=2023, month=11, day=6, hour=0, minute=0, second=1),
    schedule_interval="@weekly",
    tags=["reddit"]
) as dag:

    task_project_init = PythonOperator(
        task_id="initialization",
        python_callable=project_init_wrapper,
        provide_context=True  
    )

    scraping_reddit = PythonOperator(
        task_id="scraping_reddit",
        python_callable=reddit_scraping_wrapper,
        provide_context=True  
    )
    
    raw_bucket_upload = PythonOperator(
        task_id="upload_data_to_gcp",
        python_callable=upload_data_to_gcp_wrapper,
        provide_context=True 
    )
    
    
    spark_job = SparkSubmitOperator(
        task_id = "Spark_submit_job",
        application = "/opt/airflow/plugins/etl/spark_data_processing.py",
        conn_id = "spark_connection",
        verbose = True,
        executor_memory = "2G",
        application_args = [
            "--data_dir", "{{ ti.xcom_pull(task_ids='initialization',key='project_init_result')['data_path'] }}",
            "--post_dir", "{{ ti.xcom_pull(task_ids='initialization', key='project_init_result')['post_path'] }}",
            "--comment_dir", "{{ ti.xcom_pull(task_ids='initialization', key='project_init_result')['comment_path'] }}",
            "--user_dir", "{{ ti.xcom_pull(task_ids='initialization', key='project_init_result')['user_path'] }}" 
        ]
    )
    
    bigquery_upload = PythonOperator(
        task_id = "data_to_bigquery",
        python_callable=upload_files_to_bigquery_wrapper,
        provide_context=True  # Provide the context (ti) to the callable
    )
    
    report_task = PythonOperator(
        task_id = "report_generation",
        python_callable=report_generation_wrapper,
        provide_context=True  
    )
    
    task_project_init >> scraping_reddit 
    scraping_reddit >> [raw_bucket_upload, spark_job] >> bigquery_upload >> report_task 
    