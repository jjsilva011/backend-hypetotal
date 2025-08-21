"""
Rotas da API para gerenciamento de conectores de dropshipping.
"""

from flask import Blueprint, request, jsonify
from src.models.connector_manager import connector_manager
from src.models.connector_base import Address, OrderItem, Order
import logging

logger = logging.getLogger(__name__)

connectors_bp = Blueprint('connectors', __name__)


@connectors_bp.route('/connectors', methods=['GET'])
def list_connectors():
    """Lista todos os conectores registrados."""
    try:
        connectors = connector_manager.list_connectors()
        return jsonify({
            'success': True,
            'connectors': connectors
        })
    except Exception as e:
        logger.error(f"Erro ao listar conectores: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/connectors/health', methods=['GET'])
def health_check():
    """Verifica a saúde de todos os conectores."""
    try:
        health_status = connector_manager.health_check()
        return jsonify({
            'success': True,
            'health': health_status
        })
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/connectors/<connector_name>/test', methods=['POST'])
def test_connector(connector_name):
    """Testa a conexão de um conector específico."""
    try:
        connector = connector_manager.get_connector(connector_name)
        if not connector:
            return jsonify({
                'success': False,
                'message': f'Conector {connector_name} não encontrado'
            }), 404

        is_working = connector.test_connection()
        return jsonify({
            'success': True,
            'connector': connector_name,
            'working': is_working
        })
    except Exception as e:
        logger.error(f"Erro ao testar conector {connector_name}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/products/search', methods=['POST'])
def search_products():
    """Busca produtos em todos os conectores ativos."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Query é obrigatória'
            }), 400

        # Parâmetros opcionais
        category = data.get('category')
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        country = data.get('country', 'US')

        kwargs = {}
        if category:
            kwargs['category'] = category
        if min_price:
            kwargs['min_price'] = min_price
        if max_price:
            kwargs['max_price'] = max_price
        if country:
            kwargs['country'] = country

        results = connector_manager.search_products_all(query, **kwargs)
        
        # Converte produtos para dicionários
        formatted_results = {}
        for supplier, products in results.items():
            formatted_results[supplier] = [
                {
                    'id': p.id,
                    'name': p.name,
                    'description': p.description,
                    'price': p.price,
                    'currency': p.currency,
                    'stock_quantity': p.stock_quantity,
                    'images': p.images,
                    'variations': p.variations,
                    'category': p.category,
                    'supplier_id': p.supplier_id,
                    'supplier_product_id': p.supplier_product_id,
                    'shipping_info': p.shipping_info,
                    'last_updated': p.last_updated
                }
                for p in products
            ]

        return jsonify({
            'success': True,
            'query': query,
            'results': formatted_results
        })
    except Exception as e:
        logger.error(f"Erro ao buscar produtos: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/products/<supplier_name>/<product_id>', methods=['GET'])
def get_product_details(supplier_name, product_id):
    """Obtém detalhes de um produto específico de um fornecedor."""
    try:
        # Parâmetros opcionais da query string
        country = request.args.get('country', 'US')
        currency = request.args.get('currency', 'USD')
        language = request.args.get('language', 'en')

        kwargs = {
            'country': country,
            'currency': currency,
            'language': language
        }

        product = connector_manager.get_product_details_from_supplier(
            supplier_name, product_id, **kwargs
        )

        if not product:
            return jsonify({
                'success': False,
                'message': f'Produto {product_id} não encontrado no fornecedor {supplier_name}'
            }), 404

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
                'supplier_id': product.supplier_id,
                'supplier_product_id': product.supplier_product_id,
                'shipping_info': product.shipping_info,
                'last_updated': product.last_updated
            }
        })
    except Exception as e:
        logger.error(f"Erro ao obter produto {product_id} do {supplier_name}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/orders/create', methods=['POST'])
def create_order():
    """Cria um pedido com um fornecedor específico."""
    try:
        data = request.get_json()
        
        # Validação dos dados obrigatórios
        required_fields = ['supplier_name', 'items', 'shipping_address']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Constrói o endereço
        addr_data = data['shipping_address']
        address = Address(
            full_name=addr_data['full_name'],
            address_line1=addr_data['address_line1'],
            address_line2=addr_data.get('address_line2'),
            city=addr_data['city'],
            state=addr_data['state'],
            postal_code=addr_data['postal_code'],
            country=addr_data['country'],
            phone=addr_data['phone'],
            email=addr_data.get('email')
        )

        # Constrói os itens do pedido
        items = []
        for item_data in data['items']:
            item = OrderItem(
                product_id=item_data['product_id'],
                supplier_product_id=item_data['supplier_product_id'],
                quantity=item_data['quantity'],
                price=item_data['price'],
                variation_id=item_data.get('variation_id'),
                variation_attributes=item_data.get('variation_attributes')
            )
            items.append(item)

        # Constrói o pedido
        order = Order(
            id=data.get('order_id', ''),
            items=items,
            shipping_address=address,
            total_amount=data['total_amount'],
            currency=data.get('currency', 'USD'),
            shipping_method=data.get('shipping_method', 'standard'),
            notes=data.get('notes')
        )

        # Cria o pedido
        response = connector_manager.create_order_with_supplier(
            data['supplier_name'], order
        )

        return jsonify({
            'success': response.success,
            'order_id': response.order_id,
            'supplier_order_id': response.supplier_order_id,
            'tracking_number': response.tracking_number,
            'estimated_delivery': response.estimated_delivery,
            'message': response.message,
            'error_code': response.error_code
        })
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/shipping/calculate', methods=['POST'])
def calculate_shipping():
    """Calcula opções de envio para um pedido."""
    try:
        data = request.get_json()
        
        # Validação dos dados obrigatórios
        if 'items' not in data or 'shipping_address' not in data:
            return jsonify({
                'success': False,
                'message': 'Items e shipping_address são obrigatórios'
            }), 400

        # Constrói o endereço
        addr_data = data['shipping_address']
        address = Address(
            full_name=addr_data['full_name'],
            address_line1=addr_data['address_line1'],
            address_line2=addr_data.get('address_line2'),
            city=addr_data['city'],
            state=addr_data['state'],
            postal_code=addr_data['postal_code'],
            country=addr_data['country'],
            phone=addr_data['phone'],
            email=addr_data.get('email')
        )

        # Constrói os itens
        items = []
        for item_data in data['items']:
            item = OrderItem(
                product_id=item_data['product_id'],
                supplier_product_id=item_data['supplier_product_id'],
                quantity=item_data['quantity'],
                price=item_data['price'],
                variation_id=item_data.get('variation_id'),
                variation_attributes=item_data.get('variation_attributes')
            )
            items.append(item)

        # Calcula opções de envio
        shipping_options = connector_manager.calculate_shipping_options(items, address)

        return jsonify({
            'success': True,
            'shipping_options': shipping_options
        })
    except Exception as e:
        logger.error(f"Erro ao calcular frete: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/inventory/sync', methods=['POST'])
def sync_inventory():
    """Sincroniza estoque de produtos específicos."""
    try:
        data = request.get_json()
        
        if 'product_mapping' not in data:
            return jsonify({
                'success': False,
                'message': 'product_mapping é obrigatório'
            }), 400

        product_mapping = data['product_mapping']
        inventory_results = connector_manager.sync_inventory_all(product_mapping)

        return jsonify({
            'success': True,
            'inventory': inventory_results
        })
    except Exception as e:
        logger.error(f"Erro ao sincronizar estoque: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/tracking/<supplier_name>/<tracking_number>', methods=['GET'])
def get_tracking_info(supplier_name, tracking_number):
    """Obtém informações de rastreamento de um fornecedor específico."""
    try:
        tracking_info = connector_manager.get_tracking_info_from_supplier(
            supplier_name, tracking_number
        )

        if not tracking_info:
            return jsonify({
                'success': False,
                'message': f'Informações de rastreamento não encontradas para {tracking_number}'
            }), 404

        return jsonify({
            'success': True,
            'tracking': {
                'tracking_number': tracking_info.tracking_number,
                'status': tracking_info.status.value,
                'events': tracking_info.events,
                'estimated_delivery': tracking_info.estimated_delivery,
                'last_updated': tracking_info.last_updated
            }
        })
    except Exception as e:
        logger.error(f"Erro ao obter rastreamento {tracking_number}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@connectors_bp.route('/products/find-best', methods=['POST'])
def find_best_supplier():
    """Encontra o melhor fornecedor para um produto baseado em critérios."""
    try:
        data = request.get_json()
        
        if 'query' not in data:
            return jsonify({
                'success': False,
                'message': 'Query é obrigatória'
            }), 400

        query = data['query']
        criteria = data.get('criteria', {'priority': 'price'})

        best_option = connector_manager.find_best_supplier_for_product(query, criteria)

        if not best_option:
            return jsonify({
                'success': False,
                'message': 'Nenhum produto encontrado'
            }), 404

        product = best_option['product']
        return jsonify({
            'success': True,
            'best_option': {
                'supplier': best_option['supplier'],
                'score': best_option['score'],
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
                    'supplier_id': product.supplier_id,
                    'supplier_product_id': product.supplier_product_id,
                    'shipping_info': product.shipping_info,
                    'last_updated': product.last_updated
                }
            }
        })
    except Exception as e:
        logger.error(f"Erro ao encontrar melhor fornecedor: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

