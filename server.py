import asyncio
import argparse
import os
import shutil
from pathlib import Path

DATA_DIR = Path("data_store")
DATA_DIR.mkdir(exist_ok=True)


def resolve_within_root(root: Path, current_dir: Path, target: str) -> Path:
    candidate = (current_dir / target).resolve()
    root_resolved = root.resolve()
    if candidate == root_resolved:
        return candidate
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise ValueError("path escapes data_store")
    return candidate


def format_relative_path(root: Path, path: Path) -> str:
    root_resolved = root.resolve()
    path_resolved = path.resolve()
    if path_resolved == root_resolved:
        return "."
    return str(path_resolved.relative_to(root_resolved)).replace('\\', '/')


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info('peername')
    print(f"Connection from {peer}")
    current_dir = DATA_DIR.resolve()

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

            if cmd == 'PWD':
                writer.write(f"OK {format_relative_path(DATA_DIR, current_dir)}\n".encode())
                await writer.drain()
            elif cmd == 'LIST':
                files = sorted(os.listdir(current_dir))
                # Prefix the list with a count so clients can read the full listing
                payload = f"LIST {len(files)}\n" + '\n'.join(files) + '\n'
                writer.write(payload.encode())
                await writer.drain()

            elif cmd == 'READ' and len(parts) >= 2:
                filename = parts[1]
                try:
                    path = resolve_within_root(DATA_DIR, current_dir, filename)
                except ValueError:
                    writer.write(b'ERROR: path escapes data_store\n')
                    await writer.drain()
                    continue
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

                try:
                    path = resolve_within_root(DATA_DIR, current_dir, filename)
                except ValueError:
                    writer.write(b'ERROR: path escapes data_store\n')
                    await writer.drain()
                    continue

                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)

                # Consume the trailing newline the client sends after the raw bytes.
                try:
                    await reader.readexactly(1)
                except asyncio.IncompleteReadError:
                    pass

                writer.write(b'OK\n')
                await writer.drain()

            elif cmd == 'CD' and len(parts) >= 2:
                target = parts[1]
                try:
                    new_dir = resolve_within_root(DATA_DIR, current_dir, target)
                except ValueError:
                    writer.write(b'ERROR: path escapes data_store\n')
                    await writer.drain()
                    continue

                if not new_dir.exists() or not new_dir.is_dir():
                    writer.write(b'ERROR: directory not found\n')
                    await writer.drain()
                    continue

                current_dir = new_dir
                writer.write(f"OK {format_relative_path(DATA_DIR, current_dir)}\n".encode())
                await writer.drain()

            elif cmd == 'MKDIR' and len(parts) >= 2:
                target = parts[1]
                try:
                    new_dir = resolve_within_root(DATA_DIR, current_dir, target)
                except ValueError:
                    writer.write(b'ERROR: path escapes data_store\n')
                    await writer.drain()
                    continue

                new_dir.mkdir(parents=True, exist_ok=False)
                writer.write(f"OK {format_relative_path(DATA_DIR, new_dir)}\n".encode())
                await writer.drain()

            elif cmd == 'MV' and len(parts) >= 3:
                src_name = parts[1]
                dst_name = parts[2]
                try:
                    src = resolve_within_root(DATA_DIR, current_dir, src_name)
                    dst = resolve_within_root(DATA_DIR, current_dir, dst_name)
                except ValueError:
                    writer.write(b'ERROR: path escapes data_store\n')
                    await writer.drain()
                    continue

                if not src.exists():
                    writer.write(b'ERROR: source not found\n')
                    await writer.drain()
                    continue

                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                writer.write(f"OK {format_relative_path(DATA_DIR, dst)}\n".encode())
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
