from datetime import datetime
from app import app, db
from models import MonthPeriod

def parse_date(date_str):
    """Parse date string in format DD/MM/YYYY to Python date object"""
    day, month, year = map(int, date_str.split('/'))
    return datetime(year, month, day).date()

def initialize_month_periods():
    """Initialize month periods from the provided data"""
    with app.app_context():
        # Delete existing month periods to avoid duplicates
        MonthPeriod.query.delete()
        db.session.commit()
        
        # Month data as provided (month_code, start_date, end_date, days, hours)
        months_data = [
            ("12/24", "20/11/2024", "31/12/2024", 31, 248),
            ("01/25", "26/12/2024", "25/01/2025", 31, 248),
            ("02/25", "26/01/2025", "22/02/2025", 28, 224),
            ("03/25", "23/02/2025", "25/03/2025", 31, 248),
            ("04/25", "26/03/2025", "24/04/2025", 30, 240),
            ("05/25", "25/04/2025", "25/05/2025", 31, 248),
            ("06/25", "26/05/2025", "24/06/2025", 30, 240),
            ("07/25", "25/06/2025", "25/07/2025", 31, 248),
            ("08/25", "26/07/2025", "25/08/2025", 31, 248),
            ("09/25", "26/08/2025", "24/09/2025", 30, 240),
            ("10/25", "25/09/2025", "25/10/2025", 31, 248),
            ("11/25", "26/10/2025", "24/11/2025", 30, 240),
            ("12/25", "25/11/2025", "25/12/2025", 31, 248),
        ]
        
        # Create and add month periods
        for month_code, start_date, end_date, days, hours in months_data:
            month_period = MonthPeriod(
                month_code=month_code,
                start_date=parse_date(start_date),
                end_date=parse_date(end_date),
                days_in_month=days,
                hours_in_month=hours
            )
            db.session.add(month_period)
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully added {len(months_data)} month periods")

if __name__ == "__main__":
    initialize_month_periods()