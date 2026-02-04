"""
Blog Topic Monitor - 主入口程序
功能：启动监控服务或手动触发分析
"""

import os
import sys
import argparse
from datetime import datetime

# 添加scripts目录到路径
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
sys.path.insert(0, scripts_dir)


def main():
    parser = argparse.ArgumentParser(
        description='Blog Topic Monitor - 技术博客话题监控工具'
    )
    
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='后台运行定时任务（每天9:30、15:30、20:30自动执行）'
    )
    
    parser.add_argument(
        '--run',
        choices=['morning', 'afternoon', 'evening'],
        help='手动执行指定时间段的分析'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='指定日期（格式: YYYY-MM-DD），默认为今天'
    )
    
    args = parser.parse_args()
    
    if args.daemon:
        # 启动定时任务
        print("🚀 启动Blog Topic Monitor定时服务...")
        from scheduler import start_scheduler
        start_scheduler()
    
    elif args.run:
        # 手动执行
        time_slot_map = {
            'morning': '早间',
            'afternoon': '午间',
            'evening': '晚间'
        }
        time_slot = time_slot_map[args.run]
        
        print(f"🔍 手动执行 {time_slot} 分析...")
        from scheduler import run_analysis_pipeline
        run_analysis_pipeline(time_slot)
        print(f"✅ {time_slot}分析完成！")
    
    else:
        # 显示帮助信息
        parser.print_help()
        print("\n示例:")
        print("  python run.py --daemon              # 启动定时服务")
        print("  python run.py --run morning         # 手动执行早间分析")
        print("  python run.py --run evening         # 手动执行晚间分析")


if __name__ == '__main__':
    main()
