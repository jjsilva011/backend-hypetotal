"""
Gerenciador de conectores de dropshipping.
Coordena múltiplos conectores e fornece uma interface unificada.
"""

from typing import Dict, List, Optional, Any
from src.models.connector_base import BaseConnector, Product, Order, OrderResponse, TrackingInfo, Address, OrderItem
import logging

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Gerenciador central para todos os conectores de dropshipping.
    Fornece uma interface unificada para interagir com múltiplos fornecedores.
    """

    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self.active_connectors: List[str] = []

    def register_connector(self, name: str, connector: BaseConnector) -> bool:
        """
        Registra um novo conector.
        
        Args:
            name: Nome único do conector
            connector: Instância do conector
            
        Returns:
            bool: True se registrado com sucesso
        """
        try:
            if connector.test_connection():
                self.connectors[name] = connector
                self.active_connectors.append(name)
                logger.info(f"Conector {name} registrado com sucesso")
                return True
            else:
                logger.error(f"Falha ao testar conexão do conector {name}")
                return False
        except Exception as e:
            logger.error(f"Erro ao registrar conector {name}: {e}")
            return False

    def unregister_connector(self, name: str) -> bool:
        """
        Remove um conector registrado.
        
        Args:
            name: Nome do conector
            
        Returns:
            bool: True se removido com sucesso
        """
        if name in self.connectors:
            del self.connectors[name]
            if name in self.active_connectors:
                self.active_connectors.remove(name)
            logger.info(f"Conector {name} removido")
            return True
        return False

    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """
        Obtém um conector específico.
        
        Args:
            name: Nome do conector
            
        Returns:
            BaseConnector: Instância do conector ou None
        """
        return self.connectors.get(name)

    def list_connectors(self) -> List[Dict[str, Any]]:
        """
        Lista todos os conectores registrados.
        
        Returns:
            List[Dict]: Lista com informações dos conectores
        """
        return [
            {
                'name': name,
                'info': connector.get_connector_info(),
                'active': name in self.active_connectors
            }
            for name, connector in self.connectors.items()
        ]

    def search_products_all(self, query: str, **kwargs) -> Dict[str, List[Product]]:
        """
        Busca produtos em todos os conectores ativos.
        
        Args:
            query: Termo de busca
            **kwargs: Parâmetros adicionais
            
        Returns:
            Dict: Resultados por conector
        """
        results = {}
        for name in self.active_connectors:
            try:
                connector = self.connectors[name]
                products = connector.search_products(query, **kwargs)
                results[name] = products
                logger.info(f"Encontrados {len(products)} produtos no {name}")
            except Exception as e:
                logger.error(f"Erro ao buscar produtos no {name}: {e}")
                results[name] = []
        
        return results

    def get_product_details_from_supplier(self, supplier_name: str, product_id: str, **kwargs) -> Optional[Product]:
        """
        Obtém detalhes de um produto de um fornecedor específico.
        
        Args:
            supplier_name: Nome do fornecedor/conector
            product_id: ID do produto
            **kwargs: Parâmetros adicionais
            
        Returns:
            Product: Detalhes do produto ou None
        """
        connector = self.get_connector(supplier_name)
        if connector:
            try:
                return connector.get_product_details(product_id, **kwargs)
            except Exception as e:
                logger.error(f"Erro ao obter produto {product_id} do {supplier_name}: {e}")
        return None

    def create_order_with_supplier(self, supplier_name: str, order: Order) -> OrderResponse:
        """
        Cria um pedido com um fornecedor específico.
        
        Args:
            supplier_name: Nome do fornecedor/conector
            order: Dados do pedido
            
        Returns:
            OrderResponse: Resposta da criação do pedido
        """
        connector = self.get_connector(supplier_name)
        if not connector:
            return OrderResponse(
                success=False,
                order_id=None,
                supplier_order_id=None,
                tracking_number=None,
                estimated_delivery=None,
                message=f"Conector {supplier_name} não encontrado",
                error_code="CONNECTOR_NOT_FOUND"
            )

        try:
            return connector.create_order(order)
        except Exception as e:
            logger.error(f"Erro ao criar pedido no {supplier_name}: {e}")
            return OrderResponse(
                success=False,
                order_id=None,
                supplier_order_id=None,
                tracking_number=None,
                estimated_delivery=None,
                message=f"Erro ao criar pedido: {str(e)}",
                error_code="ORDER_CREATION_FAILED"
            )

    def calculate_shipping_options(self, items: List[OrderItem], address: Address) -> Dict[str, Dict[str, Any]]:
        """
        Calcula opções de envio em todos os conectores relevantes.
        
        Args:
            items: Lista de itens do pedido
            address: Endereço de entrega
            
        Returns:
            Dict: Opções de envio por conector
        """
        shipping_options = {}
        
        # Agrupa itens por fornecedor
        items_by_supplier = {}
        for item in items:
            supplier = item.supplier_product_id.split('_')[0] if '_' in item.supplier_product_id else 'unknown'
            if supplier not in items_by_supplier:
                items_by_supplier[supplier] = []
            items_by_supplier[supplier].append(item)

        # Calcula frete para cada fornecedor
        for supplier, supplier_items in items_by_supplier.items():
            connector = self.get_connector(supplier)
            if connector:
                try:
                    options = connector.calculate_shipping(supplier_items, address)
                    shipping_options[supplier] = options
                except Exception as e:
                    logger.error(f"Erro ao calcular frete no {supplier}: {e}")
                    shipping_options[supplier] = {'error': str(e)}

        return shipping_options

    def sync_inventory_all(self, product_mapping: Dict[str, List[str]]) -> Dict[str, Dict[str, int]]:
        """
        Sincroniza estoque em todos os conectores.
        
        Args:
            product_mapping: Mapeamento supplier -> [product_ids]
            
        Returns:
            Dict: Estoque por conector e produto
        """
        inventory_results = {}
        
        for supplier, product_ids in product_mapping.items():
            connector = self.get_connector(supplier)
            if connector:
                try:
                    inventory = connector.sync_inventory(product_ids)
                    inventory_results[supplier] = inventory
                    logger.info(f"Sincronizado estoque de {len(product_ids)} produtos do {supplier}")
                except Exception as e:
                    logger.error(f"Erro ao sincronizar estoque do {supplier}: {e}")
                    inventory_results[supplier] = {}

        return inventory_results

    def get_tracking_info_from_supplier(self, supplier_name: str, tracking_number: str) -> Optional[TrackingInfo]:
        """
        Obtém informações de rastreamento de um fornecedor específico.
        
        Args:
            supplier_name: Nome do fornecedor/conector
            tracking_number: Número de rastreamento
            
        Returns:
            TrackingInfo: Informações de rastreamento ou None
        """
        connector = self.get_connector(supplier_name)
        if connector:
            try:
                return connector.get_tracking_info(tracking_number)
            except Exception as e:
                logger.error(f"Erro ao obter rastreamento {tracking_number} do {supplier_name}: {e}")
        return None

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica a saúde de todos os conectores.
        
        Returns:
            Dict: Status de saúde de cada conector
        """
        health_status = {
            'total_connectors': len(self.connectors),
            'active_connectors': len(self.active_connectors),
            'connectors': {}
        }

        for name, connector in self.connectors.items():
            try:
                is_healthy = connector.test_connection()
                health_status['connectors'][name] = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'active': name in self.active_connectors,
                    'config': connector.get_connector_info()
                }
            except Exception as e:
                health_status['connectors'][name] = {
                    'status': 'error',
                    'active': False,
                    'error': str(e)
                }

        return health_status

    def find_best_supplier_for_product(self, product_query: str, criteria: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Encontra o melhor fornecedor para um produto baseado em critérios.
        
        Args:
            product_query: Consulta do produto
            criteria: Critérios de seleção (preço, tempo de entrega, etc.)
            
        Returns:
            Dict: Informações do melhor fornecedor e produto
        """
        if criteria is None:
            criteria = {'priority': 'price'}  # Padrão: menor preço

        all_results = self.search_products_all(product_query)
        best_option = None
        best_score = float('inf') if criteria.get('priority') == 'price' else 0

        for supplier, products in all_results.items():
            for product in products:
                score = self._calculate_product_score(product, criteria)
                
                if criteria.get('priority') == 'price' and score < best_score:
                    best_score = score
                    best_option = {
                        'supplier': supplier,
                        'product': product,
                        'score': score
                    }
                elif criteria.get('priority') != 'price' and score > best_score:
                    best_score = score
                    best_option = {
                        'supplier': supplier,
                        'product': product,
                        'score': score
                    }

        return best_option

    def _calculate_product_score(self, product: Product, criteria: Dict[str, Any]) -> float:
        """
        Calcula pontuação de um produto baseado nos critérios.
        
        Args:
            product: Produto a ser avaliado
            criteria: Critérios de avaliação
            
        Returns:
            float: Pontuação do produto
        """
        if criteria.get('priority') == 'price':
            return product.price
        elif criteria.get('priority') == 'stock':
            return product.stock_quantity
        else:
            # Pontuação composta (preço + estoque)
            price_weight = criteria.get('price_weight', 0.7)
            stock_weight = criteria.get('stock_weight', 0.3)
            
            # Normaliza preço (menor é melhor)
            price_score = 1 / (product.price + 1)
            # Normaliza estoque (maior é melhor)
            stock_score = min(product.stock_quantity / 100, 1.0)
            
            return (price_score * price_weight) + (stock_score * stock_weight)


# Instância global do gerenciador
connector_manager = ConnectorManager()

