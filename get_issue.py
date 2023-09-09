import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm import tqdm

SOURCE_PATH = './20230301/github.20230301.1.代码元数据/'  # 源路径
TARGET_PATH = './output'  # 目的路径
THREADS = 4  # 线程池大小

github_tokens = [
    ""]
headers = [{"Authorization": f"token {github_token}"}
           for github_token in github_tokens]


def get_jsonl_filenames(directory):
    # 获取目录下以jsonl结尾的文件，返回绝对路径列表
    jsonl_filenames = []
    for filename in os.listdir(directory):
        if filename.endswith('.jsonl'):
            jsonl_filenames.append(os.path.join(directory, filename))
    return jsonl_filenames


def get_data(filename):
    # 解析jsonl
    data = []
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in tqdm(lines, desc="Processing"):  # 使用 tqdm 来添加进度条
            json_obj = json.loads(line)
            data.append(json_obj)
        return data


def get_issues(metadata):
    # 根据元信息获取issues
    if os.path.exists(os.path.join(TARGET_PATH, f'{metadata["id"]}.json')):
        return
    total_issues = []
    page = 1
    while True:
        try:
            response = requests.get(metadata['url'] + '/issues', headers=random.choice(
                headers), params={"page": page, "state": "all"})
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            current_timestamp = int(time.time())
            time_diff = int(reset) - current_timestamp
            print(
                f"ID: {metadata['id']} PAGE: {page} TOKEN REMAINING {remaining} / {limit} ISSUES: {metadata['url']}")
            if int(remaining) > 20:
                if response.status_code == 200:
                    issues = response.json()
                    if not issues:
                        break  # 没有更多数据了，退出循环
                    total_issues.extend(issues)
                else:
                    print(
                        f"Failed to fetch issues. Status code: {response.status_code}")
            else:
                time.sleep(time_diff)
            page += 1
        except Exception as e:
            print(e)
            break
    add_comments(total_issues)
    write_to_file({
        'id': metadata['id'],
        'issues': total_issues
    })
    return total_issues


def add_comments(issues):
    # 增加评论
    for issue in issues:
        issue['comments_data'] = []
        if issue['comments']:
            comments_url = issue['comments_url']
            comments_response = requests.get(
                comments_url, headers=random.choice(headers))
            if comments_response.status_code == 200:
                issue['comments_data'].extend(comments_response.json())
            else:
                print(
                    f"Failed to fetch comments. Status code: {comments_response.status_code}")


def write_to_file(data):
    if not os.path.exists(TARGET_PATH):
        os.makedirs(TARGET_PATH)
    with open(os.path.join(TARGET_PATH, f'{data["id"]}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


if __name__ == '__main__':
    jsonl_filenames = get_jsonl_filenames(SOURCE_PATH)  # 获取文件名
    for filename in jsonl_filenames:
        metadatas = get_data(filename)
        with ThreadPoolExecutor(THREADS) as pool:
            for metadata in metadatas:
                pool.submit(get_issues, metadata)
