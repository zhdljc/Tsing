"""
Terrain Explorer Library - 3D Terrain Exploration with Enhanced Flight Controls
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import noise
import random
from math import sin, cos, radians, sqrt, pi, atan2, degrees
import numpy as np

# System configuration
SCREEN_SIZE = (1280, 720)
TERRAIN_SCALE = 0.05
HEIGHT_SCALE = 25.0
MOUSE_SENSITIVITY = 0.15
PLAYER_SPEED = 4.5
GRAVITY = 9.8
JUMP_FORCE = 6.0
PLAYER_HEIGHT = 1.8
LOAD_RADIUS = 30
MAX_CLIMB_ANGLE = 45
MAX_JUMP_HEIGHT = 1.2
SEED = random.randint(0, 10000)
DAY_LENGTH = 120.0
TERRAIN_BLOCK_SIZE = 1.0
SMOOTH_TERRAIN = True
FOG_ENABLED = True
FOG_DISTANCE = 150.0
STEP_HEIGHT = 0.5
TERRAIN_DETAIL = 1.0
TERRAIN_DIVERSITY = 1.0
MAX_TERRAIN_HEIGHT = 50.0
MIN_TERRAIN_HEIGHT = -20.0

# Terrain type constants
PLAINS = 0
HILLS = 1
MOUNTAINS = 2
PLATEAU = 3
BASIN = 4
CANYON = 5
VALLEY = 6

# Flight mode constants
NORMAL_MODE = 0
FLIGHT_MODE = 1
FREE_FLIGHT_MODE = 2

# Flight control parameters
BASE_LIFT = 5.0
MAX_LIFT = 15.0
LIFT_INCREMENT = 1.0
HOVER_LIFT = 9.8  # Lift to counteract gravity
FLIGHT_SPEED_MULTIPLIER = 2.0
FLIGHT_CONTROL_SENSITIVITY = 0.5
MAX_FLIGHT_SPEED = 20.0

class UI:
    def __init__(self, screen_size):
        self.screen_size = screen_size
        self.font = None
        self.buttons = []
        self.state = "title"
        self.create_ui_elements()

    def init_fonts(self):
        """Initialize fonts after Pygame is initialized"""
        try:
            self.font = pygame.font.SysFont('Arial', 32)
        except:
            # Fallback if font initialization fails
            self.font = pygame.font.Font(None, 32)

    def set_screen_size(self, size):
        self.screen_size = size
        self.create_ui_elements()

    def create_ui_elements(self):
        # Title screen buttons
        self.title_buttons = [
            {"rect": pygame.Rect(self.screen_size[0] // 2 - 100, self.screen_size[1] // 2, 200, 50),
             "text": "Start Game", "action": "start"},
            {"rect": pygame.Rect(self.screen_size[0] // 2 - 100, self.screen_size[1] // 2 + 70, 200, 50),
             "text": "Exit", "action": "exit"}
        ]

        # Pause menu buttons
        self.pause_buttons = [
            {"rect": pygame.Rect(self.screen_size[0] // 2 - 100, self.screen_size[1] // 2, 200, 50),
             "text": "Continue", "action": "continue"},
            {"rect": pygame.Rect(self.screen_size[0] // 2 - 100, self.screen_size[1] // 2 + 70, 200, 50),
             "text": "Main Menu", "action": "menu"}
        ]

    def render_text(self, text, x, y, color=(255, 255, 255), size=32):
        try:
            font = pygame.font.SysFont('Arial', size)
        except:
            font = pygame.font.Font(None, size)

        text_surface = font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)

        glWindowPos2i(x, self.screen_size[1] - y - text_surface.get_height())
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                     GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    def render_button(self, button):
        if not self.font:
            return

        # Button background
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(button["rect"].left, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].bottom)
        glVertex2i(button["rect"].left, button["rect"].bottom)
        glEnd()

        # Button border
        glColor3f(0.8, 0.8, 0.8)
        glBegin(GL_LINE_LOOP)
        glVertex2i(button["rect"].left, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].bottom)
        glVertex2i(button["rect"].left, button["rect"].bottom)
        glEnd()

        # Button text
        text_x = button["rect"].centerx - self.font.size(button["text"])[0] // 2
        text_y = button["rect"].centery - self.font.size(button["text"])[1] // 2
        self.render_text(button["text"], text_x, text_y)

    def check_click(self, pos):
        buttons = self.title_buttons if self.state == "title" else self.pause_buttons
        for button in buttons:
            if button["rect"].collidepoint(pos):
                return button["action"]
        return None

    def render_title_screen(self):
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Title
        self.render_text("Terrain Explorer", self.screen_size[0] // 2 - 150, 150, (255, 255, 255), 48)

        # Buttons
        for button in self.title_buttons:
            self.render_button(button)

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)

    def render_pause_menu(self):
        # Semi-transparent overlay
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glColor4f(0.1, 0.1, 0.1, 0.7)
        glBegin(GL_QUADS)
        glVertex2i(0, 0)
        glVertex2i(self.screen_size[0], 0)
        glVertex2i(self.screen_size[0], self.screen_size[1])
        glVertex3i(0, self.screen_size[1], 0)
        glEnd()

        # Title
        self.render_text("Paused", self.screen_size[0] // 2 - 70, 150, (255, 255, 255), 48)

        # Buttons
        for button in self.pause_buttons:
            self.render_button(button)

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)


class DebugInfo:
    def __init__(self, screen_size):
        self.screen_size = screen_size
        self.show_info = False
        self.full_info = False
        self.font = None
        self.small_font = None
        self.fps = 0
        self.player_pos = (0, 0, 0)
        self.player_rot = (0, 0)
        self.rendered_chunks = 0
        self.day_time = 0.0
        self.slope_angle = 0.0
        self.terrain_block_size = TERRAIN_BLOCK_SIZE
        self.smooth_terrain = SMOOTH_TERRAIN
        self.third_person = False
        self.fog_distance = FOG_DISTANCE
        self.player_velocity = (0, 0, 0)
        self.on_ground = False
        self.collision_info = ""
        self.terrain_type = "Unknown"
        self.player_mode = "Normal"
        self.lift_force = BASE_LIFT

    def init_fonts(self):
        """Initialize fonts after Pygame is initialized"""
        try:
            self.font = pygame.font.SysFont('Arial', 20)
        except:
            self.font = pygame.font.Font(None, 20)

        try:
            self.small_font = pygame.font.SysFont('Arial', 16)
        except:
            self.small_font = pygame.font.Font(None, 16)

    def set_screen_size(self, size):
        self.screen_size = size

    def toggle(self):
        self.show_info = not self.show_info

    def toggle_full(self):
        self.full_info = not self.full_info

    def update(self, fps, pos, rot, chunks, time, slope, third_person, vel, ground, collision, terrain_type, mode, lift):
        self.fps = fps
        self.player_pos = pos
        self.player_rot = rot
        self.rendered_chunks = chunks
        self.day_time = time
        self.slope_angle = slope
        self.third_person = third_person
        self.player_velocity = vel
        self.on_ground = ground
        self.collision_info = collision
        self.terrain_type = terrain_type
        self.player_mode = mode
        self.lift_force = lift

    def render(self):
        if not self.show_info:
            return

        try:
            hours = int((self.day_time * 24) / DAY_LENGTH) % 24
            minutes = int((self.day_time * 24 * 60) / DAY_LENGTH) % 60
            seconds = int((self.day_time * 24 * 3600) / DAY_LENGTH) % 60

            # Basic info
            basic_texts = [
                f"FPS: {self.fps}",
                f"Position: X={self.player_pos[0]:.1f} Y={self.player_pos[1]:.1f} Z={self.player_pos[2]:.1f}",
                f"Terrain: {self.terrain_type}",
                f"Mode: {self.player_mode}",
                f"Lift: {self.lift_force:.1f}",
                f"Rotation: Yaw={self.player_rot[0]:.1f} Pitch={self.player_rot[1]:.1f}",
                f"Velocity: X={self.player_velocity[0]:.1f} Y={self.player_velocity[1]:.1f} Z={self.player_velocity[2]:.1f}",
                f"Ground: {'Yes' if self.on_ground else 'No'}",
                f"Slope: {self.slope_angle:.1f}°",
                f"Camera: {'3rd Person' if self.third_person else '1st Person'}"
            ]

            # Developer info
            if self.full_info:
                basic_texts.extend([
                    f"Chunks: {self.rendered_chunks}",
                    f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}",
                    f"Block Size: {self.terrain_block_size:.2f}",
                    f"Smoothing: {'ON' if self.smooth_terrain else 'OFF'}",
                    f"Fog Distance: {self.fog_distance:.1f}",
                    f"Seed: {SEED}",
                    f"Collision: {self.collision_info}",
                    "",
                    "Controls:",
                    "WASD - Move, SPACE - Jump/Fly Up",
                    "TAB - Toggle Flight Mode",
                    "CTRL+TAB - Toggle Free Flight",
                    "F1 - Reset Flight",
                    "SHIFT - Fly Down/Crouch",
                    "CTRL - Set Hover Lift",
                    "ALT - Increase Lift",
                    "F3 - Toggle Debug Info",
                    "F12 - Toggle Full Debug",
                    "F5 - Toggle Camera",
                    "F6 - Toggle Smooth Terrain",
                    "F7/F8 - Adjust Fog Distance",
                    "F9 - Toggle Fog",
                    "+/- - Adjust Terrain Detail"
                ])

            debug_surface = pygame.Surface(self.screen_size, pygame.SRCALPHA)
            debug_surface.fill((0, 0, 0, 0))

            y_offset = 10
            for i, text in enumerate(basic_texts):
                if not self.font or not self.small_font:
                    break

                if self.full_info and i >= 10:
                    font = self.small_font
                    line_height = 20
                else:
                    font = self.font
                    line_height = 25

                text_surface = font.render(text, True, (255, 255, 255, 255))
                debug_surface.blit(text_surface, (10, y_offset))
                y_offset += line_height

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            texture_data = pygame.image.tostring(debug_surface, "RGBA", True)
            glWindowPos2i(0, 0)
            glDrawPixels(self.screen_size[0], self.screen_size[1], GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

            glEnable(GL_DEPTH_TEST)
            glDisable(GL_BLEND)

        except Exception as e:
            print(f"Debug render error: {e}")


def init_gl(screen_size):
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glShadeModel(GL_SMOOTH)
    glClearDepth(1.0)

    # Disable backface culling to fix terrain rendering issues
    glDisable(GL_CULL_FACE)

    if FOG_ENABLED:
        setup_fog()

    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, screen_size[0] / screen_size[1], 0.1, 1000)
    glMatrixMode(GL_MODELVIEW)


def setup_fog():
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogfv(GL_FOG_COLOR, (0.53, 0.81, 0.98, 1.0))
    glFogf(GL_FOG_START, FOG_DISTANCE * 0.6)
    glFogf(GL_FOG_END, FOG_DISTANCE)


class Terrain:
    def __init__(self):
        self.vertices = {}
        self.normals = {}
        self.generated_area = set()
        self.block_size = TERRAIN_BLOCK_SIZE
        self.smooth = SMOOTH_TERRAIN
        self.erosion_cache = {}

    def get_height(self, x, z):
        x_adj = x / self.block_size
        z_adj = z / self.block_size

        cache_key = (round(x, 2), round(z, 2))
        if cache_key in self.erosion_cache:
            return self.erosion_cache[cache_key]

        if not self.smooth:
            x0, z0 = int(x_adj), int(z_adj)
            height = noise.pnoise2(x0 * TERRAIN_SCALE + SEED,
                                   z0 * TERRAIN_SCALE + SEED,
                                   octaves=6, persistence=0.5, lacunarity=1.8) * HEIGHT_SCALE
        else:
            x0, z0 = int(x_adj), int(z_adj)
            dx, dz = x_adj - x0, z_adj - z0

            points = []
            for i in range(2):
                for j in range(2):
                    px = x0 + i
                    pz = z0 + j
                    if (px, pz) not in self.vertices:
                        self.vertices[(px, pz)] = noise.pnoise2(
                            px * TERRAIN_SCALE * self.block_size + SEED,
                            pz * TERRAIN_SCALE * self.block_size + SEED,
                            octaves=6, persistence=0.5, lacunarity=1.8
                        ) * HEIGHT_SCALE
                    points.append(self.vertices[(px, pz)])

            height = (points[0] * (1 - dx) * (1 - dz) +
                      points[1] * dx * (1 - dz) +
                      points[2] * (1 - dx) * dz +
                      points[3] * dx * dz)

        self.erosion_cache[cache_key] = height
        return height

    def get_slope_angle(self, x, z):
        dx = self.get_height(x + 0.01, z) - self.get_height(x - 0.01, z)
        dz = self.get_height(x, z + 0.01) - self.get_height(x, z - 0.01)
        return degrees(atan2(sqrt(dx ** 2 + dz ** 2), 0.02))

    def generate_area(self, center_x, center_z):
        new_area = set()
        radius = int(LOAD_RADIUS / self.block_size)

        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                x = int(center_x / self.block_size) + dx
                z = int(center_z / self.block_size) + dz

                # Ensure height value is generated for this point
                if (x, z) not in self.vertices:
                    self.vertices[(x, z)] = noise.pnoise2(
                        x * TERRAIN_SCALE * self.block_size + SEED,
                        z * TERRAIN_SCALE * self.block_size + SEED,
                        octaves=6, persistence=0.5, lacunarity=1.8
                    ) * HEIGHT_SCALE

                new_area.add((x, z))

        self.generated_area = new_area
        return len(new_area)

    def get_terrain_type(self, x, z):
        """Determine the type of terrain at given coordinates"""
        x_adj = x / self.block_size
        z_adj = z / self.block_size

        # Base terrain type based on large-scale noise
        terrain_type_val = noise.pnoise2(
            x_adj * TERRAIN_SCALE * 0.1 + SEED * 2,
            z_adj * TERRAIN_SCALE * 0.1 + SEED * 2,
            octaves=1
        )

        # Add medium-scale variation
        variation = noise.pnoise2(
            x_adj * TERRAIN_SCALE * 0.5 + SEED * 3,
            z_adj * TERRAIN_SCALE * 0.5 + SEED * 3,
            octaves=2
        )

        # Add small-scale features
        detail = noise.pnoise2(
            x_adj * TERRAIN_SCALE * 2 + SEED * 4,
            z_adj * TERRAIN_SCALE * 2 + SEED * 4,
            octaves=3
        )

        # Combine factors to determine terrain type
        terrain_score = (terrain_type_val * 0.6) + (variation * 0.3) + (detail * 0.1)

        # Normalize to 0-1 range
        normalized_score = (terrain_score + 1) / 2

        # Assign terrain types based on score
        if normalized_score < 0.15:
            return BASIN
        elif normalized_score < 0.3:
            return PLAINS
        elif normalized_score < 0.45:
            return HILLS
        elif normalized_score < 0.6:
            return VALLEY
        elif normalized_score < 0.75:
            return PLATEAU
        elif normalized_score < 0.9:
            return MOUNTAINS
        else:
            return CANYON


class Player:
    def __init__(self, terrain):
        self.terrain = terrain
        self.pos = [0.0, 0.0, 0.0]
        self.pos[1] = self.terrain.get_height(0, 0) + PLAYER_HEIGHT
        self.vel = [0.0, 0.0, 0.0]
        self.yaw = 0.0
        self.pitch = 0.0
        self.on_ground = True
        self.jump_cooldown = 0.0
        self.third_person = False
        self.camera_distance = 5.0
        self.last_collision = "None"
        self.current_terrain_type = PLAINS
        self.mode = NORMAL_MODE  # Start in normal mode
        self.lift_force = BASE_LIFT
        self.crouching = False
        self.crouch_height = PLAYER_HEIGHT * 0.65
        self.normal_height = PLAYER_HEIGHT
        self.free_flight = False
        self.flight_timer = 0.0
        self.flight_cooldown = 0.5  # Cooldown between flight mode changes
        self.max_lift_active = False
        self.flight_direction = [0.0, 0.0, 0.0]  # For free flight direction

    def can_step_up(self, dx, dz):
        """Check if player can step up a small height difference"""
        if abs(dx) < 0.001 and abs(dz) < 0.001:
            return False

        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        # Can step up small height differences
        return 0 < height_diff <= STEP_HEIGHT

    def can_walk_over(self, dx, dz):
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        if height_diff < 0:
            return True

        slope = self.terrain.get_slope_angle(self.pos[0] + dx, self.pos[2] + dz)
        return slope <= MAX_CLIMB_ANGLE or abs(height_diff) <= STEP_HEIGHT

    def can_jump_over(self, dx, dz):
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height
        return abs(height_diff) < MAX_JUMP_HEIGHT

    def check_movement(self, dx, dz):
        if self.can_walk_over(dx, dz):
            self.last_collision = "Walkable slope"
            return True

        if self.can_step_up(dx, dz):
            self.last_collision = "Stepped up"
            self.pos[1] += self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz) - self.terrain.get_height(
                self.pos[0], self.pos[2])
            return True

        if self.can_jump_over(dx, dz) and not self.on_ground:
            self.last_collision = "Jumpable obstacle"
            return True

        slope_angle = self.terrain.get_slope_angle(self.pos[0] + dx, self.pos[2] + dz)
        self.last_collision = f"Blocked by slope {slope_angle:.1f}°"
        return False

    def toggle_flight_mode(self):
        if self.flight_timer > 0:
            return

        if self.mode == NORMAL_MODE:
            # Enter flight mode
            self.mode = FLIGHT_MODE
            self.free_flight = False
            self.lift_force = BASE_LIFT
            self.max_lift_active = False
            self.flight_timer = self.flight_cooldown
        elif self.mode == FLIGHT_MODE:
            # Exit flight mode
            self.mode = NORMAL_MODE
            self.lift_force = BASE_LIFT
            self.vel[1] = 0  # Reset vertical velocity
            self.flight_timer = self.flight_cooldown
        elif self.mode == FREE_FLIGHT_MODE:
            # Exit free flight mode
            self.mode = NORMAL_MODE
            self.lift_force = BASE_LIFT
            self.vel[1] = 0
            self.flight_timer = self.flight_cooldown

    def toggle_free_flight(self):
        if self.flight_timer > 0:
            return

        if self.mode == FREE_FLIGHT_MODE:
            # Exit free flight mode
            self.mode = FLIGHT_MODE
            self.flight_timer = self.flight_cooldown
        else:
            # Enter free flight mode
            self.mode = FREE_FLIGHT_MODE
            self.free_flight = True
            self.flight_timer = self.flight_cooldown

    def reset_flight(self):
        self.mode = NORMAL_MODE
        self.lift_force = BASE_LIFT
        self.free_flight = False
        self.vel[1] = 0
        self.max_lift_active = False

    def increase_lift(self):
        self.lift_force = min(MAX_LIFT, self.lift_force + LIFT_INCREMENT)

    def decrease_lift(self):
        self.lift_force = max(0, self.lift_force - LIFT_INCREMENT)

    def set_hover_lift(self):
        self.lift_force = HOVER_LIFT

    def toggle_max_lift(self):
        if self.max_lift_active:
            self.lift_force = BASE_LIFT
        else:
            self.lift_force = MAX_LIFT
        self.max_lift_active = not self.max_lift_active

    def toggle_crouch(self, state):
        self.crouching = state
        if self.crouching:
            # Adjust height when crouching
            terrain_height = self.terrain.get_height(self.pos[0], self.pos[2])
            self.pos[1] = terrain_height + self.crouch_height
        else:
            # Return to normal height
            terrain_height = self.terrain.get_height(self.pos[0], self.pos[2])
            self.pos[1] = terrain_height + self.normal_height

    def update_movement(self, dt, keys, mouse_rel):
        # Update flight timer
        if self.flight_timer > 0:
            self.flight_timer -= dt

        # Handle mouse look
        self.yaw += mouse_rel[0] * MOUSE_SENSITIVITY
        self.pitch = max(-89, min(89, self.pitch - mouse_rel[1] * MOUSE_SENSITIVITY))

        # Handle flight mode controls
        if keys[K_TAB] and keys[K_LCTRL]:
            self.toggle_free_flight()
        elif keys[K_TAB] and keys[K_SPACE]:
            self.toggle_max_lift()
        elif keys[K_TAB]:
            self.toggle_flight_mode()

        if keys[K_F1]:
            self.reset_flight()

        if keys[K_LALT]:
            self.increase_lift()

        if keys[K_LCTRL] and not keys[K_TAB]:
            self.set_hover_lift()

        # Handle movement based on current mode
        if self.mode == NORMAL_MODE:
            self.update_normal_movement(dt, keys)
        elif self.mode == FLIGHT_MODE:
            self.update_flight_movement(dt, keys)
        elif self.mode == FREE_FLIGHT_MODE:
            self.update_free_flight_movement(dt, keys)

        # Update terrain type
        self.current_terrain_type = self.terrain.get_terrain_type(self.pos[0], self.pos[2])

    def update_normal_movement(self, dt, keys):
        move_dir = [0.0, 0.0]
        yaw_rad = radians(self.yaw)

        if keys[K_w]: move_dir[0] += cos(yaw_rad); move_dir[1] += sin(yaw_rad)
        if keys[K_s]: move_dir[0] -= cos(yaw_rad); move_dir[1] -= sin(yaw_rad)
        if keys[K_a]: move_dir[0] += sin(yaw_rad); move_dir[1] -= cos(yaw_rad)
        if keys[K_d]: move_dir[0] -= sin(yaw_rad); move_dir[1] += cos(yaw_rad)

        if (length := sqrt(move_dir[0] ** 2 + move_dir[1] ** 2)) > 0:
            move_dir = [move_dir[0] / length * PLAYER_SPEED * dt,
                        move_dir[1] / length * PLAYER_SPEED * dt]

            if not self.check_movement(move_dir[0], move_dir[1]):
                move_dir = [0, 0]

        self.vel[1] -= GRAVITY * dt
        self.pos[0] += move_dir[0] + self.vel[0] * dt
        self.pos[2] += move_dir[1] + self.vel[2] * dt
        self.pos[1] += self.vel[1] * dt

        terrain_height = self.terrain.get_height(self.pos[0], self.pos[2])

        # Handle crouching
        self.toggle_crouch(keys[K_LSHIFT])
        current_height = self.crouch_height if self.crouching else self.normal_height

        # Check if we hit the ground
        if self.pos[1] < terrain_height + current_height:
            self.pos[1] = terrain_height + current_height
            self.vel[1] = 0.0
            self.on_ground = True

        # Jump if on ground and space pressed
        if keys[K_SPACE] and self.on_ground:
            self.vel[1] = JUMP_FORCE
            self.on_ground = False

    def update_flight_movement(self, dt, keys):
        # Horizontal movement
        move_dir = [0.0, 0.0]
        yaw_rad = radians(self.yaw)

        if keys[K_w]: move_dir[0] += cos(yaw_rad); move_dir[1] += sin(yaw_rad)
        if keys[K_s]: move_dir[0] -= cos(yaw_rad); move_dir[1] -= sin(yaw_rad)
        if keys[K_a]: move_dir[0] += sin(yaw_rad); move_dir[1] -= cos(yaw_rad)
        if keys[K_d]: move_dir[0] -= sin(yaw_rad); move_dir[1] += cos(yaw_rad)

        speed_multiplier = FLIGHT_SPEED_MULTIPLIER
        if keys[K_LSHIFT]:
            speed_multiplier *= 1.5  # Boost when holding shift

        if (length := sqrt(move_dir[0] ** 2 + move_dir[1] ** 2)) > 0:
            move_dir = [move_dir[0] / length * PLAYER_SPEED * speed_multiplier * dt,
                        move_dir[1] / length * PLAYER_SPEED * speed_multiplier * dt]

        self.pos[0] += move_dir[0]
        self.pos[2] += move_dir[1]

        # Vertical movement
        if keys[K_SPACE]:  # Ascend
            self.vel[1] = self.lift_force
        elif keys[K_LSHIFT]:  # Descend
            self.vel[1] = -self.lift_force * 0.7
        else:
            # Apply gravity but counteracted by lift
            self.vel[1] += (GRAVITY - self.lift_force) * FLIGHT_CONTROL_SENSITIVITY * dt

        self.pos[1] += self.vel[1] * dt

        # Check ground collision - but don't exit flight mode
        terrain_height = self.terrain.get_height(self.pos[0], self.pos[2])
        if self.pos[1] < terrain_height + self.normal_height:
            self.pos[1] = terrain_height + self.normal_height
            self.vel[1] = 0
            self.on_ground = True
        else:
            self.on_ground = False

    def update_free_flight_movement(self, dt, keys):
        # Calculate direction vectors
        yaw_rad = radians(self.yaw)
        pitch_rad = radians(self.pitch)

        # Forward direction
        forward = [
            cos(yaw_rad) * cos(pitch_rad),
            sin(pitch_rad),
            sin(yaw_rad) * cos(pitch_rad)
        ]

        # Right direction
        right = [
            -sin(yaw_rad),
            0,
            cos(yaw_rad)
        ]

        # Up direction
        up = [0, 1, 0]

        # Initialize movement direction
        move_dir = [0.0, 0.0, 0.0]

        # Apply movement based on keys
        if keys[K_w]:
            move_dir[0] += forward[0]
            move_dir[1] += forward[1]
            move_dir[2] += forward[2]
        if keys[K_s]:
            move_dir[0] -= forward[0]
            move_dir[1] -= forward[1]
            move_dir[2] -= forward[2]
        if keys[K_a]:
            move_dir[0] += right[0]
            move_dir[1] += right[1]
            move_dir[2] += right[2]
        if keys[K_d]:
            move_dir[0] -= right[0]
            move_dir[1] -= right[1]
            move_dir[2] -= right[2]
        if keys[K_SPACE]:  # Ascend
            move_dir[0] += up[0]
            move_dir[1] += up[1]
            move_dir[2] += up[2]
        if keys[K_LSHIFT]:  # Descend
            move_dir[0] -= up[0]
            move_dir[1] -= up[1]
            move_dir[2] -= up[2]

        # Normalize direction vector if needed
        length = sqrt(move_dir[0]**2 + move_dir[1]**2 + move_dir[2]**2)
        if length > 0:
            move_dir = [d / length for d in move_dir]

        # Apply movement with speed multiplier
        speed = PLAYER_SPEED * FLIGHT_SPEED_MULTIPLIER * 2.0
        self.pos[0] += move_dir[0] * speed * dt
        self.pos[1] += move_dir[1] * speed * dt
        self.pos[2] += move_dir[2] * speed * dt

        # No ground collision in free flight
        self.on_ground = False


def update_lighting(time):
    sun_angle = (time * 2 * pi / DAY_LENGTH) - pi / 2
    sun_pos = (1000 * cos(sun_angle), 1000 * sin(sun_angle), 0.0, 1.0)
    intensity = max(0.2, sin(sun_angle + pi / 2))

    # Change light color based on time of day
    if intensity < 0.3:  # Dawn/dusk
        light_color = (intensity, intensity * 0.7, intensity * 0.5, 1.0)
    else:
        light_color = (intensity, intensity * 0.9, intensity * 0.8, 1.0)

    glLightfv(GL_LIGHT0, GL_POSITION, sun_pos)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_color)
    glClearColor(0.53 - 0.3 * (1 - intensity), 0.81 - 0.3 * (1 - intensity), 0.98 - 0.3 * (1 - intensity), 1.0)


def render_terrain(terrain):
    # Render terrain with proper vertex ordering to fix transparency issues
    glBegin(GL_QUADS)
    for (x, z) in terrain.generated_area:
        x_pos = x * terrain.block_size
        z_pos = z * terrain.block_size
        bs = terrain.block_size

        try:
            y00 = terrain.vertices[(x, z)]
            y10 = terrain.vertices[(x + 1, z)]
            y01 = terrain.vertices[(x, z + 1)]
            y11 = terrain.vertices[(x + 1, z + 1)]
        except KeyError:
            continue

        # Set color based on height
        avg_height = (y00 + y10 + y01 + y11) / 4.0
        if avg_height > 8.0:
            glColor3f(0.7, 0.7, 0.7)  # Gray - Mountains
        elif avg_height > 5.0:
            glColor3f(0.5, 0.5, 0.3)  # Brown - Hills
        elif avg_height > 2.0:
            glColor3f(0.4, 0.6, 0.3)  # Green - Plains
        elif avg_height > 0.0:
            glColor3f(0.9, 0.8, 0.6)  # Sand - Beach
        else:
            glColor3f(0.3, 0.3, 0.8)  # Blue - Water

        # Calculate normal
        dx = y10 - y00
        dz = y01 - y00
        normal = (-dx, 2.0, -dz)
        length = sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        if length > 0:
            normal = (normal[0]/length, normal[1]/length, normal[2]/length)

        glNormal3fv(normal)

        # Render quad with consistent vertex ordering to fix transparency
        glVertex3f(x_pos, y00, z_pos)
        glVertex3f(x_pos + bs, y10, z_pos)
        glVertex3f(x_pos + bs, y11, z_pos + bs)
        glVertex3f(x_pos, y01, z_pos + bs)
    glEnd()


def render_sky(time):
    intensity = max(0.2, sin((time * 2 * pi / DAY_LENGTH)))
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)

    # Sky gradient with time-of-day effect
    time_factor = time % DAY_LENGTH / DAY_LENGTH

    if time_factor < 0.25:  # Dawn
        top_color = (0.9, 0.5, 0.2)
        bottom_color = (0.7, 0.8, 1.0)
    elif time_factor < 0.5:  # Day
        top_color = (0.53, 0.81, 0.98)
        bottom_color = (0.8, 0.9, 1.0)
    elif time_factor < 0.75:  # Dusk
        top_color = (0.2, 0.1, 0.4)
        bottom_color = (0.9, 0.5, 0.2)
    else:  # Night
        top_color = (0.05, 0.05, 0.1)
        bottom_color = (0.1, 0.1, 0.3)

    # Apply intensity
    top_color = (top_color[0] * intensity, top_color[1] * intensity, top_color[2] * intensity)
    bottom_color = (bottom_color[0] * intensity, bottom_color[1] * intensity, bottom_color[2] * intensity)

    glBegin(GL_QUADS)
    glColor3fv(bottom_color)
    glVertex3f(-1, -1, -0.5)
    glVertex3f(1, -1, -0.5)
    glColor3fv(top_color)
    glVertex3f(1, 1, -0.5)
    glVertex3f(-1, 1, -0.5)
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


class Tsin:
    """3D Terrain Exploration Engine with Enhanced Flight Controls"""

    def __init__(self, screen_size=SCREEN_SIZE):
        self.screen_size = screen_size
        self.screen = None
        self.terrain = None
        self.player = None
        self.debug_info = None
        self.ui = None
        self.clock = pygame.time.Clock()
        self.start_time = 0
        self.running = False
        self.vr_controls = {
            'move_forward': False,
            'move_backward': False,
            'move_left': False,
            'move_right': False,
            'jump': False,
            'crouch': False,
            'fly_up': False,
            'fly_down': False,
            'look': (0, 0)
        }

    def init(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.screen_size, DOUBLEBUF | OPENGL | RESIZABLE)
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        init_gl(self.screen_size)

        # Initialize game objects AFTER Pygame is initialized
        self.terrain = Terrain()
        self.player = Player(self.terrain)
        self.debug_info = DebugInfo(self.screen_size)
        self.ui = UI(self.screen_size)

        # Initialize fonts AFTER Pygame is initialized
        self.debug_info.init_fonts()
        self.ui.init_fonts()

        self.start_time = pygame.time.get_ticks()
        self.running = True

    def shutdown(self):
        pygame.quit()
        self.running = False

    def handle_vr_command(self, command, value=None):
        """Handle VR commands for player control"""
        if command == 'move_forward':
            self.vr_controls['move_forward'] = value
        elif command == 'move_backward':
            self.vr_controls['move_backward'] = value
        elif command == 'move_left':
            self.vr_controls['move_left'] = value
        elif command == 'move_right':
            self.vr_controls['move_right'] = value
        elif command == 'jump':
            self.vr_controls['jump'] = value
        elif command == 'crouch':
            self.vr_controls['crouch'] = value
        elif command == 'fly_up':
            self.vr_controls['fly_up'] = value
        elif command == 'fly_down':
            self.vr_controls['fly_down'] = value
        elif command == 'look':
            self.vr_controls['look'] = value

    def simulate_key_press(self, key, pressed=True):
        """Simulate keyboard input for external control"""
        # This method is for external control systems like VR
        # Actual implementation would integrate with the update loop
        pass

    def get_player_state(self):
        """Get current player state for external systems"""
        return {
            'position': self.player.pos,
            'rotation': (self.player.yaw, self.player.pitch),
            'velocity': self.player.vel,
            'mode': self.player.mode,
            'lift': self.player.lift_force,
            'on_ground': self.player.on_ground,
            'terrain_type': self.player.current_terrain_type,
            'max_lift_active': self.player.max_lift_active
        }

    def set_player_state(self, position=None, rotation=None, mode=None, lift=None):
        """Set player state from external systems"""
        if position:
            self.player.pos = position
        if rotation:
            self.player.yaw, self.player.pitch = rotation
        if mode is not None:
            self.player.mode = mode
        if lift is not None:
            self.player.lift_force = lift

    def update(self):
        if not self.running:
            return False

        dt = self.clock.tick(60) / 1000.0
        current_time = (pygame.time.get_ticks() - self.start_time) / 1000.0

        # Process events
        mouse_rel = (0, 0)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if self.ui.state == "game":
                        self.ui.state = "pause"
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    elif self.ui.state == "pause":
                        self.ui.state = "game"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif self.ui.state == "title":
                        self.running = False

                elif event.key == K_F3:
                    self.debug_info.toggle()

                elif event.key == K_F12:
                    self.debug_info.toggle_full()

                elif event.key == K_F5:
                    self.player.third_person = not self.player.third_person

                elif event.key == K_F6:
                    global SMOOTH_TERRAIN
                    SMOOTH_TERRAIN = not SMOOTH_TERRAIN
                    self.terrain.smooth = SMOOTH_TERRAIN
                    self.terrain.vertices = {}

                elif event.key == K_EQUALS or event.key == K_PLUS:
                    global TERRAIN_DETAIL
                    TERRAIN_DETAIL = min(2.0, TERRAIN_DETAIL + 0.1)
                    self.terrain.vertices = {}

                elif event.key == K_MINUS:
                    TERRAIN_DETAIL = max(0.1, TERRAIN_DETAIL - 0.1)
                    self.terrain.vertices = {}

                elif event.key == K_F7:
                    global FOG_DISTANCE
                    FOG_DISTANCE = max(50, min(500, FOG_DISTANCE + 50))
                    glFogf(GL_FOG_START, FOG_DISTANCE * 0.6)
                    glFogf(GL_FOG_END, FOG_DISTANCE)
                    self.debug_info.fog_distance = FOG_DISTANCE

                elif event.key == K_F8:
                    FOG_DISTANCE = max(50, min(500, FOG_DISTANCE - 50))
                    glFogf(GL_FOG_START, FOG_DISTANCE * 0.6)
                    glFogf(GL_FOG_END, FOG_DISTANCE)
                    self.debug_info.fog_distance = FOG_DISTANCE

                elif event.key == K_F9:
                    global FOG_ENABLED
                    FOG_ENABLED = not FOG_ENABLED
                    if FOG_ENABLED:
                        glEnable(GL_FOG)
                    else:
                        glDisable(GL_FOG)

            elif event.type == VIDEORESIZE:
                self.screen_size = (event.w, event.h)
                glViewport(0, 0, event.w, event.h)
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                gluPerspective(60, event.w / event.h, 0.1, 1000)
                glMatrixMode(GL_MODELVIEW)
                self.ui.set_screen_size((event.w, event.h))
                self.debug_info.set_screen_size((event.w, event.h))

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self.ui.state in ["title", "pause"]:
                    action = self.ui.check_click(event.pos)
                    if action == "start":
                        self.ui.state = "game"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif action == "exit":
                        self.running = False
                    elif action == "continue":
                        self.ui.state = "game"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif action == "menu":
                        self.ui.state = "title"
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)

            elif event.type == MOUSEMOTION and self.ui.state == "game":
                mouse_rel = event.rel

        # Update game state
        if self.ui.state == "game":
            # Combine VR controls with keyboard input
            vr_keys = {
                K_w: self.vr_controls['move_forward'],
                K_s: self.vr_controls['move_backward'],
                K_a: self.vr_controls['move_left'],
                K_d: self.vr_controls['move_right'],
                K_SPACE: self.vr_controls['jump'] or self.vr_controls['fly_up'],
                K_LSHIFT: self.vr_controls['crouch'] or self.vr_controls['fly_down']
            }

            # Override keyboard with VR controls if active
            for key, value in vr_keys.items():
                if value:
                    keys = list(keys)
                    keys[key] = True
                    keys = tuple(keys)

            # Combine VR look with mouse look
            vr_look = self.vr_controls['look']
            mouse_rel = (mouse_rel[0] + vr_look[0], mouse_rel[1] + vr_look[1])

            # Update player
            self.player.update_movement(dt, keys, mouse_rel)

        # Update terrain
        chunk_count = self.terrain.generate_area(self.player.pos[0], self.player.pos[2])
        current_slope = self.terrain.get_slope_angle(self.player.pos[0], self.player.pos[2])

        # Get terrain type name for debug display
        terrain_type_names = {
            PLAINS: "Plains",
            HILLS: "Hills",
            MOUNTAINS: "Mountains",
            PLATEAU: "Plateau",
            BASIN: "Basin",
            CANYON: "Canyon",
            VALLEY: "Valley"
        }
        terrain_type_name = terrain_type_names.get(self.player.current_terrain_type, "Unknown")

        # Get player mode name
        mode_names = {
            NORMAL_MODE: "Normal",
            FLIGHT_MODE: "Flight",
            FREE_FLIGHT_MODE: "Free Flight"
        }
        mode_name = mode_names.get(self.player.mode, "Unknown")

        self.debug_info.update(
            int(self.clock.get_fps()),
            self.player.pos,
            (self.player.yaw, self.player.pitch),
            chunk_count,
            current_time % DAY_LENGTH,
            current_slope,
            self.player.third_person,
            self.player.vel,
            self.player.on_ground,
            self.player.last_collision,
            terrain_type_name,
            mode_name,
            self.player.lift_force
        )
        update_lighting(current_time % DAY_LENGTH)

        # Render
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Render game world if not in title screen
        if self.ui.state != "title":
            yaw_rad = radians(self.player.yaw)
            pitch_rad = radians(self.player.pitch)
            look_dir = (
                cos(yaw_rad) * cos(pitch_rad),
                sin(pitch_rad),
                sin(yaw_rad) * cos(pitch_rad)
            )

            if self.player.third_person:
                camera_offset = (
                    -look_dir[0] * self.player.camera_distance,
                    -look_dir[1] * self.player.camera_distance + 2.0,
                    -look_dir[2] * self.player.camera_distance
                )
                eye_pos = (
                    self.player.pos[0] + camera_offset[0],
                    self.player.pos[1] + camera_offset[1],
                    self.player.pos[2] + camera_offset[2]
                )
                gluLookAt(
                    *eye_pos,
                    self.player.pos[0] + look_dir[0],
                    self.player.pos[1] + self.player.normal_height + look_dir[1],
                    self.player.pos[2] + look_dir[2],
                    0, 1, 0
                )
            else:
                gluLookAt(
                    self.player.pos[0],
                    self.player.pos[1] + self.player.normal_height,
                    self.player.pos[2],
                    self.player.pos[0] + look_dir[0],
                    self.player.pos[1] + self.player.normal_height + look_dir[1],
                    self.player.pos[2] + look_dir[2],
                    0, 1, 0
                )

            render_sky(current_time % DAY_LENGTH)
            render_terrain(self.terrain)

        # Render UI
        if self.ui.state == "title":
            self.ui.render_title_screen()
        elif self.ui.state == "pause":
            self.ui.render_pause_menu()

        self.debug_info.render()
        pygame.display.flip()

        return True


# Example usage
if __name__ == "__main__":
    tsin = Tsin()
    tsin.init()

    while tsin.update():
        pass

    tsin.shutdown()