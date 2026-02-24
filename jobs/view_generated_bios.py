"""Simple script to view all generated bios in the database."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)


def main():
    print("=" * 80)
    print("GENERATED BIOS VIEWER")
    print("=" * 80)

    tx = SqliteTransactionProvider()
    generated_bio_repo = create_sqlite_generated_bio_repository(transaction_provider=tx)
    generated_bios = generated_bio_repo.list_all_generated_bios()

    num_handles = len(set(bio.handle for bio in generated_bios))
    num_bios = len(generated_bios)

    print("\n📊 STATISTICS")
    print("=" * 80)
    print(f"Number of unique handles: {num_handles}")
    print(f"Number of generated bios: {num_bios}")

    if not generated_bios:
        print("\nNo generated bios found in database.")
        return

    print("\n\n📝 GENERATED BIOS TABLE")
    print("=" * 80)
    print(f"{'Handle':<30} {'Generated Bio (first 25 chars)':<50}")
    print("-" * 80)

    for bio in generated_bios:
        bio_preview = (
            bio.generated_bio[:25] + "..."
            if len(bio.generated_bio) > 25
            else bio.generated_bio
        )
        print(f"{bio.handle:<30} {bio_preview:<50}")

    print("=" * 80)


if __name__ == "__main__":
    main()
