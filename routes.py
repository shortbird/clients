import os
from datetime import datetime, date, timedelta
from flask import render_template, request, redirect, url_for, flash, make_response, Blueprint
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, NumberRange, Optional
import notion_client
from app import notion

# Database IDs
leads_db_id = os.getenv("NOTION_LEADS_DB_ID")
partners_db_id = os.getenv("NOTION_PARTNERS_DB_ID")

class InfoRequestForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional()])
    submit = SubmitField('Request Information')

# Create the blueprint object
clients_bp = Blueprint('clients', __name__, template_folder='templates')

@clients_bp.route('/')
def home():
    """
    Acts as the main router.
    - If it's the main app domain or localhost, redirects to the core app's login.
    - If on a production partner domain, shows the specific partner page.
    """
    hostname = request.host.split(':')[0].lower()

    # --- UPDATED LOGIC ---
    # This now includes localhost and 127.0.0.1, redirecting them to the main app login.
    if hostname in ['mypathweaver.com', 'www.mypathweaver.com', 'localhost', '127.0.0.1']:
        return redirect(url_for('pathweaver.login'))

    if current_user.is_authenticated:
        return redirect(url_for('pathweaver.pathweaver_home'))

    # --- Production Partner Route (this code will no longer run on localhost) ---
    try:
        base_hostname = hostname.replace("www.", "")
        possible_domains = {hostname, base_hostname}
        partner_filter = {"or": [{"property": "Domain", "url": {"equals": d}} for d in list(possible_domains)]}
        partner_response = notion.databases.query(database_id=partners_db_id, filter=partner_filter).get("results")

        if partner_response:
            partner_page = partner_response[0]
            properties = partner_page.get("properties", {})
            template_file_obj = properties.get("TemplateFile", {}).get("rich_text", [])
            if template_file_obj:
                template_file = template_file_obj[0].get("text", {}).get("content")
                if template_file:
                    partner_name_list = properties.get("PartnerName", {}).get("title", [])
                    partner_name = partner_name_list[0].get("text", {}).get("content", "Unnamed Partner") if partner_name_list else "Unnamed Partner"

                    partner_data = {
                        "id": partner_page["id"],
                        "name": partner_name
                    }
                    form = InfoRequestForm()
                    return render_template(template_file, partner=partner_data, form=form)
    except Exception as e:
        print(f"ERROR routing for hostname '{hostname}': {e}")
    
    return "This page is not available.", 404


@clients_bp.route('/partner/<partner_id>')
def view_partner(partner_id):
    """Renders a specific partner's landing page, used for testing."""
    # This route might now be less useful since the index is bypassed, but we leave it.
    try:
        partner_page = notion.pages.retrieve(page_id=partner_id)
        properties = partner_page.get("properties", {})
        template_file_obj = properties.get("TemplateFile", {}).get("rich_text", [])

        if template_file_obj:
            template_file = template_file_obj[0].get("text", {}).get("content")
            if template_file:
                partner_name_list = properties.get("PartnerName", {}).get("title", [])
                partner_name = partner_name_list[0].get("text", {}).get("content", "Unnamed Partner") if partner_name_list else "Unnamed Partner"

                partner_data = {
                    "id": partner_page["id"],
                    "name": partner_name
                }
                form = InfoRequestForm()
                return render_template(template_file, partner=partner_data, form=form)
        
        return "Template file not specified for this partner in Notion.", 404
    except Exception as e:
        print(f"ERROR rendering partner page {partner_id}: {e}")
        return "Could not retrieve the partner page. Please check the ID and your Notion connection.", 404

# The rest of the file remains the same...

@clients_bp.route('/request_info/<partner_id>', methods=['POST'])
def request_info(partner_id):
    form = InfoRequestForm()
    if form.validate_on_submit():
        try:
            first_name = form.first_name.data
            last_name = form.last_name.data
            email = form.email.data
            phone = form.phone.data
            full_name = f"{first_name} {last_name}"

            notion.pages.create(
                parent={"database_id": leads_db_id},
                properties={
                    "LeadID": {"title": [{"text": {"content": f"{full_name} - Info Request"}}]},
                    "FirstName": {"rich_text": [{"text": {"content": first_name}}]},
                    "LastName": {"rich_text": [{"text": {"content": last_name}}]},
                    "Email": {"email": email},
                    "Phone": {"phone_number": phone or None},
                    "PartnerLink": {"relation": [{"id": partner_id}]}
                }
            )
            
            return redirect(url_for('.request_info_thank_you'))
        except Exception as e:
            print(f"Error processing info request: {e}")
            flash("An error occurred while submitting your request. Please try again later.", "error")
            return redirect(request.referrer or url_for('.home'))
    else:
        if form.errors:
            for field, errors in form.errors.items():
                label = getattr(form, field).label.text
                for error in errors:
                    flash(f"Error in the {label} field - {error}", "error")
        return redirect(request.referrer or url_for('.home'))

@clients_bp.route('/contact_submit', methods=['POST'])
def contact_submit():
    try:
        # Assuming 'name' is 'FirstName LastName'
        full_name = request.form.get('name')
        first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")
        email = request.form.get('email')
        phone = request.form.get('phone')
        today = date.today().isoformat()
        notion.pages.create(
            parent={"database_id": leads_db_id},
            properties={
                "LeadID": {"title": [{"text": {"content": f"{full_name} - {today}"}}]},
                "FirstName": {"rich_text": [{"text": {"content": first_name}}]},
                "LastName": {"rich_text": [{"text": {"content": last_name}}]},
                "Email": {"email": email},
                "Phone": {"phone_number": phone},
                "SubmissionDate": {"date": {"start": today}}
            }
        )
        flash("Thank you for your interest! We will be in touch shortly.")
    except Exception as e:
        print(f"Error submitting lead: {e}")
        flash("Sorry, there was an error submitting your request. Please try again.")
    return redirect(url_for('.home'))

@clients_bp.route('/request-info-thank-you')
def request_info_thank_you():
    return render_template('request_info_thank_you.html')