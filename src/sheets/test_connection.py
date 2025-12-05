from src.sheets.google_client import GoogleSheetsClient

SPREADSHEET_ID = "1IpNGxrBm6MhwrfhcteDuL36lLUIg_eP6fmf05Y98_c4"


def main():
    client = GoogleSheetsClient(
        credentials_path="config/service_account.json",
        spreadsheet_id=SPREADSHEET_ID
    )

    print("=== Position A1:D5 ===")
    print(client.read_range("Position", "A1:D5"))

    print("\n=== T_Ledger A1:E5 ===")
    print(client.read_range("T_Ledger", "A1:E5"))


if __name__ == "__main__":
    main()
