"""
Rotas de e-commerce integradas com sistema de dropshipping.
Gerencia produtos, pedidos, carrinho e integração com fornecedores.
"""

from flask import Blueprint, request, jsonify
from src.models.connector_manager import connector_manager
from src.models.connector_base import Order, OrderItem, Address
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

ecommerce_bp = Blueprint('ecommerce', __name__)


@ecommerce_bp.route('/products/catalog', methods=['GET'])
def get_product_catalog():
    """Obtém catálogo unificado de produtos de todos os fornecedores."""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        category = request.args.get('category')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        
        # Busca em todos os conectores ativos
        all_products = []
        active_connectors = connector_manager.get_all_connectors()
        
        for connector_name, connector in active_connectors.items():
            try:
                # Busca produtos sem query específica para catálogo geral
                products = connector.search_products(
                    query="",
                    page=1,
                    page_size=per_page,
                    category=category,
                    min_price=min_price,
                    max_price=max_price
                )
                
                for product in products:
                    all_products.append({
                        'id': f"{connector_name}_{product.id}",
                        'supplier_id': connector_name,
                        'supplier_product_id': product.id,
                        'name': product.name,
                        'description': product.description,
                        'price': product.price,
                        'currency': product.currency,
                        'stock': product.stock_quantity,
                        'images': product.images,
                        'category': product.category,
                        'variations': product.variations,
                        'shipping_info': product.shipping_info,
                        'last_updated': product.last_updated
                    })
                    
            except Exception as e:
                logger.error(f"Erro ao buscar produtos do {connector_name}: {e}")
                continue
        
        # Paginação
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_products = all_products[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'products': paginated_products,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': len(all_products),
                'pages': (len(all_products) + per_page - 1) // per_page
            },
            'suppliers_count': len(active_connectors)
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter catálogo de produtos: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ecommerce_bp.route('/products/<supplier_id>/<product_id>', methods=['GET'])
def get_product_details(supplier_id, product_id):
    """Obtém detalhes completos de um produto específico."""
    try:
        connector = connector_manager.get_connector(supplier_id)
        if not connector:
            return jsonify({
                'success': False,
                'message': f'Fornecedor {supplier_id} não encontrado'
            }), 404
        
        product = connector.get_product_details(product_id)
        if not product:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'product': {
                'id': f"{supplier_id}_{product.id}",
                'supplier_id': supplier_id,
                'supplier_product_id': product.id,
                'name': product.name,
                'description': product.description,
                'price': product.price,
                'currency': product.currency,
                'stock': product.stock_quantity,
                'images': product.images,
                'category': product.category,
                'variations': product.variations,
                'shipping_info': product.shipping_info,
                'last_updated': product.last_updated
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do produto: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ecommerce_bp.route('/orders/create', methods=['POST'])
def create_order():
    """Cria um novo pedido e roteia para o fornecedor apropriado."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['items', 'shipping_address', 'total_amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400
        
        # Constrói endereço de entrega
        addr_data = data['shipping_address']
        shipping_address = Address(
            full_name=addr_data.get('full_name', ''),
            address_line1=addr_data.get('address_line1', ''),
            address_line2=addr_data.get('address_line2'),
            city=addr_data.get('city', ''),
            state=addr_data.get('state', ''),
            postal_code=addr_data.get('postal_code', ''),
            country=addr_data.get('country', 'BR'),
            phone=addr_data.get('phone', ''),
            email=addr_data.get('email', '')
        )
        
        # Agrupa itens por fornecedor
        items_by_supplier = {}
        for item_data in data['items']:
            supplier_id = item_data.get('supplier_id')
            if not supplier_id:
                return jsonify({
                    'success': False,
                    'message': 'supplier_id é obrigatório para cada item'
                }), 400
            
            if supplier_id not in items_by_supplier:
                items_by_supplier[supplier_id] = []
            
            item = OrderItem(
                product_id=item_data.get('product_id', ''),
                supplier_product_id=item_data.get('supplier_product_id', ''),
                quantity=item_data.get('quantity', 1),
                price=item_data.get('price', 0),
                variation_id=item_data.get('variation_id'),
                variation_attributes=item_data.get('variation_attributes', {})
            )
            items_by_supplier[supplier_id].append(item)
        
        # Cria pedidos separados para cada fornecedor
        order_responses = []
        main_order_id = f"HT_{int(time.time())}"
        
        for supplier_id, items in items_by_supplier.items():
            connector = connector_manager.get_connector(supplier_id)
            if not connector:
                order_responses.append({
                    'supplier_id': supplier_id,
                    'success': False,
                    'message': f'Fornecedor {supplier_id} não disponível'
                })
                continue
            
            # Calcula total para este fornecedor
            supplier_total = sum(item.price * item.quantity for item in items)
            
            # Cria pedido para este fornecedor
            order = Order(
                id=f"{main_order_id}_{supplier_id}",
                items=items,
                shipping_address=shipping_address,
                total_amount=supplier_total,
                currency=data.get('currency', 'USD'),
                shipping_method=data.get('shipping_method', 'standard'),
                notes=data.get('notes', f'Pedido Hype Total™ - {main_order_id}')
            )
            
            response = connector.create_order(order)
            order_responses.append({
                'supplier_id': supplier_id,
                'success': response.success,
                'order_id': response.order_id,
                'supplier_order_id': response.supplier_order_id,
                'tracking_number': response.tracking_number,
                'estimated_delivery': response.estimated_delivery,
                'message': response.message,
                'error_code': response.error_code
            })
        
        # Verifica se pelo menos um pedido foi criado com sucesso
        successful_orders = [r for r in order_responses if r['success']]
        
        return jsonify({
            'success': len(successful_orders) > 0,
            'main_order_id': main_order_id,
            'supplier_orders': order_responses,
            'successful_orders': len(successful_orders),
            'total_orders': len(order_responses),
            'message': f'{len(successful_orders)} de {len(order_responses)} pedidos criados com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ecommerce_bp.route('/orders/<order_id>/tracking', methods=['GET'])
def get_order_tracking(order_id):
    """Obtém informações de rastreamento de um pedido."""
    try:
        # Se o order_id contém supplier, extrai as informações
        if '_' in order_id:
            parts = order_id.split('_')
            if len(parts) >= 3:
                supplier_id = parts[-1]
                connector = connector_manager.get_connector(supplier_id)
                
                if connector:
                    tracking_info = connector.get_tracking_info(order_id)
                    if tracking_info:
                        return jsonify({
                            'success': True,
                            'tracking': {
                                'order_id': order_id,
                                'supplier_id': supplier_id,
                                'tracking_number': tracking_info.tracking_number,
                                'status': tracking_info.status.value,
                                'events': tracking_info.events,
                                'estimated_delivery': tracking_info.estimated_delivery,
                                'last_updated': tracking_info.last_updated
                            }
                        })
        
        return jsonify({
            'success': False,
            'message': 'Informações de rastreamento não encontradas'
        }), 404
        
    except Exception as e:
        logger.error(f"Erro ao obter rastreamento: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ecommerce_bp.route('/shipping/calculate', methods=['POST'])
def calculate_shipping():
    """Calcula opções de frete para itens do carrinho."""
    try:
        data = request.get_json()
        
        # Validação
        if 'items' not in data or 'destination' not in data:
            return jsonify({
                'success': False,
                'message': 'items e destination são obrigatórios'
            }), 400
        
        # Constrói endereço de destino
        dest_data = data['destination']
        destination = Address(
            full_name='',
            address_line1='',
            address_line2=None,
            city=dest_data.get('city', ''),
            state=dest_data.get('state', ''),
            postal_code=dest_data.get('postal_code', ''),
            country=dest_data.get('country', 'BR'),
            phone='',
            email=''
        )
        
        # Agrupa itens por fornecedor
        items_by_supplier = {}
        for item_data in data['items']:
            supplier_id = item_data.get('supplier_id')
            if not supplier_id:
                continue
            
            if supplier_id not in items_by_supplier:
                items_by_supplier[supplier_id] = []
            
            item = OrderItem(
                product_id=item_data.get('product_id', ''),
                supplier_product_id=item_data.get('supplier_product_id', ''),
                quantity=item_data.get('quantity', 1),
                price=item_data.get('price', 0),
                variation_id=item_data.get('variation_id'),
                variation_attributes=item_data.get('variation_attributes', {})
            )
            items_by_supplier[supplier_id].append(item)
        
        # Calcula frete para cada fornecedor
        shipping_options = {}
        total_shipping_cost = 0
        
        for supplier_id, items in items_by_supplier.items():
            connector = connector_manager.get_connector(supplier_id)
            if not connector:
                continue
            
            shipping_calc = connector.calculate_shipping(items, destination)
            if 'options' in shipping_calc:
                shipping_options[supplier_id] = shipping_calc['options']
                
                # Soma o custo do frete mais barato de cada fornecedor
                if shipping_calc['options']:
                    min_cost = min(opt.get('cost', 0) for opt in shipping_calc['options'])
                    total_shipping_cost += min_cost
        
        return jsonify({
            'success': True,
            'shipping_by_supplier': shipping_options,
            'estimated_total_shipping': total_shipping_cost,
            'currency': 'USD',
            'calculated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao calcular frete: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ecommerce_bp.route('/inventory/sync', methods=['POST'])
def sync_inventory():
    """Sincroniza estoque de produtos específicos."""
    try:
        data = request.get_json()
        
        if 'products' not in data:
            return jsonify({
                'success': False,
                'message': 'Lista de produtos é obrigatória'
            }), 400
        
        # Agrupa produtos por fornecedor
        products_by_supplier = {}
        for product in data['products']:
            supplier_id = product.get('supplier_id')
            product_id = product.get('product_id')
            
            if supplier_id and product_id:
                if supplier_id not in products_by_supplier:
                    products_by_supplier[supplier_id] = []
                products_by_supplier[supplier_id].append(product_id)
        
        # Sincroniza estoque para cada fornecedor
        inventory_results = {}
        
        for supplier_id, product_ids in products_by_supplier.items():
            connector = connector_manager.get_connector(supplier_id)
            if connector:
                inventory = connector.sync_inventory(product_ids)
                inventory_results[supplier_id] = inventory
        
        return jsonify({
            'success': True,
            'inventory_by_supplier': inventory_results,
            'synced_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar estoque: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ecommerce_bp.route('/suppliers/status', methods=['GET'])
def get_suppliers_status():
    """Obtém status de todos os fornecedores conectados."""
    try:
        connectors = connector_manager.get_all_connectors()
        suppliers_status = {}
        
        for supplier_id, connector in connectors.items():
            try:
                is_healthy = connector.test_connection()
                suppliers_status[supplier_id] = {
                    'name': connector.config.name,
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'base_url': connector.config.base_url,
                    'last_checked': datetime.now().isoformat()
                }
            except Exception as e:
                suppliers_status[supplier_id] = {
                    'name': connector.config.name,
                    'status': 'error',
                    'error': str(e),
                    'last_checked': datetime.now().isoformat()
                }
        
        return jsonify({
            'success': True,
            'suppliers': suppliers_status,
            'total_suppliers': len(suppliers_status),
            'healthy_suppliers': len([s for s in suppliers_status.values() if s['status'] == 'healthy'])
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status dos fornecedores: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

