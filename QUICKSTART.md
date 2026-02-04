# Blog Topic Monitor Skill - 快速开始指南

## 🚀 30秒快速启动

### 步骤1：配置API密钥

```bash
cd blog-topic-monitor-skill

# 方式1：使用配置向导（推荐）
./setup.sh

# 方式2：手动编辑
vi config/config.json
# 将智谱API密钥填入 "zhipu_api_key" 字段
```

**获取智谱API密钥**：
1. 访问 https://open.bigmodel.cn/
2. 注册/登录账号
3. 在控制台创建API密钥
4. 复制密钥到配置文件

### 步骤2：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤3：测试运行

```bash
# 测试RSS抓取（可选）
cd scripts
python fetch_blogs.py
cd ..

# 完整测试：手动执行早间分析
python run.py --run morning
```

**预期输出**：
- 在 `data/reports/` 目录生成今天的Markdown报告
- 包含3个热门话题推荐

### 步骤4：启动定时服务（可选）

```bash
# 前台运行（测试用）
python run.py --daemon

# 后台运行（生产环境）
nohup python run.py --daemon > logs/daemon.log 2>&1 &
```

---

## 📋 详细说明

### 配置文件说明

`config/config.json`：

```json
{
  "zhipu_api_key": "填入你的API密钥",
  "zhipu_model": "glm-4-flash",
  "schedule": {
    "morning": "09:30",    // 早间执行时间
    "afternoon": "15:30",  // 午间执行时间
    "evening": "20:30"     // 晚间执行时间
  }
}
```

`config/categories.json`：

- 定义话题分类和优先级权重
- 可自定义添加新类别

### 查看结果

报告文件位置：`data/reports/YYYY-MM-DD.md`

每天生成一个文件，包含3个时间段的推荐。

---

## 🛠️ 常用命令

```bash
# 手动执行指定时间段
python run.py --run morning      # 早间
python run.py --run afternoon    # 午间
python run.py --run evening      # 晚间

# 查看日志
tail -f logs/scheduler.log

# 停止定时服务
ps aux | grep "run.py --daemon"
kill <PID>
```

---

## ❓ 常见问题

### Q1: "智谱AI API调用失败"

**原因**：API密钥未配置或无效

**解决**：
1. 检查 `config/config.json` 中的 `zhipu_api_key` 是否正确
2. 确认API密钥状态（是否过期、余额是否充足）

### Q2: "未抓取到任何文章"

**原因**：
- RSS源当天没有新文章
- 网络连接问题

**解决**：
1. 检查网络连接
2. 查看日志 `logs/fetch_blogs.log`
3. 尝试减少RSS源数量测试

### Q3: "报告中话题数量少于3个"

**原因**：文章数量不足或话题识别较少

**解决**：
- 这是正常的降级行为
- 系统会自动推荐所有识别到的话题
- 午间和晚间会有更多累计文章

---

## 📚 更多信息

- 详细文档：[README.md](./README.md)
- 技能说明：[SKILL.md](./SKILL.md)
- 设计方案：查看artifacts中的implementation_plan.md

---

**祝使用愉快！** 🎉

如有问题，请查看日志文件或文档。
