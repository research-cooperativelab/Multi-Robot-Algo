import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *
import math
import numpy as np
import time
verticies = (
    (1, 1),
    (2, 2)
    )

# edges = (
#     (0,1),
#     (0,3),
#     (0,4),
#     (2,1),
#     (2,3),
#     (2,7),
#     (6,3),
#     (6,4),
#     (6,7),
#     (5,1),
#     (5,4),
#     (5,7)
#     )


def drown():
    glColor3f(1, 0, 0)  # Set color to red
    glBegin(GL_LINES)
    glVertex2f(verticies[0][0], verticies[0][1])
    glVertex2f(verticies[1][0], verticies[1][1])

    glEnd()

def main():
    pygame.init()
    display = (800,600)
    pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, display[0], 0, display[1])  # Set orthographic projection
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glClearColor(0.0, 0.0, 0.0, 1.0)  # Set background color to black
    glColor3f(1, 1, 1)  # Set drawing color to white
    # gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)
    
    # glTranslatef(0.0,0.0, -2) # The points would translate to some distance away from the camera
  
    for i in np.arange(0, int(math.sqrt(2)), 0.1):
    # while start < end:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        
        # glRotatef(1, 3, 1, 1)
        glTranslatef((1/math.sqrt(2))*i, (1/math.sqrt(2))*i , 0) 
        drown()
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        
        pygame.display.flip() #takes the new frame
        pygame.time.wait(30)

main()

# nodes and then have animations that where the robots go after each simulation step.
# Opengl -> visualize the nodes and robots. 
# also show the paths of the robots and see if the algorithm works as planned.
 