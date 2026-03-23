# 领星 ERP MCP Server for Amazon Bedrock AgentCore

将领星 ERP 开放 API 封装为 MCP Server，部署到 Amazon Bedrock AgentCore，通过 Amazon Q Business (Quick Suite) 的 Chat / Flows 调用。

> 🚀 **推荐：使用 [Kiro](https://kiro.dev) 快速自动配置**  — 在 Kiro 中打开本项目，将下方提示词粘贴到 Chat 中，Kiro 会自动完成 AWS 资源创建、配置文件填写和部署。详见 [Kiro 自动部署指南](#kiro-自动部署)。

## 架构

```
用户 → Quick Suite (Chat/Flows)
        ↓ OAuth Token
   Cognito (Client Credentials Grant)
        ↓ Bearer Token
   AgentCore Runtime (MCP Server)
        ↓ API 调用
   领星 ERP OpenAPI
        ↓ Excel 报告
   S3 (预签名 URL 下载)
```

## MCP 工具列表

| 工具 | 说明 |
|------|------|
| `get_seller_list` | 查询已授权亚马逊店铺列表 |
| `get_daily_profit` | 每日利润报表（店铺维度） |
| `get_weekly_profit_summary` | 每周利润汇总 |
| `get_monthly_profit_summary` | 月度利润汇总 |
| `get_profit_by_msku` | MSKU 维度利润分析 |
| `get_negative_reviews` | 差评查询（1-3 星） |
| `get_today_negative_reviews` | 今日新增差评 |
| `generate_profit_report_excel` | 生成利润 Excel + S3 下载链接 |
| `generate_negative_review_report_excel` | 生成差评 Excel + S3 下载链接 |

## 快速开始

### 1. 前置条件

- AWS 账号（开通 Bedrock AgentCore、Cognito、S3）
- 领星 ERP 开放接口的 `AppId` 和 `AppSecret`
- Python 3.10+
- `agentcore` CLI：`pip install bedrock-agentcore-starter-toolkit`
- Windows 需要：`choco install zip -y`

### 2. 复制配置文件

```bash
# 从 example 模板创建你自己的配置
cp mcp-server/.bedrock_agentcore.example.yaml mcp-server/.bedrock_agentcore.yaml
cp mcp-server/test_invoke.example.py mcp-server/test_invoke.py
cp doc/deployment-info.example.md doc/deployment-info.md
cp mcp-server/s3-policy.example.json mcp-server/s3-policy.json
cp mcp-server/s3-role-policy.example.json mcp-server/s3-role-policy.json
```

### 3. 配置 AWS 资源

参考 [部署手册](doc/kiro-agentcore-mcp-playbook.md) 完成以下配置：

1. 创建 Cognito User Pool + Resource Server + App Client
2. 创建 S3 存储桶
3. 获取 AgentCore Runtime Role ARN
4. 将实际值填入 `.bedrock_agentcore.yaml`

### 4. 部署

```bash
cd mcp-server
agentcore deploy -a lingxing_erp_mcp \
  --auto-update-on-conflict \
  --env "LINGXING_APP_ID=<YOUR_APP_ID>" \
  --env "LINGXING_APP_SECRET=<YOUR_APP_SECRET>" \
  --env "LINGXING_S3_BUCKET=<YOUR_S3_BUCKET>" \
  --env "LINGXING_S3_PREFIX=lingxing-reports/"
```

### 5. 验证

```bash
# 填入你的配置后运行测试脚本
python test_invoke.py
```

## 项目结构

```
├── doc/
│   ├── deployment-guide.md          # 部署指南
│   ├── deployment-info.example.md   # 部署信息模板（填入你的值）
│   ├── kiro-agentcore-mcp-playbook.md  # Kiro + AgentCore 实战手册
│   └── lingxing-api-guide.md        # 领星 API 接口文档
├── mcp-server/
│   ├── mcp_server.py                # MCP Server 主入口
│   ├── lingxing_client.py           # 领星 API 客户端
│   ├── requirements.txt             # Python 依赖
│   ├── Dockerfile                   # 容器镜像（备用）
│   ├── .bedrock_agentcore.example.yaml  # AgentCore 配置模板
│   ├── test_invoke.example.py       # 测试脚本模板
│   ├── s3-policy.example.json       # S3 权限策略模板
│   ├── s3-role-policy.example.json  # S3 Role 策略模板
│   └── vpc-policy.json              # VPC 权限策略（通用，无敏感信息）
└── README.md
```

## 注意事项

- AgentCore 运行时 `/var/` 只读，日志已重定向到 `/tmp/`
- 领星 `access_token` 有效期 2 小时，客户端自动续约
- 利润报表按天查询最长跨度 31 天
- Review 接口令牌桶容量仅 1，注意控制频率
- 更多踩坑记录见 [实战手册](doc/kiro-agentcore-mcp-playbook.md#四踩坑记录)

## Kiro 自动部署

如果你使用 [Kiro](https://kiro.dev) 作为 IDE，可以跳过手动配置，直接把以下提示词粘贴到 Kiro Chat 中，Kiro 会自动完成所有 AWS 资源创建和部署工作。

### 提示词 1：初始化 AWS 资源 + 配置

```
我 clone 了这个领星 ERP MCP Server 项目，需要部署到我自己的 AWS 账号。请帮我完成以下工作：

1. 先从 example 模板复制出所有配置文件（.bedrock_agentcore.yaml、test_invoke.py、deployment-info.md、s3-policy.json、s3-role-policy.json）
2. 执行 `aws sts get-caller-identity` 获取我的账号 ID 和 Region
3. 查找现有的 AgentCore Runtime Role（`aws iam list-roles --query "Roles[?contains(RoleName, 'AgentCore')]"`），如果没有就告诉我先去 AgentCore 控制台创建一个 Agent
4. 创建 Cognito User Pool（如果还没有的话）、配置 Domain、创建 Resource Server（identifier: lingxing-mcp, scope: invoke）、创建 App Client（Client Credentials Grant）
5. 创建 S3 报告桶 `lingxing-reports-<ACCOUNT_ID>` 和 CodeBuild 桶 `bedrock-agentcore-codebuild-<ACCOUNT_ID>`
6. 给 AgentCore Role 添加 S3 读写权限（用 mcp-server/s3-policy.json）
7. 把所有实际值填入 .bedrock_agentcore.yaml、test_invoke.py、deployment-info.md

参考项目中的 doc/kiro-agentcore-mcp-playbook.md 和 doc/deployment-guide.md 了解完整流程。
```

### 提示词 2：部署 MCP Server

```
AWS 资源已经配置好了，现在帮我部署 MCP Server 到 AgentCore。

我的领星 AppId 是 <YOUR_APP_ID>，AppSecret 是 <YOUR_APP_SECRET>。

请在 mcp-server/ 目录下执行 agentcore deploy，传入环境变量 LINGXING_APP_ID、LINGXING_APP_SECRET、LINGXING_S3_BUCKET、LINGXING_S3_PREFIX。部署完成后用 test_invoke.py 验证 MCP 端点是否正常工作。
```

### 提示词 3：Quick Suite 配置（可选）

```
MCP Server 已经部署成功，帮我整理 Quick Suite 的配置信息：MCP 端点 URL、Cognito OAuth 的 Client ID / Secret / Token URL / Scope，我需要在 Quick Suite > Integrations > Actions 中填入这些值。
```

## License

MIT
