import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TransactionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("transactions", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("transactions", self.channel_name)

    async def receive(self, text_data):
        pass  # we don't need to receive messages

    async def transaction_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event['data']))