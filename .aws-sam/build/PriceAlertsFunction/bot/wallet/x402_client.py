"""
x402 Protocol client for blockchain transactions and micropayments.

This module provides a client for interacting with the x402 payment protocol
on Base blockchain. It supports ETH/USDC transfers, token swaps, and
micropayment-based access to paywalled content.
"""

import time
from typing import Dict, Optional, Any
import requests


# Token contract addresses on Base mainnet (placeholder values)
TOKEN_ADDRESSES = {
    'ETH': '0x0000000000000000000000000000000000000000',  # Native ETH
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # USDC on Base
    'BTC': '0x...',  # Placeholder for wrapped BTC
    'SOL': '0x...',  # Placeholder for wrapped SOL
}

# Network configurations
NETWORKS = {
    'base-mainnet': {
        'rpc_url': 'https://mainnet.base.org',
        'chain_id': 8453,
        'explorer': 'https://basescan.org'
    },
    'base-sepolia': {
        'rpc_url': 'https://sepolia.base.org',
        'chain_id': 84532,
        'explorer': 'https://sepolia.basescan.org'
    },
    'optimism': {
        'rpc_url': 'https://mainnet.optimism.io',
        'chain_id': 10,
        'explorer': 'https://optimistic.etherscan.io'
    }
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class X402Error(Exception):
    """Base exception for x402 protocol errors."""
    pass


class InsufficientBalanceError(X402Error):
    """Raised when wallet has insufficient balance for transaction."""
    pass


class NetworkError(X402Error):
    """Raised when network communication fails."""
    pass


class TransactionError(X402Error):
    """Raised when transaction execution fails."""
    pass


class X402Client:
    """
    Client for interacting with the x402 payment protocol.
    
    This client provides methods to execute blockchain transactions including
    token transfers, swaps, and micropayments for paywalled content access.
    
    Attributes:
        private_key: Private key for signing transactions
        network: Network identifier (e.g., 'base-mainnet')
        rpc_url: RPC endpoint URL for the selected network
        chain_id: Chain ID for the selected network
    """
    
    def __init__(self, private_key: str, network: str = 'base-mainnet'):
        """
        Initialize the x402 protocol client.
        
        Args:
            private_key: Private key for signing transactions
            network: Network identifier (default: 'base-mainnet')
            
        Raises:
            ValueError: If network is not supported
        """
        if network not in NETWORKS:
            supported = ', '.join(NETWORKS.keys())
            raise ValueError(f"Unsupported network: {network}. Supported networks: {supported}")
        
        self.private_key = private_key
        self.network = network
        self.rpc_url = NETWORKS[network]['rpc_url']
        self.chain_id = NETWORKS[network]['chain_id']
        self.explorer = NETWORKS[network]['explorer']
    
    def _make_rpc_request(self, method: str, params: list, retry_count: int = 0) -> Any:
        """
        Make a JSON-RPC request to the blockchain node.
        
        Args:
            method: RPC method name
            params: List of parameters for the method
            retry_count: Current retry attempt number
            
        Returns:
            RPC response result
            
        Raises:
            NetworkError: If request fails after all retries
        """
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': method,
            'params': params
        }
        
        try:
            response = requests.post(
                self.rpc_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown RPC error')
                raise NetworkError(f"RPC error: {error_msg}")
            
            return result.get('result')
            
        except requests.exceptions.Timeout:
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (retry_count + 1))
                return self._make_rpc_request(method, params, retry_count + 1)
            raise NetworkError(f"RPC request timed out after {MAX_RETRIES} retries")
            
        except requests.exceptions.RequestException as e:
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (retry_count + 1))
                return self._make_rpc_request(method, params, retry_count + 1)
            raise NetworkError(f"RPC request failed: {str(e)}")
            
        except Exception as e:
            raise NetworkError(f"Unexpected error in RPC request: {str(e)}")
    
    def _get_balance(self, address: str, token: str) -> float:
        """
        Get token balance for an address.
        
        Args:
            address: Wallet address
            token: Token symbol (ETH or USDC)
            
        Returns:
            Token balance as float
            
        Raises:
            NetworkError: If balance check fails
        """
        try:
            if token == 'ETH':
                # Get native ETH balance
                balance_wei = self._make_rpc_request('eth_getBalance', [address, 'latest'])
                balance = int(balance_wei, 16) / 1e18
            else:
                # Get ERC20 token balance (simplified - would need actual contract call)
                # For now, return a placeholder
                balance = 0.0
            
            return balance
            
        except Exception as e:
            raise NetworkError(f"Failed to get balance: {str(e)}")
    
    def send_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        token: str = 'ETH'
    ) -> str:
        """
        Execute a token transfer transaction.
        
        This method sends ETH or USDC from one address to another on the
        configured blockchain network.
        
        Args:
            from_address: Source wallet address
            to_address: Destination wallet address
            amount: Amount to send
            token: Token symbol ('ETH' or 'USDC')
            
        Returns:
            Transaction hash
            
        Raises:
            InsufficientBalanceError: If sender has insufficient balance
            NetworkError: If network communication fails
            TransactionError: If transaction execution fails
            ValueError: If token is not supported
            
        Examples:
            >>> client = X402Client(private_key="0x...")
            >>> tx_hash = client.send_transaction(
            ...     from_address="0xabc...",
            ...     to_address="0xdef...",
            ...     amount=0.1,
            ...     token="ETH"
            ... )
            >>> print(f"Transaction hash: {tx_hash}")
            Transaction hash: 0x123...
        """
        if token not in ['ETH', 'USDC']:
            raise ValueError(f"Unsupported token: {token}. Supported tokens: ETH, USDC")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        try:
            # Check balance
            balance = self._get_balance(from_address, token)
            if balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient {token} balance. Available: {balance}, Required: {amount}"
                )
            
            # Build transaction
            if token == 'ETH':
                tx_hash = self._send_eth_transaction(from_address, to_address, amount)
            else:
                tx_hash = self._send_erc20_transaction(from_address, to_address, amount, token)
            
            return tx_hash
            
        except InsufficientBalanceError:
            raise
        except NetworkError:
            raise
        except Exception as e:
            raise TransactionError(f"Transaction failed: {str(e)}")
    
    def _send_eth_transaction(self, from_address: str, to_address: str, amount: float) -> str:
        """
        Send native ETH transaction.
        
        Args:
            from_address: Source address
            to_address: Destination address
            amount: Amount in ETH
            
        Returns:
            Transaction hash
        """
        # Convert amount to wei
        amount_wei = int(amount * 1e18)
        
        # Get nonce
        nonce = self._make_rpc_request('eth_getTransactionCount', [from_address, 'latest'])
        
        # Get gas price
        gas_price = self._make_rpc_request('eth_gasPrice', [])
        
        # Build transaction object
        tx = {
            'from': from_address,
            'to': to_address,
            'value': hex(amount_wei),
            'gas': hex(21000),  # Standard gas limit for ETH transfer
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': self.chain_id
        }
        
        # Sign and send transaction (simplified - would need actual signing)
        # In production, this would use web3.py or eth_account to sign
        tx_hash = self._sign_and_send_transaction(tx)
        
        return tx_hash
    
    def _send_erc20_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        token: str
    ) -> str:
        """
        Send ERC20 token transaction.
        
        Args:
            from_address: Source address
            to_address: Destination address
            amount: Amount in tokens
            token: Token symbol
            
        Returns:
            Transaction hash
        """
        # Get token contract address
        token_address = TOKEN_ADDRESSES.get(token)
        if not token_address:
            raise ValueError(f"Token contract address not found for {token}")
        
        # Convert amount based on token decimals (USDC uses 6 decimals)
        decimals = 6 if token == 'USDC' else 18
        amount_units = int(amount * (10 ** decimals))
        
        # Build ERC20 transfer call data
        # transfer(address,uint256) = 0xa9059cbb
        method_id = '0xa9059cbb'
        to_address_padded = to_address[2:].zfill(64)  # Remove 0x and pad to 32 bytes
        amount_hex = hex(amount_units)[2:].zfill(64)  # Convert to hex and pad
        data = method_id + to_address_padded + amount_hex
        
        # Get nonce
        nonce = self._make_rpc_request('eth_getTransactionCount', [from_address, 'latest'])
        
        # Get gas price
        gas_price = self._make_rpc_request('eth_gasPrice', [])
        
        # Build transaction object
        tx = {
            'from': from_address,
            'to': token_address,
            'value': '0x0',
            'data': data,
            'gas': hex(100000),  # Higher gas limit for token transfer
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': self.chain_id
        }
        
        # Sign and send transaction
        tx_hash = self._sign_and_send_transaction(tx)
        
        return tx_hash
    
    def _sign_and_send_transaction(self, tx: Dict) -> str:
        """
        Sign and broadcast a transaction.
        
        Args:
            tx: Transaction object
            
        Returns:
            Transaction hash
            
        Note:
            This is a simplified implementation. In production, this would use
            proper transaction signing with eth_account or web3.py.
        """
        # In production, this would:
        # 1. Sign the transaction with the private key
        # 2. Serialize the signed transaction
        # 3. Broadcast via eth_sendRawTransaction
        
        # For now, return a mock transaction hash
        # This would be replaced with actual implementation
        mock_tx_hash = f"0x{'0' * 64}"
        
        print(f"[x402] Transaction prepared: {tx}")
        print(f"[x402] Mock transaction hash: {mock_tx_hash}")
        
        return mock_tx_hash
    
    def swap_tokens(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        from_address: str,
        min_output: Optional[float] = None
    ) -> str:
        """
        Execute a token swap transaction.
        
        This method swaps one cryptocurrency for another using a DEX
        (decentralized exchange) on the configured network.
        
        Args:
            from_token: Source token symbol (ETH, USDC, BTC, SOL)
            to_token: Destination token symbol (ETH, USDC, BTC, SOL)
            amount: Amount of source token to swap
            from_address: Address executing the swap
            min_output: Minimum acceptable output amount (slippage protection)
            
        Returns:
            Transaction hash
            
        Raises:
            InsufficientBalanceError: If sender has insufficient balance
            NetworkError: If network communication fails
            TransactionError: If swap execution fails
            ValueError: If tokens are not supported or same
            
        Examples:
            >>> client = X402Client(private_key="0x...")
            >>> tx_hash = client.swap_tokens(
            ...     from_token="USDC",
            ...     to_token="ETH",
            ...     amount=100.0,
            ...     from_address="0xabc..."
            ... )
            >>> print(f"Swap transaction: {tx_hash}")
            Swap transaction: 0x456...
        """
        supported_tokens = {'ETH', 'USDC', 'BTC', 'SOL'}
        
        if from_token not in supported_tokens:
            raise ValueError(f"Unsupported from_token: {from_token}")
        
        if to_token not in supported_tokens:
            raise ValueError(f"Unsupported to_token: {to_token}")
        
        if from_token == to_token:
            raise ValueError("Cannot swap token to itself")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        try:
            # Check balance
            balance = self._get_balance(from_address, from_token)
            if balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient {from_token} balance. Available: {balance}, Required: {amount}"
                )
            
            # Get estimated output amount
            estimated_output = self._get_swap_quote(from_token, to_token, amount)
            
            # Apply slippage protection
            if min_output is None:
                min_output = estimated_output * 0.99  # 1% slippage tolerance
            
            if estimated_output < min_output:
                raise TransactionError(
                    f"Estimated output {estimated_output} is below minimum {min_output}"
                )
            
            # Execute swap
            tx_hash = self._execute_swap(
                from_token,
                to_token,
                amount,
                min_output,
                from_address
            )
            
            return tx_hash
            
        except InsufficientBalanceError:
            raise
        except NetworkError:
            raise
        except Exception as e:
            raise TransactionError(f"Swap failed: {str(e)}")
    
    def _get_swap_quote(self, from_token: str, to_token: str, amount: float) -> float:
        """
        Get estimated output amount for a token swap.
        
        Args:
            from_token: Source token
            to_token: Destination token
            amount: Input amount
            
        Returns:
            Estimated output amount
        """
        # In production, this would query a DEX aggregator or AMM pool
        # For now, return a mock estimate based on simple conversion
        
        # Mock exchange rates (for demonstration)
        rates = {
            'ETH': 2000.0,  # ETH price in USD
            'USDC': 1.0,    # USDC price in USD
            'BTC': 40000.0, # BTC price in USD
            'SOL': 100.0    # SOL price in USD
        }
        
        from_value_usd = amount * rates.get(from_token, 1.0)
        estimated_output = from_value_usd / rates.get(to_token, 1.0)
        
        return estimated_output
    
    def _execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        min_output: float,
        from_address: str
    ) -> str:
        """
        Execute the swap transaction on-chain.
        
        Args:
            from_token: Source token
            to_token: Destination token
            amount: Input amount
            min_output: Minimum output amount
            from_address: Sender address
            
        Returns:
            Transaction hash
        """
        # In production, this would:
        # 1. Build swap transaction data for DEX router
        # 2. Approve token spending if needed
        # 3. Execute swap through router contract
        
        # For now, return a mock transaction hash
        mock_tx_hash = f"0x{'1' * 64}"
        
        print(f"[x402] Swap prepared: {amount} {from_token} -> {to_token}")
        print(f"[x402] Min output: {min_output} {to_token}")
        print(f"[x402] Mock swap hash: {mock_tx_hash}")
        
        return mock_tx_hash
    
    def fetch_paywalled_content(self, url: str, from_address: str) -> str:
        """
        Fetch paywalled content by paying x402 micropayment.
        
        This method pays the required micropayment to access paywalled content
        and retrieves the full article text.
        
        Args:
            url: URL of the paywalled content
            from_address: Address to pay from
            
        Returns:
            Full article text content
            
        Raises:
            InsufficientBalanceError: If sender has insufficient balance for payment
            NetworkError: If network communication fails
            TransactionError: If payment or content retrieval fails
            ValueError: If URL is invalid
            
        Examples:
            >>> client = X402Client(private_key="0x...")
            >>> content = client.fetch_paywalled_content(
            ...     url="https://example.com/article",
            ...     from_address="0xabc..."
            ... )
            >>> print(content[:100])
            This is the full article text...
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")
        
        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        
        try:
            # Step 1: Query x402 payment requirements
            payment_info = self._get_payment_info(url)
            
            if not payment_info:
                raise TransactionError("Failed to get payment information for URL")
            
            amount = payment_info.get('amount', 0.0)
            token = payment_info.get('token', 'ETH')
            recipient = payment_info.get('recipient')
            
            if not recipient:
                raise TransactionError("No payment recipient found for URL")
            
            # Step 2: Check balance
            balance = self._get_balance(from_address, token)
            if balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient {token} balance for micropayment. "
                    f"Required: {amount}, Available: {balance}"
                )
            
            # Step 3: Execute micropayment
            tx_hash = self.send_transaction(
                from_address=from_address,
                to_address=recipient,
                amount=amount,
                token=token
            )
            
            # Step 4: Retrieve content with payment proof
            content = self._retrieve_content(url, tx_hash)
            
            return content
            
        except InsufficientBalanceError:
            raise
        except NetworkError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to fetch paywalled content: {str(e)}")
    
    def _get_payment_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Query x402 payment requirements for a URL.
        
        Args:
            url: Content URL
            
        Returns:
            Payment information dictionary or None
        """
        try:
            # In production, this would query the x402 protocol endpoint
            # to get payment requirements for the URL
            
            # Mock payment info
            payment_info = {
                'amount': 0.001,  # 0.001 ETH or equivalent
                'token': 'ETH',
                'recipient': '0x' + '0' * 40,  # Mock recipient address
                'content_hash': '0x' + 'a' * 64  # Mock content hash
            }
            
            return payment_info
            
        except Exception as e:
            print(f"[x402] Failed to get payment info: {e}")
            return None
    
    def _retrieve_content(self, url: str, payment_tx_hash: str) -> str:
        """
        Retrieve paywalled content after payment.
        
        Args:
            url: Content URL
            payment_tx_hash: Transaction hash of the payment
            
        Returns:
            Article content text
        """
        try:
            # In production, this would:
            # 1. Verify payment transaction on-chain
            # 2. Request content from x402 gateway with payment proof
            # 3. Decrypt and return content
            
            # Mock content retrieval
            mock_content = f"""
# Article Title

This is the full text of the paywalled article retrieved via x402 micropayment.

Payment transaction: {payment_tx_hash}
Source URL: {url}

[Article content would appear here in production...]

The x402 protocol enables seamless micropayments for content access without
requiring subscriptions or account creation.
"""
            
            return mock_content.strip()
            
        except Exception as e:
            raise TransactionError(f"Failed to retrieve content: {str(e)}")
    
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get the status of a transaction.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction status information
            
        Raises:
            NetworkError: If status check fails
        """
        try:
            receipt = self._make_rpc_request('eth_getTransactionReceipt', [tx_hash])
            
            if not receipt:
                return {
                    'status': 'pending',
                    'confirmed': False
                }
            
            status = receipt.get('status')
            success = status == '0x1' if status else False
            
            return {
                'status': 'success' if success else 'failed',
                'confirmed': True,
                'block_number': int(receipt.get('blockNumber', '0x0'), 16),
                'gas_used': int(receipt.get('gasUsed', '0x0'), 16)
            }
            
        except Exception as e:
            raise NetworkError(f"Failed to get transaction status: {str(e)}")
    
    def get_explorer_url(self, tx_hash: str) -> str:
        """
        Get block explorer URL for a transaction.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Block explorer URL
        """
        return f"{self.explorer}/tx/{tx_hash}"
