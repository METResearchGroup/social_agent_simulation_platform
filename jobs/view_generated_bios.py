"""Simple script to view all generated bios in the database."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)


def main():

    tx = SqliteTransactionProvider()
    generated_bio_repo = create_sqlite_generated_bio_repository(transaction_provider=tx)
    generated_bios = generated_bio_repo.list_all_generated_bios()

    len(set(bio.handle for bio in generated_bios))
    len(generated_bios)

    if not generated_bios:
        return

    for bio in generated_bios:
        (
            bio.generated_bio[:25] + "..."
            if len(bio.generated_bio) > 25
            else bio.generated_bio
        )


if __name__ == "__main__":
    main()
