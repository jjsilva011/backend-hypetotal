"""
Serviço de sincronização de preços e estoque para dropshipping
"""

from datetime import datetime, timedelta
from src.models.user import db
from src.models.product import Product
from src.models.supplier import Supplier, SupplierProduct
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceSyncService:
    """Serviço para sincronização de preços e estoque"""
    
    @staticmethod
    def sync_product_prices(supplier_id=None, product_id=None):
        """
        Sincronizar preços de produtos
        
        Args:
            supplier_id: ID do fornecedor específico (opcional)
            product_id: ID do produto específico (opcional)
        """
        try:
            query = db.session.query(Product, SupplierProduct, Supplier).join(
                SupplierProduct, Product.supplier_product_id == SupplierProduct.supplier_sku
            ).join(
                Supplier, SupplierProduct.supplier_id == Supplier.id
            ).filter(
                Product.is_dropshipping == True,
                Product.auto_sync_price == True,
                Supplier.is_active == True
            )
            
            if supplier_id:
                query = query.filter(Supplier.id == supplier_id)
            
            if product_id:
                query = query.filter(Product.id == product_id)
            
            products_to_sync = query.all()
            
            sync_results = {
                'total_products': len(products_to_sync),
                'updated_products': 0,
                'errors': [],
                'price_changes': []
            }
            
            for product, supplier_product, supplier in products_to_sync:
                try:
                    old_price = product.price
                    old_supplier_price = product.supplier_price
                    
                    # Atualizar preço do fornecedor
                    product.supplier_price = supplier_product.supplier_price
                    
                    # Calcular novo preço com margem
                    margin = product.margin_percentage / 100
                    new_price = supplier_product.supplier_price * (1 + margin)
                    
                    # Aplicar regras de preço mínimo/máximo se configuradas
                    new_price = PriceSyncService._apply_price_rules(new_price, product, supplier)
                    
                    product.price = new_price
                    product.last_sync_at = datetime.utcnow()
                    
                    # Registrar mudança de preço
                    if old_price != new_price or old_supplier_price != supplier_product.supplier_price:
                        sync_results['price_changes'].append({
                            'product_id': product.id,
                            'product_name': product.name,
                            'old_price': old_price,
                            'new_price': new_price,
                            'old_supplier_price': old_supplier_price,
                            'new_supplier_price': supplier_product.supplier_price,
                            'margin_percentage': product.margin_percentage,
                            'supplier_name': supplier.name
                        })
                    
                    sync_results['updated_products'] += 1
                    
                except Exception as e:
                    error_msg = f"Erro ao sincronizar preço do produto {product.id}: {str(e)}"
                    sync_results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            db.session.commit()
            
            logger.info(f"Sincronização de preços concluída: {sync_results['updated_products']} produtos atualizados")
            
            return sync_results
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro na sincronização de preços: {str(e)}")
            raise e
    
    @staticmethod
    def sync_product_stock(supplier_id=None, product_id=None):
        """
        Sincronizar estoque de produtos
        
        Args:
            supplier_id: ID do fornecedor específico (opcional)
            product_id: ID do produto específico (opcional)
        """
        try:
            query = db.session.query(Product, SupplierProduct, Supplier).join(
                SupplierProduct, Product.supplier_product_id == SupplierProduct.supplier_sku
            ).join(
                Supplier, SupplierProduct.supplier_id == Supplier.id
            ).filter(
                Product.is_dropshipping == True,
                Product.auto_sync_stock == True,
                Supplier.is_active == True
            )
            
            if supplier_id:
                query = query.filter(Supplier.id == supplier_id)
            
            if product_id:
                query = query.filter(Product.id == product_id)
            
            products_to_sync = query.all()
            
            sync_results = {
                'total_products': len(products_to_sync),
                'updated_products': 0,
                'errors': [],
                'stock_changes': []
            }
            
            for product, supplier_product, supplier in products_to_sync:
                try:
                    old_stock = product.stock
                    new_stock = supplier_product.supplier_stock
                    
                    # Aplicar regras de estoque se configuradas
                    new_stock = PriceSyncService._apply_stock_rules(new_stock, product, supplier)
                    
                    product.stock = new_stock
                    product.last_sync_at = datetime.utcnow()
                    
                    # Registrar mudança de estoque
                    if old_stock != new_stock:
                        sync_results['stock_changes'].append({
                            'product_id': product.id,
                            'product_name': product.name,
                            'old_stock': old_stock,
                            'new_stock': new_stock,
                            'supplier_stock': supplier_product.supplier_stock,
                            'supplier_name': supplier.name
                        })
                    
                    sync_results['updated_products'] += 1
                    
                except Exception as e:
                    error_msg = f"Erro ao sincronizar estoque do produto {product.id}: {str(e)}"
                    sync_results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            db.session.commit()
            
            logger.info(f"Sincronização de estoque concluída: {sync_results['updated_products']} produtos atualizados")
            
            return sync_results
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro na sincronização de estoque: {str(e)}")
            raise e
    
    @staticmethod
    def sync_all_products(supplier_id=None):
        """
        Sincronizar preços e estoque de todos os produtos
        
        Args:
            supplier_id: ID do fornecedor específico (opcional)
        """
        try:
            logger.info("Iniciando sincronização completa de preços e estoque")
            
            # Sincronizar preços
            price_results = PriceSyncService.sync_product_prices(supplier_id)
            
            # Sincronizar estoque
            stock_results = PriceSyncService.sync_product_stock(supplier_id)
            
            # Combinar resultados
            combined_results = {
                'price_sync': price_results,
                'stock_sync': stock_results,
                'total_products_processed': max(price_results['total_products'], stock_results['total_products']),
                'sync_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("Sincronização completa finalizada")
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Erro na sincronização completa: {str(e)}")
            raise e
    
    @staticmethod
    def _apply_price_rules(price, product, supplier):
        """
        Aplicar regras de preço (mínimo, máximo, arredondamento)
        
        Args:
            price: Preço calculado
            product: Produto
            supplier: Fornecedor
            
        Returns:
            Preço ajustado conforme regras
        """
        # Regra de preço mínimo (exemplo: R$ 10,00)
        min_price = 10.00
        if price < min_price:
            price = min_price
        
        # Regra de preço máximo baseado na categoria (exemplo)
        max_price_rules = {
            'Eletrônicos': 10000.00,
            'Calçados': 1000.00,
            'Acessórios': 500.00
        }
        
        if product.category and product.category.name in max_price_rules:
            max_price = max_price_rules[product.category.name]
            if price > max_price:
                price = max_price
        
        # Arredondamento para .99 ou .90
        if price >= 100:
            # Para valores acima de R$ 100, arredondar para .90
            price = int(price) + 0.90
        else:
            # Para valores menores, arredondar para .99
            price = int(price) + 0.99
        
        return round(price, 2)
    
    @staticmethod
    def _apply_stock_rules(stock, product, supplier):
        """
        Aplicar regras de estoque (reserva, limite máximo)
        
        Args:
            stock: Estoque do fornecedor
            product: Produto
            supplier: Fornecedor
            
        Returns:
            Estoque ajustado conforme regras
        """
        # Regra de reserva de segurança (manter 2 unidades de reserva)
        safety_stock = 2
        if stock > safety_stock:
            stock = stock - safety_stock
        else:
            stock = 0
        
        # Regra de limite máximo de exibição (não mostrar mais que 50 unidades)
        max_display_stock = 50
        if stock > max_display_stock:
            stock = max_display_stock
        
        return stock
    
    @staticmethod
    def get_price_history(product_id, days=30):
        """
        Obter histórico de preços de um produto
        
        Args:
            product_id: ID do produto
            days: Número de dias para buscar histórico
            
        Returns:
            Lista com histórico de preços
        """
        # Em um sistema real, isso seria armazenado em uma tabela de histórico
        # Por enquanto, retornamos dados simulados
        
        product = Product.query.get(product_id)
        if not product:
            return []
        
        # Simular histórico de preços
        history = []
        current_date = datetime.utcnow()
        
        for i in range(days):
            date = current_date - timedelta(days=i)
            # Simular variação de preço de ±5%
            import random
            variation = random.uniform(0.95, 1.05)
            price = round(product.price * variation, 2)
            
            history.append({
                'date': date.isoformat(),
                'price': price,
                'supplier_price': round(price / (1 + product.margin_percentage / 100), 2)
            })
        
        return list(reversed(history))
    
    @staticmethod
    def get_stock_alerts(low_stock_threshold=5):
        """
        Obter alertas de estoque baixo
        
        Args:
            low_stock_threshold: Limite para considerar estoque baixo
            
        Returns:
            Lista de produtos com estoque baixo
        """
        try:
            low_stock_products = Product.query.filter(
                Product.is_dropshipping == True,
                Product.stock <= low_stock_threshold,
                Product.stock >= 0
            ).all()
            
            alerts = []
            for product in low_stock_products:
                supplier_product = SupplierProduct.query.filter_by(
                    supplier_id=product.supplier_id,
                    supplier_sku=product.supplier_product_id
                ).first()
                
                alerts.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'current_stock': product.stock,
                    'supplier_stock': supplier_product.supplier_stock if supplier_product else 0,
                    'last_sync': product.last_sync_at.isoformat() if product.last_sync_at else None,
                    'supplier_name': product.supplier.name if product.supplier else 'Desconhecido',
                    'alert_level': 'critical' if product.stock == 0 else 'warning'
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Erro ao obter alertas de estoque: {str(e)}")
            return []
    
    @staticmethod
    def get_price_alerts(price_change_threshold=10.0):
        """
        Obter alertas de mudanças significativas de preço
        
        Args:
            price_change_threshold: Percentual de mudança para gerar alerta
            
        Returns:
            Lista de produtos com mudanças significativas de preço
        """
        # Em um sistema real, isso compararia com histórico de preços
        # Por enquanto, retornamos dados simulados baseados na última sincronização
        
        try:
            recent_syncs = Product.query.filter(
                Product.is_dropshipping == True,
                Product.last_sync_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            alerts = []
            for product in recent_syncs:
                # Simular mudança de preço
                import random
                price_change = random.uniform(-15.0, 15.0)
                
                if abs(price_change) >= price_change_threshold:
                    alerts.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'current_price': product.price,
                        'price_change_percentage': round(price_change, 2),
                        'last_sync': product.last_sync_at.isoformat(),
                        'supplier_name': product.supplier.name if product.supplier else 'Desconhecido',
                        'alert_level': 'critical' if abs(price_change) >= 20 else 'warning'
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Erro ao obter alertas de preço: {str(e)}")
            return []
    
    @staticmethod
    def bulk_update_margins(supplier_id, new_margin_percentage):
        """
        Atualizar margem de lucro em massa para produtos de um fornecedor
        
        Args:
            supplier_id: ID do fornecedor
            new_margin_percentage: Nova margem de lucro em percentual
        """
        try:
            products = Product.query.filter_by(
                supplier_id=supplier_id,
                is_dropshipping=True
            ).all()
            
            updated_count = 0
            price_changes = []
            
            for product in products:
                old_price = product.price
                old_margin = product.margin_percentage
                
                # Atualizar margem
                product.margin_percentage = new_margin_percentage
                
                # Recalcular preço
                if product.supplier_price:
                    margin = new_margin_percentage / 100
                    new_price = product.supplier_price * (1 + margin)
                    new_price = PriceSyncService._apply_price_rules(new_price, product, product.supplier)
                    product.price = new_price
                
                product.last_sync_at = datetime.utcnow()
                
                price_changes.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'old_price': old_price,
                    'new_price': product.price,
                    'old_margin': old_margin,
                    'new_margin': new_margin_percentage
                })
                
                updated_count += 1
            
            db.session.commit()
            
            logger.info(f"Margem atualizada para {updated_count} produtos do fornecedor {supplier_id}")
            
            return {
                'updated_products': updated_count,
                'price_changes': price_changes,
                'new_margin_percentage': new_margin_percentage
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar margens em massa: {str(e)}")
            raise e

