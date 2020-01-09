from websockets.server import WebSocketServerProtocol as WebSocketConn
from websockets.exceptions import ConnectionClosedError


class Bot:
    def __init__(self,
                 idx: int,
                 remote_address: str,
                 ws: WebSocketConn,
                 user: str):
        self.idx = idx
        self.remote_address = remote_address
        self.ws = ws
        self.user = user

    def __str__(self):
        return f"Bot {self.remote_address}, idx: {self.idx}, user: {self.user}"

    async def send_command(self, command: str):
        try:
            await self.ws.send(command)
            return await self.ws.recv()
        except ConnectionClosedError:
            return False
