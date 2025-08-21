"""
Conector de demonstração para Spocket com dados simulados.
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


class DemoSpocketConnector(BaseConnector):
    """
    Conector de demonstração para Spocket com dados simulados.
    Simula todas as funcionalidades do conector real para fins de teste.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.demo_mode = True
        
        # Produtos simulados para demonstração (foco em produtos dos EUA/Europa)
        self.demo_products = [
            {
                'id': 'SP001234567',
                'title': 'Organic Cotton T-Shirt Premium',
                'description': 'Camiseta premium de algodão orgânico, corte moderno, tecido macio e respirável. Produzida de forma sustentável nos EUA.',
                'price': 24.99,
                'inventory_quantity': 120,
                'images': [
                    {'src': 'https://cdn.spocket.co/SP001234567_1.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234567_2.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234567_3.jpg'}
                ],
                'variants': [
                    {
                        'id': 'SPV001',
                        'sku': 'COTTON-TEE-BLK-S',
                        'price': 24.99,
                        'inventory_quantity': 30,
                        'title': 'Black / Small',
                        'option1': 'Black',
                        'option2': 'Small',
                        'option3': None
                    },
                    {
                        'id': 'SPV002',
                        'sku': 'COTTON-TEE-BLK-M',
                        'price': 24.99,
                        'inventory_quantity': 40,
                        'title': 'Black / Medium',
                        'option1': 'Black',
                        'option2': 'Medium',
                        'option3': None
                    },
                    {
                        'id': 'SPV003',
                        'sku': 'COTTON-TEE-WHT-M',
                        'price': 24.99,
                        'inventory_quantity': 50,
                        'title': 'White / Medium',
                        'option1': 'White',
                        'option2': 'Medium',
                        'option3': None
                    }
                ],
                'product_type': 'Clothing',
                'origin_country': 'United States',
                'processing_time': '1-2 business days',
                'shipping_time': '3-7 business days'
            },
            {
                'id': 'SP001234568',
                'title': 'Minimalist Wooden Watch Handcrafted',
                'description': 'Relógio de madeira artesanal com movimento japonês, pulseira ajustável de couro vegano e design minimalista. Feito na Europa.',
                'price': 89.99,
                'inventory_quantity': 85,
                'images': [
                    {'src': 'https://cdn.spocket.co/SP001234568_1.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234568_2.jpg'}
                ],
                'variants': [
                    {
                        'id': 'SPV004',
                        'sku': 'WOOD-WATCH-OAK',
                        'price': 89.99,
                        'inventory_quantity': 45,
                        'title': 'Oak Wood',
                        'option1': 'Oak',
                        'option2': None,
                        'option3': None
                    },
                    {
                        'id': 'SPV005',
                        'sku': 'WOOD-WATCH-WAL',
                        'price': 94.99,
                        'inventory_quantity': 40,
                        'title': 'Walnut Wood',
                        'option1': 'Walnut',
                        'option2': None,
                        'option3': None
                    }
                ],
                'product_type': 'Accessories',
                'origin_country': 'Germany',
                'processing_time': '2-3 business days',
                'shipping_time': '5-10 business days'
            },
            {
                'id': 'SP001234569',
                'title': 'Eco-Friendly Bamboo Phone Case',
                'description': 'Capa de telefone feita de bambu sustentável, proteção completa, design elegante e compatível com carregamento sem fio.',
                'price': 19.99,
                'inventory_quantity': 200,
                'images': [
                    {'src': 'https://cdn.spocket.co/SP001234569_1.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234569_2.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234569_3.jpg'}
                ],
                'variants': [
                    {
                        'id': 'SPV006',
                        'sku': 'BAMBOO-CASE-IP14',
                        'price': 19.99,
                        'inventory_quantity': 80,
                        'title': 'iPhone 14',
                        'option1': 'iPhone 14',
                        'option2': None,
                        'option3': None
                    },
                    {
                        'id': 'SPV007',
                        'sku': 'BAMBOO-CASE-IP14P',
                        'price': 21.99,
                        'inventory_quantity': 70,
                        'title': 'iPhone 14 Pro',
                        'option1': 'iPhone 14 Pro',
                        'option2': None,
                        'option3': None
                    },
                    {
                        'id': 'SPV008',
                        'sku': 'BAMBOO-CASE-SAM',
                        'price': 19.99,
                        'inventory_quantity': 50,
                        'title': 'Samsung Galaxy S23',
                        'option1': 'Samsung Galaxy S23',
                        'option2': None,
                        'option3': None
                    }
                ],
                'product_type': 'Phone Accessories',
                'origin_country': 'Canada',
                'processing_time': '1-2 business days',
                'shipping_time': '4-8 business days'
            },
            {
                'id': 'SP001234570',
                'title': 'Artisan Coffee Blend Premium Roast',
                'description': 'Blend de café artesanal premium, grãos selecionados, torra média, notas de chocolate e caramelo. Torrado nos EUA.',
                'price': 16.99,
                'inventory_quantity': 150,
                'images': [
                    {'src': 'https://cdn.spocket.co/SP001234570_1.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234570_2.jpg'}
                ],
                'variants': [
                    {
                        'id': 'SPV009',
                        'sku': 'COFFEE-BLEND-250G',
                        'price': 16.99,
                        'inventory_quantity': 80,
                        'title': '250g Bag',
                        'option1': '250g',
                        'option2': None,
                        'option3': None
                    },
                    {
                        'id': 'SPV010',
                        'sku': 'COFFEE-BLEND-500G',
                        'price': 29.99,
                        'inventory_quantity': 70,
                        'title': '500g Bag',
                        'option1': '500g',
                        'option2': None,
                        'option3': None
                    }
                ],
                'product_type': 'Food & Beverage',
                'origin_country': 'United States',
                'processing_time': '1-2 business days',
                'shipping_time': '2-5 business days'
            },
            {
                'id': 'SP001234571',
                'title': 'Handmade Ceramic Mug Set',
                'description': 'Conjunto de canecas de cerâmica artesanal, design único, perfeito para café ou chá. Feito por artesãos europeus.',
                'price': 34.99,
                'inventory_quantity': 95,
                'images': [
                    {'src': 'https://cdn.spocket.co/SP001234571_1.jpg'},
                    {'src': 'https://cdn.spocket.co/SP001234571_2.jpg'}
                ],
                'variants': [
                    {
                        'id': 'SPV011',
                        'sku': 'CERAMIC-MUG-SET2',
                        'price': 34.99,
                        'inventory_quantity': 50,
                        'title': 'Set of 2',
                        'option1': '2 Mugs',
                        'option2': None,
                        'option3': None
                    },
                    {
                        'id': 'SPV012',
                        'sku': 'CERAMIC-MUG-SET4',
                        'price': 59.99,
                        'inventory_quantity': 45,
                        'title': 'Set of 4',
                        'option1': '4 Mugs',
                        'option2': None,
                        'option3': None
                    }
                ],
                'product_type': 'Home & Kitchen',
                'origin_country': 'Portugal',
                'processing_time': '2-3 business days',
                'shipping_time': '7-12 business days'
            }
        ]

    def authenticate(self) -> bool:
        """
        Simula autenticação bem-sucedida.
        
        Returns:
            bool: Sempre True para demonstração
        """
        logger.info("Demo Spocket: Autenticação simulada bem-sucedida")
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
                    return self._parse_demo_product(demo_product)
            
            logger.warning(f"Demo Spocket: Produto {product_id} não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Demo Spocket: Erro ao obter produto {product_id}: {e}")
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
                # Busca por nome, descrição ou categoria
                if (query_lower in demo_product['title'].lower() or 
                    query_lower in demo_product['description'].lower() or
                    query_lower in demo_product['product_type'].lower()):
                    
                    product = self._parse_demo_product(demo_product)
                    results.append(product)
            
            logger.info(f"Demo Spocket: Encontrados {len(results)} produtos para '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Demo Spocket: Erro na busca de produtos: {e}")
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
            import random
            
            # Simula sucesso em 98% dos casos (Spocket tem alta qualidade)
            if random.random() < 0.98:
                supplier_order_id = f"SP{int(time.time())}{random.randint(100, 999)}"
                tracking_number = f"SP{random.randint(100000, 999999)}"
                
                return OrderResponse(
                    success=True,
                    order_id=order.id,
                    supplier_order_id=supplier_order_id,
                    tracking_number=tracking_number,
                    estimated_delivery=(datetime.now() + timedelta(days=6)).isoformat(),
                    message="Pedido criado com sucesso (simulado)"
                )
            else:
                # Simula erro ocasional
                error_messages = [
                    "Produto temporariamente indisponível",
                    "Endereço de entrega inválido",
                    "Erro na validação do pagamento"
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
            logger.error(f"Demo Spocket: Erro ao criar pedido: {e}")
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
            # Simula eventos de rastreamento (entrega mais rápida - EUA/Europa)
            events = [
                {
                    'date': (datetime.now() - timedelta(days=4)).isoformat(),
                    'description': 'Pedido confirmado e processado',
                    'location': 'Los Angeles, CA, USA'
                },
                {
                    'date': (datetime.now() - timedelta(days=3)).isoformat(),
                    'description': 'Produto embalado e etiquetado',
                    'location': 'Los Angeles, CA, USA'
                },
                {
                    'date': (datetime.now() - timedelta(days=2)).isoformat(),
                    'description': 'Produto despachado via USPS',
                    'location': 'Los Angeles, CA, USA'
                },
                {
                    'date': (datetime.now() - timedelta(days=1)).isoformat(),
                    'description': 'Em trânsito para o destino',
                    'location': 'Miami, FL, USA'
                },
                {
                    'date': datetime.now().isoformat(),
                    'description': 'Chegou ao centro de distribuição internacional',
                    'location': 'São Paulo, Brasil'
                }
            ]
            
            return TrackingInfo(
                tracking_number=tracking_number,
                status=OrderStatus.SHIPPED,
                events=events,
                estimated_delivery=(datetime.now() + timedelta(days=2)).isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Demo Spocket: Erro ao obter rastreamento: {e}")
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
            # Simula diferentes opções de frete (mais caras mas mais rápidas)
            shipping_options = [
                {
                    'service_name': 'Standard Shipping',
                    'cost': 8.99,
                    'currency': 'USD',
                    'delivery_time': '5-10 business days',
                    'description': 'Entrega padrão internacional'
                },
                {
                    'service_name': 'Express Shipping',
                    'cost': 19.99,
                    'currency': 'USD',
                    'delivery_time': '3-7 business days',
                    'description': 'Entrega expressa com rastreamento'
                },
                {
                    'service_name': 'Priority Express',
                    'cost': 39.99,
                    'currency': 'USD',
                    'delivery_time': '2-5 business days',
                    'description': 'Entrega prioritária com seguro'
                }
            ]
            
            return {
                'options': shipping_options,
                'currency': 'USD',
                'calculated_at': datetime.now().isoformat(),
                'destination': f"{address.city}, {address.country}"
            }
            
        except Exception as e:
            logger.error(f"Demo Spocket: Erro ao calcular frete: {e}")
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
                    inventory[product_id] = demo_product['inventory_quantity']
                    break
            else:
                # Produto não encontrado
                inventory[product_id] = 0
        
        logger.info(f"Demo Spocket: Sincronizado estoque de {len(product_ids)} produtos")
        return inventory

    def _parse_demo_product(self, demo_product: Dict[str, Any]) -> Product:
        """
        Converte dados do produto demo para nosso formato padrão.
        
        Args:
            demo_product: Dados do produto demo
            
        Returns:
            Product: Objeto produto padronizado
        """
        # Extrai imagens
        images = []
        if demo_product.get('images'):
            for image in demo_product['images']:
                if isinstance(image, dict):
                    images.append(image.get('src', ''))
                else:
                    images.append(str(image))
        
        # Extrai variações
        variations = []
        if demo_product.get('variants'):
            for variant in demo_product['variants']:
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
            'origin_country': demo_product.get('origin_country'),
            'processing_time': demo_product.get('processing_time'),
            'shipping_time': demo_product.get('shipping_time')
        }
        
        return Product(
            id=demo_product['id'],
            name=demo_product['title'],
            description=demo_product['description'],
            price=float(demo_product['price']),
            currency='USD',
            stock_quantity=int(demo_product['inventory_quantity']),
            images=images,
            variations=variations,
            category=demo_product['product_type'],
            supplier_id='spocket_demo',
            supplier_product_id=demo_product['id'],
            shipping_info=shipping_info,
            last_updated=datetime.now().isoformat()
        )

