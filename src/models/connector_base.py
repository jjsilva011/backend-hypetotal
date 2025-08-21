"""
Classe base abstrata para conectores de dropshipping.
Define a interface comum que todos os conectores devem implementar.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import requests
import json
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectorStatus(Enum):
    """Status do conector"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class OrderStatus(Enum):
    """Status do pedido no fornecedor"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class ConnectorConfig:
    """Configuração base para conectores"""
    name: str
    api_key: str
    api_secret: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    status: ConnectorStatus = ConnectorStatus.ACTIVE
    additional_config: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_config is None:
            self.additional_config = {}


@dataclass
class Product:
    """Estrutura de produto padronizada"""
    id: str
    name: str
    description: str
    price: float
    currency: str
    stock_quantity: int
    images: List[str]
    variations: List[Dict[str, Any]]
    category: str
    supplier_id: str
    supplier_product_id: str
    shipping_info: Dict[str, Any]
    last_updated: str


@dataclass
class Address:
    """Estrutura de endereço padronizada"""
    full_name: str
    address_line1: str
    address_line2: Optional[str]
    city: str
    state: str
    postal_code: str
    country: str
    phone: str
    email: Optional[str]


@dataclass
class OrderItem:
    """Item do pedido"""
    product_id: str
    supplier_product_id: str
    quantity: int
    price: float
    variation_id: Optional[str] = None
    variation_attributes: Optional[Dict[str, str]] = None


@dataclass
class Order:
    """Estrutura de pedido padronizada"""
    id: str
    items: List[OrderItem]
    shipping_address: Address
    total_amount: float
    currency: str
    shipping_method: str
    notes: Optional[str] = None


@dataclass
class OrderResponse:
    """Resposta da criação de pedido"""
    success: bool
    order_id: Optional[str]
    supplier_order_id: Optional[str]
    tracking_number: Optional[str]
    estimated_delivery: Optional[str]
    message: str
    error_code: Optional[str] = None


@dataclass
class TrackingInfo:
    """Informações de rastreamento"""
    tracking_number: str
    status: OrderStatus
    events: List[Dict[str, Any]]
    estimated_delivery: Optional[str]
    last_updated: str


class BaseConnector(ABC):
    """
    Classe base abstrata para todos os conectores de dropshipping.
    Define a interface comum que todos os conectores devem implementar.
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.timeout
        self._setup_session()

    def _setup_session(self):
        """Configuração inicial da sessão HTTP"""
        self.session.headers.update({
            'User-Agent': f'HypeTotal-Connector/{self.config.name}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Autentica com a API do fornecedor.
        
        Returns:
            bool: True se a autenticação foi bem-sucedida
        """
        pass

    @abstractmethod
    def get_product_details(self, product_id: str, **kwargs) -> Optional[Product]:
        """
        Obtém detalhes de um produto específico.
        
        Args:
            product_id: ID do produto no fornecedor
            **kwargs: Parâmetros adicionais específicos do fornecedor
            
        Returns:
            Product: Objeto produto ou None se não encontrado
        """
        pass

    @abstractmethod
    def search_products(self, query: str, **kwargs) -> List[Product]:
        """
        Busca produtos no catálogo do fornecedor.
        
        Args:
            query: Termo de busca
            **kwargs: Parâmetros adicionais (categoria, preço, etc.)
            
        Returns:
            List[Product]: Lista de produtos encontrados
        """
        pass

    @abstractmethod
    def create_order(self, order: Order) -> OrderResponse:
        """
        Cria um pedido no fornecedor.
        
        Args:
            order: Objeto Order com detalhes do pedido
            
        Returns:
            OrderResponse: Resposta da criação do pedido
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Obtém o status atual de um pedido.
        
        Args:
            order_id: ID do pedido no fornecedor
            
        Returns:
            OrderStatus: Status atual do pedido
        """
        pass

    @abstractmethod
    def get_tracking_info(self, tracking_number: str) -> Optional[TrackingInfo]:
        """
        Obtém informações de rastreamento de um pedido.
        
        Args:
            tracking_number: Número de rastreamento
            
        Returns:
            TrackingInfo: Informações de rastreamento
        """
        pass

    @abstractmethod
    def calculate_shipping(self, items: List[OrderItem], address: Address) -> Dict[str, Any]:
        """
        Calcula opções e custos de envio.
        
        Args:
            items: Lista de itens do pedido
            address: Endereço de entrega
            
        Returns:
            Dict: Opções de envio com custos e prazos
        """
        pass

    @abstractmethod
    def sync_inventory(self, product_ids: List[str]) -> Dict[str, int]:
        """
        Sincroniza estoque de produtos específicos.
        
        Args:
            product_ids: Lista de IDs de produtos para sincronizar
            
        Returns:
            Dict: Mapeamento product_id -> quantidade em estoque
        """
        pass

    def test_connection(self) -> bool:
        """
        Testa a conexão com a API do fornecedor.
        
        Returns:
            bool: True se a conexão está funcionando
        """
        try:
            return self.authenticate()
        except Exception as e:
            logger.error(f"Erro ao testar conexão com {self.config.name}: {e}")
            return False

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Faz uma requisição HTTP com retry automático.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL da requisição
            **kwargs: Parâmetros adicionais para requests
            
        Returns:
            requests.Response: Resposta da requisição
        """
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt + 1} falhou para {url}: {e}")
                if attempt == self.config.max_retries - 1:
                    raise
        
        raise Exception(f"Falha após {self.config.max_retries} tentativas")

    def get_connector_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o conector.
        
        Returns:
            Dict: Informações do conector
        """
        return {
            'name': self.config.name,
            'status': self.config.status.value,
            'base_url': self.config.base_url,
            'timeout': self.config.timeout,
            'max_retries': self.config.max_retries
        }

