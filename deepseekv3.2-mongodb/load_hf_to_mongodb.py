"""
Script to load a Hugging Face dataset and push it to MongoDB.

This script:
1. Loads the cfahlgren1/hub-stats dataset from the Hugging Face hub
2. Converts it to CSV
3. Pushes the data to a new MongoDB collection

It can be run with the following command:

```bash
uv run --env-file .env load_hf_to_mongodb.py
```
"""

import os
from datasets import load_dataset, get_dataset_config_names
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import pandas as pd
import numpy as np


def load_hf_dataset(dataset_name: str, config: str):
    """Load a dataset from HuggingFace Hub."""
    dataset = load_dataset(dataset_name, config, split="train")
    return dataset


def convert_to_csv(dataset, output_path: str = "hub_stats.csv"):
    """Convert HuggingFace dataset to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = dataset.to_pandas()
    df.to_csv(output_path, index=False)
    return df


def connect_to_mongodb(connection_string: str):
    """Connect to MongoDB."""
    try:
        # Add SSL parameters to work around macOS SSL issues
        client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True  # For development only
        )
        # Test connection
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise


def push_to_mongodb(df: pd.DataFrame, client: MongoClient, database_name: str, collection_name: str, limit_rows: int = None):
    """Push DataFrame to MongoDB collection."""
    # Get database and collection
    db = client[database_name]
    
    # Drop collection if it exists to avoid duplicate key errors
    if collection_name in db.list_collection_names():
        db.drop_collection(collection_name)
    
    collection = db[collection_name]
    
    # Limit rows for testing if specified
    if limit_rows is not None:
        df = df.head(limit_rows)
    
    # Drop columns that contain complex nested arrays (these cause encoding issues)
    # We identify columns where the first non-null value is a complex object/array
    columns_to_drop = []
    for col in df.columns:
        # Get first non-null value
        first_val = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
        if first_val is not None:
            # Check if it's a complex type (list, dict with nested structures, numpy array)
            if isinstance(first_val, (list, np.ndarray)):
                columns_to_drop.append(col)
            elif isinstance(first_val, dict) and any(isinstance(v, (list, dict)) for v in first_val.values()):
                columns_to_drop.append(col)
    
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)
    
    # Convert DataFrame to list of dictionaries
    records = df.to_dict('records')
    
    # Replace NaN values with None for MongoDB
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
    
    # Insert documents
    if records:
        result = collection.insert_many(records)
        print(f"✅ {collection_name}: {len(result.inserted_ids)} documents inserted")
    
    return collection


def main():
    """Main function to orchestrate the data loading and upload."""
    
    # Configuration
    DATASET_NAME = "cfahlgren1/hub-stats"
    CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
    if not CONNECTION_STRING:
        raise ValueError("MONGODB_CONNECTION_STRING environment variable not set. Please create a .env file or set the environment variable.")
    DATABASE_NAME = "huggingface_data"
    
    # TEST MODE: Set to None to insert all rows, or a number to limit for testing
    LIMIT_ROWS = None  # Insert ALL rows
    
    # Get available configs from the dataset
    CONFIGS = get_dataset_config_names(DATASET_NAME)
    
    try:
        # Connect to MongoDB once
        client = connect_to_mongodb(CONNECTION_STRING)
        
        # Process each config
        for config in CONFIGS:
            COLLECTION_NAME = f"hub_stats_{config}"
            CSV_OUTPUT = f"data/hub_stats_{config}.csv"
            
            try:
                # Step 1: Load dataset from HuggingFace
                dataset = load_hf_dataset(DATASET_NAME, config)
                
                # Step 2: Convert to CSV
                df = convert_to_csv(dataset, CSV_OUTPUT)
                
                # Step 3: Push to MongoDB
                collection = push_to_mongodb(df, client, DATABASE_NAME, COLLECTION_NAME, limit_rows=LIMIT_ROWS)
                
            except Exception as e:
                print(f"❌ Error processing '{config}': {e}")
                # Continue with next config
                continue
        
        print("\n✅ All collections loaded successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    main()

