from django import forms
from django.contrib.auth.models import User
from .models import RoommateProfile

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password']

class QuizForm(forms.ModelForm):
    class Meta:
        model = RoommateProfile
        exclude = ['user']
        widgets = {
            'sleep_schedule': forms.Select(attrs={'class': 'form-control'}),
            'cleanliness_level': forms.Select(attrs={'class': 'form-control'}),
            'noise_tolerance': forms.Select(attrs={'class': 'form-control'}),
            'study_habit': forms.Select(attrs={'class': 'form-control'}),
            'hostel_room_no': forms.TextInput(attrs={'class': 'form-control'}),
        }