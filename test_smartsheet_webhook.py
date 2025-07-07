import os
import json
from dotenv import load_dotenv
import smartsheet
import requests


def main():
    """Send a test webhook payload to a local Azure Function."""
    load_dotenv()
    smartsheet_token = os.getenv("SMTSHEET_TOKEN")
    smartsheet_id = os.getenv("SMTSHEET_ID")

    if not smartsheet_token or not smartsheet_id:
        raise Exception("SMTSHEET_TOKEN and SMTSHEET_ID must be set in the .env file.")

    ss_client = smartsheet.Smartsheet(smartsheet_token)
    ss_client.errors_as_exceptions(True)

    def print_columns(sheet):
        print("\nColumns in sheet:")
        for col in sheet.columns:
            print(f"  {col.title} (ID: {col.id})")

    sheet = ss_client.Sheets.get_sheet(smartsheet_id)
    print_columns(sheet)

    if not sheet.rows:
        raise Exception("No rows found in the sheet.")
    top_row = sheet.rows[0]

    print("\nTop row data:")
    row_cells = {}
    for cell in top_row.cells:
        col_id = str(cell.column_id)
        value = cell.value if hasattr(cell, 'value') else None
        row_cells[col_id] = value
        print(f"  Column ID: {col_id}, Value: {value}")

    forced_cells = []
    for cell in top_row.cells:
        col_id = str(cell.column_id)
        value = cell.value if hasattr(cell, 'value') else None
        if col_id == '593432251944836':
            value = 'Closed Won'
        forced_cells.append({"columnId": col_id, "value": value})

    webhook_payload = {
        "eventType": "ROW_UPDATED",
        "objectId": int(smartsheet_id),
        "row": {
            "id": top_row.id,
            "rowNumber": top_row.row_number,
            "cells": forced_cells,
        },
    }

    print("\n--- Webhook Payload Example (SMT_SALES_STAGE forced to 'Closed Won') ---")
    print(json.dumps(webhook_payload, indent=2))

    local_function_url = "http://localhost:7071/api/main"
    headers = {"Content-Type": "application/json"}

    print(f"\nSending POST to {local_function_url} ...")
    response = requests.post(local_function_url, headers=headers, data=json.dumps(webhook_payload))
    print(f"Response status: {response.status_code}")
    print(f"Response body:\n{response.text}")


if __name__ == "__main__":
    main()
