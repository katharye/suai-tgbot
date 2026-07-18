from dotenv import load_dotenv
import os

def getToken() -> str:
    load_dotenv()
    
    return os.getenv("TOKEN")


def getDatabaseUrl() -> str:
    load_dotenv()
    
    return os.getenv("DATABASE_URL")


