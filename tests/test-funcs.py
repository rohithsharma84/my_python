# Testing how to use functions

fruits={}

def add_fruit(fruit,count):
    fruits[fruit] = count

def remove_fruit(fruit):
    if fruit in fruits:
        if fruits[fruit] > 0:
            fruits[fruit] -= 1
        else:
            print("No more",fruit)
    else:
        print("No",fruit,"in stock")

def print_fruits():
    print("Fruit inventory..")
    for fruit in fruits:
        print(fruit,fruits[fruit])
    print("-------------------")

print("Adding 10 apples and 5 bananas..")
add_fruit("Apple",10)
add_fruit("Banana",5)
print_fruits()

print("Removing 1 apple..")
remove_fruit("Apple")
print_fruits()

print("Removing 1 banana..")
remove_fruit("Banana")
print_fruits()

print("Adding a new fruit..")
add_fruit("Kiwi",1)
print_fruits()