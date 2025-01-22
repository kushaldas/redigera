from django import forms


class UploadFileForm(forms.Form):
    file = forms.FileField()


class UpdateExpiryForm(forms.Form):
    date = forms.TextInput()
    pin = forms.PasswordInput()
