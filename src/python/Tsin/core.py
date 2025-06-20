import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import noise
import random
from math import sin, cos, radians, sqrt, pi, atan2, degrees
from typing import Dict, Tuple, List, Set, Optional, Callable

class TerrainConstants:
    """Centralized configuration constants for the terrain engine"""
    def __init__(self):
        # Display settings
        self.SCREEN_SIZE = (1280, 720)
        self.FOV = 60
        self.NEAR_CLIP = 0.1
        self.FAR_CLIP = 1000

        # Terrain generation
        self.TERRAIN_SCALE = 0.05
        self.HEIGHT_SCALE = 15.0
        self.LOAD_RADIUS = 20
        self.SEED = random.randint(0, 10000)
        self.TERRAIN_BLOCK_SIZE = 1.0
        self.SMOOTH_TERRAIN = False
        self.NOISE_OCTAVES = 6
        self.NOISE_PERSISTENCE = 0.5
        self.NOISE_LACUNARITY = 1.8

        # Player physics
        self.PLAYER_SPEED = 4.5
        self.GRAVITY = 9.8
        self.JUMP_FORCE = 6.0
        self.PLAYER_HEIGHT = 1.8
        self.MAX_CLIMB_ANGLE = 45
        self.MAX_JUMP_HEIGHT = 1.2
        self.STEP_HEIGHT = 0.5
        self.MOUSE_SENSITIVITY = 0.15

        # Environment
        self.DAY_LENGTH = 120.0
        self.FOG_ENABLED = True
        self.FOG_DISTANCE = 100.0
        self.FOG_COLOR = (0.53, 0.81, 0.98, 1.0)

        # Debug
        self.DEBUG_FONT_SIZE = 20
        self.SMALL_DEBUG_FONT_SIZE = 16

class TerrainModInterface:
    """Interface for modders to extend engine functionality"""
    def __init__(self, engine):
        self.engine = engine
        self.registered_callbacks = {
            'pre_update': [],
            'post_update': [],
            'pre_render': [],
            'post_render': [],
            'input_handled': []
        }

    def register_callback(self, event_type: str, callback: Callable):
        """Register a mod callback function"""
        if event_type in self.registered_callbacks:
            self.registered_callbacks[event_type].append(callback)

    def trigger_callbacks(self, event_type: str, *args):
        """Execute all registered callbacks for an event"""
        for callback in self.registered_callbacks.get(event_type, []):
            callback(*args)

    def get_terrain_height(self, x: float, z: float) -> float:
        """Get terrain height at specified coordinates"""
        return self.engine.terrain.get_height(x, z)

    def get_player_position(self) -> Tuple[float, float, float]:
        """Get current player position"""
        return tuple(self.engine.player.pos)

    def set_player_position(self, x: float, y: float, z: float):
        """Set player position"""
        self.engine.player.pos = [x, y, z]

    def get_time_of_day(self) -> float:
        """Get current time of day (0-1)"""
        return (self.engine.current_time % self.engine.constants.DAY_LENGTH) / self.engine.constants.DAY_LENGTH

    def add_custom_texture(self, texture_id: str, texture_data):
        """Add custom texture to the engine"""
        self.engine.textures[texture_id] = texture_data

    def spawn_object(self, model_id: str, position: Tuple[float, float, float]):
        """Spawn a custom object in the world"""
        self.engine.world_objects.append({
            'model': model_id,
            'position': position,
            'rotation': (0, 0, 0),
            'scale': (1, 1, 1)
        })

class TerrainDebugInfo:
    """Debug information display system"""
    def __init__(self, constants: TerrainConstants):
        self.constants = constants
        self.show_info = False
        self.full_info = False
        self.font = pygame.font.SysFont('Arial', constants.DEBUG_FONT_SIZE)
        self.small_font = pygame.font.SysFont('Arial', constants.SMALL_DEBUG_FONT_SIZE)
        self.fps = 0
        self.player_pos = (0, 0, 0)
        self.player_rot = (0, 0)
        self.rendered_chunks = 0
        self.day_time = 0.0
        self.slope_angle = 0.0
        self.player_velocity = (0, 0, 0)
        self.on_ground = False
        self.collision_info = ""

    def toggle(self):
        self.show_info = not self.show_info

    def toggle_full(self):
        self.full_info = not self.full_info

    def update(self, fps: int, pos: Tuple[float, float, float], rot: Tuple[float, float],
               chunks: int, time: float, slope: float, vel: Tuple[float, float, float],
               ground: bool, collision: str):
        self.fps = fps
        self.player_pos = pos
        self.player_rot = rot
        self.rendered_chunks = chunks
        self.day_time = time
        self.slope_angle = slope
        self.player_velocity = vel
        self.on_ground = ground
        self.collision_info = collision

    def render(self):
        if not self.show_info:
            return

        try:
            hours = int((self.day_time * 24) / self.constants.DAY_LENGTH) % 24
            minutes = int((self.day_time * 24 * 60) / self.constants.DAY_LENGTH) % 60
            seconds = int((self.day_time * 24 * 3600) / self.constants.DAY_LENGTH) % 60

            basic_texts = [
                f"FPS: {self.fps}",
                f"Position: X={self.player_pos[0]:.1f} Y={self.player_pos[1]:.1f} Z={self.player_pos[2]:.1f}",
                f"Rotation: Yaw={self.player_rot[0]:.1f} Pitch={self.player_rot[1]:.1f}",
                f"Velocity: X={self.player_velocity[0]:.1f} Y={self.player_velocity[1]:.1f} Z={self.player_velocity[2]:.1f}",
                f"Ground: {'Yes' if self.on_ground else 'No'}",
                f"Slope: {self.slope_angle:.1f}°"
            ]

            if self.full_info:
                basic_texts.extend([
                    f"Chunks: {self.rendered_chunks}",
                    f"Time: {hours:02d}:{minutes:02d}:{seconds:02d}",
                    f"Block Size: {self.constants.TERRAIN_BLOCK_SIZE:.2f}",
                    f"Smoothing: {'ON' if self.constants.SMOOTH_TERRAIN else 'OFF'}",
                    f"Fog Distance: {self.constants.FOG_DISTANCE:.1f}",
                    f"Seed: {self.constants.SEED}",
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

            debug_surface = pygame.Surface(self.constants.SCREEN_SIZE, pygame.SRCALPHA)
            debug_surface.fill((0, 0, 0, 0))

            y_offset = 10
            for i, text in enumerate(basic_texts):
                font = self.small_font if (self.full_info and i >= 7) else self.font
                text_surface = font.render(text, True, (255, 255, 255, 255))
                debug_surface.blit(text_surface, (10, y_offset))
                y_offset += 20 if (self.full_info and i >= 7) else 25

            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            texture_data = pygame.image.tostring(debug_surface, "RGBA", True)
            glWindowPos2i(0, 0)
            glDrawPixels(*self.constants.SCREEN_SIZE, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

            glEnable(GL_DEPTH_TEST)
            glDisable(GL_BLEND)

        except Exception as e:
            print(f"Debug render error: {e}")

class TerrainUI:
    """User interface system for menus and HUD"""
    def __init__(self, constants: TerrainConstants):
        self.constants = constants
        self.font = pygame.font.SysFont('Arial', 32)
        self.state = "title"  # title, game, pause
        self.create_ui_elements()

    def create_ui_elements(self):
        center_x, center_y = self.constants.SCREEN_SIZE[0] // 2, self.constants.SCREEN_SIZE[1] // 2

        self.title_buttons = [
            {"rect": pygame.Rect(center_x - 100, center_y, 200, 50),
             "text": "Start Game", "action": "start"},
            {"rect": pygame.Rect(center_x - 100, center_y + 70, 200, 50),
             "text": "Exit", "action": "exit"}
        ]

        self.pause_buttons = [
            {"rect": pygame.Rect(center_x - 100, center_y, 200, 50),
             "text": "Continue", "action": "continue"},
            {"rect": pygame.Rect(center_x - 100, center_y + 70, 200, 50),
             "text": "Main Menu", "action": "menu"}
        ]

    def render_text(self, text: str, x: int, y: int, color=(255, 255, 255), size=32):
        font = pygame.font.SysFont('Arial', size)
        text_surface = font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)

        glWindowPos2i(x, self.constants.SCREEN_SIZE[1] - y - text_surface.get_height())
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                     GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    def render_button(self, button: Dict):
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2i(button["rect"].left, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].bottom)
        glVertex2i(button["rect"].left, button["rect"].bottom)
        glEnd()

        glColor3f(0.8, 0.8, 0.8)
        glBegin(GL_LINE_LOOP)
        glVertex2i(button["rect"].left, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].top)
        glVertex2i(button["rect"].right, button["rect"].bottom)
        glVertex2i(button["rect"].left, button["rect"].bottom)
        glEnd()

        text_x = button["rect"].centerx - self.font.size(button["text"])[0] // 2
        text_y = button["rect"].centery - self.font.size(button["text"])[1] // 2
        self.render_text(button["text"], text_x, text_y)

    def check_click(self, pos: Tuple[int, int]) -> Optional[str]:
        buttons = self.title_buttons if self.state == "title" else self.pause_buttons
        for button in buttons:
            if button["rect"].collidepoint(pos):
                return button["action"]
        return None

    def render_title_screen(self):
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.render_text("Terrain Explorer",
                         self.constants.SCREEN_SIZE[0] // 2 - 150,
                         150, (255, 255, 255), 48)

        for button in self.title_buttons:
            self.render_button(button)

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)

    def render_pause_menu(self):
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glColor4f(0.1, 0.1, 0.1, 0.7)
        glBegin(GL_QUADS)
        glVertex2i(0, 0)
        glVertex2i(self.constants.SCREEN_SIZE[0], 0)
        glVertex2i(self.constants.SCREEN_SIZE[0], self.constants.SCREEN_SIZE[1])
        glVertex3i(0, self.constants.SCREEN_SIZE[1], 0)
        glEnd()

        self.render_text("Paused",
                         self.constants.SCREEN_SIZE[0] // 2 - 70,
                         150, (255, 255, 255), 48)

        for button in self.pause_buttons:
            self.render_button(button)

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)

class TerrainGenerator:
    """Procedural terrain generation system"""
    def __init__(self, constants: TerrainConstants):
        self.constants = constants
        self.vertices = {}
        self.normals = {}
        self.generated_area = set()

    def get_height(self, x: float, z: float) -> float:
        x_adj = x / self.constants.TERRAIN_BLOCK_SIZE
        z_adj = z / self.constants.TERRAIN_BLOCK_SIZE

        if not self.constants.SMOOTH_TERRAIN:
            x0, z0 = int(x_adj), int(z_adj)
            return noise.pnoise2(
                x0 * self.constants.TERRAIN_SCALE + self.constants.SEED,
                z0 * self.constants.TERRAIN_SCALE + self.constants.SEED,
                octaves=self.constants.NOISE_OCTAVES,
                persistence=self.constants.NOISE_PERSISTENCE,
                lacunarity=self.constants.NOISE_LACUNARITY
            ) * self.constants.HEIGHT_SCALE

        x0, z0 = int(x_adj), int(z_adj)
        dx, dz = x_adj - x0, z_adj - z0

        points = []
        for i in range(2):
            for j in range(2):
                px = x0 + i
                pz = z0 + j
                if (px, pz) not in self.vertices:
                    self.vertices[(px, pz)] = noise.pnoise2(
                        px * self.constants.TERRAIN_SCALE * self.constants.TERRAIN_BLOCK_SIZE + self.constants.SEED,
                        pz * self.constants.TERRAIN_SCALE * self.constants.TERRAIN_BLOCK_SIZE + self.constants.SEED,
                        octaves=self.constants.NOISE_OCTAVES,
                        persistence=self.constants.NOISE_PERSISTENCE,
                        lacunarity=self.constants.NOISE_LACUNARITY
                    ) * self.constants.HEIGHT_SCALE
                points.append(self.vertices[(px, pz)])

        return (points[0] * (1 - dx) * (1 - dz) +
                points[1] * dx * (1 - dz) +
                points[2] * (1 - dx) * dz +
                points[3] * dx * dz)

    def get_slope_angle(self, x: float, z: float) -> float:
        dx = self.get_height(x + 0.1, z) - self.get_height(x - 0.1, z)
        dz = self.get_height(x, z + 0.1) - self.get_height(x, z - 0.1)
        return degrees(atan2(sqrt(dx ** 2 + dz ** 2), 0.2))

        def generate_area(self, center_x: float, center_z: float) -> int:
            new_area = set()
        radius = int(self.constants.LOAD_RADIUS / self.constants.TERRAIN_BLOCK_SIZE)

        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                x = int(center_x / self.constants.TERRAIN_BLOCK_SIZE) + dx
                z = int(center_z / self.constants.TERRAIN_BLOCK_SIZE) + dz

                if (x, z) not in self.vertices:
                    self.vertices[(x, z)] = noise.pnoise2(
                        x * self.constants.TERRAIN_SCALE * self.constants.TERRAIN_BLOCK_SIZE + self.constants.SEED,
                        z * self.constants.TERRAIN_SCALE * self.constants.TERRAIN_BLOCK_SIZE + self.constants.SEED,
                        octaves=self.constants.NOISE_OCTAVES,
                        persistence=self.constants.NOISE_PERSISTENCE,
                        lacunarity=self.constants.NOISE_LACUNARITY
                    ) * self.constants.HEIGHT_SCALE

                new_area.add((x, z))

        self.generated_area = new_area
        return len(new_area)

class PlayerController:
    """Player movement and camera control system"""
    def __init__(self, terrain: TerrainGenerator, constants: TerrainConstants):
        self.terrain = terrain
        self.constants = constants
        self.pos = [0.0, 0.0, 0.0]
        self.pos[1] = self.terrain.get_height(0, 0) + self.constants.PLAYER_HEIGHT
        self.vel = [0.0, 0.0, 0.0]
        self.yaw = 0.0
        self.pitch = 0.0
        self.on_ground = True
        self.jump_cooldown = 0.0
        self.third_person = False
        self.camera_distance = 5.0
        self.last_collision = "None"

    def can_step_up(self, dx: float, dz: float) -> bool:
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height
        return 0 < height_diff <= self.constants.STEP_HEIGHT

    def can_walk_over(self, dx: float, dz: float) -> bool:
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height

        if height_diff < 0:
            return True

        slope = self.terrain.get_slope_angle(self.pos[0] + dx, self.pos[2] + dz)
        return slope <= self.constants.MAX_CLIMB_ANGLE or abs(height_diff) <= self.constants.STEP_HEIGHT

    def can_jump_over(self, dx: float, dz: float) -> bool:
        current_height = self.terrain.get_height(self.pos[0], self.pos[2])
        target_height = self.terrain.get_height(self.pos[0] + dx, self.pos[2] + dz)
        height_diff = target_height - current_height
        return abs(height_diff) < self.constants.MAX_JUMP_HEIGHT

    def check_movement(self, dx: float, dz: float) -> bool:
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

        self.last_collision = f"Blocked by slope {self.terrain.get_slope_angle(self.pos[0] + dx, self.pos[2] + dz):.1f}°"
        return False

    def update_movement(self, dt: float, keys: Dict[int, bool]):
        move_dir = [0.0, 0.0]
        yaw_rad = radians(self.yaw)

        if keys[K_w]:
            move_dir[0] += cos(yaw_rad)
            move_dir[1] += sin(yaw_rad)
        if keys[K_s]:
            move_dir[0] -= cos(yaw_rad)
            move_dir[1] -= sin(yaw_rad)
        if keys[K_a]:
            move_dir[0] += sin(yaw_rad)
            move_dir[1] -= cos(yaw_rad)
        if keys[K_d]:
            move_dir[0] -= sin(yaw_rad)
            move_dir[1] += cos(yaw_rad)

        if (length := sqrt(move_dir[0] ** 2 + move_dir[1] ** 2)) > 0:
            move_dir = [move_dir[0] / length * self.constants.PLAYER_SPEED * dt,
                        move_dir[1] / length * self.constants.PLAYER_SPEED * dt]

            if not self.check_movement(move_dir[0], move_dir[1]):
                move_dir = [0, 0]

        self.vel[1] -= self.constants.GRAVITY * dt
        self.pos[0] += move_dir[0] + self.vel[0] * dt
        self.pos[2] += move_dir[1] + self.vel[2] * dt
        self.pos[1] += self.vel[1] * dt

        terrain_height = self.terrain.get_height(self.pos[0], self.pos[2])

        if self.pos[1] < terrain_height + self.constants.PLAYER_HEIGHT:
            self.pos[1] = terrain_height + self.constants.PLAYER_HEIGHT
            self.vel[1] = 0.0
            self.on_ground = True

        if keys[K_SPACE] and self.on_ground:
            self.vel[1] = self.constants.JUMP_FORCE
            self.on_ground = False

class TerrainRenderer:
    """Rendering system for terrain and environment"""
    def __init__(self, constants: TerrainConstants):
        self.constants = constants
        self.textures = {}

    def init_gl(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH)
        glClearDepth(1.0)

        if self.constants.FOG_ENABLED:
            self.setup_fog()

    def setup_fog(self):
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogfv(GL_FOG_COLOR, self.constants.FOG_COLOR)
        glFogf(GL_FOG_START, self.constants.FOG_DISTANCE * 0.7)
        glFogf(GL_FOG_END, self.constants.FOG_DISTANCE)

    def update_lighting(self, time: float):
        sun_angle = (time * 2 * pi / self.constants.DAY_LENGTH) - pi / 2
        sun_pos = (1000 * cos(sun_angle), 1000 * sin(sun_angle), 0.0, 1.0)
        intensity = max(0.2, sin(sun_angle + pi / 2))
        light_color = (intensity, intensity * 0.9, intensity * 0.8, 1.0)

        glLightfv(GL_LIGHT0, GL_POSITION, sun_pos)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_color)
        glClearColor(
            self.constants.FOG_COLOR[0] - 0.3 * (1 - intensity),
            self.constants.FOG_COLOR[1] - 0.3 * (1 - intensity),
            self.constants.FOG_COLOR[2] - 0.3 * (1 - intensity),
            1.0
        )

    def render_terrain(terrain):
        glColor3f(0.4, 0.6, 0.3)  # 默认绿色
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

    def render_sky(self, time: float):
        intensity = max(0.2, sin((time * 2 * pi / self.constants.DAY_LENGTH)))
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glBegin(GL_QUADS)
        glColor3f(0.53 * intensity, 0.81 * intensity, 0.98 * intensity)
        glVertex3f(-1, -1, -0.5)
        glVertex3f(1, -1, -0.5)
        glColor3f(0.1 * intensity, 0.1 * intensity, 0.3 * intensity)
        glVertex3f(1, 1, -0.5)
        glVertex3f(-1, 1, -0.5)
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

class TerrainEngine:
    """Main terrain engine class with public API"""
    def __init__(self):
        self.constants = TerrainConstants()
        self.mod_interface = TerrainModInterface(self)
        self.debug_info = TerrainDebugInfo(self.constants)
        self.ui = TerrainUI(self.constants)
        self.terrain = TerrainGenerator(self.constants)
        self.player = PlayerController(self.terrain, self.constants)
        self.renderer = TerrainRenderer(self.constants)
        self.world_objects = []
        self.current_time = 0.0
        self.running = False
        self.clock = pygame.time.Clock()
        self.screen = None

    def initialize(self):
        """Initialize the engine systems"""
        pygame.init()
        self.screen = pygame.display.set_mode(
            self.constants.SCREEN_SIZE,
            DOUBLEBUF | OPENGL | RESIZABLE
        )
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        self.renderer.init_gl()

        glMatrixMode(GL_PROJECTION)
        gluPerspective(
            self.constants.FOV,
            self.constants.SCREEN_SIZE[0] / self.constants.SCREEN_SIZE[1],
            self.constants.NEAR_CLIP,
            self.constants.FAR_CLIP
        )
        glMatrixMode(GL_MODELVIEW)

    def run(self):
        """Main game loop"""
        self.running = True
        start_time = pygame.time.get_ticks()

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.current_time = (pygame.time.get_ticks() - start_time) / 1000.0

            self.handle_events()
            self.update(dt)
            self.render()

        pygame.quit()

    def handle_events(self):
        """Process input events"""
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                self.handle_keydown(event)

            elif event.type == VIDEORESIZE:
                self.handle_resize(event)

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                self.handle_mouse_click(event)

        self.mod_interface.trigger_callbacks('input_handled')

    def handle_keydown(self, event):
        """Process keyboard input"""
        if event.key == K_ESCAPE:
            self.toggle_pause()
        elif event.key == K_F3:
            self.debug_info.toggle()
        elif event.key == K_F12:
            self.debug_info.toggle_full()
        elif event.key == K_F5:
            self.player.third_person = not self.player.third_person
        elif event.key == K_F6:
            self.toggle_smooth_terrain()
        elif event.key in (K_EQUALS, K_PLUS):
            self.adjust_terrain_detail(0.1)
        elif event.key == K_MINUS:
            self.adjust_terrain_detail(-0.1)
        elif event.key == K_F7:
            self.adjust_fog_distance(50)
        elif event.key == K_F8:
            self.adjust_fog_distance(-50)
        elif event.key == K_F9:
            self.toggle_fog()

    def handle_resize(self, event):
        """Handle window resize events"""
        self.constants.SCREEN_SIZE = (event.w, event.h)
        glViewport(0, 0, event.w, event.h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(
            self.constants.FOV,
            event.w / event.h,
            self.constants.NEAR_CLIP,
            self.constants.FAR_CLIP
        )
        glMatrixMode(GL_MODELVIEW)
        self.ui.create_ui_elements()

    def handle_mouse_click(self, event):
        """Handle mouse click events for UI"""
        if self.ui.state in ["title", "pause"]:
            action = self.ui.check_click(event.pos)
            if action == "start":
                self.start_game()
            elif action == "exit":
                self.running = False
            elif action == "continue":
                self.resume_game()
            elif action == "menu":
                self.return_to_menu()

    def toggle_pause(self):
        """Toggle between paused and game states"""
        if self.ui.state == "game":
            self.ui.state = "pause"
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
        elif self.ui.state == "pause":
            self.ui.state = "game"
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)

    def toggle_smooth_terrain(self):
        """Toggle terrain smoothing"""
        self.constants.SMOOTH_TERRAIN = not self.constants.SMOOTH_TERRAIN
        self.terrain.vertices = {}
        self.debug_info.terrain_block_size = self.constants.TERRAIN_BLOCK_SIZE

    def adjust_terrain_detail(self, delta: float):
        """Adjust terrain block size (detail level)"""
        self.constants.TERRAIN_BLOCK_SIZE = max(
            0.1,
            min(2.0, self.constants.TERRAIN_BLOCK_SIZE + delta)
        )
        self.terrain.block_size = self.constants.TERRAIN_BLOCK_SIZE
        self.terrain.vertices = {}
        self.debug_info.terrain_block_size = self.constants.TERRAIN_BLOCK_SIZE

    def adjust_fog_distance(self, delta: float):
        """Adjust fog rendering distance"""
        self.constants.FOG_DISTANCE = max(50, min(500, self.constants.FOG_DISTANCE + delta))
        glFogf(GL_FOG_START, self.constants.FOG_DISTANCE * 0.7)
        glFogf(GL_FOG_END, self.constants.FOG_DISTANCE)
        self.debug_info.fog_distance = self.constants.FOG_DISTANCE

    def toggle_fog(self):
        """Toggle fog rendering"""
        self.constants.FOG_ENABLED = not self.constants.FOG_ENABLED
        if self.constants.FOG_ENABLED:
            glEnable(GL_FOG)
        else:
            glDisable(GL_FOG)

    def start_game(self):
        """Transition from title to game state"""
        self.ui.state = "game"
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def resume_game(self):
        """Transition from pause to game state"""
        self.ui.state = "game"
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def return_to_menu(self):
        """Transition from pause to title state"""
        self.ui.state = "title"
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

    def update(self, dt: float):
        """Update game state"""
        self.mod_interface.trigger_callbacks('pre_update', dt)

        if self.ui.state == "game":
            mx, my = pygame.mouse.get_rel()
            self.player.yaw += mx * self.constants.MOUSE_SENSITIVITY
            self.player.pitch = max(-89, min(89, self.player.pitch - my * self.constants.MOUSE_SENSITIVITY))

            keys = pygame.key.get_pressed()
            self.player.update_movement(dt, keys)

        chunk_count = self.terrain.generate_area(self.player.pos[0], self.player.pos[2])
        current_slope = self.terrain.get_slope_angle(self.player.pos[0], self.player.pos[2])

        self.debug_info.update(
            int(self.clock.get_fps()),
            self.player.pos,
            (self.player.yaw, self.player.pitch),
            chunk_count,
            self.current_time % self.constants.DAY_LENGTH,
            current_slope,
            self.player.vel,
            self.player.on_ground,
            self.player.last_collision
        )

        self.renderer.update_lighting(self.current_time % self.constants.DAY_LENGTH)
        self.mod_interface.trigger_callbacks('post_update', dt)

    def render(self):
        """Render the current frame"""
        self.mod_interface.trigger_callbacks('pre_render')

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if self.ui.state != "title":
            self.setup_camera()
            self.renderer.render_sky(self.current_time % self.constants.DAY_LENGTH)
            self.renderer.render_terrain(self.terrain)
            self.render_world_objects()

        if self.ui.state == "title":
            self.ui.render_title_screen()
        elif self.ui.state == "pause":
            self.ui.render_pause_menu()

        self.debug_info.render()
        pygame.display.flip()

        self.mod_interface.trigger_callbacks('post_render')

    def setup_camera(self):
        """Configure camera based on player state"""
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
                self.player.pos[1] + self.constants.PLAYER_HEIGHT + look_dir[1],
                self.player.pos[2] + look_dir[2],
                0, 1, 0
            )
        else:
            gluLookAt(
                self.player.pos[0],
                self.player.pos[1] + self.constants.PLAYER_HEIGHT,
                self.player.pos[2],
                self.player.pos[0] + look_dir[0],
                self.player.pos[1] + self.constants.PLAYER_HEIGHT + look_dir[1],
                self.player.pos[2] + look_dir[2],
                0, 1, 0
            )

    def render_world_objects(self):
        """Render all custom world objects"""
        for obj in self.world_objects:
            # Placeholder for object rendering
            glPushMatrix()
            glTranslatef(*obj['position'])
            glRotatef(obj['rotation'][0], 1, 0, 0)
            glRotatef(obj['rotation'][1], 0, 1, 0)
            glRotatef(obj['rotation'][2], 0, 0, 1)
            glScalef(*obj['scale'])

            # Simple cube for placeholder
            glColor3f(0.8, 0.2, 0.2)
            glBegin(GL_QUADS)
            for face in self.cube_faces():
                for vertex in face:
                    glVertex3fv(vertex)
            glEnd()

            glPopMatrix()

    def cube_faces(self):
        """Generate cube vertices for placeholder objects"""
        vertices = [
            (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, -1),
            (1, -1, 1), (1, 1, 1), (-1, -1, 1), (-1, 1, 1)
        ]

        return [
            [vertices[0], vertices[1], vertices[2], vertices[3]],  # back
            [vertices[4], vertices[5], vertices[1], vertices[0]],  # front
            [vertices[1], vertices[5], vertices[7], vertices[2]],  # top
            [vertices[0], vertices[3], vertices[6], vertices[4]],  # bottom
            [vertices[3], vertices[2], vertices[7], vertices[6]],  # left
            [vertices[4], vertices[0], vertices[1], vertices[5]]   # right
        ]

# Public API Functions
def create_engine() -> TerrainEngine:
    """Create a new instance of the terrain engine"""
    return TerrainEngine()

def run_engine(engine: TerrainEngine):
    """Run the main game loop of the engine"""
    engine.run()

def get_mod_interface(engine: TerrainEngine) -> TerrainModInterface:
    """Get the modding interface for extending engine functionality"""
    return engine.mod_interface

def update_constant(engine: TerrainEngine, constant_name: str, value):
    """Update an engine constant at runtime"""
    if hasattr(engine.constants, constant_name):
        setattr(engine.constants, constant_name, value)
        return True
    return False

if __name__ == "__main__":
    engine = create_engine()
    engine.initialize()
    run_engine(engine)