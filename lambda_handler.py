"""
Lambda entry point.
Mangum wraps FastAPI so it works as a Lambda handler.
"""
from mangum import Mangum
from main import app

handler = Mangum(app, lifespan="off")
