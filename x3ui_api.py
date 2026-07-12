import aiohttp
import json
import logging
import config

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
        self.base_url = config.XUI_URL.rstrip('/')
        self.username = config.XUI_USER
        self.password = config.XUI_PASS
        self.api_token = config.XUI_TOKEN
        self.cookies = None

    async def login(self) -> bool:
        url = f"{self.base_url}/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Маскируем пароль перед записью в лог
        safe_payload = payload.copy()
        safe_payload["password"] = "***"
        
        logger.info(f"Попытка авторизации в 3X-UI. URL: {url}")
        logger.debug(f"Параметры авторизации: {safe_payload}")

        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(url, data=payload) as r:
                    logger.info(f"Ответ авторизации: HTTP статус {r.status}")
                    response_text = await r.text()
                    logger.debug(f"Сырой ответ авторизации: {response_text}")
                    
                    if r.status == 200:
                        self.cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
                        logger.info("Авторизация успешна. Сессионные куки сохранены.")
                        return True
                    else:
                        logger.error(f"Панель отклонила авторизацию. Статус: {r.status}")
                        return False
        except Exception as e:
            logger.exception(f"Критическая ошибка при попытке авторизации: {e}")
            return False

    async def add_client(self, inbound_id: int, email: str, client_uuid: str, sub_id: str) -> bool:
        logger.info(f"Запрос на добавление клиента: email={email}, uuid={client_uuid}, sub_id={sub_id}")
        
        if not self.cookies:
            logger.info("Сессионные куки отсутствуют. Запуск авторизации...")
            if not await self.login():
                logger.error("Не удалось выполнить автоматический вход. Отмена добавления клиента.")
                return False

        url = f"{self.base_url}/panel/api/clients/add"
        total_bytes = config.TOTAL_GB_LIMIT * 1024 * 1024 * 1024 if config.TOTAL_GB_LIMIT > 0 else 0
        
        payload = {
            "client": {
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
            },
            # Используем динамический inbound_id вместо жестко зашифрованного [1]
            "inboundIds": [inbound_id]
        }

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        logger.info(f"Отправка запроса на добавление клиента. URL: {url}")
        logger.debug(f"Тело запроса (payload): {json.dumps(payload, ensure_ascii=False)}")

        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(cookies=self.cookies, connector=connector, headers=headers) as session:
                async with session.post(url, json=payload) as r:
                    logger.info(f"Ответ добавления клиента: HTTP статус {r.status}")
                    response_text = await r.text()
                    logger.debug(f"Сырой ответ добавления клиента: {response_text}")
                    
                    if r.status == 200:
                        try:
                            res = json.loads(response_text)
                            success = res.get("success", False)
                            msg = res.get("msg", "Нет сообщения")
                            logger.info(f"Результат добавления в API: success={success}, msg='{msg}'")
                            return success
                        except Exception as parse_err:
                            logger.error(f"Не удалось распарсить JSON-ответ от панели: {parse_err}")
                            return False
                    
                    if r.status in (401, 403, 302):
                        logger.warning(f"Ошибка сессии (HTTP {r.status}). Попытка повторной авторизации...")
                        if await self.login():
                            logger.info("Повторная авторизация успешна. Повторный запрос добавления клиента...")
                            async with aiohttp.ClientSession(cookies=self.cookies, connector=connector) as retry_session:
                                async with retry_session.post(url, json=payload) as retry_r:
                                    logger.info(f"Повторный ответ добавления клиента: HTTP статус {retry_r.status}")
                                    retry_text = await retry_r.text()
                                    logger.debug(f"Сырой повторный ответ: {retry_text}")
                                    if retry_r.status == 200:
                                        try:
                                            res = json.loads(retry_text)
                                            return res.get("success", False)
                                        except Exception:
                                            return False
                    
                    logger.error(f"Не удалось добавить клиента. HTTP статус: {r.status}")
                    return False
        except Exception as e:
            logger.exception(f"Критическая ошибка при добавлении клиента: {e}")
            return False

    async def update_client_status(self, inbound_id: int, client_uuid: str, email: str, sub_id: str, enable: bool) -> bool:
        logger.info(f"Запрос на изменение статуса клиента: email={email}, enable={enable}")
        
        if not self.cookies:
            logger.info("Сессионные куки отсутствуют. Запуск авторизации...")
            if not await self.login():
                logger.error("Не удалось выполнить автоматический вход. Отмена обновления статуса.")
                return False

        url = f"{self.base_url}/panel/api/inbounds/update/{email}"
        total_bytes = config.TOTAL_GB_LIMIT * 1024 * 1024 * 1024 if config.TOTAL_GB_LIMIT > 0 else 0

        payload = {
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

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        logger.info(f"Отправка запроса на обновление статуса клиента. URL: {url}")
        logger.debug(f"Тело запроса (payload): {json.dumps(payload, ensure_ascii=False)}")

        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(cookies=self.cookies, connector=connector, headers=headers) as session:
                async with session.post(url, json=payload) as r:
                    logger.info(f"Ответ обновления статуса: HTTP статус {r.status}")
                    response_text = await r.text()
                    logger.debug(f"Сырой ответ обновления статуса: {response_text}")
                    
                    if r.status == 200:
                        try:
                            res = json.loads(response_text)
                            success = res.get("success", False)
                            msg = res.get("msg", "Нет сообщения")
                            logger.info(f"Результат обновления в API: success={success}, msg='{msg}'")
                            return success
                        except Exception as parse_err:
                            logger.error(f"Не удалось распарсить JSON-ответ при обновлении статуса: {parse_err}")
                            return False
                    
                    if r.status in (401, 403, 302):
                        logger.warning(f"Ошибка сессии (HTTP {r.status}). Попытка повторной авторизации...")
                        if await self.login():
                            logger.info("Повторная авторизация успешна. Повторный запрос обновления статуса...")
                            async with aiohttp.ClientSession(cookies=self.cookies, connector=connector) as retry_session:
                                async with retry_session.post(url, json=payload) as retry_r:
                                    logger.info(f"Повторный ответ обновления статуса: HTTP статус {retry_r.status}")
                                    retry_text = await retry_r.text()
                                    logger.debug(f"Сырой повторный ответ: {retry_text}")
                                    if retry_r.status == 200:
                                        try:
                                            res = json.loads(retry_text)
                                            return res.get("success", False)
                                        except Exception:
                                            return False
                    
                    logger.error(f"Не удалось обновить статус клиента. HTTP статус: {r.status}")
                    return False
        except Exception as e:
            logger.exception(f"Критическая ошибка при обновлении статуса клиента: {e}")
            return False