"""
Price alerts database operations.

This module provides CRUD operations for price alerts in DynamoDB.
"""

import uuid
from typing import List, Dict, Any
from botocore.exceptions import ClientError
import boto3


class AlertsDB:
    """
    Database client for price alert operations.
    
    Manages price alerts stored as a list within user records and provides
    methods to query all active alerts across all users.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize AlertsDB client.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def create_alert(self, user_id: str, asset: str, target_price: float, direction: str) -> str:
        """
        Create a new price alert for a user.
        
        Args:
            user_id: Telegram user ID
            asset: Asset symbol (e.g., "BTC", "ETH")
            target_price: Price threshold to trigger alert
            direction: "above" or "below"
            
        Returns:
            str: Unique alert_id for the new alert
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            alert_id = str(uuid.uuid4())
            
            alert = {
                'alert_id': alert_id,
                'asset_symbol': asset,
                'target_price': target_price,
                'direction': direction
            }
            
            # Append to price_alerts list
            self.table.update_item(
                Key={'telegram_user_id': user_id},
                UpdateExpression='SET price_alerts = list_append(if_not_exists(price_alerts, :empty_list), :alert)',
                ExpressionAttributeValues={
                    ':alert': [alert],
                    ':empty_list': []
                }
            )
            
            return alert_id
        except ClientError as e:
            print(f"Error creating alert for user {user_id}: {e}")
            raise
    
    def get_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all price alerts for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            list: List of alert dictionaries with alert_id, asset_symbol, 
                  target_price, and direction
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={'telegram_user_id': user_id},
                ProjectionExpression='price_alerts'
            )
            
            item = response.get('Item', {})
            return item.get('price_alerts', [])
        except ClientError as e:
            print(f"Error getting alerts for user {user_id}: {e}")
            raise
    
    def get_all_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Retrieve all active price alerts across all users.
        
        Used by the price-alert-poller Lambda to check all alerts.
        
        Returns:
            list: List of dictionaries with user_id and alert details
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            all_alerts = []
            
            # Scan the table to get all users with price alerts
            response = self.table.scan(
                ProjectionExpression='telegram_user_id, price_alerts'
            )
            
            for item in response.get('Items', []):
                user_id = item.get('telegram_user_id')
                alerts = item.get('price_alerts', [])
                
                # Add user_id to each alert for context
                for alert in alerts:
                    alert_with_user = alert.copy()
                    alert_with_user['user_id'] = user_id
                    all_alerts.append(alert_with_user)
            
            # Handle pagination if there are more results
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, price_alerts',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    alerts = item.get('price_alerts', [])
                    
                    for alert in alerts:
                        alert_with_user = alert.copy()
                        alert_with_user['user_id'] = user_id
                        all_alerts.append(alert_with_user)
            
            return all_alerts
        except ClientError as e:
            print(f"Error getting all active alerts: {e}")
            raise
    
    def delete_alert(self, alert_id: str, user_id: str = None) -> None:
        """
        Delete a price alert.
        
        Args:
            alert_id: Unique identifier of the alert to delete
            user_id: Telegram user ID (optional, but improves performance)
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            if user_id:
                # If we know the user_id, we can directly update that user's record
                alerts = self.get_alerts(user_id)
                updated_alerts = [a for a in alerts if a.get('alert_id') != alert_id]
                
                self.table.update_item(
                    Key={'telegram_user_id': user_id},
                    UpdateExpression='SET price_alerts = :alerts',
                    ExpressionAttributeValues={
                        ':alerts': updated_alerts
                    }
                )
            else:
                # If we don't know the user_id, we need to scan to find it
                # This is less efficient but handles the case where we only have alert_id
                all_alerts = self.get_all_active_alerts()
                
                for alert in all_alerts:
                    if alert.get('alert_id') == alert_id:
                        user_id = alert.get('user_id')
                        alerts = self.get_alerts(user_id)
                        updated_alerts = [a for a in alerts if a.get('alert_id') != alert_id]
                        
                        self.table.update_item(
                            Key={'telegram_user_id': user_id},
                            UpdateExpression='SET price_alerts = :alerts',
                            ExpressionAttributeValues={
                                ':alerts': updated_alerts
                            }
                        )
                        break
        except ClientError as e:
            print(f"Error deleting alert {alert_id}: {e}")
            raise
