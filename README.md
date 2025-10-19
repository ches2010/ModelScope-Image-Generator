# ModelScope-Image-Generator
基于ModelScope API的图片生成工具，支持「自定义Prompt」「图片路径配置」「本地一键运行」「云服务器一键部署」，无需复杂配置，新手也能快速上手。


## 一、核心功能
1. **自定义配置**：API Key分离存储、可修改图片保存路径；
2. **简单操作**：前端自由编写Prompt，点击“生成”即触发生图；
3. **跨环境运行**：支持Windows/Mac/Linux本地一键启动，云服务器一键部署；
4. **结果可视化**：实时显示生成进度、图片保存路径，支持预览和下载。


## 二、前置准备
1. 获取ModelScope API Key：登录[ModelScope官网](https://modelscope.cn/)，个人中心->访问令牌，复制你的API Key；
2. 环境要求：本地/云服务器需安装Python 3.7+（脚本会自动检查，未装则提示）；
3. 云服务器额外要求：开放50端口（脚本会自动配置防火墙，无需手动操作）。


## 三、本地运行（Windows/Mac/Linux）
### 步骤1：克隆仓库

```bash
git clone https://github.com/ches2010/ModelScope-Image-Generator.git
cd ModelScope-Image-Generator
```

