from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label="이메일")
    user_gender = forms.ChoiceField(
        choices=User.GENDER_CHOICES,
        widget=forms.RadioSelect,
        label="성별"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "user_gender")  # password1/2는 부모 폼에 이미 있음

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.user_gender = self.cleaned_data["user_gender"]
        if commit:
            user.save()
        return user
