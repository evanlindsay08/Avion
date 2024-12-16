from aiohttp import web
import os
from dotenv import load_dotenv
import json
import aiohttp
from PIL import Image
from io import BytesIO
import requests

load_dotenv()

routes = web.RouteTableDef()

# Add Discord webhook configuration
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

async def get_discord_message(message_id, channel_id):
    """Get message data from Discord"""
    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}',
            headers={'Authorization': f'Bot {discord_token}'}
        ) as response:
            if response.status != 200:
                raise ValueError("Failed to fetch Discord message")
            
            data = await response.json()
            
            # Get the first image attachment if any
            image_url = None
            if data.get('attachments'):
                image_url = data['attachments'][0]['url']
            elif data.get('embeds'):
                # Check embeds for Twitter preview
                for embed in data['embeds']:
                    if embed.get('image'):
                        image_url = embed['image']['url']
                        break
            
            return {
                'text': data['content'],
                'image_url': image_url
            }

async def process_discord_image(image_url):
    """Process image to 1:1 ratio"""
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    
    # Resize to 1:1 ratio
    size = min(img.size)
    left = (img.width - size) // 2
    top = (img.height - size) // 2
    
    img = img.crop((left, top, left + size, top + size))
    img = img.resize((512, 512))
    
    # Save temporarily
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    
    return output

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
