"""
Feed subscriptions database operations.

This module provides CRUD operations for feed subscriptions in DynamoDB.
"""

import uuid
from typing import List, Dict, Any
from botocore.exceptions import ClientError
import boto3


class SubscriptionsDB:
    """
    Database client for feed subscription operations.
    
    Manages feed subscriptions (RSS feeds and newsletters) stored as a list
    within user records and provides methods to query all subscriptions.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize SubscriptionsDB client.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def create_subscription(self, user_id: str, feed_url: str) -> str:
        """
        Create a new feed subscription for a user.
        
        Args:
            user_id: Telegram user ID
            feed_url: RSS or newsletter URL
            
        Returns:
            str: Unique subscription_id for the new subscription
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            import time
            
            subscription_id = str(uuid.uuid4())
            
            subscription = {
                'subscription_id': subscription_id,
                'feed_url': feed_url,
                'last_fetched': int(time.time())
            }
            
            # Append to feed_subscriptions list
            self.table.update_item(
                Key={'telegram_user_id': user_id},
                UpdateExpression='SET feed_subscriptions = list_append(if_not_exists(feed_subscriptions, :empty_list), :subscription)',
                ExpressionAttributeValues={
                    ':subscription': [subscription],
                    ':empty_list': []
                }
            )
            
            return subscription_id
        except ClientError as e:
            print(f"Error creating subscription for user {user_id}: {e}")
            raise
    
    def get_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all feed subscriptions for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            list: List of subscription dictionaries with subscription_id,
                  feed_url, and last_fetched timestamp
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={'telegram_user_id': user_id},
                ProjectionExpression='feed_subscriptions'
            )
            
            item = response.get('Item', {})
            return item.get('feed_subscriptions', [])
        except ClientError as e:
            print(f"Error getting subscriptions for user {user_id}: {e}")
            raise
    
    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Retrieve all feed subscriptions across all users.
        
        Used by the feed-digest-runner Lambda to process all subscriptions.
        
        Returns:
            list: List of dictionaries with user_id and subscription details
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            all_subscriptions = []
            
            # Scan the table to get all users with feed subscriptions
            response = self.table.scan(
                ProjectionExpression='telegram_user_id, feed_subscriptions'
            )
            
            for item in response.get('Items', []):
                user_id = item.get('telegram_user_id')
                subscriptions = item.get('feed_subscriptions', [])
                
                # Add user_id to each subscription for context
                for subscription in subscriptions:
                    subscription_with_user = subscription.copy()
                    subscription_with_user['user_id'] = user_id
                    all_subscriptions.append(subscription_with_user)
            
            # Handle pagination if there are more results
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, feed_subscriptions',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    subscriptions = item.get('feed_subscriptions', [])
                    
                    for subscription in subscriptions:
                        subscription_with_user = subscription.copy()
                        subscription_with_user['user_id'] = user_id
                        all_subscriptions.append(subscription_with_user)
            
            return all_subscriptions
        except ClientError as e:
            print(f"Error getting all subscriptions: {e}")
            raise
    
    def update_last_fetched(self, subscription_id: str, timestamp: int, user_id: str = None) -> None:
        """
        Update the last fetched timestamp for a subscription.
        
        Args:
            subscription_id: Unique identifier of the subscription
            timestamp: Unix timestamp of last fetch
            user_id: Telegram user ID (optional, but improves performance)
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            if user_id:
                # If we know the user_id, directly update that user's record
                subscriptions = self.get_subscriptions(user_id)
                
                # Update the last_fetched for the matching subscription
                updated_subscriptions = []
                for subscription in subscriptions:
                    if subscription.get('subscription_id') == subscription_id:
                        subscription['last_fetched'] = timestamp
                    updated_subscriptions.append(subscription)
                
                self.table.update_item(
                    Key={'telegram_user_id': user_id},
                    UpdateExpression='SET feed_subscriptions = :subscriptions',
                    ExpressionAttributeValues={
                        ':subscriptions': updated_subscriptions
                    }
                )
            else:
                # If we don't know the user_id, scan to find it
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, feed_subscriptions'
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    subscriptions = item.get('feed_subscriptions', [])
                    
                    # Check if this user has the subscription we're looking for
                    for subscription in subscriptions:
                        if subscription.get('subscription_id') == subscription_id:
                            # Found it, update and save
                            updated_subscriptions = []
                            for s in subscriptions:
                                if s.get('subscription_id') == subscription_id:
                                    s['last_fetched'] = timestamp
                                updated_subscriptions.append(s)
                            
                            self.table.update_item(
                                Key={'telegram_user_id': user_id},
                                UpdateExpression='SET feed_subscriptions = :subscriptions',
                                ExpressionAttributeValues={
                                    ':subscriptions': updated_subscriptions
                                }
                            )
                            return
        except ClientError as e:
            print(f"Error updating last_fetched for subscription {subscription_id}: {e}")
            raise
    
    def delete_subscription(self, subscription_id: str, user_id: str = None) -> None:
        """
        Delete a feed subscription.
        
        Args:
            subscription_id: Unique identifier of the subscription to delete
            user_id: Telegram user ID (optional, but improves performance)
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            if user_id:
                # If we know the user_id, directly update that user's record
                subscriptions = self.get_subscriptions(user_id)
                updated_subscriptions = [s for s in subscriptions if s.get('subscription_id') != subscription_id]
                
                self.table.update_item(
                    Key={'telegram_user_id': user_id},
                    UpdateExpression='SET feed_subscriptions = :subscriptions',
                    ExpressionAttributeValues={
                        ':subscriptions': updated_subscriptions
                    }
                )
            else:
                # If we don't know the user_id, scan to find it
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, feed_subscriptions'
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    subscriptions = item.get('feed_subscriptions', [])
                    
                    # Check if this user has the subscription we're looking for
                    for subscription in subscriptions:
                        if subscription.get('subscription_id') == subscription_id:
                            # Found it, remove and save
                            updated_subscriptions = [s for s in subscriptions if s.get('subscription_id') != subscription_id]
                            
                            self.table.update_item(
                                Key={'telegram_user_id': user_id},
                                UpdateExpression='SET feed_subscriptions = :subscriptions',
                                ExpressionAttributeValues={
                                    ':subscriptions': updated_subscriptions
                                }
                            )
                            return
        except ClientError as e:
            print(f"Error deleting subscription {subscription_id}: {e}")
            raise
