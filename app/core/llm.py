import litellm
from litellm import completion

from app.config import get_settings

litellm.set_verbose = False

def call_llm(
  prompt: str,
  system_prompt: str = "You are a helpful assistant that answers questions based on provided context.",
  temperature: float = 0.2,
  response_format: dict | None = None
) -> str:
  
  settings = get_settings()
  messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt},
  ]
  try:
    response = completion(
      model = settings.active_llm_model,
      messages=messages,
      temperature=temperature,
      max_tokens=1024,
      response_format=response_format,
    )
    return response.choices[0].message.content.strip()

  except Exception as primary_error:
    print(f"Primary LLM ({settings.llm_provider}) failed: {primary_error}")
    print(f"Falling back to {settings.llm_fallback_provider}...")

    #try fallback provider
    try:
      response = completion(
        model = settings.fallback_llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
        response_format=response_format,
      )
      return response.choices[0].message.content.strip()
    
    except Exception as fallback_error:
      raise RuntimeError(
        f"Both providers failed.\n"
        f"Primary ({settings.llm_provider}): {primary_error}\n"
        f"Fallback ({settings.llm_fallback_provider}): {fallback_error}"
      )