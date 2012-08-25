from django import forms
from django.db import models
from crispy_forms.helper import FormHelper


class TestForm(forms.Form):
    is_company = forms.CharField(label="company", required=False, widget=forms.CheckboxInput())
    email = forms.EmailField(label="email", max_length=30, required=True, widget=forms.TextInput())
    password1 = forms.CharField(label="password", max_length=30, required=True, widget=forms.PasswordInput())
    password2 = forms.CharField(label="re-enter password", max_length=30, required=True, widget=forms.PasswordInput())
    first_name = forms.CharField(label="first name", max_length=5, required=True, widget=forms.TextInput())
    last_name = forms.CharField(label="last name", max_length=5, required=True, widget=forms.TextInput())
    datetime_field = forms.DateTimeField(label="date time", widget=forms.SplitDateTimeWidget())

    def clean(self):
        super(TestForm, self).clean()
        password1 = self.cleaned_data.get('password1', None)
        password2 = self.cleaned_data.get('password2', None)
        if not password1 and not password2 or password1 != password2:
            raise forms.ValidationError("Passwords dont match")

        return self.cleaned_data


class TestForm2(TestForm):
    def __init__(self, *args, **kwargs):
        super(TestForm2, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)


class CheckboxesTestForm(forms.Form):
    checkboxes = forms.MultipleChoiceField(
        choices = (
            (1, "Option one"),
            (2, "Option two"),
            (3, "Option three")
        ),
        initial = (1,),
        widget = forms.CheckboxSelectMultiple,
    )

    alphacheckboxes = forms.MultipleChoiceField(
        choices = (
            ('option_one', "Option one"),
            ('option_two', "Option two"),
            ('option_three', "Option three")
        ),
        initial = ('option_two', 'option_three'),
        widget = forms.CheckboxSelectMultiple,
    )

    numeric_multiple_checkboxes = forms.MultipleChoiceField(
        choices = (
            (1, "Option one"),
            (2, "Option two"),
            (3, "Option three")
        ),
        initial = (1, 2),
        widget = forms.CheckboxSelectMultiple,
    )


class TestModel(models.Model):
    email = models.CharField(max_length=20)
    password = models.CharField(max_length=20)


class TestForm3(forms.ModelForm):
    class Meta:
        model = TestModel
        fields = ['email']

    def __init__(self, *args, **kwargs):
        super(TestForm3, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)


class ExampleForm(forms.Form):
    comment = forms.CharField()


class FormWithMeta(TestForm):
    class Meta:
        fields = ('email', 'first_name', 'last_name')

