"""Export live test evidence from scraper.db to tests/fixtures/live_google_10_results.json."""

import os
import json
import sqlite3

def export_evidence():
    db_path = "data/database/scraper.db"
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    os.makedirs("tests/fixtures", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    completed_run = c.execute(
        "SELECT * FROM runs WHERE status = 'COMPLETED' ORDER BY completed_at DESC LIMIT 1"
    ).fetchone()

    if not completed_run:
        print("No completed run found in database.")
        return

    run_dict = dict(completed_run)
    run_id = run_dict["id"]

    businesses = [dict(b) for b in c.execute("SELECT * FROM businesses WHERE run_id = ?", (run_id,)).fetchall()]
    provenances = [dict(p) for p in c.execute("SELECT * FROM field_provenance WHERE run_id = ?", (run_id,)).fetchall()]
    source_records = [dict(s) for s in c.execute("SELECT id, run_id, source_type, external_id, raw_name, raw_address, raw_phone, raw_rating, raw_review_count, scraped_at FROM source_records WHERE run_id = ?", (run_id,)).fetchall()]

    evidence = {
        "verified_at": run_dict.get("completed_at"),
        "city": run_dict.get("city_input"),
        "category": run_dict.get("category"),
        "requested_limit": run_dict.get("requested_limit"),
        "status": run_dict.get("status"),
        "records_discovered": run_dict.get("records_discovered"),
        "records_saved": run_dict.get("records_saved"),
        "businesses_count": len(businesses),
        "source_records_count": len(source_records),
        "provenances_count": len(provenances),
        "businesses": businesses,
        "source_records": source_records,
    }

    out_path = "tests/fixtures/live_google_10_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)

    print(f"Exported live verification evidence to {out_path} ({len(businesses)} businesses, {len(provenances)} field provenances).")

if __name__ == "__main__":
    export_evidence()
