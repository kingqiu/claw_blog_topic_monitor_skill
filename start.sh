#!/bin/bash
# 使用虚拟环境运行Blog Topic Monitor

cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 运行主程序，传递所有参数
python run.py "$@"
