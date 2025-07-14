from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label="이메일")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")  # password1/2는 부모 폼에 이미 있음

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
