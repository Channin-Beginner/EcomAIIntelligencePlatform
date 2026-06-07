# 推荐模型评估报告（阶段四 · ItemCF）

## 算法概述

| 项 | 说明 |
|----|------|
| 算法 | **ItemCF**（物品协同过滤）+ 订单共现 + 行为余弦 + 类目/品牌内容增强 |
| 训练脚本 | `scripts/recommend/train_itemcf.py` |
| 模型产物 | `models/itemcf/manifest.json`、`item_similar.json`、`popular.json` |
| 在线服务 | Portal API `GET /recommend/guessYouLike`、`GET /recommend/similar/{id}` |

## 训练数据

- 行为：`ecom_event_log`（order / cart / fav / click / pv）
- 交易：`oms_order` + `oms_order_item`
- 规模（最近一次训练）：约 3001 用户、330 在售 SKU、15.8 万条交互

## 评估方法

- **Leave-one-out**：对交互 ≥ 2 次的用户，随机留 1 个商品，用其余行为生成 Top-10 推荐，检查是否命中。
- **HR@10** = 命中用户数 / 参与评估用户数。

## 最新指标

见 `models/itemcf/manifest.json`，典型结果：

| 指标 | 含义 | 目标 |
|------|------|------|
| `hr_at_10` | 全行为信号留一命中率 | ≥ 0.10 |
| `hr_at_10_order_holdout` | 仅对订单商品留一 | 参考项 |

最近一次训练：**HR@10 ≈ 0.12**，**订单留一 HR@10 ≈ 0.19**，满足阶段四 KPI。

## 重新训练

```powershell
cd ecom-api
pip install -r ..\scripts\recommend\requirements.txt
python ..\scripts\recommend\train_itemcf.py
```

训练完成后重启 Portal API，用户端「猜你喜欢」会自动读取新模型（按文件 mtime 热加载）。

## 前端接入

- 首页 **为你推荐** Tab：`GET /recommend/forYou`（按 ItemCF 偏好分从高到低分页）
- 商品详情页：**看了又看** → `GET /recommend/similar/{id}`（基于当前商品的相关推荐）
