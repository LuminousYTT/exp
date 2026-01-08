# 加工 MES Demo

栈：前端 HTML+JS+CSS，后端 Python Flask，数据库 MySQL（可改为本地 SQLite 试用），内置二维码生成/扫码、三段式生产（榨汁→酿造→装瓶）、质检入库与全链路追溯。

## 目录
- backend/ Flask + SQLAlchemy API
- frontend/ 多页面（总览、管理员、操作员、质检）含摄像头扫码

## 后端运行
1) 安装依赖（建议虚拟环境）
```bash
cd backend
pip install -r requirements.txt
```

2) 配置数据库
- 默认 `config.py` 指向本机 MySQL：`mysql+pymysql://root:9860@localhost:3306/mes`
- 可通过环境变量覆盖：
```bash
set DATABASE_URL=mysql+pymysql://user:password@host:3306/mesdb
```
- 若想用 SQLite 试用：`set DATABASE_URL=sqlite:///mes_demo.db`

3) 启动
```bash
python app.py
```
默认监听 `http://localhost:5000`，二维码文件保存在 `backend/qrcodes/`。

## 前端预览
直接用浏览器打开 `frontend/index.html`（或 admin/operator/qa 页面）。如前后端不同主机，请在页面顶部 `API_BASE` 修改为后端地址。

## 核心流程与功能
- 物料质检+入库：录入名称/批次/供应商/结果，生成物料二维码；扫码入库，记录检验与收货。
- 三段式生产：
   - 榨汁：消耗物料库存，生成榨汁半成品二维码，记录操作员。
   - 酿造：消耗榨汁库存，生成酒液半成品二维码，记录操作员。
   - 装瓶：消耗酿造库存，生成瓶装半成品二维码，记录操作员。
- 质检入库（成品）：对瓶装半成品或完工码质检，生成成品与质检二维码，入库并累计工单完成量。
- 工单：建单、扫码、进度累计、完工码生成。
- 追溯：
   - `/api/trace/product/<token>`：支持成品码、质检码、半成品码、物料码自动容错；返回成品信息、半成品链路（含操作员）、物料与各类检验记录。
   - `/api/trace/semi/<token>`：半成品上游链路与操作员。
   - `/api/trace/material/<token>`：物料及其检验。
- 扫码：`/api/scan/<token>` 统一识别物料/人员/工单/半成品/成品/质检码，前端摄像头基于 html5-qrcode。

## 主要接口（POST 为 JSON）
- 材料：`POST /api/materials`，`GET /api/materials`
- 人员：`POST /api/personnel`，`GET /api/personnel`
- 工单：`POST /api/workorders`，`GET /api/workorders`，`POST /api/workorders/<id>/progress`
- 工序：`POST /api/process/steps`（step=juice/ferment/bottle，输入上游二维码，记录操作员并生成下游二维码）
- 质检：`POST /api/inspections`（object_type=material/product，半成品码在质检入库时作为成品创建的上游 parent_token）
- 追溯：`GET /api/trace/product/<token>`，`GET /api/trace/semi/<token>`，`GET /api/trace/material/<token>`
- 扫码：`GET /api/scan/<token>`，健康检查：`GET /health`

## 使用提示
- 前端质检页（qa.html）：仅成品质检入库；扫码半成品码会自动填充入库与追溯输入；追溯按钮固定查 `/trace/product`，自动返回上游链路。
- 操作员页面：按工单依次榨汁/酿造/装瓶，扫码上游二维码执行步骤，生成下游二维码。
- 若运行中添加了新字段（如 qty、inspection_qr_token、operator_id 等），需对既有数据库执行相应 ALTER 或重建库。

## 生产化建议
- 将数据库连接、密钥放入环境变量并限制 CORS 域名。
- 为高频查询字段加索引；完善状态机与权限校验。
- 二维码图片可持久化到对象存储或改为短链服务；开启 HTTPS 以便摄像头权限。 
