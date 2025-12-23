#!/usr/bin/env python3
"""
Script to update debtor addresses from Fakturownia.
Reads Dłużnicy.xlsx, fetches delivery addresses from Fakturownia API,
and creates a new Excel with address columns split.
"""

import pandas as pd
import requests
import json
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:3002/api/sync/addresses"
INPUT_FILE = Path(__file__).parent.parent / "Dłużnicy.xlsx"
OUTPUT_FILE = Path(__file__).parent.parent / "Dłużnicy_z_adresami.xlsx"

def fetch_addresses(names: list[str], limit: int = 10) -> dict:
    """Fetch addresses from the API endpoint."""
    try:
        response = requests.post(
            API_URL,
            json={"names": names, "limit": limit},
            headers={"Content-Type": "application/json"},
            timeout=600  # 10 minutes timeout for large batches
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        return None

def main():
    # Parse arguments
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [limit]")
            print(f"  limit: number of clients to process (default: 10)")
            sys.exit(1)

    print(f"Reading Excel file: {INPUT_FILE}")

    # Read Excel - zakładka 'nowe'
    df = pd.read_excel(INPUT_FILE, sheet_name='nowe')
    print(f"Total rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")

    # Get unique names from "Nazwa dłużnika" column
    names_column = "Nazwa dłużnika"
    if names_column not in df.columns:
        print(f"Error: Column '{names_column}' not found")
        print(f"Available columns: {df.columns.tolist()}")
        sys.exit(1)

    # Get unique names (to avoid duplicate API calls)
    unique_names = df[names_column].dropna().unique().tolist()
    print(f"Unique names: {len(unique_names)}")

    # Limit for testing
    names_to_process = unique_names[:limit]
    print(f"\nProcessing first {len(names_to_process)} names:")
    for i, name in enumerate(names_to_process, 1):
        print(f"  {i}. {name}")

    print(f"\nCalling API...")
    result = fetch_addresses(names_to_process, limit)

    if not result or not result.get("success"):
        print(f"API call failed: {result}")
        sys.exit(1)

    data = result["data"]
    print(f"\nResults:")
    print(f"  Found: {data['found']}")
    print(f"  Not found: {data['not_found']}")

    # Create address lookup dictionary
    address_lookup = {}
    for item in data["results"]:
        name = item["name"]
        if item["found"] and item.get("parsed_address"):
            addr = item["parsed_address"]
            address_lookup[name] = {
                "client_id": item.get("client_id"),
                "delivery_address_raw": item.get("delivery_address", ""),
                "ulica": addr.get("street", ""),
                "numer_domu": addr.get("house_number", ""),
                "kod_pocztowy": addr.get("postal_code", ""),
                "miasto": addr.get("city", ""),
                "kraj": addr.get("country", ""),
            }
            print(f"\n  {name}:")
            print(f"    Raw: {item.get('delivery_address', '')}")
            print(f"    Parsed: {addr}")
        else:
            address_lookup[name] = None
            print(f"\n  {name}: NOT FOUND ({item.get('error', 'unknown')})")

    # Add new columns to dataframe
    def get_field(name, field):
        data = address_lookup.get(name)
        if data is None:
            return None
        return data.get(field)

    df["Znaleziono"] = df[names_column].map(lambda n: "TAK" if address_lookup.get(n) else "NIE")
    df["Client_ID"] = df[names_column].map(lambda n: get_field(n, "client_id"))
    df["Adres_korespondencyjny_raw"] = df[names_column].map(lambda n: get_field(n, "delivery_address_raw"))
    df["Ulica"] = df[names_column].map(lambda n: get_field(n, "ulica"))
    df["Numer_domu"] = df[names_column].map(lambda n: get_field(n, "numer_domu"))
    df["Kod_pocztowy"] = df[names_column].map(lambda n: get_field(n, "kod_pocztowy"))
    df["Miasto"] = df[names_column].map(lambda n: get_field(n, "miasto"))
    df["Kraj"] = df[names_column].map(lambda n: get_field(n, "kraj"))

    # Save to new Excel file
    print(f"\nSaving to: {OUTPUT_FILE}")
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Done! Check {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
