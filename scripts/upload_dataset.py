"""One-off loader: reads the Excel dataset and appends it into the
Supabase `purchases` table (schema created via docs/supabase_schema.sql).

Usage:
    python scripts/upload_dataset.py "postgresql+psycopg2://user:pass@host:port/dbname"

Column names are renamed to snake_case on the way in: Postgres folds
unquoted identifiers to lowercase, so keeping the Excel file's original
`CustomerID`-style names would make every LLM-generated (unquoted) SQL
query fail with "column does not exist".
"""

from __future__ import annotations

import sys

import pandas as pd
from sqlalchemy import create_engine

COLUMN_MAP = {
    "CustomerID": "customer_id",
    "Product": "product",
    "PurchaseDate": "purchase_date",
    "Quantity": "quantity",
    "UnitPrice": "unit_price",
    "CustomerName": "customer_name",
    "ProductCategory": "product_category",
    "PaymentMethod": "payment_method",
    "ReviewRating": "review_rating",
    "TotalPrice": "total_price",
}


def main(database_url: str, xlsx_path: str = "data/Customer-Purchase-History.xlsx") -> None:
    df = pd.read_excel(xlsx_path).rename(columns=COLUMN_MAP)
    engine = create_engine(database_url)
    df.to_sql("purchases", engine, if_exists="append", index=False, method="multi", chunksize=200)
    print(f"Uploaded {len(df)} rows to purchases")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    main(sys.argv[1])
