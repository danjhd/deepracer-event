import json
import os
import boto3
import requests
from io import BytesIO
from aws_xray_sdk.core import patch_all
from botocore.exceptions import ClientError
from flask import flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename
from app import app
from app.forms import RoleForm, S3Form
from flask_babel import _

patch_all()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html.j2', title='Deep Racer Model Uploader')

@app.route('/role', methods=['GET'])
def role():
    form = RoleForm()
    return render_template('role.html.j2', title='Deep Racer Model Uploader', form=form, account_id=os.environ['AWS_ACCOUNT_ID'])

@app.route('/downloads/<path>')
def downloadFile (path):
    pathFull = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads', path)
    f = open(pathFull, mode='r')
    fileContent = f.read()
    f.close()
    fileContent = fileContent.replace('{{ EventAccountId }}', os.environ['AWS_ACCOUNT_ID'])
    mem = BytesIO()
    mem.write(fileContent.encode('utf-8'))
    mem.seek(0)
    return send_file(mem, attachment_filename=path, as_attachment=True)

@app.route('/model', methods=['GET'])
def model():
    if 'rolearn' not in request.args:
        return redirect(url_for('role'))
    response = requests.get(f"{app.config['WEBSERVICE_ENDPOINT']}/models?RoleArn={request.args.get('rolearn')}", headers={'x-api-key': app.config['API_KEY']})
    if response.status_code != 200:
        if 'errorMessage' in response.json():
            flash(response.json()['errorMessage'], category='danger')
        else:
            flash(response.json(), category='danger')
        return redirect(url_for('role'))
    models = response.json()['models']
    print(json.dumps(models))
    models = [m.update({'id': n}) or m for n, m in enumerate(models)]
    if len(models) == 0:
        flash(_('No Models were found. Please verify the account has Deep Racer models and the IAM role supplied has the correct permissions to access them.'), category='warning')
    return render_template('model.html.j2', title='Deep Racer Model Uploader', icons=app.config['WEB_ICONS'], models=models)

@app.route('/s3', methods=['GET', 'POST'])
def s3():
    form = S3Form()
    if form.validate_on_submit():
        if not form.modelfile.data.filename.endswith('.tar.gz'):
            flash(_('You selected a file with an invalid filename. Please ensure you select a downloaded model file with extension .tar.gz'), category='danger')
        else:
            destination_key = f'{form.modelfile.data.filename[:-7]}-{form.accountid.data}.tar.gz'
            try:
                s3 = boto3.resource('s3')
                s3.Object(app.config['DESTINATION_BUCKET'], destination_key).metadata
                flash(_('A model with the same name already exists, file upload cancelled.'), category='warning')
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    form.modelfile.data.save(secure_filename(destination_key))
                    with open(secure_filename(destination_key), 'rb') as f:
                        boto3.client('s3').upload_fileobj(f, app.config['DESTINATION_BUCKET'], destination_key)
                    os.remove(secure_filename(destination_key))
                    flash(_('File successfully uploaded.'), category='success')
                else:
                    raise e
    return render_template('s3.html.j2', title='Deep Racer Model Uploader', form=form)

@app.route('/action', methods=['POST'])
def model_action():
    request_url = f"{app.config['WEBSERVICE_ENDPOINT']}/models/{request.form['model_id']}?RoleArn={request.form['role_arn']}"
    if request.form['action'] == 'Upload':
        response = requests.get(request_url, headers={'x-api-key': app.config['API_KEY']})
        status_title = _('Model is present')
        status_icon = app.config['WEB_ICONS']['tick']
        action_title = _('Delete')
        action_icon = app.config['WEB_ICONS']['delete']
    elif request.form['action'] == 'Delete':
        response = requests.delete(request_url, headers={'x-api-key': app.config['API_KEY']})
        status_title = _('Model is not present')
        status_icon = app.config['WEB_ICONS']['cross']
        action_title = _('Upload')
        action_icon = app.config['WEB_ICONS']['upload']
    if response.status_code != 200:
        raise Exception('API request did not return 200 status.')
    print(response.status_code)
    print(response.json())
    if response.json()['message'] in ['Model deleted.', 'Model uploaded.']:
        status_html = f'<span data-toggle="tooltip" title="{status_title}">{status_icon}</span>'
        action_html = f"<a data-toggle=\"tooltip\" title=\"{action_title} model\" href=\"javascript:modelAction(\'{request.form['id']}\', \'{action_title}\', \'{request.form['model_id']}\');\">{action_icon}</a>"
    else:
        status_html = ''
        action_html = ''
    return {
        'message': response.json()['message'],
        'status_html': status_html,
        'action_html': action_html
    }
