"""
Serviço de roteamento inteligente de pedidos para dropshipping
"""

from datetime import datetime, timedelta
from src.models.user import db
from src.models.product import Product, Order, OrderItem
from src.models.supplier import Supplier, SupplierProduct, DropshippingOrder
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderRoutingService:
    """Serviço para roteamento inteligente de pedidos"""
    
    @staticmethod
    def route_order(order_id):
        """
        Rotear um pedido para os fornecedores apropriados
        
        Args:
            order_id: ID do pedido a ser roteado
            
        Returns:
            Resultado do roteamento com detalhes dos fornecedores
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                raise Exception(f"Pedido {order_id} não encontrado")
            
            logger.info(f"Iniciando roteamento do pedido {order_id}")
            
            # Analisar itens do pedido
            routing_result = OrderRoutingService._analyze_order_items(order)
            
            # Aplicar estratégias de roteamento
            routing_strategy = OrderRoutingService._determine_routing_strategy(order, routing_result)
            
            # Executar roteamento baseado na estratégia
            final_routing = OrderRoutingService._execute_routing_strategy(order, routing_result, routing_strategy)
            
            # Criar registros de dropshipping
            dropshipping_orders = OrderRoutingService._create_dropshipping_orders(order, final_routing)
            
            # Atualizar status do pedido
            order.is_dropshipping_order = True
            order.status = 'processing'
            
            db.session.commit()
            
            logger.info(f"Roteamento do pedido {order_id} concluído com sucesso")
            
            return {
                'order_id': order_id,
                'routing_strategy': routing_strategy,
                'supplier_orders': final_routing,
                'dropshipping_orders': [ds.id for ds in dropshipping_orders],
                'total_suppliers': len(final_routing),
                'routed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro no roteamento do pedido {order_id}: {str(e)}")
            raise e
    
    @staticmethod
    def _analyze_order_items(order):
        """Analisar itens do pedido para roteamento"""
        analysis = {
            'total_items': len(order.items),
            'dropshipping_items': [],
            'regular_items': [],
            'suppliers_involved': {},
            'total_value': 0,
            'total_weight': 0,
            'requires_special_handling': False
        }
        
        for item in order.items:
            product = item.product
            analysis['total_value'] += item.price * item.quantity
            
            if product.is_dropshipping and product.supplier_id:
                # Item de dropshipping
                supplier_id = product.supplier_id
                
                if supplier_id not in analysis['suppliers_involved']:
                    analysis['suppliers_involved'][supplier_id] = {
                        'supplier': product.supplier,
                        'items': [],
                        'total_value': 0,
                        'total_quantity': 0,
                        'estimated_shipping_days': 0
                    }
                
                analysis['suppliers_involved'][supplier_id]['items'].append({
                    'order_item': item,
                    'product': product,
                    'quantity': item.quantity,
                    'unit_price': item.price,
                    'total_price': item.price * item.quantity
                })
                
                analysis['suppliers_involved'][supplier_id]['total_value'] += item.price * item.quantity
                analysis['suppliers_involved'][supplier_id]['total_quantity'] += item.quantity
                
                # Calcular peso estimado (se disponível)
                supplier_product = SupplierProduct.query.filter_by(
                    supplier_id=supplier_id,
                    supplier_sku=product.supplier_product_id
                ).first()
                
                if supplier_product and supplier_product.supplier_weight:
                    analysis['total_weight'] += supplier_product.supplier_weight * item.quantity
                
                analysis['dropshipping_items'].append(item)
            else:
                # Item regular (estoque próprio)
                analysis['regular_items'].append(item)
        
        # Calcular estimativas de envio por fornecedor
        for supplier_id, supplier_data in analysis['suppliers_involved'].items():
            supplier = supplier_data['supplier']
            avg_shipping_days = (supplier.shipping_time_min_days + supplier.shipping_time_max_days) / 2
            supplier_data['estimated_shipping_days'] = avg_shipping_days
        
        return analysis
    
    @staticmethod
    def _determine_routing_strategy(order, analysis):
        """Determinar estratégia de roteamento baseada na análise do pedido"""
        
        # Estratégias disponíveis:
        # 1. SINGLE_SUPPLIER - Tentar usar um único fornecedor
        # 2. MULTI_SUPPLIER_COST - Múltiplos fornecedores priorizando custo
        # 3. MULTI_SUPPLIER_SPEED - Múltiplos fornecedores priorizando velocidade
        # 4. HYBRID - Estratégia híbrida baseada em regras
        
        num_suppliers = len(analysis['suppliers_involved'])
        total_value = analysis['total_value']
        
        if num_suppliers == 0:
            return 'NO_DROPSHIPPING'
        elif num_suppliers == 1:
            return 'SINGLE_SUPPLIER'
        elif total_value > 1000:  # Pedidos de alto valor
            return 'MULTI_SUPPLIER_SPEED'  # Priorizar velocidade
        elif total_value < 200:  # Pedidos de baixo valor
            return 'MULTI_SUPPLIER_COST'  # Priorizar custo
        else:
            return 'HYBRID'  # Estratégia balanceada
    
    @staticmethod
    def _execute_routing_strategy(order, analysis, strategy):
        """Executar estratégia de roteamento"""
        
        if strategy == 'NO_DROPSHIPPING':
            return []
        
        elif strategy == 'SINGLE_SUPPLIER':
            # Usar o único fornecedor disponível
            supplier_id = list(analysis['suppliers_involved'].keys())[0]
            return [analysis['suppliers_involved'][supplier_id]]
        
        elif strategy == 'MULTI_SUPPLIER_COST':
            # Priorizar fornecedores com menor custo de envio
            return OrderRoutingService._route_by_cost(analysis)
        
        elif strategy == 'MULTI_SUPPLIER_SPEED':
            # Priorizar fornecedores com menor tempo de entrega
            return OrderRoutingService._route_by_speed(analysis)
        
        elif strategy == 'HYBRID':
            # Estratégia balanceada considerando custo e velocidade
            return OrderRoutingService._route_hybrid(analysis)
        
        else:
            # Fallback para múltiplos fornecedores
            return list(analysis['suppliers_involved'].values())
    
    @staticmethod
    def _route_by_cost(analysis):
        """Roteamento priorizando custo"""
        suppliers = list(analysis['suppliers_involved'].values())
        
        # Ordenar por custo de envio (menor primeiro)
        suppliers.sort(key=lambda s: s['supplier'].shipping_cost)
        
        return suppliers
    
    @staticmethod
    def _route_by_speed(analysis):
        """Roteamento priorizando velocidade"""
        suppliers = list(analysis['suppliers_involved'].values())
        
        # Ordenar por tempo de envio (menor primeiro)
        suppliers.sort(key=lambda s: s['estimated_shipping_days'])
        
        return suppliers
    
    @staticmethod
    def _route_hybrid(analysis):
        """Roteamento híbrido balanceando custo e velocidade"""
        suppliers = list(analysis['suppliers_involved'].values())
        
        # Calcular score híbrido (menor é melhor)
        for supplier_data in suppliers:
            supplier = supplier_data['supplier']
            
            # Normalizar custo de envio (0-1)
            max_cost = max(s['supplier'].shipping_cost for s in suppliers)
            cost_score = supplier.shipping_cost / max_cost if max_cost > 0 else 0
            
            # Normalizar tempo de envio (0-1)
            max_time = max(s['estimated_shipping_days'] for s in suppliers)
            time_score = supplier_data['estimated_shipping_days'] / max_time if max_time > 0 else 0
            
            # Score híbrido (peso 60% custo, 40% tempo)
            supplier_data['hybrid_score'] = (cost_score * 0.6) + (time_score * 0.4)
        
        # Ordenar por score híbrido (menor primeiro)
        suppliers.sort(key=lambda s: s.get('hybrid_score', 1))
        
        return suppliers
    
    @staticmethod
    def _create_dropshipping_orders(order, routing_result):
        """Criar registros de dropshipping orders"""
        dropshipping_orders = []
        
        for supplier_data in routing_result:
            supplier = supplier_data['supplier']
            items = supplier_data['items']
            
            # Simular envio para fornecedor
            supplier_order_result = OrderRoutingService._simulate_supplier_order(order, supplier, items)
            
            # Criar registro de dropshipping order
            dropshipping_order = DropshippingOrder(
                order_id=order.id,
                supplier_id=supplier.id,
                supplier_order_id=supplier_order_result.get('supplier_order_id'),
                supplier_status='pending',
                sent_to_supplier_at=datetime.utcnow(),
                supplier_response=json.dumps(supplier_order_result),
                notes=f"Roteado automaticamente - {len(items)} itens"
            )
            
            db.session.add(dropshipping_order)
            dropshipping_orders.append(dropshipping_order)
        
        return dropshipping_orders
    
    @staticmethod
    def _simulate_supplier_order(order, supplier, items):
        """Simular envio de pedido para fornecedor"""
        import random
        import string
        
        # Gerar ID fictício do pedido no fornecedor
        supplier_order_id = f"{supplier.name[:3].upper()}-{''.join(random.choices(string.digits, k=8))}"
        
        # Calcular totais
        total_items = len(items)
        total_amount = sum(item['total_price'] for item in items)
        
        # Simular resposta do fornecedor
        return {
            'supplier_order_id': supplier_order_id,
            'status': 'accepted',
            'total_items': total_items,
            'total_amount': total_amount,
            'estimated_processing_days': random.randint(1, 3),
            'estimated_shipping_days': random.randint(supplier.shipping_time_min_days, supplier.shipping_time_max_days),
            'shipping_cost': supplier.shipping_cost,
            'message': f'Pedido aceito - {total_items} itens no valor de R$ {total_amount:.2f}',
            'created_at': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_routing_options(order_id):
        """Obter opções de roteamento para um pedido sem executar"""
        try:
            order = Order.query.get(order_id)
            if not order:
                raise Exception(f"Pedido {order_id} não encontrado")
            
            # Analisar itens do pedido
            analysis = OrderRoutingService._analyze_order_items(order)
            
            if not analysis['suppliers_involved']:
                return {
                    'order_id': order_id,
                    'has_dropshipping_items': False,
                    'message': 'Pedido não contém itens de dropshipping'
                }
            
            # Gerar opções para cada estratégia
            options = {}
            
            strategies = ['SINGLE_SUPPLIER', 'MULTI_SUPPLIER_COST', 'MULTI_SUPPLIER_SPEED', 'HYBRID']
            
            for strategy in strategies:
                if strategy == 'SINGLE_SUPPLIER' and len(analysis['suppliers_involved']) > 1:
                    continue  # Pular se há múltiplos fornecedores
                
                routing_result = OrderRoutingService._execute_routing_strategy(order, analysis, strategy)
                
                # Calcular estimativas para esta opção
                total_shipping_cost = sum(s['supplier'].shipping_cost for s in routing_result)
                avg_shipping_days = sum(s['estimated_shipping_days'] for s in routing_result) / len(routing_result)
                
                options[strategy] = {
                    'strategy_name': strategy,
                    'suppliers_count': len(routing_result),
                    'suppliers': [
                        {
                            'supplier_id': s['supplier'].id,
                            'supplier_name': s['supplier'].name,
                            'items_count': len(s['items']),
                            'total_value': s['total_value'],
                            'shipping_cost': s['supplier'].shipping_cost,
                            'estimated_days': s['estimated_shipping_days']
                        } for s in routing_result
                    ],
                    'total_shipping_cost': total_shipping_cost,
                    'estimated_delivery_days': avg_shipping_days,
                    'recommendation_score': OrderRoutingService._calculate_recommendation_score(strategy, routing_result, analysis)
                }
            
            # Ordenar opções por score de recomendação
            sorted_options = sorted(options.items(), key=lambda x: x[1]['recommendation_score'], reverse=True)
            
            return {
                'order_id': order_id,
                'has_dropshipping_items': True,
                'analysis': {
                    'total_items': analysis['total_items'],
                    'dropshipping_items': len(analysis['dropshipping_items']),
                    'suppliers_involved': len(analysis['suppliers_involved']),
                    'total_value': analysis['total_value']
                },
                'routing_options': dict(sorted_options),
                'recommended_strategy': sorted_options[0][0] if sorted_options else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter opções de roteamento: {str(e)}")
            raise e
    
    @staticmethod
    def _calculate_recommendation_score(strategy, routing_result, analysis):
        """Calcular score de recomendação para uma estratégia"""
        score = 50  # Score base
        
        # Bonificações baseadas na estratégia
        if strategy == 'SINGLE_SUPPLIER':
            score += 20  # Simplicidade
        elif strategy == 'MULTI_SUPPLIER_SPEED':
            score += 15  # Velocidade
        elif strategy == 'MULTI_SUPPLIER_COST':
            score += 10  # Economia
        elif strategy == 'HYBRID':
            score += 25  # Balanceamento
        
        # Penalizações
        if len(routing_result) > 3:
            score -= 10  # Muitos fornecedores
        
        # Bonificações baseadas no valor do pedido
        total_value = analysis['total_value']
        if total_value > 1000:
            if strategy in ['MULTI_SUPPLIER_SPEED', 'HYBRID']:
                score += 10
        elif total_value < 200:
            if strategy in ['MULTI_SUPPLIER_COST', 'SINGLE_SUPPLIER']:
                score += 10
        
        return max(0, min(100, score))  # Limitar entre 0 e 100
    
    @staticmethod
    def get_routing_analytics():
        """Obter analytics de roteamento"""
        try:
            # Estatísticas gerais
            total_dropshipping_orders = DropshippingOrder.query.count()
            
            # Pedidos por status
            status_stats = db.session.query(
                DropshippingOrder.supplier_status,
                db.func.count(DropshippingOrder.id).label('count')
            ).group_by(DropshippingOrder.supplier_status).all()
            
            # Fornecedores mais utilizados (últimos 30 dias)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            top_suppliers = db.session.query(
                Supplier.id,
                Supplier.name,
                db.func.count(DropshippingOrder.id).label('order_count')
            ).join(
                DropshippingOrder, Supplier.id == DropshippingOrder.supplier_id
            ).filter(
                DropshippingOrder.created_at >= thirty_days_ago
            ).group_by(
                Supplier.id, Supplier.name
            ).order_by(
                db.func.count(DropshippingOrder.id).desc()
            ).limit(10).all()
            
            # Tempo médio de processamento
            avg_processing_time = db.session.query(
                db.func.avg(
                    db.func.julianday(DropshippingOrder.confirmed_by_supplier_at) - 
                    db.func.julianday(DropshippingOrder.sent_to_supplier_at)
                ).label('avg_days')
            ).filter(
                DropshippingOrder.confirmed_by_supplier_at.isnot(None),
                DropshippingOrder.sent_to_supplier_at.isnot(None)
            ).scalar()
            
            return {
                'total_dropshipping_orders': total_dropshipping_orders,
                'status_distribution': [
                    {'status': status, 'count': count} for status, count in status_stats
                ],
                'top_suppliers': [
                    {
                        'supplier_id': supplier.id,
                        'supplier_name': supplier.name,
                        'order_count': supplier.order_count
                    } for supplier in top_suppliers
                ],
                'avg_processing_time_days': round(avg_processing_time or 0, 2),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter analytics de roteamento: {str(e)}")
            raise e

