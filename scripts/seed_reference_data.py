from app.database import get_sync_db
from app.services.thin_slice_runtime import ensure_reference_data


def main() -> None:
    db = get_sync_db()
    try:
        ensure_reference_data(db)
        db.commit()
        print("reference data seeded")
    finally:
        db.close()


if __name__ == "__main__":
    main()
