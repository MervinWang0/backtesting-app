from django import forms
from base.models import PaperAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class RegisterForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = User
        fields= (
            "username",
            "password1",
            "password2",
        )

        widgets =  {
            "username" : forms.TextInput(
                attrs = {
                    "placeholder" : "Username",
                }
            )
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].widget.attrs.update(
            {
                "placeholder":"Password",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "placeholder": "Confirm Password",
            }
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()

        return user


class BacktestOptions(forms.ModelForm):
    start_date = forms.ChoiceField()
    end_date = forms.ChoiceField()

    def __init__(self, *args, date_choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        date_choices = date_choices or []

        self.fields["start_date"].choices = date_choices
        self.fields["end_date"].choices = date_choices

    class RecordDateForm(forms.ModelForm):
        record_date = forms.ChoiceField

class PaperAccountCreation(forms.ModelForm):
    class Meta:
        model = PaperAccount
        fields = [
            "name",
            "initial_capital",
        ]

        labels = {
            "name": "Account name",
            "initial_capital": "Starting balance",
        }

        help_texts = {
            "name" : "Enter a name to associate with this paper account",
            "initial_capital": "Cash available when this account is created"
        }

        widgets = {
            "name" : forms.TextInput(
                attrs={
                    "placeholder" : "Enter a suitable name",
                    "autocomplete" : "off",
                }
            ),

            "initial_balance" : forms.NumberInput(
                attrs = {
                    "min" : "0.01",
                    "step" : "0.01",
                    "placeholder" : "Enter a number",
                }
            ),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
    
    def check_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Enter an account name"
            )
        
        if self.user and PaperAccount.objects.filter(user= self.user, name__iexact =name).exists():
            raise forms.ValidationError(
                "Account with the same name already exists, please use another name"
            )
        
        return name
    
    def save(self, commit = True):
        if self.user is None:
            raise ValueError(
                "User must be provided first"
            )
        
        account = super().save(commit=False)

        account.user = self.user
        account.cash_balance = self.cleaned_data["initial_capital"]

        if commit:
            account.save()

        return account



