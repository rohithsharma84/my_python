from decimal import Decimal


class BankAccount:
    def __init__(self, name: str, amount: Decimal = Decimal('0.00')):
        self.name = name
        self.amount = amount

    def deposit(self, amount: Decimal) -> Decimal:
        self.amount += amount
        return self.amount

    def withdraw(self, amount: Decimal) -> Decimal:
        if amount > self.amount:
            raise ValueError('Insufficient balance')
        self.amount -= amount
        return self.amount

    def formatted_balance(self) -> str:
        return f'{self.amount:.2f}'
