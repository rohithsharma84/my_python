from decimal import Decimal
from django import forms


class AccountSetupForm(forms.Form):
    name = forms.CharField(
        label='Account holder name',
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your name'}),
    )
    initial_deposit = forms.DecimalField(
        label='Initial deposit',
        min_value=Decimal('0.00'),
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
    )


class AmountForm(forms.Form):
    amount = forms.DecimalField(
        label='Amount',
        min_value=Decimal('0.01'),
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
    )
