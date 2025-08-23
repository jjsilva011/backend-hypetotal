"""
Serviço de rastreamento e logística para dropshipping
"""

import requests
from datetime import datetime, timedelta
from src.models.user import db
from src.models.product import Order
from src.models.supplier import DropshippingOrder, Supplier
import logging
import json
import re

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrackingService:
    """Serviço para rastreamento de pedidos e logística"""
    
    # Mapeamento de transportadoras e seus padrões de código
    CARRIER_PATTERNS = {
        'correios': r'^[A-Z]{2}\d{9}[A-Z]{2}$',
        'jadlog': r'^\d{14}$',
        'total_express': r'^TE\d{10}$',
        'loggi': r'^LG\d{8}$',
        'mercado_envios': r'^ME\d{12}$',
        'ups': r'^1Z[A-Z0-9]{16}$',
        'fedex': r'^\d{12,14}$',
        'dhl': r'^\d{10,11}$'
    }
    
    @staticmethod
    def track_order(order_id):
        """
        Rastrear um pedido específico
        
        Args:
            order_id: ID do pedido a ser rastreado
            
        Returns:
            Informações de rastreamento consolidadas
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                raise Exception(f"Pedido {order_id} não encontrado")
            
            logger.info(f"Iniciando rastreamento do pedido {order_id}")
            
            # Buscar todos os dropshipping orders relacionados
            dropshipping_orders = DropshippingOrder.query.filter_by(order_id=order_id).all()
            
            if not dropshipping_orders:
                return {
                    'order_id': order_id,
                    'is_dropshipping': False,
                    'status': order.status,
                    'message': 'Pedido não é de dropshipping ou não foi roteado'
                }
            
            # Rastrear cada dropshipping order
            tracking_results = []
            overall_status = 'pending'
            
            for ds_order in dropshipping_orders:
                tracking_info = TrackingService._track_dropshipping_order(ds_order)
                tracking_results.append(tracking_info)
                
                # Determinar status geral
                if tracking_info['status'] == 'delivered':
                    if overall_status != 'shipped':
                        overall_status = 'delivered'
                elif tracking_info['status'] == 'shipped':
                    overall_status = 'shipped'
                elif tracking_info['status'] == 'confirmed' and overall_status == 'pending':
                    overall_status = 'confirmed'
            
            # Consolidar informações
            consolidated_tracking = TrackingService._consolidate_tracking_info(order, tracking_results, overall_status)
            
            # Atualizar status do pedido se necessário
            if order.status != overall_status:
                order.status = overall_status
                if overall_status == 'delivered':
                    order.delivered_at = datetime.utcnow()
                db.session.commit()
            
            logger.info(f"Rastreamento do pedido {order_id} concluído")
            
            return consolidated_tracking
            
        except Exception as e:
            logger.error(f"Erro no rastreamento do pedido {order_id}: {str(e)}")
            raise e
    
    @staticmethod
    def _track_dropshipping_order(ds_order):
        """Rastrear um dropshipping order específico"""
        try:
            supplier = ds_order.supplier
            tracking_number = ds_order.tracking_number
            
            tracking_info = {
                'dropshipping_order_id': ds_order.id,
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'supplier_order_id': ds_order.supplier_order_id,
                'tracking_number': tracking_number,
                'status': ds_order.supplier_status,
                'events': [],
                'estimated_delivery': None,
                'carrier': None,
                'last_update': ds_order.updated_at.isoformat() if ds_order.updated_at else None
            }
            
            if tracking_number:
                # Identificar transportadora
                carrier = TrackingService._identify_carrier(tracking_number)
                tracking_info['carrier'] = carrier
                
                # Buscar informações de rastreamento
                if supplier.tracking_api_endpoint:
                    # Usar API do fornecedor
                    api_tracking = TrackingService._track_via_supplier_api(supplier, tracking_number)
                    tracking_info.update(api_tracking)
                else:
                    # Simular rastreamento
                    simulated_tracking = TrackingService._simulate_tracking(ds_order, carrier)
                    tracking_info.update(simulated_tracking)
            else:
                # Sem código de rastreamento ainda
                tracking_info['events'] = [
                    {
                        'date': ds_order.sent_to_supplier_at.isoformat() if ds_order.sent_to_supplier_at else None,
                        'status': 'Pedido enviado ao fornecedor',
                        'location': 'Sistema',
                        'description': f'Pedido {ds_order.supplier_order_id} enviado para {supplier.name}'
                    }
                ]
            
            return tracking_info
            
        except Exception as e:
            logger.error(f"Erro ao rastrear dropshipping order {ds_order.id}: {str(e)}")
            return {
                'dropshipping_order_id': ds_order.id,
                'error': str(e),
                'status': 'error'
            }
    
    @staticmethod
    def _identify_carrier(tracking_number):
        """Identificar transportadora baseado no padrão do código de rastreamento"""
        for carrier, pattern in TrackingService.CARRIER_PATTERNS.items():
            if re.match(pattern, tracking_number):
                return carrier
        return 'unknown'
    
    @staticmethod
    def _track_via_supplier_api(supplier, tracking_number):
        """Rastrear via API do fornecedor"""
        try:
            headers = {
                'Authorization': f'Bearer {supplier.api_key}',
                'Content-Type': 'application/json'
            }
            
            if supplier.api_secret:
                headers['X-API-Secret'] = supplier.api_secret
            
            # Fazer requisição para API de rastreamento
            response = requests.get(
                f"{supplier.tracking_api_endpoint}/{tracking_number}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return TrackingService._parse_supplier_tracking_response(data)
            else:
                logger.warning(f"API de rastreamento retornou status {response.status_code}")
                return TrackingService._simulate_tracking_fallback(tracking_number)
                
        except requests.RequestException as e:
            logger.error(f"Erro na API de rastreamento: {str(e)}")
            return TrackingService._simulate_tracking_fallback(tracking_number)
    
    @staticmethod
    def _parse_supplier_tracking_response(data):
        """Parsear resposta da API de rastreamento do fornecedor"""
        # Formato padrão esperado da API
        return {
            'status': data.get('status', 'unknown'),
            'events': data.get('events', []),
            'estimated_delivery': data.get('estimated_delivery'),
            'carrier': data.get('carrier'),
            'last_update': data.get('last_update')
        }
    
    @staticmethod
    def _simulate_tracking(ds_order, carrier):
        """Simular rastreamento para demonstração"""
        import random
        
        # Simular eventos baseados no status atual
        events = []
        current_status = ds_order.supplier_status
        
        # Evento inicial
        if ds_order.sent_to_supplier_at:
            events.append({
                'date': ds_order.sent_to_supplier_at.isoformat(),
                'status': 'Pedido recebido',
                'location': 'Centro de Distribuição',
                'description': 'Pedido recebido pelo fornecedor'
            })
        
        # Evento de confirmação
        if ds_order.confirmed_by_supplier_at:
            events.append({
                'date': ds_order.confirmed_by_supplier_at.isoformat(),
                'status': 'Pedido confirmado',
                'location': 'Centro de Distribuição',
                'description': 'Pedido confirmado e em preparação'
            })
        
        # Evento de envio
        if ds_order.shipped_by_supplier_at:
            events.append({
                'date': ds_order.shipped_by_supplier_at.isoformat(),
                'status': 'Objeto postado',
                'location': 'Agência de Origem',
                'description': f'Objeto postado pela transportadora {carrier.title()}'
            })
            
            # Simular eventos intermediários se enviado
            ship_date = ds_order.shipped_by_supplier_at
            
            # Evento de trânsito (1 dia após envio)
            transit_date = ship_date + timedelta(days=1)
            if transit_date <= datetime.utcnow():
                events.append({
                    'date': transit_date.isoformat(),
                    'status': 'Objeto em trânsito',
                    'location': 'Centro de Triagem',
                    'description': 'Objeto em trânsito para cidade de destino'
                })
            
            # Evento de chegada ao destino (2-3 dias após envio)
            arrival_days = random.randint(2, 3)
            arrival_date = ship_date + timedelta(days=arrival_days)
            if arrival_date <= datetime.utcnow():
                events.append({
                    'date': arrival_date.isoformat(),
                    'status': 'Objeto chegou ao destino',
                    'location': 'Centro de Distribuição Local',
                    'description': 'Objeto chegou à cidade de destino'
                })
        
        # Evento de entrega
        if ds_order.delivered_by_supplier_at:
            events.append({
                'date': ds_order.delivered_by_supplier_at.isoformat(),
                'status': 'Objeto entregue',
                'location': 'Endereço de Destino',
                'description': 'Objeto entregue ao destinatário'
            })
        
        # Calcular entrega estimada
        estimated_delivery = None
        if ds_order.shipped_by_supplier_at and not ds_order.delivered_by_supplier_at:
            supplier = ds_order.supplier
            delivery_days = random.randint(supplier.shipping_time_min_days, supplier.shipping_time_max_days)
            estimated_delivery = (ds_order.shipped_by_supplier_at + timedelta(days=delivery_days)).isoformat()
        
        return {
            'events': events,
            'estimated_delivery': estimated_delivery,
            'last_update': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _simulate_tracking_fallback(tracking_number):
        """Fallback para simulação quando API falha"""
        return {
            'status': 'shipped',
            'events': [
                {
                    'date': datetime.utcnow().isoformat(),
                    'status': 'Informações de rastreamento indisponíveis',
                    'location': 'Sistema',
                    'description': f'Código de rastreamento: {tracking_number}'
                }
            ],
            'estimated_delivery': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'last_update': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _consolidate_tracking_info(order, tracking_results, overall_status):
        """Consolidar informações de rastreamento de múltiplos fornecedores"""
        
        # Combinar todos os eventos
        all_events = []
        for tracking in tracking_results:
            if 'events' in tracking:
                for event in tracking['events']:
                    event['supplier_name'] = tracking.get('supplier_name', 'Desconhecido')
                    all_events.append(event)
        
        # Ordenar eventos por data
        all_events.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Calcular entrega estimada mais distante
        estimated_deliveries = [
            t.get('estimated_delivery') for t in tracking_results 
            if t.get('estimated_delivery')
        ]
        
        latest_delivery = None
        if estimated_deliveries:
            latest_delivery = max(estimated_deliveries)
        
        # Contar fornecedores por status
        status_summary = {}
        for tracking in tracking_results:
            status = tracking.get('status', 'unknown')
            if status not in status_summary:
                status_summary[status] = 0
            status_summary[status] += 1
        
        return {
            'order_id': order.id,
            'is_dropshipping': True,
            'overall_status': overall_status,
            'total_suppliers': len(tracking_results),
            'status_summary': status_summary,
            'estimated_delivery': latest_delivery,
            'tracking_details': tracking_results,
            'consolidated_events': all_events[:20],  # Últimos 20 eventos
            'last_update': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def bulk_track_orders(order_ids):
        """Rastrear múltiplos pedidos em lote"""
        try:
            results = []
            errors = []
            
            for order_id in order_ids:
                try:
                    tracking_info = TrackingService.track_order(order_id)
                    results.append(tracking_info)
                except Exception as e:
                    errors.append({
                        'order_id': order_id,
                        'error': str(e)
                    })
            
            return {
                'total_processed': len(order_ids),
                'successful': len(results),
                'failed': len(errors),
                'results': results,
                'errors': errors,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro no rastreamento em lote: {str(e)}")
            raise e
    
    @staticmethod
    def get_tracking_analytics():
        """Obter analytics de rastreamento"""
        try:
            # Estatísticas gerais
            total_orders = DropshippingOrder.query.count()
            
            # Distribuição por status
            status_distribution = db.session.query(
                DropshippingOrder.supplier_status,
                db.func.count(DropshippingOrder.id).label('count')
            ).group_by(DropshippingOrder.supplier_status).all()
            
            # Tempo médio de entrega (últimos 30 dias)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            avg_delivery_time = db.session.query(
                db.func.avg(
                    db.func.julianday(DropshippingOrder.delivered_by_supplier_at) - 
                    db.func.julianday(DropshippingOrder.shipped_by_supplier_at)
                ).label('avg_days')
            ).filter(
                DropshippingOrder.delivered_by_supplier_at.isnot(None),
                DropshippingOrder.shipped_by_supplier_at.isnot(None),
                DropshippingOrder.created_at >= thirty_days_ago
            ).scalar()
            
            # Pedidos com atraso (estimativa ultrapassada)
            delayed_orders = db.session.query(DropshippingOrder).filter(
                DropshippingOrder.supplier_status.in_(['shipped', 'confirmed']),
                DropshippingOrder.shipped_by_supplier_at.isnot(None)
            ).all()
            
            delayed_count = 0
            for order in delayed_orders:
                if order.shipped_by_supplier_at:
                    supplier = order.supplier
                    expected_delivery = order.shipped_by_supplier_at + timedelta(days=supplier.shipping_time_max_days)
                    if expected_delivery < datetime.utcnow():
                        delayed_count += 1
            
            # Transportadoras mais utilizadas
            tracking_numbers = db.session.query(DropshippingOrder.tracking_number).filter(
                DropshippingOrder.tracking_number.isnot(None)
            ).all()
            
            carrier_stats = {}
            for (tracking_number,) in tracking_numbers:
                carrier = TrackingService._identify_carrier(tracking_number)
                if carrier not in carrier_stats:
                    carrier_stats[carrier] = 0
                carrier_stats[carrier] += 1
            
            return {
                'total_orders': total_orders,
                'status_distribution': [
                    {'status': status, 'count': count} for status, count in status_distribution
                ],
                'avg_delivery_time_days': round(avg_delivery_time or 0, 2),
                'delayed_orders': delayed_count,
                'carrier_distribution': carrier_stats,
                'tracking_coverage': {
                    'with_tracking': len(tracking_numbers),
                    'without_tracking': total_orders - len(tracking_numbers),
                    'coverage_percentage': round((len(tracking_numbers) / total_orders * 100) if total_orders > 0 else 0, 2)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter analytics de rastreamento: {str(e)}")
            raise e
    
    @staticmethod
    def update_tracking_number(ds_order_id, tracking_number, carrier=None):
        """Atualizar código de rastreamento de um dropshipping order"""
        try:
            ds_order = DropshippingOrder.query.get(ds_order_id)
            if not ds_order:
                raise Exception(f"Dropshipping order {ds_order_id} não encontrado")
            
            # Validar formato do código de rastreamento
            if carrier:
                pattern = TrackingService.CARRIER_PATTERNS.get(carrier.lower())
                if pattern and not re.match(pattern, tracking_number):
                    logger.warning(f"Código de rastreamento {tracking_number} não corresponde ao padrão da transportadora {carrier}")
            
            # Identificar transportadora automaticamente se não fornecida
            if not carrier:
                carrier = TrackingService._identify_carrier(tracking_number)
            
            # Atualizar informações
            ds_order.tracking_number = tracking_number
            ds_order.carrier = carrier
            ds_order.updated_at = datetime.utcnow()
            
            # Atualizar status se ainda estiver pendente
            if ds_order.supplier_status in ['pending', 'confirmed']:
                ds_order.supplier_status = 'shipped'
                ds_order.shipped_by_supplier_at = datetime.utcnow()
            
            # Atualizar pedido principal
            order = ds_order.order
            if order.tracking_number is None:
                order.tracking_number = tracking_number
            
            db.session.commit()
            
            logger.info(f"Código de rastreamento {tracking_number} adicionado ao dropshipping order {ds_order_id}")
            
            return {
                'dropshipping_order_id': ds_order_id,
                'tracking_number': tracking_number,
                'carrier': carrier,
                'status': ds_order.supplier_status,
                'updated_at': ds_order.updated_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar código de rastreamento: {str(e)}")
            raise e
    
    @staticmethod
    def get_delivery_performance():
        """Obter métricas de performance de entrega"""
        try:
            # Últimos 30 dias
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Pedidos entregues no prazo vs atrasados
            delivered_orders = DropshippingOrder.query.filter(
                DropshippingOrder.supplier_status == 'delivered',
                DropshippingOrder.delivered_by_supplier_at >= thirty_days_ago
            ).all()
            
            on_time = 0
            delayed = 0
            
            for order in delivered_orders:
                if order.shipped_by_supplier_at and order.delivered_by_supplier_at:
                    supplier = order.supplier
                    expected_delivery = order.shipped_by_supplier_at + timedelta(days=supplier.shipping_time_max_days)
                    
                    if order.delivered_by_supplier_at <= expected_delivery:
                        on_time += 1
                    else:
                        delayed += 1
            
            # Performance por fornecedor
            supplier_performance = db.session.query(
                Supplier.id,
                Supplier.name,
                db.func.count(DropshippingOrder.id).label('total_orders'),
                db.func.sum(
                    db.case(
                        (DropshippingOrder.supplier_status == 'delivered', 1),
                        else_=0
                    )
                ).label('delivered_orders')
            ).join(
                DropshippingOrder, Supplier.id == DropshippingOrder.supplier_id
            ).filter(
                DropshippingOrder.created_at >= thirty_days_ago
            ).group_by(
                Supplier.id, Supplier.name
            ).all()
            
            supplier_stats = []
            for supplier in supplier_performance:
                delivery_rate = (supplier.delivered_orders / supplier.total_orders * 100) if supplier.total_orders > 0 else 0
                supplier_stats.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'total_orders': supplier.total_orders,
                    'delivered_orders': supplier.delivered_orders,
                    'delivery_rate_percentage': round(delivery_rate, 2)
                })
            
            # Ordenar por taxa de entrega
            supplier_stats.sort(key=lambda x: x['delivery_rate_percentage'], reverse=True)
            
            return {
                'period': '30 days',
                'delivery_performance': {
                    'on_time_deliveries': on_time,
                    'delayed_deliveries': delayed,
                    'total_deliveries': on_time + delayed,
                    'on_time_percentage': round((on_time / (on_time + delayed) * 100) if (on_time + delayed) > 0 else 0, 2)
                },
                'supplier_performance': supplier_stats,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter performance de entrega: {str(e)}")
            raise e

