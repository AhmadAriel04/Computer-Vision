
import asyncio
import json
from pathlib import Path

import websockets


async def main():
    image_path = Path("test_face.jpeg")

    if not image_path.exists():
        print(f"File tidak ditemukan: {image_path.resolve()}")
        return

    uri = "ws://127.0.0.1:8000/ws/detect"

    try:
        async with websockets.connect(uri) as ws:
            await ws.send(image_path.read_bytes())

            response = await ws.recv()
            result = json.loads(response)

            print(json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            ))

    except Exception as exc:
        print(f"Pengujian gagal: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
