from django import forms

class BacktestOptions(forms.form):
    start_date = forms.choiceField()
    end_date = forms.ChoiceField()

    def __init__(self, *args, date_choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        date_choices = date_choices or []

        self.fields["start_date"].choices = date_choices
        self.fields["end_date"].choices = date_choices

    class RecordDateForm(forms.form):
        record_date = forms.ChoicesField
        