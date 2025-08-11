# Personal Finance Tracker

A simple and secure personal finance tracking web application built with Flask and SQLite. Track your income, expenses, manage categories, view detailed transaction history, and visualize your financial data with charts and exports.

---

## Features

- **User Authentication:** Register, login, and logout securely with password hashing.
- **Transaction Management:** Add, edit, delete income and expense transactions.
- **Category Management:** Create, edit, and delete transaction categories personalized for each user.
- **Dashboard:** Overview of total income, expenses, balance, and recent transactions.
- **Search & Pagination:** Search transactions by description, category, or type with pagination support.
- **Data Export:** Export your transaction history to CSV or PDF formats.
- **Visual Reports:** Monthly income vs expense summary chart powered by Chart.js.
- **Secure:** CSRF protection and user-based data isolation.

---

## Technologies Used

- Python 3
- Flask
- Flask-Login
- Flask-WTF
- SQLAlchemy (SQLite database)
- WTForms
- ReportLab (PDF generation)
- Chart.js (data visualization)
- Bootstrap 5 (responsive UI)

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/finance-tracker.git
   cd finance-tracker


Create and activate a virtual environment

python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

Install dependencies
pip install -r requirements.txt

Run the application
flask run

he app will be accessible at http://127.0.0.1:5000.



Usage
Register a new user account.

Login and start adding income and expense transactions.

Manage your transaction categories.

View dashboard for summary and recent activity.

Export your data for backup or offline analysis.

Use the search bar on transactions page to filter records.


Project Structure

finance-tracker/
│
├── app.py                 # Main Flask application and routes
├── templates/             # HTML templates (Jinja2)
├── static/
│   ├── css/               # CSS files
│   └── js/                # JavaScript files
├── requirements.txt       # Python dependencies
└── README.md

   
Notes

The app uses a local SQLite database (finance.db). For production, consider using a more robust DBMS.

Change the SECRET_KEY in app.py to a secure environment variable for production.

The PDF export feature uses ReportLab and generates simple transaction reports.

Bootstrap 5 ensures the UI is responsive and mobile-friendly.

License
This project is open source and available under the MIT License.


Acknowledgements
Flask official documentation: https://flask.palletsprojects.com/

ReportLab documentation: https://www.reportlab.com/docs/

Chart.js: https://www.chartjs.org/

Bootstrap: https://getbootstrap.com/

If you have any questions or want to contribute, feel free to open an issue or pull request!


---

If you want, I can help you generate a `requirements.txt` based on your imports or  create deployment instructions for hosting (e.g., Render or Heroku).
