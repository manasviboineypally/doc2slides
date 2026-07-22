"""Test database connection and create tables."""
from app.db.session import init_db, engine
from sqlalchemy import text

print("Testing database connection...")

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"✅ Connected to PostgreSQL: {version[:50]}...")
    
    print("\nCreating tables...")
    init_db()
    print("✅ Tables created (or already exist)")
    
    print("\n🎉 Database is ready!")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")