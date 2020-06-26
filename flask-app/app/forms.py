from aws_xray_sdk.core import patch_all
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

patch_all()

class RoleForm(FlaskForm):
    rolearn = StringField(
        _l('Please enter the Role Arn here:'),
        render_kw = {
            'placeholder': _l('Enter the AWS IAM Role arn'),
            'pattern': r'^arn:aws:iam::\d{12}:role/.+$',
            'title': _l('Must be a valid AWS IAM Role arn in the format: arn:aws:iam::{AccountId}:role/{RoleNameWithPath}')
        },
        validators = [DataRequired()]
    )
    submit = SubmitField(
        _l('Submit'),
        render_kw = {
            'onclick': 'loading();'
        }
    )

class S3Form(FlaskForm):
    accountid = StringField(
        _l('Account Id:'),
        render_kw = {
            'placeholder': _l('Enter the AWS Account Id'),
            'pattern': r'^\d{12}$',
            'title': _l('Must be a valid AWS Account Id. (12 digits e.g. 123456789012)'),
            'maxlength': 12
        },
        validators = [DataRequired(), Length(min=12,max=12)]
    )
    modelfile = FileField(
        _l('Model File'),
        render_kw = {
            'accept': '.tar.gz'
        },
        validators = [DataRequired()]
    )
    submit = SubmitField(
        _l('Upload'),
        render_kw = {
            'onclick': 'loading();'
        }
    )
