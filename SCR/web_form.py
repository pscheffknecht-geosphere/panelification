from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap5

from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField, SelectField, SelectMultipleField, BooleanField 
from wtforms.validators import DataRequired, Length

import secrets
import os

app = Flask(__name__)

bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)

foo = secrets.token_urlsafe(16)
app.secret_key = foo

models = {
    '1': 'arome',
    '2': 'aromeruc',
    '3': 'claef-control',
    '4': 'claef1k-control'
}
model_choices = [(key, model) for key, model in models.items()]

class PanelificationRequest(FlaskForm):
    name = StringField("Custom Name", validators=[DataRequired(), Length(1, 100)])
    start = StringField("Start date as yyyymmddHH", validators=[DataRequired(), Length(10, 10)])
    duration = StringField("Duration in hours", validators=[DataRequired(), Length(1, 2)])
    min_lead = StringField("Minimum Lead Time in hours", validators=[Length(0, 2)])
    max_lead = StringField("Maximum Lead Time in hours", validators=[DataRequired(), Length(1, 2)])
    region = SelectField('Region', choices=['Austria', 'Finland'])
    verification_subdomain = SelectField('Verification Subdomain', choices = [
        "Default", "NorthWest", "SouthEast"])
    models = SelectMultipleField(choices = model_choices, default=[0, 1, 2])
    forcedraw = BooleanField(default = "checked")
    submit = SubmitField('Submit')

def make_panelification_command(form):
    command_start = "python main.py "
    command_name = "--name {:s} ".format(form.name.data) if len(form.name.data) > 0 else ""
    command_string = command_start + command_name
    if len(form.min_lead.data) > 0:
        lead_string = "-l {:s} {:s}".format(form.min_lead.data, form.max_lead.data)
    else:
        lead_string = "-l {:s}".format(form.max_lead.data)
    command_body = "-s {:s} -d {:s} {:s} --region {:s} --subdomains {:s} ".format(
        form.start.data, form.duration.data, lead_string, form.region.data, form.verification_subdomain.data)
    command_string += command_body
    model_string = "--custom_experiments "
    for mod in form.models.data:
        model_string += "{:s} ".format(models[mod])
    command_string += model_string
    print(form.forcedraw.data)
    if form.forcedraw.data:
        print("Adding forcedraw")
        command_string += "--forcedraw "
    return command_string


@app.route('/', methods=['GET', 'POST'])
def panelify():
    form = PanelificationRequest()
    names = ['bogus', 'names']
    message = ""
    if form.validate_on_submit():
        message = make_panelification_command(form)
        os.system(message)
    else:
        message = "That was not OK"
    return render_template('index.html', names=names, form=form, message=message)
