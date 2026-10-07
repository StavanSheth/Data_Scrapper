"""In-process background worker for executing scraping runs."""

import asyncio
import json
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

# Global registry of active cancel callbacks and WebSocket listeners
CANCEL_FLAGS: Dict[str, bool] = {}
WS_LISTENERS: Dict[str, Set[Callable[[dict], None]]] = {}

def register_ws_listener(run_id: str, callback: Callable[[dict], None]) -> None:
    if run_id not in WS_LISTENERS:
        WS_LISTENERS[run_id] = set()
    WS_LISTENERS[run_id].add(callback)

def unregister_ws_listener(run_id: str, callback: Callable[[dict], None]) -> None:
    if run_id in WS_LISTENERS and callback in WS_LISTENERS[run_id]:
        WS_LISTENERS[run_id].remove(callback)

async def broadcast_event(run_id: str, event_data: dict) -> None:
    listeners = WS_LISTENERS.get(run_id, set())
    for cb in list(listeners):
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(event_data)
            else:
                cb(event_data)
        except Exception:
            pass

def request_cancel(run_id: str) -> bool:
    CANCEL_FLAGS[run_id] = True
    return True

class RunWorker:
    def __init__(self):
        self.validation_service = ValidationService()

    async def execute_run(
        self,
        run_id: str,
        city: str,
        category: str,
        limit: int,
    ) -> None:
        """Executes the Google Maps discovery run in the background."""
        CANCEL_FLAGS[run_id] = False
        scraper = GoogleMapsScraper()

        # Update status to RUNNING
        with get_db_context() as db:
            run_repo = RunRepository(db)
            now_iso = datetime.now(timezone.utc).isoformat()
            run_repo.update_status(run_id, status="RUNNING", started_at=now_iso)

        await broadcast_event(run_id, {
            "event": "run.started",
            "run_id": run_id,
            "status": "RUNNING",
            "city": city,
            "category": category,
            "limit": limit,
        })

        discovered = 0
        saved = 0
        failed = 0
        error_msg = None

        try:
            def is_cancelled() -> bool:
                return CANCEL_FLAGS.get(run_id, False)

            # Stream records from scraper
            async for raw_record in scraper.scrape(
                city=city,
                category=category,
                limit=limit,
                run_id=run_id,
                cancel_check=is_cancelled,
            ):
                discovered += 1
                source_record_id = f"src_{uuid.uuid4().hex[:12]}"

                # 1. Store Source Record (Raw Data Retention)
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
                    # 3. Deduplication Check and Save
                    with get_db_context() as db:
                        biz_repo = BusinessRepository(db)
                        duplicate = biz_repo.find_duplicate(
                            run_id=run_id,
                            google_place_id=business.google_place_id,
                            normalized_name=business.normalized_name,
                            city=business.city,
                            phone=business.phone,
                        )

                        if not duplicate:
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
                            biz_repo.create_with_provenances(biz_model, provenances)
                            saved += 1
                        else:
                            # Already exists in current run, do not duplicate
                            pass

                # Update run progress counts
                with get_db_context() as db:
                    run_repo = RunRepository(db)
                    run_repo.update_counts(
                        run_id=run_id,
                        discovered=discovered,
                        saved=saved,
                        failed=failed,
                    )

                # Broadcast live progress
                pct = int((saved / limit) * 100) if limit > 0 else 0
                await broadcast_event(run_id, {
                    "event": "run.progress",
                    "run_id": run_id,
                    "status": "RUNNING",
                    "stage": "DISCOVERING_GOOGLE",
                    "discovered": discovered,
                    "saved": saved,
                    "failed": failed,
                    "percentage": min(pct, 100),
                })

        except Exception as e:
            error_msg = str(e)
            failed += 1

        finally:
            now_iso = datetime.now(timezone.utc).isoformat()
            final_status = "COMPLETED"

            if CANCEL_FLAGS.get(run_id, False):
                final_status = "CANCELLED"
            elif error_msg and saved == 0:
                final_status = "FAILED"
            elif failed > 0 and saved > 0:
                # Partial success (per prompt & Document 1 Section 9)
                final_status = "PARTIAL"
            elif saved == 0 and discovered > 0:
                final_status = "FAILED"

            with get_db_context() as db:
                run_repo = RunRepository(db)
                run_repo.update_counts(
                    run_id=run_id,
                    discovered=discovered,
                    saved=saved,
                    failed=failed,
                    error_count=failed,
                )
                run_repo.update_status(
                    run_id=run_id,
                    status=final_status,
                    completed_at=now_iso if final_status != "CANCELLED" else None,
                    cancelled_at=now_iso if final_status == "CANCELLED" else None,
                    error_message=error_msg,
                )

            CANCEL_FLAGS.pop(run_id, None)

            await broadcast_event(run_id, {
                "event": f"run.{final_status.lower()}",
                "run_id": run_id,
                "status": final_status,
                "discovered": discovered,
                "saved": saved,
                "failed": failed,
                "completed_at": now_iso,
                "error_message": error_msg,
            })
