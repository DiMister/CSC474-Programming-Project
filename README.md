Project: Simple File Server (TCP)

What this provides
- `server.py`: an asyncio-based TCP server exposing a minimal file store (LIST/READ/WRITE).
- `client.py`: a simple CLI client to interact with the server (LIST, READ, WRITE).

Protocol (text-based)
- LIST\n
  Server responds with file names separated by newlines and a final newline.

- READ <filename>\n
  Server responds with: `LEN <bytes>\n` then the raw file bytes, then a trailing newline.

- WRITE <filename> <len>\n<raw-bytes>
  Client reads `data_store/<filename>` locally, sends WRITE with the expected length, then raw bytes (server writes them to `data_store/<filename>`).

Usage

1) Start server (listen on all interfaces):

```powershell
python .\server.py --host 0.0.0.0 --port 12345
```

2) Start client (connect to server IP):

```powershell
python .\client.py --host 127.0.0.1 --port 12345
```

Type commands at the prompt, for example:
- `LIST`
- `READ myfile.txt`
- `WRITE myfile.txt`
