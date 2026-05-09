#!/usr/bin/env python3
"""Simple Calculator CLI

Usage: python calculator-cli\calculator.py

Supports: addition, subtraction, multiplication, division
Runs in a loop until the user exits. Handles invalid input and divide-by-zero gracefully.

Built using GitHub Copilot CLI using the below prompt:
You are an expert Python programmer. create a new folder called "calculator-cli" and 
built a python based simple math calculator that allows addition, subtraction,       
multiplication, and division. This will be a cli based app that the user launches    
from ther terminal using python command. Run the app in an infinite loop until the   
user chooses to exit. Handle common math calculation errors gracefully like divide by
 zero, etc.
"""

def get_number(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Invalid number. Please enter a numeric value.")


def main():
    print("Simple Calculator CLI — supports +, -, *, /")
    while True:
        print("\nSelect operation:")
        print("1) Add (+)")
        print("2) Subtract (-)")
        print("3) Multiply (*)")
        print("4) Divide (/)")
        print("5) Exit")
        choice = input("Enter choice (1-5): ").strip()
        if choice == '5' or choice.lower() in ('exit','q','quit'):
            print("Goodbye!")
            break
        if choice not in ('1','2','3','4'):
            print("Invalid choice. Try again.")
            continue
        a = get_number('Enter first number: ')
        b = get_number('Enter second number: ')
        try:
            if choice == '1':
                result = a + b
                op = '+'
            elif choice == '2':
                result = a - b
                op = '-'
            elif choice == '3':
                result = a * b
                op = '*'
            elif choice == '4':
                if b == 0:
                    raise ZeroDivisionError
                result = a / b
                op = '/'
            print(f"{a} {op} {b} = {result}")
        except ZeroDivisionError:
            print('Error: Division by zero is not allowed.')
        except Exception as e:
            print('An error occurred:', e)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nExiting calculator. Goodbye!')
