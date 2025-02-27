import time
from flask import Flask, render_template, redirect, url_for, jsonify
from flask_bootstrap import Bootstrap5

from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField, SelectField, SelectMultipleField, BooleanField, \
    DecimalField
from wtforms.validators import DataRequired, Length, NumberRange, InputRequired

import secrets
import glob
import subprocess
import datetime as dt

import regions
import custom_experiments

app = Flask(__name__)

bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)

foo = secrets.token_urlsafe(16)
app.secret_key = foo

ALL_PARAMETERS = ["precip" , "precip2" , "precip3", "sunshine" , "lightnning" , "hail" , "gusts"]
ALL_TIME_SERIES_OPTIONS = ["bias", "mae", "rms", "corr", "d90", "fss_condensed_weighted"]
def get_default_name():
    return "MyPanel_{:s}".format(dt.datetime.now().strftime("%Y-%m-%d_%H%M%S"))


def get_choices_for_models():
    model_dict = custom_experiments.experiment_configurations
    model_choices = [(str(ii), key) for ii, (key, _) in enumerate(model_dict.items())]
    return model_choices


def get_choices_for_regions():
    region_choices = [key for key in regions.regions]
    return region_choices


def get_subdomain_choices(region_name):
    subdomain_choices = [(str(ii), key) for ii, key in enumerate(
        regions.regions[region_name]['verification_subdomains'])]
    return subdomain_choices

def get_time_series_choices():
    time_series_choices = [(str(ii), key) for ii, key in enumerate(ALL_TIME_SERIES_OPTIONS)]
    return time_series_choices


class PanelificationRequest(FlaskForm):
    name = StringField(default=get_default_name(), 
        validators=[DataRequired(), Length(1, 100)])
    parameter = SelectField(choices=ALL_PARAMETERS, default=ALL_PARAMETERS[0])
    start = StringField("Start date as yyyymmddHH", 
        validators=[DataRequired(), Length(10, 10)], default="2023080418")
    duration = DecimalField(default=6,
        validators=[DataRequired(), NumberRange(0, 999)])
    min_lead = DecimalField(default=0, 
        validators=[InputRequired(), NumberRange(0, 999)])
    max_lead = DecimalField(default=6,
        validators=[InputRequired(), NumberRange(0, 999)])
    region_choices = get_choices_for_regions()
    region = SelectField(choices=region_choices, default='Austria')
    verification_subdomains = SelectMultipleField(
        choices=get_subdomain_choices(region_choices[2]), 
        default=['0'])
    model_choices = get_choices_for_models()
    models = SelectMultipleField(
        choices=model_choices, default=['0', '1'])
    sorting = SelectField(choices=['default', 'model', 'init'], default='default')
    draw_subdomain = BooleanField(default="checked")
    draw = BooleanField(default="checked")
    zoom_to_subdomain = BooleanField(default="unchecked")
    forcedraw = BooleanField(default="checked")
    forcescore = BooleanField(default="checked")
    draw_p90 = BooleanField()
    clean = BooleanField()
    hidden = BooleanField()
    mode = SelectField(choices=['normal', 'resampled'], default='normal')
    fix_nans = BooleanField()
    save = BooleanField()
    fss_mode = SelectField(choices=['ranks', 'relative'], default='ranks')
    # rank_score_time_series = BooleanField()
    rank_score_time_series = SelectMultipleField(
        choices=ALL_TIME_SERIES_OPTIONS, 
        default=['4'])
    rank_by_fss_metric = SelectField(
        choices=['fss_condensed_weighted', 'fss_condensed', 'fss_total_abs_score'], 
        default='fss_condensed_weighted')
    save_full_fss = BooleanField()
    logfile = StringField(default="", validators=[Length(0, 100)])
    loglevel = SelectField(choices=['critical', 'error', 'warning', 'info', 'debug'], default='info')
    submit = SubmitField('Submit')

def make_panelification_command(form):
    command_string = "python main.py "
    command_string += "--name {:s} ".format(form.name.data) if len(form.name.data) > 0 else ""
    command_string += "--parameter {:s} ".format(form.parameter.data)
    command_string += "-s {:s} -d {:d} ".format(form.start.data, int(form.duration.data))
    command_string += "-l {:d} {:d} ".format(int(form.min_lead.data), int(form.max_lead.data))
    command_string += "--region " + form.region.data + " "
    # # add subdomains
    command_string += "--subdomains "
    subdomain_choices = dict(get_subdomain_choices(form.region.data))
    for sd in form.verification_subdomains.data:
        command_string += " {:s} ".format(subdomain_choices[sd])
    command_string += "--custom_experiments "
    model_choices = dict(get_choices_for_models())
    for mod in form.models.data:
        command_string += "{:s} ".format(model_choices[mod])
    if form.sorting != "default":
        command_string += "--sorting "+form.sorting.data+" "
    # process boolean arguments:
    command_string += "--draw_subdomain " + str(form.draw_subdomain.data) + " "
    command_string += "--draw " + str(form.draw.data) + " "
    command_string += "--zoom_to_subdomain " +str(form.zoom_to_subdomain.data) + " "
    command_string += "--forcedraw " + str(form.forcedraw.data) + " "
    command_string += "--forcescore " + str(form.forcescore.data) + " "
    command_string += "--draw_p90 " + str(form.draw_p90.data) + " "
    command_string += "--clean " + str(form.clean.data) + " "
    command_string += "--hidden " + str(form.hidden.data) + " "
    command_string += "--fix_nans " + str(form.fix_nans.data) + " "
    command_string += "--save " + str(form.save.data) + " "
    command_string += "--rank_score_time_series " # + str(form.rank_score_time_series.data) + " "
    rank_score_time_series = dict(get_time_series_choices())
    for rts in form.rank_score_time_series.data:
        command_string += " {:s}".format(rts) + " "
        # command_string += " {:s}".format(rank_score_time_series[rts])
    command_string += "--save_full_fss " + str(form.save_full_fss.data) + " "
    command_string += "--fss_mode " + form.fss_mode.data + " "
    if len(form.logfile.data) > 0:
        logfile_name = form.logfile.data
        logfile_name = logfile_name if logfile_name.endwith(".log") else logfile_name + ".log"
        command_string += "--logfile " + logfile_name + " "
    command_string += "--loglevel " + form.loglevel.data + " "
    command_string += "--mode " + form.mode.data + " "
    command_string += "--rank_by_fss_metric " + form.rank_by_fss_metric.data + " "
    return command_string


def get_img_path(stdout_strings):
    for s in stdout_strings:
        if "File saved to:" in s:
            return s.split(':')[3].replace(" ", "")
    return "No image generated :("


@app.route('/', methods=['GET', 'POST'])
def panelify():
    form = PanelificationRequest()
    names = ['bogus', 'names']
    message = ""
    if form.validate_on_submit():
        message = make_panelification_command(form)
        proc = subprocess.Popen(
            message,
            # "for ii in $(seq 1 5); do sleep 1; echo $ii; done",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout_strings = []
        while proc.poll() is None:
            time.sleep(1)
        emptycounter = 0
        while emptycounter < 5:
            newline = proc.stderr.readline().rstrip().decode('UTF-8')
            if len(newline) < 5:
                emptycounter += 1
            stdout_strings.append(newline)
        img_path = get_img_path(stdout_strings)
        return render_template('index.html', names=names, form=form, 
            message=message, stdout=stdout_strings, img_path=img_path, img_name=img_path.split("/")[-1])

    else:
        message = "No valid command (yet?)"
        return render_template('index.html', names=names, form=form, 
            message=message, stdout=["No console output"], img_path="No image generated (yet?)")


@app.route('/browse_graphics')
def browse_panels():
    img_list = [x.replace("static/", "") for x in glob.glob("static/*.png")]
    return render_template('panels.html', panel_list=img_list)


@app.route('/subdomain/<region>')
def subdomains(region):
    subdomains = regions.regions[region]["verification_subdomains"]
    subdomain_array = []
    ii = 0
    for sd_name, _ in regions.regions[region]['verification_subdomains'].items():
        new_subdomain_object = {}
        new_subdomain_object['id'] = ii
        new_subdomain_object['name'] = sd_name
        subdomain_array.append(new_subdomain_object)
        ii += 1

    return jsonify({'verification_subdomains': subdomain_array})


if __name__ == "__main__":
    app.run()
