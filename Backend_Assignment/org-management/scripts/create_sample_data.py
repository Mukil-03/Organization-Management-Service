import asyncio
from datetime import datetime

from app.db import db
from app.utils import safe_collection_name


async def main():
    master_db = db.get_master_db()
    orgs = master_db["organizations"]
    org_name = "Sample Org"
    collection_name = safe_collection_name(org_name)

    await orgs.insert_one(
        {
            "organization_name": org_name,
            "collection_name": collection_name,
            "admin": {"email": "sample@org.com", "password": "hashed_password_here"},
            "created_at": datetime.utcnow(),
        }
    )
    org_collection = master_db[collection_name]
    await org_collection.insert_many(
        [
            {"name": "Document 1"},
            {"name": "Document 2"},
        ]
    )
    print(f"Inserted sample data for {org_name} in collection {collection_name}")


if __name__ == "__main__":
    asyncio.run(main())


