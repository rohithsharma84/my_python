"""
Show an apple at a random location on the screen and scroll it to the right. 
If the user clicks on it with the mouse, add 1 to the score and redraw the apple.
If the user misses the apple, subtract 1 from the life and continue.
If the apple reaches the right edge of the screen, subtract 1 from the life and continue.
User gets +1 life for every 5 points.
If the user lost all lives, the game is over.
"""

import pgzrun
from random import randint
from time import sleep

apple = Actor("apple.png")

def draw():
    global score, life, result_text
    screen.clear()
    if life >= 0:
        screen.draw.text(result_text, color="red", midtop=(400, 10))
        screen.draw.text("Life: " + str(life), color="red", topleft=(10,30))
        screen.draw.text("Score: " + str(score), color="red", topleft=(10,10))
        apple.draw()
    else: # Show "game over" at the center of the screen in large fonts
        screen.draw.text(result_text, color="red", fontsize=100, center=(400,300))
        screen.draw.text("Score: " + str(score), color="red", fontsize=80, center=(400,250))

def update():
    apple.left += 4
    if apple.left > 800:
        lose_life()
        place_apple()

def set_apple_normal():
    apple.image = "apple.png"

def set_apple_cut():
    apple.image = "apple_cut.png"
    sounds.eep.play()
    clock.schedule_unique(set_apple_normal, 0.2)
    clock.schedule_unique(place_apple, 0.2)

def place_apple():
    apple.x = randint(60,400)
    apple.y = randint(60,500)

def on_mouse_down(pos):
    global score, life, result_text
    if life < 0: # Exit the game
        quit()
    if apple.collidepoint(pos):
        score += 1
        if score % 5 == 0: # add a life every 5 points
            life += 1 
        result_text = "Good shot!"
        set_apple_cut()
        apple.draw()
    else:
        lose_life()
        return

def lose_life():
    global life, result_text
    if life > 1:
            life -= 1
            result_text = "You missed!"
            place_apple()
    elif life == 1:
        life -= 1
        result_text = "Last life!"
        place_apple()
    else: # Used all lives
        life -= 1
        result_text = "Game over!"

# Program starts here
WIDTH = 800
HEIGHT = 600
score = 0
life = 3
result_text = "Shoot the apple!"
set_apple_normal()
place_apple()

pgzrun.go()