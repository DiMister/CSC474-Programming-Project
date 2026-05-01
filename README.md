Project: Simple File Server (TCP)

What this provides
- `server.py`: an asyncio-based TCP server exposing a minimal file store (LIST/READ/WRITE).
- `client.py`: a simple CLI client to interact with the server (LIST, READ, WRITE, PWD, CD, MKDIR, MV).

Protocol (text-based)
- LIST\n
  Server responds with file names separated by newlines and a final newline.

- READ <filename>\n
  Server responds with: `LEN <bytes>\n` then the raw file bytes, then a trailing newline.

- WRITE <filename> <len>\n<raw-bytes>
  Client reads `data_store/<filename>` locally, sends WRITE with the expected length, then raw bytes (server writes them to `data_store/<filename>`).

- PWD\n
  Prints the server's current directory, relative to `data_store`.

- CD <dir>\n
  Changes the server's current directory. Paths stay inside `data_store`.

- MKDIR <dir>\n
  Creates a new directory relative to the server's current directory.

- MV <source> <destination>\n
  Moves or renames a file/directory relative to the server's current directory.

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
- `PWD`
- `CD subfolder`
- `MKDIR notes`
- `MV old.txt archive/old.txt`
- `READ myfile.txt`
- `WRITE myfile.txt`
