# 领星 ERP MCP Server 部署指南

## 架构概览

```
用户 → Quick Suite (Flows/Chat) → AgentCore Runtime → 领星 MCP Server → 领星 OpenAPI
                                        ↓
                                   Cognito (OAuth)
                                        ↓
                                   S3 (Excel 报告)
```

## 前置条件

1. AWS 账号，开通 Bedrock AgentCore、Cognito、S3
2. 领星 ERP 开放接口的 `AppId` 和 `AppSecret`
3. 安装 `agentcore` CLI：`pip install bedrock-agentcore-toolkit`
4. 配置好 IP 白名单（AgentCore 出口 IP 加入领星白名单）

## 第一步：配置 Cognito

```bash
# 创建 User Pool
aws cognito-idp create-user-pool --pool-name lingxing-mcp-pool

# 创建 App Client（Client Credentials Grant）
aws cognito-idp create-user-pool-client \
  --user-pool-id YOUR_POOL_ID \
  --client-name lingxing-mcp-client \
  --generate-secret \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-scopes openid
```

记录 `UserPoolId` 和 `ClientId`，填入 `.bedrock_agentcore.yaml`。

## 第二步：创建 S3 存储桶

```bash
aws s3 mb s3://your-lingxing-reports-bucket --region us-east-1
```

## 第三步：配置环境变量

在 AgentCore 部署时注入以下环境变量：

| 变量名 | 说明 |
|--------|------|
| LINGXING_APP_ID | 领星 AppId |
| LINGXING_APP_SECRET | 领星 AppSecret |
| LINGXING_S3_BUCKET | S3 存储桶名 |
| LINGXING_S3_PREFIX | S3 前缀，默认 `lingxing-reports/` |

## 第四步：部署到 AgentCore

```bash
# 1. 编辑 .bedrock_agentcore.yaml，填入实际值

# 2. 配置
agentcore configure

# 3. 部署
agentcore launch
```

部署成功后会返回 MCP 端点 URL。

## 第五步：Quick Suite 配置

### 5.1 添加 MCP Action

1. 进入 Quick Suite → Integrations → Actions
2. 选择 "MCP Server"
3. 填入 AgentCore 返回的端点 URL
4. 配置 OAuth 认证（Cognito Client ID / Secret）

### 5.2 创建 Flows

建议创建以下 Flows：

**Flow 1: 每日利润分析**
- 触发：每日定时 / 手动
- Step 1: 调用 `get_daily_profit`（昨天日期）
- Step 2: 调用 `generate_profit_report_excel`
- Step 3: 返回下载链接

**Flow 2: 每周利润汇总**
- 触发：每周一
- Step 1: 调用 `get_weekly_profit_summary`（weeks_ago=1）
- Step 2: 调用 `generate_profit_report_excel`（上周日期范围）
- Step 3: 返回下载链接

**Flow 3: 每日差评监控**
- 触发：每日定时
- Step 1: 调用 `get_today_negative_reviews`
- Step 2: 如有差评，调用 `generate_negative_review_report_excel`
- Step 3: 返回差评汇总 + 下载链接

## MCP 工具列表

| 工具名 | 说明 |
|--------|------|
| get_seller_list | 查询店铺列表 |
| get_daily_profit | 每日利润（店铺维度） |
| get_weekly_profit_summary | 每周利润汇总 |
| get_monthly_profit_summary | 月度利润汇总 |
| get_profit_by_msku | MSKU 维度利润 |
| get_negative_reviews | 差评查询 |
| get_today_negative_reviews | 今日差评 |
| generate_profit_report_excel | 生成利润 Excel + S3 下载 |
| generate_negative_review_report_excel | 生成差评 Excel + S3 下载 |

## 注意事项

- AgentCore 运行时 `/var/` 只读，日志已重定向到 `/tmp/`
- AgentCore 无状态，Excel 生成和上传在同一请求内完成
- 领星 access_token 有效期 2 小时，客户端自动续约
- 利润报表按天查询最长跨度 31 天
- Review 接口令牌桶容量仅 1，注意控制频率
- AgentCore 执行角色需要 S3 读写权限
