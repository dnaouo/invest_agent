"""Internal credential loader — not for use outside the vault package."""

from decouple import config

_CREDENTIALS = {
    "moonshot": "MOONSHOT_API_KEY",
    "tushare": "TUSHARE_TOKEN",
    "langfuse_public": "LANGFUSE_PUBLIC_KEY",
    "langfuse_secret": "LANGFUSE_SECRET_KEY",
    "langfuse_host": "LANGFUSE_HOST",
}


def _get(service_name: str) -> str:
    """Return the raw value for *service_name* from the environment / .env."""
    env_var = _CREDENTIALS.get(service_name)
    if env_var is None:
        raise ValueError(f"Unknown service: {service_name!r}")

    value: str = config(env_var, default="")
    if not value:
        raise RuntimeError(
            f"Credential for {service_name!r} (env var {env_var}) is not set or empty"
        )
    return value
