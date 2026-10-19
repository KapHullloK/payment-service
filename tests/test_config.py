import pytest
from pydantic import ValidationError

from payment_service.core.config import ApplicationConfig


def test_empty_webhook_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ApplicationConfig(_env_file=None, WEBHOOK_SECRET="")
