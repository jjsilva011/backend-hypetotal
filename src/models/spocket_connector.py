"""
Conector específico para Spocket Dropshipping API.
Implementa todas as funcionalidades necessárias para integração com o Spocket.
"""

import hashlib
import hmac
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from src.models.connector_base import (
    BaseConnector, ConnectorConfig, Product, Order, OrderResponse, 
    TrackingInfo, Address, OrderItem, OrderStatus
)
import logging

logger = logging.getLogger(__name__)


class SpocketConnector(BaseConnector):
    """
    Conector para Spocket Dropshipping API.
    Implementa autenticação, busca de produtos, criação de pedidos e rastreamento.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.api_secret = config.api_secret
        
        # URLs da API do Spocket
        self.api_base_url = config.base_url or "https://api.spocket.co/api/v1"
        
        # Configurações específicas do Spocket
        self.default_country = config.additional_config.get('default_country', 'US')
        self.default_currency = config.additional_config.get('default_currency', 'USD')

    def _build_headers(self) -> Dict[str, str]:
        """
        Constrói os headers necessários para requisições da API.
        
        Returns:
            Dict: Headers da requisição
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        return headers

    def authenticate(self) -> bool:
        """
        Autentica com a API do Spocket.
        Para o Spocket, isso verifica se a API key é válida.
        
        Returns:
            bool: True se autenticado com sucesso
        """
        try:
            # Testa a API key fazendo uma chamada simples
            return self._test_api_key()
            
        except Exception as e:
            logger.error(f"Erro na autenticação Spocket: {e}")
            return False

    def _test_api_key(self) -> bool:
        """
        Testa se a API key atual é válida fazendo uma chamada de teste.
        
        Returns:
            bool: True se a API key é válida
        """
        try:
            url = f"{self.api_base_url}/products"
            params = {'page': 1, 'per_page': 1}
            
            headers = self._build_headers()
            response = self._make_request('GET', url, params=params, headers=headers)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erro ao testar API key Spocket: {e}")
            return False

    def get_product_details(self, product_id: str, **kwargs) -> Optional[Product]:
        """
        Obtém detalhes de um produto específico do Spocket.
        
        Args:
            product_id: ID do produto no Spocket
            **kwargs: Parâmetros adicionais
            
        Returns:
            Product: Objeto produto ou None se não encontrado
        """
        try:
            url = f"{self.api_base_url}/products/{product_id}"
            
            headers = self._build_headers()
            response = self._make_request('GET', url, headers=headers)
            result = response.json()
            
            if 'product' in result:
                product_data = result['product']
                return self._parse_product_data(product_data)
            else:
                logger.error(f"Spocket: Erro ao obter produto {product_id}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Spocket: Erro ao obter detalhes do produto {product_id}: {e}")
            return None

    def search_products(self, query: str, **kwargs) -> List[Product]:
        """
        Busca produtos no catálogo do Spocket.
        
        Args:
            query: Termo de busca
            **kwargs: Parâmetros adicionais (category, min_price, max_price, etc.)
            
        Returns:
            List[Product]: Lista de produtos encontrados
        """
        try:
            url = f"{self.api_base_url}/products"
            
            params = {
                'page': kwargs.get('page', 1),
                'per_page': kwargs.get('page_size', 20),
                'search': query
            }
            
            # Adiciona filtros opcionais
            if kwargs.get('category'):
                params['category'] = kwargs['category']
            if kwargs.get('min_price'):
                params['min_price'] = kwargs['min_price']
            if kwargs.get('max_price'):
                params['max_price'] = kwargs['max_price']
            if kwargs.get('country'):
                params['country'] = kwargs['country']
            
            headers = self._build_headers()
            response = self._make_request('GET', url, params=params, headers=headers)
            result = response.json()
            
            products = []
            if 'products' in result:
                for product_data in result['products']:
                    product = self._parse_product_data(product_data)
                    if product:
                        products.append(product)
            
            logger.info(f"Spocket: Encontrados {len(products)} produtos para '{query}'")
            return products
            
        except Exception as e:
            logger.error(f"Spocket: Erro ao buscar produtos: {e}")
            return []

    def create_order(self, order: Order) -> OrderResponse:
        """
        Cria um pedido no Spocket.
        
        Args:
            order: Objeto Order com detalhes do pedido
            
        Returns:
            OrderResponse: Resposta da criação do pedido
        """
        try:
            url = f"{self.api_base_url}/orders"
            
            # Constrói o endereço de entrega
            shipping_address = {
                'first_name': order.shipping_address.full_name.split()[0] if order.shipping_address.full_name else '',
                'last_name': ' '.join(order.shipping_address.full_name.split()[1:]) if len(order.shipping_address.full_name.split()) > 1 else '',
                'address1': order.shipping_address.address_line1,
                'address2': order.shipping_address.address_line2 or '',
                'city': order.shipping_address.city,
                'province': order.shipping_address.state,
                'zip': order.shipping_address.postal_code,
                'country': order.shipping_address.country,
                'phone': order.shipping_address.phone,
                'email': order.shipping_address.email or ''
            }
            
            # Constrói os itens do pedido
            line_items = []
            for item in order.items:
                line_item = {
                    'product_id': item.supplier_product_id,
                    'variant_id': item.variation_id or '',
                    'quantity': item.quantity,
                    'price': str(item.price)
                }
                line_items.append(line_item)
            
            # Parâmetros da API
            order_data = {
                'order': {
                    'order_number': order.id,
                    'shipping_address': shipping_address,
                    'line_items': line_items,
                    'note': order.notes or f'Order {order.id}',
                    'currency': order.currency
                }
            }
            
            headers = self._build_headers()
            response = self._make_request('POST', url, json=order_data, headers=headers)
            result = response.json()
            
            if 'order' in result and result.get('success', False):
                order_result = result['order']
                
                return OrderResponse(
                    success=True,
                    order_id=order.id,
                    supplier_order_id=str(order_result.get('id', '')),
                    tracking_number=order_result.get('tracking_number'),
                    estimated_delivery=order_result.get('estimated_delivery'),
                    message="Pedido criado com sucesso"
                )
            else:
                error_msg = result.get('message', 'Erro desconhecido')
                return OrderResponse(
                    success=False,
                    order_id=None,
                    supplier_order_id=None,
                    tracking_number=None,
                    estimated_delivery=None,
                    message=f"Erro ao criar pedido: {error_msg}",
                    error_code=result.get('error_code')
                )
                
        except Exception as e:
            logger.error(f"Spocket: Erro ao criar pedido: {e}")
            return OrderResponse(
                success=False,
                order_id=None,
                supplier_order_id=None,
                tracking_number=None,
                estimated_delivery=None,
                message=f"Erro interno: {str(e)}",
                error_code="INTERNAL_ERROR"
            )

    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Obtém o status atual de um pedido.
        
        Args:
            order_id: ID do pedido no Spocket
            
        Returns:
            OrderStatus: Status atual do pedido
        """
        try:
            url = f"{self.api_base_url}/orders/{order_id}"
            
            headers = self._build_headers()
            response = self._make_request('GET', url, headers=headers)
            result = response.json()
            
            if 'order' in result:
                order_data = result['order']
                
                # Mapeia status do Spocket para nosso enum
                status_mapping = {
                    'pending': OrderStatus.PENDING,
                    'processing': OrderStatus.PROCESSING,
                    'shipped': OrderStatus.SHIPPED,
                    'delivered': OrderStatus.DELIVERED,
                    'cancelled': OrderStatus.CANCELLED,
                    'failed': OrderStatus.FAILED
                }
                
                spocket_status = order_data.get('status', 'pending').lower()
                return status_mapping.get(spocket_status, OrderStatus.PENDING)
            
            return None
            
        except Exception as e:
            logger.error(f"Spocket: Erro ao obter status do pedido {order_id}: {e}")
            return None

    def get_tracking_info(self, tracking_number: str) -> Optional[TrackingInfo]:
        """
        Obtém informações de rastreamento de um pedido.
        
        Args:
            tracking_number: Número de rastreamento ou ID do pedido
            
        Returns:
            TrackingInfo: Informações de rastreamento
        """
        try:
            url = f"{self.api_base_url}/orders/{tracking_number}/tracking"
            
            headers = self._build_headers()
            response = self._make_request('GET', url, headers=headers)
            result = response.json()
            
            if 'tracking' in result:
                tracking_data = result['tracking']
                
                # Mapeia status para nosso enum
                status_mapping = {
                    'pending': OrderStatus.PENDING,
                    'processing': OrderStatus.PROCESSING,
                    'shipped': OrderStatus.SHIPPED,
                    'delivered': OrderStatus.DELIVERED,
                    'exception': OrderStatus.FAILED
                }
                
                status = status_mapping.get(tracking_data.get('status', 'pending').lower(), OrderStatus.PENDING)
                
                # Constrói eventos de rastreamento
                events = []
                if tracking_data.get('events'):
                    for event in tracking_data['events']:
                        events.append({
                            'date': event.get('timestamp'),
                            'description': event.get('description'),
                            'location': event.get('location', '')
                        })
                
                return TrackingInfo(
                    tracking_number=tracking_data.get('tracking_number', tracking_number),
                    status=status,
                    events=events,
                    estimated_delivery=tracking_data.get('estimated_delivery'),
                    last_updated=datetime.now().isoformat()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Spocket: Erro ao obter rastreamento {tracking_number}: {e}")
            return None

    def calculate_shipping(self, items: List[OrderItem], address: Address) -> Dict[str, Any]:
        """
        Calcula opções e custos de envio.
        
        Args:
            items: Lista de itens do pedido
            address: Endereço de entrega
            
        Returns:
            Dict: Opções de envio com custos e prazos
        """
        try:
            url = f"{self.api_base_url}/shipping/calculate"
            
            # Constrói lista de produtos para cálculo
            products = []
            for item in items:
                products.append({
                    'product_id': item.supplier_product_id,
                    'variant_id': item.variation_id or '',
                    'quantity': item.quantity
                })
            
            shipping_data = {
                'destination': {
                    'country': address.country,
                    'province': address.state,
                    'city': address.city,
                    'zip': address.postal_code
                },
                'products': products
            }
            
            headers = self._build_headers()
            response = self._make_request('POST', url, json=shipping_data, headers=headers)
            result = response.json()
            
            shipping_options = []
            if 'shipping_rates' in result:
                for rate in result['shipping_rates']:
                    shipping_options.append({
                        'service_name': rate.get('name'),
                        'cost': rate.get('price'),
                        'currency': rate.get('currency', 'USD'),
                        'delivery_time': rate.get('delivery_time'),
                        'description': rate.get('description', '')
                    })
            
            return {
                'options': shipping_options,
                'currency': 'USD',
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Spocket: Erro ao calcular frete: {e}")
            return {'error': str(e)}

    def sync_inventory(self, product_ids: List[str]) -> Dict[str, int]:
        """
        Sincroniza estoque de produtos específicos.
        
        Args:
            product_ids: Lista de IDs de produtos para sincronizar
            
        Returns:
            Dict: Mapeamento product_id -> quantidade em estoque
        """
        inventory = {}
        
        for product_id in product_ids:
            try:
                product = self.get_product_details(product_id)
                if product:
                    inventory[product_id] = product.stock_quantity
                else:
                    inventory[product_id] = 0
                    
            except Exception as e:
                logger.error(f"Spocket: Erro ao sincronizar estoque do produto {product_id}: {e}")
                inventory[product_id] = 0
        
        return inventory

    def _parse_product_data(self, product_data: Dict[str, Any]) -> Product:
        """
        Converte dados do produto da API do Spocket para nosso formato padrão.
        
        Args:
            product_data: Dados do produto da API
            
        Returns:
            Product: Objeto produto padronizado
        """
        # Extrai imagens
        images = []
        if product_data.get('images'):
            for image in product_data['images']:
                if isinstance(image, dict):
                    images.append(image.get('src', ''))
                else:
                    images.append(str(image))
        
        # Extrai variações
        variations = []
        if product_data.get('variants'):
            for variant in product_data['variants']:
                variations.append({
                    'variant_id': variant.get('id'),
                    'sku': variant.get('sku'),
                    'price': variant.get('price'),
                    'stock': variant.get('inventory_quantity'),
                    'title': variant.get('title'),
                    'option1': variant.get('option1'),
                    'option2': variant.get('option2'),
                    'option3': variant.get('option3')
                })
        
        # Informações de envio
        shipping_info = {
            'origin_country': product_data.get('origin_country'),
            'processing_time': product_data.get('processing_time'),
            'shipping_time': product_data.get('shipping_time')
        }
        
        return Product(
            id=str(product_data.get('id', '')),
            name=product_data.get('title', ''),
            description=product_data.get('description', ''),
            price=float(product_data.get('price', 0)),
            currency='USD',
            stock_quantity=int(product_data.get('inventory_quantity', 0)),
            images=images,
            variations=variations,
            category=product_data.get('product_type', ''),
            supplier_id='spocket',
            supplier_product_id=str(product_data.get('id', '')),
            shipping_info=shipping_info,
            last_updated=datetime.now().isoformat()
        )

