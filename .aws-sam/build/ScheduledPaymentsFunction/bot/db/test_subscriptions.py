"""
Unit tests for SubscriptionsDB module.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from bot.db.subscriptions import SubscriptionsDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    return Mock()


@pytest.fixture
def subscriptions_db(mock_table):
    """Create SubscriptionsDB instance with mocked table."""
    with patch('boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        
        db = SubscriptionsDB(table_name='test-table', region='us-east-1')
        db.table = mock_table
        return db


def test_create_subscription_success(subscriptions_db, mock_table):
    """Test successful subscription creation."""
    with patch('time.time', return_value=1704000000):
        subscription_id = subscriptions_db.create_subscription(
            '123456', 'https://example.com/rss'
        )
        
        assert subscription_id is not None
        assert isinstance(subscription_id, str)
        
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        
        assert call_args['Key'] == {'telegram_user_id': '123456'}
        
        # Verify subscription structure
        subscription_list = call_args['ExpressionAttributeValues'][':subscription']
        assert len(subscription_list) == 1
        subscription = subscription_list[0]
        assert subscription['feed_url'] == 'https://example.com/rss'
        assert subscription['last_fetched'] == 1704000000
        assert 'subscription_id' in subscription


def test_create_subscription_error(subscriptions_db, mock_table):
    """Test subscription creation with DynamoDB error."""
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        subscriptions_db.create_subscription('123456', 'https://example.com/rss')


def test_get_subscriptions_success(subscriptions_db, mock_table):
    """Test successful subscriptions retrieval."""
    expected_subscriptions = [
        {
            'subscription_id': 'uuid-1',
            'feed_url': 'https://example.com/rss',
            'last_fetched': 1704000000
        }
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'feed_subscriptions': expected_subscriptions}
    }
    
    result = subscriptions_db.get_subscriptions('123456')
    
    assert result == expected_subscriptions
    mock_table.get_item.assert_called_once_with(
        Key={'telegram_user_id': '123456'},
        ProjectionExpression='feed_subscriptions'
    )


def test_get_subscriptions_empty(subscriptions_db, mock_table):
    """Test subscriptions retrieval when user has no subscriptions."""
    mock_table.get_item.return_value = {'Item': {}}
    
    result = subscriptions_db.get_subscriptions('123456')
    
    assert result == []


def test_get_subscriptions_error(subscriptions_db, mock_table):
    """Test subscriptions retrieval with DynamoDB error."""
    mock_table.get_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'GetItem'
    )
    
    with pytest.raises(ClientError):
        subscriptions_db.get_subscriptions('123456')


def test_get_all_subscriptions_success(subscriptions_db, mock_table):
    """Test successful retrieval of all subscriptions."""
    mock_table.scan.return_value = {
        'Items': [
            {
                'telegram_user_id': '123456',
                'feed_subscriptions': [
                    {
                        'subscription_id': 'uuid-1',
                        'feed_url': 'https://example.com/rss',
                        'last_fetched': 1704000000
                    }
                ]
            },
            {
                'telegram_user_id': '789012',
                'feed_subscriptions': [
                    {
                        'subscription_id': 'uuid-2',
                        'feed_url': 'https://another.com/feed',
                        'last_fetched': 1704010000
                    }
                ]
            }
        ]
    }
    
    result = subscriptions_db.get_all_subscriptions()
    
    assert len(result) == 2
    assert result[0]['user_id'] == '123456'
    assert result[0]['subscription_id'] == 'uuid-1'
    assert result[1]['user_id'] == '789012'
    assert result[1]['subscription_id'] == 'uuid-2'


def test_get_all_subscriptions_with_pagination(subscriptions_db, mock_table):
    """Test retrieval of all subscriptions with pagination."""
    mock_table.scan.side_effect = [
        {
            'Items': [
                {
                    'telegram_user_id': '123456',
                    'feed_subscriptions': [
                        {'subscription_id': 'uuid-1', 'feed_url': 'https://example.com/rss'}
                    ]
                }
            ],
            'LastEvaluatedKey': {'telegram_user_id': '123456'}
        },
        {
            'Items': [
                {
                    'telegram_user_id': '789012',
                    'feed_subscriptions': [
                        {'subscription_id': 'uuid-2', 'feed_url': 'https://another.com/feed'}
                    ]
                }
            ]
        }
    ]
    
    result = subscriptions_db.get_all_subscriptions()
    
    assert len(result) == 2
    assert mock_table.scan.call_count == 2


def test_get_all_subscriptions_error(subscriptions_db, mock_table):
    """Test get all subscriptions with DynamoDB error."""
    mock_table.scan.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'Scan'
    )
    
    with pytest.raises(ClientError):
        subscriptions_db.get_all_subscriptions()


def test_update_last_fetched_with_user_id(subscriptions_db, mock_table):
    """Test successful last_fetched update with user_id provided."""
    existing_subscriptions = [
        {
            'subscription_id': 'uuid-1',
            'feed_url': 'https://example.com/rss',
            'last_fetched': 1704000000
        }
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'feed_subscriptions': existing_subscriptions}
    }
    
    subscriptions_db.update_last_fetched('uuid-1', 1704100000, user_id='123456')
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    updated_subscriptions = call_args['ExpressionAttributeValues'][':subscriptions']
    assert updated_subscriptions[0]['last_fetched'] == 1704100000


def test_update_last_fetched_error(subscriptions_db, mock_table):
    """Test last_fetched update with DynamoDB error."""
    mock_table.get_item.return_value = {
        'Item': {'feed_subscriptions': [{'subscription_id': 'uuid-1', 'last_fetched': 1704000000}]}
    }
    
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        subscriptions_db.update_last_fetched('uuid-1', 1704100000, user_id='123456')


def test_delete_subscription_with_user_id(subscriptions_db, mock_table):
    """Test successful subscription deletion with user_id provided."""
    existing_subscriptions = [
        {'subscription_id': 'uuid-1', 'feed_url': 'https://example.com/rss'},
        {'subscription_id': 'uuid-2', 'feed_url': 'https://another.com/feed'}
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'feed_subscriptions': existing_subscriptions}
    }
    
    subscriptions_db.delete_subscription('uuid-1', user_id='123456')
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    updated_subscriptions = call_args['ExpressionAttributeValues'][':subscriptions']
    assert len(updated_subscriptions) == 1
    assert updated_subscriptions[0]['subscription_id'] == 'uuid-2'


def test_delete_subscription_without_user_id(subscriptions_db, mock_table):
    """Test subscription deletion without user_id (requires scan)."""
    mock_table.scan.return_value = {
        'Items': [
            {
                'telegram_user_id': '123456',
                'feed_subscriptions': [
                    {'subscription_id': 'uuid-1', 'feed_url': 'https://example.com/rss'}
                ]
            }
        ]
    }
    
    subscriptions_db.delete_subscription('uuid-1')
    
    mock_table.update_item.assert_called_once()


def test_delete_subscription_error(subscriptions_db, mock_table):
    """Test subscription deletion with DynamoDB error."""
    mock_table.get_item.return_value = {
        'Item': {'feed_subscriptions': [{'subscription_id': 'uuid-1'}]}
    }
    
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        subscriptions_db.delete_subscription('uuid-1', user_id='123456')
