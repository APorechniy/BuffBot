# services/payment_service.py
import hashlib
import hmac
import aiohttp
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger("payment_service")

# --- 1. Функция генерации подписи (сигнатуры) ---
def generate_signature(params: dict, secret_key: str) -> str:
    """Генерирует HMAC SHA256 сигнатуру из словаря параметров."""
    # Сортировка ключей в алфавитном порядке
    sorted_keys = sorted(params.keys())

    # Конкатенация значений отсортированных параметров в одну строку
    concatenated_string = "".join(str(params[key]) for key in sorted_keys)

    # Генерация HMAC SHA256 хеша
    signature = hmac.new(
        key=secret_key.encode("utf-8"),
        msg=concatenated_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return signature


# --- 2. Типизированные структуры данных ---

@dataclass
class PaymentInvoice:
    """Типизированный результат создания счета на оплату."""
    id: str
    order_id: str
    payment_url: str
    amount: float
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class PaymentWebhookPayload:
    """Типизированный результат парсинга вебхука от платежного шлюза."""
    order_id: str
    amount: float
    status: str  # Ожидается "success" при успешной оплате
    raw_data: Dict[str, Any]


# --- 3. Абстрактный интерфейс платежей ---

class BasePaymentGateway(ABC):
    """Абстрактный интерфейс для интеграции любых платежных систем."""

    @abstractmethod
    async def create_invoice(self, order_id: str, amount: float, hook_url: str) -> PaymentInvoice:
        """Создает инвойс в платежной системе и возвращает PaymentInvoice."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Проверяет подлинность вебхука (валидность сигнатуры / HMAC)."""
        pass

    @abstractmethod
    def parse_webhook(self, raw_body: bytes, query_params: Dict[str, str]) -> PaymentWebhookPayload:
        """Парсит вебхук от платежной системы и приводит его к единой структуре."""
        pass


# --- 4. Конкретная реализация вашего платежного шлюза ---

class ActivePaymentGateway(BasePaymentGateway):
    def __init__(self):
        self.base_url = settings.PAYMENT_URL.rstrip('/')
        self.shop_id = settings.PAYMENT_SHOP_ID
        self.api_key = settings.PAYMENT_API_KEY
        self.callback_key = settings.PAYMENT_CALLBACK_KEY

    async def create_invoice(self, order_id: str, amount: float, hook_url: str) -> PaymentInvoice:
        url = f"{self.base_url}/invoice/create"
        
        payload = {
            "shop_id": self.shop_id,
            "amount": amount,
            "order_id": order_id,
            "comment": f"Оплата VPN доступа (Заказ #{order_id})",
            "callback_url": hook_url
        }
        
        # Вычисляем подпись исходящего запроса по API_KEY
        signature = generate_signature(payload, self.api_key)
        
        headers = {
            "Content-Type": "application/json",
            "X-SIGNATURE": signature
        }
        
        logger.info(f"Отправка запроса на создание инвойса. URL: {url}, Заказ: {order_id}")
        logger.debug(f"Payload: {payload}")
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=payload, headers=headers) as r:
                logger.info(f"Ответ платежной системы при создании инвойса: HTTP {r.status}")
                response_text = await r.text()
                logger.debug(f"Тело ответа: {response_text}")
                
                if r.status in (200, 201):
                    try:
                        data = json.loads(response_text)
                        # Извлекаем ссылку на оплату
                        payment_url = data.get("link")
                        id = data.get("id")
                        
                        if not payment_url:
                            raise Exception("Ответ API не содержит ссылки на оплату (поле 'link' отсутствует).")
                            
                        return PaymentInvoice(
                            id=id,
                            order_id=order_id,
                            payment_url=payment_url,
                            amount=amount,
                            raw_response=data
                        )
                    except Exception as parse_err:
                        logger.error(f"Не удалось распарсить ответ платежной системы: {parse_err}")
                        raise parse_err
                else:
                    raise Exception(f"Ошибка API платежной системы ({r.status}): {response_text}")

    def verify_webhook_signature(self, raw_body: bytes, headers: dict) -> bool:
        """Проверка входящей сигнатуры по CALLBACK_KEY."""
        signature = headers.get("X-SIGNATURE") or headers.get("x-signature") or headers.get("X-Signature")
        if not signature:
            logger.error("Вебхук отклонен: отсутствует заголовок X-SIGNATURE")
            return False
            
        try:
            data = json.loads(raw_body.decode('utf-8'))
            payload_to_sign = {k: v for k, v in data.items() if k != "sign"}
            
            # Вычисляем проверочную подпись на основе CALLBACK_KEY
            computed_signature = generate_signature(payload_to_sign, self.callback_key)
            
            is_valid = hmac.compare_digest(computed_signature.lower(), signature.lower())
            if not is_valid:
                logger.error(f"Неверная подпись вебхука! Ожидалось: {computed_signature}, Получено: {signature}")
            return is_valid
        except Exception as e:
            logger.exception(f"Исключение при проверке подписи вебхука: {e}")
            return False

    def parse_webhook(self, raw_body: bytes, query_params: dict) -> PaymentWebhookPayload:
        """Парсинг тела успешного вебхука."""
        data = json.loads(raw_body.decode('utf-8'))
        
        order_id = str(data.get("order_id"))
        amount = float(data.get("amount", 0.0))
        status = str(data.get("status", "")).lower()
        
        normalized_status = "success" if status in ("success", "paid", "completed") else status
        
        return PaymentWebhookPayload(
            order_id=order_id,
            amount=amount,
            status=normalized_status,
            raw_data=data
        )