"""
Conector de demonstração para CJ Dropshipping com dados simulados.
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


class DemoCJDropshippingConnector(BaseConnector):
    """
    Conector de demonstração para CJ Dropshipping com dados simulados.
    Simula todas as funcionalidades do conector real para fins de teste.
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.demo_mode = True
        
        # Produtos simulados para demonstração
        self.demo_products = [
            {
                'pid': 'CJ001234567',
                'productName': 'Gaming Mechanical Keyboard RGB',
                'description': 'Teclado mecânico gamer com switches azuis, iluminação RGB personalizável, teclas anti-ghosting e design ergonômico. Ideal para jogos e trabalho.',
                'sellPrice': 79.99,
                'quantity': 250,
                'image': 'https://img.cjdropshipping.com/CJ001234567_1.jpg',
                'images': [
                    'https://img.cjdropshipping.com/CJ001234567_1.jpg',
                    'https://img.cjdropshipping.com/CJ001234567_2.jpg',
                    'https://img.cjdropshipping.com/CJ001234567_3.jpg'
                ],
                'variants': [
                    {
                        'vid': 'V001',
                        'variantSku': 'KB-RGB-BLU',
                        'variantSellPrice': 79.99,
                        'variantQuantity': 100,
                        'variantKey': 'Switch: Blue, Layout: US'
                    },
                    {
                        'vid': 'V002',
                        'variantSku': 'KB-RGB-RED',
                        'variantSellPrice': 84.99,
                        'variantQuantity': 80,
                        'variantKey': 'Switch: Red, Layout: US'
                    },
                    {
                        'vid': 'V003',
                        'variantSku': 'KB-RGB-BRN',
                        'variantSellPrice': 89.99,
                        'variantQuantity': 70,
                        'variantKey': 'Switch: Brown, Layout: US'
                    }
                ],
                'categoryName': 'Computer Accessories',
                'sourceFrom': 'CN Warehouse',
                'packWeight': 1.2,
                'packLength': 45,
                'packWidth': 15,
                'packHeight': 5
            },
            {
                'pid': 'CJ001234568',
                'productName': 'Wireless Gaming Mouse 16000 DPI',
                'description': 'Mouse gamer sem fio com sensor óptico 16000 DPI, 7 botões programáveis, bateria de 70h e iluminação RGB. Perfeito para jogos competitivos.',
                'sellPrice': 45.99,
                'quantity': 180,
                'image': 'https://img.cjdropshipping.com/CJ001234568_1.jpg',
                'images': [
                    'https://img.cjdropshipping.com/CJ001234568_1.jpg',
                    'https://img.cjdropshipping.com/CJ001234568_2.jpg'
                ],
                'variants': [
                    {
                        'vid': 'V004',
                        'variantSku': 'MS-WL-BLK',
                        'variantSellPrice': 45.99,
                        'variantQuantity': 90,
                        'variantKey': 'Color: Black'
                    },
                    {
                        'vid': 'V005',
                        'variantSku': 'MS-WL-WHT',
                        'variantSellPrice': 45.99,
                        'variantQuantity': 90,
                        'variantKey': 'Color: White'
                    }
                ],
                'categoryName': 'Computer Accessories',
                'sourceFrom': 'CN Warehouse',
                'packWeight': 0.3,
                'packLength': 15,
                'packWidth': 8,
                'packHeight': 4
            },
            {
                'pid': 'CJ001234569',
                'productName': 'LED Strip Lights 5M RGB WiFi',
                'description': 'Fita LED RGB 5 metros com controle WiFi, compatível com Alexa e Google Home, 16 milhões de cores e efeitos musicais.',
                'sellPrice': 24.99,
                'quantity': 400,
                'image': 'https://img.cjdropshipping.com/CJ001234569_1.jpg',
                'images': [
                    'https://img.cjdropshipping.com/CJ001234569_1.jpg',
                    'https://img.cjdropshipping.com/CJ001234569_2.jpg',
                    'https://img.cjdropshipping.com/CJ001234569_3.jpg'
                ],
                'variants': [
                    {
                        'vid': 'V006',
                        'variantSku': 'LED-5M-RGB',
                        'variantSellPrice': 24.99,
                        'variantQuantity': 200,
                        'variantKey': 'Length: 5M, Type: RGB'
                    },
                    {
                        'vid': 'V007',
                        'variantSku': 'LED-10M-RGB',
                        'variantSellPrice': 39.99,
                        'variantQuantity': 150,
                        'variantKey': 'Length: 10M, Type: RGB'
                    },
                    {
                        'vid': 'V008',
                        'variantSku': 'LED-5M-RGBW',
                        'variantSellPrice': 29.99,
                        'variantQuantity': 50,
                        'variantKey': 'Length: 5M, Type: RGBW'
                    }
                ],
                'categoryName': 'Home & Garden',
                'sourceFrom': 'CN Warehouse',
                'packWeight': 0.5,
                'packLength': 20,
                'packWidth': 15,
                'packHeight': 3
            },
            {
                'pid': 'CJ001234570',
                'productName': 'Bluetooth Speaker Waterproof 20W',
                'description': 'Caixa de som Bluetooth à prova d\'água IPX7, potência 20W, bateria 12h, microfone integrado e graves potentes.',
                'sellPrice': 35.99,
                'quantity': 320,
                'image': 'https://img.cjdropshipping.com/CJ001234570_1.jpg',
                'images': [
                    'https://img.cjdropshipping.com/CJ001234570_1.jpg',
                    'https://img.cjdropshipping.com/CJ001234570_2.jpg'
                ],
                'variants': [
                    {
                        'vid': 'V009',
                        'variantSku': 'SPK-BT-BLK',
                        'variantSellPrice': 35.99,
                        'variantQuantity': 120,
                        'variantKey': 'Color: Black'
                    },
                    {
                        'vid': 'V010',
                        'variantSku': 'SPK-BT-BLU',
                        'variantSellPrice': 35.99,
                        'variantQuantity': 100,
                        'variantKey': 'Color: Blue'
                    },
                    {
                        'vid': 'V011',
                        'variantSku': 'SPK-BT-RED',
                        'variantSellPrice': 35.99,
                        'variantQuantity': 100,
                        'variantKey': 'Color: Red'
                    }
                ],
                'categoryName': 'Electronics',
                'sourceFrom': 'CN Warehouse',
                'packWeight': 0.8,
                'packLength': 18,
                'packWidth': 8,
                'packHeight': 8
            },
            {
                'pid': 'CJ001234571',
                'productName': 'Car Phone Mount Magnetic Wireless Charger',
                'description': 'Suporte veicular magnético com carregamento sem fio 15W, rotação 360°, compatível com iPhone e Android.',
                'sellPrice': 28.99,
                'quantity': 150,
                'image': 'https://img.cjdropshipping.com/CJ001234571_1.jpg',
                'images': [
                    'https://img.cjdropshipping.com/CJ001234571_1.jpg',
                    'https://img.cjdropshipping.com/CJ001234571_2.jpg'
                ],
                'variants': [
                    {
                        'vid': 'V012',
                        'variantSku': 'CAR-MAG-15W',
                        'variantSellPrice': 28.99,
                        'variantQuantity': 75,
                        'variantKey': 'Power: 15W, Mount: Vent'
                    },
                    {
                        'vid': 'V013',
                        'variantSku': 'CAR-MAG-10W',
                        'variantSellPrice': 24.99,
                        'variantQuantity': 75,
                        'variantKey': 'Power: 10W, Mount: Dashboard'
                    }
                ],
                'categoryName': 'Car Accessories',
                'sourceFrom': 'CN Warehouse',
                'packWeight': 0.4,
                'packLength': 12,
                'packWidth': 10,
                'packHeight': 6
            }
        ]

    def authenticate(self) -> bool:
        """
        Simula autenticação bem-sucedida.
        
        Returns:
            bool: Sempre True para demonstração
        """
        logger.info("Demo CJ Dropshipping: Autenticação simulada bem-sucedida")
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
                if demo_product['pid'] == product_id:
                    return self._parse_demo_product(demo_product)
            
            logger.warning(f"Demo CJ Dropshipping: Produto {product_id} não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Demo CJ Dropshipping: Erro ao obter produto {product_id}: {e}")
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
                if (query_lower in demo_product['productName'].lower() or 
                    query_lower in demo_product['description'].lower() or
                    query_lower in demo_product['categoryName'].lower()):
                    
                    product = self._parse_demo_product(demo_product)
                    results.append(product)
            
            logger.info(f"Demo CJ Dropshipping: Encontrados {len(results)} produtos para '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Demo CJ Dropshipping: Erro na busca de produtos: {e}")
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
            
            # Simula sucesso em 95% dos casos
            if random.random() < 0.95:
                supplier_order_id = f"CJ{int(time.time())}{random.randint(100, 999)}"
                
                return OrderResponse(
                    success=True,
                    order_id=order.id,
                    supplier_order_id=supplier_order_id,
                    tracking_number=None,  # Será gerado posteriormente
                    estimated_delivery=(datetime.now() + timedelta(days=8)).isoformat(),
                    message="Pedido criado com sucesso (simulado)"
                )
            else:
                # Simula erro ocasional
                error_messages = [
                    "Produto temporariamente indisponível",
                    "Endereço de entrega não atendido",
                    "Quantidade solicitada excede estoque",
                    "Erro na validação do pedido"
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
            logger.error(f"Demo CJ Dropshipping: Erro ao criar pedido: {e}")
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
                    'date': (datetime.now() - timedelta(days=6)).isoformat(),
                    'description': 'Pedido recebido e confirmado',
                    'location': 'Shenzhen, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=5)).isoformat(),
                    'description': 'Produto separado no armazém',
                    'location': 'Shenzhen, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=4)).isoformat(),
                    'description': 'Produto embalado e etiquetado',
                    'location': 'Shenzhen, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=3)).isoformat(),
                    'description': 'Produto despachado para transporte internacional',
                    'location': 'Shenzhen, China'
                },
                {
                    'date': (datetime.now() - timedelta(days=1)).isoformat(),
                    'description': 'Produto chegou ao centro de distribuição',
                    'location': 'São Paulo, Brasil'
                },
                {
                    'date': datetime.now().isoformat(),
                    'description': 'Produto saiu para entrega',
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
            logger.error(f"Demo CJ Dropshipping: Erro ao obter rastreamento: {e}")
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
                    'service_name': 'CJ Packet',
                    'cost': 0.00,
                    'currency': 'USD',
                    'delivery_time': '8-16 days',
                    'description': 'Frete grátis padrão'
                },
                {
                    'service_name': 'CJ Express',
                    'cost': 12.99,
                    'currency': 'USD',
                    'delivery_time': '6-12 days',
                    'description': 'Entrega mais rápida com rastreamento'
                },
                {
                    'service_name': 'DHL Express',
                    'cost': 29.99,
                    'currency': 'USD',
                    'delivery_time': '3-7 days',
                    'description': 'Entrega expressa internacional'
                },
                {
                    'service_name': 'FedEx Priority',
                    'cost': 34.99,
                    'currency': 'USD',
                    'delivery_time': '2-5 days',
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
            logger.error(f"Demo CJ Dropshipping: Erro ao calcular frete: {e}")
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
                if demo_product['pid'] == product_id:
                    inventory[product_id] = demo_product['quantity']
                    break
            else:
                # Produto não encontrado
                inventory[product_id] = 0
        
        logger.info(f"Demo CJ Dropshipping: Sincronizado estoque de {len(product_ids)} produtos")
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
        if demo_product.get('image'):
            images.append(demo_product['image'])
        if demo_product.get('images'):
            images.extend(demo_product['images'])
        
        # Extrai variações
        variations = []
        if demo_product.get('variants'):
            for variant in demo_product['variants']:
                variations.append({
                    'variant_id': variant.get('vid'),
                    'sku': variant.get('variantSku'),
                    'price': variant.get('variantSellPrice'),
                    'stock': variant.get('variantQuantity'),
                    'attributes': variant.get('variantKey')
                })
        
        # Informações de envio
        shipping_info = {
            'warehouse': demo_product.get('sourceFrom'),
            'weight': demo_product.get('packWeight'),
            'dimensions': {
                'length': demo_product.get('packLength'),
                'width': demo_product.get('packWidth'),
                'height': demo_product.get('packHeight')
            }
        }
        
        return Product(
            id=demo_product['pid'],
            name=demo_product['productName'],
            description=demo_product['description'],
            price=float(demo_product['sellPrice']),
            currency='USD',
            stock_quantity=int(demo_product['quantity']),
            images=images,
            variations=variations,
            category=demo_product['categoryName'],
            supplier_id='cj_dropshipping_demo',
            supplier_product_id=demo_product['pid'],
            shipping_info=shipping_info,
            last_updated=datetime.now().isoformat()
        )

