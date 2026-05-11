# get_pkg_list

用于获取指定 ROS 发行版的 Debian 二进制包列表，并基于 `apt-cache` 分析这些包之间的 ROS 依赖关系。

当前脚本支持多个 ROS 发行版，例如：`humble`、`jazzy`。

## 文件说明

- `get_ros_deb_list.py`：从本机 `apt` 软件源中搜索指定发行版的 `ros-<distro>-*` 包，并生成包列表文件。
- `analyze_dependencies.py`：读取包列表，分析包之间的依赖，输出依赖深度排序结果和分层结果。
- `ros_humble_packages.txt`：已有的 `humble` 包列表样例。
- `dependency_layers_humble.txt`：已有的 `humble` 分层结果样例。

## 依赖要求

需要系统已安装并可使用：

- `python3`
- `apt-cache`

同时需要本机已经配置好对应 ROS 发行版的软件源；否则 `apt-cache search` 或 `apt-cache showsrc` 可能查不到结果。

## 用法

默认发行版为 `humble`。

### 1. 生成指定发行版的包列表

```bash
python3 get_ros_deb_list.py
```

等价于：

```bash
python3 get_ros_deb_list.py humble
```

指定其他发行版，例如 `jazzy`：

```bash
python3 get_ros_deb_list.py jazzy
```

生成文件：

- `ros_humble_packages.txt`
- 或 `ros_jazzy_packages.txt`
- 其它发行版对应 `ros_<distro>_packages.txt`

### 2. 分析依赖关系

先确保对应的包列表文件已经生成。

```bash
python3 analyze_dependencies.py
```

等价于：

```bash
python3 analyze_dependencies.py humble
```

分析 `jazzy`：

```bash
python3 analyze_dependencies.py jazzy
```

生成文件：

- `sorted_packages_<distro>.txt`：按依赖深度排序后的包列表
- `dependency_layers_<distro>.txt`：按层分组的依赖结果，层与层之间使用 `---` 分隔

## 输出说明

### `sorted_packages_<distro>.txt`

按依赖深度从小到大排序：

- 越靠前表示越接近底层依赖
- 越靠后表示依赖更多其它 ROS 包

### `dependency_layers_<distro>.txt`

按层输出包：

- 同一层中的包不依赖当前分析集合内尚未完成的其它包
- 每一层之间以 `---` 分隔
- 若存在循环依赖或元数据缺失，脚本会做保底处理，避免死循环

## 实现说明

`analyze_dependencies.py` 的依赖分析策略：

1. 先通过 `apt-cache show` 获取二进制包信息，并尝试解析 `Source` 字段。
2. 再通过 `apt-cache showsrc` 获取源码包的：
   - `Build-Depends`
   - `Build-Depends-Indep`
   - `Build-Depends-Arch`
3. 从这些字段中提取 `ros-<distro>-*` 依赖。
4. 如果 `showsrc` 无结果，则回退到二进制包的：
   - `Depends`
   - `Pre-Depends`

因此，分层结果更偏向“构建依赖分析”；在缺少源码索引时，会退化为“运行时依赖近似分析”。

## 注意事项

- 该工具只提取指定发行版前缀的 ROS 包依赖，例如 `ros-humble-*` 或 `ros-jazzy-*`。
- 会自动忽略 `-dbgsym` 包。
- 若某些包在当前 `apt` 源中缺少源码索引，依赖结果可能不完整。
- 不同 Ubuntu / ROS 软件源环境下，输出结果可能不同。

## 示例流程

以 `jazzy` 为例：

```bash
python3 get_ros_deb_list.py jazzy
python3 analyze_dependencies.py jazzy
```

最终会得到：

- `ros_jazzy_packages.txt`
- `sorted_packages_jazzy.txt`
- `dependency_layers_jazzy.txt`
