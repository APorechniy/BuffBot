# x3ui_api.py (с отключенной проверкой SSL для локальных запросов)
import aiohttp
import json
import config

class X3UiClient:
    def __init__(self):
        self.base_url = config.XUI_URL
        self.username = config.XUI_USER
        self.password = config.XUI_PASS
        self.cookies = None

    async def login(self) -> bool:
        url = f"{self.base_url}"
        payload = {
            "username": self.username,
            "password": self.password
        }
        # Используем TCPConnector с отключенной проверкой SSL
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, data=payload) as r:
                if r.status == 200:
                    self.cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
                    return True
                return False

    async def add_client(self, inbound_id: int, email: str, client_uuid: str, sub_id: str) -> bool:
        if not self.cookies and not await self.login():
            return False

        url = f"{self.base_url}panel/api/inbounds/addClient"
        total_bytes = config.TOTAL_GB_LIMIT * 1024 * 1024 * 1024 if config.TOTAL_GB_LIMIT > 0 else 0
        
        client_settings = {
            "clients": [
                {
                    "id": client_uuid,
                    "alterId": 0,
                    "email": email,
                    "limitIp": config.LIMIT_IP,
                    "totalGB": total_bytes,
                    "expiryTime": 0,
                    "enable": True,
                    "tgId": "",
                    "subId": sub_id,
                    "flow": "xtls-rprx-vision"
                }
            ]
        }
        
        payload = {
            "id": inbound_id,
            "settings": json.dumps(client_settings)
        }

        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(cookies=self.cookies, connector=connector) as session:
            async with session.post(url, json=payload) as r:
                if r.status == 200:
                    res = await r.json()
                    return res.get("success", False)
                if r.status in (401, 403, 302):
                    if await self.login():
                        async with aiohttp.ClientSession(cookies=self.cookies, connector=connector) as retry_session:
                            async with retry_session.post(url, json=payload) as retry_r:
                                if retry_r.status == 200:
                                    res = await retry_r.json()
                                    return res.get("success", False)
                return False

    async def update_client_status(self, inbound_id: int, client_uuid: str, email: str, sub_id: str, enable: bool) -> bool:
        if not self.cookies and not await self.login():
            return False

        url = f"{self.base_url}panel/api/inbounds/updateClient/{client_uuid}"
        total_bytes = config.TOTAL_GB_LIMIT * 1024 * 1024 * 1024 if config.TOTAL_GB_LIMIT > 0 else 0
        
        client_settings = {
            "clients": [
                {
                    "id": client_uuid,
                    "alterId": 0,
                    "email": email,
                    "limitIp": config.LIMIT_IP,
                    "totalGB": total_bytes,
                    "expiryTime": 0,
                    "enable": enable,
                    "tgId": "",
                    "subId": sub_id,
                    "flow": "xtls-rprx-vision"
                }
            ]
        }
        
        payload = {
            "id": inbound_id,
            "settings": json.dumps(client_settings)
        }

        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(cookies=self.cookies, connector=connector) as session:
            async with session.post(url, json=payload) as r:
                if r.status == 200:
                    res = await r.json()
                    return res.get("success", False)
                if r.status in (401, 403, 302):
                    if await self.login():
                        async with aiohttp.ClientSession(cookies=self.cookies, connector=connector) as retry_session:
                            async with retry_session.post(url, json=payload) as retry_r:
                                if retry_r.status == 200:
                                    res = await retry_r.json()
                                    return res.get("success", False)
                return False