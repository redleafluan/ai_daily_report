import os
import sys
import subprocess

def setup_cron():
    print("=== Notion Daily Report 定时任务助手 ===")
    
    # Get current directory and paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "run_report.sh")
    
    # Ensure the shell script is executable
    os.chmod(script_path, 0o755)
    print(f"配置文件路径: {script_path}")
    
    # Ask for time
    print("\n您希望每天几点生成日报？(24小时制)")
    hour = input("请输入小时 (0-23, 默认 23): ").strip() or "23"
    minute = input("请输入分钟 (0-59, 默认 00): ").strip() or "00"
    
    try:
        h = int(hour)
        m = int(minute)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except ValueError:
        print("时间格式错误，将使用默认值 23:00")
        h, m = 23, 0
        
    cron_time = f"{m} {h} * * *"
    cron_cmd = f"/bin/bash {script_path}"
    new_job = f"{cron_time} {cron_cmd}"
    
    print(f"\n即将添加任务: 每天 {h:02d}:{m:02d} 执行")
    
    # Read existing cron
    try:
        # Check if crontab exists
        current_cron = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode('utf-8')
    except subprocess.CalledProcessError:
        current_cron = ""
        
    # Remove existing job for this script to avoid duplicates
    lines = current_cron.splitlines()
    new_lines = [line for line in lines if script_path not in line]
    
    # Add new job
    new_lines.append(new_job)
    new_lines.append("") # End with newline
    
    final_cron = "\n".join(new_lines)
    
    # Write back
    p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(input=final_cron.encode('utf-8'))
    
    if p.returncode == 0:
        print("\n✅ 定时任务设置成功！")
        print(f"日志文件将保存在: {os.path.join(current_dir, 'cron_log.txt')}")
        print("电脑在设定时间必须处于开机（或睡眠唤醒）状态任务才会执行。")
    else:
        print("\n❌ 设置失败:")
        print(stderr.decode('utf-8'))

if __name__ == "__main__":
    setup_cron()
