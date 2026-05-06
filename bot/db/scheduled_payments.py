"""
Scheduled payments database operations.

This module provides CRUD operations for scheduled payments in DynamoDB.
"""

import uuid
from typing import List, Dict, Any
from botocore.exceptions import ClientError
import boto3


class ScheduledPaymentsDB:
    """
    Database client for scheduled payment operations.
    
    Manages scheduled payments stored as a list within user records and provides
    methods to query due payments across all users.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize ScheduledPaymentsDB client.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def create_payment(self, user_id: str, contact_id: str, amount: float, 
                      currency: str, recurrence: str, next_run: int) -> str:
        """
        Create a new scheduled payment.
        
        Args:
            user_id: Telegram user ID
            contact_id: ID of the contact to pay
            amount: Payment amount
            currency: Currency symbol (e.g., "ETH", "USDC")
            recurrence: "once", "daily", "weekly", or "monthly"
            next_run: Unix timestamp for next execution
            
        Returns:
            str: Unique payment_id for the new scheduled payment
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            payment_id = str(uuid.uuid4())
            
            payment = {
                'payment_id': payment_id,
                'contact_id': contact_id,
                'amount': amount,
                'currency': currency,
                'recurrence': recurrence,
                'next_run': next_run
            }
            
            # Append to scheduled_payments list
            self.table.update_item(
                Key={'telegram_user_id': user_id},
                UpdateExpression='SET scheduled_payments = list_append(if_not_exists(scheduled_payments, :empty_list), :payment)',
                ExpressionAttributeValues={
                    ':payment': [payment],
                    ':empty_list': []
                }
            )
            
            return payment_id
        except ClientError as e:
            print(f"Error creating scheduled payment for user {user_id}: {e}")
            raise
    
    def get_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all scheduled payments for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            list: List of payment dictionaries with payment_id, contact_id,
                  amount, currency, recurrence, and next_run
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={'telegram_user_id': user_id},
                ProjectionExpression='scheduled_payments'
            )
            
            item = response.get('Item', {})
            return item.get('scheduled_payments', [])
        except ClientError as e:
            print(f"Error getting scheduled payments for user {user_id}: {e}")
            raise
    
    def get_due_payments(self) -> List[Dict[str, Any]]:
        """
        Retrieve all scheduled payments that are due for execution.
        
        Used by the scheduled-payment-runner Lambda to find payments
        where next_run <= current time.
        
        Returns:
            list: List of dictionaries with user_id and payment details
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            import time
            current_time = int(time.time())
            
            due_payments = []
            
            # Scan the table to get all users with scheduled payments
            response = self.table.scan(
                ProjectionExpression='telegram_user_id, scheduled_payments'
            )
            
            for item in response.get('Items', []):
                user_id = item.get('telegram_user_id')
                payments = item.get('scheduled_payments', [])
                
                # Filter for due payments and add user_id
                for payment in payments:
                    if payment.get('next_run', float('inf')) <= current_time:
                        payment_with_user = payment.copy()
                        payment_with_user['user_id'] = user_id
                        due_payments.append(payment_with_user)
            
            # Handle pagination if there are more results
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, scheduled_payments',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    payments = item.get('scheduled_payments', [])
                    
                    for payment in payments:
                        if payment.get('next_run', float('inf')) <= current_time:
                            payment_with_user = payment.copy()
                            payment_with_user['user_id'] = user_id
                            due_payments.append(payment_with_user)
            
            return due_payments
        except ClientError as e:
            print(f"Error getting due payments: {e}")
            raise
    
    def update_next_run(self, payment_id: str, next_run: int, user_id: str = None) -> None:
        """
        Update the next execution time for a scheduled payment.
        
        Args:
            payment_id: Unique identifier of the payment
            next_run: New Unix timestamp for next execution
            user_id: Telegram user ID (optional, but improves performance)
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            if user_id:
                # If we know the user_id, directly update that user's record
                payments = self.get_payments(user_id)
                
                # Update the next_run for the matching payment
                updated_payments = []
                for payment in payments:
                    if payment.get('payment_id') == payment_id:
                        payment['next_run'] = next_run
                    updated_payments.append(payment)
                
                self.table.update_item(
                    Key={'telegram_user_id': user_id},
                    UpdateExpression='SET scheduled_payments = :payments',
                    ExpressionAttributeValues={
                        ':payments': updated_payments
                    }
                )
            else:
                # If we don't know the user_id, scan to find it
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, scheduled_payments'
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    payments = item.get('scheduled_payments', [])
                    
                    # Check if this user has the payment we're looking for
                    for payment in payments:
                        if payment.get('payment_id') == payment_id:
                            # Found it, update and save
                            updated_payments = []
                            for p in payments:
                                if p.get('payment_id') == payment_id:
                                    p['next_run'] = next_run
                                updated_payments.append(p)
                            
                            self.table.update_item(
                                Key={'telegram_user_id': user_id},
                                UpdateExpression='SET scheduled_payments = :payments',
                                ExpressionAttributeValues={
                                    ':payments': updated_payments
                                }
                            )
                            return
        except ClientError as e:
            print(f"Error updating next_run for payment {payment_id}: {e}")
            raise
    
    def delete_payment(self, payment_id: str, user_id: str = None) -> None:
        """
        Delete a scheduled payment.
        
        Args:
            payment_id: Unique identifier of the payment to delete
            user_id: Telegram user ID (optional, but improves performance)
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            if user_id:
                # If we know the user_id, directly update that user's record
                payments = self.get_payments(user_id)
                updated_payments = [p for p in payments if p.get('payment_id') != payment_id]
                
                self.table.update_item(
                    Key={'telegram_user_id': user_id},
                    UpdateExpression='SET scheduled_payments = :payments',
                    ExpressionAttributeValues={
                        ':payments': updated_payments
                    }
                )
            else:
                # If we don't know the user_id, scan to find it
                response = self.table.scan(
                    ProjectionExpression='telegram_user_id, scheduled_payments'
                )
                
                for item in response.get('Items', []):
                    user_id = item.get('telegram_user_id')
                    payments = item.get('scheduled_payments', [])
                    
                    # Check if this user has the payment we're looking for
                    for payment in payments:
                        if payment.get('payment_id') == payment_id:
                            # Found it, remove and save
                            updated_payments = [p for p in payments if p.get('payment_id') != payment_id]
                            
                            self.table.update_item(
                                Key={'telegram_user_id': user_id},
                                UpdateExpression='SET scheduled_payments = :payments',
                                ExpressionAttributeValues={
                                    ':payments': updated_payments
                                }
                            )
                            return
        except ClientError as e:
            print(f"Error deleting payment {payment_id}: {e}")
            raise
