"""
Rotas para configuração e teste do conector de demonstração.
"""

from flask import Blueprint, request, jsonify
from src.models.demo_aliexpress_connector import DemoAliExpressConnector
from src.models.connector_base import ConnectorConfig, ConnectorStatus
from src.models.connector_manager import connector_manager
import logging

logger = logging.getLogger(__name__)

demo_bp = Blueprint('demo', __name__)


@demo_bp.route('/demo/setup-aliexpress', methods=['POST'])
def setup_demo_aliexpress():
    """Configura o conector de demonstração do AliExpress."""
    try:
        # Configuração padrão para demonstração
        config = ConnectorConfig(
            name='aliexpress_demo',
            api_key='demo_app_key',
            api_secret='demo_app_secret',
            base_url='https://demo-api.aliexpress.com',
            timeout=30,
            max_retries=3,
            status=ConnectorStatus.ACTIVE,
            additional_config={
                'demo_mode': True,
                'default_country': 'US',
                'default_currency': 'USD',
                'default_language': 'en'
            }
        )

        # Cria e registra o conector de demonstração
        connector = DemoAliExpressConnector(config)
        success = connector_manager.register_connector('aliexpress_demo', connector)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Conector de demonstração AliExpress configurado com sucesso',
                'connector_info': connector.get_connector_info(),
                'demo_mode': True,
                'available_products': len(connector.demo_products)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Falha ao registrar o conector de demonstração'
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao configurar conector demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@demo_bp.route('/demo/test-search', methods=['POST'])
def test_demo_search():
    """Testa a busca de produtos no conector de demonstração."""
    try:
        data = request.get_json()
        query = data.get('query', 'smartphone')
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('aliexpress_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração não está configurado. Use /api/demo/setup-aliexpress primeiro.'
            }), 404

        # Busca produtos
        products = connector.search_products(query)
        
        # Formata resposta
        formatted_products = []
        for product in products:
            formatted_products.append({
                'id': product.id,
                'name': product.name,
                'description': product.description[:100] + '...' if len(product.description) > 100 else product.description,
                'price': product.price,
                'currency': product.currency,
                'stock': product.stock_quantity,
                'images': product.images,
                'variations_count': len(product.variations),
                'category': product.category,
                'shipping_info': product.shipping_info
            })
        
        return jsonify({
            'success': True,
            'query': query,
            'products_found': len(products),
            'products': formatted_products,
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar busca demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@demo_bp.route('/demo/test-product-details', methods=['POST'])
def test_demo_product_details():
    """Testa a obtenção de detalhes de um produto específico."""
    try:
        data = request.get_json()
        
        if 'product_id' not in data:
            return jsonify({
                'success': False,
                'message': 'product_id é obrigatório'
            }), 400

        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('aliexpress_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração não está configurado'
            }), 404

        # Obtém detalhes do produto
        product = connector.get_product_details(data['product_id'])
        
        if product:
            return jsonify({
                'success': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'currency': product.currency,
                    'stock_quantity': product.stock_quantity,
                    'images': product.images,
                    'variations': product.variations,
                    'category': product.category,
                    'shipping_info': product.shipping_info,
                    'last_updated': product.last_updated
                },
                'demo_mode': True
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao testar detalhes do produto demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@demo_bp.route('/demo/test-create-order', methods=['POST'])
def test_demo_create_order():
    """Testa a criação de um pedido simulado."""
    try:
        data = request.get_json()
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('aliexpress_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração não está configurado'
            }), 404

        # Dados de exemplo para teste
        from src.models.connector_base import Order, OrderItem, Address
        
        # Endereço de exemplo
        address = Address(
            full_name=data.get('full_name', 'João Silva'),
            address_line1=data.get('address', 'Rua das Flores, 123'),
            address_line2=None,
            city=data.get('city', 'São Paulo'),
            state=data.get('state', 'SP'),
            postal_code=data.get('postal_code', '01234-567'),
            country=data.get('country', 'BR'),
            phone=data.get('phone', '+55 11 99999-9999'),
            email=data.get('email', 'joao@email.com')
        )
        
        # Item de exemplo
        items = [
            OrderItem(
                product_id=data.get('product_id', '1005004043442825'),
                supplier_product_id=data.get('product_id', '1005004043442825'),
                quantity=data.get('quantity', 1),
                price=data.get('price', 299.99),
                variation_id='SKU001',
                variation_attributes={'sku_attr': '14:350853#Black;5:361386#128GB'}
            )
        ]
        
        # Pedido de exemplo
        order = Order(
            id=f"ORDER_{int(time.time())}",
            items=items,
            shipping_address=address,
            total_amount=data.get('total_amount', 299.99),
            currency='USD',
            shipping_method='AliExpress Standard Shipping',
            notes='Pedido de teste - demonstração'
        )
        
        # Cria o pedido
        response = connector.create_order(order)
        
        return jsonify({
            'success': response.success,
            'order_id': response.order_id,
            'supplier_order_id': response.supplier_order_id,
            'tracking_number': response.tracking_number,
            'estimated_delivery': response.estimated_delivery,
            'message': response.message,
            'error_code': response.error_code,
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar criação de pedido demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@demo_bp.route('/demo/test-tracking', methods=['POST'])
def test_demo_tracking():
    """Testa o rastreamento de um pedido simulado."""
    try:
        data = request.get_json()
        
        if 'tracking_number' not in data:
            return jsonify({
                'success': False,
                'message': 'tracking_number é obrigatório'
            }), 400

        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('aliexpress_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração não está configurado'
            }), 404

        # Obtém informações de rastreamento
        tracking_info = connector.get_tracking_info(data['tracking_number'])
        
        if tracking_info:
            return jsonify({
                'success': True,
                'tracking': {
                    'tracking_number': tracking_info.tracking_number,
                    'status': tracking_info.status.value,
                    'events': tracking_info.events,
                    'estimated_delivery': tracking_info.estimated_delivery,
                    'last_updated': tracking_info.last_updated
                },
                'demo_mode': True
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Informações de rastreamento não encontradas'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao testar rastreamento demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@demo_bp.route('/demo/test-shipping', methods=['POST'])
def test_demo_shipping():
    """Testa o cálculo de frete simulado."""
    try:
        data = request.get_json()
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('aliexpress_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração não está configurado'
            }), 404

        # Dados de exemplo para teste
        from src.models.connector_base import OrderItem, Address
        
        # Endereço de exemplo
        address = Address(
            full_name='João Silva',
            address_line1='Rua das Flores, 123',
            address_line2=None,
            city=data.get('city', 'São Paulo'),
            state=data.get('state', 'SP'),
            postal_code='01234-567',
            country=data.get('country', 'BR'),
            phone='+55 11 99999-9999',
            email='joao@email.com'
        )
        
        # Itens de exemplo
        items = [
            OrderItem(
                product_id='1005004043442825',
                supplier_product_id='1005004043442825',
                quantity=data.get('quantity', 1),
                price=299.99
            )
        ]
        
        # Calcula frete
        shipping_options = connector.calculate_shipping(items, address)
        
        return jsonify({
            'success': True,
            'shipping_options': shipping_options,
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar cálculo de frete demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@demo_bp.route('/demo/available-products', methods=['GET'])
def get_demo_products():
    """Lista todos os produtos disponíveis na demonstração."""
    try:
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('aliexpress_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração não está configurado'
            }), 404

        # Lista produtos disponíveis
        products = []
        for demo_product in connector.demo_products:
            products.append({
                'id': demo_product['id'],
                'name': demo_product['name'],
                'price': demo_product['price'],
                'currency': demo_product['currency'],
                'stock': demo_product['stock_quantity'],
                'category': demo_product['category'],
                'variations_count': len(demo_product['variations'])
            })
        
        return jsonify({
            'success': True,
            'products': products,
            'total_products': len(products),
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar produtos demo: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


import time

