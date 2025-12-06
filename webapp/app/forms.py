from django import forms
from django.contrib.auth.models import User
from .models import RoommateProfile
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password']

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email",
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': True})
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)

            if self.user_cache is None:
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(email__iexact=email)
                    self.user_cache = authenticate(self.request, username=user.username, password=password)
                except User.DoesNotExist:
                    pass

            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )

        return self.cleaned_data

class QuizForm(forms.ModelForm):
    class Meta:
        model = RoommateProfile
        exclude = ['user']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '03001234567',
                'pattern': '03[0-9]{9}', # HTML5 client-side validation
                'title': 'Must be a valid Pakistani mobile number starting with 03'
            }),
            'sleep_schedule': forms.Select(attrs={'class': 'form-control'}),
            'cleanliness_level': forms.Select(attrs={'class': 'form-control'}),
            'noise_tolerance': forms.Select(attrs={'class': 'form-control'}),
            'study_habit': forms.Select(attrs={'class': 'form-control'}),
        }
    
    # Extra Server-Side Validation
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Check if this number is already used by another profile
            if RoommateProfile.objects.filter(phone_number=phone).exists():
                raise forms.ValidationError("This phone number is already in use by another student.")
        return phone