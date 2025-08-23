"""
Rotas para configuração e teste do conector AliExpress.
"""

from flask import Blueprint, request, jsonify
from src.models.aliexpress_connector import AliExpressConnector
from src.models.connector_base import ConnectorConfig, ConnectorStatus
from src.models.connector_manager import connector_manager
import logging

logger = logging.getLogger(__name__)

aliexpress_bp = Blueprint('aliexpress', __name__)


@aliexpress_bp.route('/aliexpress/setup', methods=['POST'])
def setup_aliexpress_connector():
    """Configura o conector AliExpress com as credenciais fornecidas."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['app_key', 'app_secret']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Configuração adicional
        additional_config = {
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token'),
            'token_expires_at': data.get('token_expires_at'),
            'default_country': data.get('default_country', 'US'),
            'default_currency': data.get('default_currency', 'USD'),
            'default_language': data.get('default_language', 'en')
        }

        # Cria a configuração do conector
        config = ConnectorConfig(
            name='aliexpress',
            api_key=data['app_key'],
            api_secret=data['app_secret'],
            base_url=data.get('base_url', 'https://api-sg.aliexpress.com/sync'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            status=ConnectorStatus.ACTIVE,
            additional_config=additional_config
        )

        # Cria e registra o conector
        connector = AliExpressConnector(config)
        
        # Testa a conexão antes de registrar
        if connector.test_connection():
            success = connector_manager.register_connector('aliexpress', connector)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Conector AliExpress configurado com sucesso',
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
                'message': 'Falha na autenticação com AliExpress. Verifique as credenciais.'
            }), 401
            
    except Exception as e:
        logger.error(f"Erro ao configurar conector AliExpress: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@aliexpress_bp.route('/aliexpress/test-auth', methods=['POST'])
def test_aliexpress_auth():
    """Testa a autenticação com AliExpress sem registrar o conector."""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['app_key', 'app_secret']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Configuração temporária para teste
        additional_config = {
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token'),
            'token_expires_at': data.get('token_expires_at'),
            'default_country': data.get('default_country', 'US'),
            'default_currency': data.get('default_currency', 'USD'),
            'default_language': data.get('default_language', 'en')
        }

        config = ConnectorConfig(
            name='aliexpress_test',
            api_key=data['app_key'],
            api_secret=data['app_secret'],
            base_url=data.get('base_url', 'https://api-sg.aliexpress.com/sync'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            status=ConnectorStatus.ACTIVE,
            additional_config=additional_config
        )

        # Cria conector temporário para teste
        connector = AliExpressConnector(config)
        
        # Testa autenticação
        auth_success = connector.authenticate()
        
        return jsonify({
            'success': auth_success,
            'message': 'Autenticação bem-sucedida' if auth_success else 'Falha na autenticação',
            'has_access_token': bool(data.get('access_token')),
            'token_expires_at': data.get('token_expires_at')
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar autenticação AliExpress: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@aliexpress_bp.route('/aliexpress/generate-auth-url', methods=['POST'])
def generate_auth_url():
    """Gera URL de autorização para obter access token do AliExpress."""
    try:
        data = request.get_json()
        
        if 'app_key' not in data:
            return jsonify({
                'success': False,
                'message': 'app_key é obrigatório'
            }), 400

        app_key = data['app_key']
        redirect_uri = data.get('redirect_uri', 'http://localhost:5001/api/aliexpress/callback')
        
        # URL de autorização do AliExpress
        auth_url = (
            f"https://oauth.aliexpress.com/authorize?"
            f"response_type=code&"
            f"client_id={app_key}&"
            f"redirect_uri={redirect_uri}&"
            f"state=aliexpress_auth"
        )
        
        return jsonify({
            'success': True,
            'auth_url': auth_url,
            'redirect_uri': redirect_uri,
            'instructions': [
                '1. Acesse a URL de autorização',
                '2. Faça login na sua conta AliExpress',
                '3. Autorize a aplicação',
                '4. Copie o código de autorização da URL de retorno',
                '5. Use o código para obter o access token'
            ]
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL de autorização: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@aliexpress_bp.route('/aliexpress/exchange-token', methods=['POST'])
def exchange_auth_code():
    """Troca código de autorização por access token."""
    try:
        data = request.get_json()
        
        required_fields = ['app_key', 'app_secret', 'auth_code']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                }), 400

        # Cria conector temporário para fazer a troca
        config = ConnectorConfig(
            name='aliexpress_temp',
            api_key=data['app_key'],
            api_secret=data['app_secret'],
            base_url='https://api-sg.aliexpress.com/sync',
            additional_config={}
        )
        
        connector = AliExpressConnector(config)
        
        # Parâmetros para troca do código
        api_params = {
            'code': data['auth_code'],
            'uuid': data.get('uuid', '')
        }
        
        params = connector._build_request_params('auth/token/security/create', api_params)
        response = connector._make_request('POST', connector.api_base_url, data=params)
        result = response.json()
        
        if 'access_token' in result:
            return jsonify({
                'success': True,
                'access_token': result['access_token'],
                'refresh_token': result.get('refresh_token'),
                'expires_in': result.get('expires_in'),
                'token_type': 'Bearer',
                'message': 'Token obtido com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Erro ao obter token: {result.get('error_description', 'Erro desconhecido')}",
                'error_code': result.get('error')
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao trocar código por token: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@aliexpress_bp.route('/aliexpress/test-product', methods=['POST'])
def test_product_search():
    """Testa a busca de produtos no AliExpress."""
    try:
        data = request.get_json()
        
        # Verifica se o conector está registrado
        connector = connector_manager.get_connector('aliexpress')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector AliExpress não está configurado'
            }), 404

        # Parâmetros de busca
        query = data.get('query', 'smartphone')
        category = data.get('category')
        country = data.get('country', 'US')
        
        # Testa busca de produtos
        products = connector.search_products(
            query, 
            category=category, 
            country=country
        )
        
        # Formata resposta
        formatted_products = []
        for product in products[:5]:  # Limita a 5 produtos para teste
            formatted_products.append({
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'currency': product.currency,
                'stock': product.stock_quantity,
                'images': product.images[:2],  # Primeiras 2 imagens
                'supplier_id': product.supplier_id
            })
        
        return jsonify({
            'success': True,
            'query': query,
            'products_found': len(products),
            'products': formatted_products,
            'message': f'Encontrados {len(products)} produtos'
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar busca de produtos: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@aliexpress_bp.route('/aliexpress/test-product-details', methods=['POST'])
def test_product_details():
    """Testa a obtenção de detalhes de um produto específico."""
    try:
        data = request.get_json()
        
        if 'product_id' not in data:
            return jsonify({
                'success': False,
                'message': 'product_id é obrigatório'
            }), 400

        # Verifica se o conector está registrado
        connector = connector_manager.get_connector('aliexpress')
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector AliExpress não está configurado'
            }), 404

        # Obtém detalhes do produto
        product = connector.get_product_details(
            data['product_id'],
            country=data.get('country', 'US'),
            currency=data.get('currency', 'USD'),
            language=data.get('language', 'en')
        )
        
        if product:
            return jsonify({
                'success': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description[:200] + '...' if len(product.description) > 200 else product.description,
                    'price': product.price,
                    'currency': product.currency,
                    'stock_quantity': product.stock_quantity,
                    'images': product.images,
                    'variations_count': len(product.variations),
                    'category': product.category,
                    'shipping_info': product.shipping_info,
                    'last_updated': product.last_updated
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao testar detalhes do produto: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@aliexpress_bp.route('/aliexpress/status', methods=['GET'])
def get_aliexpress_status():
    """Obtém o status atual do conector AliExpress."""
    try:
        connector = connector_manager.get_connector('aliexpress')
        
        if not connector:
            return jsonify({
                'success': False,
                'message': 'Conector AliExpress não está configurado',
                'configured': False
            })

        # Testa conexão
        is_working = connector.test_connection()
        
        return jsonify({
            'success': True,
            'configured': True,
            'working': is_working,
            'connector_info': connector.get_connector_info(),
            'has_access_token': bool(connector.access_token),
            'token_expires_at': connector.token_expires_at
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status do AliExpress: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

