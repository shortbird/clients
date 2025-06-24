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
    
    # --- UPDATED LOGIC FOR PRODUCTION ---
    # In production (like on Vercel), load credentials from an environment variable.
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json_str:
        creds_info = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    else:
        # Fallback for local development: use the credentials.json file.
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
    return gspread.authorize(creds)

def save_lead_to_sheet(form, partner_name):
    """Saves a lead's information to the designated Google Sheet."""
    try:
        client = get_google_sheet_client()
        
        # --- UPDATED LOGIC FOR PRODUCTION ---
        # Get the sheet name from an environment variable.
        sheet_name = os.getenv("GOOGLE_SHEET_NAME")
        if not sheet_name:
            # Fallback for local development
            sheet_name = "Your Google Sheet Name" 
            
        sheet = client.open(sheet_name).sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_name = f"{form.first_name.data} {form.last_name.data}"
        email = form.email.data
        phone = form.phone.data
        
        row = [timestamp, full_name, email, phone, partner_name]
        sheet.append_row(row)
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        flash("The Google Sheet was not found. Please check the configuration.", "error")
        print("ERROR: Spreadsheet not found. Make sure the name is correct and the service account has access.")
        return False
    except Exception as e:
        flash("An error occurred while saving your information.", "error")
        print(f"ERROR saving to Google Sheet: {e}")
        return False

# The rest of your routes remain the same...

@clients_bp.route('/')
def home():
    """
    Acts as the main router.
    For simplicity, this now redirects to a default page since Notion is removed.
    """
    # Redirecting to a default landing page for demonstration
    return redirect(url_for('.view_founder_studio'))

@clients_bp.route('/founder-studio')
def view_founder_studio():
    """Renders the Founder Studio landing page."""
    form = InfoRequestForm()
    return render_template('founder_studio.html', form=form)

@clients_bp.route('/timshel')
def view_timshel():
    """Renders the Timshel landing page."""
    form = InfoRequestForm()
    return render_template('timshel.html', form=form)

@clients_bp.route('/trailhead')
def view_trailhead():
    """Renders the Trailhead landing page."""
    form = InfoRequestForm()
    dummy_partner = {'id': 'trailhead'}
    return render_template('trailhead_landing_page.html', form=form, partner=dummy_partner)

@clients_bp.route('/request-info', methods=['POST'])
def request_info():
    """Handles the info request form submission for all partners."""
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