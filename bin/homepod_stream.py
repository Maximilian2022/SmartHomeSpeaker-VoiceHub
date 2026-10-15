import asyncio
import sys
import os
import pyatv

async def stream(target, audio_path):
    if not os.path.exists(audio_path):
        print(f"Error: file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.get_event_loop()
    
    # IPアドレスかIDかで検索
    hosts = [target] if "." in target else None
    atvs = await pyatv.scan(loop, hosts=hosts, timeout=3)
    
    selected = None
    for a in atvs:
        if a.identifier == target or str(a.address) == target or a.name == target:
            selected = a
            break

    if not selected and atvs:
        # hosts 指定時
        selected = atvs[0]

    if not selected:
        print(f"Error: device not found for target: {target}", file=sys.stderr)
        sys.exit(2)

    atv = await pyatv.connect(selected, loop)
    try:
        await atv.stream.stream_file(audio_path)
    finally:
        atv.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python homepod_stream.py <target_ip_or_id> <audio_path>")
        sys.exit(1)
        
    target = sys.argv[1]
    audio_path = sys.argv[2]
    asyncio.run(stream(target, audio_path))
    sys.exit(0)
