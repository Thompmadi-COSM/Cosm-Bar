import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    base_dir = os.path.dirname(os.path.abspath(__file__))  # directory of sheets.py
    json_path = os.path.join(base_dir, "..", "Bar_training.json")  # parent directory
    json_path = os.path.abspath(json_path)  # normalize the path

    creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    client = gspread.authorize(creds)
    return client

def get_sheet_names():
    client = connect_sheet()
    spreadsheet = client.open("Bartending Drinks")
    sheet_list = spreadsheet.worksheets()
    
    excluded_sheets = {"Template", "How to Update Drinks"}
    filtered_sheets = [sheet.title for sheet in sheet_list if sheet.title not in excluded_sheets]
    
    return filtered_sheets


def get_all_drinks(venue):
    client = connect_sheet()
    sheet = client.open("Bartending Drinks").worksheet(venue)
    data = sheet.get_all_records()

    drinks = {}
    for row in data:
        name = row.get("Drink Name", "").strip()
        if not name:
            continue

        if name not in drinks:
            drinks[name] = {
                "mixers": [],
                "spirits": [],
                "amounts": [],
                "garnishes": [],
                "glass_types": [],
                "correct": {
                    "mixers": [],
                    "spirits": [],
                    "amounts": [],
                    "garnish": "",
                    "glass_type": ""
                }
            }

        mixer = row.get("Mixer", "").strip()
        spirit = row.get("Spirit", "").strip()
        amount = row.get("Amount", "").strip()
        garnish = row.get("Garnish", "").strip()
        glass = row.get("Glass", "").strip()

        print(f"Row Drink: {name}, Mixer: {mixer}, Spirit: {spirit}, Amount: {amount}, Garnish: {garnish}, Glass: {glass}")

        def parse_amount(amt_str):
            try:
                return float(amt_str.split()[0])  # '1.0 oz' → 1.0
            except:
                return None

        if mixer:
            amt = parse_amount(amount)
            if amt is not None:
                drinks[name]["mixers"].append(mixer)
                drinks[name]["correct"]["mixers"].append(mixer)
                drinks[name]["amounts"].append(amt)
                drinks[name]["correct"]["amounts"].append(amt)

        if spirit:
            amt = parse_amount(amount)
            if amt is not None:
                drinks[name]["spirits"].append(spirit)
                drinks[name]["correct"]["spirits"].append(spirit)
                drinks[name]["amounts"].append(amt)
                drinks[name]["correct"]["amounts"].append(amt)

        if garnish and not drinks[name]["correct"]["garnish"]:
            drinks[name]["correct"]["garnish"] = garnish
        if glass and not drinks[name]["correct"]["glass_type"]:
            drinks[name]["correct"]["glass_type"] = glass

        if garnish and garnish not in drinks[name]["garnishes"]:
            drinks[name]["garnishes"].append(garnish)
        if glass and glass not in drinks[name]["glass_types"]:
            drinks[name]["glass_types"].append(glass)

    return drinks


