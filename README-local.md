# EcomAI 本地启动指南

## 前置条件

| 组件 | 版本建议 |
|------|----------|
| Python | 3.10+（推荐 conda 环境 `ecomai`） |
| Node.js | ≥ 20 |
| MySQL | 8.x，本地服务已启动 |
| Redis | 可选（阶段一 JWT 无状态，可不启） |

## 1. 初始化数据库

```powershell
# 创建库并导入 mall 基础数据（按你的 MySQL 账号修改 -p 参数）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS mall DEFAULT CHARSET utf8mb4;"
mysql -u root -p mall < mall\mall-back\document\sql\mall.sql
mysql -u root -p mall < sql\ddl\ecom_event_log.sql
mysql -u root -p mall < sql\ddl\ums_member_product_collection.sql
mysql -u root -p mall < sql\ads\ads_tables.sql
```

复制并编辑 API 环境变量：

```powershell
copy ecom-api\.env.example ecom-api\.env
# 编辑 MYSQL_PASSWORD 等
```

## 2. 启动后端

```powershell
cd ecom-api
pip install -r requirements.txt
python run.py

快速启动命令：cd ecom-api; python run.py

```

- 管理端 API：<http://127.0.0.1:8081>
- 用户端 API：<http://127.0.0.1:8085>
- 健康检查：`/health`

## 3. 启动管理端

```powershell
cd ecom-admin-web
npm install
npm run dev

快速启动命令：cd ecom-admin-web; npm run dev

```

访问 <http://127.0.0.1:8090>，默认账号 **admin / macro123**。

## 4. 启动用户端（PC 商城）

```powershell
cd ecom-user-web
npm install
npm run dev

快速启动命令：cd ecom-user-web; npm run dev

```

访问 <http://127.0.0.1:5173>，默认会员 **test / 123456**。

## 5. 启动运营端（阶段三大屏）

```powershell
# 灌注数据后刷新 ADS 汇总表
python scripts\ads\refresh_ads.py

cd ecom-ops-web
npm install
npm run dev

快速启动命令：cd ecom-ops-web; npm run dev

```

访问 <http://127.0.0.1:8095>，默认参考日期为 **当天**（可在页头切换）；ADS 刷新会汇总库内全部订单与行为数据。

大屏 8 模块：核心 KPI、24h 曲线、转化漏斗、UV/PV、地域 TOP、30 日趋势、热销 TOP、订单状态。  
指标口径见 `docs/ads_metrics.md`。

## 6. 推荐与行为闭环

### 6.1 训练 ItemCF 模型

```powershell
cd ecom-api
pip install -r ..\scripts\recommend\requirements.txt
python ..\scripts\recommend\train_itemcf.py
python run.py
```

- 模型目录：`models/itemcf/`
- 评估说明：`docs/recommend_eval.md`
- 接口：`GET /recommend/forYou`（首页为你推荐）、`GET /recommend/similar/{productId}`（详情看了又看）

### 6.2 用户行为（推荐画像数据源）

| 类型 | 行为 | 采集方式 |
|------|------|----------|
| 隐式 | 浏览 pv、点击 click | 前端 `POST /event/track` |
| 显式 | 加购 cart | 服务端加购时写入 `ecom_event_log` |
| 显式 | 收藏 fav | 详情页收藏按钮 → `ums_member_product_collection` + 事件日志 |
| 显式 | 下单 order | `oms_order` + 可选事件日志 |

在线「为你推荐」会合并以上信号，并按时间衰减（约 23 天半衰期）计算偏好权重。  
用户端顶栏：**我的收藏** / 购物车 / 我的订单；详情页有 **收藏** 按钮。

## 7. 智能 BI 助手（豆包）

### 7.1 配置火山引擎豆包

在 [火山方舟](https://console.volcengine.com/ark) 创建推理接入点，复制 API Key 与接入点 ID（`ep-xxx`），写入 `ecom-api/.env`：

```env
LLM_API_BASE=https://ark.cn-beijing.volces.com/api/v3
LLM_API_KEY=你的方舟_API_Key
LLM_MODEL=ep-你的接入点ID
LLM_TIMEOUT=60
```

安装依赖并重启 Admin API：

```powershell
cd ecom-api
pip install -r requirements.txt
python run.py
```

### 7.2 使用方式

1. 启动运营端 `ecom-ops-web`（端口 8095）
2. 点击右下角 **EcomAI** 悬浮按钮，打开豆包风格对话窗
3. 助手自动使用大屏当前 **参考日期**；可问 GMV、漏斗、趋势等
4. 接口：`POST /ops/assistant/query`、`GET /ops/assistant/suggestions`

**路由说明**：常见指标优先走 **模板路由**（与大屏 ADS 口径一致）；复杂问题走 **NL2SQL + 豆包解读**。  
知识库与安全策略见 `docs/metrics_dictionary.md`、`docs/nl2sql_safety.md`。

## 8. 验收路径

1. 用户端：首页浏览 → 商品详情 → 加购 → 结算 → 模拟支付 → 订单列表
2. 管理端：登录 → 商品列表上下架 → 订单列表查看/发货

## 默认端口一览

| 服务 | 端口 |
|------|------|
| ecom-api (admin) | 8081 |
| ecom-api (portal) | 8085 |
| ecom-admin-web | 8090 |
| ecom-user-web | 5173 |
| ecom-ops-web | 8095 |

## 常见问题

- **登录报用户名或密码错误**：确认已导入 `mall.sql`，且 `ecom-api/.env` 数据库连接正确。
- **bcrypt 报错**：requirements 已锁定 `bcrypt<4.1`，重新 `pip install -r requirements.txt`。
- **收藏功能报错**：确认已执行 `sql/ddl/ums_member_product_collection.sql` 并重启 Portal API。
