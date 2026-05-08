""" Learning about classes and objects
    Here, we will define a class called bankAccount
    We will ask the user to input a name and initial deposit amount
    Next, we present them 4 choices: d-deposit, w-withdraw, b-balance, or q-quit
"""
import sys
class bankAccount:
    def __init__(self, name, amount=0.0):
        self.name = name
        self.amount=amount
    def printBalance(self):
        print("Current balance: $%.2f" % self.amount)
    def deposit(self,amount):
        self.amount += amount
        return self.amount
    def withdraw(self, amount):
        if amount > self.amount:
            print("Insufficient balance!")
            return
        else:
            self.amount -= amount
            return self.amount

# Use this class to create a new account
my_account = bankAccount(input("Enter your name: "), float(input("Enter initial deposit: $")))

while True:
    choice = input("What do you want to do? b-balance, d-deposit, w-withdraw, q-quit: ")
    if choice == 'b':
        my_account.printBalance()
    elif choice == 'd':
        my_account.deposit(float(input("Enter deposit amount: $")))
        my_account.printBalance()
    elif choice == 'w':
        my_account.withdraw(float(input("Enter amount to withdraw: $:")))
        my_account.printBalance()
    elif choice == 'q':
        sys.exit()