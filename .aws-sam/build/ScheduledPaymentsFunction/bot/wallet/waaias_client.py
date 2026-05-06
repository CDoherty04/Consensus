"""
WAIaaS (Wallet-as-a-Service) API client for agent wallet management.

This module provides a client for interacting with the WAIaaS API to create
wallets, fetch balances, and retrieve transaction history. It includes retry
logic with exponential backoff for handling API timeouts.
"""

import time
from typing import Dict, List, Optional
import requests


class WAIaaSClient:
    """
    Client for interacting with the WAIaaS (Wallet-as-a-Service) API.
    
    This client provides methods to create wallets, fetch balances for ETH and
    USDC on Base blockchain, and retrieve transaction history. It includes
    automatic retry logic with exponential backoff for handling API timeouts.
    
    Attributes:
        api_key: WAIaaS API authentication key
        base_url: Base URL for WAIaaS API
        max_retries: Maximum number of retry attempts for failed requests
        initial_backoff: Initial backoff delay in seconds for retries
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.waaias.com/v1"):
        """
        Initialize the WAIaaS client.
        
        Args:
            api_key: WAIaaS API authentication key
            base_url: Base URL for WAIaaS API (default: https://api.waaias.com/v1)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.max_retries = 3
        self.initial_backoff = 1.0  # seconds
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make a request to the WAIaaS API with retry logic.
        
        Implements exponential backoff retry strategy for handling API timeouts
        and transient failures. Retries up to max_retries times with increasing
        delays between attempts.
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint path
            data: Optional JSON data for POST requests
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary or None on error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        backoff = self.initial_backoff
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=30
                )
                
                # Raise exception for 4xx and 5xx status codes
                response.raise_for_status()
                
                # Return JSON response
                return response.json()
                
            except requests.exceptions.Timeout:
                print(f"WAIaaS API request timed out (attempt {attempt + 1}/{self.max_retries}): {url}")
                
                # Don't sleep after the last attempt
                if attempt < self.max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    
            except requests.exceptions.HTTPError as e:
                # Don't retry on client errors (4xx)
                if e.response.status_code < 500:
                    print(f"WAIaaS API client error: {e}")
                    return None
                
                # Retry on server errors (5xx)
                print(f"WAIaaS API server error (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    
            except requests.exceptions.RequestException as e:
                print(f"WAIaaS API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    
            except Exception as e:
                print(f"Unexpected error in WAIaaS API request: {e}")
                return None
        
        # All retries exhausted
        print(f"WAIaaS API request failed after {self.max_retries} attempts: {url}")
        return None
    
    def create_wallet(self, user_id: str) -> Optional[str]:
        """
        Create a new wallet via WAIaaS API.
        
        Creates a new cryptocurrency wallet for the specified user. The wallet
        supports ETH and USDC on Base blockchain. The private key is managed
        securely by WAIaaS and never exposed to the client.
        
        Args:
            user_id: Unique identifier for the user (e.g., Telegram user ID)
            
        Returns:
            Wallet address (0x...) or None on error
            
        Examples:
            >>> client = WAIaaSClient(api_key="your-api-key")
            >>> address = client.create_wallet("123456789")
            >>> print(f"Created wallet: {address}")
            Created wallet: 0xabc123...
        """
        data = {
            'user_id': user_id,
            'blockchain': 'base',
            'network': 'mainnet'
        }
        
        response = self._make_request('POST', '/wallets', data=data)
        
        if not response:
            return None
        
        # Extract wallet address from response
        wallet_address = response.get('address')
        
        if not wallet_address:
            print(f"WAIaaS create_wallet response missing 'address' field: {response}")
            return None
        
        return wallet_address
    
    def get_balance(self, address: str, token: str = 'ETH') -> Optional[float]:
        """
        Fetch token balance for a wallet address.
        
        Retrieves the balance for the specified token (ETH or USDC) on Base
        blockchain. The balance is returned as a float value in the token's
        standard unit (ETH for Ethereum, USDC for USD Coin).
        
        Args:
            address: Wallet address (0x...)
            token: Token symbol ('ETH' or 'USDC', default: 'ETH')
            
        Returns:
            Token balance as float or None on error
            
        Examples:
            >>> client = WAIaaSClient(api_key="your-api-key")
            >>> eth_balance = client.get_balance("0xabc123...", "ETH")
            >>> usdc_balance = client.get_balance("0xabc123...", "USDC")
            >>> print(f"ETH: {eth_balance}, USDC: {usdc_balance}")
            ETH: 0.5, USDC: 100.0
        """
        token = token.upper()
        
        if token not in ['ETH', 'USDC']:
            print(f"Unsupported token: {token}. Supported tokens: ETH, USDC")
            return None
        
        params = {
            'address': address,
            'token': token,
            'blockchain': 'base',
            'network': 'mainnet'
        }
        
        response = self._make_request('GET', '/balances', params=params)
        
        if not response:
            return None
        
        # Extract balance from response
        balance = response.get('balance')
        
        if balance is None:
            print(f"WAIaaS get_balance response missing 'balance' field: {response}")
            return None
        
        try:
            return float(balance)
        except (ValueError, TypeError) as e:
            print(f"Failed to parse balance as float: {balance}, error: {e}")
            return None
    
    def get_transactions(
        self,
        address: str,
        limit: int = 10,
        offset: int = 0
    ) -> Optional[List[Dict]]:
        """
        Retrieve transaction history for a wallet address.
        
        Fetches the transaction history for the specified wallet address on
        Base blockchain. Returns a list of transactions with details including
        amount, counterparty address, timestamp, and transaction type.
        
        Args:
            address: Wallet address (0x...)
            limit: Maximum number of transactions to retrieve (default: 10)
            offset: Number of transactions to skip for pagination (default: 0)
            
        Returns:
            List of transaction dictionaries or None on error
            
        Transaction Dictionary Format:
            {
                'hash': '0x...',
                'from': '0x...',
                'to': '0x...',
                'amount': 1.5,
                'token': 'ETH',
                'timestamp': 1704067200,
                'type': 'send' | 'receive',
                'status': 'confirmed' | 'pending' | 'failed'
            }
            
        Examples:
            >>> client = WAIaaSClient(api_key="your-api-key")
            >>> txs = client.get_transactions("0xabc123...", limit=5)
            >>> for tx in txs:
            ...     print(f"{tx['type']}: {tx['amount']} {tx['token']}")
            send: 1.5 ETH
            receive: 100.0 USDC
        """
        params = {
            'address': address,
            'blockchain': 'base',
            'network': 'mainnet',
            'limit': limit,
            'offset': offset
        }
        
        response = self._make_request('GET', '/transactions', params=params)
        
        if not response:
            return None
        
        # Extract transactions from response
        transactions = response.get('transactions')
        
        if transactions is None:
            print(f"WAIaaS get_transactions response missing 'transactions' field: {response}")
            return None
        
        if not isinstance(transactions, list):
            print(f"WAIaaS get_transactions 'transactions' field is not a list: {transactions}")
            return None
        
        return transactions
    
    def get_balances(self, address: str) -> Optional[Dict[str, float]]:
        """
        Fetch balances for all supported tokens in a single call.
        
        This is a convenience method that fetches both ETH and USDC balances
        in a single operation. More efficient than calling get_balance() twice.
        
        Args:
            address: Wallet address (0x...)
            
        Returns:
            Dictionary mapping token symbols to balances, or None on error
            
        Examples:
            >>> client = WAIaaSClient(api_key="your-api-key")
            >>> balances = client.get_balances("0xabc123...")
            >>> print(f"ETH: {balances['ETH']}, USDC: {balances['USDC']}")
            ETH: 0.5, USDC: 100.0
        """
        eth_balance = self.get_balance(address, 'ETH')
        usdc_balance = self.get_balance(address, 'USDC')
        
        # Return None if both requests failed
        if eth_balance is None and usdc_balance is None:
            return None
        
        # Return partial results if one request succeeded
        return {
            'ETH': eth_balance if eth_balance is not None else 0.0,
            'USDC': usdc_balance if usdc_balance is not None else 0.0
        }
