from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo

class SettingsForm(FlaskForm):
    hostname = StringField("HostName", validators=[DataRequired()])
    port = IntegerField("Port", validators=[DataRequired()])
    allowSelfSignedCerts = BooleanField("Allow self signed certificated")
    submit = SubmitField("Save Settings")
    


class AddDeviceForm(FlaskForm):
    devicename = StringField("Device Name", validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    confirmPassword = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("Add device")

