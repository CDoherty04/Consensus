"""
Unit tests for UserStateDB module.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError
from bot.db.user_state import UserStateDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    return Mock()


@pytest.fixture
def user_state_db(mock_table):
    """Create UserStateDB instance with mocked table."""
    with patch('boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        
        db = UserStateDB(table_name='test-table', region='us-east-1')
        db.table = mock_table
        return db


def test_get_user_success(user_state_db, mock_table):
    """Test successful user retrieval."""
    expected_user = {
        'telegram_user_id': '123456',
        'wallet_address': '0xabc123',
        'current_page': 0,
        'interaction_mode': 'menu'
    }
    
    mock_table.get_item.return_value = {'Item': expected_user}
    
    result = user_state_db.get_user('123456')
    
    assert result == expected_user
    mock_table.get_item.assert_called_once_with(
        Key={'telegram_user_id': '123456'}
    )


def test_get_user_not_found(user_state_db, mock_table):
    """Test user retrieval when user doesn't exist."""
    mock_table.get_item.return_value = {}
    
    result = user_state_db.get_user('999999')
    
    assert result is None


def test_get_user_error(user_state_db, mock_table):
    """Test user retrieval with DynamoDB error."""
    mock_table.get_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'GetItem'
    )
    
    with pytest.raises(ClientError):
        user_state_db.get_user('123456')


def test_update_user_success(user_state_db, mock_table):
    """Test successful user update."""
    updates = {
        'current_page': 2,
        'interaction_mode': 'nl'
    }
    
    user_state_db.update_user('123456', updates)
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    assert call_args['Key'] == {'telegram_user_id': '123456'}
    assert 'UpdateExpression' in call_args
    assert 'ExpressionAttributeNames' in call_args
    assert 'ExpressionAttributeValues' in call_args


def test_update_user_multiple_fields(user_state_db, mock_table):
    """Test updating multiple user fields."""
    updates = {
        'current_page': 3,
        'interaction_mode': 'menu',
        'network': 'base-sepolia'
    }
    
    user_state_db.update_user('123456', updates)
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    # Verify all fields are in the update expression
    assert '#current_page' in call_args['ExpressionAttributeNames']
    assert '#interaction_mode' in call_args['ExpressionAttributeNames']
    assert '#network' in call_args['ExpressionAttributeNames']


def test_update_user_error(user_state_db, mock_table):
    """Test user update with DynamoDB error."""
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        user_state_db.update_user('123456', {'current_page': 1})


def test_create_user_success(user_state_db, mock_table):
    """Test successful user creation."""
    user_state_db.create_user('123456', '0xabc123')
    
    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]
    
    user_record = call_args['Item']
    assert user_record['telegram_user_id'] == '123456'
    assert user_record['wallet_address'] == '0xabc123'
    assert user_record['current_page'] == 0
    assert user_record['interaction_mode'] == 'menu'
    assert user_record['network'] == 'base-mainnet'
    assert user_record['notification_prefs'] == {
        'price_alerts': True,
        'scheduled_payments': True,
        'feed_digests': True
    }
    assert user_record['contacts'] == []
    assert user_record['scheduled_payments'] == []
    assert user_record['price_alerts'] == []
    assert user_record['feed_subscriptions'] == []
    assert 'created_at' in user_record
    assert 'updated_at' in user_record


def test_create_user_error(user_state_db, mock_table):
    """Test user creation with DynamoDB error."""
    mock_table.put_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'PutItem'
    )
    
    with pytest.raises(ClientError):
        user_state_db.create_user('123456', '0xabc123')
