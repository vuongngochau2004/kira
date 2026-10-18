"""Version history of one provision, used by citation links."""

from dataclasses import dataclass
from datetime import date

from src.modules.legal.application.errors import LegalProvisionNotFound
from src.modules.legal.application.ports import LegalProvisionSearchPort
from src.modules.legal.domain.qa import ProvisionHit


@dataclass(frozen=True)
class ProvisionHistory:
    provision_key: str
    label: str
    number: str
    title: str
    doc_type: str
    versions: list[ProvisionHit]
    in_force: ProvisionHit | None


class GetProvisionHistory:
    def __init__(self, search: LegalProvisionSearchPort) -> None:
        self._search = search

    async def execute(self, provision_key: str, day: date) -> ProvisionHistory:
        versions = sorted(
            await self._search.list_versions(provision_key), key=lambda hit: hit.valid_from
        )
        if not versions:
            raise LegalProvisionNotFound(provision_key)
        latest = versions[-1]
        return ProvisionHistory(
            provision_key=provision_key,
            label=latest.label,
            number=latest.number,
            title=latest.title,
            doc_type=latest.doc_type,
            versions=versions,
            in_force=next((v for v in versions if v.in_force_on(day)), None),
        )
