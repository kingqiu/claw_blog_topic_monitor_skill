# Blog Topic Monitor Skill

自动化技术博客话题监控工具，每天监控100+优质技术博客，基于AI智能分析推荐最热门的3个话题，为公众号内容创作提供选题灵感。

## ✨ 核心功能

- **📡 RSS源监控**：自动抓取100+优质技术博客的最新文章
- **🤖 AI话题分析**：使用智谱GLM-4-Flash提取文章主题并进行语义聚类
- **🔥 热力值算法**：综合提及度(60%)、讨论深度(30%)、类别权重(10%)计算话题热度
- **📝 智能推荐**：每天3个时间段(9:30/15:30/20:30)自动生成中文推荐报告
- **🌐 批量翻译**：自动将英文文章标题和摘要翻译成中文
- **⚙️ 灵活配置**：类别定义、权重参数、定时时间均可通过配置文件调整

## 📋 目录结构

```
blog-topic-monitor-skill/
├── config/
│   ├── config.json          # 主配置文件（API密钥、定时时间等）
│   └── categories.json      # 类别配置（可自定义类别和权重）
├── scripts/
│   ├── fetch_blogs.py       # RSS抓取模块
│   ├── analyze_topics.py    # 话题分析与聚类
│   ├── calculate_heat.py    # 热力值计算
│   ├── generate_report.py   # 报告生成
│   └── scheduler.py         # 定时调度器
├── data/
│   ├── raw/                 # 原始RSS数据
│   ├── processed/           # 处理后的话题数据
│   └── reports/             # 每日推荐报告（Markdown）
├── logs/                    # 运行日志
├── run.py                   # 主入口程序
├── requirements.txt         # Python依赖
└── README.md                # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd blog-topic-monitor-skill
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `config/config.json`，填入智谱AI API密钥：

```json
{
  "zhipu_api_key": "your_api_key_here",
  ...
}
```

### 3. 运行测试

手动执行一次分析，验证功能：

```bash
# 手动执行早间分析
python run.py --run morning
```

### 4. 启动定时服务

```bash
# 后台运行（每天自动执行3次）
python run.py --daemon
```

## 📊 输出示例

每天生成一个Markdown报告文件 `data/reports/YYYY-MM-DD.md`，包含：

- **3个时间段的推荐**（早间9:30、午间15:30、晚间20:30）
- 每个话题包含：
  - 🔥 热力值评分（0-100）
  - 📝 推荐理由（不超过300字）
  - 📚 5篇相关文章（中文标题、链接、简介）
  - 📊 讨论深度（星级表示）

示例片段：

```markdown
### 🔥 话题1：大模型推理优化 [热力值: 83.5/100]

**分类**：技术探讨 | **提及次数**：8篇 | **讨论深度**：★★★★☆

**推荐理由**：
大模型推理优化成为本周AI领域最热门的技术话题，8篇顶级博客深入探讨了这一方向...

**相关文章**：
1. **[深度] 大模型推理的量化革命：从INT8到INT4**  
   📰 来源：OpenAI Blog  
   🔗 链接：https://...  
   📝 简介：详细介绍了最新的INT4量化技术...
```

## ⚙️ 配置说明

### 类别配置 (`config/categories.json`)

支持自定义类别及其权重：

```json
{
  "categories": [
    {
      "name": "技术探讨",
      "priority_weight": 1.0,
      "keywords": ["技术", "算法", "架构"]
    }
  ]
}
```

### 定时任务配置 (`config/config.json`)

可修改执行时间：

```json
{
  "schedule": {
    "morning": "09:30",
    "afternoon": "15:30",
    "evening": "20:30"
  }
}
```

### 热力值算法参数

```json
{
  "heat_config": {
    "mention_weight": 0.6,   // 提及度权重
    "depth_weight": 0.3,     // 深度权重
    "category_weight": 0.1   // 类别权重
  }
}
```

## 🔧 命令行使用

```bash
# 启动定时服务（推荐）
python run.py --daemon

# 手动执行指定时间段
python run.py --run morning      # 早间分析
python run.py --run afternoon    # 午间分析
python run.py --run evening      # 晚间分析

# 单独执行某个模块（测试用）
cd scripts
python fetch_blogs.py            # 只抓取RSS
python analyze_topics.py         # 只分析话题
python calculate_heat.py         # 只计算热力值
python generate_report.py        # 只生成报告
```

## 📈 工作流程

```
1. 定时触发 (9:30/15:30/20:30)
   ↓
2. 抓取RSS源 (fetch_blogs.py)
   - 解析BlogFeeds.md中的100+RSS源
   - 过滤当天发布的文章
   ↓
3. 话题分析 (analyze_topics.py)
   - 使用GLM-4-Flash提取文章主题
   - 语义聚类合并相似话题
   ↓
4. 热力值计算 (calculate_heat.py)
   - 提及度(60%) + 深度(30%) + 类别(10%)
   - 排序选出Top 3话题
   ↓
5. 报告生成 (generate_report.py)
   - AI生成推荐理由
   - 批量翻译文章标题和摘要
   - 输出Markdown格式报告
   ↓
6. 追加到当天报告文件 (data/reports/YYYY-MM-DD.md)
```

## 🛠️ 常见问题

### Q: 如何添加或删除RSS源？

编辑 `../BlogFeeds.md` OPML文件，添加或删除 `<outline>` 标签。

### Q: 如何调整话题类别？

编辑 `config/categories.json`，可添加新类别或修改现有类别的权重。

### Q: 文章太少时会怎样？

系统会自动降级：
- 如果文章数 < 5篇，推荐标准会降低
- 如果没有识别到话题，跳过本次推荐

### Q: 如何修改推荐话题数量？

编辑 `config/config.json`：

```json
{
  "output_config": {
    "topics_per_report": 3,      // 每次推荐几个话题
    "articles_per_topic": 5      // 每个话题关联几篇文章
  }
}
```

## 📝 日志查看

```bash
# 查看抓取日志
tail -f logs/fetch_blogs.log

# 查看调度器日志
tail -f logs/scheduler.log
```

## 🔗 依赖项

- Python 3.8+
- feedparser：RSS解析
- zhipuai：智谱AI SDK
- apscheduler：定时任务
- python-dateutil：日期处理

## 📄 License

MIT

---

*创建日期: 2026-02-03*  
*版本: 1.0.0*
