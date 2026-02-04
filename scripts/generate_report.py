"""
报告生成模块
功能：生成Markdown格式的推荐报告，包含推荐理由和翻译
"""

import json
import os
import logging
from typing import List, Dict
from datetime import datetime
from zhipuai import ZhipuAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '../config/config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def call_zhipu_ai(prompt: str, model: str = "glm-4-flash") -> str:
    """调用智谱AI"""
    config = load_config()
    client = ZhipuAI(api_key=config['zhipu_api_key'])
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content


def generate_recommendation(topic: Dict) -> str:
    """
    生成话题推荐理由（不超过300字）
    
    Args:
        topic: 话题对象
    
    Returns:
        str: 推荐理由
    """
    logger.info(f"正在生成推荐理由: {topic['canonical_name']}")
    
    # 获取该话题的前3篇文章标题作为参考
    article_titles = [art['title'] for art in topic['articles'][:3]]
    
    prompt = f"""请为以下技术话题撰写一段公众号选题推荐理由（严格不超过300字）：

话题：{topic['canonical_name']}
类别：{topic['category']}
热力值：{topic['heat_score']}/100
相关文章数：{topic['total_mentions']}篇
平均讨论深度：{topic['avg_depth']:.2f}/1.0

代表性文章标题：
{chr(10).join(['- ' + title for title in article_titles])}

撰写要求：
1. 说明为什么这个话题值得关注（技术价值、行业意义）
2. 该话题目前的讨论热度和深度
3. 对公众号读者的价值（技术洞察、行业趋势、实战意义等）
4. 语气专业但易懂，适合科技媒体风格
5. **严格控制在300字以内**
6. 不要使用"本话题"、"该话题"等词汇，直接描述话题内容

注意：只返回推荐理由文本，不要包含"推荐理由："等标题。"""

    try:
        recommendation = call_zhipu_ai(prompt)
        
        # 确保不超过300字
        if len(recommendation) > 300:
            recommendation = recommendation[:297] + "..."
        
        return recommendation.strip()
    
    except Exception as e:
        logger.error(f"生成推荐理由失败: {e}")
        return f"{topic['canonical_name']}获得{topic['heat_score']}的高热力值，{topic['total_mentions']}篇文章深入讨论，值得关注。"


def translate_articles_batch(articles: List[Dict]) -> List[Dict]:
    """
    批量翻译文章标题和摘要
    
    Args:
        articles: 文章列表
    
    Returns:
        List[Dict]: 翻译后的文章列表
    """
    logger.info(f"正在批量翻译 {len(articles)} 篇文章...")
    
    # 构建输入
    articles_input = []
    for i, art in enumerate(articles):
        articles_input.append({
            'id': i,
            'title': art['title'],
            'summary': art.get('summary', '')[:500]  # 增加摘要长度供翻译参考
        })
    
    prompt = f"""请将以下{len(articles)}篇英文技术文章的标题和摘要翻译成中文。

翻译要求：
1. 保持专业术语的准确性（如LLM、API、GPU等可保留英文）
2. 标题要简洁有力
3. ❗摘要控制在200-300字，详细介绍文章核心内容、主要观点和技术细节
4. 语言流畅自然，符合中文科技媒体习惯

输入JSON：
{json.dumps(articles_input, ensure_ascii=False, indent=2)}

输出格式（JSON数组）：
[
  {{"id": 0, "title": "中文标题", "summary": "中文摘要（200-300字）"}},
  {{"id": 1, "title": "中文标题", "summary": "中文摘要（200-300字）"}}
]

只返回JSON数组，不要其他文字。"""

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
        
        translations = json.loads(response)
        
        # 合并翻译结果
        translated_articles = []
        for art, trans in zip(articles, translations):
            translated_articles.append({
                **art,
                'title_cn': trans.get('title', art['title']),
                'summary_cn': trans.get('summary', art.get('summary', ''))
            })
        
        logger.info(f"✓ 翻译完成")
        return translated_articles
    
    except Exception as e:
        logger.error(f"批量翻译失败: {e}")
        # 降级：返回原文
        return [{**art, 'title_cn': art['title'], 'summary_cn': art.get('summary', '')} 
                for art in articles]


def format_depth_stars(depth: float) -> str:
    """将讨论深度转换为星级表示"""
    stars = int(depth * 5)
    return '★' * stars + '☆' * (5 - stars)


def generate_topic_section(rank: int, topic: Dict, recommendation: str, articles: List[Dict]) -> str:
    """
    生成单个话题的Markdown段落
    
    Args:
        rank: 排名
        topic: 话题对象
        recommendation: 推荐理由
        articles: 翻译后的文章列表（最多5篇）
    
    Returns:
        str: Markdown段落
    """
    depth_stars = format_depth_stars(topic['avg_depth'])
    
    section = f"""### 🔥 话题{rank}：{topic['canonical_name']} [热力值: {topic['heat_score']}/100]

**分类**：{topic['category']} | **提及次数**：{topic['total_mentions']}篇 | **讨论深度**：{depth_stars}

**推荐理由**：

{recommendation}

**相关文章**：

"""
    
    # 添加文章列表
    for i, art in enumerate(articles, 1):
        # 判断是否是深度文章（depth > 0.7）
        depth_tag = "🔬 " if art.get('depth', 0) > 0.7 else ""
        
        # 格式化发布日期
        published = art.get('published', '')
        if published:
            try:
                from dateutil import parser as date_parser
                pub_date = date_parser.parse(published)
                published_str = pub_date.strftime('%Y-%m-%d %H:%M')
            except:
                published_str = published[:16] if len(published) > 16 else published
        else:
            published_str = '未知'
        
        # 获取标题（优先用中文翻译）
        title = art.get('title_cn', art['title'])
        link = art['link']
        
        # 获取摘要（增加字数到300）
        summary = art.get('summary_cn', art.get('summary', ''))[:300]
        
        section += f"""{i}. {depth_tag}**[{title}]({link})**  
   📰 来源：{art['source']} | 📅 发布：{published_str}  
   📝 {summary}

"""
    
    return section


def generate_report(top_topics: List[Dict], time_slot: str, date_str: str, total_articles: int):
    """
    生成完整的Markdown报告
    
    Args:
        top_topics: Top N话题列表
        time_slot: 时间段（早间/午间/晚间）
        date_str: 日期字符串
        total_articles: 总文章数
    """
    config = load_config()
    logger.info(f"开始生成 {time_slot} 推荐报告...")
    
    # 当前时间
    now = datetime.now().strftime('%H:%M')
    
    # 生成报告头部
    report_header = f"""## 📊 {time_slot}推荐 ({now}更新)

> 基于当日累计文章分析，截至{now}共监控到**{total_articles}篇**新文章

"""
    
    # 生成每个话题的段落
    sections = []
    
    for i, topic in enumerate(top_topics, 1):
        # 生成推荐理由
        recommendation = generate_recommendation(topic)
        
        # 选出Top 5文章（按depth排序）
        sorted_articles = sorted(
            topic['articles'],
            key=lambda x: x.get('depth', 0),
            reverse=True
        )[:config['output_config']['articles_per_topic']]
        
        # 翻译文章
        translated_articles = translate_articles_batch(sorted_articles)
        
        # 生成段落
        section = generate_topic_section(i, topic, recommendation, translated_articles)
        sections.append(section)
    
    # 组合完整报告
    full_report = report_header + '\n'.join(sections)
    
    # 写入到当天的报告文件（覆盖模式）
    write_daily_report(date_str, time_slot, full_report, total_articles, len(top_topics))
    
    logger.info(f"✅ {time_slot}报告生成完成！")


def write_daily_report(date_str: str, time_slot: str, content: str, 
                       total_articles: int, total_topics: int):
    """
    将报告内容写入当天的Markdown文件（覆盖模式）

    Args:
        date_str: 日期字符串
        time_slot: 时间段
        content: 报告内容
        total_articles: 总文章数
        total_topics: 总话题数
    """
    config = load_config()
    reports_dir = os.path.join(os.path.dirname(__file__), config['reports_dir'])
    os.makedirs(reports_dir, exist_ok=True)
    
    report_file = os.path.join(reports_dir, f'{date_str}.md')
    
    # 检查文件是否已存在
    if os.path.exists(report_file):
        # 文件已存在，需要追加
        with open(report_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # 找到最后一个总览部分之前
        if '## 📈 今日数据总览' in existing_content:
            # 移除旧的总览
            existing_content = existing_content.split('## 📈 今日数据总览')[0]
        
        # 追加新内容
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(existing_content)
            f.write(content)
            f.write("\n---\n\n")
    else:
        # 文件不存在，创建新文件
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"""# 技术博客话题监控 - {date_str}

---

""")
            f.write(content)
            f.write("\n---\n\n")
    
    # 更新总览（在文件末尾）
    update_daily_summary(report_file, date_str, time_slot, total_articles, total_topics)
    
    logger.info(f"报告已更新到: {report_file}")


def update_daily_summary(report_file: str, date_str: str, time_slot: str, 
                        total_articles: int, total_topics: int):
    """更新每日数据总览"""
    
    # 读取现有内容
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除旧的总览（如果存在）
    if '## 📈 今日数据总览' in content:
        content = content.split('## 📈 今日数据总览')[0]
    
    # 添加新的总览
    config = load_config()
    opml_path = os.path.join(os.path.dirname(__file__), config['opml_file'])
    
    # 统计RSS源数量
    from fetch_blogs import parse_opml_file
    rss_sources = parse_opml_file(opml_path)
    
    summary = f"""## 📈 今日数据总览

- **监控RSS源数量**：{len(rss_sources)}个
- **抓取文章总数**：{total_articles}篇
- **识别话题数**：{total_topics}个
- **生成报告时间**：{time_slot} {datetime.now().strftime('%H:%M')}

---

*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*  
*数据来源：{len(rss_sources)}个技术博客RSS源*  
*由 Blog Topic Monitor Skill 自动生成*
"""
    
    # 写回文件
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(content + summary)


if __name__ == '__main__':
    import sys
    from calculate_heat import get_top_topics
    
    # 获取参数
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    time_slot = sys.argv[2] if len(sys.argv) > 2 else '早间'
    
    # 加载热力值数据
    config = load_config()
    data_dir = os.path.join(os.path.dirname(__file__), config['data_dir'])
    heat_file = os.path.join(data_dir, 'processed', date_str, f'heat_scores_{time_slot}.json')
    
    with open(heat_file, 'r', encoding='utf-8') as f:
        heat_data = json.load(f)
    
    scored_topics = heat_data['topics']
    
    # 获取Top N（根据配置）
    top_n = config['output_config']['topics_per_report']
    top_topics = scored_topics[:top_n]
    
    print(f"将生成 {len(top_topics)} 个话题的推荐报告")
    
    # 计算总文章数
    from fetch_blogs import load_articles
    articles = load_articles(date_str)
    
    # 生成报告
    generate_report(top_topics, time_slot, date_str, len(articles))