"""
定时任务调度器
功能：在每天的9:30、15:30、20:30自动执行分析流程
"""

import os
import sys
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# 添加scripts目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 计算日志目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(PROJECT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

from fetch_blogs import fetch_all_articles
from analyze_topics import analyze_all_articles, cluster_topics, save_topics
from calculate_heat import calculate_all_heat_scores, save_heat_scores, get_top_topics
from generate_report import generate_report
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'scheduler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), '../config/config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_analysis_pipeline(time_slot: str):
    """
    执行完整的分析流程
    
    Args:
        time_slot: 时间段（早间/午间/晚间）
    """
    logger.info(f"{'='*60}")
    logger.info(f"开始执行 {time_slot} 分析任务")
    logger.info(f"{'='*60}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 步骤1：抓取RSS（过去24小时内的文章）
        logger.info(f"[1/5] 抓取RSS源（过去24小时）...")
        articles = fetch_all_articles(hours_ago=24)
        
        if not articles:
            logger.warning(f"{time_slot}：未抓取到任何文章，跳过本次分析")
            return
        
        logger.info(f"✓ 抓取到 {len(articles)} 篇文章")
        
        # 检查最小文章数阈值
        config = load_config()
        min_threshold = config['output_config']['min_articles_threshold']
        
        if len(articles) < min_threshold:
            logger.warning(f"{time_slot}：文章数({len(articles)})低于阈值({min_threshold})，将降低推荐标准")
        
        # 步骤2：话题提取与聚类
        logger.info(f"[2/5] 分析文章话题...")
        analyzed_articles = analyze_all_articles(articles)
        
        logger.info(f"[3/5] 话题聚类...")
        topics = cluster_topics(analyzed_articles)
        
        if not topics:
            logger.warning(f"{time_slot}：未识别到任何话题，跳过本次推荐")
            return
        
        logger.info(f"✓ 识别出 {len(topics)} 个话题")
        
        # 保存话题
        save_topics(topics, today)
        
        # 步骤3：计算热力值
        logger.info(f"[4/5] 计算热力值...")
        scored_topics = calculate_all_heat_scores(topics)
        
        # 保存热力值
        save_heat_scores(scored_topics, today, time_slot)
        
        # 步骤4：生成报告
        logger.info(f"[5/5] 生成推荐报告...")
        
        # 根据话题数量调整推荐数
        topics_per_report = min(config['output_config']['topics_per_report'], len(scored_topics))
        top_topics = scored_topics[:topics_per_report]
        
        generate_report(top_topics, time_slot, today, len(articles))
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ {time_slot}任务完成！推荐了 {len(top_topics)} 个话题")
        logger.info(f"{'='*60}\n")
    
    except Exception as e:
        logger.error(f"❌ {time_slot}任务执行失败: {e}", exc_info=True)


def job_morning():
    """早间任务：9:30"""
    run_analysis_pipeline('早间')


def job_afternoon():
    """午间任务：15:30"""
    run_analysis_pipeline('午间')


def job_evening():
    """晚间任务：20:30"""
    run_analysis_pipeline('晚间')


def start_scheduler():
    """启动定时调度器"""
    config = load_config()
    timezone = pytz.timezone(config['timezone'])
    
    # 创建调度器
    scheduler = BlockingScheduler(timezone=timezone)
    
    # 解析时间配置
    morning_time = config['schedule']['morning']  # "09:30"
    afternoon_time = config['schedule']['afternoon']  # "15:30"
    evening_time = config['schedule']['evening']  # "20:30"
    
    morning_hour, morning_minute = map(int, morning_time.split(':'))
    afternoon_hour, afternoon_minute = map(int, afternoon_time.split(':'))
    evening_hour, evening_minute = map(int, evening_time.split(':'))
    
    # 注册定时任务
    scheduler.add_job(
        job_morning,
        CronTrigger(hour=morning_hour, minute=morning_minute, timezone=timezone),
        id='morning_job',
        name='早间分析',
        replace_existing=True
    )
    
    scheduler.add_job(
        job_afternoon,
        CronTrigger(hour=afternoon_hour, minute=afternoon_minute, timezone=timezone),
        id='afternoon_job',
        name='午间分析',
        replace_existing=True
    )
    
    scheduler.add_job(
        job_evening,
        CronTrigger(hour=evening_hour, minute=evening_minute, timezone=timezone),
        id='evening_job',
        name='晚间分析',
        replace_existing=True
    )
    
    logger.info("="*60)
    logger.info("🚀 Blog Topic Monitor 调度器启动成功！")
    logger.info("="*60)
    logger.info(f"早间任务: 每天 {morning_time}")
    logger.info(f"午间任务: 每天 {afternoon_time}")
    logger.info(f"晚间任务: 每天 {evening_time}")
    logger.info(f"时区: {config['timezone']}")
    logger.info("="*60)
    logger.info("\n等待定时任务触发...\n")
    
    # 启动调度器
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n调度器已停止")


if __name__ == '__main__':
    start_scheduler()
