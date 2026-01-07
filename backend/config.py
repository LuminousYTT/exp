import os

# Database URL format for MySQL: mysql+pymysql://user:password@host:3306/dbname
# 这里直接写死为本地 MySQL root 账户，若需切换其他账户或云数据库，可改成对应连接串。
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:9860@localhost:3306/mes")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
