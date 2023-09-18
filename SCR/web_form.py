from flask import Flask, render_template, redirect, url_for, jsonify
from flask_bootstrap import Bootstrap5

from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField, SelectField, SelectMultipleField, BooleanField, \
    DecimalField
from wtforms.validators import DataRequired, Length, NumberRange

import secrets
import os
import datetime as dt

import regions
import custom_experiments

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

selection_dict = {
    'models': custom_experiments.experiment_configurations,
    'regions': regions.regions,
}

def get_default_name():
    return "MyPanel_{:s}".format(dt.datetime.now().strftime("%Y-%m-%d_%H%M%S"))


def get_choices_for_models():
    model_dict = custom_experiments.experiment_configurations
    model_choices = [(ii, key) for ii, (key, model) in enumerate(model_dict.items())]
    return model_choices


def get_choices_for_regions():
    region_choices = [key for key in regions.regions]
    return region_choices


def get_subdomain_choices(region_name):
    subdomain_choices = [(ii, key) for ii, key in enumerate(
        regions.regions[region_name]['verification_subdomains'])]
    return subdomain_choices


class PanelificationRequest(FlaskForm):
    name = StringField("Custom Name", default=get_default_name(), 
        validators=[DataRequired(), Length(1, 100)])
    start = StringField("Start date as yyyymmddHH", 
        validators=[DataRequired(), Length(10, 10)])
    duration = DecimalField("Duration in hours", 
        validators=[DataRequired(), NumberRange(0, 999)])
    min_lead = DecimalField("Minimum Lead Time in hours", 
        validators=[NumberRange(0, 999)])
    max_lead = DecimalField("Maximum Lead Time in hours", 
        validators=[DataRequired(), NumberRange(0, 999)])
    region_choices = get_choices_for_regions()
    region = SelectField('Region', choices=region_choices, default='Austria')
    verification_subdomain = SelectMultipleField('Verification Subdomain', 
        choices = get_subdomain_choices(region_choices[1]), default=[0])
    models = SelectMultipleField(choices=get_choices_for_models(), default=[0, 1, 2])
    sorting = SelectField(choices=['default', 'model', 'init'], default='default')
    draw_subdomain = BooleanField(default="checked")
    draw = BooleanField(default="checked")
    forcedraw = BooleanField(default="checked")
    forcescore = BooleanField(default="checked")
    draw_p90 = BooleanField()
    clean = BooleanField()
    hidden = BooleanField()
    mode = SelectField(choices=['None', 'resampled'], default='None')
    fix_nans = BooleanField()
    save = BooleanField()
    fss_mode = SelectField(choices=['ranks', 'relative'], default='ranks')
    rank_core_time_series = BooleanField()
    rank_by_fss_metric = SelectField(choices=['fss_condensed_weighted', 'fss_condensed', 'fss_total_abs_score'],
        default='fss_condensed_weighted')
    save_full_fss = BooleanField()
    logfile = StringField(default="", validators=[Length(0, 100)])
    loglevel = SelectField(choices=['critical', 'error', 'warning', 'info', 'debug'], default='info')
    submit = SubmitField('Submit')

def make_panelification_command(form):
    command_start = "python main.py "
    command_name = "--name {:s} ".format(form.name.data) if len(form.name.data) > 0 else ""
    command_string = command_start + command_name
    if len(form.min_lead.data) > 0:
        lead_string = "-l {:s} {:s}".format(form.min_lead.data, form.max_lead.data)
    else:
        lead_string = "-l {:s}".format(form.max_lead.data)
    command_body = "-s {:s} -d {:s} {:s} --region {:s}".format(
        form.start.data, form.duration.data, lead_string, form.region.data, form.verification_subdomain.data)
    # add subdomains
    subdomain_string += "--verification_subdomains "
    for sd in form.form.verification_subdomain.data.data:
        subdomain_string += " {:s} ".format(models[mod])
    command_string += subdomain_string
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
        print("Executing panel command:")
        print(message)
        os.system(message)
    else:
        message = "That was not OK"
    return render_template('index.html', names=names, form=form, message=message)


@app.route('/subdomain/<region>')
def subdomains(region):
    print(region)
    subdomains = regions.regions[region]["verification_subdomains"]
    subdomain_array = []
    print(regions.regions[region])
    print(regions.regions[region]['verification_subdomains'])
    ii = 0
    for sd_name, _ in regions.regions[region]['verification_subdomains'].items():
        new_subdomain_object = {}
        new_subdomain_object['id'] = ii
        new_subdomain_object['name'] = sd_name
        print("Appending: ", new_subdomain_object)
        subdomain_array.append(new_subdomain_object)
        ii += 1

    return jsonify({'verification_subdomains': subdomain_array})

