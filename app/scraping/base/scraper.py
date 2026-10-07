"""Base interfaces and protocols for scrapers."""

from typing import Protocol, AsyncGenerator
from app.core.domain.models import RawGoogleRecord

class BaseScraper(Protocol):
    """Protocol for business discovery scrapers."""

    async def scrape(
        self,
        city: str,
        category: str,
        limit: int,
        run_id: str
    ) -> AsyncGenerator[RawGoogleRecord, None]:
        """Asynchronously yield raw records as they are discovered."""
        ...
