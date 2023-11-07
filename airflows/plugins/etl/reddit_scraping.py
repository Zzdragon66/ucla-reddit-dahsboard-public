from datetime import datetime
from dateutil import tz
from pathlib import Path
import pandas as pd
import praw
from time import sleep
from zoneinfo import ZoneInfo

post_related_fields = [
    "id",
    "title", 
    "score",
    "num_comments",
    "created_utc",
    "url",
    "upvote_ratio", 
]
comment_related_fields = [
    "id", 
    "created",
]

user_related_fields = [
    "id", 
    "name"
]

def reddit_initialization(client_id:str, client_secrete:str):
    '''initialize the reddit credential with a json format'''
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secrete,
        user_agent="macos:reddit_app_for_project"
    )
    return reddit

def get_attribute(obj, field):
    '''Get the attribute of the obj[field] if object does not have the field return None'''
    if hasattr(obj, field):
        return getattr(obj, field)
    return None

def extract_users(cur_user, related_fields : list[str]) -> dict:
    '''
        Extract the fields from the user
        if the user is None, return None
    '''
    none_row = {"user_" + field : None for field in related_fields} 
    if cur_user is None:
        return none_row
    sleep(1) # to avoid the drawning the api limit
    try:
        ret_row = {"user_" + field : get_attribute(cur_user, field) for field in related_fields}
    except Exception:
        return none_row
    return ret_row
        

def post_comment_converter(cur_post, related_fields : list[str]) -> dict:
    '''
        Extract fields from post and comments and append user to user row
    '''
    return {field : post_comment_extract_field(cur_post, field) for field in related_fields}

def post_comment_extract_field(cur_post, field):
    '''
    extract the fields from the cur_post and comment
    if the current field is time -> converted it into the date
    '''
    if not hasattr(cur_post, field):
        return None
    if field == "created_utc" or field == "created":
        return convert_utc_time(getattr(cur_post, field)) 
    return getattr(cur_post, field)

def convert_utc_time(utc_time) -> datetime.date: 
    '''Convert the UTC time into datetime.date'''
    cur_time_zone = ZoneInfo('America/Los_Angeles')
    return pd.to_datetime(utc_time, utc=True, unit='s').astimezone(cur_time_zone).date()


def scrape_post_comments(reddit, date_lower : datetime.date, date_upper : datetime.date, 
        post_path: str, comment_path : str, user_path : str,
        write_thres = 200) -> Path:
    """
    reddit: the reddit instance 
    scraping all of the data and store it from locally
    """
    # initialize the library to store data
    print(date_lower, date_upper) 
    post_path = Path(post_path)
    comment_path = Path(comment_path)
    user_path = Path(user_path)
    # check if the path exists
    if not post_path.exists() or not comment_path.exists() or not user_path.exists():
        raise FileNotFoundError("The path does not exists")
    ucla_reddit_new_posts = reddit.subreddit('ucla').new(limit = None)
    post_rows = []
    comment_rows = []
    user_rows = []
    # use count to do log and file exportation
    post_out_cnt = 1
    comment_out_cnt = 1
    user_out_cnt = 1
    for cur_post in ucla_reddit_new_posts:
        cur_post_date = convert_utc_time(cur_post.created_utc)
        if (cur_post_date < date_lower):
            break
        if cur_post_date >= date_lower and cur_post_date <= date_upper:
            sleep(1)
            print(f"Date={cur_post_date}, post_count={len(post_rows)}, comment_count={len(comment_rows)}, user_count={len(user_rows)}")
            # Extract user from the post 
            user_row = extract_users(cur_post.author, user_related_fields) 
            user_rows.append(user_row)
            post_row = post_comment_converter(cur_post, post_related_fields)
            post_row.update(user_row)
            post_rows.append(post_row)
            if (cur_post.num_comments > 0):
                # add the comments to comments table
                parent_id = getattr(cur_post, "id")
                cur_post.comments.replace_more(limit=None)
                cur_post_comments = cur_post.comments.list()
                for cur_post_comment in cur_post_comments:
                    sleep(1)
                    # Extract user from the comment
                    user_row = extract_users(cur_post_comment.author, user_related_fields)
                    user_rows.append(user_row)
                    # Extract the comments field from the comments
                    cur_comment_row = post_comment_converter(cur_post_comment, comment_related_fields)
                    cur_comment_row["parent_id"] = parent_id
                    cur_comment_row.update(user_row)
                    comment_rows.append(cur_comment_row)
        # write the data back for posts
        if (len(post_rows) >= write_thres):
            post_file_name = f"post-{post_out_cnt}.parquet"
            pd.DataFrame(post_rows).to_parquet(post_path / post_file_name) 
            post_rows.clear()
            post_out_cnt += 1

        # write the data back for comments
        if (len(comment_rows) >= write_thres):
            comment_file_name = f"comment-{comment_out_cnt}.parquet"
            pd.DataFrame(comment_rows).to_parquet(comment_path / comment_file_name)
            comment_rows.clear()
            comment_out_cnt += 1
        # write out the user data back to disk
        if (len(user_rows) >= write_thres):
            user_file_name = f"user-{user_out_cnt}.parquet"
            pd.DataFrame(user_rows).to_parquet(user_path / user_file_name)
            user_rows.clear()
            user_out_cnt += 1


    # if there is data remaing, write back to disk
    if len(post_rows) > 0:
        post_file_name = f"post-{post_out_cnt}.parquet"
        pd.DataFrame(post_rows).to_parquet(post_path / post_file_name) 
        post_rows.clear()
    if  len(comment_rows)> 0:
        comment_file_name = f"comment-{comment_out_cnt}.parquet"
        pd.DataFrame(comment_rows).to_parquet(comment_path / comment_file_name)
        comment_rows.clear()
    if (len(user_rows) > 0):
        user_file_name = f"user-{user_out_cnt}.parquet"
        pd.DataFrame(user_rows).to_parquet(user_path / user_file_name)
        user_rows.clear()
        user_out_cnt += 1

    return post_path, comment_path

def reddit_scraping(client_id : str, client_secret: str, 
                    date_lower : str, date_upper : str, 
                    post_path : str, comment_path : str, user_path : str, write_thres = 200):
    '''
        Scraping the reddit with given client_id, client_scret, date_lower
    '''
    date_lower = pd.to_datetime(date_lower).date()
    date_upper = pd.to_datetime(date_upper).date()
    reddit = reddit_initialization(client_id, client_secret)
    scrape_post_comments(reddit, date_lower, date_upper, post_path, comment_path, user_path, write_thres)

def main():
    '''Main function for calling this file directly'''
    return None

if __name__ == "__main__":
    main()