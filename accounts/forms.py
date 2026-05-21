from django import forms

from common.forms import INPUT_CLASS, SELECT_CLASS, CHECKBOX_CLASS
from .models import User


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'role', 'is_active'
        ]

        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'role': forms.Select(attrs={'class': SELECT_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }
