from aiohttp import web, ClientSession
import json
import os
from dotenv import load_dotenv
import pathlib

load_dotenv()

routes = web.RouteTableDef()
BASE_DIR = pathlib.Path(__file__).parent
LEONARDO_API_KEY = os.getenv('LEONARDO_API_KEY')
LEONARDO_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

ART_STYLE_PROMPTS = {
    '3d': """3D rendered style, volumetric lighting, subsurface scattering,
        realistic textures, ambient occlusion, ray-traced reflections""",
    'anime': """anime art style, manga-inspired, cel-shaded, vibrant colors,
        kawaii aesthetic, clean linework, anime character design""",
    'minimalist': """minimalist design, clean lines, simple shapes,
        limited color palette, negative space, geometric composition""",
    'cartoon': """cartoon style, bold outlines, vibrant colors,
        exaggerated features, playful design, smooth shading""",
    'realistic': """realistic digital painting, detailed textures,
        professional illustration, photorealistic elements, detailed shading"""
}

# Single CORS middleware
@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        return web.Response(headers={
            'Access-Control-Allow-Origin': 'https://avionai.net',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '86400',
        })

    response = await handler(request)
    response.headers.update({
        'Access-Control-Allow-Origin': 'https://avionai.net',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    })
    return response

# Static file handlers
@routes.get('/')
async def serve_index(request):
    return web.FileResponse(BASE_DIR / 'index.html')

@routes.get('/home')
async def serve_home(request):
    return web.FileResponse(BASE_DIR / 'home.html')

@routes.get('/generator')
async def serve_generator(request):
    return web.FileResponse(BASE_DIR / 'generator.html')

@routes.get('/whitepaper')
async def serve_whitepaper(request):
    return web.FileResponse(BASE_DIR / 'whitepaper.html')

@routes.get('/assets/{filename:.*}')
async def serve_assets(request):
    filename = request.match_info['filename']
    return web.FileResponse(BASE_DIR / 'assets' / filename)

@routes.options('/api/generate')
async def api_options(request):
    return web.Response(headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600',
    })

@routes.post('/api/generate')
async def generate(request):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    if request.method == 'OPTIONS':
        return web.Response(headers=headers)
    
    try:
        data = await request.json()
        idea = data.get('idea')
        art_style = data.get('artStyle', '3d')
        
        if not LEONARDO_API_KEY:
            return web.json_response({"error": "API key not configured"}, status=500, headers=headers)

        # Get the art style prompt
        style_prompt = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS['3d'])

        # Create base prompt
        base_prompt = f"""detailed cryptocurrency mascot logo of a {idea},
            {style_prompt},
            centered composition, clean vectorized style,
            suitable for crypto token, professional logo design"""

        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {LEONARDO_API_KEY}',
            'content-type': 'application/json'
        }

        payload = {
            "height": 512,
            "width": 512,
            "prompt": base_prompt,
            "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",
            "negative_prompt": "text, watermark, logo, words, letters, signature, realistic, photographic, abstract shapes, blurry, low quality",
            "num_images": 1,
            "guidance_scale": 8,
            "init_strength": 0.4
        }

        async with ClientSession() as session:
            async with session.post(
                f"{LEONARDO_BASE_URL}/generations",
                headers=headers,
                json=payload
            ) as response:
                response_text = await response.text()
                print(f"Response status: {response.status}")
                print(f"Response text: {response_text}")
                
                if response.status != 200:
                    return web.json_response(
                        {"error": f"Failed to generate image: {response_text}"}, 
                        status=response.status
                    )
                
                generation_data = json.loads(response_text)
                generation_id = generation_data['sdGenerationJob']['generationId']
                
                # Poll for results
                for _ in range(30):
                    async with session.get(
                        f"{LEONARDO_BASE_URL}/generations/{generation_id}",
                        headers=headers
                    ) as check_response:
                        if check_response.status == 200:
                            result = await check_response.json()
                            if result['generations_by_pk']['status'] == 'COMPLETE':
                                image_url = result['generations_by_pk']['generated_images'][0]['url']
                                return web.json_response({
                                    'imageUrl': image_url,
                                    'name': idea.title(),
                                    'ticker': ''.join(word[0].upper() for word in idea.split()[:3]),
                                    'description': f"Revolutionary {idea} token powered by advanced AI technology.",
                                    'socialLinks': ['Twitter Account', 'Telegram Group', 'Website'],
                                    'success': True
                                }, headers=headers)
                    await web.asyncio.sleep(1)

                return web.json_response({"error": "Timeout waiting for image"}, status=500)

    except Exception as e:
        print(f"Detailed error: {str(e)}")  # Debug log
        return web.json_response({"error": str(e)}, status=500, headers=headers)

async def init_app():
    app = web.Application(middlewares=[cors_middleware])
    app.add_routes(routes)
    return app

if __name__ == '__main__':
    print("Starting server...")
    print(f"Leonardo API Key present: {'Yes' if LEONARDO_API_KEY else 'No'}")
    port = int(os.environ.get('PORT', 8000))
    web.run_app(init_app(), port=port, host='0.0.0.0') 
