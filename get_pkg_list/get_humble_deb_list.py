#!/usr/bin/env python3
import subprocess
import sys

def get_humble_packages():
    try:
        result = subprocess.run(
            ['apt-cache', 'search', 'ros-humble-'],
            capture_output=True,
            text=True,
            check=True
        )

        packages = []
        for line in result.stdout.strip().split('\n'):
            if line:
                pkg_name = line.split()[0]
                packages.append(pkg_name)

        packages.sort()

        output_file = 'ros_humble_packages.txt'
        fact_nums = 0
        with open(output_file, 'w') as f:
            for pkg in packages:
                if '-dbgsym' not in pkg:
                    f.write(pkg + '\n')
                    fact_nums += 1


        print(f"成功获取 {fact_nums} 个包，已保存到 {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    get_humble_packages()
