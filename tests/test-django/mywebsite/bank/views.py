from decimal import Decimal
from django.shortcuts import redirect, render
from django.urls import reverse
from .forms import AccountSetupForm, AmountForm
from .utils import BankAccount


SESSION_ACCOUNT_NAME = 'account_name'
SESSION_ACCOUNT_BALANCE = 'account_balance'
SESSION_MESSAGE = 'account_message'


def get_saved_account(request):
    name = request.session.get(SESSION_ACCOUNT_NAME)
    balance = request.session.get(SESSION_ACCOUNT_BALANCE)
    if name is None or balance is None:
        return None
    try:
        balance_value = Decimal(balance)
    except (TypeError, ValueError):
        return None
    return BankAccount(name, balance_value)


def account_setup(request):
    if request.method == 'POST':
        form = AccountSetupForm(request.POST)
        if form.is_valid():
            request.session[SESSION_ACCOUNT_NAME] = form.cleaned_data['name']
            request.session[SESSION_ACCOUNT_BALANCE] = str(form.cleaned_data['initial_deposit'])
            request.session[SESSION_MESSAGE] = 'Account created successfully.'
            return redirect('bank:dashboard')
    else:
        form = AccountSetupForm()
    return render(request, 'bank/account_setup.html', {'form': form})


def dashboard(request):
    account = get_saved_account(request)
    if account is None:
        return redirect('bank:account_setup')

    message = request.session.pop(SESSION_MESSAGE, '')
    deposit_form = AmountForm(prefix='deposit')
    withdraw_form = AmountForm(prefix='withdraw')

    return render(request, 'bank/dashboard.html', {
        'account': account,
        'message': message,
        'deposit_form': deposit_form,
        'withdraw_form': withdraw_form,
    })


def account_action(request):
    account = get_saved_account(request)
    if account is None:
        return redirect('bank:account_setup')

    action = request.POST.get('action')
    message = ''

    if action == 'deposit':
        form = AmountForm(request.POST, prefix='deposit')
        if form.is_valid():
            amount = form.cleaned_data['amount']
            account.deposit(amount)
            request.session[SESSION_ACCOUNT_BALANCE] = str(account.amount)
            message = f'Deposited ${amount:.2f} successfully.'
        else:
            return render(request, 'bank/dashboard.html', {
                'account': account,
                'message': 'Please enter a valid deposit amount.',
                'deposit_form': form,
                'withdraw_form': AmountForm(prefix='withdraw'),
            })
    elif action == 'withdraw':
        form = AmountForm(request.POST, prefix='withdraw')
        if form.is_valid():
            amount = form.cleaned_data['amount']
            try:
                account.withdraw(amount)
                request.session[SESSION_ACCOUNT_BALANCE] = str(account.amount)
                message = f'Withdrew ${amount:.2f} successfully.'
            except ValueError:
                message = 'Insufficient balance for that withdrawal.'
                return render(request, 'bank/dashboard.html', {
                    'account': account,
                    'message': message,
                    'deposit_form': AmountForm(prefix='deposit'),
                    'withdraw_form': form,
                })
        else:
            return render(request, 'bank/dashboard.html', {
                'account': account,
                'message': 'Please enter a valid withdrawal amount.',
                'deposit_form': AmountForm(prefix='deposit'),
                'withdraw_form': form,
            })
    elif action == 'quit':
        request.session.flush()
        return redirect('bank:account_setup')
    else:
        message = 'Unknown action. Please try again.'

    request.session[SESSION_MESSAGE] = message
    return redirect('bank:dashboard')
