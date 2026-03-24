"""
本地测试所有领星 API 接口
直接调用领星 OpenAPI，区分 IP 限制和权限不足的错误

用法：
  设置环境变量 LINGXING_APP_ID 和 LINGXING_APP_SECRET 后运行
  python test_local_all_apis.py
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lingxing_client import LingxingClient


# ============================================================
# 错误分类规则
# ============================================================
# 领星 API 常见错误码：
#   "200"  -> 成功（授权接口）
#   0      -> 成功（业务接口，新版）
#   "403"  -> 授权失败（IP白名单/权限问题）
#   "2001006" -> sign 签名错误
#   "3001008" -> 限流
#   "1000001" -> 参数错误
#   "4010000" -> token 无效/过期

IP_RESTRICTION_KEYWORDS = [
    "ip", "IP", "白名单", "whitelist", "white list",
    "不在白名单", "not in whitelist", "ip limit",
    "请求IP不在白名单",
]

PERMISSION_KEYWORDS = [
    "权限", "permission", "授权失败", "无权", "forbidden",
    "没有权限", "not authorized", "access denied",
    "请更新授权或检查权限", "未授权",
]


def classify_error(code, msg):
    """
    分类错误类型：
    - SUCCESS: 请求成功
    - IP_RESTRICTED: IP 白名单限制
    - NO_PERMISSION: 没有接口权限
    - SIGN_ERROR: 签名错误
    - TOKEN_ERROR: token 问题
    - RATE_LIMITED: 限流
    - PARAM_ERROR: 参数错误
    - UNKNOWN: 未知错误
    """
    code_str = str(code)
    msg_lower = (msg or "").lower()

    # 成功
    if code_str in ("200", "0"):
        return "SUCCESS"

    # IP 限制检测
    for kw in IP_RESTRICTION_KEYWORDS:
        if kw.lower() in msg_lower:
            return "IP_RESTRICTED"

    # 权限不足检测
    for kw in PERMISSION_KEYWORDS:
        if kw.lower() in msg_lower:
            return "NO_PERMISSION"

    # 403 需要进一步判断
    if code_str == "403":
        # 403 通常是权限问题，但也可能是 IP 限制
        # 如果 msg 里没有明确 IP 关键词，归类为权限问题
        return "NO_PERMISSION"

    # 签名错误
    if code_str == "2001006" or "sign" in msg_lower:
        return "SIGN_ERROR"

    # Token 错误
    if code_str in ("4010000", "401") or "token" in msg_lower:
        return "TOKEN_ERROR"

    # 限流
    if code_str == "3001008" or "rate" in msg_lower or "limit" in msg_lower:
        return "RATE_LIMITED"

    # 参数错误
    if code_str == "1000001" or "param" in msg_lower:
        return "PARAM_ERROR"

    return "UNKNOWN"


def safe_decode_msg(msg):
    """尝试修复乱码的中文消息"""
    if not msg:
        return msg
    try:
        # 尝试 latin-1 -> utf-8 修复
        return msg.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return msg


# ============================================================
# 测试用例定义
# ============================================================
def get_test_cases():
    """定义所有要测试的接口"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_start = datetime.now().strftime("%Y-%m-01")
    this_month = datetime.now().strftime("%Y-%m")
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    return [
        {
            "name": "1. 获取 Token（认证接口）",
            "api_path": "/api/auth-server/oauth/access-token",
            "test_type": "auth",
            "description": "获取 access_token，验证 AppId/AppSecret 是否正确",
        },
        {
            "name": "2. 查询店铺列表",
            "api_path": "/erp/sc/data/seller/lists",
            "method": "GET",
            "body": None,
            "description": "获取所有已授权亚马逊店铺",
        },
        {
            "name": "3. 利润报表-店铺维度（每日）",
            "api_path": "/bd/profit/report/open/report/seller/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "monthlyQuery": False,
                "startDate": week_ago,
                "endDate": yesterday,
                "currencyCode": "CNY",
                "orderStatus": "Disbursed",
            },
            "description": "按店铺维度查询每日利润（含 boolean 参数）",
        },
        {
            "name": "4. 利润报表-店铺月度汇总（monthlyQuery）",
            "api_path": "/bd/profit/report/open/report/seller/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "monthlyQuery": True,
                "startDate": this_month,
                "endDate": this_month,
                "currencyCode": "CNY",
            },
            "description": "通过 seller/list + monthlyQuery=true 实现月度汇总",
        },
        {
            "name": "5. 利润报表-MSKU 维度",
            "api_path": "/bd/profit/report/open/report/msku/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "startDate": week_ago,
                "endDate": yesterday,
                "currencyCode": "CNY",
            },
            "description": "按 MSKU 维度查询利润",
        },
        {
            "name": "6. 利润报表-ASIN 维度",
            "api_path": "/bd/profit/report/open/report/asin/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "startDate": week_ago,
                "endDate": yesterday,
                "currencyCode": "CNY",
            },
            "description": "按 ASIN 维度查询利润",
        },
        {
            "name": "7. 利润报表-父ASIN 维度",
            "api_path": "/bd/profit/report/open/report/parent/asin/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "startDate": week_ago,
                "endDate": yesterday,
                "currencyCode": "CNY",
            },
            "description": "按父 ASIN 维度查询利润（路径已修正：加 /asin）",
        },
        {
            "name": "8. 利润报表-SKU 维度",
            "api_path": "/bd/profit/report/open/report/sku/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "startDate": week_ago,
                "endDate": yesterday,
                "currencyCode": "CNY",
            },
            "description": "按 SKU 维度查询利润",
        },
        {
            "name": "9. 利润报表-订单维度",
            "api_path": "/bd/profit/report/open/report/order/list",
            "method": "POST",
            "body": {
                "offset": 0,
                "length": 10,
                "search_date_field": "posted_date_locale",
                "start_date": week_ago,
                "end_date": yesterday,
                "currency_code": "CNY",
            },
            "description": "按订单维度查询利润（参数已修正：search_date_field + 下划线风格）",
        },
        {
            "name": "10. 利润报表-店铺月度汇总（独立接口）",
            "api_path": "/bd/profit/report/open/report/seller/summary/list",
            "method": "POST",
            "body": {
                "startDate": month_start,
                "endDate": yesterday,
                "currencyCode": "CNY",
            },
            "description": "独立的月度汇总接口（路径已修正：加 /list，日期用 yyyy-MM-dd）",
        },
        {
            "name": "11. 评价管理-Review（新版 v3）",
            "api_path": "/basicOpen/openapi/service/v3/data/mws/reviews",
            "method": "POST",
            "body": {
                "sort_field": "review_date",
                "sort_type": "desc",
                "date_field": "review_time",
                "start_date": week_ago,
                "end_date": today,
                "star": "1,2,3",
                "offset": 0,
                "length": 10,
                "status": "0,1,2",
            },
            "description": "查询 1-3 星差评 Review（推荐使用）",
        },
        {
            "name": "12. 评价管理-Review（旧版）",
            "api_path": "/data/mws/reviews",
            "method": "POST",
            "body": {
                "sort_field": "review_date",
                "sort_type": "desc",
                "date_field": "review_time",
                "start_date": week_ago,
                "end_date": today,
                "star": "1,2,3",
                "offset": 0,
                "length": 10,
            },
            "description": "查询 Review（旧版接口，可能已下线）",
        },
    ]


# ============================================================
# 主测试逻辑
# ============================================================
def main():
    print("=" * 70)
    print("  领星 ERP OpenAPI 本地全接口测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    app_id = os.environ.get("LINGXING_APP_ID", "")
    app_secret = os.environ.get("LINGXING_APP_SECRET", "")

    if not app_id or not app_secret:
        print("\n[ERROR] 请设置环境变量 LINGXING_APP_ID 和 LINGXING_APP_SECRET")
        print("  set LINGXING_APP_ID=your_app_id")
        print("  set LINGXING_APP_SECRET=your_app_secret")
        sys.exit(1)

    print(f"\n  App ID: {app_id[:6]}...{app_id[-4:]}")
    print(f"  App Secret: {app_secret[:4]}...{app_secret[-4:]}")

    client = LingxingClient(app_id, app_secret)
    test_cases = get_test_cases()
    results = []

    # --- 测试 1: 获取 Token ---
    print("\n" + "-" * 70)
    print("  测试 1: 获取 Token（认证接口）")
    print("-" * 70)
    try:
        client._get_token()
        token_result = {
            "name": "1. 获取 Token（认证接口）",
            "api_path": "/api/auth-server/oauth/access-token",
            "status": "SUCCESS",
            "error_type": "SUCCESS",
            "code": "200",
            "msg": "OK",
            "detail": f"token={client.access_token[:20]}..., expires_in={int(client.token_expires_at - time.time())}s",
        }
        print(f"  ✅ 成功 - Token: {client.access_token[:20]}...")
    except Exception as e:
        err_msg = str(e)
        decoded_msg = safe_decode_msg(err_msg)
        error_type = "TOKEN_ERROR"
        if any(kw.lower() in decoded_msg.lower() for kw in IP_RESTRICTION_KEYWORDS):
            error_type = "IP_RESTRICTED"
        token_result = {
            "name": "1. 获取 Token（认证接口）",
            "api_path": "/api/auth-server/oauth/access-token",
            "status": "FAILED",
            "error_type": error_type,
            "code": "N/A",
            "msg": decoded_msg,
            "detail": "",
        }
        print(f"  ❌ 失败 - {decoded_msg}")
        print("\n  [FATAL] Token 获取失败，无法继续测试业务接口")
        results.append(token_result)
        # 标记所有后续接口为未测试
        for tc in test_cases[1:]:
            results.append({
                "name": tc["name"],
                "api_path": tc["api_path"],
                "status": "SKIPPED",
                "error_type": "SKIPPED",
                "code": "-",
                "msg": "Token 获取失败，跳过",
                "detail": "",
            })
        print_summary(results)
        save_results(results)
        return

    results.append(token_result)

    # --- 测试业务接口 ---
    for tc in test_cases[1:]:
        print(f"\n{'-' * 70}")
        print(f"  测试 {tc['name']}")
        print(f"  Path: {tc['api_path']}")
        print(f"-" * 70)

        time.sleep(0.5)  # 避免限流

        try:
            resp = client._request(tc["method"], tc["api_path"], tc.get("body"))

            # 提取 code 和 msg
            code = resp.get("code", resp.get("status", "N/A"))
            msg = resp.get("msg", resp.get("message", ""))
            decoded_msg = safe_decode_msg(str(msg))

            error_type = classify_error(code, decoded_msg)

            # 提取数据摘要
            detail = ""
            if error_type == "SUCCESS":
                data = resp.get("data", None)
                if isinstance(data, list):
                    detail = f"返回 {len(data)} 条记录"
                elif isinstance(data, dict):
                    records = data.get("records", data.get("list", []))
                    total = data.get("total", len(records) if isinstance(records, list) else 0)
                    detail = f"返回 {len(records) if isinstance(records, list) else '?'} 条记录, total={total}"
                total_field = resp.get("total", None)
                if total_field is not None:
                    detail = f"返回记录, total={total_field}"

            result = {
                "name": tc["name"],
                "api_path": tc["api_path"],
                "status": "OK" if error_type == "SUCCESS" else "FAILED",
                "error_type": error_type,
                "code": str(code),
                "msg": decoded_msg,
                "detail": detail,
            }
            results.append(result)

            if error_type == "SUCCESS":
                print(f"  ✅ 成功 - code={code}, {detail}")
            else:
                print(f"  ❌ 失败 - [{error_type}] code={code}, msg={decoded_msg}")

        except Exception as e:
            err_msg = safe_decode_msg(str(e))
            results.append({
                "name": tc["name"],
                "api_path": tc["api_path"],
                "status": "ERROR",
                "error_type": "EXCEPTION",
                "code": "N/A",
                "msg": err_msg,
                "detail": "",
            })
            print(f"  💥 异常 - {err_msg}")

    print_summary(results)
    save_results(results)


def print_summary(results):
    """打印测试总结"""
    print("\n" + "=" * 70)
    print("  测试结果总结")
    print("=" * 70)

    # 分类统计
    categories = {}
    for r in results:
        et = r["error_type"]
        if et not in categories:
            categories[et] = []
        categories[et].append(r)

    # 打印统计
    print(f"\n  总计测试: {len(results)} 个接口\n")

    type_labels = {
        "SUCCESS": "✅ 成功",
        "IP_RESTRICTED": "🔒 IP 白名单限制",
        "NO_PERMISSION": "🚫 没有接口权限",
        "SIGN_ERROR": "🔑 签名错误",
        "TOKEN_ERROR": "🔐 Token 错误",
        "RATE_LIMITED": "⏱️  限流",
        "PARAM_ERROR": "📝 参数错误",
        "EXCEPTION": "💥 异常",
        "SKIPPED": "⏭️  跳过",
        "UNKNOWN": "❓ 未知错误",
    }

    for et, label in type_labels.items():
        if et in categories:
            items = categories[et]
            print(f"  {label}: {len(items)} 个")
            for item in items:
                print(f"    - {item['name']}")
                if item.get("detail"):
                    print(f"      {item['detail']}")
                if et not in ("SUCCESS", "SKIPPED") and item.get("msg"):
                    print(f"      msg: {item['msg'][:100]}")

    # 详细表格
    print(f"\n{'─' * 90}")
    print(f"  {'接口名称':<35} {'状态':<12} {'错误类型':<18} {'code':<10}")
    print(f"{'─' * 90}")
    for r in results:
        status_icon = {"OK": "✅", "FAILED": "❌", "ERROR": "💥", "SKIPPED": "⏭️"}.get(r["status"], "?")
        print(f"  {status_icon} {r['name']:<33} {r['status']:<10} {r['error_type']:<16} {r['code']:<10}")
    print(f"{'─' * 90}")


def save_results(results):
    """保存测试结果到 JSON"""
    output = {
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "summary": {},
        "results": results,
    }

    # 统计
    for r in results:
        et = r["error_type"]
        output["summary"][et] = output["summary"].get(et, 0) + 1

    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "local_api_test_results.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存到: {os.path.abspath(filepath)}")


if __name__ == "__main__":
    main()
