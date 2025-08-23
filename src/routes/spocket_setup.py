"""
Rotas para configuração e teste do conector Spocket.
"""

from flask import Blueprint, request, jsonify
from src.models.spocket_connector import SpocketConnector
from src.models.demo_spocket_connector import DemoSpocketConnector
from src.models.connector_base import ConnectorConfig, ConnectorStatus
from src.models.connector_manager import connector_manager
import logging

logger = logging.getLogger(__name__)

spocket_bp = Blueprint('spocket', __name__)


@spocket_bp.route('/spocket/setup', methods=['POST'])
def setup_spocket_connector():
    """Configura o conector Spocket com as credenciais fornecidas."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['api_key']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Configuração adicional
        additional_config = {
            'default_country': data.get('default_country', 'US'),
            'default_currency': data.get('default_currency', 'USD')
        }

        # Cria a configuração do conector
        config = ConnectorConfig(
            name='spocket',
            api_key=data['api_key'],
            api_secret=data.get('api_secret', ''),  # Spocket pode não usar secret
            base_url=data.get('base_url', 'https://api.spocket.co/api/v1'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            status=ConnectorStatus.ACTIVE,
            additional_config=additional_config
        )

        # Cria e registra o conector
        connector = SpocketConnector(config)
        
        # Testa a conexão antes de registrar
        if connector.test_connection():
            success = connector_manager.register_connector('spocket', connector)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Conector Spocket configurado com sucesso',
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
                'message': 'Falha na autenticação com Spocket. Verifique a API key.'
            }), 401
            
    except Exception as e:
        logger.error(f"Erro ao configurar conector Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/test-auth', methods=['POST'])
def test_spocket_auth():
    """Testa a autenticação com Spocket sem registrar o conector."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['api_key']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Configuração temporária para teste
        additional_config = {
            'default_country': data.get('default_country', 'US'),
            'default_currency': data.get('default_currency', 'USD')
        }

        config = ConnectorConfig(
            name='spocket_test',
            api_key=data['api_key'],
            api_secret=data.get('api_secret', ''),
            base_url=data.get('base_url', 'https://api.spocket.co/api/v1'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            status=ConnectorStatus.ACTIVE,
            additional_config=additional_config
        )

        # Cria conector temporário para teste
        connector = SpocketConnector(config)
        
        # Testa autenticação
        auth_success = connector.authenticate()
        
        return jsonify({
            'success': auth_success,
            'message': 'Autenticação bem-sucedida' if auth_success else 'Falha na autenticação',
            'api_key_valid': auth_success
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar autenticação Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/demo/setup', methods=['POST'])
def setup_spocket_demo():
    """Configura o conector de demonstração do Spocket."""
    try:
        # Configuração padrão para demonstração
        config = ConnectorConfig(
            name='spocket_demo',
            api_key='demo_api_key',
            api_secret='demo_api_secret',
            base_url='https://demo-api.spocket.co',
            timeout=30,
            max_retries=3,
            status=ConnectorStatus.ACTIVE,
            additional_config={
                'demo_mode': True,
                'default_country': 'US',
                'default_currency': 'USD'
            }
        )

        # Cria e registra o conector de demonstração
        connector = DemoSpocketConnector(config)
        success = connector_manager.register_connector('spocket_demo', connector)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Conector de demonstração Spocket configurado com sucesso',
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
        logger.error(f"Erro ao configurar conector demo Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/demo/test-search', methods=['POST'])
def test_spocket_demo_search():
    """Testa a busca de produtos no conector de demonstração Spocket."""
    try:
        data = request.get_json()
        query = data.get('query', 'organic')
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('spocket_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração Spocket não está configurado. Use /api/spocket/demo/setup primeiro.'
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
        logger.error(f"Erro ao testar busca demo Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/demo/test-product-details', methods=['POST'])
def test_spocket_demo_product_details():
    """Testa a obtenção de detalhes de um produto específico."""
    try:
        data = request.get_json()
        
        if 'product_id' not in data:
            return jsonify({
                'success': False,
                'message': 'product_id é obrigatório'
            }), 400

        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('spocket_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração Spocket não está configurado'
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
        logger.error(f"Erro ao testar detalhes do produto demo Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/demo/available-products', methods=['GET'])
def get_spocket_demo_products():
    """Lista todos os produtos disponíveis na demonstração Spocket."""
    try:
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('spocket_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração Spocket não está configurado'
            }), 404

        # Lista produtos disponíveis
        products = []
        for demo_product in connector.demo_products:
            products.append({
                'id': demo_product['id'],
                'name': demo_product['title'],
                'price': demo_product['price'],
                'currency': 'USD',
                'stock': demo_product['inventory_quantity'],
                'category': demo_product['product_type'],
                'origin_country': demo_product['origin_country'],
                'variations_count': len(demo_product['variants'])
            })
        
        return jsonify({
            'success': True,
            'products': products,
            'total_products': len(products),
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar produtos demo Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/status', methods=['GET'])
def get_spocket_status():
    """Obtém o status atual do conector Spocket."""
    try:
        connector = connector_manager.get_connector('spocket')
        
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector Spocket não está configurado',
                'configured': False
            })

        # Testa conexão
        is_working = connector.test_connection()
        
        return jsonify({
            'success': True,
            'configured': True,
            'working': is_working,
            'connector_info': connector.get_connector_info()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status do Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@spocket_bp.route('/spocket/demo/test-create-order', methods=['POST'])
def test_spocket_demo_create_order():
    """Testa a criação de um pedido simulado no Spocket."""
    try:
        data = request.get_json()
        
        # Verifica se o conector demo está registrado
        connector = connector_manager.get_connector('spocket_demo')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector de demonstração Spocket não está configurado'
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
            phone=data.get('phone', '+55 11 99999-8888'),
            email=data.get('email', 'joao@email.com')
        )
        
        # Item de exemplo
        items = [
            OrderItem(
                product_id=data.get('product_id', 'SP001234567'),
                supplier_product_id=data.get('product_id', 'SP001234567'),
                quantity=data.get('quantity', 1),
                price=data.get('price', 24.99),
                variation_id='SPV001',
                variation_attributes={'option1': 'Black', 'option2': 'Small'}
            )
        ]
        
        # Pedido de exemplo
        order = Order(
            id=f"SP_ORDER_{int(time.time())}",
            items=items,
            shipping_address=address,
            total_amount=data.get('total_amount', 24.99),
            currency='USD',
            shipping_method='Standard',
            notes='Pedido de teste Spocket - demonstração'
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
        logger.error(f"Erro ao testar criação de pedido demo Spocket: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


import time

