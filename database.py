import gspread
from oauth2client.service_account import ServiceAccountCredentials
import redis

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)

client = gspread.authorize(creds)
spreadsheet = client.open("Restaurant_System")

orders_sheet = spreadsheet.worksheet("Orders")
menu_sheet = spreadsheet.worksheet("Menu")

redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
