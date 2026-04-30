import argparse
import asyncio
import shlex
from pathlib import Path


DATA_DIR = Path("client_files")


async def tcp_client(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    print(f"Connected to {host}:{port}")

    async def send_cmd(cmd):
        writer.write((cmd + '\n').encode())
        await writer.drain()

    try:
        while True:
            cmd = input('> ')
            if not cmd:
                continue
            parts = shlex.split(cmd)
            if parts[0].upper() == 'WRITE' and len(parts) >= 2:
                # WRITE filename
                filename = parts[1]
                local_path = DATA_DIR / filename
                if not local_path.exists():
                    print(f"ERROR: local file not found: {local_path}")
                    continue
                try:
                    data = local_path.read_bytes()
                except OSError as exc:
                    print(f"ERROR: could not read {local_path}: {exc}")
                    continue
                await send_cmd(f"WRITE {filename} {len(data)}")
                # send raw data
                writer.write(data)
                writer.write(b"\n")
                await writer.drain()
                resp = await reader.readuntil(b"\n")
                print(resp.decode().strip())
            else:
                await send_cmd(cmd)
                # read a line response (LIST or ERROR or LEN ...)
                resp = await reader.readuntil(b"\n")
                text = resp.decode(errors='replace')
                if text.startswith('LEN '):
                    # read length and then raw data
                    try:
                        length = int(text.split()[1])
                    except Exception:
                        print(text)
                        continue
                    data = await reader.readexactly(length)
                    # consume trailing newline
                    await reader.readexactly(1)
                    print(f"---BEGIN FILE ({length} bytes)---")
                    print(data.decode(errors='replace'))
                    print(f"---END FILE---")
                else:
                    print(text.strip())
    except (EOFError, KeyboardInterrupt):
        print('\nClosing')
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=12345)
    args = parser.parse_args()

    asyncio.run(tcp_client(args.host, args.port))
