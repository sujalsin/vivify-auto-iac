#!/usr/bin/env python3
"""Initialize database schema"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import init_db, get_db_pool

async def main():
    """Initialize database"""
    print("Initializing database...")
    try:
        await init_db()
        print("✓ Database schema initialized successfully")
        
        # Test connection
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✓ Database connection verified")
            else:
                print("✗ Database connection test failed")
                return 1
    except Exception as e:
        print(f"✗ Database initialization failed: {str(e)}")
        print("\nMake sure PostgreSQL is running:")
        print("  docker-compose up -d postgres")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

