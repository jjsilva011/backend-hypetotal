"""
Conector de demonstração para AliExpress com dados simulados.
Usado para testes e demonstrações quando não há credenciais reais disponíveis.
"""

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


class DemoAliExpressConnector(BaseConnector):
    """
    Conector de demonstração para AliExpress com dados simulados.
    Simula todas as funcionalidades do conector real para fins de teste.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.demo_mode = True
        
        # Produtos simulados para demonstração
        self.demo_products = [
            {
                'id': '1005004043442825',
                'name': 'Smartphone Galaxy X1 Pro 128GB',
                'description': 'Smartphone premium com tela AMOLED 6.7", câmera tripla 108MP, processador octa-core e bateria 5000mAh. Ideal para uso profissional e entretenimento.',
                'price': 299.99,
                'currency': 'USD',
                'stock_quantity': 150,
                'images': [
                    'https://ae01.alicdn.com/kf/S123456789.jpg',
                    'https://ae01.alicdn.com/kf/S987654321.jpg'
                ],
                'variations': [
                    {
                        'sku_id': 'SKU001',
                        'sku_attr': '14:350853#Black;5:361386#128GB',
                        'price': 299.99,
                        'stock': 50,
                        'attributes': 'Color: Black, Storage: 128GB'
                    },
                    {
                        'sku_id': 'SKU002',
                        'sku_attr': '14:350854#Blue;5:361386#128GB',
                        'price': 299.99,
                        'stock': 45,
                        'attributes': 'Color: Blue, Storage: 128GB'
                    },
                    {
                        'sku_id': 'SKU003',
                        'sku_attr': '14:350853#Black;5:361387#256GB',
                        'price': 399.99,
                        'stock': 30,
                        'attributes': 'Color: Black, Storage: 256GB'
                    }
                ],
                'category': 'Electronics',
                'shipping_info': {
                    'delivery_time': '7-15 days',
                    'shipping_fee': 'Free'
                }
            },
            {
                'id': '1005004043442826',
                'name': 'Wireless Bluetooth Headphones Pro',
                'description': 'Fones de ouvido sem fio com cancelamento de ruído ativo, bateria de 30h, som Hi-Fi e microfone integrado. Perfeito para trabalho e lazer.',
                'price': 89.99,
                'currency': 'USD',
                'stock_quantity': 200,
                'images': [
                    'https://ae01.alicdn.com/kf/H123456789.jpg',
                    'https://ae01.alicdn.com/kf/H987654321.jpg'
                ],
                'variations': [
                    {
                        'sku_id': 'SKU004',
                        'sku_attr': '14:350853#Black',
                        'price': 89.99,
                        'stock': 80,
                        'attributes': 'Color: Black'
                    },
                    {
                        'sku_id': 'SKU005',
                        'sku_attr': '14:350854#White',
                        'price': 89.99,
                        'stock': 70,
                        'attributes': 'Color: White'
                    },
                    {
                        'sku_id': 'SKU006',
                        'sku_attr': '14:350855#Red',
                        'price': 94.99,
                        'stock': 50,
                        'attributes': 'Color: Red'
                    }
                ],
                'category': 'Electronics',
                'shipping_info': {
                    'delivery_time': '5-12 days',
                    'shipping_fee': 'Free'
                }
            },
            {
                'id': '1005004043442827',
                'name': 'Smart Watch Fitness Tracker',
                'description': 'Relógio inteligente com monitor cardíaco, GPS, resistente à água IP68, tela touch colorida e bateria de 7 dias.',
                'price': 59.99,
                'currency': 'USD',
                'stock_quantity': 300,
                'images': [
                    'https://ae01.alicdn.com/kf/W123456789.jpg',
                    'https://ae01.alicdn.com/kf/W987654321.jpg'
                ],
                'variations': [
                    {
                        'sku_id': 'SKU007',
                        'sku_attr': '14:350853#Black;200007763:201336100#42mm',
                        'price': 59.99,
                        'stock': 100,
                        'attributes': 'Color: Black, Size: 42mm'
                    },
                    {
                        'sku_id': 'SKU008',
                        'sku_attr': '14:350854#Silver;200007763:201336101#46mm',
                        'price': 64.99,
                        'stock': 80,
                        'attributes': 'Color: Silver, Size: 46mm'
                    }
                ],
                'category': 'Electronics',
                'shipping_info': {
                    'delivery_time': '6-14 days',
                    'shipping_fee': 'Free'
                }
            },
            {
                'id': '1005004043442828',
                'name': 'USB-C Fast Charging Cable 3m',
                'description': 'Cabo USB-C de alta qualidade com carregamento rápido 100W, transferência de dados 480Mbps, resistente e durável.',
                'price': 12.99,
                'currency': 'USD',
                'stock_quantity': 500,
                'images': [
                    'https://ae01.alicdn.com/kf/C123456789.jpg'
                ],
                'variations': [
                    {
                        'sku_id': 'SKU009',
                        'sku_attr': '14:350853#Black;200000124:200003482#3m',
                        'price': 12.99,
                        'stock': 200,
                        'attributes': 'Color: Black, Length: 3m'
                    },
                    {
                        'sku_id': 'SKU010',
                        'sku_attr': '14:350854#White;200000124:200003481#2m',
                        'price': 9.99,
                        'stock': 300,
                        'attributes': 'Color: White, Length: 2m'
                    }
                ],
                'category': 'Electronics',
                'shipping_info': {
                    'delivery_time': '4-10 days',
                    'shipping_fee': 'Free'
                }
            },
            {
                'id': '1005004043442829',
                'name': 'Portable Power Bank 20000mAh',
                'description': 'Power bank portátil com capacidade 20000mAh, carregamento rápido PD 22.5W, display LED e múltiplas portas USB.',
                'price': 34.99,
                'currency': 'USD',
                'stock_quantity': 180,
                'images': [
                    'https://ae01.alicdn.com/kf/P123456789.jpg',
                    'https://ae01.alicdn.com/kf/P987654321.jpg'
                ],
                'variations': [
                    {
                        'sku_id': 'SKU011',
                        'sku_attr': '14:350853#Black;200000124:200003483#20000mAh',
                        'price': 34.99,
                        'stock': 90,
                        'attributes': 'Color: Black, Capacity: 20000mAh'
                    },
                    {
                        'sku_id': 'SKU012',
                        'sku_attr': '14:350854#Blue;200000124:200003482#10000mAh',
                        'price': 24.99,
                        'stock': 90,
                        'attributes': 'Color: Blue, Capacity: 10000mAh'
                    }
                ],
                'category': 'Electronics',
                'shipping_info': {
                    'delivery_time': '5-13 days',
                    'shipping_fee': 'Free'
                }
            }
        ]

    def authenticate(self) -> bool:
        """
        Simula autenticação bem-sucedida.
        
        Returns:
            bool: Sempre True para demonstração
        """
        logger.info("Demo AliExpress: Autenticação simulada bem-sucedida")
        return True

    def get_product_details(self, product_id: str, **kwargs) -> Optional[Product]:
        """
        Obtém detalhes de um produto simulado.
        
        Args:
            product_id: ID do produto
            **kwargs: Parâmetros adicionais
            
        Returns:
            Product: Produto simulado ou None se não encontrado
        """
        try:
            # Busca produto nos dados simulados
            for demo_product in self.demo_products:
                if demo_product['id'] == product_id:
                    return Product(
                        id=demo_product['id'],
                        name=demo_product['name'],
                        description=demo_product['description'],
                        price=demo_product['price'],
                        currency=demo_product['currency'],
                        stock_quantity=demo_product['stock_quantity'],
                        images=demo_product['images'],
                        variations=demo_product['variations'],
                        category=demo_product['category'],
                        supplier_id='aliexpress_demo',
                        supplier_product_id=demo_product['id'],
                        shipping_info=demo_product['shipping_info'],
                        last_updated=datetime.now().isoformat()
                    )
            
            logger.warning(f"Demo AliExpress: Produto {product_id} não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Demo AliExpress: Erro ao obter produto {product_id}: {e}")
            return None

    def search_products(self, query: str, **kwargs) -> List[Product]:
        """
        Busca produtos simulados baseado na query.
        
        Args:
            query: Termo de busca
            **kwargs: Parâmetros adicionais
            
        Returns:
            List[Product]: Lista de produtos simulados
        """
        try:
            results = []
            query_lower = query.lower()
            
            for demo_product in self.demo_products:
                # Busca por nome ou descrição
                if (query_lower in demo_product['name'].lower() or 
                    query_lower in demo_product['description'].lower() or
                    query_lower in demo_product['category'].lower()):
                    
                    product = Product(
                        id=demo_product['id'],
                        name=demo_product['name'],
                        description=demo_product['description'],
                        price=demo_product['price'],
                        currency=demo_product['currency'],
                        stock_quantity=demo_product['stock_quantity'],
                        images=demo_product['images'],
                        variations=demo_product['variations'],
                        category=demo_product['category'],
                        supplier_id='aliexpress_demo',
                        supplier_product_id=demo_product['id'],
                        shipping_info=demo_product['shipping_info'],
                        last_updated=datetime.now().isoformat()
                    )
                    results.append(product)
            
            logger.info(f"Demo AliExpress: Encontrados {len(results)} produtos para '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Demo AliExpress: Erro na busca de produtos: {e}")
            return []

    def create_order(self, order: Order) -> OrderResponse:
        """
        Simula criação de pedido.
        
        Args:
            order: Dados do pedido
            
        Returns:
            OrderResponse: Resposta simulada
        """
        try:
            # Simula processamento do pedido
            import random
            
            # Simula sucesso em 90% dos casos
            if random.random() < 0.9:
                supplier_order_id = f"AE{int(time.time())}{random.randint(1000, 9999)}"
                
                return OrderResponse(
                    success=True,
                    order_id=order.id,
                    supplier_order_id=supplier_order_id,
                    tracking_number=None,  # Será gerado posteriormente
                    estimated_delivery=(datetime.now() + timedelta(days=10)).isoformat(),
                    message="Pedido criado com sucesso (simulado)"
                )
            else:
                # Simula erro ocasional
                error_messages = [
                    "Produto fora de estoque",
                    "Endereço de entrega inválido",
                    "Método de pagamento rejeitado",
                    "Produto não disponível para este país"
                ]
                
                return OrderResponse(
                    success=False,
                    order_id=None,
                    supplier_order_id=None,
                    tracking_number=None,
                    estimated_delivery=None,
                    message=f"Erro simulado: {random.choice(error_messages)}",
                    error_code="DEMO_ERROR"
                )
                
        except Exception as e:
            logger.error(f"Demo AliExpress: Erro ao criar pedido: {e}")
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
        Simula obtenção de status do pedido.
        
        Args:
            order_id: ID do pedido
            
        Returns:
            OrderStatus: Status simulado
        """
        import random
        
        # Simula diferentes status baseado no ID
        statuses = [
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED
        ]
        
        # Usa hash do order_id para consistência
        status_index = hash(order_id) % len(statuses)
        return statuses[status_index]

    def get_tracking_info(self, tracking_number: str) -> Optional[TrackingInfo]:
        """
        Simula informações de rastreamento.
        
        Args:
            tracking_number: Número de rastreamento
            
        Returns:
            TrackingInfo: Informações simuladas
        """
        try:
            # Simula eventos de rastreamento
            events = [
                {
                    'date': (datetime.now() - timedelta(days=5)).isoformat(),
                    'description': 'Pedido confirmado pelo vendedor',
                    'location': 'Guangzhou, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=4)).isoformat(),
                    'description': 'Produto embalado e pronto para envio',
                    'location': 'Guangzhou, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=3)).isoformat(),
                    'description': 'Produto despachado para o país de destino',
                    'location': 'Guangzhou, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=1)).isoformat(),
                    'description': 'Produto chegou ao país de destino',
                    'location': 'São Paulo, Brasil'
                },
                {
                    'date': datetime.now().isoformat(),
                    'description': 'Produto em trânsito para entrega',
                    'location': 'São Paulo, Brasil'
                }
            ]
            
            return TrackingInfo(
                tracking_number=tracking_number,
                status=OrderStatus.SHIPPED,
                events=events,
                estimated_delivery=(datetime.now() + timedelta(days=3)).isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Demo AliExpress: Erro ao obter rastreamento: {e}")
            return None

    def calculate_shipping(self, items: List[OrderItem], address: Address) -> Dict[str, Any]:
        """
        Simula cálculo de frete.
        
        Args:
            items: Lista de itens
            address: Endereço de entrega
            
        Returns:
            Dict: Opções de frete simuladas
        """
        try:
            # Simula diferentes opções de frete
            shipping_options = [
                {
                    'service_name': 'AliExpress Standard Shipping',
                    'cost': 0.00,
                    'currency': 'USD',
                    'delivery_time': '7-15 days',
                    'description': 'Frete grátis padrão'
                },
                {
                    'service_name': 'AliExpress Premium Shipping',
                    'cost': 9.99,
                    'currency': 'USD',
                    'delivery_time': '5-10 days',
                    'description': 'Entrega mais rápida com rastreamento'
                },
                {
                    'service_name': 'DHL Express',
                    'cost': 24.99,
                    'currency': 'USD',
                    'delivery_time': '3-7 days',
                    'description': 'Entrega expressa internacional'
                }
            ]
            
            return {
                'options': shipping_options,
                'currency': 'USD',
                'calculated_at': datetime.now().isoformat(),
                'destination': f"{address.city}, {address.country}"
            }
            
        except Exception as e:
            logger.error(f"Demo AliExpress: Erro ao calcular frete: {e}")
            return {'error': str(e)}

    def sync_inventory(self, product_ids: List[str]) -> Dict[str, int]:
        """
        Simula sincronização de estoque.
        
        Args:
            product_ids: Lista de IDs de produtos
            
        Returns:
            Dict: Estoque simulado por produto
        """
        inventory = {}
        
        for product_id in product_ids:
            # Busca produto nos dados simulados
            for demo_product in self.demo_products:
                if demo_product['id'] == product_id:
                    inventory[product_id] = demo_product['stock_quantity']
                    break
            else:
                # Produto não encontrado
                inventory[product_id] = 0
        
        logger.info(f"Demo AliExpress: Sincronizado estoque de {len(product_ids)} produtos")
        return inventory

