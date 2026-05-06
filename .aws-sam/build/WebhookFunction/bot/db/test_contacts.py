"""
Unit tests for ContactsDB module.
"""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from bot.db.contacts import ContactsDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    return Mock()


@pytest.fixture
def contacts_db(mock_table):
    """Create ContactsDB instance with mocked table."""
    with patch('boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        
        db = ContactsDB(table_name='test-table', region='us-east-1')
        db.table = mock_table
        return db


def test_add_contact_success(contacts_db, mock_table):
    """Test successful contact addition."""
    contact_id = contacts_db.add_contact('123456', 'Alice', '0xabc123')
    
    assert contact_id is not None
    assert isinstance(contact_id, str)
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    assert call_args['Key'] == {'telegram_user_id': '123456'}
    assert 'UpdateExpression' in call_args
    assert 'ExpressionAttributeValues' in call_args
    
    # Verify contact structure
    contact_list = call_args['ExpressionAttributeValues'][':contact']
    assert len(contact_list) == 1
    contact = contact_list[0]
    assert contact['name'] == 'Alice'
    assert contact['address'] == '0xabc123'
    assert 'contact_id' in contact


def test_add_contact_error(contacts_db, mock_table):
    """Test contact addition with DynamoDB error."""
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        contacts_db.add_contact('123456', 'Alice', '0xabc123')


def test_get_contacts_success(contacts_db, mock_table):
    """Test successful contacts retrieval."""
    expected_contacts = [
        {'contact_id': 'uuid-1', 'name': 'Alice', 'address': '0xabc123'},
        {'contact_id': 'uuid-2', 'name': 'Bob', 'address': '0xdef456'}
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'contacts': expected_contacts}
    }
    
    result = contacts_db.get_contacts('123456')
    
    assert result == expected_contacts
    mock_table.get_item.assert_called_once_with(
        Key={'telegram_user_id': '123456'},
        ProjectionExpression='contacts'
    )


def test_get_contacts_empty(contacts_db, mock_table):
    """Test contacts retrieval when user has no contacts."""
    mock_table.get_item.return_value = {'Item': {}}
    
    result = contacts_db.get_contacts('123456')
    
    assert result == []


def test_get_contacts_no_user(contacts_db, mock_table):
    """Test contacts retrieval when user doesn't exist."""
    mock_table.get_item.return_value = {}
    
    result = contacts_db.get_contacts('999999')
    
    assert result == []


def test_get_contacts_error(contacts_db, mock_table):
    """Test contacts retrieval with DynamoDB error."""
    mock_table.get_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'GetItem'
    )
    
    with pytest.raises(ClientError):
        contacts_db.get_contacts('123456')


def test_remove_contact_success(contacts_db, mock_table):
    """Test successful contact removal."""
    existing_contacts = [
        {'contact_id': 'uuid-1', 'name': 'Alice', 'address': '0xabc123'},
        {'contact_id': 'uuid-2', 'name': 'Bob', 'address': '0xdef456'}
    ]
    
    # Mock get_contacts to return existing contacts
    mock_table.get_item.return_value = {
        'Item': {'contacts': existing_contacts}
    }
    
    contacts_db.remove_contact('123456', 'uuid-1')
    
    # Verify update was called with filtered contacts
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    
    assert call_args['Key'] == {'telegram_user_id': '123456'}
    updated_contacts = call_args['ExpressionAttributeValues'][':contacts']
    assert len(updated_contacts) == 1
    assert updated_contacts[0]['contact_id'] == 'uuid-2'


def test_remove_contact_not_found(contacts_db, mock_table):
    """Test removing a contact that doesn't exist."""
    existing_contacts = [
        {'contact_id': 'uuid-1', 'name': 'Alice', 'address': '0xabc123'}
    ]
    
    mock_table.get_item.return_value = {
        'Item': {'contacts': existing_contacts}
    }
    
    # Should not raise error, just update with same list
    contacts_db.remove_contact('123456', 'uuid-999')
    
    mock_table.update_item.assert_called_once()
    call_args = mock_table.update_item.call_args[1]
    updated_contacts = call_args['ExpressionAttributeValues'][':contacts']
    assert len(updated_contacts) == 1


def test_remove_contact_error(contacts_db, mock_table):
    """Test contact removal with DynamoDB error."""
    mock_table.get_item.return_value = {
        'Item': {'contacts': [{'contact_id': 'uuid-1', 'name': 'Alice', 'address': '0xabc123'}]}
    }
    
    mock_table.update_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'Test error'}},
        'UpdateItem'
    )
    
    with pytest.raises(ClientError):
        contacts_db.remove_contact('123456', 'uuid-1')
