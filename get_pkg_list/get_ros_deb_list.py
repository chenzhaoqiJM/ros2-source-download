#!/usr/bin/env python3
import os
import subprocess
import sys


def get_distro_name():
    if len(sys.argv) > 1:
        return sys.argv[1].strip().lower()
    return 'humble'


def get_packages(distro):
    package_prefix = f'ros-{distro}-'

    try:
        result = subprocess.run(
            ['apt-cache', 'search', package_prefix],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        packages = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            pkg_name = line.split()[0]
            if pkg_name.startswith(package_prefix) and '-dbgsym' not in pkg_name:
                packages.append(pkg_name)

        packages.sort()

        output_dir = os.path.join(os.path.dirname(__file__), distro)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'ros_{distro}_packages.txt')
        with open(output_file, 'w') as f:
            for pkg in packages:
                f.write(pkg + '\n')

        print(f"成功获取 {len(packages)} 个 {distro} 包，已保存到 {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    get_packages(get_distro_name())
