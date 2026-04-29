"""AI Scheduling services package.

Provides the 30-criteria evaluation engine, scorer modules, chat service,
alert engine, pre-job generator, change request service, and supporting
utilities.
"""

from grins_platform.services.ai.scheduling.admin_tools import AdminSchedulingTools
from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
from grins_platform.services.ai.scheduling.change_request_service import (
    ChangeRequestResult,
    ChangeRequestService,
)
from grins_platform.services.ai.scheduling.chat_service import SchedulingChatService
from grins_platform.services.ai.scheduling.criteria_evaluator import (
    CriteriaEvaluator,
    ScorerProtocol,
)
from grins_platform.services.ai.scheduling.data_migration import DataMigrationService
from grins_platform.services.ai.scheduling.external_services import (
    ExternalServicesClient,
)
from grins_platform.services.ai.scheduling.prejob_generator import PreJobGenerator
from grins_platform.services.ai.scheduling.resource_alerts import (
    ResourceAlertGenerator,
)
from grins_platform.services.ai.scheduling.resource_tools import (
    ResourceSchedulingTools,
)
from grins_platform.services.ai.scheduling.security import (
    SchedulingLLMConfig,
    SchedulingSecurityService,
    SchedulingStorageConfig,
)

__all__ = [
    "AdminSchedulingTools",
    "AlertEngine",
    "ChangeRequestResult",
    "ChangeRequestService",
    "CriteriaEvaluator",
    "DataMigrationService",
    "ExternalServicesClient",
    "PreJobGenerator",
    "ResourceAlertGenerator",
    "ResourceSchedulingTools",
    "SchedulingChatService",
    "SchedulingLLMConfig",
    "SchedulingSecurityService",
    "SchedulingStorageConfig",
    "ScorerProtocol",
]
