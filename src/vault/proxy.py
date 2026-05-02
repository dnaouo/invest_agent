"""Public credential interface — the only module business code should import."""

from vault.secrets import _get, _CREDENTIALS


def get_credential(service_name: str) -> str:
    """Return the credential string for *service_name*.

    Raises:
        ValueError: *service_name* is not a known service.
        RuntimeError: The underlying env var is unset or empty.
    """
    if service_name not in _CREDENTIALS:
        raise ValueError(f"Unknown service: {service_name!r}")
    return _get(service_name)
