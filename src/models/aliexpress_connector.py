"""
Conector específico para AliExpress Dropshipping API.
Implementa todas as funcionalidades necessárias para integração com o AliExpress.
"""

import hashlib
import hmac
import time
import json
import urllib.parse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from src.models.connector_base import (
    BaseConnector, ConnectorConfig, Product, Order, OrderResponse, 
    TrackingInfo, Address, OrderItem, OrderStatus
)
import logging

logger = logging.getLogger(__name__)


class AliExpressConnector(BaseConnector):
    """
    Conector para AliExpress Dropshipping API.
    Implementa autenticação, busca de produtos, criação de pedidos e rastreamento.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.app_key = config.api_key
        self.app_secret = config.api_secret
        self.access_token = config.additional_config.get('access_token')
        self.refresh_token = config.additional_config.get('refresh_token')
        self.token_expires_at = config.additional_config.get('token_expires_at')
        
        # URLs da API do AliExpress
        self.api_base_url = config.base_url or "https://api-sg.aliexpress.com/sync"
        self.auth_base_url = "https://oauth.aliexpress.com"
        
        # Configurações específicas do AliExpress
        self.default_country = config.additional_config.get('default_country', 'US')
        self.default_currency = config.additional_config.get('default_currency', 'USD')
        self.default_language = config.additional_config.get('default_language', 'en')

    def _generate_signature(self, method: str, params: Dict[str, Any]) -> str:
        """
        Gera a assinatura necessária para autenticar requisições na API do AliExpress.
        
        Args:
            method: Nome do método da API
            params: Parâmetros da requisição
            
        Returns:
            str: Assinatura HMAC-SHA256
        """
        # Ordena os parâmetros alfabeticamente
        sorted_params = sorted(params.items())
        
        # Constrói a string de consulta
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # Constrói a string para assinar
        string_to_sign = f"{method}&{urllib.parse.quote(query_string, safe='')}"
        
        # Gera a assinatura HMAC-SHA256
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        return signature

    def _build_request_params(self, method: str, api_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Constrói os parâmetros base para requisições da API.
        
        Args:
            method: Nome do método da API
            api_params: Parâmetros específicos da API
            
        Returns:
            Dict: Parâmetros completos da requisição
        """
        if api_params is None:
            api_params = {}

        # Parâmetros base obrigatórios
        params = {
            'method': method,
            'app_key': self.app_key,
            'timestamp': str(int(time.time() * 1000)),
            'format': 'json',
            'v': '2.0',
            'sign_method': 'hmac'
        }

        # Adiciona access_token se disponível
        if self.access_token:
            params['session'] = self.access_token

        # Adiciona parâmetros específicos da API
        for key, value in api_params.items():
            if isinstance(value, (dict, list)):
                params[key] = json.dumps(value)
            else:
                params[key] = str(value)

        # Gera e adiciona a assinatura
        params['sign'] = self._generate_signature(method, params)
        
        return params

    def authenticate(self) -> bool:
        """
        Autentica com a API do AliExpress.
        Para o AliExpress, isso verifica se temos um token válido.
        
        Returns:
            bool: True se autenticado com sucesso
        """
        try:
            # Verifica se temos um token válido
            if not self.access_token:
                logger.warning("Access token não configurado para AliExpress")
                return False

            # Verifica se o token não expirou
            if self.token_expires_at:
                expires_at = datetime.fromisoformat(self.token_expires_at)
                if datetime.now() >= expires_at:
                    logger.info("Token expirado, tentando renovar...")
                    return self._refresh_access_token()

            # Testa o token fazendo uma chamada simples
            return self._test_token()
            
        except Exception as e:
            logger.error(f"Erro na autenticação AliExpress: {e}")
            return False

    def _test_token(self) -> bool:
        """
        Testa se o token atual é válido fazendo uma chamada de teste.
        
        Returns:
            bool: True se o token é válido
        """
        try:
            params = self._build_request_params('aliexpress.ds.category.get')
            response = self._make_request('POST', self.api_base_url, data=params)
            
            result = response.json()
            return 'error_response' not in result
            
        except Exception as e:
            logger.error(f"Erro ao testar token: {e}")
            return False

    def _refresh_access_token(self) -> bool:
        """
        Renova o access token usando o refresh token.
        
        Returns:
            bool: True se renovado com sucesso
        """
        try:
            if not self.refresh_token:
                logger.error("Refresh token não disponível")
                return False

            params = self._build_request_params(
                'auth/token/refresh',
                {'refresh_token': self.refresh_token}
            )
            
            response = self._make_request('POST', self.api_base_url, data=params)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.refresh_token = result.get('refresh_token', self.refresh_token)
                
                # Calcula nova data de expiração
                expires_in = result.get('expires_in', 3600)
                self.token_expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                
                logger.info("Token renovado com sucesso")
                return True
            else:
                logger.error(f"Erro ao renovar token: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False

    def get_product_details(self, product_id: str, **kwargs) -> Optional[Product]:
        """
        Obtém detalhes de um produto específico do AliExpress.
        
        Args:
            product_id: ID do produto no AliExpress
            **kwargs: Parâmetros adicionais (country, currency, language)
            
        Returns:
            Product: Objeto produto ou None se não encontrado
        """
        try:
            api_params = {
                'product_id': product_id,
                'ship_to_country': kwargs.get('country', self.default_country),
                'target_currency': kwargs.get('currency', self.default_currency),
                'target_language': kwargs.get('language', self.default_language)
            }
            
            params = self._build_request_params('aliexpress.ds.product.get', api_params)
            response = self._make_request('POST', self.api_base_url, data=params)
            result = response.json()
            
            if 'aliexpress_ds_product_get_response' in result:
                product_data = result['aliexpress_ds_product_get_response']['result']
                return self._parse_product_data(product_data)
            else:
                logger.error(f"Erro ao obter produto {product_id}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do produto {product_id}: {e}")
            return None

    def search_products(self, query: str, **kwargs) -> List[Product]:
        """
        Busca produtos no catálogo do AliExpress.
        
        Args:
            query: Termo de busca
            **kwargs: Parâmetros adicionais (category, min_price, max_price, etc.)
            
        Returns:
            List[Product]: Lista de produtos encontrados
        """
        try:
            # Para o AliExpress, usamos a API de feed para buscar produtos
            # Primeiro obtemos o feedname para a categoria
            feedname = self._get_feedname_for_category(kwargs.get('category'))
            
            if not feedname:
                logger.warning(f"Feedname não encontrado para categoria: {kwargs.get('category')}")
                return []

            # Obtém IDs de produtos do feed
            product_ids = self._get_product_ids_from_feed(feedname, query, **kwargs)
            
            # Obtém detalhes de cada produto
            products = []
            for product_id in product_ids[:20]:  # Limita a 20 produtos por busca
                product = self.get_product_details(product_id, **kwargs)
                if product:
                    products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            return []

    def _get_feedname_for_category(self, category: str = None) -> Optional[str]:
        """
        Obtém o feedname para uma categoria específica.
        
        Args:
            category: Nome da categoria
            
        Returns:
            str: Feedname ou None se não encontrado
        """
        try:
            params = self._build_request_params('aliexpress.ds.feedname.get')
            response = self._make_request('POST', self.api_base_url, data=params)
            result = response.json()
            
            if 'aliexpress_ds_feedname_get_response' in result:
                feednames = result['aliexpress_ds_feedname_get_response']['result']
                
                # Se categoria específica foi fornecida, procura por ela
                if category:
                    for feed in feednames:
                        if category.lower() in feed.get('feed_name', '').lower():
                            return feed.get('feed_name')
                
                # Retorna o primeiro feedname disponível
                if feednames:
                    return feednames[0].get('feed_name')
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter feedname: {e}")
            return None

    def _get_product_ids_from_feed(self, feedname: str, query: str, **kwargs) -> List[str]:
        """
        Obtém IDs de produtos de um feed específico.
        
        Args:
            feedname: Nome do feed
            query: Termo de busca
            **kwargs: Parâmetros adicionais
            
        Returns:
            List[str]: Lista de IDs de produtos
        """
        try:
            api_params = {
                'feed_name': feedname,
                'page_no': kwargs.get('page', 1),
                'page_size': kwargs.get('page_size', 20)
            }
            
            params = self._build_request_params('aliexpress.ds.feed.itemids.get', api_params)
            response = self._make_request('POST', self.api_base_url, data=params)
            result = response.json()
            
            if 'aliexpress_ds_feed_itemids_get_response' in result:
                items = result['aliexpress_ds_feed_itemids_get_response']['result']
                return [str(item.get('item_id')) for item in items if item.get('item_id')]
            
            return []
            
        except Exception as e:
            logger.error(f"Erro ao obter IDs de produtos do feed: {e}")
            return []

    def create_order(self, order: Order) -> OrderResponse:
        """
        Cria um pedido no AliExpress.
        
        Args:
            order: Objeto Order com detalhes do pedido
            
        Returns:
            OrderResponse: Resposta da criação do pedido
        """
        try:
            # Constrói o endereço de entrega
            logistics_address = {
                'address': order.shipping_address.address_line1,
                'city': order.shipping_address.city,
                'country': order.shipping_address.country,
                'full_name': order.shipping_address.full_name,
                'mobile_no': order.shipping_address.phone,
                'phone_country': '+1',  # Assumindo US por padrão
                'province': order.shipping_address.state,
                'zip': order.shipping_address.postal_code
            }
            
            # Constrói os itens do pedido
            product_items = []
            for item in order.items:
                product_item = {
                    'logistics_service_name': order.shipping_method or 'AliExpress Standard Shipping',
                    'order_memo': order.notes or f'Order {order.id}',
                    'product_count': item.quantity,
                    'product_id': item.supplier_product_id,
                    'sku_attr': item.variation_attributes.get('sku_attr', '') if item.variation_attributes else ''
                }
                product_items.append(product_item)
            
            # Parâmetros da API
            api_params = {
                'param_place_order_request4_open_api_d_t_o': {
                    'logistics_address': logistics_address,
                    'product_items': product_items
                }
            }
            
            params = self._build_request_params('aliexpress.ds.order.create', api_params)
            response = self._make_request('POST', self.api_base_url, data=params)
            result = response.json()
            
            if 'aliexpress_ds_order_create_response' in result:
                order_result = result['aliexpress_ds_order_create_response']['result']
                
                if order_result.get('is_success'):
                    return OrderResponse(
                        success=True,
                        order_id=order.id,
                        supplier_order_id=str(order_result.get('order_list', [{}])[0].get('order_id', '')),
                        tracking_number=None,  # Será obtido posteriormente
                        estimated_delivery=None,
                        message="Pedido criado com sucesso"
                    )
                else:
                    error_msg = order_result.get('error_msg', 'Erro desconhecido')
                    return OrderResponse(
                        success=False,
                        order_id=None,
                        supplier_order_id=None,
                        tracking_number=None,
                        estimated_delivery=None,
                        message=f"Erro ao criar pedido: {error_msg}",
                        error_code=order_result.get('error_code')
                    )
            else:
                error_msg = result.get('error_response', {}).get('msg', 'Erro na API')
                return OrderResponse(
                    success=False,
                    order_id=None,
                    supplier_order_id=None,
                    tracking_number=None,
                    estimated_delivery=None,
                    message=f"Erro na API: {error_msg}",
                    error_code=result.get('error_response', {}).get('code')
                )
                
        except Exception as e:
            logger.error(f"Erro ao criar pedido: {e}")
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
            order_id: ID do pedido no AliExpress
            
        Returns:
            OrderStatus: Status atual do pedido
        """
        try:
            tracking_info = self.get_tracking_info(order_id)
            if tracking_info:
                return tracking_info.status
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter status do pedido {order_id}: {e}")
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
            api_params = {
                'order_id': tracking_number
            }
            
            params = self._build_request_params('aliexpress.ds.order.tracking.get', api_params)
            response = self._make_request('POST', self.api_base_url, data=params)
            result = response.json()
            
            if 'aliexpress_ds_order_tracking_get_response' in result:
                tracking_data = result['aliexpress_ds_order_tracking_get_response']['result']
                
                # Mapeia status do AliExpress para nosso enum
                status_mapping = {
                    'WAIT_SELLER_SEND_GOODS': OrderStatus.CONFIRMED,
                    'SELLER_SEND_GOODS': OrderStatus.PROCESSING,
                    'WAIT_BUYER_ACCEPT_GOODS': OrderStatus.SHIPPED,
                    'FINISH': OrderStatus.DELIVERED,
                    'CANCEL': OrderStatus.CANCELLED
                }
                
                ae_status = tracking_data.get('order_status', '')
                status = status_mapping.get(ae_status, OrderStatus.PENDING)
                
                # Constrói eventos de rastreamento
                events = []
                if tracking_data.get('logistics_info_list'):
                    for info in tracking_data['logistics_info_list']:
                        events.append({
                            'date': info.get('status_date'),
                            'description': info.get('status_desc'),
                            'location': info.get('location', '')
                        })
                
                return TrackingInfo(
                    tracking_number=tracking_data.get('logistics_no', tracking_number),
                    status=status,
                    events=events,
                    estimated_delivery=tracking_data.get('estimated_delivery_time'),
                    last_updated=datetime.now().isoformat()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter rastreamento {tracking_number}: {e}")
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
            shipping_options = []
            
            for item in items:
                api_params = {
                    'country_code': address.country,
                    'product_id': item.supplier_product_id,
                    'product_num': item.quantity,
                    'province_code': address.state,
                    'city_code': address.city,
                    'send_goods_country_code': 'CN',  # Assumindo origem China
                    'price': str(item.price)
                }
                
                params = self._build_request_params('aliexpress.ds.freight.query', api_params)
                response = self._make_request('POST', self.api_base_url, data=params)
                result = response.json()
                
                if 'aliexpress_ds_freight_query_response' in result:
                    freight_data = result['aliexpress_ds_freight_query_response']['result']
                    
                    for freight in freight_data.get('freight_list', []):
                        shipping_options.append({
                            'service_name': freight.get('service_name'),
                            'cost': freight.get('freight_amount'),
                            'currency': freight.get('currency'),
                            'delivery_time': freight.get('delivery_time'),
                            'product_id': item.supplier_product_id
                        })
            
            return {
                'options': shipping_options,
                'currency': self.default_currency,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular frete: {e}")
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
                logger.error(f"Erro ao sincronizar estoque do produto {product_id}: {e}")
                inventory[product_id] = 0
        
        return inventory

    def _parse_product_data(self, product_data: Dict[str, Any]) -> Product:
        """
        Converte dados do produto da API do AliExpress para nosso formato padrão.
        
        Args:
            product_data: Dados do produto da API
            
        Returns:
            Product: Objeto produto padronizado
        """
        # Extrai imagens
        images = []
        if product_data.get('ae_item_base_info_dto', {}).get('image_urls'):
            images = product_data['ae_item_base_info_dto']['image_urls'].split(';')
        
        # Extrai variações
        variations = []
        if product_data.get('ae_item_sku_info_dtos'):
            for sku in product_data['ae_item_sku_info_dtos']:
                variations.append({
                    'sku_id': sku.get('id'),
                    'sku_attr': sku.get('sku_attr'),
                    'price': sku.get('sku_price'),
                    'stock': sku.get('sku_stock'),
                    'attributes': sku.get('sku_attr_name')
                })
        
        # Informações de envio
        shipping_info = {}
        if product_data.get('logistics_info_dto'):
            shipping_info = {
                'delivery_time': product_data['logistics_info_dto'].get('delivery_time'),
                'shipping_fee': product_data['logistics_info_dto'].get('shipping_fee')
            }
        
        base_info = product_data.get('ae_item_base_info_dto', {})
        
        return Product(
            id=str(base_info.get('product_id', '')),
            name=base_info.get('subject', ''),
            description=base_info.get('detail', ''),
            price=float(base_info.get('product_min_price', 0)),
            currency=self.default_currency,
            stock_quantity=int(base_info.get('product_stock', 0)),
            images=images,
            variations=variations,
            category=base_info.get('category_id', ''),
            supplier_id='aliexpress',
            supplier_product_id=str(base_info.get('product_id', '')),
            shipping_info=shipping_info,
            last_updated=datetime.now().isoformat()
        )

