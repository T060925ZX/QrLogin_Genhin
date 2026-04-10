# 原神抢码登录工具

## 📦 项目文件

- `main.py` - 主程序
- `kuang.py` - 扫描框窗口
- `stoken.txt` - Cookie配置文件（需自行创建）
- `stoken.txt.example` - Cookie配置示例
- `requirements.txt` - Python依赖
- `快速开始.md` - 使用指南

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install opencv-python pyzbar Pillow numpy
```

### 2. 配置Cookie
```bash
# 复制示例文件
copy stoken.txt.example stoken.txt

# 编辑 stoken.txt，填入你的cookie
```

### 3. 运行程序
```bash
python main.py
```

## 📝 Cookie获取

1. 给你的Yunzai发送 我的stoken （私聊）

1. 浏览器打开 https://account.mihoyo.com/
2. 登录账号
3. F12 → Network → 刷新
4. 复制Request Headers中的cookie
5. 粘贴到 `stoken.txt`

格式：`stuid=xxx;stoken=xxx;ltoken=xxx;mid=xxx;`

## ⚙️ 功能特性

- ✅ 自动屏幕截图识别二维码
- ✅ 极速抢码模式（10ms扫描间隔）
- ✅ 支持云游戏登录
- ✅ DPI自动适配
- ✅ 窗口位置可配置
- ✅ 从文件读取Cookie

## 📌 注意事项

- Cookie包含敏感信息，请勿泄露
- stoken.txt已加入.gitignore
- 预览窗口默认在右上角
- 红框始终在屏幕中央

---

**祝游戏愉快! 🎮**
