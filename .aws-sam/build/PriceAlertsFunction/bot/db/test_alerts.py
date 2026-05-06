"""
Unit tests for AlertsDB module.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from bot.db.alerts import AlertsDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    return Mock()


@pytest.fixture
def alerts_db(mock_table):
    """Create AlertsDB instance with mocked table."""
    with patch('boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        
        db = AlertsDB(table_name='test-table', region='us-east-1')
        db.table = mock_table
        return db


def test_create_alert_success(alerts_db, mock_table):
    """Test successful alert creation."""
    alert_id = alerts_db.create_alert('123456', 'BTC', 100000.0, 'above')
    
    assert alert_id is not None
    assert isinstance(alert_id, str)
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    assert call_args['Key'] == {'telegram_user_id': '123456'}
    
    # Verify alert structure
    alert_list = call_args['ExpressionAttributeValues'][':alert']
    assert len(alert_list) == 1
    alert = alert_list[0]
    assert alert['asset_symbol'] == 'BTC'
    assert alert['target_price'] == 100000.0
    assert alert['direction'] == 'above'
    assert 'alert_id' in alert


def test_create_alert_error(alerts_db, mock_table):
    """Test alert creation with DynamoDB error."""
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        alerts_db.create_alert('123456', 'BTC', 100000.0, 'above')


def test_get_alerts_success(alerts_db, mock_table):
    """Test successful alerts retrieval."""
    expected_alerts = [
        {'alert_id': 'uuid-1', 'asset_symbol': 'BTC', 'target_price': 100000.0, 'direction': 'above'},
        {'alert_id': 'uuid-2', 'asset_symbol': 'ETH', 'target_price': 5000.0, 'direction': 'below'}
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'price_alerts': expected_alerts}
    }
    
    result = alerts_db.get_alerts('123456')
    
    assert result == expected_alerts
    mock_table.get_item.assert_called_once_with(
        Key={'telegram_user_id': '123456'},
        ProjectionExpression='price_alerts'
    )


def test_get_alerts_empty(alerts_db, mock_table):
    """Test alerts retrieval when user has no alerts."""
    mock_table.get_item.return_value = {'Item': {}}
    
    result = alerts_db.get_alerts('123456')
    
    assert result == []


def test_get_alerts_error(alerts_db, mock_table):
    """Test alerts retrieval with DynamoDB error."""
    mock_table.get_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'GetItem'
    )
    
    with pytest.raises(ClientError):
        alerts_db.get_alerts('123456')


def test_get_all_active_alerts_success(alerts_db, mock_table):
    """Test successful retrieval of all active alerts."""
    mock_table.scan.return_value = {
        'Items': [
            {
                'telegram_user_id': '123456',
                'price_alerts': [
                    {'alert_id': 'uuid-1', 'asset_symbol': 'BTC', 'target_price': 100000.0, 'direction': 'above'}
                ]
            },
            {
                'telegram_user_id': '789012',
                'price_alerts': [
                    {'alert_id': 'uuid-2', 'asset_symbol': 'ETH', 'target_price': 5000.0, 'direction': 'below'}
                ]
            }
        ]
    }
    
    result = alerts_db.get_all_active_alerts()
    
    assert len(result) == 2
    assert result[0]['user_id'] == '123456'
    assert result[0]['alert_id'] == 'uuid-1'
    assert result[1]['user_id'] == '789012'
    assert result[1]['alert_id'] == 'uuid-2'


def test_get_all_active_alerts_with_pagination(alerts_db, mock_table):
    """Test retrieval of all active alerts with pagination."""
    # First page
    mock_table.scan.side_effect = [
        {
            'Items': [
                {
                    'telegram_user_id': '123456',
                    'price_alerts': [
                        {'alert_id': 'uuid-1', 'asset_symbol': 'BTC', 'target_price': 100000.0, 'direction': 'above'}
                    ]
                }
            ],
            'LastEvaluatedKey': {'telegram_user_id': '123456'}
        },
        # Second page
        {
            'Items': [
                {
                    'telegram_user_id': '789012',
                    'price_alerts': [
                        {'alert_id': 'uuid-2', 'asset_symbol': 'ETH', 'target_price': 5000.0, 'direction': 'below'}
                    ]
                }
            ]
        }
    ]
    
    result = alerts_db.get_all_active_alerts()
    
    assert len(result) == 2
    assert mock_table.scan.call_count == 2


def test_get_all_active_alerts_error(alerts_db, mock_table):
    """Test get all active alerts with DynamoDB error."""
    mock_table.scan.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'Scan'
    )
    
    with pytest.raises(ClientError):
        alerts_db.get_all_active_alerts()


def test_delete_alert_with_user_id(alerts_db, mock_table):
    """Test successful alert deletion with user_id provided."""
    existing_alerts = [
        {'alert_id': 'uuid-1', 'asset_symbol': 'BTC', 'target_price': 100000.0, 'direction': 'above'},
        {'alert_id': 'uuid-2', 'asset_symbol': 'ETH', 'target_price': 5000.0, 'direction': 'below'}
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'price_alerts': existing_alerts}
    }
    
    alerts_db.delete_alert('uuid-1', user_id='123456')
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    updated_alerts = call_args['ExpressionAttributeValues'][':alerts']
    assert len(updated_alerts) == 1
    assert updated_alerts[0]['alert_id'] == 'uuid-2'


def test_delete_alert_without_user_id(alerts_db, mock_table):
    """Test alert deletion without user_id (requires scan)."""
    # Mock get_all_active_alerts
    with patch.object(alerts_db, 'get_all_active_alerts') as mock_get_all:
        mock_get_all.return_value = [
            {'alert_id': 'uuid-1', 'user_id': '123456', 'asset_symbol': 'BTC'},
            {'alert_id': 'uuid-2', 'user_id': '789012', 'asset_symbol': 'ETH'}
        ]
        
        # Mock get_alerts for the specific user
        with patch.object(alerts_db, 'get_alerts') as mock_get_alerts:
            mock_get_alerts.return_value = [
                {'alert_id': 'uuid-1', 'asset_symbol': 'BTC', 'target_price': 100000.0, 'direction': 'above'}
            ]
            
            alerts_db.delete_alert('uuid-1')
            
            mock_table.update_item.assert_called_once()


def test_delete_alert_error(alerts_db, mock_table):
    """Test alert deletion with DynamoDB error."""
    mock_table.get_item.return_value = {
        'Item': {'price_alerts': [{'alert_id': 'uuid-1', 'asset_symbol': 'BTC'}]}
    }
    
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        alerts_db.delete_alert('uuid-1', user_id='123456')
