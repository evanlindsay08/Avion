from aiohttp import web
import os
from dotenv import load_dotenv
from aiohttp_cors import setup as cors_setup, ResourceOptions

load_dotenv()

routes = web.RouteTableDef()

# Configure CORS
async def init_app():
    app = web.Application()
    
    # Setup CORS
    cors = cors_setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS"]
        )
    })
    
    app.add_routes(routes)
    
    # Configure CORS for all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

# Your existing routes
@routes.post('/api/generate')
async def generate(request):
    try:
        data = await request.json()
        # Your existing generation code...
        
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    web.run_app(init_app(), port=port, host='0.0.0.0') 