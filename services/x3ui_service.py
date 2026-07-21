import aiohttp
import json
import logging
from config import settings

# Настраиваем именованный логгер
logger = logging.getLogger("x3ui_api")

class X3UiClient:
    def __init__(self):
        self.base_url = settings.XUI_URL.rstrip('/')
        self.api_token = settings.XUI_TOKEN

    async def _make_request(self, endpoint: str, payload: dict) -> bool:
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            try:
                async with session.post(url, json=payload, timeout=10) as r:
                    logger.info(f"Запрос {endpoint}: HTTP статус {r.status}")
                    response_text = await r.text()
                    
                    if r.status == 200:
                        res = json.loads(response_text)
                        return res.get("success", False)
                    logger.error(f"Ошибка API 3X-UI ({r.status}): {response_text}")
                    return False
            except Exception as e:
                logger.exception(f"Критическая ошибка сети с 3X-UI: {e}")
                return False

    async def add_client(self, inbound_id: int, email: str, client_uuid: str, sub_id: str, tg_id: int, expiry_time_ms: int = 0, flow: str = "xtls-rprx-vision") -> bool:
        total_bytes = settings.TOTAL_GB_LIMIT * 1024 * 1024 * 1024 if settings.TOTAL_GB_LIMIT > 0 else 0
        
        payload = {
            "client": {
                "id": client_uuid,
                "alterId": 0,
                "email": email,
                "limitIp": settings.LIMIT_IP,
                "totalGB": total_bytes,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": tg_id,
                "subId": sub_id,
                "flow": flow
            },
            "inboundIds": [inbound_id]
        }

        return await self._make_request("/panel/api/clients/add", payload)

    async def update_client_status(self, inbound_id: int, client_uuid: str, email: str, sub_id: str, enable: bool, tg_id: int, expiry_time_ms: int = 0, flow: str = "xtls-rprx-vision") -> bool:
        total_bytes = settings.TOTAL_GB_LIMIT * 1024 * 1024 * 1024 if settings.TOTAL_GB_LIMIT > 0 else 0

        payload = {
            "id": client_uuid,
            "alterId": 0,
            "email": email,
            "limitIp": settings.LIMIT_IP,
            "totalGB": total_bytes,
            "expiryTime": expiry_time_ms,
            "enable": enable,
            "tgId": tg_id,
            "subId": sub_id,
            "flow": flow
        }

        return await self._make_request(f"/panel/api/clients/update/{email}", payload)