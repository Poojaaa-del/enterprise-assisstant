# scripts/export_openapi.py
"""
OpenAPI Schema Export Utility Script
Dumps the complete FastAPI OpenAPI JSON schema to openapi.json for Postman/Insomnia import.

Usage (from project root):
    venv/Scripts/python.exe scripts/export_openapi.py
"""
import json
import os
import sys

# Add backend directory to sys.path so 'from main import app' works
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

from main import app


def export_openapi():
    print("[INFO] Generating OpenAPI schema from FastAPI application instance...")
    openapi_schema = app.openapi()

    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "openapi.json"))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    endpoint_count = len(openapi_schema.get("paths", {}))
    print(f"[OK] OpenAPI schema successfully exported to: {output_path}")
    print(f"[INFO] Total endpoints documented: {endpoint_count}")


if __name__ == "__main__":
    export_openapi()
