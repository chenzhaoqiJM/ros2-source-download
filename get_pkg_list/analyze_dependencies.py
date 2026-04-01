#!/usr/bin/env python3
import subprocess
import sys
from collections import defaultdict

def get_dependencies(package):
    """获取包的ros-humble*构建依赖（Build-Depends）"""
    try:
        result = subprocess.run(
            ['apt-cache', 'showsrc', package],
            capture_output=True,
            text=True,
            timeout=10
        )
        deps = []
        for line in result.stdout.split('\n'):
            if line.startswith('Build-Depends:'):
                bd_line = line.split(':', 1)[1].strip()
                # Build-Depends 是逗号分隔的，每项可能带版本约束和标签
                for item in bd_line.split(','):
                    dep = item.strip().split()[0] if item.strip() else ''
                    if dep.startswith('ros-humble-'):
                        deps.append(dep)
        return deps
    except:
        return []

def calculate_depth(pkg, deps_map, memo):
    """计算包的依赖深度（递归）"""
    if pkg in memo:
        return memo[pkg]

    deps = deps_map.get(pkg, [])
    if not deps:
        memo[pkg] = 0
        return 0

    max_depth = max(calculate_depth(dep, deps_map, memo) for dep in deps)
    memo[pkg] = max_depth + 1
    return memo[pkg]

def build_dependency_layers(packages, deps_map):
    """按层解析依赖关系：同一层内的包互不依赖。"""
    package_set = set(packages)
    remaining = set(packages)
    resolved = set()
    layers = []

    while remaining:
        current_layer = sorted(
            pkg for pkg in remaining
            if set(dep for dep in deps_map.get(pkg, []) if dep in package_set) <= resolved
        )

        if not current_layer:
            # 出现循环依赖或缺失元数据时，保底输出剩余包，避免死循环
            current_layer = sorted(remaining)

        layers.append(current_layer)
        resolved.update(current_layer)
        remaining.difference_update(current_layer)

    return layers

def main():
    # 读取包列表
    with open('ros_humble_packages.txt', 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.strip().endswith('-dbgsym')]

    print(f"处理 {len(packages)} 个包...", file=sys.stderr)

    # 构建依赖图
    deps_map = {}
    for i, pkg in enumerate(packages):
        if i % 100 == 0:
            print(f"进度: {i}/{len(packages)}", file=sys.stderr)
        deps_map[pkg] = get_dependencies(pkg)

    print("计算依赖深度...", file=sys.stderr)

    # 计算每个包的深度
    memo = {}
    for pkg in packages:
        calculate_depth(pkg, deps_map, memo)

    # 按深度排序（从小到大，即底层在上）
    sorted_packages = sorted(packages, key=lambda p: memo.get(p, 0))
    dependency_layers = build_dependency_layers(packages, deps_map)

    # 输出结果
    with open('sorted_packages.txt', 'w') as f:
        for pkg in sorted_packages:
            f.write(pkg + '\n')

    with open('dependency_layers.txt', 'w') as f:
        for index, layer in enumerate(dependency_layers):
            if index > 0:
                f.write('---\n')
            for pkg in layer:
                f.write(pkg + '\n')

    print("结果已保存到 sorted_packages.txt", file=sys.stderr)
    print("分层结果已保存到 dependency_layers.txt", file=sys.stderr)

if __name__ == '__main__':
    main()
