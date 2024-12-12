from aiohttp import web
import os
from dotenv import load_dotenv
import json
import aiohttp

load_dotenv()

routes = web.RouteTableDef()

@routes.options('/api/generate')
async def options_handler(request):
    return web.Response(headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    })

@routes.post('/api/generate')
async def generate(request):
    try:
        # Add CORS headers to response
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        
        data = await request.json()
        
        # Get Leonardo API key
        api_key = os.getenv('LEONARDO_API_KEY')
        if not api_key:
            return web.json_response({"error": "API key not found"}, status=500, headers=headers)

        # Make request to Leonardo API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://cloud.leonardo.ai/api/rest/v1/generations',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    "prompt": data['idea'],
                    "modelId": "ac614f96-1082-45bf-be9d-757f2d31c174",
                    "width": 512,
                    "height": 512,
                    "num_images": 1,
                    "negative_prompt": "nsfw, bad quality, text, watermark",
                }
            ) as response:
                if response.status != 200:
                    return web.json_response(
                        {"error": f"Leonardo API error: {await response.text()}"}, 
                        status=500,
                        headers=headers
                    )
                
                result = await response.json()
                return web.json_response({
                    'imageUrl': result['generations'][0]['url'] if result.get('generations') else None,
                    'success': True
                }, headers=headers)

    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON"}, 
            status=400,
            headers=headers
        )
    except Exception as e:
        return web.json_response(
            {"error": str(e)}, 
            status=500,
            headers=headers
        )

# Serve static files
@routes.get('/')
async def serve_index(request):
    return web.FileResponse('index.html')

@routes.get('/home')
async def serve_home(request):
    return web.FileResponse('home.html')

@routes.get('/generator')
async def serve_generator(request):
    return web.FileResponse('generator.html')

@routes.get('/whitepaper')
async def serve_whitepaper(request):
    return web.FileResponse('whitepaper.html')

async def init_app():
    app = web.Application()
    app.add_routes(routes)
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    web.run_app(init_app(), port=port, host='0.0.0.0') 