from django import forms

from .models import Login, Features


class LoginForm(forms.ModelForm):
    class Meta:
        model = Login
        fields = "__all__"

class FeatureForm(forms.ModelForm):
    class Meta:
        model = Features
        fields = "__all__"       