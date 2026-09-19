"""Run the local workspace with Waitress instead of the development server."""
import os
from waitress import serve
from app import create_app

if __name__ == '__main__':
    application=create_app()
    host = os.environ.get('URBAN_HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5050'))
    print(f'Urban Furniture is available at http://{host}:{port}', flush=True)
    serve(application, host=host, port=port, threads=32,channel_timeout=75)
