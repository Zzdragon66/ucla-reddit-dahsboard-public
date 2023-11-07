from pyspark.sql import SparkSession
import os 
import pandas as pd 
import numpy as np
from pathlib import Path
import argparse

def initialize_spark():
    '''initialize the pyspark'''
    spark = SparkSession.builder. \
        appName("Local development"). \
        getOrCreate()
    return spark 

def combine_file_to_tables(posts_dir : str, comments_dir : str, user_dir : str, spark):
    '''Process the data and output three dataframe'''
    posts_dir = Path(posts_dir) 
    comments_dir = Path(comments_dir) 
    user_dir = Path(user_dir) 
    if not comments_dir.exists():
        raise FileNotFoundError("comments directory not found")
    if not posts_dir.exists():
        raise FileNotFoundError("posts directory not found")
    if not user_dir.exists():
        raise FileNotFoundError("user directory not found") 
    
    
    comment_file_paths = [str(comments_dir / file_name) for file_name in sorted(os.listdir(comments_dir))]
    post_file_paths = [str(posts_dir / file_name) for file_name in sorted(os.listdir(posts_dir))]
    user_file_paths = [str(user_dir / file_name) for file_name in sorted(os.listdir(user_dir))]
    comment_df = None
    for comment_file_path in comment_file_paths: 
        if comment_df is None:
            comment_df = spark.read.format("parquet").load(comment_file_path)
        else:
            comment_df = comment_df.unionAll(spark.read.format("parquet").load(comment_file_path))
    # combine all of the post df
    post_df = None
    for post_file_path in post_file_paths:
        if post_df is None:
            post_df = spark.read.format("parquet").load(post_file_path)
        else:
            post_df = post_df.unionAll(spark.read.format("parquet").load(post_file_path))
    # combine all of the user df
    user_df = None
    for user_file_path in user_file_paths:
        if user_df is None:
            user_df = spark.read.format("parquet").load(user_file_path)
        else:
            user_df = user_df.unionAll(spark.read.format("parquet").load(user_file_path))
    user_df = user_df.distinct()
    return post_df, comment_df, user_df

def export_data(data_dir : Path, post_df, comment_df, user_df):
    '''Export the data to local files'''
    export_dir = data_dir / "combine_all"
    post_dir = export_dir / "post"
    comment_dir = export_dir / "comment"
    user_dir = export_dir / "user"
    if not export_dir.exists():
        export_dir.mkdir(parents=True)
    post_df.coalesce(1).write.mode("overwrite").parquet(str(post_dir))
    comment_df.coalesce(1).write.mode("overwrite").parquet(str(comment_dir))
    user_df.coalesce(1).write.mode("overwrite").parquet(str(user_dir))

def spark_data_processing(data_dir: str, post_dir : str, comment_dir : str, user_dir : str):
    '''Process the data and output the data to the local file'''
    spark = initialize_spark()
    post_df, comment_df, user_df = combine_file_to_tables(post_dir, comment_dir, user_dir, spark)
    export_data(Path(data_dir), post_df, comment_df, user_df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str)
    parser.add_argument("--post_dir", type=str)
    parser.add_argument("--comment_dir", type=str)
    parser.add_argument("--user_dir", type=str)
    args = parser.parse_args()
    spark_data_processing(args.data_dir, 
                        args.post_dir, 
                        args.comment_dir, 
                        args.user_dir) 
    
if __name__ == "__main__":
    main()