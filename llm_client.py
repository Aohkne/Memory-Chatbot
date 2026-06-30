from langchain_nvidia_ai_endpoints import ChatNVIDIA

import config

_chat_model = None
_classifier_model = None


def _common_kwargs() -> dict:
    kwargs = {"model": config.CHAT_MODEL, "api_key": config.NVIDIA_API_KEY}
    if config.BASE_URL:
        kwargs["base_url"] = config.BASE_URL
    return kwargs


def get_chat_model() -> ChatNVIDIA:
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatNVIDIA(
            **_common_kwargs(),
            temperature=1,
            top_p=0.95,
            max_tokens=16384,
            timeout=120,
            model_kwargs={"extra_body": {"chat_template_kwargs": {"thinking": False}}},
        )
    return _chat_model


def get_classifier_model() -> ChatNVIDIA:
    """Lower temperature instance for extraction/consolidation tasks that need stable output."""
    global _classifier_model
    if _classifier_model is None:
        _classifier_model = ChatNVIDIA(
            **_common_kwargs(),
            temperature=0.2,
            top_p=0.9,
            max_tokens=4096,
            timeout=120,
            model_kwargs={"extra_body": {"chat_template_kwargs": {"thinking": False}}},
        )
    return _classifier_model
