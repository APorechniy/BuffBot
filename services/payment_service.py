# payment_interface.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class PaymentInvoice:
    """Типизированный результат создания счета на оплату."""
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

class BasePaymentGateway(ABC):
    """Абстрактный интерфейс для интеграции любых платежных систем."""

    @abstractmethod
    async def create_invoice(self, order_id: str, amount: float, hook_url: str) -> PaymentInvoice:
        """
        Создает инвойс в платежной системе и возвращает PaymentInvoice.
        
        :param order_id: Уникальный ID заказа в вашей БД.
        :param amount: Сумма платежа.
        :param hook_url: URL-адрес для отправки вебхука.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """
        Проверяет подлинность вебхука (валидность сигнатуры / HMAC).
        
        :param raw_body: Сырые байты тела POST-запроса от шлюза.
        :param headers: Заголовки HTTP-запроса.
        """
        pass

    @abstractmethod
    def parse_webhook(self, raw_body: bytes, query_params: Dict[str, str]) -> PaymentWebhookPayload:
        """
        Парсит вебхук от платежной системы и приводит его к единой структуре.
        
        :param raw_body: Сырые байты тела POST-запроса.
        :param query_params: Параметры строки запроса (если платежка шлет данные GET-ом).
        """
        pass