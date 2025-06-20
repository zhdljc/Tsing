import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import noise
import random
from math import sin, cos, radians, sqrt, pi, atan2, degrees

# System configuration
SCREEN_SIZE = (1280, 720)
TERRAIN_SCALE = 0.05
HEIGHT_SCALE = 15.0
MOUSE_SENSITIVITY = 0.15
PLAYER_SPEED = 4.5
GRAVITY = 9.8
JUMP_FORCE = 6.0
PLAYER_HEIGHT = 1.8
LOAD_RADIUS = 20
MAX_CLIMB_ANGLE = 45  # Reduced from 80 to make climbing more realistic
MAX_JUMP_HEIGHT = 1.2
SEED = random.randint(0, 10000)
DAY_LENGTH = 120.0
TERRAIN_BLOCK_SIZE = 1.0
SMOOTH_TERRAIN = False
FOG_ENABLED = True
FOG_DISTANCE = 100.0
STEP_HEIGHT = 0.5  # Maximum height player can step up without jumping


class UI:
    def __init__(self):
        self.font = pygame.font.SysFont('Arial', 32)
        self.buttons = []
        self.state = "title"  # title, game, pause
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
        self.show_info = False  # Start with debug info hidden
        self.full_info = False
        self.font = pygame.font.SysFont('Arial', 20)
        self.small_font = pygame.font.SysFont('Arial', 16)  # For developer info
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

    def toggle(self):
        self.show_info = not self.show_info

    def toggle_full(self):
        self.full_info = not self.full_info

    def update(self, fps, pos, rot, chunks, time, slope, third_person, vel, ground, collision):
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

    def render(self):
        if not self.show_info:
            return

        try:
            hours = int((self.day_time * 24) / DAY_LENGTH) % 24
            minutes = int((self.day_time * 24 * 60) / DAY_LENGTH) % 60
            seconds = int((self.day_time * 24 * 3600) / DAY_LENGTH) % 60

            # Basic info (F3 mode)
            basic_texts = [
                f"FPS: {self.fps}",
                f"Position: X={self.player_pos[0]:.1f} Y={self.player_pos[1]:.1f} Z={self.player_pos[2]:.1f}",
                f"Rotation: Yaw={self.player_rot[0]:.1f} Pitch={self.player_rot[1]:.1f}",
                f"Velocity: X={self.player_velocity[0]:.1f} Y={self.player_velocity[1]:.1f} Z={self.player_velocity[2]:.1f}",
                f"Ground: {'Yes' if self.on_ground else 'No'}",
                f"Slope: {self.slope_angle:.1f}°",
                f"Camera: {'3rd Person' if self.third_person else '1st Person'}"
            ]

            # Developer info (F12 mode)
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
                # Use smaller font for developer info
                font = self.small_font if (self.full_info and i >= 7) else self.font
                text_surface = font.render(text, True, (255, 255, 255, 255))
                debug_surface.blit(text_surface, (10, y_offset))
                y_offset += 20 if (self.full_info and i >= 7) else 25

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

    if FOG_ENABLED:
        setup_fog()


def setup_fog():
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogfv(GL_FOG_COLOR, (0.53, 0.81, 0.98, 1.0))
    glFogf(GL_FOG_START, FOG_DISTANCE * 0.7)
    glFogf(GL_FOG_END, FOG_DISTANCE)


class Terrain:
    def __init__(self):
        self.vertices = {}
        self.normals = {}
        self.generated_area = set()
        self.block_size = TERRAIN_BLOCK_SIZE
        self.smooth = SMOOTH_TERRAIN

    def get_height(self, x, z):
        x_adj = x / self.block_size
        z_adj = z / self.block_size

        if not self.smooth:
            x0, z0 = int(x_adj), int(z_adj)
            return noise.pnoise2(x0 * TERRAIN_SCALE + SEED,
                                 z0 * TERRAIN_SCALE + SEED,
                                 octaves=6, persistence=0.5, lacunarity=1.8) * HEIGHT_SCALE

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

        return (points[0] * (1 - dx) * (1 - dz) +
                points[1] * dx * (1 - dz) +
                points[2] * (1 - dx) * dz +
                points[3] * dx * dz)

    def get_slope_angle(self, x, z):
        dx = self.get_height(x + 0.1, z) - self.get_height(x - 0.1, z)
        dz = self.get_height(x, z + 0.1) - self.get_height(x, z - 0.1)
        return degrees(atan2(sqrt(dx ** 2 + dz ** 2), 0.2))

    def generate_area(self, center_x, center_z):
        new_area = set()
        radius = int(LOAD_RADIUS / self.block_size)

        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                x = int(center_x / self.block_size) + dx
                z = int(center_z / self.block_size) + dz

                if (x, z) not in self.vertices:
                    self.vertices[(x, z)] = noise.pnoise2(
                        x * TERRAIN_SCALE * self.block_size + SEED,
                        z * TERRAIN_SCALE * self.block_size + SEED,
                        octaves=6, persistence=0.5, lacunarity=1.8
                    ) * HEIGHT_SCALE

                new_area.add((x, z))

        self.generated_area = new_area
        return len(new_area)


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

    def can_step_up(self, dx, dz):
        """Check if player can step up a small height difference"""
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        # Can step up if the height difference is positive but small
        return 0 < height_diff <= STEP_HEIGHT

    def can_walk_over(self, dx, dz):
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        # Allow walking down any slope (negative height difference)
        if height_diff < 0:
            return True

        # For positive height differences, check slope angle
        slope = self.terrain.get_slope_angle(self.pos[0] + dx, self.pos[2] + dz)
        return slope <= MAX_CLIMB_ANGLE or abs(height_diff) <= STEP_HEIGHT

    def can_jump_over(self, dx, dz):
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        return abs(height_diff) < MAX_JUMP_HEIGHT

    def check_movement(self, dx, dz):
        # First try normal movement
        if self.can_walk_over(dx, dz):
            self.last_collision = "Walkable slope"
            return True

        # Then check if we can step up
        if self.can_step_up(dx, dz):
            self.last_collision = "Stepped up"
            self.pos[1] += self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz) - self.terrain.get_height(
                self.pos[0], self.pos[2])
            return True

        # Finally check if we can jump over
        if self.can_jump_over(dx, dz) and not self.on_ground:
            self.last_collision = "Jumpable obstacle"
            return True

        self.last_collision = f"Blocked by slope {self.terrain.get_slope_angle(self.pos[0] + dx, self.pos[2] + dz):.1f}°"
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
    light_color = (intensity, intensity * 0.9, intensity * 0.8, 1.0)

    glLightfv(GL_LIGHT0, GL_POSITION, sun_pos)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_color)
    glClearColor(0.53 - 0.3 * (1 - intensity), 0.81 - 0.3 * (1 - intensity), 0.98 - 0.3 * (1 - intensity), 1.0)


def render_terrain(terrain):
    glColor3f(0.4, 0.6, 0.3)
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

        dx = y10 - y00
        dz = y01 - y00
        normal = (-dx, 2.0, -dz)
        length = sqrt(normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2)
        if length > 0:
            normal = (normal[0] / length, normal[1] / length, normal[2] / length)

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

    glBegin(GL_QUADS)
    # Sky gradient
    glColor3f(0.53 * intensity, 0.81 * intensity, 0.98 * intensity)
    glVertex3f(-1, -1, -0.5)
    glVertex3f(1, -1, -0.5)
    glColor3f(0.1 * intensity, 0.1 * intensity, 0.3 * intensity)
    glVertex3f(1, 1, -0.5)
    glVertex3f(-1, 1, -0.5)
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


def main():
    pygame.init()
    global SCREEN_SIZE, TERRAIN_BLOCK_SIZE, SMOOTH_TERRAIN, FOG_DISTANCE, FOG_ENABLED

    screen = pygame.display.set_mode(SCREEN_SIZE, DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.mouse.set_visible(True)  # Start with mouse visible
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

                elif event.key == K_F12:  # Added F12 for full debug
                    debug_info.toggle_full()

                elif event.key == K_F5:
                    player.third_person = not player.third_person

                elif event.key == K_F6:
                    SMOOTH_TERRAIN = not SMOOTH_TERRAIN
                    terrain.smooth = SMOOTH_TERRAIN
                    terrain.vertices = {}

                elif event.key == K_EQUALS or event.key == K_PLUS:
                    TERRAIN_BLOCK_SIZE = min(2.0, TERRAIN_BLOCK_SIZE + 0.1)
                    terrain.block_size = TERRAIN_BLOCK_SIZE
                    terrain.vertices = {}
                    debug_info.terrain_block_size = TERRAIN_BLOCK_SIZE

                elif event.key == K_MINUS:
                    TERRAIN_BLOCK_SIZE = max(0.1, TERRAIN_BLOCK_SIZE - 0.1)
                    terrain.block_size = TERRAIN_BLOCK_SIZE
                    terrain.vertices = {}
                    debug_info.terrain_block_size = TERRAIN_BLOCK_SIZE

                elif event.key == K_F7:
                    FOG_DISTANCE = max(50, min(500, FOG_DISTANCE + 50))
                    glFogf(GL_FOG_START, FOG_DISTANCE * 0.7)
                    glFogf(GL_FOG_END, FOG_DISTANCE)
                    debug_info.fog_distance = FOG_DISTANCE

                elif event.key == K_F8:
                    FOG_DISTANCE = max(50, min(500, FOG_DISTANCE - 50))
                    glFogf(GL_FOG_START, FOG_DISTANCE * 0.7)
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
            player.last_collision
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
