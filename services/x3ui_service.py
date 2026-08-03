import aiohttp
import json
import logging
from config import settings

# Настраиваем именованный логгер
logger = logging.getLogger("x3ui_api")

# Если логгер еще не настроен в основном приложении, настроим базовый вывод в консоль
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)  # Уровень DEBUG для отображения сырых ответов API

class X3UiClient:
    def __init__(self):
        self.base_url = settings.XUI_URL.rstrip('/')
        self.api_token = settings.XUI_TOKEN

    async def add_client(self, inbound_id: int, email: str, client_uuid: str, sub_id: str, tg_id: int, expiry_time_ms: int = 0, total_gb_limit: int = settings.TOTAL_GB_LIMIT) -> bool:
        logger.info(f"Запрос на добавление клиента: email={email}, uuid={client_uuid}, sub_id={sub_id}")

        url = f"{self.base_url}/panel/api/clients/add"
        total_bytes = total_gb_limit * 1024 * 1024 * 1024 if total_gb_limit > 0 else 0
        
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
                "flow": "xtls-rprx-vision"
            },
            "inboundIds": [inbound_id]
        }

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(url, json=payload) as r:
                    response_text = await r.text()
                    
                    if r.status == 200:
                        try:
                            res = json.loads(response_text)
                            success = res.get("success", False)
                            return success
                        except Exception as parse_err:
                            logger.error(f"Не удалось распарсить JSON-ответ от панели: {parse_err}")
                            return False
                    
                    logger.error(f"Не удалось добавить клиента. HTTP статус: {r.status}")
                    return False
        except Exception as e:
            logger.exception(f"Критическая ошибка при добавлении клиента: {e}")
            return False

    async def update_client_status(self, inbound_id: int, client_uuid: str, email: str, sub_id: str, enable: bool, tg_id: int, expiry_time_ms: int = 0, total_gb_limit: int = settings.TOTAL_GB_LIMIT) -> bool:
        url = f"{self.base_url}/panel/api/clients/update/{email}"
        total_bytes = total_gb_limit * 1024 * 1024 * 1024 if total_gb_limit > 0 else 0

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
            "flow": "xtls-rprx-vision"
        }

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(url, json=payload) as r:
                    response_text = await r.text()
                    
                    if r.status == 200:
                        try:
                            res = json.loads(response_text)
                            success = res.get("success", False)
                            return success
                        except Exception as parse_err:
                            logger.error(f"Не удалось распарсить JSON-ответ при обновлении статуса: {parse_err}")
                            return False
                    
                    logger.error(f"Не удалось обновить статус клиента. HTTP статус: {r.status}")
                    return False
        except Exception as e:
            logger.exception(f"Критическая ошибка при обновлении статуса клиента: {e}")
            return False

    async def delete_client(self, inbound_id: int, client_uuid: str) -> bool:
        """
        Полностью и безвозвратно удаляет клиента из входящего подключения панели 3X-UI.
        """
        # Стандартный эндпоинт удаления клиента в API 3X-UI
        url = f"{self.base_url}/panel/api/inbounds/delClient/{client_uuid}"
        
        # Передаем ID входящего подключения и UUID удаляемого клиента
        payload = {
            "id": inbound_id,
            "client": client_uuid
        }

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(url, json=payload) as r:
                    response_text = await r.text()
                    
                    if r.status == 200:
                        try:
                            res = json.loads(response_text)
                            success = res.get("success", False)
                            msg = res.get("msg", "Нет сообщения")
                            return success
                        except Exception as parse_err:
                            logger.error(f"Не удалось распарсить ответ API при удалении: {parse_err}")
                            return False
                    
                    logger.error(f"Не удалось удалить клиента. HTTP статус: {r.status}")
                    return False
        except Exception as e:
            logger.exception(f"Критическая ошибка при удалении клиента: {e}")
            return False