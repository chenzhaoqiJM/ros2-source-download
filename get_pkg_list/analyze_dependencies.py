#!/usr/bin/env python3
import os
import re
import subprocess
import sys


def parse_control_fields(text):
    """解析 Debian control 风格字段（支持续行）。"""
    fields = {}
    current_key = None

    for raw_line in text.splitlines():
        if not raw_line:
            continue

        if raw_line[0].isspace() and current_key:
            fields[current_key] += ' ' + raw_line.strip()
            continue

        if ':' not in raw_line:
            current_key = None
            continue

        key, value = raw_line.split(':', 1)
        current_key = key.strip()
        fields[current_key] = value.strip()

    return fields


def get_distro_name():
    if len(sys.argv) > 1:
        return sys.argv[1].strip().lower()
    return 'humble'


def extract_ros_deps(dep_expr, distro):
    """从依赖表达式中提取指定发行版的 ros-* 依赖。"""
    if not dep_expr:
        return []

    deps = []
    seen = set()
    package_prefix = f'ros-{distro}-'

    # 逗号分隔依赖项，每项可能包含 alternatives（|）和版本/架构约束
    for item in dep_expr.split(','):
        for alternative in item.split('|'):
            alt = alternative.strip()
            match = re.match(r'([a-z0-9][a-z0-9+.-]*)', alt)
            if not match:
                continue
            pkg = match.group(1)
            if pkg.startswith(package_prefix) and pkg not in seen:
                seen.add(pkg)
                deps.append(pkg)

    return deps


def apt_show_fields(package):
    """读取 apt-cache show 的首个段落字段。"""
    result = subprocess.run(
        ['apt-cache', 'show', package],
        capture_output=True,
        text=True,
        timeout=10
    )
    # 只取第一个 stanza，避免多版本混杂
    first_stanza = result.stdout.split('\n\n', 1)[0]
    return parse_control_fields(first_stanza)


def resolve_source_package(binary_package):
    """从二进制包解析其 Source 包名；没有 Source 字段时回退为自身。"""
    fields = apt_show_fields(binary_package)
    source_field = fields.get('Source', '')
    if source_field:
        return source_field.split()[0].strip()
    return binary_package


def get_runtime_ros_deps(package, distro):
    """showsrc 不可用时，回退使用二进制 Depends 作为近似依赖。"""
    fields = apt_show_fields(package)
    depends_expr = ', '.join(
        v for v in [fields.get('Depends', ''), fields.get('Pre-Depends', '')] if v
    )
    return extract_ros_deps(depends_expr, distro)

def get_dependencies(package, distro):
    """获取包的 ros-<distro>-* 依赖，优先 Build-Depends，失败时回退 Depends。"""
    try:
        source_package = resolve_source_package(package)
        result = subprocess.run(
            ['apt-cache', 'showsrc', source_package],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            fields = parse_control_fields(result.stdout)
            dep_expr = ', '.join(
                v for v in [
                    fields.get('Build-Depends', ''),
                    fields.get('Build-Depends-Indep', ''),
                    fields.get('Build-Depends-Arch', ''),
                ] if v
            )
            deps = extract_ros_deps(dep_expr, distro)
            if deps:
                return deps

        # 某些包没有 source 索引（如部分外部仓库包），回退到二进制 Depends
        return get_runtime_ros_deps(package, distro)
    except Exception:
        return []

def calculate_depth(pkg, deps_map, memo):
    """计算包的依赖深度（递归）"""
    if memo.get(pkg) == -1:
        # 检测到环；让层级逻辑兜底处理，避免无限递归
        return 0

    if pkg in memo:
        return memo[pkg]

    memo[pkg] = -1

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
    distro = get_distro_name()
    output_dir = os.path.join(os.path.dirname(__file__), distro)
    os.makedirs(output_dir, exist_ok=True)
    package_file = os.path.join(output_dir, f'ros_{distro}_packages.txt')
    sorted_output_file = os.path.join(output_dir, f'sorted_packages_{distro}.txt')
    layers_output_file = os.path.join(output_dir, f'dependency_layers_{distro}.txt')

    # 读取包列表
    with open(package_file, 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.strip().endswith('-dbgsym')]

    print(f"处理 {len(packages)} 个包...", file=sys.stderr)

    # 构建依赖图
    deps_map = {}
    for i, pkg in enumerate(packages):
        if i % 100 == 0:
            print(f"进度: {i}/{len(packages)}", file=sys.stderr)
        deps_map[pkg] = get_dependencies(pkg, distro)

    print("计算依赖深度...", file=sys.stderr)

    # 计算每个包的深度
    memo = {}
    for pkg in packages:
        calculate_depth(pkg, deps_map, memo)

    # 按深度排序（从小到大，即底层在上）
    sorted_packages = sorted(packages, key=lambda p: memo.get(p, 0))
    dependency_layers = build_dependency_layers(packages, deps_map)

    # 输出结果
    with open(sorted_output_file, 'w') as f:
        for pkg in sorted_packages:
            f.write(pkg + '\n')

    with open(layers_output_file, 'w') as f:
        for index, layer in enumerate(dependency_layers):
            if index > 0:
                f.write('---\n')
            for pkg in layer:
                f.write(pkg + '\n')

    print(f"结果已保存到 {sorted_output_file}", file=sys.stderr)
    print(f"分层结果已保存到 {layers_output_file}", file=sys.stderr)

if __name__ == '__main__':
    main()
