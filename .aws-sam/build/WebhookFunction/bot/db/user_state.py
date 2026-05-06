"""
User state database operations.

This module provides CRUD operations for user state in DynamoDB.
"""

import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


class UserStateDB:
    """
    Database client for user state operations.
    
    Manages user records in DynamoDB including wallet address, current page,
    interaction mode, network selection, and notification preferences.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize UserStateDB client.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user state from DynamoDB.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: User state record, or None if user doesn't exist
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={'telegram_user_id': user_id}
            )
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting user {user_id}: {e}")
            raise
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> None:
        """
        Update user state fields in DynamoDB.
        
        Args:
            user_id: Telegram user ID
            updates: Dictionary of field names and values to update
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Build update expression dynamically
            update_expr_parts = []
            expr_attr_names = {}
            expr_attr_values = {}
            
            for key, value in updates.items():
                # Use attribute names to handle reserved keywords
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expr_parts.append(f"{attr_name} = {attr_value}")
                expr_attr_names[attr_name] = key
                expr_attr_values[attr_value] = value
            
            update_expression = "SET " + ", ".join(update_expr_parts)
            
            self.table.update_item(
                Key={'telegram_user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
        except ClientError as e:
            print(f"Error updating user {user_id}: {e}")
            raise
    
    def create_user(self, user_id: str, wallet_address: str) -> None:
        """
        Initialize new user record in DynamoDB.
        
        Creates a new user with default values for all fields.
        
        Args:
            user_id: Telegram user ID
            wallet_address: Agent wallet address from WAIaaS
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            import time
            
            user_record = {
                'telegram_user_id': user_id,
                'wallet_address': wallet_address,
                'current_page': 0,
                'interaction_mode': 'menu',
                'network': 'base-mainnet',
                'notification_prefs': {
                    'price_alerts': True,
                    'scheduled_payments': True,
                    'feed_digests': True
                },
                'nl_conversation_history': [],
                'contacts': [],
                'scheduled_payments': [],
                'price_alerts': [],
                'feed_subscriptions': [],
                'created_at': int(time.time()),
                'updated_at': int(time.time())
            }
            
            self.table.put_item(Item=user_record)
        except ClientError as e:
            print(f"Error creating user {user_id}: {e}")
            raise
