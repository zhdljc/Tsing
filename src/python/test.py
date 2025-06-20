"""
Known issue: There are texture (or display) errors in low-lying terrain, visible from below but not from above, limited to low areas, not fixed for now.
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import noise
import random
from math import sin, cos, radians, sqrt, pi, atan2, degrees, exp, log
import numpy as np
from collections import defaultdict

# System configuration
SCREEN_SIZE = (1280, 720)
TERRAIN_SCALE = 0.05
HEIGHT_SCALE = 25.0  # Increased for more dramatic terrain
MOUSE_SENSITIVITY = 0.15
PLAYER_SPEED = 4.5
GRAVITY = 9.8
JUMP_FORCE = 6.0
PLAYER_HEIGHT = 1.8
LOAD_RADIUS = 30  # Increased for better LOD
MAX_CLIMB_ANGLE = 45
MAX_JUMP_HEIGHT = 1.2
SEED = random.randint(0, 10000)
DAY_LENGTH = 120.0
TERRAIN_BLOCK_SIZE = 1.0
SMOOTH_TERRAIN = True  # Default to smooth
FOG_ENABLED = True
FOG_DISTANCE = 150.0  # Increased for larger view distance
STEP_HEIGHT = 0.5
TERRAIN_DETAIL = 1.0  # Control terrain roughness
TERRAIN_DIVERSITY = 1.0  # Control terrain type diversity
MAX_TERRAIN_HEIGHT = 50.0  # Maximum height for mountains
MIN_TERRAIN_HEIGHT = -20.0  # Minimum depth for basins

# Terrain type constants
PLAINS = 0
HILLS = 1
MOUNTAINS = 2
PLATEAU = 3
BASIN = 4
CANYON = 5
VALLEY = 6

class UI:
    def __init__(self):
        self.font = pygame.font.SysFont('Arial', 32)
        self.buttons = []
        self.state = "title"
        self.create_ui_elements()

    def create_ui_elements(self):
        # Title screen buttons
        self.title_buttons = [
            {"rect": pygame.Rect(SCREEN_SIZE[0] // 2 - 100, SCREEN_SIZE[1] // 2, 200, 50), "text": "Start Game",
             "action": "start"},
            {"rect": pygame.Rect(SCREEN_SIZE[0] // 2 - 100, SCREEN_SIZE[1] // 2 + 70, 200, 50), "text": "Exit",
             "action": "exit"}
        ]

        # Pause menu buttons
        self.pause_buttons = [
            {"rect": pygame.Rect(SCREEN_SIZE[0] // 2 - 100, SCREEN_SIZE[1] // 2, 200, 50), "text": "Continue",
             "action": "continue"},
            {"rect": pygame.Rect(SCREEN_SIZE[0] // 2 - 100, SCREEN_SIZE[1] // 2 + 70, 200, 50), "text": "Main Menu",
             "action": "menu"}
        ]

    def render_text(self, text, x, y, color=(255, 255, 255), size=32):
        font = pygame.font.SysFont('Arial', size)
        text_surface = font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)

        glWindowPos2i(x, SCREEN_SIZE[1] - y - text_surface.get_height())
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                     GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    def render_button(self, button):
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
        self.render_text("Terrain Explorer", SCREEN_SIZE[0] // 2 - 150, 150, (255, 255, 255), 48)

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
        glVertex2i(SCREEN_SIZE[0], 0)
        glVertex2i(SCREEN_SIZE[0], SCREEN_SIZE[1])
        glVertex3i(0, SCREEN_SIZE[1], 0)
        glEnd()

        # Title
        self.render_text("Paused", SCREEN_SIZE[0] // 2 - 70, 150, (255, 255, 255), 48)

        # Buttons
        for button in self.pause_buttons:
            self.render_button(button)

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)


class DebugInfo:
    def __init__(self):
        self.show_info = False
        self.full_info = False
        self.font = pygame.font.SysFont('Arial', 20)
        self.small_font = pygame.font.SysFont('Arial', 16)
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

    def toggle(self):
        self.show_info = not self.show_info

    def toggle_full(self):
        self.full_info = not self.full_info

    def update(self, fps, pos, rot, chunks, time, slope, third_person, vel, ground, collision, terrain_type):
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
                    "WASD - Move, SPACE - Jump",
                    "F3 - Toggle Debug Info",
                    "F12 - Toggle Full Debug",
                    "F5 - Toggle Camera",
                    "F6 - Toggle Smooth Terrain",
                    "F7/F8 - Adjust Fog Distance",
                    "F9 - Toggle Fog",
                    "+/- - Adjust Terrain Detail"
                ])

            debug_surface = pygame.Surface((SCREEN_SIZE[0], SCREEN_SIZE[1]), pygame.SRCALPHA)
            debug_surface.fill((0, 0, 0, 0))

            y_offset = 10
            for i, text in enumerate(basic_texts):
                font = self.small_font if (self.full_info and i >= 8) else self.font
                text_surface = font.render(text, True, (255, 255, 255, 255))
                debug_surface.blit(text_surface, (10, y_offset))
                y_offset += 20 if (self.full_info and i >= 8) else 25

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            texture_data = pygame.image.tostring(debug_surface, "RGBA", True)
            glWindowPos2i(0, 0)
            glDrawPixels(SCREEN_SIZE[0], SCREEN_SIZE[1], GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

            glEnable(GL_DEPTH_TEST)
            glDisable(GL_BLEND)

        except Exception as e:
            print(f"Debug render error: {e}")


def init_gl():
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glShadeModel(GL_SMOOTH)
    glClearDepth(1.0)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)

    if FOG_ENABLED:
        setup_fog()


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
        self.erosion_cache = {}  # 添加侵蚀结果缓存

    def get_height(self, x, z):
        x_adj = x / self.block_size
        z_adj = z / self.block_size

        # 检查缓存
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

        # 缓存结果
        self.erosion_cache[cache_key] = height
        return height

    def get_slope_angle(self, x, z):
        # 使用更小的偏移量以避免递归问题
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

                # 确保该点的高度值已生成
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

    def can_step_up(self, dx, dz):
        """Check if player can step up a small height difference"""
        # 添加边界检查，防止无限递归
        if abs(dx) < 0.001 and abs(dz) < 0.001:
            return False

        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        # 可以踏上小高度差
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

    def update_movement(self, dt, keys):
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
        self.current_terrain_type = self.terrain.get_terrain_type(self.pos[0], self.pos[2])

        # Check if we hit the ground
        if self.pos[1] < terrain_height + PLAYER_HEIGHT:
            self.pos[1] = terrain_height + PLAYER_HEIGHT
            self.vel[1] = 0.0
            self.on_ground = True

        # Jump if on ground and space pressed
        if keys[K_SPACE] and self.on_ground:
            self.vel[1] = JUMP_FORCE
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

        # 根据高度设置颜色 - 简单的高度梯度
        avg_height = (y00 + y10 + y01 + y11) / 4.0
        if avg_height > 8.0:
            glColor3f(0.7, 0.7, 0.7)  # 灰色 - 高山
        elif avg_height > 5.0:
            glColor3f(0.5, 0.5, 0.3)  # 棕色 - 丘陵
        elif avg_height > 2.0:
            glColor3f(0.4, 0.6, 0.3)  # 绿色 - 平原
        elif avg_height > 0.0:
            glColor3f(0.9, 0.8, 0.6)  # 沙色 - 沙滩
        else:
            glColor3f(0.3, 0.3, 0.8)  # 蓝色 - 水域

        # 计算法线
        dx = y10 - y00
        dz = y01 - y00
        normal = (-dx, 2.0, -dz)
        length = sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        if length > 0:
            normal = (normal[0]/length, normal[1]/length, normal[2]/length)

        glNormal3fv(normal)
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


def main():
    pygame.init()
    global SCREEN_SIZE, TERRAIN_BLOCK_SIZE, SMOOTH_TERRAIN, FOG_DISTANCE, FOG_ENABLED, TERRAIN_DETAIL, TERRAIN_DIVERSITY

    screen = pygame.display.set_mode(SCREEN_SIZE, DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    init_gl()

    terrain = Terrain()
    player = Player(terrain)
    debug_info = DebugInfo()
    ui = UI()
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()

    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, SCREEN_SIZE[0] / SCREEN_SIZE[1], 0.1, 1000)
    glMatrixMode(GL_MODELVIEW)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        current_time = (pygame.time.get_ticks() - start_time) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if ui.state == "game":
                        ui.state = "pause"
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    elif ui.state == "pause":
                        ui.state = "game"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif ui.state == "title":
                        running = False

                elif event.key == K_F3:
                    debug_info.toggle()

                elif event.key == K_F12:
                    debug_info.toggle_full()

                elif event.key == K_F5:
                    player.third_person = not player.third_person

                elif event.key == K_F6:
                    SMOOTH_TERRAIN = not SMOOTH_TERRAIN
                    terrain.smooth = SMOOTH_TERRAIN
                    terrain.vertices = {}

                elif event.key == K_EQUALS or event.key == K_PLUS:
                    TERRAIN_DETAIL = min(2.0, TERRAIN_DETAIL + 0.1)
                    terrain.vertices = {}

                elif event.key == K_MINUS:
                    TERRAIN_DETAIL = max(0.1, TERRAIN_DETAIL - 0.1)
                    terrain.vertices = {}

                elif event.key == K_F7:
                    FOG_DISTANCE = max(50, min(500, FOG_DISTANCE + 50))
                    glFogf(GL_FOG_START, FOG_DISTANCE * 0.6)
                    glFogf(GL_FOG_END, FOG_DISTANCE)
                    debug_info.fog_distance = FOG_DISTANCE

                elif event.key == K_F8:
                    FOG_DISTANCE = max(50, min(500, FOG_DISTANCE - 50))
                    glFogf(GL_FOG_START, FOG_DISTANCE * 0.6)
                    glFogf(GL_FOG_END, FOG_DISTANCE)
                    debug_info.fog_distance = FOG_DISTANCE

                elif event.key == K_F9:
                    FOG_ENABLED = not FOG_ENABLED
                    if FOG_ENABLED:
                        glEnable(GL_FOG)
                    else:
                        glDisable(GL_FOG)

            elif event.type == VIDEORESIZE:
                SCREEN_SIZE = (event.w, event.h)
                glViewport(0, 0, event.w, event.h)
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                gluPerspective(60, event.w / event.h, 0.1, 1000)
                glMatrixMode(GL_MODELVIEW)

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if ui.state in ["title", "pause"]:
                    action = ui.check_click(event.pos)
                    if action == "start":
                        ui.state = "game"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif action == "exit":
                        running = False
                    elif action == "continue":
                        ui.state = "game"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif action == "menu":
                        ui.state = "title"
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)

        # Update game state
        if ui.state == "game":
            mx, my = pygame.mouse.get_rel()
            player.yaw += mx * MOUSE_SENSITIVITY
            player.pitch = max(-89, min(89, player.pitch - my * MOUSE_SENSITIVITY))

            keys = pygame.key.get_pressed()
            player.update_movement(dt, keys)

        # Always update these for debug info
        chunk_count = terrain.generate_area(player.pos[0], player.pos[2])
        current_slope = terrain.get_slope_angle(player.pos[0], player.pos[2])

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
        terrain_type_name = terrain_type_names.get(player.current_terrain_type, "Unknown")

        debug_info.update(
            int(clock.get_fps()),
            player.pos,
            (player.yaw, player.pitch),
            chunk_count,
            current_time % DAY_LENGTH,
            current_slope,
            player.third_person,
            player.vel,
            player.on_ground,
            player.last_collision,
            terrain_type_name
        )
        update_lighting(current_time % DAY_LENGTH)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Render game world if not in title screen
        if ui.state != "title":
            yaw_rad = radians(player.yaw)
            pitch_rad = radians(player.pitch)
            look_dir = (
                cos(yaw_rad) * cos(pitch_rad),
                sin(pitch_rad),
                sin(yaw_rad) * cos(pitch_rad)
            )

            if player.third_person:
                camera_offset = (
                    -look_dir[0] * player.camera_distance,
                    -look_dir[1] * player.camera_distance + 2.0,
                    -look_dir[2] * player.camera_distance
                )
                eye_pos = (
                    player.pos[0] + camera_offset[0],
                    player.pos[1] + camera_offset[1],
                    player.pos[2] + camera_offset[2]
                )
                gluLookAt(
                    *eye_pos,
                    player.pos[0] + look_dir[0],
                    player.pos[1] + PLAYER_HEIGHT + look_dir[1],
                    player.pos[2] + look_dir[2],
                    0, 1, 0
                )
            else:
                gluLookAt(
                    player.pos[0], player.pos[1] + PLAYER_HEIGHT, player.pos[2],
                                   player.pos[0] + look_dir[0],
                                   player.pos[1] + PLAYER_HEIGHT + look_dir[1],
                                   player.pos[2] + look_dir[2],
                    0, 1, 0
                )

            render_sky(current_time % DAY_LENGTH)
            render_terrain(terrain)

        # Render UI
        if ui.state == "title":
            ui.render_title_screen()
        elif ui.state == "pause":
            ui.render_pause_menu()

        debug_info.render()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()