import uvicorn
from main import app
from core.settings import Settings

if __name__ == "__main__":
    s = Settings()
    uvicorn.run(app, host=s.host, port=s.port)
