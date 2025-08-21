"""
Rotas para configuração e teste do conector CJ Dropshipping.
"""

from flask import Blueprint, request, jsonify
from src.models.cj_dropshipping_connector import CJDropshippingConnector
from src.models.demo_cj_connector import DemoCJDropshippingConnector
from src.models.connector_base import ConnectorConfig, ConnectorStatus
from src.models.connector_manager import connector_manager
import logging

logger = logging.getLogger(__name__)

cj_bp = Blueprint('cj_dropshipping', __name__)


@cj_bp.route('/cj/setup', methods=['POST'])
def setup_cj_connector():
    """Configura o conector CJ Dropshipping com as credenciais fornecidas."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['access_key', 'secret_key']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Configuração adicional
        additional_config = {
            'access_token': data.get('access_token'),
            'default_country': data.get('default_country', 'US'),
            'default_currency': data.get('default_currency', 'USD'),
            'warehouse_id': data.get('warehouse_id', 'CN')
        }

        # Cria a configuração do conector
        config = ConnectorConfig(
            name='cj_dropshipping',
            api_key=data['access_key'],
            api_secret=data['secret_key'],
            base_url=data.get('base_url', 'https://developers.cjdropshipping.com/api2.0/v1'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            status=ConnectorStatus.ACTIVE,
            additional_config=additional_config
        )

        # Cria e registra o conector
        connector = CJDropshippingConnector(config)
        
        # Testa a conexão antes de registrar
        if connector.test_connection():
            success = connector_manager.register_connector('cj_dropshipping', connector)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Conector CJ Dropshipping configurado com sucesso',
                    'connector_info': connector.get_connector_info()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Falha ao registrar o conector'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'Falha na autenticação com CJ Dropshipping. Verifique as credenciais.'
            }), 401
            
    except Exception as e:
        logger.error(f"Erro ao configurar conector CJ Dropshipping: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/test-auth', methods=['POST'])
def test_cj_auth():
    """Testa a autenticação com CJ Dropshipping sem registrar o conector."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['access_key', 'secret_key']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Configuração temporária para teste
        additional_config = {
            'access_token': data.get('access_token'),
            'default_country': data.get('default_country', 'US'),
            'default_currency': data.get('default_currency', 'USD'),
            'warehouse_id': data.get('warehouse_id', 'CN')
        }

        config = ConnectorConfig(
            name='cj_dropshipping_test',
            api_key=data['access_key'],
            api_secret=data['secret_key'],
            base_url=data.get('base_url', 'https://developers.cjdropshipping.com/api2.0/v1'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            status=ConnectorStatus.ACTIVE,
            additional_config=additional_config
        )

        # Cria conector temporário para teste
        connector = CJDropshippingConnector(config)
        
        # Testa autenticação
        auth_success = connector.authenticate()
        
        return jsonify({
            'success': auth_success,
            'message': 'Autenticação bem-sucedida' if auth_success else 'Falha na autenticação',
            'has_access_token': bool(data.get('access_token')),
            'access_token': connector.access_token if auth_success else None
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar autenticação CJ Dropshipping: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/demo/setup', methods=['POST'])
def setup_cj_demo():
    """Configura o conector de demonstração do CJ Dropshipping."""
    try:
        # Configuração padrão para demonstração
        config = ConnectorConfig(
            name='cj_dropshipping_demo',
            api_key='demo_access_key',
            api_secret='demo_secret_key',
            base_url='https://demo-api.cjdropshipping.com',
            timeout=30,
            max_retries=3,
            status=ConnectorStatus.ACTIVE,
            additional_config={
                'demo_mode': True,
                'default_country': 'US',
                'default_currency': 'USD',
                'warehouse_id': 'CN'
            }
        )

        # Cria e registra o conector de demonstração
        connector = DemoCJDropshippingConnector(config)
        success = connector_manager.register_connector('cj_dropshipping_demo', connector)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Conector de demonstração CJ Dropshipping configurado com sucesso',
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
        logger.error(f"Erro ao configurar conector demo CJ: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/demo/test-search', methods=['POST'])
def test_cj_demo_search():
    """Testa a busca de produtos no conector de demonstração CJ."""
    try:
        data = request.get_json()
        query = data.get('query', 'gaming')
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('cj_dropshipping_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração CJ não está configurado. Use /api/cj/demo/setup primeiro.'
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
        logger.error(f"Erro ao testar busca demo CJ: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/demo/test-product-details', methods=['POST'])
def test_cj_demo_product_details():
    """Testa a obtenção de detalhes de um produto específico."""
    try:
        data = request.get_json()
        
        if 'product_id' not in data:
            return jsonify({
                'success': False,
                'message': 'product_id é obrigatório'
            }), 400

        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('cj_dropshipping_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração CJ não está configurado'
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
        logger.error(f"Erro ao testar detalhes do produto demo CJ: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/demo/available-products', methods=['GET'])
def get_cj_demo_products():
    """Lista todos os produtos disponíveis na demonstração CJ."""
    try:
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('cj_dropshipping_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração CJ não está configurado'
            }), 404

        # Lista produtos disponíveis
        products = []
        for demo_product in connector.demo_products:
            products.append({
                'id': demo_product['pid'],
                'name': demo_product['productName'],
                'price': demo_product['sellPrice'],
                'currency': 'USD',
                'stock': demo_product['quantity'],
                'category': demo_product['categoryName'],
                'variations_count': len(demo_product['variants'])
            })
        
        return jsonify({
            'success': True,
            'products': products,
            'total_products': len(products),
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar produtos demo CJ: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/status', methods=['GET'])
def get_cj_status():
    """Obtém o status atual do conector CJ Dropshipping."""
    try:
        connector = connector_manager.get_connector('cj_dropshipping')
        
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector CJ Dropshipping não está configurado',
                'configured': False
            })

        # Testa conexão
        is_working = connector.test_connection()
        
        return jsonify({
            'success': True,
            'configured': True,
            'working': is_working,
            'connector_info': connector.get_connector_info(),
            'has_access_token': bool(connector.access_token)
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status do CJ Dropshipping: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@cj_bp.route('/cj/demo/test-create-order', methods=['POST'])
def test_cj_demo_create_order():
    """Testa a criação de um pedido simulado no CJ."""
    try:
        data = request.get_json()
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('cj_dropshipping_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração CJ não está configurado'
            }), 404

        # Dados de exemplo para teste
        from src.models.connector_base import Order, OrderItem, Address
        
        # Endereço de exemplo
        address = Address(
            full_name=data.get('full_name', 'Maria Santos'),
            address_line1=data.get('address', 'Av. Paulista, 1000'),
            address_line2=None,
            city=data.get('city', 'São Paulo'),
            state=data.get('state', 'SP'),
            postal_code=data.get('postal_code', '01310-100'),
            country=data.get('country', 'BR'),
            phone=data.get('phone', '+55 11 98888-7777'),
            email=data.get('email', 'maria@email.com')
        )
        
        # Item de exemplo
        items = [
            OrderItem(
                product_id=data.get('product_id', 'CJ001234567'),
                supplier_product_id=data.get('product_id', 'CJ001234567'),
                quantity=data.get('quantity', 1),
                price=data.get('price', 79.99),
                variation_id='V001',
                variation_attributes={'variantKey': 'Switch: Blue, Layout: US'}
            )
        ]
        
        # Pedido de exemplo
        order = Order(
            id=f"CJ_ORDER_{int(time.time())}",
            items=items,
            shipping_address=address,
            total_amount=data.get('total_amount', 79.99),
            currency='USD',
            shipping_method='CJ_PACKET',
            notes='Pedido de teste CJ - demonstração'
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
        logger.error(f"Erro ao testar criação de pedido demo CJ: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


import time

