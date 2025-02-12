from django import forms
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordChangeForm

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Profile.objects.create(user=user)
        return user

class CustomPasswordChangeForm(PasswordChangeForm):
    class Meta:
        model = User
        fields = ['old_password', 'new_password1', 'new_password2']

class DatasetUploadForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',  # Bootstrap class for file input
                'id': 'dataset-upload-file',
                'accept': '.csv, .xlsx, .xls',
                'aria-label': 'Upload Dataset',
            }),
        }

class SalesComparisonForm(forms.Form):
    current_month_file = forms.FileField(
        label="Upload new sales data",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'id': 'sales-comparison-file', 'accept': '.csv, .xlsx, .xls'})
    )


class SalesDataUploadForm(forms.Form):
    file = forms.FileField(
        label="Upload Sales Data File",
        help_text="Upload a CSV file with 'date' and 'sales' columns"
    )


class DatasetFilterForm(forms.Form):
    file_name = forms.CharField(
        max_length=255,
        required=False,
        label='File Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter Dateset '})
    )
    start_date = forms.DateField(
        required=False,
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'Start date'})
    )
    end_date = forms.DateField(
        required=False,
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'End date'})
    )
