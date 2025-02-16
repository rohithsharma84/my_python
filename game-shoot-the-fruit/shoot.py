# Show an apple on the screen and if the user clicks on it
# with mouse, the apple should disappear and show a message
# saying "You got it!", and display the apple at a new random 
# location

import pgzrun
import random

apple = Actor("apple.png")

def draw():
    screen.clear()
    apple.draw()

pgzrun.go()