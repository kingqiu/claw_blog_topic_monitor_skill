"""
话题分析与聚类模块
功能：使用智谱AI提取文章主题，进行话题聚类
"""

import json
import os
import logging
from typing import List, Dict
from zhipuai import ZhipuAI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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


def call_zhipu_ai(prompt: str, model: str = "glm-4-flash") -> str:
    """
    调用智谱AI API
    
    Args:
        prompt: 提示词
        model: 模型名称
    
    Returns:
        str: AI响应内容
    """
    config = load_config()
    api_key = config.get('zhipu_api_key')
    
    if not api_key:
        raise ValueError("智谱AI API Key未配置，请在config/config.json中设置")
    
    client = ZhipuAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"调用智谱AI失败: {e}")
        raise


def extract_topics_from_article(article: Dict) -> Dict:
    """
    从单篇文章中提取主题和分类
    
    Args:
        article: 文章字典
    
    Returns:
        Dict: 包含主题、分类、关键词和讨论深度的字典
    """
    logger.info(f"分析文章: {article['title'][:50]}...")
    
    # 加载类别配置
    categories_config = load_categories()
    category_names = [cat['name'] for cat in categories_config['categories']]
    
    # 构建Prompt
    prompt = f"""请分析以下技术博客文章，提取关键信息：

标题：{article['title']}
来源：{article['source']}
摘要：{article.get('summary', '')[:500]}
内容片段：{article.get('content', '')[:1000]}

请以JSON格式返回：
1. main_topics: 文章讨论的1-3个主要话题
   ⚠️ 重要：话题名称必须**具体且有信息量**（8-15个中文字）
   - 正确示例：「OpenAI发布Codex桌面应用」「开源项目运营成本分析」「AI生成内容与人类创作本质区别」
   - 错误示例：「AI发展」「成本分析」「产品发布」（太笼统！）
   - 话题名称应包含：具体公司/项目名 + 具体事件/观点
2. category: 分类（从以下选项中选择一个：{', '.join(category_names)}）
3. keywords: 5-10个关键词（中文）
4. discussion_depth: 对每个主要话题的讨论深度评分字典（0-1，1表示深入分析）

注意：
- 如果文章与AI领域无关，main_topics返回空数组
- discussion_depth的key要与main_topics中的话题完全一致

示例输出：
{{
  "main_topics": ["大模型推理延迟优化实践", "INT8量化对精度的影响"],
  "category": "技术探讨",
  "keywords": ["LLM", "INT8", "量化", "推理加速", "性能优化"],
  "discussion_depth": {{"大模型推理延迟优化实践": 0.9, "INT8量化对精度的影响": 0.7}}
}}

请只返回JSON，不要其他解释文字。"""

    try:
        response = call_zhipu_ai(prompt)
        
        # 清理响应，提取JSON部分
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        result = json.loads(response)
        
        # 验证结果
        if 'main_topics' not in result:
            result['main_topics'] = []
        if 'category' not in result:
            result['category'] = categories_config['default_category']
        if 'discussion_depth' not in result:
            result['discussion_depth'] = {}
        
        logger.info(f"  ✓ 提取到 {len(result['main_topics'])} 个话题")
        return result
    
    except Exception as e:
        logger.error(f"  ✗ 提取失败: {e}")
        # 返回空结果
        return {
            'main_topics': [],
            'category': categories_config['default_category'],
            'keywords': [],
            'discussion_depth': {}
        }


def analyze_all_articles(articles: List[Dict]) -> List[Dict]:
    """
    分析所有文章，提取主题
    
    Args:
        articles: 文章列表
    
    Returns:
        List[Dict]: 带有主题分析的文章列表
    """
    logger.info(f"开始分析 {len(articles)} 篇文章...")
    
    analyzed_articles = []
    
    for i, article in enumerate(articles, 1):
        logger.info(f"进度: {i}/{len(articles)}")
        
        try:
            analysis = extract_topics_from_article(article)
            
            # 合并到文章对象
            article_with_topics = {
                **article,
                'main_topics': analysis['main_topics'],
                'category': analysis['category'],
                'keywords': analysis.get('keywords', []),
                'discussion_depth': analysis.get('discussion_depth', {})
            }
            
            analyzed_articles.append(article_with_topics)
        
        except Exception as e:
            logger.error(f"分析文章失败: {article['title'][:50]} - {e}")
            # 即使失败也添加，但标记为无主题
            article['main_topics'] = []
            analyzed_articles.append(article)
    
    logger.info(f"✅ 分析完成！共 {len(analyzed_articles)} 篇文章")
    return analyzed_articles


def cluster_topics(articles_with_topics: List[Dict]) -> List[Dict]:
    """
    聚合所有文章的话题，合并相似话题
    
    Args:
        articles_with_topics: 带有主题分析的文章列表
    
    Returns:
        List[Dict]: 话题聚类列表
    """
    logger.info("开始话题聚类...")
    
    # 收集所有话题
    all_topics = []
    for article in articles_with_topics:
        for topic in article.get('main_topics', []):
            if not topic:  # 跳过空话题
                continue
            
            all_topics.append({
                'topic': topic,
                'article': article,
                'depth': article.get('discussion_depth', {}).get(topic, 0.5)
            })
    
    if not all_topics:
        logger.warning("没有找到任何话题")
        return []
    
    logger.info(f"共收集到 {len(all_topics)} 个话题实例")
    
    # 提取唯一话题列表
    unique_topics = list(set([t['topic'] for t in all_topics]))
    
    logger.info(f"去重后有 {len(unique_topics)} 个不同话题")
    
    # 使用AI进行语义聚类
    prompt = f"""以下是从多篇技术博客中提取的话题列表（共{len(unique_topics)}个）：

{json.dumps(unique_topics, ensure_ascii=False, indent=2)}

请将语义相似的话题合并成聚类。合并规则：
1. 只合并**高度相关且语义相似**的话题
2. 不要过度合并，保持话题的区分度
3. ⚠️ 重要：canonical_name 必须是**具体的话题名称**，而不是宽泛的分类！
   - 正确示例："OpenAI发布Codex应用"、"供应链安全漏洞攻击"、"AI社交网络兴起"
   - 错误示例："人工智能"、"安全漏洞"、"产品发布" （这些太宽泛！）
4. 如果某个话题很独特，可以单独成为一个聚类
5. category 是分类（如技术探讨、行业动态），但 canonical_name 是具体话题

示例：
- "大模型推理优化" 和 "LLM推理加速" 应合并为 canonical_name="大模型推理性能优化"
- "GPT-5发布" 和 "Claude 4上线" 是不同话题，不能合并

返回格式（JSON数组）：
[
  {{
    "canonical_name": "大模型推理性能优化",
    "merged_topics": ["大模型推理优化", "LLM推理加速", "推理性能提升"],
    "category": "技术探讨"
  }},
  {{
    "canonical_name": "GPT-5正式发布与用户反响",
    "merged_topics": ["GPT-5发布", "GPT-5消息"],
    "category": "行业动态"
  }}
]

请只返回JSON数组，不要其他文字。"""

    try:
        response = call_zhipu_ai(prompt)
        
        # 清理响应
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        clusters_raw = json.loads(response)
        
        # 为每个聚类添加关联文章
        # ⚠️ 重要：一篇文章只能属于一个聚类，避免重复
        clusters = []
        assigned_articles = set()  # 全局跟踪已分配的文章链接

        for cluster in clusters_raw:
            canonical_name = cluster['canonical_name']
            merged_topics = cluster['merged_topics']

            # 找到所有属于这个聚类的文章（但排除已分配的）
            cluster_articles = []
            depths = []

            for topic_instance in all_topics:
                # 如果这篇文章已经分配给其他聚类，跳过
                if topic_instance['article']['link'] in assigned_articles:
                    continue

                if topic_instance['topic'] in merged_topics:
                    cluster_articles.append({
                        'title': topic_instance['article']['title'],
                        'link': topic_instance['article']['link'],
                        'source': topic_instance['article']['source'],
                        'summary': topic_instance['article'].get('summary', ''),
                        'content': topic_instance['article'].get('content', ''),
                        'depth': topic_instance['depth'],
                        'published': topic_instance['article'].get('published', ''),
                        'category': topic_instance['article'].get('category', '')
                    })
                    depths.append(topic_instance['depth'])
                    # 标记这篇文章为已分配
                    assigned_articles.add(topic_instance['article']['link'])

            # 只有当聚类有文章时才添加
            if cluster_articles:
                clusters.append({
                    'canonical_name': canonical_name,
                    'category': cluster.get('category', '行业动态'),
                    'articles': cluster_articles,
                    'total_mentions': len(cluster_articles),
                    'avg_depth': sum(depths) / len(depths) if depths else 0.5
                })
        
        logger.info(f"✅ 聚类完成！共 {len(clusters)} 个话题聚类")
        return clusters
    
    except Exception as e:
        logger.error(f"话题聚类失败: {e}")
        # 降级方案：不聚类，每个话题独立
        # ⚠️ 重要：同样需要确保一篇文章只属于一个聚类
        logger.warning("使用降级方案：不进行聚类")

        clusters = {}
        assigned_articles = {}  # 文章链接 -> 话题名称（第一个分配的话题）

        for topic_instance in all_topics:
            topic_name = topic_instance['topic']
            article_link = topic_instance['article']['link']

            # 如果这篇文章已经分配给其他话题，跳过
            if article_link in assigned_articles:
                continue

            # 记录这篇文章分配给当前话题
            assigned_articles[article_link] = topic_name

            if topic_name not in clusters:
                clusters[topic_name] = {
                    'canonical_name': topic_name,
                    'category': topic_instance['article'].get('category', '行业动态'),
                    'articles': [],
                    'depths': []
                }

            clusters[topic_name]['articles'].append({
                'title': topic_instance['article']['title'],
                'link': topic_instance['article']['link'],
                'source': topic_instance['article']['source'],
                'summary': topic_instance['article'].get('summary', ''),
                'content': topic_instance['article'].get('content', ''),
                'depth': topic_instance['depth'],
                'published': topic_instance['article'].get('published', ''),
                'category': topic_instance['article'].get('category', '')
            })
            clusters[topic_name]['depths'].append(topic_instance['depth'])

        result = []
        for cluster in clusters.values():
            result.append({
                'canonical_name': cluster['canonical_name'],
                'category': cluster['category'],
                'articles': cluster['articles'],
                'total_mentions': len(cluster['articles']),
                'avg_depth': sum(cluster['depths']) / len(cluster['depths']) if cluster['depths'] else 0.5
            })

        return result


def save_topics(topics: List[Dict], date_str: str):
    """保存话题聚类结果"""
    config = load_config()
    data_dir = os.path.join(os.path.dirname(__file__), config['data_dir'])
    
    date_dir = os.path.join(data_dir, 'processed', date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    output_file = os.path.join(date_dir, 'topics.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'clusters': topics}, f, ensure_ascii=False, indent=2)
    
    logger.info(f"话题已保存到: {output_file}")


if __name__ == '__main__':
    import sys
    from fetch_blogs import load_articles
    from datetime import datetime
    
    # 获取日期参数
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    
    # 加载文章
    articles = load_articles(date_str)
    print(f"加载了 {len(articles)} 篇文章")
    
    # 分析文章
    analyzed_articles = analyze_all_articles(articles)
    
    # 话题聚类
    topics = cluster_topics(analyzed_articles)
    print(f"\n✅ 识别出 {len(topics)} 个话题聚类")
    
    # 保存结果
    save_topics(topics, date_str)
