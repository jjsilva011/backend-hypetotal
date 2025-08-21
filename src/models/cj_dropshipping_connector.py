"""
Conector específico para CJ Dropshipping API.
Implementa todas as funcionalidades necessárias para integração com o CJ Dropshipping.
"""

import hashlib
import hmac
import time
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from src.models.connector_base import (
    BaseConnector, ConnectorConfig, Product, Order, OrderResponse, 
    TrackingInfo, Address, OrderItem, OrderStatus
)
import logging

logger = logging.getLogger(__name__)


class CJDropshippingConnector(BaseConnector):
    """
    Conector para CJ Dropshipping API.
    Implementa autenticação, busca de produtos, criação de pedidos e rastreamento.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.access_key = config.api_key
        self.secret_key = config.api_secret
        self.access_token = config.additional_config.get('access_token')
        
        # URLs da API do CJ Dropshipping
        self.api_base_url = config.base_url or "https://developers.cjdropshipping.com/api2.0/v1"
        
        # Configurações específicas do CJ Dropshipping
        self.default_country = config.additional_config.get('default_country', 'US')
        self.default_currency = config.additional_config.get('default_currency', 'USD')
        self.warehouse_id = config.additional_config.get('warehouse_id', 'CN')

    def _generate_signature(self, method: str, path: str, params: Dict[str, Any], timestamp: str) -> str:
        """
        Gera a assinatura necessária para autenticar requisições na API do CJ Dropshipping.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            path: Caminho da API
            params: Parâmetros da requisição
            timestamp: Timestamp da requisição
            
        Returns:
            str: Assinatura HMAC-SHA256
        """
        # Ordena os parâmetros alfabeticamente
        sorted_params = sorted(params.items()) if params else []
        
        # Constrói a string de consulta
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # Constrói a string para assinar
        string_to_sign = f"{method}\n{path}\n{query_string}\n{timestamp}"
        
        # Gera a assinatura HMAC-SHA256
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Codifica em base64
        return base64.b64encode(signature).decode('utf-8')

    def _build_headers(self, method: str, path: str, params: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Constrói os headers necessários para requisições da API.
        
        Args:
            method: Método HTTP
            path: Caminho da API
            params: Parâmetros da requisição
            
        Returns:
            Dict: Headers da requisição
        """
        timestamp = str(int(time.time()))
        signature = self._generate_signature(method, path, params, timestamp)
        
        headers = {
            'Content-Type': 'application/json',
            'CJ-Access-Token': self.access_token or '',
            'CJ-Access-Key': self.access_key,
            'CJ-Timestamp': timestamp,
            'CJ-Signature': signature
        }
        
        return headers

    def authenticate(self) -> bool:
        """
        Autentica com a API do CJ Dropshipping.
        Para o CJ Dropshipping, isso obtém um access token usando as credenciais.
        
        Returns:
            bool: True se autenticado com sucesso
        """
        try:
            if self.access_token:
                # Testa o token atual
                return self._test_token()
            
            # Obtém novo token
            return self._get_access_token()
            
        except Exception as e:
            logger.error(f"Erro na autenticação CJ Dropshipping: {e}")
            return False

    def _get_access_token(self) -> bool:
        """
        Obtém um access token usando as credenciais.
        
        Returns:
            bool: True se obtido com sucesso
        """
        try:
            path = "/authentication/getAccessToken"
            url = f"{self.api_base_url}{path}"
            
            # Parâmetros para obter token
            params = {
                'accessKey': self.access_key,
                'secretKey': self.secret_key
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = self._make_request('POST', url, json=params, headers=headers)
            result = response.json()
            
            if result.get('result') and result.get('data'):
                self.access_token = result['data'].get('accessToken')
                logger.info("CJ Dropshipping: Token obtido com sucesso")
                return True
            else:
                logger.error(f"CJ Dropshipping: Erro ao obter token: {result}")
                return False
                
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao obter token: {e}")
            return False

    def _test_token(self) -> bool:
        """
        Testa se o token atual é válido fazendo uma chamada de teste.
        
        Returns:
            bool: True se o token é válido
        """
        try:
            path = "/product/list"
            url = f"{self.api_base_url}{path}"
            
            params = {
                'pageNum': 1,
                'pageSize': 1
            }
            
            headers = self._build_headers('GET', path, params)
            response = self._make_request('GET', url, params=params, headers=headers)
            result = response.json()
            
            return result.get('result', False)
            
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao testar token: {e}")
            return False

    def get_product_details(self, product_id: str, **kwargs) -> Optional[Product]:
        """
        Obtém detalhes de um produto específico do CJ Dropshipping.
        
        Args:
            product_id: ID do produto no CJ Dropshipping
            **kwargs: Parâmetros adicionais
            
        Returns:
            Product: Objeto produto ou None se não encontrado
        """
        try:
            path = "/product/query"
            url = f"{self.api_base_url}{path}"
            
            params = {
                'pid': product_id
            }
            
            headers = self._build_headers('GET', path, params)
            response = self._make_request('GET', url, params=params, headers=headers)
            result = response.json()
            
            if result.get('result') and result.get('data'):
                product_data = result['data']
                return self._parse_product_data(product_data)
            else:
                logger.error(f"CJ Dropshipping: Erro ao obter produto {product_id}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao obter detalhes do produto {product_id}: {e}")
            return None

    def search_products(self, query: str, **kwargs) -> List[Product]:
        """
        Busca produtos no catálogo do CJ Dropshipping.
        
        Args:
            query: Termo de busca
            **kwargs: Parâmetros adicionais (category, min_price, max_price, etc.)
            
        Returns:
            List[Product]: Lista de produtos encontrados
        """
        try:
            path = "/product/list"
            url = f"{self.api_base_url}{path}"
            
            params = {
                'pageNum': kwargs.get('page', 1),
                'pageSize': kwargs.get('page_size', 20),
                'keywords': query
            }
            
            # Adiciona filtros opcionais
            if kwargs.get('category_id'):
                params['categoryId'] = kwargs['category_id']
            if kwargs.get('min_price'):
                params['minPrice'] = kwargs['min_price']
            if kwargs.get('max_price'):
                params['maxPrice'] = kwargs['max_price']
            if kwargs.get('warehouse_id'):
                params['warehouseId'] = kwargs['warehouse_id']
            
            headers = self._build_headers('GET', path, params)
            response = self._make_request('GET', url, params=params, headers=headers)
            result = response.json()
            
            products = []
            if result.get('result') and result.get('data', {}).get('list'):
                for product_data in result['data']['list']:
                    product = self._parse_product_data(product_data)
                    if product:
                        products.append(product)
            
            logger.info(f"CJ Dropshipping: Encontrados {len(products)} produtos para '{query}'")
            return products
            
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao buscar produtos: {e}")
            return []

    def create_order(self, order: Order) -> OrderResponse:
        """
        Cria um pedido no CJ Dropshipping.
        
        Args:
            order: Objeto Order com detalhes do pedido
            
        Returns:
            OrderResponse: Resposta da criação do pedido
        """
        try:
            path = "/shopping/order/createOrder"
            url = f"{self.api_base_url}{path}"
            
            # Constrói o endereço de entrega
            shipping_address = {
                'firstName': order.shipping_address.full_name.split()[0] if order.shipping_address.full_name else '',
                'lastName': ' '.join(order.shipping_address.full_name.split()[1:]) if len(order.shipping_address.full_name.split()) > 1 else '',
                'address': order.shipping_address.address_line1,
                'address2': order.shipping_address.address_line2 or '',
                'city': order.shipping_address.city,
                'state': order.shipping_address.state,
                'zip': order.shipping_address.postal_code,
                'country': order.shipping_address.country,
                'phone': order.shipping_address.phone,
                'email': order.shipping_address.email or ''
            }
            
            # Constrói os itens do pedido
            products = []
            for item in order.items:
                product_item = {
                    'pid': item.supplier_product_id,
                    'vid': item.variation_id or '',
                    'quantity': item.quantity,
                    'shippingMethod': order.shipping_method or 'CJ_PACKET'
                }
                products.append(product_item)
            
            # Parâmetros da API
            order_data = {
                'orderNumber': order.id,
                'shippingAddress': shipping_address,
                'products': products,
                'remark': order.notes or f'Order {order.id}'
            }
            
            headers = self._build_headers('POST', path)
            response = self._make_request('POST', url, json=order_data, headers=headers)
            result = response.json()
            
            if result.get('result') and result.get('data'):
                order_result = result['data']
                
                return OrderResponse(
                    success=True,
                    order_id=order.id,
                    supplier_order_id=order_result.get('orderId', ''),
                    tracking_number=None,  # Será obtido posteriormente
                    estimated_delivery=None,
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
                    error_code=result.get('code')
                )
                
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao criar pedido: {e}")
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
            order_id: ID do pedido no CJ Dropshipping
            
        Returns:
            OrderStatus: Status atual do pedido
        """
        try:
            path = "/shopping/order/getOrderDetail"
            url = f"{self.api_base_url}{path}"
            
            params = {
                'orderId': order_id
            }
            
            headers = self._build_headers('GET', path, params)
            response = self._make_request('GET', url, params=params, headers=headers)
            result = response.json()
            
            if result.get('result') and result.get('data'):
                order_data = result['data']
                
                # Mapeia status do CJ Dropshipping para nosso enum
                status_mapping = {
                    'PENDING': OrderStatus.PENDING,
                    'PROCESSING': OrderStatus.PROCESSING,
                    'SHIPPED': OrderStatus.SHIPPED,
                    'DELIVERED': OrderStatus.DELIVERED,
                    'CANCELLED': OrderStatus.CANCELLED,
                    'FAILED': OrderStatus.FAILED
                }
                
                cj_status = order_data.get('orderStatus', 'PENDING')
                return status_mapping.get(cj_status, OrderStatus.PENDING)
            
            return None
            
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao obter status do pedido {order_id}: {e}")
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
            path = "/logistic/getTrackNumber"
            url = f"{self.api_base_url}{path}"
            
            params = {
                'orderId': tracking_number
            }
            
            headers = self._build_headers('GET', path, params)
            response = self._make_request('GET', url, params=params, headers=headers)
            result = response.json()
            
            if result.get('result') and result.get('data'):
                tracking_data = result['data']
                
                # Mapeia status para nosso enum
                status_mapping = {
                    'PENDING': OrderStatus.PENDING,
                    'PROCESSING': OrderStatus.PROCESSING,
                    'SHIPPED': OrderStatus.SHIPPED,
                    'DELIVERED': OrderStatus.DELIVERED,
                    'EXCEPTION': OrderStatus.FAILED
                }
                
                status = status_mapping.get(tracking_data.get('status', 'PENDING'), OrderStatus.PENDING)
                
                # Constrói eventos de rastreamento
                events = []
                if tracking_data.get('trackingDetails'):
                    for detail in tracking_data['trackingDetails']:
                        events.append({
                            'date': detail.get('time'),
                            'description': detail.get('description'),
                            'location': detail.get('location', '')
                        })
                
                return TrackingInfo(
                    tracking_number=tracking_data.get('trackingNumber', tracking_number),
                    status=status,
                    events=events,
                    estimated_delivery=tracking_data.get('estimatedDelivery'),
                    last_updated=datetime.now().isoformat()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao obter rastreamento {tracking_number}: {e}")
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
            path = "/logistic/freightCalculate"
            url = f"{self.api_base_url}{path}"
            
            # Constrói lista de produtos para cálculo
            products = []
            for item in items:
                products.append({
                    'pid': item.supplier_product_id,
                    'vid': item.variation_id or '',
                    'quantity': item.quantity
                })
            
            shipping_data = {
                'country': address.country,
                'products': products
            }
            
            headers = self._build_headers('POST', path)
            response = self._make_request('POST', url, json=shipping_data, headers=headers)
            result = response.json()
            
            shipping_options = []
            if result.get('result') and result.get('data'):
                for method in result['data']:
                    shipping_options.append({
                        'service_name': method.get('shippingName'),
                        'cost': method.get('freight'),
                        'currency': 'USD',
                        'delivery_time': method.get('deliveryTime'),
                        'description': method.get('description', '')
                    })
            
            return {
                'options': shipping_options,
                'currency': 'USD',
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"CJ Dropshipping: Erro ao calcular frete: {e}")
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
                logger.error(f"CJ Dropshipping: Erro ao sincronizar estoque do produto {product_id}: {e}")
                inventory[product_id] = 0
        
        return inventory

    def _parse_product_data(self, product_data: Dict[str, Any]) -> Product:
        """
        Converte dados do produto da API do CJ Dropshipping para nosso formato padrão.
        
        Args:
            product_data: Dados do produto da API
            
        Returns:
            Product: Objeto produto padronizado
        """
        # Extrai imagens
        images = []
        if product_data.get('image'):
            images.append(product_data['image'])
        if product_data.get('images'):
            images.extend(product_data['images'])
        
        # Extrai variações
        variations = []
        if product_data.get('variants'):
            for variant in product_data['variants']:
                variations.append({
                    'variant_id': variant.get('vid'),
                    'sku': variant.get('variantSku'),
                    'price': variant.get('variantSellPrice'),
                    'stock': variant.get('variantQuantity'),
                    'attributes': variant.get('variantKey')
                })
        
        # Informações de envio
        shipping_info = {
            'warehouse': product_data.get('sourceFrom'),
            'weight': product_data.get('packWeight'),
            'dimensions': {
                'length': product_data.get('packLength'),
                'width': product_data.get('packWidth'),
                'height': product_data.get('packHeight')
            }
        }
        
        return Product(
            id=str(product_data.get('pid', '')),
            name=product_data.get('productName', ''),
            description=product_data.get('description', ''),
            price=float(product_data.get('sellPrice', 0)),
            currency='USD',
            stock_quantity=int(product_data.get('quantity', 0)),
            images=images,
            variations=variations,
            category=product_data.get('categoryName', ''),
            supplier_id='cj_dropshipping',
            supplier_product_id=str(product_data.get('pid', '')),
            shipping_info=shipping_info,
            last_updated=datetime.now().isoformat()
        )

