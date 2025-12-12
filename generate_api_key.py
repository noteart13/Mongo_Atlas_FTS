import argparse
import base64
import secrets
import sys
from pathlib import Path


def generate_key(byte_len: int, fmt: str) -> str:
    if fmt == "urlsafe":
        return secrets.token_urlsafe(byte_len)
    if fmt == "hex":
        return secrets.token_hex(byte_len)
    if fmt == "base64":
        return base64.b64encode(secrets.token_bytes(byte_len)).decode("utf-8")
    raise ValueError("Unsupported format. Use: urlsafe | hex | base64")


def upsert_env(env_path: Path, key: str, value: str):
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate a random API key")
    parser.add_argument("--bytes", type=int, default=32, help="Number of random bytes")
    parser.add_argument("--format", type=str, default="urlsafe", choices=["urlsafe", "hex", "base64"], help="Output format")
    parser.add_argument("--env-file", type=str, default=None, help="Write/update API_KEY in the given .env file")
    args = parser.parse_args()

    key = generate_key(args.bytes, args.format)

    if args.env_file:
        upsert_env(Path(args.env_file), "API_KEY", key)

    # Print the key to stdout only
    sys.stdout.write(key)


if __name__ == "__main__":
    main()