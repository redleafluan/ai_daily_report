#!/bin/bash

# 获取当前脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 进入该目录
cd "$DIR"

# 获取当前时间
NOW=$(date +"%Y-%m-%d %H:%M:%S")

echo "[$NOW] Starting Daily Report..." >> cron_log.txt

# 运行 Python 脚本
# 尝试使用 python3，如果找不到则尝试 python
if command -v python3 &> /dev/null; then
    python3 notion_daily_report.py >> cron_log.txt 2>&1
else
    python notion_daily_report.py >> cron_log.txt 2>&1
fi

echo "[$NOW] Finished." >> cron_log.txt
