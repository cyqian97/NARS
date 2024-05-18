import pygame
import os
import sys

# Center the game window on the screen
os.environ['SDL_VIDEO_CENTERED'] = '1'

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
BUTTON_WIDTH, BUTTON_HEIGHT = 100, 50
RED, BLUE, ORANGE, WHITE, BLACK = (255, 0, 0), (0, 0, 255), (255, 165, 0), (255, 255, 255), (0, 0, 0)

# Setup the display
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Drawing App')

# Button class
class Button:
    def __init__(self, color, x, y, width, height, text=''):
        self.color = color
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text

    def draw(self, screen, outline=None):
        if outline:
            pygame.draw.rect(screen, outline, (self.x-2, self.y-2, self.width+4, self.height+4), 0)
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height), 0)
        if self.text != '':
            font = pygame.font.SysFont('comicsans', 40)
            text = font.render(self.text, 1, BLACK)
            screen.blit(text, (self.x + (self.width/2 - text.get_width()/2), self.y + (self.height/2 - text.get_height()/2)))

    def is_over(self, pos):
        return self.x < pos[0] < self.x + self.width and self.y < pos[1] < self.y + self.height

# Buttons
red_button = Button(RED, 50, 50, BUTTON_WIDTH, BUTTON_HEIGHT, 'Red')
blue_button = Button(BLUE, 200, 50, BUTTON_WIDTH, BUTTON_HEIGHT, 'Blue')
orange_button = Button(ORANGE, 350, 50, BUTTON_WIDTH, BUTTON_HEIGHT, 'Orange')

# Variables to track state
current_color = None
orange_path_points = []

# Main loop
running = True
screen.fill(WHITE)
while running:
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if red_button.is_over(mouse_pos):
                current_color = RED
                print("red!!!!")
            elif blue_button.is_over(mouse_pos):
                current_color = BLUE
            elif orange_button.is_over(mouse_pos):
                current_color = ORANGE
                orange_path_points = []
            else:
                if current_color == RED:
                    pygame.draw.circle(screen, RED, mouse_pos, 20)
                    print("draw red!!!")
                elif current_color == BLUE:
                    pygame.draw.circle(screen, BLUE, mouse_pos, 20)
                elif current_color == ORANGE:
                    orange_path_points.append(mouse_pos)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # Draw buttons
    red_button.draw(screen, BLACK)
    blue_button.draw(screen, BLACK)
    orange_button.draw(screen, BLACK)
    
    # Draw orange path if points exist
    if len(orange_path_points)>1:
        pygame.draw.lines(screen, ORANGE, False, orange_path_points, 5)

    pygame.display.update()

pygame.quit()
sys.exit()
