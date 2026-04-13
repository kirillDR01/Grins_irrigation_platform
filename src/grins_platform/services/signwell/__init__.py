"""SignWell e-signature integration.

Validates: CRM Changes Update 2 Req 18.1, 18.3, 18.5, 18.6
"""

from grins_platform.services.signwell.client import SignWellClient
from grins_platform.services.signwell.config import SignWellSettings

__all__ = ["SignWellClient", "SignWellSettings"]
