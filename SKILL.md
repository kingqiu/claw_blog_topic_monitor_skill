---
description: 自动化技术博客话题监控，每天推荐3个最热门话题
---

# Blog Topic Monitor Skill

## 概述

自动化监控100+优质技术博客，使用AI分析话题热度，每天在3个时间段（9:30、15:30、20:30）自动生成中文推荐报告，为公众号内容创作提供选题灵感。

## 核心能力

1. **RSS源监控**：自动抓取BlogFeeds.md中配置的所有技术博客
2. **AI话题提取**：使用智谱GLM-4-Flash分析文章主题
3. **语义聚类**：将相似话题合并，避免重复推荐
4. **热力值计算**：综合多维度指标评估话题热度
5. **智能翻译**：批量翻译英文文章为中文
6. **自动化报告**：生成结构化Markdown推荐文档

## 使用方法

### 首次配置

1. **安装依赖**：
```bash
cd blog-topic-monitor-skill
pip install -r requirements.txt
```

2. **配置API密钥**：
编辑 `config/config.json`，填入智谱AI API密钥

3. **测试运行**：
```bash
python run.py --run morning
```

### 日常使用

**启动定时服务**（推荐）：
```bash
python run.py --daemon
```

服务将在每天9:30、15:30、20:30自动执行分析，生成报告保存在 `data/reports/` 目录。

**手动触发**：
```bash
python run.py --run morning      # 早间
python run.py --run afternoon    # 午间
python run.py --run evening      # 晚间
```

### 查看报告

报告文件：`data/reports/YYYY-MM-DD.md`

每个话题包含：
- 热力值评分（0-100）
- 推荐理由（300字以内）
- 5篇相关文章（中文标题、链接、简介）

## 配置说明

### RSS源管理

编辑 `../BlogFeeds.md`（OPML格式），可添加或删除RSS源。

### 类别配置

编辑 `config/categories.json`，可自定义类别及权重：

- **技术探讨**：权重1.0（最高优先级）
- **趋势观点**：权重1.0（最高优先级）
- **实战技巧**：权重0.7（次优先）
- **行业动态**：权重0.5（最低优先）

### 热力值算法

默认权重配置（可在 `config/config.json` 中修改）：

- **提及度**：60%（话题被多少篇文章讨论）
- **深度度**：30%（文章对话题的讨论深度）
- **类别权重**：10%（基于上述类别优先级）

公式：`热力值 = min(文章数/10 * 60, 60) + 平均深度 * 30 + 类别权重 * 10`

### 定时任务

可在 `config/config.json` 中修改执行时间：

```json
{
  "schedule": {
    "morning": "09:30",
    "afternoon": "15:30",
    "evening": "20:30"
  }
}
```

## 技术架构

**数据流**：
```
RSS抓取 → 话题提取 → 语义聚类 → 热力值计算 → 报告生成
```

**核心模块**：
- `fetch_blogs.py`：RSS抓取与解析
- `analyze_topics.py`：AI话题分析
- `calculate_heat.py`：热力值计算
- `generate_report.py`：报告生成
- `scheduler.py`：定时调度

**AI能力**：
- 使用智谱GLM-4-Flash模型
- 话题提取 + 语义聚类 + 翻译

## 输出示例

```markdown
### 🔥 话题1：大模型推理优化 [热力值: 83.5/100]

**分类**：技术探讨 | **提及次数**：8篇 | **讨论深度**：★★★★☆

**推荐理由**：
大模型推理优化成为本周AI领域最热门的技术话题，8篇顶级博客深入探讨...

**相关文章**：
1. **[深度] 大模型推理的量化革命：从INT8到INT4**  
   📰 来源：OpenAI Blog  
   🔗 链接：https://...  
   📝 简介：详细介绍了最新的INT4量化技术...
```

## 常见问题

### 如何添加新的RSS源？

编辑 `../BlogFeeds.md`，在OPML文件中添加新的 `<outline>` 标签。

### 如何调整推荐数量？

编辑 `config/config.json`：

```json
{
  "output_config": {
    "topics_per_report": 3,
    "articles_per_topic": 5
  }
}
```

### 文章数量不足时会怎样？

系统会自动降级：
- 文章 < 5篇时，降低推荐标准
- 无话题时，跳过本次推荐
- 话题 < 3个时，推荐全部话题

## 依赖项

- Python 3.8+
- feedparser
- zhipuai
- apscheduler
- python-dateutil

## 版本

**当前版本**：1.0.0  
**创建日期**：2026-02-03

---

*这是一个基于AI的自动化内容推荐工具，旨在提高技术媒体的内容生产效率*
