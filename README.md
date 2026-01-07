# 电子组装车间 MES Demo

栈：前端 HTML+JS+CSS，后端 Python Flask，数据库 MySQL（支持本地 SQLite 快速试用），支持二维码生成与扫码校验。

## 目录
- backend/ 后端 Flask + SQLAlchemy
- frontend/ 单页前端（含表单、列表、扫码）

## 后端运行
1. 安装依赖（推荐虚拟环境）：
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. 配置数据库连接（MySQL）：
   - 设置环境变量 `DATABASE_URL`，示例：
     ```bash
     set DATABASE_URL=mysql+pymysql://user:password@localhost:3306/mesdb
     ```
   - 若未设置将使用本地文件 `sqlite:///mes_demo.db` 便于快速试用。
3. 启动服务：
   ```bash
   python app.py
   ```
   默认监听 `http://localhost:5000`。

## 前端预览
直接用浏览器打开 `frontend/index.html`。如前后端跨主机，修改页面顶部的 `API_BASE` 常量指向后端地址。

## 功能说明
- 原材料：入库信息+批次+供应商+检验结果，自动生成唯一二维码，扫码可查合规性。
- 人员：工号/岗位/权限建档，二维码校验后才允许作业，可追溯责任人。
- 成品：合格后生成追溯码，整合原材料、工序数据、最终质检结果。
- 扫码：前端使用摄像头 (html5-qrcode)；后端 `/api/scan/<token>` 返回类型与详情。

## 主要接口（POST 为 JSON）
- `POST /api/materials` 创建原材料，返回 `qr_image_base64`
- `GET /api/materials`
- `POST /api/personnel`
- `GET /api/personnel`
- `POST /api/products`
- `GET /api/products`
- `GET /api/scan/<qr_token>` 统一扫码校验
- `GET /health`

## 生产化建议
- 将数据库连接、密钥等放入 `.env` 或环境变量；限制 CORS 域。
- 为表添加索引/约束，细化状态机（入厂检/上线/报废）。
- 前端接入企业认证；扫码校验后再触发工序权限控制。
- 持久化二维码图片到对象存储，或使用短链服务。
