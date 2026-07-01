import os
import sys
import random
import math

import pygame


WIDTH, HEIGHT = 1200, 600
FPS = 60
PADDLE_WIDTH = 12
PADDLE_HEIGHT = 90
BALL_SIZE = 16
PLAYER_PADDLE_SPEED = 20
AI_PADDLE_SPEED = 8
BALL_SPEED = 7
BALL_ACCELERATION = 1.08
HIT_POWER = 1.5
MAX_BALL_SPEED = 18
MAX_RACKET_LEVEL = 5
RACKET_POWER_STEP = 0.2
UPGRADE_COST = 5
WIN_REWARD = 1
GRAVITY = 0.25
BOUNCE_DAMPING = 0.92
MAX_FALL_SPEED = 15


class Paddle:
    def __init__(self, x, y, speed, is_left=True):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = speed
        self.is_left = is_left
        self.racket_angle = 0
        self.base_angle = -70 if is_left else 250
        self.racket_pivot_offset = 12
        self.swinging = False

    def move(self, direction):
        self.rect.y += direction * self.speed
        self.rect.y = max(0, min(HEIGHT - self.rect.height, self.rect.y))

    def move_to(self, target_y, max_speed=None):
        if max_speed is None:
            max_speed = self.speed
        distance = target_y - self.rect.centery
        if abs(distance) <= max_speed:
            self.rect.centery = target_y
        else:
            self.rect.y += max_speed if distance > 0 else -max_speed
        self.rect.y = max(0, min(HEIGHT - self.rect.height, self.rect.y))

    def update_racket(self):
        if self.racket_angle != 0:
            self.racket_angle *= 0.6
            if abs(self.racket_angle) < 0.5:
                self.racket_angle = 0
                self.swinging = False

    def swing_racket(self):
        if not self.swinging:
            self.racket_angle = 55 if self.is_left else -55
            self.swinging = True

    def draw(self, screen):
        body_rect = pygame.Rect(self.rect.x - 6, self.rect.y + 16, self.rect.width + 12, self.rect.height - 16)
        body_color = (70, 140, 255) if self.is_left else (255, 80, 80)
        pygame.draw.rect(screen, body_color, body_rect)
        head_center = (self.rect.centerx, self.rect.top - 10)
        pygame.draw.circle(screen, (255, 255, 255), head_center, 9)

        pivot_x = self.rect.right if self.is_left else self.rect.left
        pivot = (pivot_x, self.rect.centery + self.racket_pivot_offset)
        angle = self.base_angle + self.racket_angle
        rad = math.radians(angle)
        length = 40
        end_x = pivot[0] + int(math.cos(rad) * length)
        end_y = pivot[1] - int(math.sin(rad) * length)
        pygame.draw.line(screen, (255, 255, 255), pivot, (end_x, end_y), 5)


class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        self.rect = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
        self.dx = BALL_SPEED if os.environ.get("TENNIS_HEADLESS") != "1" else BALL_SPEED
        self.dy = BALL_SPEED

    def update(self):
        self.dy = max(-MAX_FALL_SPEED, min(MAX_FALL_SPEED, self.dy + GRAVITY))
        self.rect.x += self.dx
        self.rect.y += self.dy

    def draw(self, screen):
        pygame.draw.ellipse(screen, (255, 255, 255), self.rect)


class TennisGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pygame Tennis")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.left_paddle = Paddle(30, HEIGHT // 2 - PADDLE_HEIGHT // 2, PLAYER_PADDLE_SPEED, is_left=True)
        self.right_paddle = Paddle(WIDTH - 30 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2, AI_PADDLE_SPEED, is_left=False)
        self.ball = Ball()
        self.money = 0
        self.running = True
        self.serving = True
        self.serve_power = 10
        self.serve_angle = -35
        self.practice_mode = False
        self.practice_button_rect = pygame.Rect(WIDTH - 220, 20, 180, 40)
        self.racket_level = 1
        self.racket_power = 1.0
        self.ai_miss_offset = 0
        self.ai_miss_active = False
        self.net_height = HEIGHT // 4
        self.net_x = WIDTH // 2
        self.net_top = HEIGHT - self.net_height
        self.blockers = [
            {"rect": pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 - 50, 20, 100), "vel": [0, 5]},
            {"rect": pygame.Rect(WIDTH // 2 + 90, HEIGHT // 2 + 30, 20, 100), "vel": [0, -5]}
        ]
        self.reset_point()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.ball.reset()
                    self.money = 0
                    self.reset_point()
                elif event.key == pygame.K_SPACE and self.serving:
                    self.start_serve()
                elif event.key == pygame.K_u:
                    if self.racket_level < MAX_RACKET_LEVEL and self.money >= UPGRADE_COST:
                        self.racket_level += 1
                        self.racket_power = 1.0 + (self.racket_level - 1) * RACKET_POWER_STEP
                        self.money -= UPGRADE_COST
                elif self.serving:
                    if event.key == pygame.K_UP:
                        self.serve_power = min(16, self.serve_power + 1)
                    elif event.key == pygame.K_DOWN:
                        self.serve_power = max(4, self.serve_power - 1)
                    elif event.key == pygame.K_LEFT:
                        self.serve_angle = max(-75, self.serve_angle - 5)
                    elif event.key == pygame.K_RIGHT:
                        self.serve_angle = min(-15, self.serve_angle + 5)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.practice_button_rect.collidepoint(event.pos):
                    self.practice_mode = not self.practice_mode
                    if self.practice_mode:
                        self.reset_point()
                elif self.serving:
                    self.start_serve()

    def move_right_paddle_ai(self):
        if self.ball.rect.centerx <= WIDTH // 2:
            self.ai_miss_active = False
            self.ai_miss_offset = 0
            self.right_paddle.move_to(HEIGHT // 2, self.right_paddle.speed)
            return

        if not self.ai_miss_active and random.random() < 0.008:
            self.ai_miss_active = True
            self.ai_miss_offset = random.randint(-35, 35)

        target_y = self.ball.rect.centery + (self.ai_miss_offset if self.ai_miss_active else 0)
        target_y -= self.right_paddle.racket_pivot_offset
        target_y = max(self.right_paddle.rect.height // 2,
                       min(HEIGHT - self.right_paddle.rect.height // 2, target_y))
        self.right_paddle.move_to(target_y, self.right_paddle.speed)

    def reset_point(self):
        self.serving = True
        self.ball.reset()
        self.ball.dx = 0
        self.ball.dy = 0
        self.ball.rect.centery = self.left_paddle.rect.centery
        self.ball.rect.left = self.left_paddle.rect.right + 8

    def start_serve(self):
        self.serving = False
        rad = math.radians(self.serve_angle)
        self.ball.dx = self.serve_power * self.racket_power * math.cos(rad)
        self.ball.dy = self.serve_power * self.racket_power * math.sin(rad)

    def resolve_blocker_collision(self, blocker_rect, prev_ball_rect):
        current_rect = self.ball.rect
        swept_rect = prev_ball_rect.union(current_rect)
        if not swept_rect.colliderect(blocker_rect):
            return False

        if abs(self.ball.dx) >= abs(self.ball.dy):
            if self.ball.dx > 0:
                self.ball.rect.right = blocker_rect.left
            else:
                self.ball.rect.left = blocker_rect.right
            self.ball.dx = -self.ball.dx * 0.8
        else:
            if self.ball.dy > 0:
                self.ball.rect.bottom = blocker_rect.top
            else:
                self.ball.rect.top = blocker_rect.bottom
            self.ball.dy = -self.ball.dy * 0.8
        return True

    def update(self):
        mouse_y = pygame.mouse.get_pos()[1]
        self.left_paddle.rect.centery = max(self.left_paddle.rect.height // 2,
                                           min(HEIGHT - self.left_paddle.rect.height // 2, mouse_y))

        self.left_paddle.update_racket()
        self.right_paddle.update_racket()
        self.move_right_paddle_ai()
        prev_ball_rect = self.ball.rect.copy()
        if self.serving:
            self.ball.rect.centery = self.left_paddle.rect.centery
            self.ball.rect.left = self.left_paddle.rect.right + 8
        else:
            self.ball.update()

        for blocker in self.blockers:
            rect = blocker["rect"]
            vel = blocker["vel"]
            rect.x += vel[0]
            rect.y += vel[1]
            if rect.top <= 40 or rect.bottom >= HEIGHT - 40:
                vel[1] *= -1
            if rect.left <= 40 or rect.right >= WIDTH - 40:
                vel[0] *= -1

        for blocker in self.blockers:
            if self.resolve_blocker_collision(blocker["rect"], prev_ball_rect):
                break

        net_rect = pygame.Rect(self.net_x - 8, self.net_top, 16, self.net_height)
        if self.ball.rect.colliderect(net_rect):
            if self.ball.dx > 0:
                self.ball.rect.right = net_rect.left
            else:
                self.ball.rect.left = net_rect.right
            self.ball.dx = -self.ball.dx * 0.8

        for blocker in self.blockers:
            rect = blocker["rect"]
            if self.ball.rect.colliderect(rect):
                overlap = self.ball.rect.clip(rect)
                if overlap.width < overlap.height:
                    if self.ball.dx > 0:
                        self.ball.rect.right = rect.left
                    else:
                        self.ball.rect.left = rect.right
                    self.ball.dx = -self.ball.dx * 0.8
                else:
                    if self.ball.dy > 0:
                        self.ball.rect.bottom = rect.top
                    else:
                        self.ball.rect.top = rect.bottom
                    self.ball.dy = -self.ball.dy * 0.8

        if self.ball.rect.top <= 0:
            self.ball.rect.top = 0
            self.ball.dy = -self.ball.dy * BOUNCE_DAMPING
        elif self.ball.rect.bottom >= HEIGHT:
            self.ball.rect.bottom = HEIGHT
            self.ball.dy = -self.ball.dy * BOUNCE_DAMPING

        if self.ball.rect.colliderect(self.left_paddle.rect):
            self.ball.rect.x = self.left_paddle.rect.right
            offset = (self.ball.rect.centery - self.left_paddle.rect.centery) / (PADDLE_HEIGHT / 2)
            self.ball.dx = min(abs(self.ball.dx) * BALL_ACCELERATION * HIT_POWER * self.racket_power, MAX_BALL_SPEED)
            self.ball.dy = BALL_SPEED * offset - 14
            self.left_paddle.swing_racket()
        elif self.ball.rect.colliderect(self.right_paddle.rect):
            self.ball.rect.x = self.right_paddle.rect.left - self.ball.rect.width
            offset = (self.ball.rect.centery - self.right_paddle.rect.centery) / (PADDLE_HEIGHT / 2)
            self.ball.dx = -min(abs(self.ball.dx) * BALL_ACCELERATION * HIT_POWER * self.racket_power, MAX_BALL_SPEED)
            self.ball.dy = BALL_SPEED * offset - 14
            self.right_paddle.swing_racket()

        if self.ball.rect.left <= 0:
            if self.practice_mode:
                self.ball.rect.left = 0
                self.ball.dx = abs(self.ball.dx)
            else:
                self.reset_point()
        elif self.ball.rect.right >= WIDTH:
            if self.practice_mode:
                self.ball.rect.right = WIDTH
                self.ball.dx = -abs(self.ball.dx)
            else:
                self.money += WIN_REWARD
                self.reset_point()

    def draw(self):
        self.screen.fill((18, 120, 58))
        pygame.draw.rect(self.screen, (46, 139, 87), (20, 20, WIDTH - 40, HEIGHT - 40), 0)

        for y in range(self.net_top, self.net_top + self.net_height, 16):
            pygame.draw.line(self.screen, (255, 255, 255), (self.net_x, y), (self.net_x, min(y + 10, self.net_top + self.net_height)), 3)
        pygame.draw.line(self.screen, (192, 192, 192), (self.net_x - 3, self.net_top), (self.net_x + 3, self.net_top + self.net_height), 2)

        for blocker in self.blockers:
            pygame.draw.rect(self.screen, (200, 200, 200), blocker["rect"])

        self.left_paddle.draw(self.screen)
        self.right_paddle.draw(self.screen)
        self.ball.draw(self.screen)

        money_text = self.font.render(f"Money: ${self.money}", True, (255, 255, 255))
        self.screen.blit(money_text, (WIDTH // 2 - money_text.get_width() // 2, 30))

        button_color = (70, 160, 255) if self.practice_mode else (90, 90, 90)
        pygame.draw.rect(self.screen, button_color, self.practice_button_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), self.practice_button_rect, 2)
        button_text = self.font.render("Practice Mode", True, (255, 255, 255))
        button_text_rect = button_text.get_rect(center=self.practice_button_rect.center)
        self.screen.blit(button_text, button_text_rect)

        if self.serving:
            arrow_start = self.ball.rect.center
            rad = math.radians(self.serve_angle)
            arrow_length = self.serve_power * 10
            arrow_end = (arrow_start[0] + int(math.cos(rad) * arrow_length),
                         arrow_start[1] + int(math.sin(rad) * arrow_length))
            pygame.draw.line(self.screen, (255, 215, 0), arrow_start, arrow_end, 4)
            head_size = 8
            angle = math.atan2(arrow_start[1] - arrow_end[1], arrow_end[0] - arrow_start[0])
            left = (arrow_end[0] - int(math.cos(angle + math.pi / 6) * head_size),
                    arrow_end[1] + int(math.sin(angle + math.pi / 6) * head_size))
            right = (arrow_end[0] - int(math.cos(angle - math.pi / 6) * head_size),
                     arrow_end[1] + int(math.sin(angle - math.pi / 6) * head_size))
            pygame.draw.polygon(self.screen, (255, 215, 0), [arrow_end, left, right])
            hint = self.font.render(f"Power:{self.serve_power} Angle:{self.serve_angle} Level:{self.racket_level}", True, (255, 255, 255))
            self.screen.blit(hint, (20, 20))
            upgrade_hint = self.font.render("Press U to upgrade racket ($5)", True, (255, 255, 255))
            self.screen.blit(upgrade_hint, (20, 50))
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    game = TennisGame()
    game.run()
