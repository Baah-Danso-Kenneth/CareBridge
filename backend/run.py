import uvicorn
import logging
from app.utils.logging import setup_logging

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)


    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )