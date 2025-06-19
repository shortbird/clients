import csv
import datetime
import os
import json
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    abort,
)
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email
import gspread
from google.oauth2.service_account import Credentials


clients_bp = Blueprint(
    "clients", __name__, template_folder="templates", static_folder="static"
)

# --- Partner Data ---
PARTNERS = {
    "timshel": {
        "template": "timshel.html",
        "partner_name": "Timshel",
        "logo_file": "images/timshel_logo.png",
    },
    "founder-studio": {
        "template": "founder_studio.html",
        "partner_name": "Founder Studio",
        "logo_file": "images/founder_studio_logo.png",
    },
    "trailhead": {
        "template": "trailhead_landing_page.html",
        "partner_name": "Trailhead",
        "logo_file": "images/trailhead_logo.png",
    },
}

# --- Domain Mapping ---
DOMAIN_PARTNER_MAP = {
    "trailheadschool.org": "trailhead",
    "founderstudio.org": "founder-studio",
    "timsheleducation.org": "timshel",
}

class RequestInfoForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    phone = StringField("Phone")
    partner_name = HiddenField("Partner Name")
    submit = SubmitField("Request Information")

# --- Google Sheets Integration ---

def get_google_sheet_client():
    """
    Authenticates with Google Sheets API using credentials from an
    environment variable (for Vercel) or a local file.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    creds_json_str = os.environ.get('GOOGLE_CREDENTIALS')
    
    try:
        if creds_json_str:
            creds_info = json.loads(creds_json_str)
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
        client = gspread.authorize(creds)
        return client
    except FileNotFoundError:
        print("!!! ERROR: credentials.json not found. Make sure it's in the project root for local development. !!!")
        return None
    except json.JSONDecodeError:
        print("!!! ERROR: Could not parse GOOGLE_CREDENTIALS environment variable. !!!")
        return None


def save_lead_to_sheet(form, partner_name):
    """Saves lead information to a Google Sheet."""
    client = get_google_sheet_client()
    if not client:
        print("!!! Could not get Google Sheets client. Aborting save. !!!")
        return

    try:
        # !!! IMPORTANT: Replace this string with the exact name of your Google Sheet !!!
        sheet_name = "Your Google Sheet Name"
        sheet = client.open(sheet_name).sheet1
        
        # Check if the sheet is empty and add a header row if needed
        if not sheet.get_all_records():
            header = ['timestamp', 'full_name', 'email', 'phone', 'partner']
            sheet.append_row(header)
            
        full_name = f"{form.first_name.data} {form.last_name.data}"
        row_to_insert = [
            datetime.datetime.now().isoformat(),
            full_name,
            form.email.data,
            form.phone.data,
            partner_name
        ]
        sheet.append_row(row_to_insert)
        print(f"--- Successfully wrote lead for {partner_name} to Google Sheet '{sheet_name}'. ---")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"!!! ERROR: Spreadsheet '{sheet_name}' not found. Make sure the name is correct and it's shared with your service account's client_email. !!!")
    except Exception as e:
        print(f"!!! ERROR writing to Google Sheet: {e} !!!")


def get_partner_data_with_url(partner_id):
    partner = PARTNERS.get(partner_id)
    if not partner:
        return None
    
    partner_data = partner.copy()
    partner_data["logo_url"] = url_for(
        "clients.static", filename=partner_data["logo_file"]
    )
    return partner_data


@clients_bp.route("/")
def home():
    hostname = request.host.split(":")[0].lower()
    if "localhost" in hostname or "127.0.0.1" in hostname:
        return render_template("local_test_index.html", partners=PARTNERS)

    base_hostname = hostname.replace("www.", "")
    partner_id = DOMAIN_PARTNER_MAP.get(base_hostname)

    if partner_id:
        partner_data = get_partner_data_with_url(partner_id)
        if partner_data:
            form = RequestInfoForm(partner_name=partner_data["partner_name"])
            return render_template(
                partner_data["template"], partner=partner_data, form=form
            )
            
    trailhead_data = get_partner_data_with_url("trailhead")
    if trailhead_data:
        form = RequestInfoForm(partner_name=trailhead_data["partner_name"])
        return render_template("trailhead_landing_page.html", partner=trailhead_data, form=form)
    else:
        abort(404)


@clients_bp.route("/partner/<partner_id>")
def partner_landing_page(partner_id):
    partner_data = get_partner_data_with_url(partner_id)
    if not partner_data:
        abort(404)
    form = RequestInfoForm(partner_name=partner_data["partner_name"])
    return render_template(
        partner_data["template"], partner=partner_data, form=form
    )


@clients_bp.route("/request-info", methods=["POST"])
def request_info():
    form = RequestInfoForm()
    partner_name = form.partner_name.data

    if form.validate_on_submit():
        save_lead_to_sheet(form, partner_name)
        return redirect(url_for("clients.thank_you"))

    partner_id = None
    for pid, pdata in PARTNERS.items():
        if pdata["partner_name"] == partner_name:
            partner_id = pid
            break
    
    if partner_id:
        partner_data = get_partner_data_with_url(partner_id)
        return render_template(partner_data["template"], partner=partner_data, form=form)
    return "Error processing request.", 400


@clients_bp.route("/thank-you")
def thank_you():
    return render_template("request_info_thank_you.html")