# 领星 ERP 开放 API 接口文档

> 文档来源：https://apidoc.lingxing.com/#/  
> 文档密钥：LF34XUn3hw  
> 整理日期：2026-03-20

---

## 1. 基础信息

### 1.1 API 请求域名

```
https://openapi.lingxing.com
```

### 1.2 认证流程

1. 在领星 ERP【设置】>【业务配置】>【全局】>【开放接口】中申请 `AppId` 和 `AppSecret`
2. 配置 IP 白名单（公网 IP，不支持域名）
3. 使用 `AppId` + `AppSecret` 获取 `access_token`
4. 所有业务接口请求需携带公共参数

### 1.3 公共请求参数（Query Params）

| 参数名 | 类型 | 描述 | 来源 |
|--------|------|------|------|
| access_token | string | 接口令牌 | 授权接口获取 |
| app_key | string | APP ID | ERP 开放接口菜单 |
| timestamp | string | 时间戳 | 实时生成 |
| sign | string | 接口签名 | MD5 + AES 加密生成 |

### 1.4 签名 sign 生成规则

1. 所有参数（业务参数 + access_token + app_key + timestamp）按 ASCII 排序
2. 拼接为 `key1=value1&key2=value2&...`（value 为空不参与，null 参与）
3. MD5(32位) 加密后转大写
4. AES/ECB/PKCS5PADDING 加密，密钥为 appId
5. sign 传输时需 URL encode

### 1.5 限流

- 改进的令牌桶算法，维度：appId + 接口 url
- 令牌回收基于请求完成/异常/超时(2min)
- 限流错误码：3001008

### 1.6 SDK 下载

- [Python SDK](https://apidoc.lingxing.com/file/openapi-python3-sdk-20230419.zip)
- [Node SDK](https://apidoc.lingxing.com/file/openapi-node-sdk-master-20230515.zip)
- [Java SDK](https://apidoc.lingxing.com/file/openapi-sdk-java-20240730.zip)
- [Go SDK](https://apidoc.lingxing.com/file/openapi-go-sdk.zip)
- [PHP SDK](https://apidoc.lingxing.com/file/openapi-php-sdk-master-20230817.zip)

---

## 2. 授权接口

### 2.1 获取 access_token

- **Path**: `POST /api/auth-server/oauth/access-token`
- **Content-Type**: `multipart/form-data`
- **令牌桶容量**: 100

**请求参数（form-data）：**

| 参数名 | 说明 | 必填 | 类型 |
|--------|------|------|------|
| appId | AppID | 是 | string |
| appSecret | AppSecret | 是 | string |

**请求示例：**
```bash
curl --location 'https://openapi.lingxing.com/api/auth-server/oauth/access-token' \
  --form 'appId="your_app_id"' \
  --form 'appSecret="your_app_secret"'
```

**返回结果：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | int | 状态码，200 成功 |
| msg | string | 消息提示 |
| data.access_token | string | 请求令牌 |
| data.refresh_token | string | 续约令牌 |
| data.expires_in | int | 过期时间（秒），默认 7199 |

**返回示例：**
```json
{
  "code": "200",
  "msg": "OK",
  "data": {
    "access_token": "4dcaa78e-b52d-4325-bc35-571021bb0787",
    "refresh_token": "da5b5047-e6d1-496c-ab4d-d5425a6a66e4",
    "expires_in": 7199
  }
}
```

### 2.2 续约 access_token

- **Path**: `POST /api/auth-server/oauth/refresh`
- refresh_token 有效期 2 小时，一次性使用
- 每次续约返回新的 refresh_token

---

## 3. 基础数据接口

### 3.1 查询亚马逊店铺列表

- **Path**: `GET /erp/sc/data/seller/lists`
- **令牌桶容量**: 1
- 一次性返回企业全部已授权店铺，唯一键为 `sid`

**返回字段：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| data[].sid | number | 店铺id（领星唯一标识，其他接口需要用到） |
| data[].mid | number | 站点id |
| data[].name | string | 店铺名 |
| data[].seller_id | string | 亚马逊店铺id |
| data[].account_name | string | 店铺账户名称 |
| data[].region | string | 站点简称（NA=北美, EU=欧洲等） |
| data[].country | string | 商城所在国家名称 |
| data[].status | int | 店铺状态：0停止同步 1正常 2授权异常 3欠费停服 |
| data[].marketplace_id | string | 市场id |


---

## 4. 利润分析相关接口（财务模块）

### 4.1 接口列表总览

| 接口名称 | Path | 方式 | 说明 |
|----------|------|------|------|
| 利润报表-MSKU | /bd/profit/report/open/report/msku/list | POST | 按 MSKU 维度查询利润 |
| 利润报表-ASIN | /bd/profit/report/open/report/asin/list | POST | 按 ASIN 维度查询利润 |
| 利润报表-父ASIN | /bd/profit/report/open/report/parent/list | POST | 按父 ASIN 维度查询利润 |
| 利润报表-SKU | /bd/profit/report/open/report/sku/list | POST | 按 SKU 维度查询利润 |
| 利润报表-店铺 | /bd/profit/report/open/report/seller/list | POST | 按店铺维度查询利润 |
| 利润报表-店铺月度汇总 | /bd/profit/report/open/report/seller/summary | POST | 店铺月度汇总 |
| 利润报表-订单 | /bd/profit/report/open/report/order/list | POST | 按订单维度查询利润 |
| 利润报表-订单transaction | /bd/profit/report/open/report/order/transaction/list | POST | 订单transaction视图 |
| 利润统计-MSKU | (统计模块) | POST | 利润统计 MSKU 维度 |
| 利润统计-ASIN | (统计模块) | POST | 利润统计 ASIN 维度 |
| 利润统计-父ASIN | (统计模块) | POST | 利润统计父 ASIN 维度 |
| 利润统计-店铺 | (统计模块) | POST | 利润统计店铺维度 |

### 4.2 查询利润报表-店铺（详细）

- **Path**: `POST /bd/profit/report/open/report/seller/list`
- **令牌桶容量**: 10

**请求参数（JSON Body）：**

| 参数名 | 说明 | 必填 | 类型 | 示例 |
|--------|------|------|------|------|
| offset | 分页偏移量 | 否 | int | 0 |
| length | 分页长度，上限10000 | 否 | int | 1000 |
| mids | 站点id数组 | 否 | array | [2] |
| sids | 店铺id数组 | 否 | array | [110] |
| monthlyQuery | 是否按月查询（false=按天，true=按月） | 否 | boolean | false |
| startDate | 开始时间（按天Y-m-d，按月Y-m） | 是 | string | "2023-09-21" |
| endDate | 结束时间（按天最长31天跨度） | 是 | string | "2023-10-20" |
| currencyCode | 币种code（默认原币种） | 否 | string | "CNY" |
| summaryEnabled | 是否按店铺汇总返回 | 否 | boolean | false |
| orderStatus | 交易状态：Deferred/Disbursed/DisbursedAndPreSettled/All | 否 | string | "Disbursed" |

**请求示例：**
```json
{
  "offset": 0,
  "length": 1000,
  "mids": [2],
  "sids": [110],
  "monthlyQuery": false,
  "startDate": "2023-09-21",
  "endDate": "2023-10-20",
  "currencyCode": "CNY",
  "summaryEnabled": false,
  "orderStatus": "Disbursed"
}
```

**核心返回字段（data.records[]）：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| sid | int | 店铺id |
| storeName | string | 店铺名 |
| countryCode | string | 国家编码 |
| country | string | 国家中文名 |
| currencyCode | string | 币种 |
| postedDateLocale | string | 本地时间 |
| totalSalesQuantity | int | 销量 |
| fbaSalesQuantity | int | FBA销量 |
| fbmSalesQuantity | int | FBM销量 |
| totalSalesAmount | number | 销售额 |
| fbaSaleAmount | number | FBA销售额 |
| fbmSaleAmount | number | FBM销售额 |
| totalAdsSales | number | 广告销售额 |
| totalAdsCost | number | 广告费 |
| adsSpCost | number | SP广告费 |
| adsSbCost | number | SB广告费 |
| adsSdCost | number | SD广告费 |
| promotionalRebates | number | 促销折扣 |
| totalSalesRefunds | number | 收入退款额 |
| refundsQuantity | int | 退款量 |
| refundsRate | number | 退款率 |
| fbaReturnsQuantity | int | 退货量 |
| fbaReturnsQuantityRate | number | 退货率 |
| fbaDeliveryFee | number | FBA发货费 |
| totalStorageFee | number | FBA仓储费 |
| cgPriceTotal | number | 采购成本 |
| cgTransportCostsTotal | number | 头程成本 |
| totalCost | number | 合计成本 |
| grossProfit | number | 毛利润 |
| grossRate | number | 毛利率 |
| platformIncome | number | 平台收入 |
| platformExpense | number | 平台支出 |
| grossProfitTax | number | 合计税费 |
| otherFeeStr | array | 自定义费用信息 |
| customOrderFee | number | 订单其他费 |
| promotionFee | number | 推广费 |
| sharedSubscriptionFee | number | 订阅费 |
| sharedLdFee | number | 秒杀费 |
| sharedCouponFee | number | 优惠券 |
| adjustments | number | 调整费用 |


---

## 5. 差评分析相关接口（客服模块）

### 5.1 接口列表总览

| 接口名称 | Path | 方式 | 说明 |
|----------|------|------|------|
| 评价管理-Review(新) | /basicOpen/openapi/service/v3/data/mws/reviews | POST | 查询 Review 列表（推荐） |
| 评价管理-Review(旧) | /data/mws/reviews | POST | 查询 Review 列表（旧版） |
| 评价管理-1-3星Feedback | (Feedback低星) | POST | 1-3星 Feedback 列表 |
| 评价管理-4-5星Feedback | (Feedback高星) | POST | 4-5星 Feedback 列表 |
| 评价统计-Review列表 | /data/mws/reviewLists | POST | Review 统计列表 |
| 评价统计-Review每日新增 | /data/mws/reviewDetail | POST | Review 每日新增数 |
| 评价统计-Feedback列表 | /data/mws/feedbackLists | POST | Feedback 统计列表 |
| 评价统计-Feedback每日新增 | /data/mws/feedbackDetail | POST | Feedback 每日新增数 |
| 买家之声列表 | /data/service/voiceOfBuyerList | POST | 买家之声 |

### 5.2 查询评价管理-Review(新)（详细）

- **Path**: `POST /basicOpen/openapi/service/v3/data/mws/reviews`
- **令牌桶容量**: 1

**请求参数（JSON Body）：**

| 参数名 | 说明 | 必填 | 类型 | 示例 |
|--------|------|------|------|------|
| sort_field | 排序类型 | 否 | string | "review_date" |
| sort_type | 排序方向 | 否 | string | "desc" |
| sids | 店铺id，多个逗号分隔 | 否 | string | "1" |
| mids | 站点id，多个逗号分隔 | 否 | string | "1" |
| principal_uids | listing负责人，多个逗号分隔 | 否 | string | "128402" |
| search_field | 搜索字段 | 否 | string | "asin" |
| search_value | 搜索值 | 否 | string | "B07XXX" |
| date_field | 时间搜索类型：review_time/create_time/last_update_time | 是 | string | "review_time" |
| start_date | 开始时间 Y-m-d | 是 | string | "2024-06-06" |
| end_date | 结束时间 Y-m-d | 是 | string | "2024-09-04" |
| status | 状态：0待处理/1处理中/2已完成 | 否 | string | "0,1,2" |
| star | 星级，多个逗号分隔 | 否 | string | "1,2,3" |
| review_modified_status | 内容状态：-1已删除/0未标识/1已变更 | 否 | string | "-1,1,0" |
| mark | 标识：is_vp/is_er/is_topc/is_topr/is_vine | 否 | string | "is_vp" |
| cs_principal_uids | 处理人 | 否 | string | "10329601" |
| offset | 分页偏移量 | 否 | int | 0 |
| length | 分页长度，上限200 | 否 | int | 20 |
| cids | 分类id | 否 | string | "30" |
| global_tag_ids | 标签id | 否 | string | "" |
| match_types | 匹配类型 | 否 | string | "" |

**search_field 可选值：**
- `asin` - ASIN
- `parent_asin` - 父ASIN
- `remark` - 备注
- `amazon_order_id` - 订单号
- `author` - 买家信息
- `review_id` - Review ID
- `buyer_email` - 买家邮箱
- `last_title` - 评价标题

**请求示例（查询1-3星差评）：**
```json
{
  "sort_field": "review_date",
  "sort_type": "desc",
  "date_field": "review_time",
  "start_date": "2024-01-01",
  "end_date": "2024-03-20",
  "star": "1,2,3",
  "offset": 0,
  "length": 200
}
```

**返回字段（data[]）：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| asin | string | ASIN |
| parent_asin | array | 父ASIN列表 |
| seller_sku | array | MSKU列表 |
| last_star | number | 星级（1-5） |
| last_title | string | 评价标题 |
| last_content | string | 评价内容 |
| review_likes | number | 点赞数 |
| review_id | string | Review ID |
| review_url | string | 评价链接 |
| author | string | 买家信息 |
| images | array | 评论图片链接 |
| videos | array | 评论视频链接 |
| is_vp | number | 是否VP |
| seller_name | array | 店铺名 |
| marketplace | string | 国家 |
| review_date | string | 评价时间 |
| create_time | string | 创建时间 |
| update_time | string | 更新时间 |
| amazon_order_list | array | 订单号列表 |
| buyer_email | array | 买家邮箱 |
| remark | string | 备注 |
| status | number | 处理状态：0待处理/1处理中/2已完成 |
| tags | array | 标签 |
| cs_principals | array | 处理人 |
| item_name | array | 商品标题 |
| local_info | array | 本地信息（local_sku/local_name/category_name） |
| total | number | 总数（顶层字段） |

**返回示例：**
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "asin": "B07XKHF683",
      "seller_sku": ["YE-2XPZ-XKY1-A"],
      "last_star": 1,
      "last_title": "Bad quality",
      "last_content": "Product broke after 2 days...",
      "review_id": "R1KKLEHWNZWH05",
      "author": "John",
      "seller_name": ["MyStore-US"],
      "marketplace": "美国",
      "review_date": "2024-01-15",
      "status": 0
    }
  ],
  "total": 1
}
```

---

## 6. 其他经营数据相关接口

### 6.1 统计模块

| 接口名称 | 说明 |
|----------|------|
| 查询亚马逊销量统计 | 按日统计销量数据 |
| 查询产品表现 | 产品表现数据（新版） |
| 查询店铺汇总销量 | 店铺维度汇总销量 |
| 查询退货分析 | 退货分析数据 |
| 查询运营日志(新) | 运营日志记录 |

### 6.2 销售模块

| 接口名称 | 说明 |
|----------|------|
| 查询亚马逊Listing | Listing 数据 |
| 查询亚马逊订单列表 | 订单列表 |
| 查询亚马逊订单详情 | 订单详情 |

### 6.3 财务模块-其他

| 接口名称 | 说明 |
|----------|------|
| 查询费用类型列表 | 费用分类 |
| 查询费用明细列表 | 费用明细 |
| 查询结算中心-结算汇总 | 结算汇总 |
| 查询结算中心-交易明细 | 交易明细 |

---

## 7. 推荐的数据抓取方案

### 7.1 每日利润分析

1. 调用 **获取 access_token** 接口获取令牌
2. 调用 **查询亚马逊店铺列表** 获取所有店铺 sid
3. 调用 **利润报表-店铺** 接口，按天查询前一天数据
4. 可选：调用 **利润报表-MSKU/ASIN** 获取更细粒度数据

### 7.2 每周利润汇总

1. 调用 **利润报表-店铺** 接口，startDate/endDate 设为过去7天
2. 或调用 **利润报表-店铺月度汇总** 按月汇总

### 7.3 每日差评监控

1. 调用 **评价管理-Review(新)** 接口
2. 设置 `star: "1,2,3"` 筛选差评
3. 设置 `date_field: "review_time"` + 当天日期范围
4. 分析 `last_content` 评价内容，提取差评原因

### 7.4 注意事项

- access_token 有效期约 2 小时，需定时续约或重新获取
- 利润报表按天查询最长跨度 31 天
- Review 接口令牌桶容量仅 1，需控制请求频率
- sign 签名需实时生成，不要缓存（2分钟过期）
- 所有金额字段默认原币种，可通过 currencyCode 转换为 CNY
