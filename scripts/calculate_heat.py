"""
热力值计算模块
功能：根据提及度、深度、类别权重计算话题热力值
"""

import json
import os
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '../config/config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_categories() -> dict:
    """加载类别配置"""
    categories_path = os.path.join(os.path.dirname(__file__), '../config/categories.json')
    with open(categories_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_heat_score(topic_cluster: Dict) -> float:
    """
    计算单个话题的热力值（100分制）
    
    公式：热力值 = 提及度得分(60%) + 深度得分(30%) + 类别加权(10%)
    
    Args:
        topic_cluster: 话题聚类对象
    
    Returns:
        float: 热力值（0-100）
    """
    config = load_config()
    categories_config = load_categories()
    heat_config = config['heat_config']
    
    # 1. 提及度得分（基于文章数量，10篇=满分60）
    mention_count = topic_cluster['total_mentions']
    mention_score = min(mention_count / 10.0 * 60, 60)
    
    # 2. 深度得分（基于平均讨论深度，最高30分）
    avg_depth = topic_cluster['avg_depth']
    depth_score = avg_depth * 30
    
    # 3. 类别权重加分（基于配置的优先级权重）
    category = topic_cluster.get('category', '行业动态')
    
    # 从配置中查找类别权重
    category_weight = 0.5  # 默认权重
    for cat in categories_config['categories']:
        if cat['name'] == category:
            category_weight = cat['priority_weight']
            break
    
    category_bonus = category_weight * 10
    
    # 总分
    heat_score = mention_score + depth_score + category_bonus
    
    return round(heat_score, 1)


def calculate_all_heat_scores(topic_clusters: List[Dict]) -> List[Dict]:
    """
    计算所有话题的热力值并排序
    
    Args:
        topic_clusters: 话题聚类列表
    
    Returns:
        List[Dict]: 带有热力值的话题列表，按热力值降序排序
    """
    logger.info(f"开始计算 {len(topic_clusters)} 个话题的热力值...")
    
    scored_topics = []
    
    for cluster in topic_clusters:
        heat_score = calculate_heat_score(cluster)
        
        scored_topic = {
            **cluster,
            'heat_score': heat_score
        }
        
        scored_topics.append(scored_topic)
        
        logger.info(f"  {cluster['canonical_name']}: {heat_score}/100 "
                   f"(提及{cluster['total_mentions']}篇, 深度{cluster['avg_depth']:.2f})")
    
    # 按热力值降序排序
    scored_topics.sort(key=lambda x: x['heat_score'], reverse=True)
    
    logger.info(f"✅ 热力值计算完成")
    return scored_topics


def get_top_topics(scored_topics: List[Dict], top_n: int = 3) -> List[Dict]:
    """
    获取热力值Top N的话题
    
    Args:
        scored_topics: 带热力值的话题列表
        top_n: 返回前N个
    
    Returns:
        List[Dict]: Top N话题
    """
    return scored_topics[:top_n]


def save_heat_scores(scored_topics: List[Dict], date_str: str, time_slot: str):
    """保存热力值结果"""
    config = load_config()
    data_dir = os.path.join(os.path.dirname(__file__), config['data_dir'])
    
    date_dir = os.path.join(data_dir, 'processed', date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    output_file = os.path.join(date_dir, f'heat_scores_{time_slot}.json')
    
    # 添加排名
    for i, topic in enumerate(scored_topics, 1):
        topic['rank'] = i
    
    result = {
        'timestamp': f'{date_str} {time_slot}',
        'total_topics': len(scored_topics),
        'topics': scored_topics
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"热力值已保存到: {output_file}")


if __name__ == '__main__':
    import sys
    from datetime import datetime
    
    # 获取参数
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    time_slot = sys.argv[2] if len(sys.argv) > 2 else '早间'
    
    # 加载话题聚类
    config = load_config()
    data_dir = os.path.join(os.path.dirname(__file__), config['data_dir'])
    topics_file = os.path.join(data_dir, 'processed', date_str, 'topics.json')
    
    with open(topics_file, 'r', encoding='utf-8') as f:
        topics_data = json.load(f)
    
    topic_clusters = topics_data['clusters']
    print(f"加载了 {len(topic_clusters)} 个话题聚类")
    
    # 计算热力值
    scored_topics = calculate_all_heat_scores(topic_clusters)
    
    # 显示Top 10
    print(f"\n🔥 热力值 Top 10：")
    for topic in scored_topics[:10]:
        print(f"  {topic['rank']}. {topic['canonical_name']}: {topic['heat_score']}/100")
    
    # 保存
    save_heat_scores(scored_topics, date_str, time_slot)
