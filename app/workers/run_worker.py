"""Supervised background worker for executing and checkpointing scraping runs."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Callable
from app.database.session import get_db_context
from app.database.models import RunModel, SourceRecordModel, BusinessModel
from app.database.repositories.run_repository import RunRepository
from app.database.repositories.source_record_repository import SourceRecordRepository
from app.database.repositories.business_repository import BusinessRepository
from app.scraping.maps.google_maps_scraper import GoogleMapsScraper
from app.core.services.validation_service import ValidationService
from app.core.domain.failure_codes import FailureCode
from app.core.events import event_bus

logger = logging.getLogger("run_worker")

def register_ws_listener(run_id: str, callback: Callable[[dict], None]) -> None:
    event_bus.subscribe(run_id, callback)

def unregister_ws_listener(run_id: str, callback: Callable[[dict], None]) -> None:
    event_bus.unsubscribe(run_id, callback)

async def broadcast_event(run_id: str, event_data: dict) -> None:
    await event_bus.publish(run_id, event_data)

class TaskManager:
    """Supervises in-process async tasks to prevent unhandled background task death."""
    _active_tasks: Dict[str, asyncio.Task] = {}
    _cancelled_runs: Set[str] = set()

    @classmethod
    def spawn(cls, run_id: str, coro) -> asyncio.Task:
        cls._cancelled_runs.discard(run_id)
        task = asyncio.create_task(coro)
        cls._active_tasks[run_id] = task

        def _on_done(t: asyncio.Task):
            cls._active_tasks.pop(run_id, None)
            cls._cancelled_runs.discard(run_id)
            if t.cancelled():
                logger.info(f"Task for run {run_id} was cancelled.")
            elif t.exception():
                logger.error(f"Task for run {run_id} failed with exception: {t.exception()}", exc_info=t.exception())

        task.add_done_callback(_on_done)
        return task

    @classmethod
    def cancel(cls, run_id: str) -> bool:
        cls._cancelled_runs.add(run_id)
        task = cls._active_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    @classmethod
    def recover_stale_runs(cls) -> int:
        """Recovers any runs left in RUNNING or QUEUED state across server restarts."""
        with get_db_context() as db:
            repo = RunRepository(db)
            return repo.recover_stale_runs()

class RunWorker:
    def __init__(self, scraper: Optional[GoogleMapsScraper] = None):
        self.validation_service = ValidationService()
        self.scraper = scraper or GoogleMapsScraper()

    async def execute_run(
        self,
        run_id: str,
        city: str,
        category: str,
        limit: int,
    ) -> None:
        """Executes the Google Maps discovery run with persistent checkpointing."""
        # ponytail: Checkpoint reconstruction from SQLite source records across process crashes, upgrade trigger: distributed persistent browser session / remote CDP worker pool.
        scraper = self.scraper

        # Checkpoint resumption: query previously extracted records and progress
        existing_place_ids: set[str] = set()
        existing_urls: set[str] = set()
        already_saved = 0
        already_failed = 0
        already_discovered = 0
        already_attempted = 0
        already_duplicates = 0

        with get_db_context() as db:
            src_repo = SourceRecordRepository(db)
            existing_place_ids, existing_urls = src_repo.get_existing_identifiers_for_run(run_id)

            run_repo = RunRepository(db)
            run_model = run_repo.get_by_id(run_id)
            if run_model:
                already_saved = run_model.records_saved or 0
                already_failed = run_model.records_failed or 0
                already_discovered = run_model.records_discovered or 0
                already_attempted = getattr(run_model, "records_attempted", 0) or already_discovered
                already_duplicates = getattr(run_model, "records_duplicates", 0) or 0

            now_iso = datetime.now(timezone.utc).isoformat()
            run_repo.update_status(
                run_id,
                status="RUNNING",
                started_at=run_model.started_at if run_model and run_model.started_at else now_iso,
            )

        discovered = already_discovered
        attempted = already_attempted
        saved = already_saved
        failed = already_failed
        duplicates = already_duplicates
        error_msg = None
        failure_code = None

        await broadcast_event(run_id, {
            "event": "run.started",
            "run_id": run_id,
            "status": "RUNNING",
            "city": city,
            "category": category,
            "limit": limit,
            "resumed_from": saved,
        })

        def is_cancelled() -> bool:
            # Check fast in-memory cancellation set first
            if run_id in TaskManager._cancelled_runs:
                return True
            # Query SQLite database state directly for persistent cross-process cancellation
            try:
                with get_db_context() as db:
                    repo = RunRepository(db)
                    return repo.is_cancelled(run_id)
            except Exception:
                return False

        try:
            # Limit represents maximum accepted canonical businesses.
            # We buffer candidate generation up to (remaining * 3 + 30) so failures or duplicates
            # do not prematurely terminate before reaching the accepted limit.
            remaining_limit = max(0, limit - saved)
            candidate_buffer = max(remaining_limit * 3, remaining_limit + 30)

            if remaining_limit > 0:
                # Stream records from scraper resuming from checkpoint
                async for raw_record in scraper.scrape(
                    city=city,
                    category=category,
                    limit=candidate_buffer,
                    run_id=run_id,
                    cancel_check=is_cancelled,
                    initial_seen_place_ids=existing_place_ids,
                    initial_seen_urls=existing_urls,
                ):
                    if is_cancelled():
                        break

                    discovered += 1
                    attempted += 1
                    source_record_id = f"src_{uuid.uuid4().hex[:12]}"

                    # Atomic persistence: store source record, business entity, provenances, and progress counts in one transaction
                    with get_db_context() as db:
                        src_repo = SourceRecordRepository(db)
                        src_model = SourceRecordModel(
                            id=source_record_id,
                            run_id=run_id,
                            platform_id=None,
                            source_type="GOOGLE",
                            source_url=raw_record.profile_url,
                            external_id=raw_record.place_id,
                            raw_name=raw_record.name,
                            raw_address=raw_record.address,
                            raw_phone=raw_record.phone,
                            raw_email=None,
                            raw_website=raw_record.website,
                            raw_category=raw_record.category,
                            raw_latitude=raw_record.latitude,
                            raw_longitude=raw_record.longitude,
                            raw_rating=raw_record.rating,
                            raw_review_count=raw_record.review_count,
                            raw_payload=json.dumps(raw_record.raw_payload),
                            extraction_status=raw_record.status or "SUCCESS",
                            scraped_at=raw_record.scraped_at,
                        )
                        src_repo.create(src_model)

                        if raw_record.status == "EXTRACTION_FAILED":
                            failed += 1
                            logger.warning(
                                "Scraper-level extraction failure for run %s: %s",
                                run_id,
                                raw_record.raw_payload.get("error") if raw_record.raw_payload else "Unknown scraper error",
                            )
                        else:
                            # 2. Normalize and Validate
                            business, provenances, val_errors = self.validation_service.process_raw_record(
                                raw=raw_record,
                                run_id=run_id,
                                source_record_id=source_record_id,
                                default_city=city,
                            )

                            if not business or val_errors:
                                failed += 1
                            else:
                                # 3. Deduplication Check and Save (enforced at app and DB levels)
                                biz_repo = BusinessRepository(db)
                                duplicate = biz_repo.find_duplicate(
                                    run_id=run_id,
                                    google_place_id=business.google_place_id,
                                    normalized_name=business.normalized_name,
                                    city=business.city,
                                    phone=business.phone,
                                    normalized_phone=business.normalized_phone,
                                    website_domain=business.website_domain,
                                    postal_code=business.postal_code,
                                    address=business.address,
                                )

                                if duplicate:
                                    duplicates += 1
                                else:
                                    biz_model = BusinessModel(
                                        id=business.business_id,
                                        run_id=run_id,
                                        source=business.source,
                                        source_record_id=source_record_id,
                                        name=business.name,
                                        normalized_name=business.normalized_name,
                                        category=business.category,
                                        subcategory=business.subcategory,
                                        address=business.address,
                                        street=business.street,
                                        locality=business.locality,
                                        city=business.city,
                                        state=business.state,
                                        postal_code=business.postal_code,
                                        country=business.country,
                                        latitude=business.latitude,
                                        longitude=business.longitude,
                                        phone=business.phone,
                                        normalized_phone=business.normalized_phone,
                                        email=business.email,
                                        website=business.website,
                                        website_domain=business.website_domain,
                                        website_status=business.website_status,
                                        rating=business.rating,
                                        review_count=business.review_count,
                                        google_place_id=business.google_place_id,
                                        google_profile_url=business.google_profile_url,
                                        opening_hours=business.opening_hours,
                                        status=business.status,
                                        created_at=business.created_at,
                                        updated_at=business.updated_at,
                                    )
                                    created_biz = biz_repo.create_with_provenances(biz_model, provenances)
                                    if created_biz and created_biz.id == business.business_id:
                                        saved += 1
                                    else:
                                        # Duplicate caught by DB unique constraint
                                        duplicates += 1

                        # Update run progress counts in SQLite atomically within same transaction
                        run_repo = RunRepository(db)
                        run_repo.update_counts(
                            run_id=run_id,
                            discovered=discovered,
                            attempted=attempted,
                            saved=saved,
                            failed=failed,
                            duplicates=duplicates,
                        )

                    # Broadcast live progress: saved / requested limit
                    pct = int((saved / max(limit, 1)) * 100)
                    await broadcast_event(run_id, {
                        "event": "run.progress",
                        "run_id": run_id,
                        "status": "RUNNING",
                        "stage": "DISCOVERING_GOOGLE",
                        "discovered": discovered,
                        "attempted": attempted,
                        "saved": saved,
                        "failed": failed,
                        "duplicates": duplicates,
                        "percentage": min(pct, 100),
                    })

                    # Stop if requested limit of accepted canonical businesses has been reached
                    if saved >= limit:
                        logger.info("Reached target limit of %d accepted businesses. Ending discovery.", limit)
                        break

        except asyncio.CancelledError:
            # Task cancellation requested
            error_msg = "Run was cancelled by user."
            failure_code = FailureCode.CANCELLED_BY_USER.value
        except Exception as e:
            logger.error(f"Error in scraping run {run_id}: {e}", exc_info=True)
            error_msg = str(e) or "An unexpected error occurred during scraping."
            err_lower = error_msg.lower()
            if "browser_start_failed" in err_lower:
                failure_code = FailureCode.BROWSER_START_FAILED.value
            elif "navigation_failed" in err_lower:
                failure_code = FailureCode.NAVIGATION_FAILED.value
            elif "feed_not_found" in err_lower:
                failure_code = FailureCode.FEED_NOT_FOUND.value
            else:
                failure_code = FailureCode.UNKNOWN_ERROR.value
            failed += 1

        finally:
            now_iso = datetime.now(timezone.utc).isoformat()
            cancelled = is_cancelled()

            if cancelled:
                final_status = "CANCELLED"
            elif error_msg and saved == 0 and not cancelled:
                final_status = "FAILED"
            elif saved >= limit:
                final_status = "COMPLETED"
            elif saved > 0 and failed > 0:
                final_status = "PARTIAL"
            elif saved > 0:
                final_status = "COMPLETED"
            elif saved == 0 and discovered > 0:
                final_status = "FAILED"
            else:
                final_status = "COMPLETED"

            with get_db_context() as db:
                run_repo = RunRepository(db)
                run_repo.update_counts(
                    run_id=run_id,
                    discovered=discovered,
                    attempted=attempted,
                    saved=saved,
                    failed=failed,
                    duplicates=duplicates,
                    error_count=failed,
                )
                run_repo.update_status(
                    run_id=run_id,
                    status=final_status,
                    completed_at=now_iso if final_status != "CANCELLED" else None,
                    cancelled_at=now_iso if final_status == "CANCELLED" else None,
                    error_message=error_msg,
                )

            await broadcast_event(run_id, {
                "event": f"run.{final_status.lower()}",
                "run_id": run_id,
                "status": final_status,
                "discovered": discovered,
                "attempted": attempted,
                "saved": saved,
                "failed": failed,
                "duplicates": duplicates,
                "percentage": 100,
                "completed_at": now_iso,
                "error_message": error_msg,
            })
