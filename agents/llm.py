import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from the project-root .env file
load_dotenv(override=True)

def get_llm():
    """
    Constructs a ChatOpenAI model targeting OpenRouter with 3 fallback models configured.
    Primary model defaults to 'google/gemma-4-26b-a4b-it:free'.
    3 fallback free models:
      1. poolside/laguna-s-2.1:free
      2. nvidia/nemotron-3-super-120b-a12b:free
      3. nvidia/nemotron-3-nano-30b-a3b:free
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    primary_model_name = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free")
    
    fallback_env = os.getenv(
        "OPENROUTER_FALLBACK_MODELS",
        "poolside/laguna-s-2.1:free,nvidia/nemotron-3-super-120b-a12b:free,nvidia/nemotron-3-nano-30b-a3b:free"
    )
    fallback_model_names = [m.strip() for m in fallback_env.split(",") if m.strip()]
    
    primary_llm = ChatOpenAI(
        model=primary_model_name,
        api_key=api_key,
        base_url=base_url,
        max_retries=2,
        temperature=0.7,
        timeout=8.0,
    )
    
    if not fallback_model_names:
        return primary_llm
        
    fallback_llms = [
        ChatOpenAI(
            model=fb_name,
            api_key=api_key,
            base_url=base_url,
            max_retries=2,
            temperature=0.7,
            timeout=8.0,
        )
        for fb_name in fallback_model_names
    ]
    
    return primary_llm.with_fallbacks(fallback_llms)

# Global LLM instance with fallbacks configured
llm = get_llm()
