"""
Serviço de sincronização automática para dropshipping
"""

import requests
import json
from datetime import datetime, timedelta
from src.models.user import db
from src.models.product import Product
from src.models.supplier import Supplier, SupplierProduct, DropshippingOrder
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncService:
    """Serviço para sincronização com fornecedores"""
    
    @staticmethod
    def sync_supplier_products(supplier_id):
        """Sincronizar produtos de um fornecedor específico"""
        try:
            supplier = Supplier.query.get(supplier_id)
            if not supplier or not supplier.is_active:
                raise Exception(f"Fornecedor {supplier_id} não encontrado ou inativo")
            
            logger.info(f"Iniciando sincronização do fornecedor: {supplier.name}")
            
            if supplier.integration_type == 'API':
                return SyncService._sync_via_api(supplier)
            elif supplier.integration_type == 'CSV':
                return SyncService._sync_via_csv(supplier)
            elif supplier.integration_type == 'XML':
                return SyncService._sync_via_xml(supplier)
            else:
                # Sincronização manual ou simulada
                return SyncService._sync_simulated(supplier)
                
        except Exception as e:
            logger.error(f"Erro na sincronização do fornecedor {supplier_id}: {str(e)}")
            raise e
    
    @staticmethod
    def _sync_via_api(supplier):
        """Sincronização via API REST"""
        try:
            headers = {
                'Authorization': f'Bearer {supplier.api_key}',
                'Content-Type': 'application/json'
            }
            
            if supplier.api_secret:
                headers['X-API-Secret'] = supplier.api_secret
            
            # Fazer requisição para obter produtos
            response = requests.get(
                f"{supplier.api_endpoint}/products",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Erro na API do fornecedor: {response.status_code}")
            
            products_data = response.json()
            
            return SyncService._process_products_data(supplier, products_data.get('products', []))
            
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão com API do fornecedor: {str(e)}")
    
    @staticmethod
    def _sync_via_csv(supplier):
        """Sincronização via arquivo CSV"""
        # Em um cenário real, aqui seria feito o download e processamento do CSV
        logger.info(f"Sincronização CSV não implementada para {supplier.name}")
        return SyncService._sync_simulated(supplier)
    
    @staticmethod
    def _sync_via_xml(supplier):
        """Sincronização via arquivo XML"""
        # Em um cenário real, aqui seria feito o download e processamento do XML
        logger.info(f"Sincronização XML não implementada para {supplier.name}")
        return SyncService._sync_simulated(supplier)
    
    @staticmethod
    def _sync_simulated(supplier):
        """Sincronização simulada para demonstração"""
        # Simular dados de produtos
        sample_products = [
            {
                'sku': f'SUPP-{supplier.id}-001',
                'name': f'Produto Premium {supplier.name} 1',
                'description': 'Produto de alta qualidade com excelente custo-benefício',
                'price': 99.99,
                'stock': 50,
                'category': 'Eletrônicos',
                'brand': 'Marca Premium',
                'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop',
                'specifications': json.dumps({
                    'cor': 'Preto',
                    'material': 'Plástico ABS',
                    'garantia': '12 meses'
                }),
                'features': json.dumps([
                    'Alta qualidade',
                    'Durável',
                    'Fácil de usar'
                ]),
                'dimensions': '10x5x2 cm',
                'weight': 0.2
            },
            {
                'sku': f'SUPP-{supplier.id}-002',
                'name': f'Acessório {supplier.name} Pro',
                'description': 'Acessório profissional para uso diário',
                'price': 149.99,
                'stock': 30,
                'category': 'Acessórios',
                'brand': 'Marca Pro',
                'image_url': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop',
                'specifications': json.dumps({
                    'cor': 'Azul',
                    'material': 'Metal',
                    'garantia': '24 meses'
                }),
                'features': json.dumps([
                    'Design moderno',
                    'Resistente',
                    'Multifuncional'
                ]),
                'dimensions': '15x8x3 cm',
                'weight': 0.5
            },
            {
                'sku': f'SUPP-{supplier.id}-003',
                'name': f'Kit Completo {supplier.name}',
                'description': 'Kit completo com todos os acessórios necessários',
                'price': 299.99,
                'stock': 15,
                'category': 'Kits',
                'brand': 'Marca Complete',
                'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop',
                'specifications': json.dumps({
                    'itens_inclusos': '5 peças',
                    'material': 'Misto',
                    'garantia': '18 meses'
                }),
                'features': json.dumps([
                    'Kit completo',
                    'Ótimo custo-benefício',
                    'Fácil instalação'
                ]),
                'dimensions': '25x15x10 cm',
                'weight': 1.2
            }
        ]
        
        return SyncService._process_products_data(supplier, sample_products)
    
    @staticmethod
    def _process_products_data(supplier, products_data):
        """Processar dados de produtos recebidos"""
        synced_count = 0
        new_count = 0
        updated_count = 0
        errors = []
        
        for product_data in products_data:
            try:
                sku = product_data.get('sku')
                if not sku:
                    errors.append("SKU não fornecido para um produto")
                    continue
                
                # Buscar produto existente
                existing_product = SupplierProduct.query.filter_by(
                    supplier_id=supplier.id,
                    supplier_sku=sku
                ).first()
                
                if existing_product:
                    # Atualizar produto existente
                    SyncService._update_supplier_product(existing_product, product_data)
                    updated_count += 1
                else:
                    # Criar novo produto
                    new_product = SyncService._create_supplier_product(supplier, product_data)
                    if new_product:
                        new_count += 1
                
                synced_count += 1
                
            except Exception as e:
                errors.append(f"Erro ao processar produto {product_data.get('sku', 'unknown')}: {str(e)}")
        
        # Atualizar timestamp da última sincronização
        supplier.last_sync = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Sincronização concluída para {supplier.name}: {synced_count} produtos processados")
        
        return {
            'synced_products': synced_count,
            'new_products': new_count,
            'updated_products': updated_count,
            'errors': errors,
            'sync_timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _update_supplier_product(supplier_product, product_data):
        """Atualizar produto existente do fornecedor"""
        supplier_product.supplier_name = product_data.get('name', supplier_product.supplier_name)
        supplier_product.supplier_description = product_data.get('description', supplier_product.supplier_description)
        supplier_product.supplier_price = product_data.get('price', supplier_product.supplier_price)
        supplier_product.supplier_stock = product_data.get('stock', supplier_product.supplier_stock)
        supplier_product.supplier_image_url = product_data.get('image_url', supplier_product.supplier_image_url)
        supplier_product.supplier_category = product_data.get('category', supplier_product.supplier_category)
        supplier_product.supplier_brand = product_data.get('brand', supplier_product.supplier_brand)
        supplier_product.supplier_specifications = product_data.get('specifications', supplier_product.supplier_specifications)
        supplier_product.supplier_features = product_data.get('features', supplier_product.supplier_features)
        supplier_product.supplier_dimensions = product_data.get('dimensions', supplier_product.supplier_dimensions)
        supplier_product.supplier_weight = product_data.get('weight', supplier_product.supplier_weight)
        supplier_product.is_available = product_data.get('available', True)
        supplier_product.last_synced_at = datetime.utcnow()
        supplier_product.updated_at = datetime.utcnow()
        
        # Se o produto está mapeado, atualizar o produto principal também
        if supplier_product.is_mapped and supplier_product.product_id:
            SyncService._update_mapped_product(supplier_product)
    
    @staticmethod
    def _create_supplier_product(supplier, product_data):
        """Criar novo produto do fornecedor"""
        try:
            new_product = SupplierProduct(
                supplier_id=supplier.id,
                supplier_sku=product_data['sku'],
                supplier_name=product_data.get('name'),
                supplier_description=product_data.get('description'),
                supplier_price=product_data.get('price', 0.0),
                supplier_stock=product_data.get('stock', 0),
                supplier_image_url=product_data.get('image_url'),
                supplier_category=product_data.get('category'),
                supplier_brand=product_data.get('brand'),
                supplier_specifications=product_data.get('specifications'),
                supplier_features=product_data.get('features'),
                supplier_dimensions=product_data.get('dimensions'),
                supplier_weight=product_data.get('weight'),
                is_available=product_data.get('available', True),
                last_synced_at=datetime.utcnow()
            )
            
            db.session.add(new_product)
            
            # Auto-mapear se configurado
            if supplier.auto_import_products:
                SyncService._auto_map_product(new_product, supplier)
            
            return new_product
            
        except Exception as e:
            logger.error(f"Erro ao criar produto do fornecedor: {str(e)}")
            return None
    
    @staticmethod
    def _update_mapped_product(supplier_product):
        """Atualizar produto mapeado no catálogo principal"""
        try:
            product = Product.query.get(supplier_product.product_id)
            if not product:
                return
            
            supplier = Supplier.query.get(supplier_product.supplier_id)
            
            # Atualizar preço se configurado
            if product.auto_sync_price and supplier_product.supplier_price:
                margin = product.margin_percentage / 100
                new_price = supplier_product.supplier_price * (1 + margin)
                product.price = new_price
            
            # Atualizar estoque se configurado
            if product.auto_sync_stock:
                product.stock = supplier_product.supplier_stock
            
            # Atualizar outras informações
            product.last_sync_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar produto mapeado: {str(e)}")
    
    @staticmethod
    def _auto_map_product(supplier_product, supplier):
        """Auto-mapear produto do fornecedor para o catálogo"""
        try:
            # Calcular preço final com margem
            margin = supplier.default_margin_percentage / 100
            final_price = supplier_product.supplier_price * (1 + margin)
            
            # Criar novo produto no catálogo
            new_product = Product(
                name=supplier_product.supplier_name,
                description=supplier_product.supplier_description,
                price=final_price,
                image_url=supplier_product.supplier_image_url,
                stock=supplier_product.supplier_stock,
                brand=supplier_product.supplier_brand,
                sku=f"DS-{supplier_product.supplier_sku}",
                specifications=supplier_product.supplier_specifications,
                features=supplier_product.supplier_features,
                supplier_id=supplier.id,
                supplier_product_id=supplier_product.supplier_sku,
                is_dropshipping=True,
                supplier_price=supplier_product.supplier_price,
                margin_percentage=supplier.default_margin_percentage,
                last_sync_at=datetime.utcnow()
            )
            
            db.session.add(new_product)
            db.session.flush()  # Para obter o ID
            
            # Atualizar mapeamento
            supplier_product.product_id = new_product.id
            supplier_product.is_mapped = True
            supplier_product.mapping_confidence = 0.8  # Auto-mapeamento tem confiança menor
            
            logger.info(f"Produto auto-mapeado: {supplier_product.supplier_name}")
            
        except Exception as e:
            logger.error(f"Erro no auto-mapeamento: {str(e)}")
    
    @staticmethod
    def sync_all_suppliers():
        """Sincronizar todos os fornecedores ativos"""
        suppliers = Supplier.query.filter_by(is_active=True).all()
        results = []
        
        for supplier in suppliers:
            try:
                result = SyncService.sync_supplier_products(supplier.id)
                results.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'status': 'success',
                    'result': result
                })
            except Exception as e:
                results.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def check_suppliers_for_sync():
        """Verificar quais fornecedores precisam de sincronização"""
        now = datetime.utcnow()
        suppliers_to_sync = []
        
        suppliers = Supplier.query.filter_by(is_active=True).all()
        
        for supplier in suppliers:
            if supplier.last_sync:
                time_since_sync = now - supplier.last_sync
                sync_interval = timedelta(minutes=supplier.sync_frequency_minutes)
                if time_since_sync >= sync_interval:
                    suppliers_to_sync.append(supplier)
            else:
                # Nunca foi sincronizado
                suppliers_to_sync.append(supplier)
        
        return suppliers_to_sync

