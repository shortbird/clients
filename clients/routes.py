import csv
import datetime
import os
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

clients_bp = Blueprint(
    "clients", __name__, template_folder="templates", static_folder="static"
)

# --- Partner Data (Replaces Notion Database) ---
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

# Map production domains to partner IDs
DOMAIN_PARTNER_MAP = {
    "trailheadschool.org": "trailhead",
    "founderstudio.org": "founder-studio",
    "timsheleducation.org": "timshel",
}


class RequestInfoForm(FlaskForm):
    """Form for users to request information."""
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    # Added the phone field to match the templates
    phone = StringField("Phone") 
    partner_name = HiddenField("Partner Name")
    submit = SubmitField("Request Information")


def save_lead_to_csv(form, partner_name):
    """Saves lead information to a CSV file."""
    file_path = 'leads.csv'
    file_exists = os.path.isfile(file_path)
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
            # Added 'phone' to the fieldnames
            fieldnames = ['timestamp', 'full_name', 'email', 'phone', 'partner']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            full_name = f"{form.first_name.data} {form.last_name.data}"
            writer.writerow({
                'timestamp': datetime.datetime.now().isoformat(),
                'full_name': full_name,
                'email': form.email.data,
                'phone': form.phone.data, # Save the phone number
                'partner': partner_name
            })
            print(f"--- Successfully wrote lead for {partner_name} to {file_path} ---")
    except IOError as e:
        print(f"!!! ERROR writing to CSV file: {e} !!!")


def get_partner_data_with_url(partner_id):
    """Gets partner data and dynamically adds the logo_url."""
    partner = PARTNERS.get(partner_id)
    if not partner:
        return None
    
    partner_data = partner.copy()
    partner_data["logo_url"] = url_for(
        "clients.static", filename=partner_data["logo_file"], _external=True
    )
    return partner_data


@clients_bp.route("/")
def home():
    """
    Determines which landing page to show based on the hostname.
    """
    hostname = request.host.split(":")[0].lower()

    # Local development check
    if "localhost" in hostname or "127.0.0.1" in hostname:
        return render_template("local_test_index.html", partners=PARTNERS)

    # Production logic: determine partner from domain
    base_hostname = hostname.replace("www.", "")
    
    partner_id = DOMAIN_PARTNER_MAP.get(base_hostname)

    if partner_id:
        partner_data = get_partner_data_with_url(partner_id)
        if partner_data:
            form = RequestInfoForm(partner_name=partner_data["partner_name"])
            return render_template(
                partner_data["template"], partner=partner_data, form=form
            )
            
    # Default to Trailhead if no specific partner domain is matched
    trailhead_data = get_partner_data_with_url("trailhead")
    if trailhead_data:
        form = RequestInfoForm(partner_name=trailhead_data["partner_name"])
        return render_template("trailhead_landing_page.html", partner=trailhead_data, form=form)
    else:
        abort(404)


@clients_bp.route("/partner/<partner_id>")
def partner_landing_page(partner_id):
    """
    Renders a specific partner's landing page.
    """
    partner_data = get_partner_data_with_url(partner_id)
    if not partner_data:
        abort(404)

    form = RequestInfoForm(partner_name=partner_data["partner_name"])
    return render_template(
        partner_data["template"], partner=partner_data, form=form
    )


@clients_bp.route("/request-info", methods=["POST"])
def request_info():
    """Handles the form submission for requesting information."""
    form = RequestInfoForm()
    partner_name = form.partner_name.data

    if form.validate_on_submit():
        save_lead_to_csv(form, partner_name)
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
    """Displays a thank you page after form submission."""
    return render_template("request_info_thank_you.html")