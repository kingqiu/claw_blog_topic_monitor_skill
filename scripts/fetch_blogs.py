"""
RSS源抓取模块
功能：解析OPML文件，抓取所有RSS源的文章，过滤过去24小时内发布的内容
"""

import feedparser
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
import xml.etree.ElementTree as ET
import requests
from typing import List, Dict, Optional
import time
import pytz

# 计算日志目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(PROJECT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'fetch_blogs.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '../config/config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_opml_file(opml_path: str) -> List[Dict[str, str]]:
    """
    解析OPML文件，提取所有RSS源
    
    Args:
        opml_path: OPML文件路径
    
    Returns:
        List[Dict]: RSS源列表，每个包含 {title, xmlUrl, htmlUrl}
    """
    logger.info(f"解析OPML文件: {opml_path}")
    
    try:
        tree = ET.parse(opml_path)
        root = tree.getroot()
        
        rss_sources = []
        # 查找所有 outline 标签，type="rss" 的条目
        for outline in root.findall(".//outline[@type='rss']"):
            source = {
                'title': outline.get('title', outline.get('text', 'Unknown')),
                'xmlUrl': outline.get('xmlUrl'),
                'htmlUrl': outline.get('htmlUrl', '')
            }
            if source['xmlUrl']:
                rss_sources.append(source)
        
        logger.info(f"成功解析 {len(rss_sources)} 个RSS源")
        return rss_sources
    
    except Exception as e:
        logger.error(f"解析OPML文件失败: {e}")
        return []


def parse_published_date(entry) -> Optional[datetime]:
    """
    解析文章发布时间，返回带时区的datetime对象
    支持多种日期格式
    """
    # 尝试多种日期字段
    date_fields = ['published', 'updated', 'created']
    
    for field in date_fields:
        if hasattr(entry, field):
            try:
                date_str = getattr(entry, field)
                parsed = date_parser.parse(date_str)
                # 如果没有时区信息，假设为UTC
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except:
                continue
    
    # 如果有 published_parsed 或 updated_parsed
    for field in ['published_parsed', 'updated_parsed']:
        if hasattr(entry, field):
            try:
                time_struct = getattr(entry, field)
                if time_struct:
                    # struct_time 转 datetime，假设为UTC
                    dt = datetime.fromtimestamp(time.mktime(time_struct), tz=timezone.utc)
                    return dt
            except:
                continue
    
    return None


def fetch_rss_source(rss_url: str, title: str, start_time: datetime, end_time: datetime, retries: int = 2) -> List[Dict]:
    """
    抓取单个RSS源的文章
    
    Args:
        rss_url: RSS URL
        title: 源名称
        start_time: 时间窗口开始（24小时前）
        end_time: 时间窗口结束（当前时间）
        retries: 重试次数
    
    Returns:
        List[Dict]: 文章列表
    """
    articles = []
    
    for attempt in range(retries):
        try:
            logger.debug(f"正在抓取: {title} ({rss_url})")
            
            # 设置超时和User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; BlogTopicMonitor/1.0)'
            }
            
            # 使用 requests 获取 RSS 内容，设置 15 秒超时
            response = requests.get(rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 传给 feedparser 解析
            feed = feedparser.parse(response.content)
            
            # 检查是否成功
            if feed.bozo and not feed.entries:
                logger.warning(f"RSS源可能有问题: {title}")
                continue
            
            # 遍历所有条目
            for entry in feed.entries:
                published_date = parse_published_date(entry)
                
                # 如果无法解析日期，跳过
                if not published_date:
                    continue
                
                # 只保留时间窗口内的文章（过去24小时）
                if not (start_time <= published_date <= end_time):
                    continue
                
                # 提取文章内容
                content = ''
                if hasattr(entry, 'content'):
                    content = entry.content[0].value if entry.content else ''
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                
                article = {
                    'title': entry.title if hasattr(entry, 'title') else 'Untitled',
                    'link': entry.link if hasattr(entry, 'link') else '',
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'content': content[:2000],  # 限制长度，只取前2000字符
                    'published': published_date.isoformat(),
                    'source': title,
                    'source_url': feed.feed.get('link', '') if hasattr(feed, 'feed') else '',
                    'word_count': len(content)
                }
                
                articles.append(article)
                logger.debug(f"  - 找到文章: {article['title']}")
            
            if articles:
                logger.info(f"✓ {title}: 找到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.warning(f"抓取失败 ({attempt + 1}/{retries}): {title} - {e}")
            if attempt < retries - 1:
                time.sleep(2)  # 等待2秒后重试
    
    logger.error(f"✗ {title}: 抓取失败")
    return []


def fetch_all_articles(hours_ago: int = 24) -> List[Dict]:
    """
    抓取所有RSS源的文章（过去N小时内发布的）
    
    Args:
        hours_ago: 时间窗口（小时），默认24小时
    
    Returns:
        List[Dict]: 所有文章列表
    """
    config = load_config()
    
    # 计算时间窗口
    tz = pytz.timezone(config.get('timezone', 'Asia/Shanghai'))
    now = datetime.now(tz)
    end_time = now
    start_time = now - timedelta(hours=hours_ago)
    
    logger.info(f"="*60)
    logger.info(f"开始抓取文章")
    logger.info(f"时间窗口: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"="*60)
    
    # 解析OPML文件
    opml_path = os.path.join(os.path.dirname(__file__), config['opml_file'])
    rss_sources = parse_opml_file(opml_path)
    
    if not rss_sources:
        logger.error("未找到任何RSS源")
        return []
    
    # 抓取所有源
    all_articles = []
    success_count = 0
    
    for i, source in enumerate(rss_sources, 1):
        logger.info(f"进度: {i}/{len(rss_sources)} - {source['title']}")
        articles = fetch_rss_source(
            source['xmlUrl'],
            source['title'],
            start_time,
            end_time
        )
        all_articles.extend(articles)
        if articles:
            success_count += 1
    
    logger.info(f"="*60)
    logger.info(f"抓取完成！")
    logger.info(f"  - 有效源: {success_count}/{len(rss_sources)} 个")
    logger.info(f"  - 总文章: {len(all_articles)} 篇")
    logger.info(f"="*60)
    
    # 保存到JSON文件（使用当天日期作为文件名）
    today_str = now.strftime('%Y-%m-%d')
    save_articles(all_articles, today_str, start_time, end_time)
    
    return all_articles


def save_articles(articles: List[Dict], date_str: str, start_time: datetime, end_time: datetime):
    """
    保存文章到JSON文件
    
    Args:
        articles: 文章列表
        date_str: 日期字符串（YYYY-MM-DD）
        start_time: 时间窗口开始
        end_time: 时间窗口结束
    """
    config = load_config()
    data_dir = os.path.join(os.path.dirname(__file__), config['data_dir'])
    
    # 创建日期目录
    date_dir = os.path.join(data_dir, 'raw', date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = end_time.strftime('%H%M')
    output_file = os.path.join(date_dir, f'articles_{timestamp}.json')
    
    # 添加元数据
    data = {
        'metadata': {
            'fetch_time': end_time.isoformat(),
            'time_window_start': start_time.isoformat(),
            'time_window_end': end_time.isoformat(),
            'hours_range': 24,
            'total_articles': len(articles)
        },
        'articles': articles
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"文章已保存到: {output_file}")


def load_articles(date_str: str, time_slot: str = None) -> List[Dict]:
    """
    加载指定日期的文章
    
    Args:
        date_str: 日期字符串（YYYY-MM-DD）
        time_slot: 时间段标识（可选，如 "0930"）
    
    Returns:
        List[Dict]: 文章列表
    """
    config = load_config()
    data_dir = os.path.join(os.path.dirname(__file__), config['data_dir'])
    
    date_dir = os.path.join(data_dir, 'raw', date_str)
    
    if not os.path.exists(date_dir):
        logger.warning(f"数据目录不存在: {date_dir}")
        return []
    
    # 如果指定了时间段，找对应文件
    if time_slot:
        input_file = os.path.join(date_dir, f'articles_{time_slot}.json')
        if os.path.exists(input_file):
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('articles', [])
    
    # 否则找最新的文件
    files = [f for f in os.listdir(date_dir) if f.startswith('articles_') and f.endswith('.json')]
    if not files:
        logger.warning(f"未找到文章文件: {date_dir}")
        return []
    
    # 按时间戳排序，取最新
    files.sort(reverse=True)
    latest_file = os.path.join(date_dir, files[0])
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('articles', [])


if __name__ == '__main__':
    import sys
    
    # 支持命令行参数指定时间窗口（小时）
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    
    articles = fetch_all_articles(hours_ago=hours)
    print(f"\n✅ 抓取完成：过去{hours}小时内共 {len(articles)} 篇文章")
