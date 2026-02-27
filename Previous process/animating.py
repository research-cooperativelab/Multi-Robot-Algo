import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import math

pygame.init()
display = (800, 600)
pygame.display.set_mode(display, pygame.DOUBLEBUF | pygame.OPENGL)


glClearColor(0.0, 0.0, 0.0, 1.0)
gluOrtho2D(0, display[0], 0, display[1])

# def draw_rectangle(x, y, width, height):
#     glBegin(GL_QUADS)
#     glVertex2f(x, y)
#     glVertex2f(x + width, y)
#     glVertex2f(x + width, y + height)
#     glVertex2f(x, y + height)
#     glEnd()

def draw_circle(x, y, radius):
    glBegin(GL_POLYGON)
    for i in range(100):
        angle = 2 * 3.14159 * i / 100
        glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
    glEnd()

def draw_line(x1, y1, x2, y2):
    glBegin(GL_LINES)

    
    glVertex2f(x1, y1)
    glVertex2f(x2, y2)
    glEnd()

# parametric function of a line 
def parametric_line(t, x1, y1, x2, y2):
    return (t * (x2 - x1), t * (y2 - y1))

 

t = 0


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    glClear(GL_COLOR_BUFFER_BIT)

    
    glColor3f(0.0, 0.0, 1.0)  # Set color to blue
    # set the tickness of the line
    glLineWidth(10)
    draw_line(400, 300, 600, 400)
    
    glColor3f(1.0, 0.0, 0.0)  # Set color to red
    draw_circle(400, 300, 30)
    
    glColor3f(0.0, 1.0, 0.0)  # Set color to green
    draw_circle(600, 400, 30)
    
    parametric_l = parametric_line(t, 400, 300, 600, 400)
    glPushMatrix()  # Save the current matrix state
    glTranslatef(parametric_l[0], parametric_l[1], 0.0)  

    glColor3f(1.0, 1.0, 0.0)  # Set color to yellow
    draw_circle(400, 300, 10)

    glPopMatrix()  # Restore the previous matrix state

    # Draw a moving point along the line
    t += 0.01
    if t > 1:
        t = 0

    pygame.display.flip()        
    pygame.time.wait(10)


pygame.quit()