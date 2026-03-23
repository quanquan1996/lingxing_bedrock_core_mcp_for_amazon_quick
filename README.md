# 领星 ERP MCP Server for Amazon Bedrock AgentCore

将领星 ERP 开放 API 封装为 MCP Server，部署到 Amazon Bedrock AgentCore，通过 Amazon Q Business (Quick Suite) 的 Chat / Flows 调用。

> 🚀 **部署用 Kiro：使用 [Kiro](https://kiro.dev) 快速自动配置** — 在 Kiro 中打开本项目，粘贴提示词，Kiro 自动完成 AWS 资源创建、配置文件填写和部署，全程无需手动操作。详见 [Kiro 自动部署指南](#kiro-自动部署)。
>
> 🔌 **接入也用 Kiro：一句提示词接入任意数据 API** — 本项目可作为模板，将任何业务 API 封装为 MCP Server 部署到 AgentCore。粘贴提示词，Kiro 会自动问你接口文档和需求，然后生成代码。详见 [Kiro 接入新的数据 API](#接入新的数据-api)。

## 接入新的数据 API

本项目不仅适用于领星 ERP，你可以用同样的架构将任何业务 API 封装为 MCP Server 并部署到 AgentCore。

在 Kiro 中打开本项目，粘贴以下提示词即可开始：

```
我想基于这个项目的架构，接入一个新的数据 API 并封装为 MCP Server 部署到 AgentCore。

请先问我以下信息：
1. API 接口文档的 URL 或文件路径（你需要阅读理解接口文档）
2. 我希望封装哪些接口、实现哪些功能（比如数据查询、报表生成等）

然后参考本项目中 #mcp-server/lingxing_client.py 和 #mcp-server/mcp_server.py 的代码结构，
以及 #doc/kiro-agentcore-mcp-playbook.md 的部署流程，帮我：
- 创建新的 API 客户端（类似 lingxing_client.py）
- 在 mcp_server.py 中新增对应的 MCP 工具
- 如果需要 Excel 报告生成，也一并实现
- 更新 requirements.txt（如果有新依赖）
```

Kiro 会依次询问你的接口文档和需求范围，然后自动生成代码。

---

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
我 clone 了这个领星 ERP MCP Server 项目，需要部署到我自己的 AWS 账号。请参考 #doc/kiro-agentcore-mcp-playbook.md 和 #doc/deployment-guide.md 帮我完成以下工作：

1. 从 example 模板复制出所有配置文件
2. 自动获取我的 AWS 账号信息（账号 ID、Region）
3. 查找或创建 AgentCore Runtime Role
4. 创建 Cognito 资源（User Pool、Domain、Resource Server、App Client）
5. 创建 S3 存储桶并配置权限
6. 把所有实际值自动填入配置文件

如果缺少任何信息请直接问我。
```

### 提示词 2：部署 + 验证

```
AWS 资源已经配置好了，帮我把 MCP Server 部署到 AgentCore 并验证。需要用到领星的 AppId 和 AppSecret 作为环境变量，部署完成后运行 test_invoke.py 测试端点。如果缺少信息请问我。
```

### 提示词 3：Quick Suite 配置（可选）

```
MCP Server 已部署成功，帮我整理在 Quick Suite 中配置 MCP Action 所需的全部信息（端点 URL、OAuth 认证参数），从现有配置文件中提取即可。
```

## License

MIT
