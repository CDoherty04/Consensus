"""
Unit tests for ScheduledPaymentsDB module.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from bot.db.scheduled_payments import ScheduledPaymentsDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    return Mock()


@pytest.fixture
def payments_db(mock_table):
    """Create ScheduledPaymentsDB instance with mocked table."""
    with patch('boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        
        db = ScheduledPaymentsDB(table_name='test-table', region='us-east-1')
        db.table = mock_table
        return db


def test_create_payment_success(payments_db, mock_table):
    """Test successful payment creation."""
    payment_id = payments_db.create_payment(
        '123456', 'contact-1', 10.0, 'USDC', 'weekly', 1704067200
    )
    
    assert payment_id is not None
    assert isinstance(payment_id, str)
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    assert call_args['Key'] == {'telegram_user_id': '123456'}
    
    # Verify payment structure
    payment_list = call_args['ExpressionAttributeValues'][':payment']
    assert len(payment_list) == 1
    payment = payment_list[0]
    assert payment['contact_id'] == 'contact-1'
    assert payment['amount'] == 10.0
    assert payment['currency'] == 'USDC'
    assert payment['recurrence'] == 'weekly'
    assert payment['next_run'] == 1704067200
    assert 'payment_id' in payment


def test_create_payment_error(payments_db, mock_table):
    """Test payment creation with DynamoDB error."""
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        payments_db.create_payment('123456', 'contact-1', 10.0, 'USDC', 'weekly', 1704067200)


def test_get_payments_success(payments_db, mock_table):
    """Test successful payments retrieval."""
    expected_payments = [
        {
            'payment_id': 'uuid-1',
            'contact_id': 'contact-1',
            'amount': 10.0,
            'currency': 'USDC',
            'recurrence': 'weekly',
            'next_run': 1704067200
        }
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'scheduled_payments': expected_payments}
    }
    
    result = payments_db.get_payments('123456')
    
    assert result == expected_payments
    mock_table.get_item.assert_called_once_with(
        Key={'telegram_user_id': '123456'},
        ProjectionExpression='scheduled_payments'
    )


def test_get_payments_empty(payments_db, mock_table):
    """Test payments retrieval when user has no payments."""
    mock_table.get_item.return_value = {'Item': {}}
    
    result = payments_db.get_payments('123456')
    
    assert result == []


def test_get_payments_error(payments_db, mock_table):
    """Test payments retrieval with DynamoDB error."""
    mock_table.get_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'GetItem'
    )
    
    with pytest.raises(ClientError):
        payments_db.get_payments('123456')


def test_get_due_payments_success(payments_db, mock_table):
    """Test successful retrieval of due payments."""
    with patch('time.time', return_value=1704100000):
        mock_table.scan.return_value = {
            'Items': [
                {
                    'telegram_user_id': '123456',
                    'scheduled_payments': [
                        {
                            'payment_id': 'uuid-1',
                            'contact_id': 'contact-1',
                            'amount': 10.0,
                            'currency': 'USDC',
                            'recurrence': 'weekly',
                            'next_run': 1704067200  # Past due
                        },
                        {
                            'payment_id': 'uuid-2',
                            'contact_id': 'contact-2',
                            'amount': 20.0,
                            'currency': 'ETH',
                            'recurrence': 'monthly',
                            'next_run': 1704200000  # Future
                        }
                    ]
                }
            ]
        }
        
        result = payments_db.get_due_payments()
        
        # Only the past due payment should be returned
        assert len(result) == 1
        assert result[0]['payment_id'] == 'uuid-1'
        assert result[0]['user_id'] == '123456'


def test_get_due_payments_with_pagination(payments_db, mock_table):
    """Test retrieval of due payments with pagination."""
    with patch('time.time', return_value=1704100000):
        mock_table.scan.side_effect = [
            {
                'Items': [
                    {
                        'telegram_user_id': '123456',
                        'scheduled_payments': [
                            {'payment_id': 'uuid-1', 'next_run': 1704067200}
                        ]
                    }
                ],
                'LastEvaluatedKey': {'telegram_user_id': '123456'}
            },
            {
                'Items': [
                    {
                        'telegram_user_id': '789012',
                        'scheduled_payments': [
                            {'payment_id': 'uuid-2', 'next_run': 1704080000}
                        ]
                    }
                ]
            }
        ]
        
        result = payments_db.get_due_payments()
        
        assert len(result) == 2
        assert mock_table.scan.call_count == 2


def test_get_due_payments_error(payments_db, mock_table):
    """Test get due payments with DynamoDB error."""
    mock_table.scan.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'Scan'
    )
    
    with pytest.raises(ClientError):
        payments_db.get_due_payments()


def test_update_next_run_with_user_id(payments_db, mock_table):
    """Test successful next_run update with user_id provided."""
    existing_payments = [
        {
            'payment_id': 'uuid-1',
            'contact_id': 'contact-1',
            'amount': 10.0,
            'currency': 'USDC',
            'recurrence': 'weekly',
            'next_run': 1704067200
        }
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'scheduled_payments': existing_payments}
    }
    
    payments_db.update_next_run('uuid-1', 1704672000, user_id='123456')
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    updated_payments = call_args['ExpressionAttributeValues'][':payments']
    assert updated_payments[0]['next_run'] == 1704672000


def test_update_next_run_error(payments_db, mock_table):
    """Test next_run update with DynamoDB error."""
    mock_table.get_item.return_value = {
        'Item': {'scheduled_payments': [{'payment_id': 'uuid-1', 'next_run': 1704067200}]}
    }
    
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        payments_db.update_next_run('uuid-1', 1704672000, user_id='123456')


def test_delete_payment_with_user_id(payments_db, mock_table):
    """Test successful payment deletion with user_id provided."""
    existing_payments = [
        {'payment_id': 'uuid-1', 'amount': 10.0},
        {'payment_id': 'uuid-2', 'amount': 20.0}
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'scheduled_payments': existing_payments}
    }
    
    payments_db.delete_payment('uuid-1', user_id='123456')
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    updated_payments = call_args['ExpressionAttributeValues'][':payments']
    assert len(updated_payments) == 1
    assert updated_payments[0]['payment_id'] == 'uuid-2'


def test_delete_payment_error(payments_db, mock_table):
    """Test payment deletion with DynamoDB error."""
    mock_table.get_item.return_value = {
        'Item': {'scheduled_payments': [{'payment_id': 'uuid-1'}]}
    }
    
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        payments_db.delete_payment('uuid-1', user_id='123456')
