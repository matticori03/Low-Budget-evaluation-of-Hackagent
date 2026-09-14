import os
from hackagent.router.types import AgentTypeEnum
from hackagent import HackAgent

def get_agent_config(model_name: str):
    """
    Dynamically determine AgentTypeEnum, endpoint, and api_key based on model name.
    """
    # Require explicit provider prefixes for cloud models to avoid colliding with local Ollama model names
    is_api = (
        model_name.startswith("gemini/") or 
        model_name.startswith("openai/") or
        model_name.startswith("anthropic/") or
        model_name.startswith("zhipu/") or
        model_name.startswith("glm/") or
        model_name.startswith("zai/")
    )
    if is_api:
        api_key = None
        if model_name.startswith("gemini/"):
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY not set; cannot route to Gemini.")
        elif model_name.startswith("openai/"):
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set; cannot route to OpenAI.")
        elif model_name.startswith("anthropic/"):
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set; cannot route to Anthropic.")
        elif model_name.startswith("zhipu/") or model_name.startswith("glm/") or model_name.startswith("zai/"):
            api_key = os.environ.get("ZHIPUAI_API_KEY") or os.environ.get("GLM_API_KEY") or os.environ.get("ZAI_API_KEY")
            if not api_key:
                raise RuntimeError("ZHIPUAI_API_KEY / GLM_API_KEY / ZAI_API_KEY not set; cannot route to GLM.")
            
        # LiteLLM canonical provider prefix for Zhipu/GLM is 'zai/'
        identifier = model_name
        if identifier.startswith("zhipu/"):
            identifier = identifier.replace("zhipu/", "zai/", 1)
        elif identifier.startswith("glm/"):
            identifier = identifier.replace("glm/", "zai/", 1)
            
        return {
            "identifier": identifier,
            "agent_type": AgentTypeEnum.LITELLM,
            "api_key": api_key,
            "endpoint": ""
        }
    else:
        return {
            "identifier": model_name,
            "agent_type": AgentTypeEnum.OLLAMA,
            "endpoint": "http://localhost:11434",
            "timeout": 1200
        }

def get_target_agent(target_model: str, run_id: str) -> HackAgent:
    """
    Configura il target agent con il run_id corretto in modo centralizzato.
    """
    return HackAgent(
        name="vulnerable-bank-local",
        agent_type="openai-sdk",
        endpoint="http://localhost:8000/v1",
        timeout=1200,
        metadata={
            "model": target_model, 
            "run_id": run_id,
            "extra_body": {
                "metadata": {
                    "run_id": run_id
                }
            }
        }
    )
