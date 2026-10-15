import asyncio
import json
import sys
import pyatv

async def main():
    atvs = await pyatv.scan(asyncio.get_event_loop(), timeout=3)
    results = []
    seen = set()
    for a in atvs:
        if a.identifier in seen:
            continue
        seen.add(a.identifier)
        
        model = str(a.device_info.model or '')
        name = str(a.name or '')
        is_hp = 'HomePod' in model or 'HomePod' in name or 'AudioAccessory' in str(a.device_info)
        is_atv = 'Apple TV' in model or 'AppleTV' in str(a.device_info)
        
        if not is_hp and not is_atv:
            continue
            
        model_name = 'Apple HomePod'
        if 'Mini' in model or 'mini' in name:
            model_name = 'Apple HomePod mini'
        elif 'gen 2' in model or 'Gen 2' in model:
            model_name = 'Apple HomePod (第2世代)'
        elif is_atv:
            model_name = 'Apple TV'

        target_id = a.identifier
        address = str(a.address)

        results.append({
            'id': f"homepod_{target_id.replace(':', '_').replace('-', '_')}",
            'name': name,
            'rawName': name,
            'ip': f"homepod:{target_id}",
            'rawIp': address,
            'mac': target_id,
            'model': model_name,
            'type': 'homepod'
        })
    print(json.dumps(results, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(main())
