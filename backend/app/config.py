import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    """Base settings for App"""

    APP_NAME = "CAREBRIDGE"
    APP_VERSION = "0.1.0"
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    PRIMARY_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODEL = "llama-3.1-8b-instant"

    DATA_PATH = "data/medical_knowledge.json"

    MAX_ATTEMPTS = 3
    PASS_THRESHOLD = 0.7

    FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
    FHIR_TIMEOUT = int(os.getenv("FHIR_TIMEOUT", "10"))
    FHIR_ENABLED = os.getenv("FHIR_ENABLED", "true").lower() == "true"


    def validate(self):
        """Validate the settings"""
        missing = [k for k in ["GROQ_API_KEY", "COHERE_API_KEY", "TAVILY_API_KEY"] if not getattr(self, k) ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")   


config = Config() 
