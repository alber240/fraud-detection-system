"""
WebSocket consumers for real-time updates
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from banking.models import BankingTransaction
from prediction.models import FraudAlert


class TransactionConsumer(AsyncWebsocketConsumer):
    """Handles real-time transaction updates for staff dashboard"""
    
    async def connect(self):
        # Join transaction group
        await self.channel_layer.group_add(
            'transactions_group',
            self.channel_name
        )
        await self.accept()
        print(f"WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        # Leave transaction group
        await self.channel_layer.group_discard(
            'transactions_group',
            self.channel_name
        )
        print(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """Handle messages from client"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except Exception as e:
            print(f"WebSocket receive error: {e}")

    async def transaction_update(self, event):
        """Send transaction update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_transaction',
            'transaction': event['transaction']
        }))


class AlertConsumer(AsyncWebsocketConsumer):
    """Handles real-time alert updates"""
    
    async def connect(self):
        await self.channel_layer.group_add(
            'alerts_group',
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            'alerts_group',
            self.channel_name
        )

    async def alert_update(self, event):
        """Send alert update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_alert',
            'alert': event['alert']
        }))