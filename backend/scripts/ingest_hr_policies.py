from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.rag.ingestion_service import PolicyIngestionService


def main():
    policy_directory = PROJECT_ROOT / "storage" / "rag" / "policies"

    service = PolicyIngestionService(
        policy_directory=str(policy_directory)
    )

    result = service.ingest()

    print("\nHR POLICY INGESTION COMPLETE")
    print("-" * 40)

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()