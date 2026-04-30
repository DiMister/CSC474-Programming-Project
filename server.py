import asyncio
import argparse
import os
from pathlib import Path

DATA_DIR = Path("data_store")
DATA_DIR.mkdir(exist_ok=True)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info('peername')
    print(f"Connection from {peer}")

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            line = line.decode('utf-8', errors='replace').strip()
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].upper()

            if cmd == 'LIST':
                files = os.listdir(DATA_DIR)
                # Prefix the list with a count so clients can read the full listing
                payload = f"LIST {len(files)}\n" + '\n'.join(files) + '\n'
                writer.write(payload.encode())
                await writer.drain()

            elif cmd == 'READ' and len(parts) >= 2:
                filename = parts[1]
                path = DATA_DIR / filename
                if not path.exists():
                    writer.write(b'ERROR: not found\n')
                    await writer.drain()
                    continue

                data = path.read_bytes()
                writer.write(f"LEN {len(data)}\n".encode())
                writer.write(data)
                writer.write(b"\n")
                await writer.drain()

            elif cmd == 'WRITE' and len(parts) >= 3:
                filename = parts[1]
                try:
                    length = int(parts[2])
                except ValueError:
                    writer.write(b'ERROR: bad length\n')
                    await writer.drain()
                    continue

                try:
                    data = await reader.readexactly(length)
                except asyncio.IncompleteReadError:
                    writer.write(b'ERROR: incomplete write payload\n')
                    await writer.drain()
                    break

                path = DATA_DIR / filename
                path.write_bytes(data)

                # Consume the trailing newline the client sends after the raw bytes.
                try:
                    await reader.readexactly(1)
                except asyncio.IncompleteReadError:
                    pass

                writer.write(b'OK\n')
                await writer.drain()

            else:
                writer.write(b'ERROR: unknown command\n')
                await writer.drain()

    except Exception as e:
        writer.write(f'ERROR: {e}\n'.encode())
        try:
            await writer.drain()
        except Exception:
            pass
    finally:
        writer.close()
        await writer.wait_closed()


async def main(host, port):
    server = await asyncio.start_server(handle_client, host, port)
    print(f"TCP server listening on {host}:{port}")
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=12345)
    args = parser.parse_args()
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print('Server shutting down')
