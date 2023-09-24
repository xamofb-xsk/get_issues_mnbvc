import json
import os
import random
import time
import requests
from tqdm import tqdm
import argparse
SOURCE_PATH = './20230301/github.20230301.1.代码元数据/'  # 源路径
TARGET_PATH = './output'  # 目的路径
TMP_PATH = './tmp' # 存放爬取记录

github_token = ""
header = {"Authorization": f"token {github_token}"}

def get_jsonl_filenames(directory):
    # 获取目录下以jsonl结尾的文件，返回相对路径列表
    jsonl_filenames = []
    for filename in os.listdir(directory):
        if filename.endswith('.jsonl'):
            jsonl_filenames.append(filename)
    return jsonl_filenames


def get_data(filename):
    # 解析jsonl
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception as e:
                print(e)

def get(url, params=None):
    # requests.get， 并防止token超限
    print(f'get {url}')
    for i in range(3):
        try:
            response = requests.get(url, headers=header, params=params)
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            current_timestamp = int(time.time())
            time_diff = int(reset) - current_timestamp
            if response.status_code == 200:
                data = response.json()
            else:
                data = []
            if int(remaining) <= 20:
                time.sleep(time_diff)            
            return data
        except Exception as e:
            print(e)
            continue

def get_issues(metadata, record_file):
    record = {}
    if os.path.exists(record_file):
        with open(record_file, 'r') as f:
            try:
                record = json.load(f)
            except Exception as e:
                print(e)
        
    if metadata['id'] in record:
        return

    with open(os.path.join(TARGET_PATH, f'{metadata["id"]}.jsonl'), 'w', encoding='utf-8') as f:
        pass

    page = 1
    while True:
        try:
            issues = get(metadata['url'] + '/issues', params={"page": page, "state": "all"})
            add_comments(metadata, issues)
            if issues:
                page += 1
            else:
                break
        except Exception as e:
            print(e)
            break

    record[metadata['id']] = {'get_time': time.time()}
    with open(record_file, 'w') as f:
        json.dump(record, f)



def add_comments(metadata, issues):
    # 增加评论
    for issue in issues:
        issue['comments_data'] = []
        if issue['comments']:
            comments_url = issue['comments_url']
            comments_data = get(comments_url)
            if comments_data:
                issue['comments_data'].extend(comments_data)
        write_to_file(metadata, issue)
        
def write_to_file(metadata, issue):
    with open(os.path.join(TARGET_PATH, f'{metadata["id"]}.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps(issue, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            prog='python get_issue.py',
            description='GET MNBVC ISSUES',
            epilog='Text at the bottom of help')
    parser.add_argument('-p', '--path', help='meta jsonl path', required=True)
    parser.add_argument('-t', '--token', help='github token like github_pat_*', required=True)
    

    args = parser.parse_args()
    SOURCE_PATH = args.path
    headers = {"Authorization": f"token {args.token}"}

    if not os.path.exists(TARGET_PATH):
        os.makedirs(TARGET_PATH)

    if not os.path.exists(TMP_PATH):
        os.makedirs(TMP_PATH)

    jsonl_filenames = get_jsonl_filenames(SOURCE_PATH)  # 获取文件名
    for filename in jsonl_filenames:
        abs_filename = os.path.join(SOURCE_PATH, filename)
        record_file = os.path.join(TMP_PATH, filename.replace('jsonl', 'json'))
        for metadata in get_data(abs_filename):
            get_issues(metadata, record_file)