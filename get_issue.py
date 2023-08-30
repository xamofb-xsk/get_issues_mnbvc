import time
import os
import json
import requests
from tqdm import tqdm

jsonl_filenames = []
# GitHub API 的仓库 Issues 列表 URL
urls = []
issue_nums = []
compare_num = 0
datas = []

# 发起 GET 请求获取仓库的 Issues 列表
github_token = ""
headers = {
    "Authorization": f"token {github_token}"
}


def get_jsonl_filenames(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.jsonl'):
            jsonl_filenames.append(filename)


def get_data(filename):
    data = []
    with open(filename, "r", encoding="utf-8") as f:
        num_lines = sum(1 for _ in f)  # 获取文件总行数
        f.seek(0)  # 将文件指针重新回到文件开头
        for line in tqdm(f, total=num_lines, desc="Processing"):  # 使用 tqdm 来添加进度条
            json_obj = json.loads(line)
            data.append(json_obj)
        f.close()
        return data


def get_issue_num(url):
    global compare_num, issue_nums
    page = 1
    while True:
        response = requests.get(url['url'] + '/issues', headers=headers, params={"page": page, "state": "all"})
        limit = response.headers.get("X-RateLimit-Limit")
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        current_timestamp = int(time.time())
        time_diff = int(reset) - current_timestamp
        print(f"可请求次数: {limit}")
        print(f"剩余请求次数: {remaining}")
        print(f"重置时间还有: {time_diff // 60} 分钟")
        print(f"已请求：{page}页")
        if int(remaining) > 20:
            if response.status_code == 200:
                issues = response.json()
                if not issues:
                    break  # 没有更多数据了，退出循环
                for issue in issues:
                    issue_nums.append(issue['number'])
            else:
                print(f"Failed to fetch issues. Status code: {response.status_code}")
        else:
            time.sleep(time_diff)
        page += 1

    print(f"所有 ISSUE 编号请求完毕: {issue_nums}")
    print(f"供：{len(issue_nums)}条\n")
    print("进入 ISSUE 详情获取阶段\n")
    # get_issue(res.json())
    return issue_nums


def get_issue(url, filename):
    global compare_num, issue_nums
    filename = filename.split('.')
    name = filename[0] + "-data" + ".jsonl"
    print(name)
    compare_num += 1
    json = {}
    metadata = {}
    item_data = []
    repo = {}
    repo["Repo_ID"] = url['id']
    json["来源"] = url['url']
    # json["repo_full_name"] = url["full_name"]
    num_issues = len(issue_nums)
    print(f"issue_num len: {num_issues}")
    for k, issue_num in tqdm(enumerate(issue_nums), total=num_issues, desc="Processing issues", unit="issue"):
        expand = ""
        expand = f"<h1>{issue_num}</h1>"
        issue_url = url['url'] + '/issues' + f"/{issue_num}"
        json["ID"] = issue_num
        # print(issue_url)
        try:
            response = requests.get(issue_url, headers=headers)
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            current_timestamp = int(time.time())
            time_diff = int(reset) - current_timestamp
            print(f"\n可请求次数: {limit}")
            print(f"剩余请求次数: {remaining}")
            print(f"重置时间还有: {time_diff // 60} 分钟")

            time.sleep(0.5)
            if int(remaining) > 20:
                if response.status_code == 200:
                    issue_data = response.json()  # 解析 JSON 响应
                    json['主题'] = issue_data['title']
                    expand += f"{issue_data['created_at']}<br>{issue_data['title']}<ul><li>"
                    json1 = {}
                    comments_url = issue_data['comments_url']
                    comments_response = requests.get(comments_url, headers=headers)
                    if issue_data['body'] is not None:
                        json1["楼ID"] = "0"
                        json1[f'回复'] = issue_data["body"]
                        json1["扩展字段"] = {"回复人": issue_data['user']['login']}
                        expand += f"[{issue_data['user']['login']}]{issue_data['body']}</li>"
                        item_data.append(json1)
                        json1 = {}
                    if comments_response.status_code == 200:
                        comments = comments_response.json()
                        metadata["发帖时间"] = issue_data["created_at"]
                        metadata["回复数"] = len(comments)
                        for i, comment in enumerate(comments):
                            i += 1
                            comment_body = comment['body']
                            json1["楼ID"] = f"{i}"
                            if comment_body is not None:
                                json1[f'回复'] = comment_body
                                json1["扩展字段"] = {"回复人": comment['user']['login']}
                                expand += f"[{comment['user']['login']}]{comment_body}</li>"
                                item_data.append(json1)
                                json1 = {}
                        expand += "</ul>"
                        json["回复"] = item_data
                        item_data = []
                        metadata["拓展字段"] = {"原文": expand}
                        json["元数据"] = metadata
                        repo[f"问题{k}"] = json
                        metadata = {}
                        json = {}
                    else:
                        print(f"Failed to fetch comments. Status code: {comments_response.status_code}")
                        break
                else:
                    print(f"Failed to fetch issue details. Status code: {response.status_code}")
                    break
            else:
                time.sleep(time_diff)
        except:
            write_to_file(repo, name)
            time.sleep(10)

    write_to_file(repo, name)


def write_to_file(json_data, filename):
    if not os.path.exists("./output"):
        os.makedirs("./output")
    with open(f"./output/{filename}", 'a', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False)
        f.write('\n')
        f.close()


if __name__ == '__main__':
    directory_path = './'
    get_jsonl_filenames(directory_path)  # 获取文件名
    for filename in jsonl_filenames:
        data = get_data(filename)
        for url in data:
            issue_nums = get_issue_num(url)
            get_issue(url, filename)
