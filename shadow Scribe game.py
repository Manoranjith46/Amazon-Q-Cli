import pygame
import math
import random
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_GRAY = (192, 192, 192)
BLUE = (0, 100, 200)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
YELLOW = (255, 255, 0)
PURPLE = (150, 50, 200)
ORANGE = (255, 165, 0)
SHADOW_COLOR = (20, 20, 40)
LIGHT_COLOR = (255, 255, 200, 100)

# Game States
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    SPELLBOOK = 3
    GAME_OVER = 4
    VICTORY = 5

# Tile Types
class TileType(Enum):
    FLOOR = 1
    WALL = 2
    SHADOW = 3
    DOOR = 4
    SWITCH = 5
    GAP = 6
    BRIDGE = 7
    CANDLE = 8
    SCROLL = 9

@dataclass
class Spell:
    name: str
    word: str
    cooldown: float
    duration: float
    uses_left: int
    max_uses: int
    description: str

class Player:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.size = 20
        self.speed = 2
        self.light_radius = 80
        self.max_light = 100
        self.current_light = self.max_light
        self.is_invisible = False
        self.invisible_timer = 0
        self.in_shadow = False
        self.noise_level = 0
        self.typing_accuracy = 1.0
        self.mind_drain = 0
        self.max_mind_drain = 100
        
    def move(self, dx: int, dy: int, level_map: List[List[int]]):
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed
        
        # Check collision with walls
        if self.can_move_to(new_x, new_y, level_map):
            self.x = new_x
            self.y = new_y
            
            # Check if on noisy tile
            tile_x = int(self.x // 32)
            tile_y = int(self.y // 32)
            if 0 <= tile_x < len(level_map[0]) and 0 <= tile_y < len(level_map):
                if level_map[tile_y][tile_x] == TileType.FLOOR.value:
                    self.noise_level = 1
                else:
                    self.noise_level = 0
    
    def can_move_to(self, x: int, y: int, level_map: List[List[int]]) -> bool:
        # Check boundaries
        if x < 0 or y < 0 or x >= len(level_map[0]) * 32 or y >= len(level_map) * 32:
            return False
            
        # Check tile collision
        tile_x = int(x // 32)
        tile_y = int(y // 32)
        
        if 0 <= tile_x < len(level_map[0]) and 0 <= tile_y < len(level_map):
            tile_type = level_map[tile_y][tile_x]
            return tile_type not in [TileType.WALL.value, TileType.GAP.value]
        
        return False
    
    def update(self, dt: float):
        # Update invisibility
        if self.is_invisible:
            self.invisible_timer -= dt
            if self.invisible_timer <= 0:
                self.is_invisible = False
        
        # Update light (slowly decreases)
        self.current_light = max(0, self.current_light - dt * 2)
        
        # Update mind drain (slowly recovers)
        self.mind_drain = max(0, self.mind_drain - dt * 5)
        
        # Reset noise level
        self.noise_level = max(0, self.noise_level - dt * 3)
    
    def cast_spell(self, spell_name: str):
        if spell_name == "invisible":
            self.is_invisible = True
            self.invisible_timer = 5.0
        elif spell_name == "glow":
            self.current_light = min(self.max_light, self.current_light + 30)

class Enemy:
    def __init__(self, x: int, y: int, patrol_points: List[Tuple[int, int]]):
        self.x = x
        self.y = y
        self.size = 18
        self.speed = 1
        self.patrol_points = patrol_points
        self.current_target = 0
        self.detection_radius = 60
        self.sound_detection_radius = 40
        self.is_chasing = False
        self.chase_timer = 0
        self.frozen = False
        self.freeze_timer = 0
        
    def update(self, dt: float, player: Player):
        # Update freeze status
        if self.frozen:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.frozen = False
            return
        
        # Check for player detection
        distance_to_player = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
        
        # Visual detection (only if player not invisible and in light)
        can_see_player = (not player.is_invisible and 
                         distance_to_player < self.detection_radius and
                         player.current_light > 20)
        
        # Sound detection
        can_hear_player = (distance_to_player < self.sound_detection_radius and 
                          player.noise_level > 0.5)
        
        if can_see_player or can_hear_player:
            self.is_chasing = True
            self.chase_timer = 3.0
        
        if self.is_chasing:
            self.chase_timer -= dt
            if self.chase_timer <= 0:
                self.is_chasing = False
            else:
                # Chase player
                dx = player.x - self.x
                dy = player.y - self.y
                distance = math.sqrt(dx**2 + dy**2)
                if distance > 0:
                    self.x += (dx / distance) * self.speed
                    self.y += (dy / distance) * self.speed
        else:
            # Patrol behavior
            if self.patrol_points:
                target_x, target_y = self.patrol_points[self.current_target]
                dx = target_x - self.x
                dy = target_y - self.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance < 5:
                    self.current_target = (self.current_target + 1) % len(self.patrol_points)
                else:
                    self.x += (dx / distance) * self.speed * 0.5
                    self.y += (dy / distance) * self.speed * 0.5
    
    def freeze(self, duration: float):
        self.frozen = True
        self.freeze_timer = duration

class Level:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tile_size = 32
        self.map = [[TileType.FLOOR.value for _ in range(width)] for _ in range(height)]
        self.enemies = []
        self.bridges = []
        self.switches = []
        self.candles = []
        self.scrolls = []
        
    def generate_basic_level(self):
        # Create walls around the perimeter
        for x in range(self.width):
            self.map[0][x] = TileType.WALL.value
            self.map[self.height-1][x] = TileType.WALL.value
        for y in range(self.height):
            self.map[y][0] = TileType.WALL.value
            self.map[y][self.width-1] = TileType.WALL.value
        
        # Add some internal walls
        for i in range(5):
            x = random.randint(2, self.width-3)
            y = random.randint(2, self.height-3)
            self.map[y][x] = TileType.WALL.value
        
        # Add shadow areas
        for i in range(3):
            x = random.randint(1, self.width-2)
            y = random.randint(1, self.height-2)
            self.map[y][x] = TileType.SHADOW.value
        
        # Add gaps
        for i in range(2):
            x = random.randint(1, self.width-2)
            y = random.randint(1, self.height-2)
            self.map[y][x] = TileType.GAP.value
        
        # Add enemies
        for i in range(2):
            x = random.randint(2, self.width-3) * 32
            y = random.randint(2, self.height-3) * 32
            patrol_points = [
                (x, y),
                (x + 64, y),
                (x + 64, y + 64),
                (x, y + 64)
            ]
            self.enemies.append(Enemy(x, y, patrol_points))
        
        # Add candles
        for i in range(3):
            x = random.randint(1, self.width-2)
            y = random.randint(1, self.height-2)
            if self.map[y][x] == TileType.FLOOR.value:
                self.candles.append((x, y))
        
        # Add scroll
        x = random.randint(1, self.width-2)
        y = random.randint(1, self.height-2)
        if self.map[y][x] == TileType.FLOOR.value:
            self.scrolls.append((x, y))

class SpellSystem:
    def __init__(self):
        self.spells = {
            "invisible": Spell("Invisibility", "invisible", 10.0, 5.0, 3, 3, "Become undetectable for 5 seconds"),
            "freeze": Spell("Freeze", "freeze", 15.0, 3.0, 2, 2, "Pause enemy movement temporarily"),
            "bridge": Spell("Bridge", "bridge", 8.0, 0.0, 5, 5, "Create walkable platform across gaps"),
            "glow": Spell("Glow", "glow", 5.0, 0.0, 10, 10, "Restore light energy"),
        }
        self.cooldowns = {spell: 0.0 for spell in self.spells}
        self.current_input = ""
        self.typing_errors = 0
        
    def update(self, dt: float):
        for spell in self.cooldowns:
            self.cooldowns[spell] = max(0, self.cooldowns[spell] - dt)
    
    def try_cast_spell(self, word: str, player: Player, level: Level) -> bool:
        if word in self.spells:
            spell = self.spells[word]
            if self.cooldowns[word] <= 0 and spell.uses_left > 0:
                # Cast the spell
                if word == "invisible":
                    player.cast_spell("invisible")
                elif word == "freeze":
                    for enemy in level.enemies:
                        enemy.freeze(spell.duration)
                elif word == "bridge":
                    # Create bridge at nearest gap
                    player_tile_x = int(player.x // 32)
                    player_tile_y = int(player.y // 32)
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            tx, ty = player_tile_x + dx, player_tile_y + dy
                            if (0 <= tx < level.width and 0 <= ty < level.height and
                                level.map[ty][tx] == TileType.GAP.value):
                                level.bridges.append((tx, ty))
                                break
                elif word == "glow":
                    player.cast_spell("glow")
                
                # Apply cooldown and use
                self.cooldowns[word] = spell.cooldown
                spell.uses_left -= 1
                return True
        else:
            # Wrong spell - increase mind drain
            player.mind_drain = min(player.max_mind_drain, player.mind_drain + 10)
            self.typing_errors += 1
        
        return False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Shadow Scribe")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)
        
        self.state = GameState.MENU
        self.player = Player(64, 64)
        self.level = Level(25, 20)
        self.level.generate_basic_level()
        self.spell_system = SpellSystem()
        self.camera_x = 0
        self.camera_y = 0
        
        # UI state
        self.current_input = ""
        self.input_active = False
        self.spellbook_open = False
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_SPACE:
                        self.state = GameState.PLAYING
                
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_TAB:
                        self.spellbook_open = not self.spellbook_open
                        if self.spellbook_open:
                            self.state = GameState.SPELLBOOK
                        else:
                            self.state = GameState.PLAYING
                    
                    elif event.key == pygame.K_RETURN:
                        if self.current_input:
                            success = self.spell_system.try_cast_spell(
                                self.current_input.lower(), self.player, self.level)
                            self.current_input = ""
                    
                    elif event.key == pygame.K_BACKSPACE:
                        self.current_input = self.current_input[:-1]
                    
                    else:
                        if event.unicode.isalpha():
                            self.current_input += event.unicode.lower()
                
                elif self.state == GameState.SPELLBOOK:
                    if event.key == pygame.K_TAB:
                        self.spellbook_open = False
                        self.state = GameState.PLAYING
                
                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.restart_game()
        
        return True
    
    def update(self, dt: float):
        if self.state == GameState.PLAYING:
            # Handle player movement
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
            
            self.player.move(dx, dy, self.level.map)
            self.player.update(dt)
            
            # Update enemies
            for enemy in self.level.enemies:
                enemy.update(dt, self.player)
            
            # Update spell system
            self.spell_system.update(dt)
            
            # Update camera
            self.camera_x = self.player.x - SCREEN_WIDTH // 2
            self.camera_y = self.player.y - SCREEN_HEIGHT // 2
            
            # Check game over conditions
            if self.player.current_light <= 0:
                self.state = GameState.GAME_OVER
            
            if self.player.mind_drain >= self.player.max_mind_drain:
                self.state = GameState.GAME_OVER
            
            # Check enemy collision
            for enemy in self.level.enemies:
                distance = math.sqrt((enemy.x - self.player.x)**2 + (enemy.y - self.player.y)**2)
                if distance < 25:
                    self.state = GameState.GAME_OVER
            
            # Check candle collection
            player_tile_x = int(self.player.x // 32)
            player_tile_y = int(self.player.y // 32)
            for i, (cx, cy) in enumerate(self.level.candles):
                if cx == player_tile_x and cy == player_tile_y:
                    self.player.current_light = min(self.player.max_light, 
                                                  self.player.current_light + 40)
                    self.level.candles.pop(i)
                    break
            
            # Check scroll collection
            for i, (sx, sy) in enumerate(self.level.scrolls):
                if sx == player_tile_x and sy == player_tile_y:
                    # Unlock new spell or restore uses
                    for spell in self.spell_system.spells.values():
                        spell.uses_left = spell.max_uses
                    self.level.scrolls.pop(i)
                    break
    
    def draw(self):
        self.screen.fill(BLACK)
        
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.draw_game()
        elif self.state == GameState.SPELLBOOK:
            self.draw_spellbook()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()
        
        pygame.display.flip()
    
    def draw_menu(self):
        title = self.large_font.render("SHADOW SCRIBE", True, WHITE)
        subtitle = self.font.render("A Magical Typing Adventure", True, GRAY)
        instruction = self.font.render("Press SPACE to begin your quest", True, WHITE)
        
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))
        self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 250))
        self.screen.blit(instruction, (SCREEN_WIDTH//2 - instruction.get_width()//2, 400))
        
        # Draw instructions
        instructions = [
            "Use WASD or Arrow Keys to move",
            "Type magic words and press ENTER to cast spells",
            "Press TAB to open your spellbook",
            "Avoid the ghostly sentinels",
            "Collect candles to restore light",
            "Find scrolls to restore spell uses"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, LIGHT_GRAY)
            self.screen.blit(text, (50, 500 + i * 25))
    
    def draw_game(self):
        # Draw level
        for y in range(self.level.height):
            for x in range(self.level.width):
                screen_x = x * 32 - self.camera_x
                screen_y = y * 32 - self.camera_y
                
                if -32 <= screen_x <= SCREEN_WIDTH and -32 <= screen_y <= SCREEN_HEIGHT:
                    tile_type = self.level.map[y][x]
                    color = GRAY
                    
                    if tile_type == TileType.WALL.value:
                        color = DARK_GRAY
                    elif tile_type == TileType.SHADOW.value:
                        color = SHADOW_COLOR
                    elif tile_type == TileType.GAP.value:
                        color = BLACK
                    
                    pygame.draw.rect(self.screen, color, 
                                   (screen_x, screen_y, 32, 32))
        
        # Draw bridges
        for bx, by in self.level.bridges:
            screen_x = bx * 32 - self.camera_x
            screen_y = by * 32 - self.camera_y
            pygame.draw.rect(self.screen, ORANGE, (screen_x, screen_y, 32, 32))
        
        # Draw candles
        for cx, cy in self.level.candles:
            screen_x = cx * 32 - self.camera_x + 16
            screen_y = cy * 32 - self.camera_y + 16
            pygame.draw.circle(self.screen, YELLOW, (screen_x, screen_y), 8)
        
        # Draw scrolls
        for sx, sy in self.level.scrolls:
            screen_x = sx * 32 - self.camera_x + 16
            screen_y = sy * 32 - self.camera_y + 16
            pygame.draw.rect(self.screen, PURPLE, (screen_x-6, screen_y-8, 12, 16))
        
        # Draw player light
        if self.player.current_light > 0:
            light_surface = pygame.Surface((self.player.light_radius * 2, 
                                          self.player.light_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(light_surface, LIGHT_COLOR, 
                             (self.player.light_radius, self.player.light_radius), 
                             int(self.player.light_radius * (self.player.current_light / 100)))
            
            self.screen.blit(light_surface, 
                           (self.player.x - self.player.light_radius - self.camera_x,
                            self.player.y - self.player.light_radius - self.camera_y))
        
        # Draw enemies
        for enemy in self.level.enemies:
            screen_x = enemy.x - self.camera_x
            screen_y = enemy.y - self.camera_y
            color = RED if enemy.is_chasing else BLUE
            if enemy.frozen:
                color = LIGHT_GRAY
            pygame.draw.circle(self.screen, color, (int(screen_x), int(screen_y)), enemy.size)
        
        # Draw player
        screen_x = self.player.x - self.camera_x
        screen_y = self.player.y - self.camera_y
        player_color = GREEN
        if self.player.is_invisible:
            player_color = (50, 255, 50, 100)
        pygame.draw.circle(self.screen, player_color, (int(screen_x), int(screen_y)), self.player.size)
        
        # Draw UI
        self.draw_ui()
    
    def draw_ui(self):
        # Light meter
        light_width = 200
        light_height = 20
        light_x = 20
        light_y = 20
        
        pygame.draw.rect(self.screen, DARK_GRAY, (light_x, light_y, light_width, light_height))
        light_fill = int((self.player.current_light / self.player.max_light) * light_width)
        pygame.draw.rect(self.screen, YELLOW, (light_x, light_y, light_fill, light_height))
        
        light_text = self.small_font.render("Light", True, WHITE)
        self.screen.blit(light_text, (light_x, light_y - 20))
        
        # Mind drain meter
        mind_y = light_y + 40
        pygame.draw.rect(self.screen, DARK_GRAY, (light_x, mind_y, light_width, light_height))
        mind_fill = int((self.player.mind_drain / self.player.max_mind_drain) * light_width)
        pygame.draw.rect(self.screen, RED, (light_x, mind_y, mind_fill, light_height))
        
        mind_text = self.small_font.render("Mind Drain", True, WHITE)
        self.screen.blit(mind_text, (light_x, mind_y - 20))
        
        # Current input
        input_text = self.font.render(f"Spell: {self.current_input}", True, WHITE)
        self.screen.blit(input_text, (20, SCREEN_HEIGHT - 60))
        
        # Instructions
        instruction_text = self.small_font.render("TAB: Spellbook | Type spells and press ENTER", True, LIGHT_GRAY)
        self.screen.blit(instruction_text, (20, SCREEN_HEIGHT - 30))
    
    def draw_spellbook(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Spellbook background
        book_width = 600
        book_height = 500
        book_x = (SCREEN_WIDTH - book_width) // 2
        book_y = (SCREEN_HEIGHT - book_height) // 2
        
        pygame.draw.rect(self.screen, DARK_GRAY, (book_x, book_y, book_width, book_height))
        pygame.draw.rect(self.screen, WHITE, (book_x, book_y, book_width, book_height), 3)
        
        # Title
        title = self.font.render("SPELLBOOK", True, WHITE)
        self.screen.blit(title, (book_x + 20, book_y + 20))
        
        # Spells
        y_offset = 60
        for spell_name, spell in self.spell_system.spells.items():
            cooldown = self.spell_system.cooldowns[spell_name]
            
            # Spell name and word
            spell_text = f"{spell.name} ({spell.word})"
            color = WHITE if cooldown <= 0 and spell.uses_left > 0 else GRAY
            text = self.font.render(spell_text, True, color)
            self.screen.blit(text, (book_x + 20, book_y + y_offset))
            
            # Uses left
            uses_text = f"Uses: {spell.uses_left}/{spell.max_uses}"
            uses_surface = self.small_font.render(uses_text, True, color)
            self.screen.blit(uses_surface, (book_x + 300, book_y + y_offset))
            
            # Cooldown
            if cooldown > 0:
                cooldown_text = f"Cooldown: {cooldown:.1f}s"
                cooldown_surface = self.small_font.render(cooldown_text, True, RED)
                self.screen.blit(cooldown_surface, (book_x + 400, book_y + y_offset))
            
            # Description
            desc_surface = self.small_font.render(spell.description, True, LIGHT_GRAY)
            self.screen.blit(desc_surface, (book_x + 20, book_y + y_offset + 20))
            
            y_offset += 60
        
        # Instructions
        instruction = self.small_font.render("Press TAB to close", True, WHITE)
        self.screen.blit(instruction, (book_x + 20, book_y + book_height - 30))
    
    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        game_over_text = self.large_font.render("GAME OVER", True, RED)
        self.screen.blit(game_over_text, 
                        (SCREEN_WIDTH//2 - game_over_text.get_width()//2, 300))
        
        restart_text = self.font.render("Press R to restart", True, WHITE)
        self.screen.blit(restart_text, 
                        (SCREEN_WIDTH//2 - restart_text.get_width()//2, 400))
    
    def restart_game(self):
        self.player = Player(64, 64)
        self.level = Level(25, 20)
        self.level.generate_basic_level()
        self.spell_system = SpellSystem()
        self.current_input = ""
        self.state = GameState.PLAYING
    
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            running = self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
