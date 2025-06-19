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
# Store partner information directly in this dictionary.
# The key is the subdomain/path id (e.g., 'timshel').
PARTNERS = {
    "timshel": {
        "template": "timshel.html",
        "partner_name": "Timshel",
        "logo_url": url_for('clients.static', filename='images/timshel_logo.png', _external=True)
    },
    "founder-studio": {
        "template": "founder_studio.html",
        "partner_name": "Founder Studio",
        "logo_url": url_for('clients.static', filename='images/founder_studio_logo.png', _external=True)
    },
    "trailhead": {
        "template": "trailhead_landing_page.html",
        "partner_name": "Trailhead",
        "logo_url": url_for('clients.static', filename='images/trailhead_logo.png', _external=True)
    },
    # --- Add new partners here ---
    # "new-partner-id": {
    #     "template": "new_partner_template.html",
    #     "partner_name": "New Partner Name",
    #     "logo_url": url_for('clients.static', filename='images/new_logo.png', _external=True)
    # },
}


class RequestInfoForm(FlaskForm):
    """Form for users to request information."""
    name = StringField("Full Name", validators=[DataRequired()])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    partner_name = HiddenField("Partner Name")
    submit = SubmitField("Request Information")


def save_lead_to_csv(form, partner_name):
    """Saves lead information to a CSV file."""
    file_path = 'leads.csv'
    # Check if the file exists to determine if we need to write headers
    file_exists = os.path.isfile(file_path)

    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'name', 'email', 'partner']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()  # Write header only once

            writer.writerow({
                'timestamp': datetime.datetime.now().isoformat(),
                'name': form.name.data,
                'email': form.email.data,
                'partner': partner_name
            })
    except IOError as e:
        print(f"Error writing to CSV file: {e}")


@clients_bp.route("/")
def home():
    """
    Determines which landing page to show based on the hostname.
    """
    hostname = request.host.split(":")[0]  # Get hostname without port
    # Handle localhost and custom domains
    if "localhost" in hostname or "127.0.0.1" in hostname:
         # For local testing, render a simple index page
         # with links to the partner pages.
        return render_template("local_test_index.html", partners=PARTNERS)

    # Extract subdomain (e.g., 'timshel' from 'timshel.yourdomain.com')
    subdomain = hostname.split(".")[0]

    partner = PARTNERS.get(subdomain)
    if partner:
        form = RequestInfoForm(partner_name=partner["partner_name"])
        return render_template(
            partner["template"], partner=partner, form=form
        )
    else:
        # Default fallback page if no partner matches the subdomain
        return render_template("trailhead_landing_page.html")


@clients_bp.route("/partner/<partner_id>")
def partner_landing_page(partner_id):
    """
    Renders a specific partner's landing page.
    Useful for local testing, e.g., /partner/timshel
    """
    partner = PARTNERS.get(partner_id)
    if not partner:
        abort(404)  # Partner not found

    form = RequestInfoForm(partner_name=partner["partner_name"])
    return render_template(
        partner["template"], partner=partner, form=form
    )


@clients_bp.route("/request-info", methods=["POST"])
def request_info():
    """Handles the form submission for requesting information."""
    form = RequestInfoForm()
    # The partner name is submitted via a hidden field in the form
    partner_name = form.partner_name.data

    if form.validate_on_submit():
        # Save the lead information to our new CSV function
        save_lead_to_csv(form, partner_name)
        # Redirect to a generic thank you page
        return redirect(url_for("clients.thank_you"))

    # If form validation fails, we need to re-render the correct partner page
    # We find the partner_id by looking for a matching partner_name
    partner_id = None
    for pid, pdata in PARTNERS.items():
        if pdata["partner_name"] == partner_name:
            partner_id = pid
            break
    
    if partner_id:
        partner = PARTNERS.get(partner_id)
        # Re-render the form with validation errors
        return render_template(partner["template"], partner=partner, form=form)

    # Fallback if something goes wrong
    return "Error processing request.", 400


@clients_bp.route("/thank-you")
def thank_you():
    """Displays a thank you page after form submission."""
    return render_template("request_info_thank_you.html")
