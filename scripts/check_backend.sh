#!/bin/bash

# 后端代码检查脚本
echo "🔍 检查后端代码质量..."

# 检查 Python 文件语法
echo "📄 检查 Python 语法..."
find backend -name "*.py" -exec python3 -m py_compile {} \;

if [ $? -ne 0 ]; then
    echo "❌ Python 语法检查失败"
    exit 1
fi

# 如果安装了 flake8，则运行代码风格检查
if command -v flake8 &> /dev/null; then
    echo "🎨 运行 flake8 代码风格检查..."
    flake8 backend --max-line-length=88 --exclude=venv,__pycache__,.git
    if [ $? -ne 0 ]; then
        echo "❌ flake8 检查失败"
        exit 1
    fi
else
    echo "⚠️  flake8 未安装，跳过代码风格检查"
fi

# 安全性检查（如果安装了 safety）
if command -v safety &> /dev/null; then
    echo "🛡️  运行安全检查..."
    safety check
    if [ $? -ne 0 ]; then
        echo "❌ 安全检查发现潜在问题"
        exit 1
    fi
else
    echo "⚠️  safety 未安装，跳过安全检查"
fi

echo "✅ 后端代码检查通过"