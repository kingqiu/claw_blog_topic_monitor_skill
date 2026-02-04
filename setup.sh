#!/bin/bash

# Blog Topic Monitor - 快速配置脚本

echo "========================================="
echo "  Blog Topic Monitor - 配置向导"
echo "========================================="
echo ""

# 检查config.json是否存在
if [ ! -f "config/config.json" ]; then
    echo "❌ 配置文件不存在，正在创建..."
    cp config/config.json.example config/config.json
fi

# 检查API密钥
API_KEY=$(grep -o '"zhipu_api_key": "[^"]*"' config/config.json | cut -d'"' -f4)

if [ -z "$API_KEY" ]; then
    echo "⚠️  智谱AI API密钥未配置"
    echo ""
    echo "请按照以下步骤操作："
    echo "1. 打开 https://open.bigmodel.cn/ 获取API密钥"
    echo "2. 编辑 config/config.json 文件"
    echo "3. 将API密钥填入 \"zhipu_api_key\" 字段"
    echo ""
    read -p "是否现在编辑配置文件? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-vi} config/config.json
    fi
else
    echo "✅ API密钥已配置"
fi

# 检查依赖
echo ""
echo "检查Python依赖..."
if python3 -m pip show feedparser zhipuai apscheduler > /dev/null 2>&1; then
    echo "✅ 依赖已安装"
else
    echo "⚠️  需要安装依赖"
    read -p "是否现在安装? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip3 install -r requirements.txt
    fi
fi

# 检查BlogFeeds.md
echo ""
echo "检查RSS源文件..."
if [ -f "../BlogFeeds.md" ]; then
    RSS_COUNT=$(grep -c 'xmlUrl=' ../BlogFeeds.md || echo "0")
    echo "✅ 找到 $RSS_COUNT 个RSS源"
else
    echo "❌ BlogFeeds.md 文件不存在"
fi

echo ""
echo "========================================="
echo "  配置完成！"
echo "========================================="
echo ""
echo "下一步操作："
echo ""
echo "1. 测试RSS抓取："
echo "   cd scripts && python3 fetch_blogs.py"
echo ""
echo "2. 手动执行早间分析："
echo "   python3 run.py --run morning"
echo ""
echo "3. 启动定时服务："
echo "   python3 run.py --daemon"
echo ""
