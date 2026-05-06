"""
Contacts database operations.

This module provides CRUD operations for user contacts in DynamoDB.
"""

import uuid
from typing import List, Dict, Any
from botocore.exceptions import ClientError
import boto3


class ContactsDB:
    """
    Database client for contact operations.
    
    Manages user contacts (saved wallet addresses with friendly names)
    stored as a list within the user record.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize ContactsDB client.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def add_contact(self, user_id: str, name: str, address: str) -> str:
        """
        Add a contact to the user's contact list.
        
        Args:
            user_id: Telegram user ID
            name: Friendly name for the contact
            address: Wallet address
            
        Returns:
            str: Unique contact_id for the new contact
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            contact_id = str(uuid.uuid4())
            
            contact = {
                'contact_id': contact_id,
                'name': name,
                'address': address
            }
            
            # Append to contacts list
            self.table.update_item(
                Key={'telegram_user_id': user_id},
                UpdateExpression='SET contacts = list_append(if_not_exists(contacts, :empty_list), :contact)',
                ExpressionAttributeValues={
                    ':contact': [contact],
                    ':empty_list': []
                }
            )
            
            return contact_id
        except ClientError as e:
            print(f"Error adding contact for user {user_id}: {e}")
            raise
    
    def get_contacts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all contacts for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            list: List of contact dictionaries with contact_id, name, and address
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={'telegram_user_id': user_id},
                ProjectionExpression='contacts'
            )
            
            item = response.get('Item', {})
            return item.get('contacts', [])
        except ClientError as e:
            print(f"Error getting contacts for user {user_id}: {e}")
            raise
    
    def remove_contact(self, user_id: str, contact_id: str) -> None:
        """
        Remove a contact from the user's contact list.
        
        Args:
            user_id: Telegram user ID
            contact_id: Unique identifier of the contact to remove
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # First, get the current contacts
            contacts = self.get_contacts(user_id)
            
            # Filter out the contact to remove
            updated_contacts = [c for c in contacts if c.get('contact_id') != contact_id]
            
            # Update the contacts list
            self.table.update_item(
                Key={'telegram_user_id': user_id},
                UpdateExpression='SET contacts = :contacts',
                ExpressionAttributeValues={
                    ':contacts': updated_contacts
                }
            )
        except ClientError as e:
            print(f"Error removing contact {contact_id} for user {user_id}: {e}")
            raise
