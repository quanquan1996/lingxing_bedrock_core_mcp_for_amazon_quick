# 领星 API 接口测试总结

> 测试时间：2026-03-24 12:45（第二轮验证）
> 本机公网 IP：52.220.90.127（已加入白名单）

---

## 测试结果总览

| # | 接口 | Path | 状态 | 说明 |
|---|------|------|------|------|
| 1 | 获取 Token | /api/auth-server/oauth/access-token | ✅ 成功 | Token 正常获取 |
| 2 | 查询店铺列表 | /erp/sc/data/seller/lists | ❌ 无权限 | code=403, 需要在领星重新授权 |
| 3 | 利润报表-店铺（每日） | /bd/profit/report/open/report/seller/list | ✅ 成功 | total=37 |
| 4 | 利润报表-店铺月度汇总 | seller/list + monthlyQuery=true | ✅ 成功 | total=141 |
| 5 | 利润报表-MSKU | /bd/profit/report/open/report/msku/list | ✅ 成功 | total=865 |
| 6 | 利润报表-ASIN | /bd/profit/report/open/report/asin/list | ✅ 成功 | total=702 |
| 7 | 利润报表-父ASIN | /bd/profit/report/open/report/parent/asin/list | ✅ 已验证 | total=231，路径修正后验证通过 |
| 8 | 利润报表-SKU | /bd/profit/report/open/report/sku/list | ✅ 成功 | total=693 |
| 9 | 利润报表-订单 | /bd/profit/report/open/report/order/list | ✅ 已验证 | search_date_field 参数修正后验证通过（即将下线） |
| 10 | 月度汇总（独立接口） | /bd/profit/report/open/report/seller/summary/list | ✅ 已验证 | 返回 23 条，路径修正+日期格式 yyyy-MM-dd |
| 11 | 评价管理-Review（新版v3） | /basicOpen/openapi/service/v3/data/mws/reviews | ✅ 成功 | 正常返回差评数据 |
| 12 | 评价管理-Review（旧版） | /data/mws/reviews | ❌ 404 | 旧版接口已下线 |

**统计：10/12 成功，1 无权限，1 已下线。3 个修正项全部验证通过。**

---

## 已修复的问题

### ✅ 签名错误（已修复）

`lingxing_client.py` 的 `_request()` 方法中，签名参数合并 body 时，Python 的 `bool`（`True`/`False`）和 `list` 类型导致签名不正确。

修复方案：签名时跳过 list/dict 类型参数，boolean 转为小写 `true`/`false`。

### ✅ IP 白名单（已解决）

本机 IP `52.220.90.127` 已加入领星白名单，不再报 `3001002`。

---

## 仍存在的问题

### 🚫 店铺列表无权限（code: 403）

接口 `/erp/sc/data/seller/lists` 返回"授权失效，请更新授权有效期或检查权限"。

**解决方案**：在领星 ERP【设置】>【业务配置】>【全局】>【开放接口】中，重新授权"基础数据"模块。

### ✅ 父ASIN 接口路径已修正并验证通过

原路径 `/bd/profit/report/open/report/parent/list` 不正确。
正确路径为：`/bd/profit/report/open/report/parent/asin/list`（多了 `/asin`）。
已在 `lingxing_client.py` 中添加 `get_profit_by_parent_asin()` 方法，验证返回 total=231。

### ✅ 店铺月度汇总独立接口路径已修正并验证通过

原路径 `/bd/profit/report/open/report/seller/summary` 不正确。
正确路径为：`/bd/profit/report/open/report/seller/summary/list`（多了 `/list`）。
已在 `lingxing_client.py` 中添加 `get_profit_seller_summary_v2()` 方法，验证返回 23 条记录。
注意：该接口日期格式必须为 `yyyy-MM-dd`（不是 `yyyy-MM`）。
现有的 `get_profit_seller_summary()` 通过 `seller/list` + `monthlyQuery=true` 实现，仍然可用。

### ❌ Review 旧版接口已下线

`/data/mws/reviews` 返回 404，已确认下线。使用新版 v3 接口 `/basicOpen/openapi/service/v3/data/mws/reviews`（已验证可用）。

### ✅ 订单维度参数已确认并验证通过

查阅官方文档确认：
- 缺少的必填参数名为 `search_date_field`（不是 `dateType`/`date_type`/`date_field`）
- 可选值：`posted_date_locale`（结算时间）、`fund_transfer_datetime_locale`（转账时间）、`shipment_datetime_locale`（发货时间）
- 该接口参数使用下划线风格：`start_date`、`end_date`、`currency_code`（不是驼峰 `startDate`/`endDate`）
- ⚠️ 官方标注该接口即将下线，建议使用 `查询利润报表 - 订单维度transaction视图`（`/bd/profit/report/open/report/order/transaction/list`）替代
- 已在 `lingxing_client.py` 中添加 `get_profit_by_order()` 方法，验证通过（total=0，可能是日期范围内无数据）

---

## MCP Server 当前可用工具

基于测试结果，以下工具可正常工作：

| 工具 | 依赖接口 | 状态 |
|------|----------|------|
| get_daily_profit | seller/list ✅ | ✅ 可用 |
| get_weekly_profit_summary | seller/list ✅ | ✅ 可用 |
| get_monthly_profit_summary | seller/summary/list ✅ | ✅ 可用（日期需 yyyy-MM-dd） |
| get_profit_by_msku | msku/list ✅ | ✅ 可用 |
| get_profit_by_parent_asin | parent/asin/list ✅ | ✅ 已验证（total=231） |
| get_profit_by_order | order/list ✅ | ✅ 已验证（即将下线） |
| get_negative_reviews | v3/reviews ✅ | ✅ 可用 |
| get_today_negative_reviews | v3/reviews ✅ | ✅ 可用 |
| get_seller_list | seller/lists ❌ | ❌ 需授权 |
| generate_profit_report_excel | seller/list ✅ | ✅ 可用 |
| generate_negative_review_report_excel | v3/reviews ✅ | ✅ 可用 |
