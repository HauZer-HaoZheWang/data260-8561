import random

from database import SessionLocal
from models import Trial, TrialDetail


SEED = 8561
random.seed(SEED)


def main():
    db = SessionLocal()

    try:
        # Remove old performance-test data
        db.query(TrialDetail).delete(
            synchronize_session=False
        )
        db.query(Trial).delete(
            synchronize_session=False
        )
        db.commit()

        # Create 5,000 primary records
        trials = [
            Trial(
                brief_title=f"Seeded Clinical Trial {i}",
                sponsor=f"Sponsor {i % 50}",
            )
            for i in range(1, 5001)
        ]

        db.add_all(trials)
        db.commit()

        # Create 200 related records
        first_200_trials = (
            db.query(Trial)
            .order_by(Trial.id.asc())
            .limit(200)
            .all()
        )

        details = [
            TrialDetail(
                trial_id=trial.id,
                detail=f"Related detail for trial {trial.id}",
            )
            for trial in first_200_trials
        ]

        db.add_all(details)
        db.commit()

        trial_count = db.query(Trial).count()
        detail_count = db.query(TrialDetail).count()

        print(f"SEED={SEED}")
        print(f"trials={trial_count}")
        print(f"trial_details={detail_count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
