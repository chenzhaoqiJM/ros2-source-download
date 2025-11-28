import yaml
import os
import subprocess
import sys

# --- 配置区域 ---
YAML_FILE = 'distribution.yaml'   # 你的ROS分布文件名
IGNORE_FILE = 'ignore_list.txt'   # 指定要跳过的包名列表文件
TARGET_DIR = 'src'                # 下载的目标文件夹
# ----------------

def load_ignore_list(filename):
    """读取忽略列表，返回一个集合"""
    ignore_set = set()
    if not os.path.exists(filename):
        print(f"[提示] 未找到忽略文件 {filename}，将下载所有包。")
        return ignore_set

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除空白符和注释
            name = line.split('#')[0].strip()
            if name:
                ignore_set.add(name)
    return ignore_set

def clone_repositories():
    # 1. 创建目标目录 src
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"[创建目录] {TARGET_DIR}")

    # 2. 加载忽略列表
    ignore_set = load_ignore_list(IGNORE_FILE)

    # 3. 加载 YAML 文件
    if not os.path.exists(YAML_FILE):
        print(f"[错误] 找不到文件: {YAML_FILE}")
        sys.exit(1)

    print(f"[开始读取] {YAML_FILE}...")

    with open(YAML_FILE, 'r', encoding='utf-8') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"[YAML解析错误] {exc}")
            sys.exit(1)

    repositories = data.get('repositories', {})
    print(f"共发现 {len(repositories)} 个仓库定义。")
    print("-" * 40)

    # 4. 遍历并下载
    for repo_name, repo_info in repositories.items():
        # --- 检查是否在忽略列表中 ---
        if repo_name in ignore_set:
            print(f"[跳过] {repo_name} (在忽略列表中)")
            continue

        # --- 获取 Source 信息 ---
        source_info = repo_info.get('source')
        if not source_info:
            print(f"[警告] {repo_name} 没有 source 字段，跳过。")
            continue

        url = source_info.get('url')
        version = source_info.get('version')
        type_ = source_info.get('type', 'git')

        if type_ != 'git':
            print(f"[跳过] {repo_name} 类型不是 git ({type_})")
            continue

        # --- 构建 git 命令 ---
        # 目标路径: ./src/RepoName
        repo_dest = os.path.join(TARGET_DIR, repo_name)

        if os.path.exists(repo_dest):
            print(f"[跳过] {repo_name} 文件夹已存在")
            continue

        print(f"[正在下载] {repo_name} -> 分支: {version}")

        cmd = ['git', 'clone', url, repo_dest]

        # 如果有版本信息，添加参数
        if version:
            cmd.extend(['--depth', '1', '--branch', str(version)])

        # --- 执行命令 ---
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"[失败] 克隆 {repo_name} 失败，请检查网络或分支名称。")
        except Exception as e:
            print(f"[错误] 发生未知错误: {e}")

    print("-" * 40)
    print("所有任务完成。")

if __name__ == "__main__":
    clone_repositories()