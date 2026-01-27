"""
Google Sheets service for fetching product data.
"""
import gspread
from google.oauth2.service_account import Credentials
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service to interact with Google Sheets with caching."""
    
    def __init__(self):
        """Initialize the Google Sheets client."""
        self.credentials_file = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
        self.spreadsheet_id = settings.GOOGLE_SHEETS_SPREADSHEET_ID
        self.worksheet_name = settings.GOOGLE_SHEETS_WORKSHEET_NAME
        self.client = None
        self.worksheet = None
        
        # Cache settings
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
        
    def connect(self):
        """Connect to Google Sheets."""
        try:
            # Define the scope
            scope = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            # Authenticate using the service account
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scope
            )
            
            # Create the client
            self.client = gspread.authorize(creds)
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Get the specific worksheet
            self.worksheet = spreadsheet.worksheet(self.worksheet_name)
            
            logger.info("Successfully connected to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Google Sheets: {str(e)}")
            return False
    
    def _is_cache_valid(self):
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_duration
    
    def _fetch_all_products(self):
        """Fetch all products from Google Sheets and cache them."""
        try:
            if not self.worksheet:
                if not self.connect():
                    return {}
            
            # Get all values from the sheet
            all_records = self.worksheet.get_all_values()
            
            # Skip the header row (first row)
            if len(all_records) <= 1:
                return {}
            
            products_by_status = {'In-Stock': [], 'On The Way': []}
            
            # Process each row (starting from row 2, index 1)
            for row in all_records[1:]:
                # Ensure row has enough columns
                if len(row) < 13:
                    continue
                
                # Column indices (0-based):
                # A=0 (Id), B=1 (Item Name), D=3 (Image Link), F=5 (Wholesale),
                # H=7 (Unit 1), L=11 (QTY On Hand), M=12 (Status), N=13 (Expiry Date)
                item_name = row[1].strip() if len(row) > 1 else ""
                image_link = row[3].strip() if len(row) > 3 else ""
                wholesale_price = row[5].strip().lstrip('K') if len(row) > 5 else ""
                unit = row[7].strip() if len(row) > 7 else ""
                qty_on_hand = row[11].strip() if len(row) > 11 else ""
                item_status = row[12].strip() if len(row) > 12 else ""
                expiry_date = row[13].strip() if len(row) > 13 else ""
                
                # Skip empty rows
                if not item_name:
                    continue
                
                # Create product dict
                product = {
                    'name': item_name,
                    'image_link': image_link,
                    'price': wholesale_price,
                    'unit': unit,
                    'stock_count': qty_on_hand,
                    'status': item_status,
                    'expiry_date': expiry_date,
                }
                
                # Group by status
                if item_status in products_by_status:
                    products_by_status[item_status].append(product)
            
            logger.info(f"Fetched {len(products_by_status.get('In-Stock', []))} In-Stock and {len(products_by_status.get('On The Way', []))} On The Way products")
            return products_by_status
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
    def get_in_stock_products(self):
        """Get all in-stock products."""
        return self.get_products_by_status("In-Stock")
    
    def get_on_the_way_products(self):
        """Get all on-the-way products."""
        return self.get_products_by_status("On The Way")


# Create a singleton instance
sheets_service = GoogleSheetsService()
