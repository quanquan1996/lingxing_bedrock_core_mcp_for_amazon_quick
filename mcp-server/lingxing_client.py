"""
领星 ERP OpenAPI 客户端
处理认证、签名、令牌管理和 API 调用
"""

import os
import time
import hashlib
import json
import base64
import urllib.parse
from typing import Optional, Any
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import httpx

# 领星 API 基础域名
BASE_URL = "https://openapi.lingxing.com"


class LingxingClient:
    """领星 ERP API 客户端，封装认证和请求逻辑"""

    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id or os.environ.get("LINGXING_APP_ID", "")
        self.app_secret = app_secret or os.environ.get("LINGXING_APP_SECRET", "")
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: float = 0
        self._http = httpx.Client(base_url=BASE_URL, timeout=30)

        if not self.app_id or not self.app_secret:
            print("[WARN] LINGXING_APP_ID / LINGXING_APP_SECRET not set", flush=True)

    # ------------------------------------------------------------------
    # 签名生成
    # ------------------------------------------------------------------
    def _generate_sign(self, params: dict[str, Any]) -> str:
        """
        按领星文档生成 sign：
        1. 所有参数按 ASCII 排序拼接 key=value
        2. MD5 32位大写
        3. AES/ECB/PKCS5 加密，密钥为 appId
        4. URL encode
        """
        # 过滤空值（null 参与，空字符串不参与）
        filtered = {k: v for k, v in params.items() if v is not None and v != ""}
        sorted_keys = sorted(filtered.keys())
        query_str = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)

        # MD5
        md5_hash = hashlib.md5(query_str.encode("utf-8")).hexdigest().upper()

        # AES/ECB/PKCS5Padding，密钥为 appId（需补齐到 16 字节）
        key = self.app_id.encode("utf-8")
        # 补齐到 16 字节
        if len(key) < 16:
            key = key.ljust(16, b"\0")
        elif len(key) > 16:
            key = key[:16]

        cipher = AES.new(key, AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(md5_hash.encode("utf-8"), AES.block_size))
        b64 = base64.b64encode(encrypted).decode("utf-8")

        return urllib.parse.quote(b64, safe="")

    # ------------------------------------------------------------------
    # 令牌管理
    # ------------------------------------------------------------------
    def _ensure_token(self):
        """确保 access_token 有效，过期则刷新或重新获取"""
        if self.access_token and time.time() < self.token_expires_at - 60:
            return
        if self.refresh_token:
            try:
                self._refresh_token()
                return
            except Exception:
                pass
        self._get_token()

    def _get_token(self):
        """获取新的 access_token"""
        resp = self._http.post(
            "/api/auth-server/oauth/access-token",
            data={"appId": self.app_id, "appSecret": self.app_secret},
        )
        data = resp.json()
        if str(data.get("code")) != "200":
            raise Exception(f"获取 token 失败: {data.get('msg', data)}")
        self.access_token = data["data"]["access_token"]
        self.refresh_token = data["data"]["refresh_token"]
        self.token_expires_at = time.time() + data["data"]["expires_in"]
        print(f"[AUTH] 获取新 token 成功，有效期 {data['data']['expires_in']}s", flush=True)

    def _refresh_token(self):
        """续约 access_token"""
        resp = self._http.post(
            "/api/auth-server/oauth/refresh",
            data={"refreshToken": self.refresh_token},
        )
        data = resp.json()
        if str(data.get("code")) != "200":
            raise Exception(f"续约 token 失败: {data.get('msg', data)}")
        self.access_token = data["data"]["access_token"]
        self.refresh_token = data["data"]["refresh_token"]
        self.token_expires_at = time.time() + data["data"]["expires_in"]
        print("[AUTH] 续约 token 成功", flush=True)

    # ------------------------------------------------------------------
    # 通用请求
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        """发送带签名的 API 请求"""
        self._ensure_token()

        timestamp = str(int(time.time()))
        query_params = {
            "access_token": self.access_token,
            "app_key": self.app_id,
            "timestamp": timestamp,
        }

        # 签名需要包含业务参数（跳过 list/dict 复杂类型，boolean 转小写）
        sign_params = {**query_params}
        if body:
            for k, v in body.items():
                if v is None or isinstance(v, (list, dict)):
                    continue
                if isinstance(v, bool):
                    sign_params[k] = str(v).lower()  # True -> "true", False -> "false"
                else:
                    sign_params[k] = v

        query_params["sign"] = self._generate_sign(sign_params)

        if method.upper() == "GET":
            resp = self._http.get(path, params=query_params)
        else:
            resp = self._http.post(path, params=query_params, json=body)

        return resp.json()

    # ------------------------------------------------------------------
    # 业务接口
    # ------------------------------------------------------------------
    def get_seller_list(self) -> dict:
        """查询亚马逊店铺列表"""
        return self._request("GET", "/erp/sc/data/seller/lists")

    def get_profit_by_seller(
        self,
        start_date: str,
        end_date: str,
        sids: list[int] | None = None,
        mids: list[int] | None = None,
        monthly: bool = False,
        currency: str = "CNY",
        order_status: str = "Disbursed",
        offset: int = 0,
        length: int = 1000,
    ) -> dict:
        """查询利润报表-店铺维度"""
        body = {
            "offset": offset,
            "length": length,
            "monthlyQuery": monthly,
            "startDate": start_date,
            "endDate": end_date,
            "currencyCode": currency,
            "orderStatus": order_status,
        }
        if sids:
            body["sids"] = sids
        if mids:
            body["mids"] = mids
        return self._request("POST", "/bd/profit/report/open/report/seller/list", body)

    def get_profit_by_msku(
        self,
        start_date: str,
        end_date: str,
        sids: list[int] | None = None,
        offset: int = 0,
        length: int = 1000,
        currency: str = "CNY",
    ) -> dict:
        """查询利润报表-MSKU 维度"""
        body = {
            "offset": offset,
            "length": length,
            "startDate": start_date,
            "endDate": end_date,
            "currencyCode": currency,
        }
        if sids:
            body["sids"] = sids
        return self._request("POST", "/bd/profit/report/open/report/msku/list", body)

    def get_profit_seller_summary(
        self,
        start_date: str,
        end_date: str,
        sids: list[int] | None = None,
        currency: str = "CNY",
    ) -> dict:
        """查询利润报表-店铺月度汇总（通过 seller/list + monthlyQuery=true 实现）"""
        body = {
            "offset": 0,
            "length": 10000,
            "monthlyQuery": True,
            "startDate": start_date,
            "endDate": end_date,
            "currencyCode": currency,
        }
        if sids:
            body["sids"] = sids
        return self._request("POST", "/bd/profit/report/open/report/seller/list", body)

    def get_profit_by_parent_asin(
        self,
        start_date: str,
        end_date: str,
        sids: list[int] | None = None,
        monthly: bool = False,
        offset: int = 0,
        length: int = 1000,
        currency: str = "CNY",
    ) -> dict:
        """查询利润报表-父ASIN 维度"""
        body = {
            "offset": offset,
            "length": length,
            "monthlyQuery": monthly,
            "startDate": start_date,
            "endDate": end_date,
            "currencyCode": currency,
        }
        if sids:
            body["sids"] = sids
        return self._request("POST", "/bd/profit/report/open/report/parent/asin/list", body)

    def get_profit_by_order(
        self,
        start_date: str,
        end_date: str,
        search_date_field: str = "posted_date_locale",
        sids: list[int] | None = None,
        offset: int = 0,
        length: int = 1000,
        currency: str = "CNY",
    ) -> dict:
        """查询利润报表-订单维度（即将下线，建议用 transaction 视图）"""
        body = {
            "offset": offset,
            "length": length,
            "search_date_field": search_date_field,
            "start_date": start_date,
            "end_date": end_date,
            "currency_code": currency,
        }
        if sids:
            body["sids"] = sids
        return self._request("POST", "/bd/profit/report/open/report/order/list", body)

    def get_profit_seller_summary_v2(
        self,
        start_date: str,
        end_date: str,
        sids: list[int] | None = None,
        monthly: bool = False,
        currency: str = "CNY",
    ) -> dict:
        """查询利润报表-店铺月度汇总（独立接口，日期格式 yyyy-MM-dd）"""
        body = {
            "monthlyQuery": monthly,
            "startDate": start_date,
            "endDate": end_date,
            "currencyCode": currency,
        }
        if sids:
            body["sids"] = sids
        return self._request("POST", "/bd/profit/report/open/report/seller/summary/list", body)

    def get_reviews(
        self,
        start_date: str,
        end_date: str,
        star: str = "1,2,3",
        date_field: str = "review_time",
        sids: str = "",
        offset: int = 0,
        length: int = 200,
        status: str = "0,1,2",
    ) -> dict:
        """查询评价管理-Review（新版），默认查差评 1-3 星"""
        body = {
            "sort_field": "review_date",
            "sort_type": "desc",
            "date_field": date_field,
            "start_date": start_date,
            "end_date": end_date,
            "star": star,
            "offset": offset,
            "length": length,
            "status": status,
        }
        if sids:
            body["sids"] = sids
        return self._request(
            "POST", "/basicOpen/openapi/service/v3/data/mws/reviews", body
        )

