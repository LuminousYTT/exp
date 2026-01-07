import os

# Database URL format for MySQL: mysql+pymysql://user:password@host:3306/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mes_demo.db")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
