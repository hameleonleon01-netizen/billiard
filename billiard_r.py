import arcade
import math
import random
import time
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 700
SCREEN_TITLE = "Про Бильярд: Настоящий Стол - Ultimate"

FRICTION = 0.985
ROTATIONAL_FRICTION = 0.96
WALL_BOUNCE = 0.78
BALL_RADIUS = 14
POCKET_RADIUS = 32
HIT_FORCE_MULTIPLIER = 0.12
MAX_POWER = 25
MIN_POWER = 3
GRAVITY_EFFECT = 0.2
SPIN_EFFECT = 0.15

DEEP_SPACE = (10, 5, 25)
TABLE_GREEN = (35, 150, 70)
CUSHION_DARK = (25, 120, 60)
CUSHION_LIGHT = (50, 180, 90)
WOOD_BROWN = (60, 35, 25)
WOOD_LIGHT = (90, 60, 45)
NEON_CYAN = (0, 255, 255)
NEON_PINK = (255, 0, 200)
NEON_GREEN = (0, 255, 100)
HIGHLIGHT_COLOR = (255, 255, 255, 180)
SHADOW_COLOR = (0, 0, 0, 120)

MAX_SCORE = 15
TIME_LIMIT = 300
TURN_TIME_LIMIT = 30
MAX_BALLS_IN_GAME = 15


class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    AIMING = 5
    BALLS_MOVING = 6


class BallType(Enum):
    CUE = 1
    SOLID = 2
    STRIPE = 3
    EIGHT = 4
    SPECIAL = 5


class GameMode(Enum):
    PRACTICE = 1
    TIMED = 2
    TURN_BASED = 3
    CHALLENGE = 4


@dataclass
class Particle:
    x: float
    y: float
    dx: float
    dy: float
    color: Tuple[int, int, int]
    size: float
    life: float
    max_life: float
    particle_type: str = "spark"


@dataclass
class TrailPoint:
    x: float
    y: float
    time: float
    visible: bool = True


class Ball(arcade.SpriteCircle):
    def __init__(self, x: float, y: float, color: Tuple[int, int, int],
                 ball_type: BallType = BallType.SOLID, number: int = 1):
        super().__init__(BALL_RADIUS, color)
        self.center_x, self.center_y = x, y
        self.ball_type = ball_type
        self.number = number
        self.initial_x, self.initial_y = x, y
        self.angular_velocity = 0.0
        self.spin_angle = 0.0
        self.rotation = 0.0
        self.in_pocket = False
        self.pocket_time = 0.0
        self.trail: List[TrailPoint] = []
        self.last_update_time = time.time()
        self.highlight = False
        self.highlight_time = 0.0
        self.special_effect = None

        if ball_type != BallType.CUE and number > 0:
            self.number_color = (255, 255, 255) if max(color) < 128 else (0, 0, 0)

        self.mass = 1.0
        self.elasticity = 0.9
        self.friction_coeff = 0.98

    def update(self, delta_time: float = 1 / 60):
        current_time = time.time()

        self.center_x += self.change_x
        self.center_y += self.change_y

        speed = math.sqrt(self.change_x ** 2 + self.change_y ** 2)
        if speed > 0:
            friction = FRICTION - (speed * 0.0005)
            self.change_x *= friction
            self.change_y *= friction

            self.rotation += self.angular_velocity * delta_time * 30
            self.angular_velocity *= ROTATIONAL_FRICTION

            if abs(self.angular_velocity) > 0.1:
                self.change_x += self.angular_velocity * SPIN_EFFECT * delta_time
                self.change_y -= self.angular_velocity * SPIN_EFFECT * delta_time

        if abs(self.change_x) < 0.08:
            self.change_x = 0
        if abs(self.change_y) < 0.08:
            self.change_y = 0

        if speed > 2.0:
            self.trail.append(TrailPoint(
                self.center_x, self.center_y, current_time
            ))

        if len(self.trail) > 10:
            self.trail.pop(0)

        self.trail = [p for p in self.trail if current_time - p.time < 0.5]

        if self.highlight:
            self.highlight_time += delta_time
            if self.highlight_time > 1.0:
                self.highlight = False

        self.last_update_time = current_time

    def draw_trail(self):
        if len(self.trail) < 2:
            return

        for i in range(len(self.trail) - 1):
            x1, y1 = self.trail[i].x, self.trail[i].y
            x2, y2 = self.trail[i + 1].x, self.trail[i + 1].y
            alpha = int(255 * (i / len(self.trail)) * 0.7)
            color = (self.color[0], self.color[1], self.color[2], alpha)
            arcade.draw_line(x1, y1, x2, y2, color, 3)

    def apply_force(self, dx: float, dy: float, power: float):
        angle = math.atan2(dy, dx)
        self.change_x = math.cos(angle) * power
        self.change_y = math.sin(angle) * power
        self.angular_velocity = power * 0.1 * random.uniform(-1, 1)

    def reset(self):
        self.center_x, self.center_y = self.initial_x, self.initial_y
        self.change_x, self.change_y = 0, 0
        self.angular_velocity = 0
        self.in_pocket = False
        self.trail.clear()


class BilliardTable:
    def __init__(self):
        self.width, self.height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.table_color = TABLE_GREEN
        self.cushion_color = CUSHION_DARK
        self.wood_color = WOOD_BROWN
        self.pocket_locations = [
            (60, 60), (self.width // 2, 50), (self.width - 60, 60),
            (60, self.height - 60), (self.width // 2, self.height - 50), (self.width - 60, self.height - 60)
        ]
        self.diamond_positions = []
        self.setup_diamonds()

    def setup_diamonds(self):
        for x in range(150, self.width - 150, 150):
            self.diamond_positions.append((x, 50))
            self.diamond_positions.append((x, self.height - 50))

        for y in range(150, self.height - 150, 150):
            self.diamond_positions.append((50, y))
            self.diamond_positions.append((self.width - 50, y))

    def draw(self):
        self.draw_wood_frame()
        self.draw_cushions()
        self.draw_table_surface()
        self.draw_pockets()
        self.draw_markings()

    def draw_wood_frame(self):
        arcade.draw_lrbt_rectangle_filled(20, self.width - 20, 20, self.height - 20, WOOD_BROWN)

        for i in range(20, self.width - 20, 30):
            arcade.draw_line(i, 20, i, self.height - 20, WOOD_LIGHT, 1)

        corner_positions = [(30, 30), (self.width - 30, 30),
                            (30, self.height - 30), (self.width - 30, self.height - 30)]
        for x, y in corner_positions:
            arcade.draw_circle_filled(x, y, 15, (200, 200, 200))
            arcade.draw_circle_outline(x, y, 15, (100, 100, 100), 2)

    def draw_cushions(self):
        arcade.draw_lrbt_rectangle_filled(40, self.width - 40, 40, self.height - 40, CUSHION_DARK)

        arcade.draw_lrbt_rectangle_outline(45, self.width - 45, 45, self.height - 45, CUSHION_LIGHT, 3)

        arcade.draw_lrbt_rectangle_outline(60, self.width - 60, 60, self.height - 60, (20, 100, 50), 2)

    def draw_table_surface(self):
        arcade.draw_lrbt_rectangle_filled(65, self.width - 65, 65, self.height - 65, self.table_color)

        for i in range(70, self.width - 65, 40):
            arcade.draw_line(i, 65, i, self.height - 65, (30, 140, 65, 30), 1)
        for i in range(70, self.height - 65, 40):
            arcade.draw_line(65, i, self.width - 65, i, (30, 140, 65, 30), 1)

    def draw_pockets(self):
        for x, y in self.pocket_locations:
            arcade.draw_circle_filled(x, y, POCKET_RADIUS + 5, (40, 40, 40))
            arcade.draw_circle_filled(x, y, POCKET_RADIUS, (0, 0, 0))
            arcade.draw_circle_filled(x, y, POCKET_RADIUS - 8, (20, 20, 20))

    def draw_markings(self):
        center_x, center_y = self.width // 2, self.height // 2

        arcade.draw_line(center_x, 65, center_x, self.height - 65, (255, 255, 255, 100), 2)

        home_line_x = 300
        arcade.draw_line(home_line_x, 65, home_line_x, self.height - 65, (255, 255, 255, 100), 2)

        arcade.draw_arc_outline(home_line_x, center_y, 180, 250,
                                (255, 255, 255, 120), 90, 270, 2)

        arcade.draw_circle_filled(home_line_x, center_y, 5, (255, 255, 255))

        arcade.draw_circle_filled(center_x, center_y, 5, (255, 255, 255))

        for x, y in self.diamond_positions:
            arcade.draw_circle_filled(x, y, 4, (255, 255, 255, 200))
            arcade.draw_circle_outline(x, y, 4, (200, 200, 200), 1)


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit_sparks(self, x: float, y: float, color: Tuple[int, int, int],
                    count: int = 8, speed: float = 3.0):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed_var = random.uniform(speed * 0.5, speed * 1.5)
            self.particles.append(Particle(
                x=x, y=y,
                dx=math.cos(angle) * speed_var,
                dy=math.sin(angle) * speed_var,
                color=color,
                size=random.uniform(2, 5),
                life=random.uniform(0.5, 1.0),
                max_life=1.0,
                particle_type="spark"
            ))

    def emit_cue_hit(self, x: float, y: float, power: float):
        for _ in range(int(power * 2)):
            angle = random.uniform(0, math.pi * 2)
            distance = random.uniform(0, power)
            self.particles.append(Particle(
                x=x + math.cos(angle) * distance,
                y=y + math.sin(angle) * distance,
                dx=0, dy=0,
                color=(255, 255, 200),
                size=random.uniform(3, 8),
                life=0.3,
                max_life=0.3,
                particle_type="cue_hit"
            ))

    def emit_pocket(self, x: float, y: float):
        for _ in range(15):
            angle = random.uniform(0, math.pi * 2)
            self.particles.append(Particle(
                x=x, y=y,
                dx=math.cos(angle) * random.uniform(1, 3),
                dy=math.sin(angle) * random.uniform(1, 3),
                color=NEON_CYAN,
                size=random.uniform(4, 8),
                life=random.uniform(0.8, 1.2),
                max_life=1.2,
                particle_type="pocket"
            ))

    def update(self, delta_time: float):
        for particle in self.particles[:]:
            particle.life -= delta_time
            if particle.life <= 0:
                self.particles.remove(particle)
                continue

            particle.x += particle.dx
            particle.y += particle.dy

            if particle.particle_type == "spark":
                particle.dy -= GRAVITY_EFFECT * delta_time * 60
                particle.dx *= 0.95

            particle.size *= 0.97

    def draw(self):
        for particle in self.particles:
            alpha = int(255 * (particle.life / particle.max_life))
            if len(particle.color) == 3:
                color = (*particle.color, alpha)
            else:
                color = (*particle.color[:3], alpha)

            arcade.draw_circle_filled(particle.x, particle.y,
                                      particle.size, color)


class GamePhysics:
    @staticmethod
    def resolve_ball_collision(ball1: Ball, ball2: Ball):
        dx = ball2.center_x - ball1.center_x
        dy = ball2.center_y - ball1.center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0 or distance > BALL_RADIUS * 2:
            return

        nx, ny = dx / distance, dy / distance

        overlap = (BALL_RADIUS * 2) - distance
        separation = overlap * 0.5

        ball1.center_x -= nx * separation
        ball1.center_y -= ny * separation
        ball2.center_x += nx * separation
        ball2.center_y += ny * separation

        dvx = ball2.change_x - ball1.change_x
        dvy = ball2.change_y - ball1.change_y
        speed_along_normal = dvx * nx + dvy * ny

        if speed_along_normal > 0:
            return

        restitution = 0.9
        impulse = 2 * speed_along_normal / (ball1.mass + ball2.mass)
        impulse *= restitution

        ball1.change_x += impulse * ball2.mass * nx
        ball1.change_y += impulse * ball2.mass * ny
        ball2.change_x -= impulse * ball1.mass * nx
        ball2.change_y -= impulse * ball1.mass * ny

        if abs(ball1.angular_velocity) > 0.1:
            transfer = ball1.angular_velocity * 0.3
            ball1.angular_velocity -= transfer
            ball2.angular_velocity += transfer

    @staticmethod
    def check_wall_collision(ball: Ball):
        left_bound, right_bound = 65, SCREEN_WIDTH - 65
        bottom_bound, top_bound = 65, SCREEN_HEIGHT - 65

        if ball.left < left_bound:
            ball.left = left_bound
            ball.change_x = abs(ball.change_x) * WALL_BOUNCE
            ball.angular_velocity *= -0.8
            return True
        elif ball.right > right_bound:
            ball.right = right_bound
            ball.change_x = -abs(ball.change_x) * WALL_BOUNCE
            ball.angular_velocity *= -0.8
            return True

        if ball.bottom < bottom_bound:
            ball.bottom = bottom_bound
            ball.change_y = abs(ball.change_y) * WALL_BOUNCE
            ball.angular_velocity *= -0.8
            return True
        elif ball.top > top_bound:
            ball.top = top_bound
            ball.change_y = -abs(ball.change_y) * WALL_BOUNCE
            ball.angular_velocity *= -0.8
            return True

        return False


class SettingsMenu(arcade.View):
    def __init__(self, main_menu):
        super().__init__()
        self.main_menu = main_menu
        self.selected_option = 0
        self.menu_options = ["ГРОМКОСТЬ МУЗЫКИ", "ГРОМКОСТЬ ЗВУКОВ", "НАЗАД"]
        self.music_volume = main_menu.music_volume
        self.sound_volume = main_menu.sound_volume
        self.adjusting = False
        self.current_adjust = 0

    def on_draw(self):
        self.clear()
        arcade.set_background_color(DEEP_SPACE)

        arcade.draw_text(
            "НАСТРОЙКИ",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150,
            NEON_CYAN, 50, anchor_x="center", bold=True
        )

        start_y = SCREEN_HEIGHT // 2
        for i, option in enumerate(self.menu_options):
            y_pos = start_y - i * 100

            color = NEON_GREEN if i == self.selected_option else arcade.color.LIGHT_GRAY
            arcade.draw_text(
                option,
                SCREEN_WIDTH // 2 - 200, y_pos,
                color, 28, anchor_x="left"
            )

            if i < 2:
                slider_x = SCREEN_WIDTH // 2 + 50
                slider_width = 300
                slider_height = 20

                arcade.draw_lrbt_rectangle_filled(
                    slider_x, slider_x + slider_width,
                              y_pos - slider_height // 2, y_pos + slider_height // 2,
                    (50, 50, 50, 200)
                )

                volume = self.music_volume if i == 0 else self.sound_volume
                fill_width = slider_width * volume
                color_gradient = NEON_CYAN

                arcade.draw_lrbt_rectangle_filled(
                    slider_x, slider_x + fill_width,
                              y_pos - slider_height // 2, y_pos + slider_height // 2,
                    color_gradient
                )

                # Рамка
                arcade.draw_lrbt_rectangle_outline(
                    slider_x, slider_x + slider_width,
                              y_pos - slider_height // 2, y_pos + slider_height // 2,
                    (255, 255, 255, 200), 2
                )

                percent = int(volume * 100)
                arcade.draw_text(
                    f"{percent}%",
                    slider_x + slider_width + 30, y_pos - 10,
                    arcade.color.WHITE, 20, anchor_x="left"
                )

        # Подсказки
        if self.adjusting:
            hint = "← → - Изменить  ENTER - Применить  ESC - Отмена"
        else:
            hint = "↑↓ - Выбор  ENTER - Изменить  ESC - Назад"

        arcade.draw_text(
            hint,
            SCREEN_WIDTH // 2, 100,
            arcade.color.LIGHT_GRAY, 16, anchor_x="center"
        )

    def on_key_press(self, key, modifiers):
        if self.adjusting:
            if key == arcade.key.LEFT:
                if self.current_adjust == 0:
                    self.music_volume = max(0, self.music_volume - 0.05)
                else:
                    self.sound_volume = max(0, self.sound_volume - 0.05)
            elif key == arcade.key.RIGHT:
                if self.current_adjust == 0:
                    self.music_volume = min(1, self.music_volume + 0.05)
                else:
                    self.sound_volume = min(1, self.sound_volume + 0.05)
            elif key == arcade.key.ENTER:
                self.main_menu.music_volume = self.music_volume
                self.main_menu.sound_volume = self.sound_volume
                if self.main_menu.music_player:
                    self.main_menu.music_player.volume = self.music_volume
                self.adjusting = False
            elif key == arcade.key.ESCAPE:
                self.music_volume = self.main_menu.music_volume
                self.sound_volume = self.main_menu.sound_volume
                self.adjusting = False
        else:
            if key == arcade.key.UP:
                self.selected_option = (self.selected_option - 1) % len(self.menu_options)
            elif key == arcade.key.DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.menu_options)
            elif key == arcade.key.ENTER:
                if self.selected_option == 2:  # НАЗАД
                    self.return_to_menu()
                else:
                    self.adjusting = True
                    self.current_adjust = self.selected_option
            elif key == arcade.key.ESCAPE:
                self.return_to_menu()

    def return_to_menu(self):
        self.main_menu.music_volume = self.music_volume
        self.main_menu.sound_volume = self.sound_volume
        self.window.show_view(self.main_menu)


class MainMenu(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_balls = arcade.SpriteList()
        self.particle_system = ParticleSystem()
        self.time_elapsed = 0.0
        self.selected_mode = 0
        self.menu_options = ["ТРЕНИРОВКА", "НА ВРЕМЯ",
                             "ПО ХОДАМ", "ЧЕМПИОНАТ", "НАСТРОЙКИ", "ВЫХОД"]
        self.music_volume = 0.15
        self.sound_volume = 0.7
        self.music_player = None
        self.background_music = None
        self.setup_background()
        self.setup_music()

    def setup_background(self):
        for _ in range(20):
            ball = Ball(
                random.randint(0, SCREEN_WIDTH),
                random.randint(0, SCREEN_HEIGHT),
                random.choice([
                    (255, 100, 100), (100, 255, 100), (100, 100, 255),
                    (255, 255, 100), (255, 100, 255), (100, 255, 255)
                ])
            )
            ball.change_x = random.uniform(-2, 2)
            ball.change_y = random.uniform(-2, 2)
            self.background_balls.append(ball)

    def setup_music(self):
        try:
            if self.music_player:
                self.music_player.stop()
                self.music_player = None

            self.background_music = arcade.load_sound(":resources:music/1918.mp3")
            self.music_player = arcade.play_sound(self.background_music,
                                                  volume=self.music_volume, loop=True)
        except:
            self.background_music = None
            self.music_player = None

    def on_draw(self):
        self.clear()
        arcade.set_background_color(DEEP_SPACE)

        self.draw_stars()

        for ball in self.background_balls:
            arcade.draw_circle_filled(
                ball.center_x, ball.center_y,
                BALL_RADIUS,
                (*ball.color[:3], 40)
            )

        self.particle_system.draw()

        self.draw_title()

        self.draw_menu_options()

        self.draw_hints()

    def draw_stars(self):
        random.seed(0)
        for _ in range(100):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(100, 255)
            arcade.draw_circle_filled(x, y, size, (brightness, brightness, brightness, 150))
        random.seed()

    def draw_title(self):
        for offset in range(5, 0, -1):
            alpha = 50 - offset * 10
            arcade.draw_text(
                "ПРО БИЛЬЯРД",
                SCREEN_WIDTH // 2 + offset, SCREEN_HEIGHT - 150 + offset,
                (0, 255, 255, alpha),
                60, anchor_x="center", bold=True
            )

        arcade.draw_text(
            "ПРО БИЛЬЯРД",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150,
            NEON_CYAN,
            60, anchor_x="center", bold=True
        )

        arcade.draw_text(
            "ULTIMATE",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 200,
            NEON_PINK,
            30, anchor_x="center", bold=True
        )

    def draw_menu_options(self):
        start_y = SCREEN_HEIGHT // 2 + 50

        for i, option in enumerate(self.menu_options):
            color = NEON_GREEN if i == self.selected_mode else arcade.color.LIGHT_GRAY
            y_pos = start_y - i * 50

            if i == self.selected_mode:
                arcade.draw_lrbt_rectangle_filled(
                    SCREEN_WIDTH // 2 - 200, SCREEN_WIDTH // 2 + 200,
                    y_pos - 20, y_pos + 20,
                    (255, 255, 255, 20)
                )

            arcade.draw_text(
                option,
                SCREEN_WIDTH // 2, y_pos,
                color, 28, anchor_x="center"
            )

    def draw_hints(self):
        arcade.draw_text(
            "↑↓ - Выбор  ENTER - Выбрать  ESC - Выход",
            SCREEN_WIDTH // 2, 50,
            arcade.color.LIGHT_GRAY, 16, anchor_x="center"
        )

    def on_update(self, delta_time):
        self.time_elapsed += delta_time

        for ball in self.background_balls:
            ball.center_x += ball.change_x
            ball.center_y += ball.change_y

            if ball.left < 0 or ball.right > SCREEN_WIDTH:
                ball.change_x *= -1
            if ball.bottom < 0 or ball.top > SCREEN_HEIGHT:
                ball.change_y *= -1

        self.particle_system.update(delta_time)

        if random.random() < 0.05:
            self.particle_system.emit_sparks(
                random.randint(100, SCREEN_WIDTH - 100),
                random.randint(100, SCREEN_HEIGHT - 100),
                random.choice([NEON_CYAN, NEON_PINK, NEON_GREEN])
            )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.UP:
            self.selected_mode = (self.selected_mode - 1) % len(self.menu_options)
        elif key == arcade.key.DOWN:
            self.selected_mode = (self.selected_mode + 1) % len(self.menu_options)
        elif key == arcade.key.ENTER:
            self.start_game()
        elif key == arcade.key.ESCAPE:
            arcade.exit()

    def on_mouse_press(self, x, y, button, modifiers):
        start_y = SCREEN_HEIGHT // 2 + 50
        for i in range(len(self.menu_options)):
            y_pos = start_y - i * 50
            if abs(x - SCREEN_WIDTH // 2) < 200 and abs(y - y_pos) < 20:
                self.selected_mode = i
                self.start_game()
                break

    def start_game(self):
        if self.selected_mode == 5:  # ВЫХОД
            arcade.exit()
            return
        elif self.selected_mode == 4:  # НАСТРОЙКИ
            settings_view = SettingsMenu(self)
            self.window.show_view(settings_view)
            return

        game_view = GameView()
        game_view.music_volume = self.music_volume
        game_view.sound_volume = self.sound_volume
        game_view.music_player = self.music_player

        if self.selected_mode == 0:
            game_view.game_mode = GameMode.PRACTICE
        elif self.selected_mode == 1:
            game_view.game_mode = GameMode.TIMED
            game_view.time_remaining = TIME_LIMIT
        elif self.selected_mode == 2:
            game_view.game_mode = GameMode.TURN_BASED
        elif self.selected_mode == 3:
            game_view.game_mode = GameMode.CHALLENGE
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.game_state = GameState.AIMING
        self.game_mode = GameMode.PRACTICE
        self.table = BilliardTable()
        self.balls = arcade.SpriteList()
        self.cue_ball = None
        self.particle_system = ParticleSystem()
        self.physics = GamePhysics()

        self.score = 0
        self.high_score = 0
        self.time_remaining = TIME_LIMIT
        self.turn_time = TURN_TIME_LIMIT
        self.current_turn = 1
        self.balls_potted_this_turn = 0
        self.combo = 0
        self.max_combo = 0
        self.shots_taken = 0
        self.accuracy = 0.0

        self.power = 0.0
        self.aiming_angle = 0.0
        self.aiming_power = 0.0
        self.show_guides = True
        self.selected_ball_type = None

        self.music_volume = 0.15
        self.sound_volume = 0.7
        self.music_player = None
        self.show_volume_indicator = False
        self.volume_indicator_time = 0

        self.setup_sounds()

        self.start_time = time.time()
        self.last_shot_time = 0
        self.consecutive_pots = 0
        self.last_time_update = time.time()

        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.screen_shake = 0.0
        self.slow_motion = False
        self.slow_motion_time = 0.0

        self.background_music = None

    def setup_sounds(self):
        try:
            self.hit_sound = arcade.load_sound(":resources:sounds/hit3.wav")
            self.pocket_sound = arcade.load_sound(":resources:sounds/coin2.wav")
            self.cue_hit_sound = arcade.load_sound(":resources:sounds/laser1.wav")
            self.wall_hit_sound = arcade.load_sound(":resources:sounds/hurt5.wav")
            self.victory_sound = arcade.load_sound(":resources:sounds/upgrade4.wav")
        except:
            self.hit_sound = self.pocket_sound = self.cue_hit_sound = None
            self.wall_hit_sound = self.victory_sound = None

    def setup(self):
        self.balls.clear()
        self.score = 0
        self.current_turn = 1
        self.combo = 0
        self.shots_taken = 0
        self.balls_potted_this_turn = 0
        self.time_remaining = TIME_LIMIT
        self.turn_time = TURN_TIME_LIMIT
        self.game_state = GameState.AIMING
        self.last_time_update = time.time()

        self.cue_ball = Ball(300, SCREEN_HEIGHT // 2,
                             arcade.color.WHITE, BallType.CUE, 0)
        self.balls.append(self.cue_ball)

        self.setup_pyramid()


    def setup_pyramid(self):
        colors_solids = [
            (255, 50, 50),
            (255, 150, 50),
            (255, 255, 50),
            (50, 255, 50),
            (50, 150, 255),
            (100, 50, 200),
            (150, 50, 50),
        ]

        colors_stripes = [
            (255, 100, 100),
            (255, 200, 100),
            (255, 255, 100),
            (100, 255, 100),
            (100, 200, 255),
            (150, 100, 220),
            (200, 100, 100),
        ]

        eight_ball = Ball(SCREEN_WIDTH - 200, SCREEN_HEIGHT // 2,
                          arcade.color.BLACK, BallType.EIGHT, 8)
        self.balls.append(eight_ball)

        pyramid_x = SCREEN_WIDTH - 300
        pyramid_y = SCREEN_HEIGHT // 2

        ball_index = 0

        for row in range(5):
            for col in range(row + 1):
                x = pyramid_x + row * 28
                y = pyramid_y + (col - row / 2) * 28

                if ball_index < 7:
                    ball = Ball(x, y, colors_solids[ball_index],
                                BallType.SOLID, ball_index + 1)
                else:
                    ball = Ball(x, y, colors_stripes[ball_index - 7],
                                BallType.STRIPE, ball_index + 2)

                self.balls.append(ball)
                ball_index += 1

                if ball_index >= 14:
                    break

    def on_draw(self):
        self.clear()
        arcade.set_background_color(DEEP_SPACE)

        self.table.draw()

        for ball in self.balls:
            if ball.change_x != 0 or ball.change_y != 0:
                ball.draw_trail()

        for ball in self.balls:
            shadow_offset = 4
            arcade.draw_circle_filled(
                ball.center_x, ball.center_y - shadow_offset,
                BALL_RADIUS,
                SHADOW_COLOR
            )

        self.balls.draw()

        for ball in self.balls:
            if ball.ball_type != BallType.CUE and ball.number > 0:
                text_color = getattr(ball, 'number_color', arcade.color.WHITE)
                arcade.draw_text(
                    str(ball.number),
                    ball.center_x, ball.center_y,
                    text_color,
                    10, anchor_x="center", anchor_y="center", bold=True
                )

        for ball in self.balls:
            highlight_x = ball.center_x - BALL_RADIUS * 0.3
            highlight_y = ball.center_y + BALL_RADIUS * 0.3
            arcade.draw_circle_filled(
                highlight_x, highlight_y,
                BALL_RADIUS * 0.4,
                HIGHLIGHT_COLOR
            )

        self.particle_system.draw()

        if self.game_state == GameState.AIMING and self.cue_ball:
            self.draw_aiming_interface()

        self.draw_ui()

        if self.slow_motion:
            self.draw_slow_motion_effect()

        if self.game_state == GameState.PAUSED:
            arcade.draw_lrbt_rectangle_filled(
                0, SCREEN_WIDTH, 0, SCREEN_HEIGHT,
                (0, 0, 0, 150)
            )
            arcade.draw_text(
                "ПАУЗА",
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                arcade.color.WHITE, 50, anchor_x="center", bold=True
            )
            arcade.draw_text(
                "Нажми P для продолжения",
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
                arcade.color.LIGHT_GRAY, 20, anchor_x="center"
            )

        if self.show_volume_indicator:
            time_left = self.volume_indicator_time - time.time()
            if time_left > 0:
                alpha = min(255, int(255 * time_left))
                arcade.draw_lrbt_rectangle_filled(
                    SCREEN_WIDTH // 2 - 200, SCREEN_WIDTH // 2 + 200,
                    SCREEN_HEIGHT // 2 - 50, SCREEN_HEIGHT // 2 + 50,
                    (0, 0, 0, 180)
                )
                arcade.draw_text(
                    "ГРОМКОСТЬ МУЗЫКИ",
                    SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20,
                    arcade.color.WHITE, 24, anchor_x="center", bold=True
                )
                # Ползунок
                slider_x = SCREEN_WIDTH // 2 - 150
                slider_width = 300
                slider_height = 20
                slider_y = SCREEN_HEIGHT // 2 - 20

                arcade.draw_lrbt_rectangle_filled(
                    slider_x, slider_x + slider_width,
                              slider_y - slider_height // 2, slider_y + slider_height // 2,
                    (50, 50, 50, 200)
                )

                fill_width = slider_width * self.music_volume
                arcade.draw_lrbt_rectangle_filled(
                    slider_x, slider_x + fill_width,
                              slider_y - slider_height // 2, slider_y + slider_height // 2,
                    NEON_CYAN
                )

                percent = int(self.music_volume * 100)
                arcade.draw_text(
                    f"{percent}%",
                    SCREEN_WIDTH // 2, slider_y - 30,
                    arcade.color.WHITE, 20, anchor_x="center"
                )

                arcade.draw_text(
                    "← → для изменения  ESC для выхода",
                    SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60,
                    arcade.color.LIGHT_GRAY, 16, anchor_x="center"
                )
            else:
                self.show_volume_indicator = False

    def draw_aiming_interface(self):
        mouse_x, mouse_y = self.window._mouse_x, self.window._mouse_y

        dx = mouse_x - self.cue_ball.center_x
        dy = mouse_y - self.cue_ball.center_y
        distance = max(math.sqrt(dx * dx + dy * dy), 1)
        angle = math.atan2(dy, dx)

        max_distance = 200
        if distance > max_distance:
            distance = max_distance
            mouse_x = self.cue_ball.center_x + math.cos(angle) * max_distance
            mouse_y = self.cue_ball.center_y + math.sin(angle) * max_distance

        arcade.draw_line(
            self.cue_ball.center_x, self.cue_ball.center_y,
            mouse_x, mouse_y,
            (255, 255, 255, 180), 2
        )

        for i in range(1, 6):
            t = i / 6
            point_x = self.cue_ball.center_x + math.cos(angle) * distance * t
            point_y = self.cue_ball.center_y + math.sin(angle) * distance * t
            arcade.draw_circle_filled(
                point_x, point_y, 3,
                (255, 255, 255, 200 - i * 30)
            )

        arcade.draw_circle_outline(mouse_x, mouse_y, 20, (255, 255, 255, 150), 2)
        arcade.draw_circle_filled(mouse_x, mouse_y, 3, (255, 255, 255))

        self.aiming_power = min(distance / 100, 1.0)
        power_bar_width = 200
        power_bar_height = 20
        power_bar_x = SCREEN_WIDTH // 2 - power_bar_width // 2
        power_bar_y = 100

        arcade.draw_lrbt_rectangle_filled(
            power_bar_x, power_bar_x + power_bar_width,
                         power_bar_y - power_bar_height // 2, power_bar_y + power_bar_height // 2,
            (50, 50, 50, 200)
        )

        fill_width = power_bar_width * self.aiming_power
        color_gradient = (
            int(50 + 205 * self.aiming_power),
            int(255 - 155 * self.aiming_power),
            50
        )

        arcade.draw_lrbt_rectangle_filled(
            power_bar_x, power_bar_x + fill_width,
                         power_bar_y - power_bar_height // 2, power_bar_y + power_bar_height // 2,
            color_gradient
        )

        arcade.draw_lrbt_rectangle_outline(
            power_bar_x, power_bar_x + power_bar_width,
                         power_bar_y - power_bar_height // 2, power_bar_y + power_bar_height // 2,
            (255, 255, 255, 200), 2
        )

        arcade.draw_text(
            f"СИЛА: {int(self.aiming_power * 100)}%",
            SCREEN_WIDTH // 2, power_bar_y + 30,
            (255, 255, 255), 16,
            anchor_x="center"
        )

        if self.show_guides:
            self.draw_bank_shot_preview(angle, distance)

    def draw_bank_shot_preview(self, angle: float, distance: float):
        preview_length = 800
        segments = 3

        current_x, current_y = self.cue_ball.center_x, self.cue_ball.center_y
        current_dx, current_dy = math.cos(angle), math.sin(angle)
        power = self.aiming_power * MAX_POWER

        for segment in range(segments):
            t_left = (65 - current_x) / current_dx if current_dx != 0 else float('inf')
            t_right = (SCREEN_WIDTH - 65 - current_x) / current_dx if current_dx != 0 else float('inf')
            t_bottom = (65 - current_y) / current_dy if current_dy != 0 else float('inf')
            t_top = (SCREEN_HEIGHT - 65 - current_y) / current_dy if current_dy != 0 else float('inf')

            t_min = min(t for t in [t_left, t_right, t_bottom, t_top] if t > 0)

            if t_min > preview_length / power:
                end_x = current_x + current_dx * preview_length
                end_y = current_y + current_dy * preview_length
                arcade.draw_line(
                    current_x, current_y, end_x, end_y,
                    (255, 255, 0, 100 - segment * 30), 1
                )
                break

            bounce_x = current_x + current_dx * t_min
            bounce_y = current_y + current_dy * t_min

            arcade.draw_line(
                current_x, current_y, bounce_x, bounce_y,
                (255, 255, 0, 100 - segment * 30), 1
            )

            arcade.draw_circle_outline(
                bounce_x, bounce_y, 8,
                (255, 255, 0, 150 - segment * 50), 1
            )

            if abs(bounce_x - 65) < 1 or abs(bounce_x - (SCREEN_WIDTH - 65)) < 1:
                current_dx *= -WALL_BOUNCE
            if abs(bounce_y - 65) < 1 or abs(bounce_y - (SCREEN_HEIGHT - 65)) < 1:
                current_dy *= -WALL_BOUNCE

            current_x, current_y = bounce_x, bounce_y
            preview_length -= t_min * power

    def draw_ui(self):
        stats_bg_color = (0, 0, 0, 180)
        arcade.draw_lrbt_rectangle_filled(0, 200, SCREEN_HEIGHT - 80, SCREEN_HEIGHT, stats_bg_color)
        arcade.draw_lrbt_rectangle_outline(0, 200, SCREEN_HEIGHT - 80, SCREEN_HEIGHT, NEON_CYAN, 2)

        # Предотвращаем отрицательный счет
        display_score = max(0, self.score)
        score_color = NEON_CYAN if display_score > self.high_score else arcade.color.WHITE
        arcade.draw_text(
            f"СЧЕТ: {display_score}",
            20, SCREEN_HEIGHT - 60,
            score_color, 24, bold=True
        )

        arcade.draw_text(
            f"РЕКОРД: {self.high_score}",
            20, SCREEN_HEIGHT - 90,
            arcade.color.LIGHT_GRAY, 18
        )

        if self.combo > 1:
            combo_color = NEON_PINK if self.combo >= 5 else NEON_GREEN
            arcade.draw_text(
                f"КОМБО x{self.combo}!",
                SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60,
                combo_color, 28, bold=True
            )

        if self.game_mode == GameMode.TIMED:
            time_color = (255, 100, 100) if self.time_remaining < 30 else arcade.color.WHITE
            minutes = int(max(0, self.time_remaining) // 60)
            seconds = int(max(0, self.time_remaining) % 60)
            arcade.draw_text(
                f"ВРЕМЯ: {minutes:02d}:{seconds:02d}",
                SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40,
                time_color, 24, anchor_x="center"
            )

        if self.game_mode == GameMode.TURN_BASED:
            arcade.draw_text(
                f"ХОД: {self.current_turn}",
                SCREEN_WIDTH // 2, SCREEN_HEIGHT - 70,
                arcade.color.LIGHT_GRAY, 20, anchor_x="center"
            )

            arcade.draw_text(
                f"ШАРОВ: {self.balls_potted_this_turn}",
                SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
                arcade.color.LIGHT_GRAY, 16, anchor_x="center"
            )

        accuracy_text = f"ТОЧНОСТЬ: {self.accuracy:.1f}%"
        arcade.draw_text(
            accuracy_text,
            SCREEN_WIDTH - len(accuracy_text) * 6 - 20, 40,
            arcade.color.LIGHT_GRAY, 16
        )

        if self.game_state != GameState.PAUSED and not self.show_volume_indicator:
            state_text = ""
            if self.game_state == GameState.AIMING:
                state_text = "ПРИЦЕЛ - Кликни для удара"
            elif self.game_state == GameState.BALLS_MOVING:
                state_text = "ШАРЫ ДВИГАЮТСЯ"

            if state_text:
                arcade.draw_text(
                    state_text,
                    SCREEN_WIDTH // 2, 80,
                    arcade.color.WHITE, 20,
                    anchor_x="center"
                )

        hints = [
            "ЛКМ: Удар  |  ПКМ: Сила удара",
            "R: Сброс шара  |  P: Пауза",
            "G: Направляющие  |  M: Громкость",
            "ESC: Меню"
        ]

        for i, hint in enumerate(hints):
            arcade.draw_text(
                hint,
                SCREEN_WIDTH // 2, 20 + i * 20,
                arcade.color.LIGHT_GRAY, 12,
                anchor_x="center"
            )

    def draw_slow_motion_effect(self):
        overlay = (0, 100, 255, 30)
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, 0, SCREEN_HEIGHT,
            overlay
        )

        for i in range(5):
            alpha = 10 + i * 5
            border_color = (0, 50, 255, alpha)
            arcade.draw_lrbt_rectangle_outline(
                i, SCREEN_WIDTH - i, i, SCREEN_HEIGHT - i,
                border_color, 1
            )

    def on_update(self, delta_time: float):
        current_time = time.time()

        # Если игра на паузе - ничего не обновляем
        if self.game_state == GameState.PAUSED:
            return

        # Обновление времени для режима "НА ВРЕМЯ"
        if self.game_mode == GameMode.TIMED and self.game_state != GameState.PAUSED:
            self.time_remaining -= delta_time
            if self.time_remaining <= 0:
                self.time_remaining = 0
                self.game_over()

        if self.slow_motion:
            delta_time *= 0.3
            self.slow_motion_time -= delta_time
            if self.slow_motion_time <= 0:
                self.slow_motion = False

        if self.game_mode == GameMode.TURN_BASED and self.game_state == GameState.AIMING:
            self.turn_time -= delta_time
            if self.turn_time <= 0:
                self.end_turn()

        balls_moving = False
        for ball in self.balls:
            ball.update(delta_time)

            if self.physics.check_wall_collision(ball):
                if hasattr(self, 'wall_hit_sound') and self.wall_hit_sound:
                    volume = min(0.5, math.sqrt(ball.change_x ** 2 + ball.change_y ** 2) / 20) * self.sound_volume
                    arcade.play_sound(self.wall_hit_sound, volume=volume)
                    self.particle_system.emit_sparks(
                        ball.center_x, ball.center_y,
                        (200, 200, 200),
                        count=3,
                        speed=2
                    )

            if ball.change_x != 0 or ball.change_y != 0:
                balls_moving = True

        balls_list = list(self.balls)
        for i in range(len(balls_list)):
            for j in range(i + 1, len(balls_list)):
                ball1, ball2 = balls_list[i], balls_list[j]
                if ball1.in_pocket or ball2.in_pocket:
                    continue

                dx = ball2.center_x - ball1.center_x
                dy = ball2.center_y - ball1.center_y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < BALL_RADIUS * 2.1:
                    self.physics.resolve_ball_collision(ball1, ball2)

                    relative_speed = abs(ball1.change_x - ball2.change_x) + abs(ball1.change_y - ball2.change_y)
                    if relative_speed > 1.0 and hasattr(self, 'hit_sound') and self.hit_sound:
                        volume = min(0.7, relative_speed / 30) * self.sound_volume
                        arcade.play_sound(self.hit_sound, volume=volume)

                        if relative_speed > 3.0:
                            mid_x = (ball1.center_x + ball2.center_x) / 2
                            mid_y = (ball1.center_y + ball2.center_y) / 2
                            self.particle_system.emit_sparks(
                                mid_x, mid_y,
                                ball1.color[:3],
                                count=int(relative_speed * 2),
                                speed=relative_speed * 0.5
                            )

                            if relative_speed > 8.0:
                                self.screen_shake = min(10.0, relative_speed * 0.8)

        if self.screen_shake > 0:
            self.screen_shake *= 0.9
            if self.screen_shake < 0.1:
                self.screen_shake = 0

        self.check_pocket_collisions()

        if balls_moving:
            self.game_state = GameState.BALLS_MOVING
        else:
            if self.game_state == GameState.BALLS_MOVING:
                self.on_balls_stopped()
            self.game_state = GameState.AIMING

        self.particle_system.update(delta_time)

        self.check_win_conditions()

    def check_pocket_collisions(self):
        for ball in self.balls[:]:
            if ball.in_pocket:
                continue

            for px, py in self.table.pocket_locations:
                distance = math.sqrt((ball.center_x - px) ** 2 + (ball.center_y - py) ** 2)

                if distance < POCKET_RADIUS:
                    self.on_ball_potted(ball, px, py)
                    break

    def on_ball_potted(self, ball: Ball, pocket_x: float, pocket_y: float):
        ball.in_pocket = True
        ball.pocket_time = time.time()

        if hasattr(self, 'pocket_sound') and self.pocket_sound:
            arcade.play_sound(self.pocket_sound, volume=0.6 * self.sound_volume)

        self.particle_system.emit_pocket(pocket_x, pocket_y)

        self.slow_motion = True
        self.slow_motion_time = 1.0

        if ball.ball_type == BallType.CUE:
            # Биток просто возвращается на место без штрафа
            ball.center_x, ball.center_y = 300, SCREEN_HEIGHT // 2
            ball.change_x, ball.change_y = 0, 0
            ball.in_pocket = False
            self.combo = 0

            if self.game_mode == GameMode.TURN_BASED:
                self.end_turn()
        else:
            base_points = 100
            bonus_points = 0

            if ball.ball_type == BallType.EIGHT:
                bonus_points = 500
                if self.game_mode == GameMode.TURN_BASED:
                    self.game_over(victory=True)
            elif ball.ball_type == BallType.SPECIAL:
                bonus_points = 300
            elif ball.number == 7 or ball.number == 15:
                bonus_points = 150

            combo_multiplier = 1 + (self.combo * 0.2)
            points = int((base_points + bonus_points) * combo_multiplier)

            self.score += points
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.balls_potted_this_turn += 1
            self.consecutive_pots += 1

            ball.remove_from_sprite_lists()

            self.show_score_popup(ball.center_x, ball.center_y, points)

            if self.combo >= 3:
                self.screen_shake = min(15.0, self.combo * 2)

    def show_score_popup(self, x: float, y: float, points: int):
        color = NEON_GREEN if points < 300 else NEON_PINK
        self.particle_system.emit_sparks(x, y, color, count=20, speed=5)

    def on_balls_stopped(self):
        self.shots_taken += 1

        if self.shots_taken > 0:
            successful_shots = self.shots_taken
            self.accuracy = (successful_shots / self.shots_taken) * 100

        if self.consecutive_pots == 0:
            self.combo = 0
        self.consecutive_pots = 0

    def check_cue_ball_contact(self) -> bool:
        return True

    def check_win_conditions(self):
        if self.game_mode == GameMode.TIMED and self.time_remaining <= 0:
            self.game_over()

        balls_remaining = sum(1 for ball in self.balls
                              if not ball.in_pocket and ball.ball_type != BallType.CUE)

        if balls_remaining == 0:
            self.game_over(victory=True)

        if self.score >= MAX_SCORE * 1000:
            self.game_over(victory=True)

    def game_over(self, victory: bool = False):
        self.game_state = GameState.GAME_OVER

        if self.score > self.high_score:
            self.high_score = self.score

        if victory and hasattr(self, 'victory_sound') and self.victory_sound:
            arcade.play_sound(self.victory_sound, volume=0.8 * self.sound_volume)

        self.show_results_screen(victory)

    def show_results_screen(self, victory: bool):
        results_view = ResultsView(self.score, self.high_score, victory,
                                   self.game_mode, self.accuracy, self.max_combo,
                                   self.music_volume, self.sound_volume)
        self.window.show_view(results_view)

    def end_turn(self, penalty: bool = False):
        self.current_turn += 1
        self.balls_potted_this_turn = 0
        self.turn_time = TURN_TIME_LIMIT
        self.combo = 0

        if self.cue_ball and self.cue_ball.in_pocket:
            self.cue_ball.reset()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if self.game_state != GameState.AIMING or self.game_state == GameState.PAUSED or self.show_volume_indicator:
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            self.take_shot(x, y)
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.adjust_power(x, y)

    def take_shot(self, target_x: float, target_y: float):
        if not self.cue_ball or self.cue_ball.in_pocket:
            return

        dx = target_x - self.cue_ball.center_x
        dy = target_y - self.cue_ball.center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return

        power = min(self.aiming_power * MAX_POWER, MAX_POWER)
        power = max(power, MIN_POWER)

        self.cue_ball.apply_force(dx, dy, power)

        self.particle_system.emit_cue_hit(
            self.cue_ball.center_x,
            self.cue_ball.center_y,
            power
        )

        if hasattr(self, 'cue_hit_sound') and self.cue_hit_sound:
            volume = min(0.8, power / MAX_POWER * 0.5 + 0.3) * self.sound_volume
            arcade.play_sound(self.cue_hit_sound, volume=volume)

        self.last_shot_time = time.time()
        self.game_state = GameState.BALLS_MOVING

    def adjust_power(self, x: float, y: float):
        if not self.cue_ball:
            return
        max_distance = 300
        distance = min(math.sqrt(
            (x - self.cue_ball.center_x) ** 2 +
            (y - self.cue_ball.center_y) ** 2
        ), max_distance)

        self.aiming_power = distance / max_distance

    def on_key_press(self, key: int, modifiers: int):
        if self.show_volume_indicator:
            if key == arcade.key.LEFT:
                self.music_volume = max(0, self.music_volume - 0.05)
                if self.music_player:
                    self.music_player.volume = self.music_volume
                self.volume_indicator_time = time.time() + 2
            elif key == arcade.key.RIGHT:
                self.music_volume = min(1, self.music_volume + 0.05)
                if self.music_player:
                    self.music_player.volume = self.music_volume
                self.volume_indicator_time = time.time() + 2
            elif key == arcade.key.ESCAPE:
                self.show_volume_indicator = False
            return

        if key == arcade.key.P:
            self.toggle_pause()
        elif key == arcade.key.R and self.game_state == GameState.AIMING:
            self.reset_shot()
        elif key == arcade.key.G:
            self.show_guides = not self.show_guides
        elif key == arcade.key.M:
            self.show_volume_indicator = True
            self.volume_indicator_time = time.time() + 2
        elif key == arcade.key.ESCAPE:
            self.return_to_menu()
        elif key == arcade.key.SPACE and self.game_state == GameState.AIMING:
            mouse_x, mouse_y = self.window._mouse_x, self.window._mouse_y
            self.take_shot(mouse_x, mouse_y)
        elif key == arcade.key.ENTER and self.game_state == GameState.GAME_OVER:
            self.restart_game()

    def toggle_pause(self):
        if self.game_state == GameState.PAUSED:
            self.game_state = GameState.AIMING
        else:
            self.game_state = GameState.PAUSED

    def reset_shot(self):
        if self.cue_ball and self.game_state == GameState.AIMING:
            self.cue_ball.center_x, self.cue_ball.center_y = 300, SCREEN_HEIGHT // 2
            self.cue_ball.change_x, self.cue_ball.change_y = 0, 0

    def return_to_menu(self):
        menu_view = MainMenu()
        # Возвращаем настройки громкости в меню
        menu_view.music_volume = self.music_volume
        menu_view.sound_volume = self.sound_volume
        menu_view.setup_music()
        self.window.show_view(menu_view)

    def restart_game(self):
        self.setup()


class ResultsView(arcade.View):
    def __init__(self, score: int, high_score: int, victory: bool,
                 game_mode: GameMode, accuracy: float, max_combo: int,
                 music_volume: float, sound_volume: float):
        super().__init__()
        self.score = score
        self.high_score = high_score
        self.victory = victory
        self.game_mode = game_mode
        self.accuracy = accuracy
        self.max_combo = max_combo
        self.music_volume = music_volume
        self.sound_volume = sound_volume
        self.time_elapsed = 0.0
        self.particles = ParticleSystem()

    def on_draw(self):
        self.clear()
        arcade.set_background_color(DEEP_SPACE)

        self.draw_background_effects()

        if self.victory:
            title = "ПОБЕДА!"
            title_color = NEON_GREEN
            subtitle = "Отличная игра!"
        else:
            title = "ИГРА ОКОНЧЕНА"
            title_color = (255, 100, 100)
            subtitle = "Повезет в следующий раз!"

        arcade.draw_text(
            title, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 150,
            title_color, 60, anchor_x="center", bold=True
        )

        arcade.draw_text(
            subtitle, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 200,
            arcade.color.WHITE, 24, anchor_x="center"
        )

        stats_y = SCREEN_HEIGHT - 300
        mode_names = {
            GameMode.PRACTICE: "Тренировка",
            GameMode.TIMED: "На время",
            GameMode.TURN_BASED: "По ходам",
            GameMode.CHALLENGE: "Чемпионат"
        }

        stats = [
            ("ИТОГОВЫЙ СЧЕТ", f"{max(0, self.score):,}"),
            ("РЕКОРД", f"{self.high_score:,}"),
            ("РЕЖИМ", mode_names.get(self.game_mode, "Неизвестно")),
            ("ТОЧНОСТЬ", f"{self.accuracy:.1f}%"),
            ("МАКС КОМБО", f"x{self.max_combo}"),
            ("НОВЫЙ РЕКОРД", "ДА!" if self.score > self.high_score else "Нет")
        ]

        for i, (label, value) in enumerate(stats):
            y = stats_y - i * 50

            arcade.draw_text(
                label, SCREEN_WIDTH // 2 - 150, y,
                arcade.color.LIGHT_GRAY, 22, anchor_x="right"
            )

            value_color = NEON_CYAN if "РЕКОРД" in label and "ДА" in value else arcade.color.WHITE
            arcade.draw_text(
                value, SCREEN_WIDTH // 2 - 120, y,
                value_color, 22, anchor_x="left"
            )

        button_y = 150
        buttons = [
            ("ИГРАТЬ СНОВА", self.restart_game),
            ("ГЛАВНОЕ МЕНЮ", self.return_to_menu),
            ("ВЫХОД", arcade.exit)
        ]

        for i, (text, _) in enumerate(buttons):
            x = SCREEN_WIDTH // 2 + (i - 1) * 200
            y = button_y

            arcade.draw_lrbt_rectangle_filled(
                x - 90, x + 90, y - 25, y + 25,
                (40, 40, 60, 200)
            )

            arcade.draw_lrbt_rectangle_outline(
                x - 90, x + 90, y - 25, y + 25,
                NEON_CYAN, 2
            )

            arcade.draw_text(
                text, x, y,
                arcade.color.WHITE, 20,
                anchor_x="center", anchor_y="center"
            )

        arcade.draw_text(
            "Нажми ENTER чтобы играть снова, ESC для меню",
            SCREEN_WIDTH // 2, 50,
            arcade.color.LIGHT_GRAY, 16, anchor_x="center"
        )

        self.particles.draw()

    def draw_background_effects(self):
        pulse = abs(math.sin(self.time_elapsed * 2)) * 0.5 + 0.5
        radius = 100 + pulse * 50

        for i in range(3):
            offset = i * 120
            color = (
                int(NEON_CYAN[0] * (1 - i * 0.3)),
                int(NEON_CYAN[1] * (1 - i * 0.3)),
                int(NEON_CYAN[2] * (1 - i * 0.3)),
                30
            )

            arcade.draw_circle_outline(
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                radius + offset,
                color, 3
            )

    def on_update(self, delta_time: float):
        self.time_elapsed += delta_time
        self.particles.update(delta_time)

        if random.random() < 0.1:
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            self.particles.emit_sparks(x, y, NEON_CYAN, count=5, speed=2)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        button_y = 150
        buttons = [
            ("ИГРАТЬ СНОВА", self.restart_game),
            ("ГЛАВНОЕ МЕНЮ", self.return_to_menu),
            ("ВЫХОД", arcade.exit)
        ]

        for i, (_, action) in enumerate(buttons):
            btn_x = SCREEN_WIDTH // 2 + (i - 1) * 200
            btn_y = button_y

            if abs(x - btn_x) < 90 and abs(y - btn_y) < 25:
                action()
                break

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.ENTER:
            self.restart_game()
        elif key == arcade.key.ESCAPE:
            self.return_to_menu()

    def restart_game(self):
        game_view = GameView()
        game_view.game_mode = self.game_mode
        game_view.music_volume = self.music_volume
        game_view.sound_volume = self.sound_volume
        game_view.setup()
        self.window.show_view(game_view)

    def return_to_menu(self):
        menu_view = MainMenu()
        menu_view.music_volume = self.music_volume
        menu_view.sound_volume = self.sound_volume
        menu_view.setup_music()
        self.window.show_view(menu_view)


def main():
    window = arcade.Window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_TITLE,
        resizable=True,
        fullscreen=False
    )

    menu_view = MainMenu()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()