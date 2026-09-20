"""Vercel and standard WSGI entry point for the Urban Furniture API."""
from app import create_app

app = create_app()
