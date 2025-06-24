import os
import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, Blueprint
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Email, Optional
import gspread
from google.oauth2.service_account import Credentials

# Create the blueprint object
clients_bp = Blueprint('clients', __name__, template_folder='templates')

class InfoRequestForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional()])

def get_google_sheet_client():
    """Authenticates with Google and returns the gspread client."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json_str:
        print("Found GOOGLE_CREDENTIALS environment variable. Using for authentication.")
        creds_info = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    else:
        # --- UPDATED LOCAL DIAGNOSTICS ---
        print("GOOGLE_CREDENTIALS environment variable not found. Looking for local 'credentials.json' file...")
        try:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            print("Successfully loaded local 'credentials.json' file.")
        except FileNotFoundError:
            print("---!!! ERROR !!!---")
            print("Could not find 'credentials.json' file in the root directory.")
            print("Please ensure the file exists and you are running 'flask run' from the main project folder.")
            print("-------------------")
            return None # Stop execution if credentials can't be found
        
    return gspread.authorize(creds)

def save_lead_to_sheet(form, partner_name):
    """Saves a lead's information to the designated Google Sheet."""
    client = get_google_sheet_client()
    if not client:
        flash("Could not connect to Google Sheets due to a local credential error. See terminal for details.", "error")
        return False

    try:
        sheet_name = os.getenv("GOOGLE_SHEET_NAME")
        if not sheet_name:
            sheet_name = "Your Google Sheet Name" 
            print("GOOGLE_SHEET_NAME environment variable not set. Using default sheet name.")
        
        # --- NEW DIAGNOSTIC PRINT STATEMENT ---
        print(f"--> Attempting to open Google Sheet named: '{sheet_name}'")
        
        sheet = client.open(sheet_name).sheet1
        
        print(f"Successfully opened sheet: '{sheet_name}'")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_name = f"{form.first_name.data} {form.last_name.data}"
        email = form.email.data
        phone = form.phone.data
        
        row = [timestamp, full_name, email, phone, partner_name]
        sheet.append_row(row)
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        print("---!!! ERROR !!!---")
        print(f"Spreadsheet named '{sheet_name}' was not found.")
        print("Please check two things:")
        print("1. The sheet name is spelled exactly correct (it is case-sensitive).")
        print(f"2. The sheet has been shared with the service account email: {client.auth.service_account_email}")
        print("-------------------")
        flash("The Google Sheet was not found. Please check your local configuration.", "error")
        return False
    except Exception as e:
        flash("An error occurred while saving your information.", "error")
        print(f"ERROR saving to Google Sheet: {e}")
        return False

# The rest of your routes remain the same...

@clients_bp.route('/')
def home():
    return redirect(url_for('.view_founder_studio'))

@clients_bp.route('/founder-studio')
def view_founder_studio():
    form = InfoRequestForm()
    return render_template('founder_studio.html', form=form)

@clients_bp.route('/timshel')
def view_timshel():
    form = InfoRequestForm()
    return render_template('timshel.html', form=form)

@clients_bp.route('/trailhead')
def view_trailhead():
    form = InfoRequestForm()
    dummy_partner = {'id': 'trailhead'}
    return render_template('trailhead_landing_page.html', form=form, partner=dummy_partner)

@clients_bp.route('/request-info', methods=['POST'])
def request_info():
    form = InfoRequestForm()
    if form.validate_on_submit():
        partner_name = request.form.get('partner_name', 'Unknown Partner')
        if save_lead_to_sheet(form, partner_name):
            return redirect(url_for('.request_info_thank_you'))
        else:
            return redirect(request.referrer or url_for('.home'))
    else:
        for field, errors in form.errors.items():
            label = getattr(form, field).label.text
            for error in errors:
                flash(f"Error in the {label} field - {error}", "error")
        return redirect(request.referrer or url_for('.home'))

@clients_bp.route('/request-info-thank-you')
def request_info_thank_you():
    return render_template('request_info_thank_you.html')