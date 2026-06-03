"""
Top-Down Shooter with Controller Support
=========================================
Controls:
  Controller:
    Left stick      — Move
    Right stick     — Aim & shoot (auto-fires when tilted)
    Right trigger   — Shoot toward crosshair
    Left bumper     — Dash
    Start / Options — Pause

  Keyboard + Mouse (fallback):
    WASD / Arrow keys — Move
    Mouse             — Aim
    Left click / Space— Shoot
    Shift             — Dash
    Escape            — Pause

Requirements:
    pip install pygame
"""

import pygame
import math
import random
import sys
import time

# ─── Constants ───────────────────────────────────────────────────────────────

WIDTH, HEIGHT = 900, 650
FPS = 60
TITLE = "VOID STRIKER"

# Colors
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
BG         = (10,  12,  20)
GRID_COLOR = (20,  26,  45)
PLAYER_COL = (80,  200, 255)
BULLET_COL = (255, 240, 80)
ENEMY_COL  = (220, 60,  60)
ELITE_COL  = (220, 120, 30)
BOSS_COL   = (200, 40,  200)
DASH_COL   = (100, 220, 255)
HIT_COL    = (255, 255, 255)
RED        = (220, 60,  60)
GREEN      = (60,  220, 100)
DARK_GREEN = (20,  80,  40)
YELLOW     = (255, 220, 50)
PURPLE     = (180, 60,  220)
UI_BG      = (15,  18,  30)
UI_BORDER  = (40,  60,  100)

DEADZONE = 0.15

# ─── Helpers ─────────────────────────────────────────────────────────────────

def normalize(v):
    mag = math.hypot(*v)
    return (v[0]/mag, v[1]/mag) if mag > 0 else (0, 0)

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def lerp(a, b, t):
    return a + (b - a) * t

# ─── Particle ────────────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, color, vel, life=0.5, size=4, fade=True):
        self.x, self.y = x, y
        self.color     = color
        self.vx, self.vy = vel
        self.life      = life
        self.max_life  = life
        self.size      = size
        self.fade      = fade

    def update(self, dt):
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.vx  *= 0.92
        self.vy  *= 0.92
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t     = self.life / self.max_life
        alpha = int(255 * t) if self.fade else 255
        size  = max(1, int(self.size * t))
        col   = tuple(clamp(int(c * (0.4 + 0.6 * t)), 0, 255) for c in self.color)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), size)

# ─── Bullet ──────────────────────────────────────────────────────────────────

class Bullet:
    SPEED = 520
    RADIUS = 5

    def __init__(self, x, y, dx, dy):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.alive = True
        self.trail = []

    def update(self, dt):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.x += self.dx * self.SPEED * dt
        self.y += self.dy * self.SPEED * dt
        if not (-20 < self.x < WIDTH+20 and -20 < self.y < HEIGHT+20):
            self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            t = (i+1)/len(self.trail)
            r = max(1, int(self.RADIUS * t * 0.6))
            col = tuple(int(c * t) for c in BULLET_COL)
            pygame.draw.circle(surf, col, (int(tx), int(ty)), r)
        pygame.draw.circle(surf, BULLET_COL, (int(self.x), int(self.y)), self.RADIUS)
        pygame.draw.circle(surf, WHITE,      (int(self.x), int(self.y)), self.RADIUS-2)

# ─── Enemy ───────────────────────────────────────────────────────────────────

class Enemy:
    def __init__(self, x, y, kind="basic"):
        self.x, self.y = x, y
        self.kind      = kind
        self.alive     = True
        self.hit_flash = 0.0
        self.angle     = 0.0

        if kind == "basic":
            self.hp = self.max_hp = 2
            self.speed  = random.uniform(70, 110)
            self.radius = 14
            self.color  = ENEMY_COL
            self.score  = 10
        elif kind == "elite":
            self.hp = self.max_hp = 6
            self.speed  = random.uniform(55, 85)
            self.radius = 20
            self.color  = ELITE_COL
            self.score  = 30
        elif kind == "boss":
            self.hp = self.max_hp = 25
            self.speed  = 45
            self.radius = 34
            self.color  = BOSS_COL
            self.score  = 150

    def update(self, px, py, dt):
        dx, dy = px - self.x, py - self.y
        nx, ny = normalize((dx, dy))
        self.x      += nx * self.speed * dt
        self.y      += ny * self.speed * dt
        self.angle  += 90 * dt
        self.hit_flash = max(0, self.hit_flash - dt * 4)

    def take_hit(self, dmg=1):
        self.hp -= dmg
        self.hit_flash = 1.0
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf):
        col = HIT_COL if self.hit_flash > 0.5 else self.color
        cx, cy, r = int(self.x), int(self.y), self.radius

        if self.kind == "basic":
            pts = []
            for i in range(4):
                a = math.radians(self.angle + i*90)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, WHITE, pts, 1)

        elif self.kind == "elite":
            pts = []
            for i in range(6):
                a = math.radians(self.angle + i*60)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, WHITE, pts, 2)

        elif self.kind == "boss":
            pygame.draw.circle(surf, col, (cx, cy), r)
            for i in range(8):
                a = math.radians(self.angle + i*45)
                ex = cx + r*math.cos(a)
                ey = cy + r*math.sin(a)
                pygame.draw.circle(surf, WHITE, (int(ex), int(ey)), 4)
            pygame.draw.circle(surf, WHITE, (cx, cy), r, 2)

        # Health bar (enemies with >1 max hp)
        if self.max_hp > 1:
            bw = self.radius * 2 + 6
            bh = 4
            bx = cx - bw//2
            by = cy - self.radius - 10
            pygame.draw.rect(surf, (60, 20, 20), (bx, by, bw, bh))
            hp_ratio = self.hp / self.max_hp
            pygame.draw.rect(surf, RED, (bx, by, int(bw*hp_ratio), bh))

# ─── Player ──────────────────────────────────────────────────────────────────

class Player:
    SPEED       = 200
    RADIUS      = 13
    MAX_HP      = 5
    FIRE_RATE   = 0.12   # seconds between shots
    DASH_CD     = 1.2
    DASH_DUR    = 0.15
    DASH_SPEED  = 700
    IFRAMES     = 1.0    # invincibility after hit

    def __init__(self):
        self.x, self.y    = WIDTH//2, HEIGHT//2
        self.hp            = self.MAX_HP
        self.alive         = True
        self.fire_timer    = 0.0
        self.dash_cd       = 0.0
        self.dash_timer    = 0.0
        self.dash_dx       = 0.0
        self.dash_dy       = 0.0
        self.iframes       = 0.0
        self.aim_angle     = 0.0
        self.trail         = []
        self.score         = 0

    def update(self, dt, move, aim_vec, shoot, dash_pressed):
        # Dash
        if dash_pressed and self.dash_cd <= 0 and (move[0]!=0 or move[1]!=0):
            nd = normalize(move)
            self.dash_dx, self.dash_dy = nd
            self.dash_timer = self.DASH_DUR
            self.dash_cd    = self.DASH_CD

        if self.dash_timer > 0:
            self.dash_timer -= dt
            self.x += self.dash_dx * self.DASH_SPEED * dt
            self.y += self.dash_dy * self.DASH_SPEED * dt
        else:
            nx, ny = normalize(move) if (move[0]!=0 or move[1]!=0) else (0,0)
            self.x += nx * self.SPEED * dt
            self.y += ny * self.SPEED * dt

        self.x = clamp(self.x, self.RADIUS, WIDTH  - self.RADIUS)
        self.y = clamp(self.y, self.RADIUS, HEIGHT - self.RADIUS)

        if aim_vec[0]!=0 or aim_vec[1]!=0:
            self.aim_angle = math.atan2(aim_vec[1], aim_vec[0])

        self.fire_timer = max(0, self.fire_timer - dt)
        self.dash_cd    = max(0, self.dash_cd    - dt)
        self.iframes    = max(0, self.iframes    - dt)

        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)

        # Auto-shoot when aim is given
        can_fire = shoot and self.fire_timer <= 0
        if can_fire:
            self.fire_timer = self.FIRE_RATE
            dx = math.cos(self.aim_angle)
            dy = math.sin(self.aim_angle)
            return Bullet(self.x, self.y, dx, dy)
        return None

    def take_hit(self):
        if self.iframes > 0:
            return False
        self.hp    -= 1
        self.iframes = self.IFRAMES
        if self.hp <= 0:
            self.alive = False
        return True

    def draw(self, surf):
        dashing = self.dash_timer > 0
        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            t = (i+1)/len(self.trail)
            col = DASH_COL if dashing else PLAYER_COL
            pygame.draw.circle(surf, tuple(int(c*t*0.4) for c in col),
                               (int(tx), int(ty)), max(1, int(self.RADIUS*t*0.5)))

        # Blink during iframes
        if self.iframes > 0 and int(self.iframes * 10) % 2 == 0:
            return

        cx, cy = int(self.x), int(self.y)
        col = DASH_COL if dashing else PLAYER_COL

        # Body
        pygame.draw.circle(surf, col, (cx, cy), self.RADIUS)
        pygame.draw.circle(surf, WHITE, (cx, cy), self.RADIUS, 2)

        # Gun barrel
        bx = cx + int(math.cos(self.aim_angle) * (self.RADIUS + 8))
        by = cy + int(math.sin(self.aim_angle) * (self.RADIUS + 8))
        pygame.draw.line(surf, WHITE, (cx, cy), (bx, by), 3)

        # Crosshair dot
        pygame.draw.circle(surf, YELLOW, (bx, by), 3)

# ─── Game ────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock  = pygame.time.Clock()

        self.font_big  = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_med  = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_sm   = pygame.font.SysFont("consolas", 18)

        self.joystick = None
        self._init_controller()
        self.reset()

    def _init_controller(self):
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Controller: {self.joystick.get_name()}")
        else:
            print("No controller found — keyboard+mouse mode.")

    def reset(self):
        self.player    = Player()
        self.bullets   = []
        self.enemies   = []
        self.particles = []
        self.wave      = 0
        self.wave_timer= 0.0
        self.spawn_cd  = 0.0
        self.paused    = False
        self.game_over = False
        self.score     = 0
        self.high_score= getattr(self, "high_score", 0)
        self._next_wave()

    # ── Wave management ──────────────────────────────────────────────────────

    def _next_wave(self):
        self.wave      += 1
        self.wave_timer = 3.0
        self.spawn_queue= self._build_wave(self.wave)

    def _build_wave(self, w):
        q = []
        basics = 4 + w * 2
        elites = max(0, w - 2)
        bosses = 1 if w % 5 == 0 else 0
        for _ in range(basics): q.append("basic")
        for _ in range(elites): q.append("elite")
        for _ in range(bosses): q.append("boss")
        random.shuffle(q)
        return q

    def _spawn_enemy(self, kind):
        edge = random.choice(["top","bottom","left","right"])
        if edge == "top":    x,y = random.randint(0,WIDTH), -30
        elif edge == "bottom": x,y = random.randint(0,WIDTH), HEIGHT+30
        elif edge == "left": x,y = -30, random.randint(0,HEIGHT)
        else:                x,y = WIDTH+30, random.randint(0,HEIGHT)
        self.enemies.append(Enemy(x, y, kind))

    # ── Input ─────────────────────────────────────────────────────────────────

    def _get_input(self):
        move  = [0.0, 0.0]
        aim   = [0.0, 0.0]
        shoot = False
        dash  = False
        pause = False

        keys = pygame.key.get_pressed()
        # Keyboard move
        if keys[pygame.K_w] or keys[pygame.K_UP]:    move[1] -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  move[1] += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  move[0] -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move[0] += 1
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]: dash = True

        # Mouse aim
        mx, my = pygame.mouse.get_pos()
        dx, dy = mx - self.player.x, my - self.player.y
        mag = math.hypot(dx, dy)
        if mag > 5:
            aim = [dx/mag, dy/mag]
        if pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]:
            shoot = True

        # Controller overrides keyboard if connected
        j = self.joystick
        if j:
            # Left stick = move
            lx = j.get_axis(0)
            ly = j.get_axis(1)
            if abs(lx) > DEADZONE: move[0] = lx
            if abs(ly) > DEADZONE: move[1] = ly

            # Right stick = aim
            try:
                rx = j.get_axis(2)
                ry = j.get_axis(3)
            except Exception:
                rx, ry = 0, 0
            if abs(rx) > DEADZONE or abs(ry) > DEADZONE:
                aim   = [rx, ry]
                shoot = True  # auto-fire when aiming with stick

            # Right trigger (axis 5 on most controllers, or axis 4)
            try:
                rt = j.get_axis(5)
            except Exception:
                try: rt = j.get_axis(4)
                except: rt = -1
            if rt > 0.3:
                shoot = True

            # Left bumper = dash (button 4)
            try:
                if j.get_button(4): dash = True
            except Exception:
                pass

            # Start / options = pause (button 7 or 9)
            try:
                if j.get_button(7) or j.get_button(9): pause = True
            except Exception:
                pass

        return move, aim, shoot, dash, pause

    # ── Particles ─────────────────────────────────────────────────────────────

    def _burst(self, x, y, color, n=12, speed=140):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(speed*0.3, speed)
            self.particles.append(
                Particle(x, y, color, (math.cos(a)*s, math.sin(a)*s),
                         life=random.uniform(0.3, 0.7),
                         size=random.randint(2,6)))

    # ── Draw helpers ─────────────────────────────────────────────────────────

    def _draw_grid(self):
        for x in range(0, WIDTH, 50):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WIDTH, y))

    def _draw_hud(self):
        # Bottom bar background
        bar_h = 52
        pygame.draw.rect(self.screen, UI_BG,    (0, HEIGHT-bar_h, WIDTH, bar_h))
        pygame.draw.rect(self.screen, UI_BORDER, (0, HEIGHT-bar_h, WIDTH, bar_h), 1)

        # HP hearts
        for i in range(self.player.MAX_HP):
            col = RED if i < self.player.hp else (40, 20, 20)
            pygame.draw.circle(self.screen, col, (22 + i*28, HEIGHT-bar_h+14), 8)

        # Score
        sc_surf = self.font_med.render(f"SCORE  {self.score:06d}", True, WHITE)
        self.screen.blit(sc_surf, (WIDTH//2 - sc_surf.get_width()//2, HEIGHT-bar_h+8))

        # Wave
        wv_surf = self.font_sm.render(f"WAVE {self.wave}", True, YELLOW)
        self.screen.blit(wv_surf, (WIDTH - wv_surf.get_width() - 12, HEIGHT-bar_h+10))

        # Dash cooldown
        dash_ratio = 1.0 - clamp(self.player.dash_cd / self.player.DASH_CD, 0, 1)
        bar_w = 80
        bx, by = WIDTH - bar_w - 12, HEIGHT - bar_h + 28
        pygame.draw.rect(self.screen, (30, 30, 50), (bx, by, bar_w, 8))
        pygame.draw.rect(self.screen, DASH_COL, (bx, by, int(bar_w*dash_ratio), 8))
        db_surf = self.font_sm.render("DASH", True, DASH_COL)
        self.screen.blit(db_surf, (bx, by - 14))

        # Wave announcement
        if self.wave_timer > 0:
            alpha = min(1.0, self.wave_timer)
            col   = tuple(int(c*alpha) for c in YELLOW)
            msg   = self.font_big.render(f"WAVE  {self.wave}", True, col)
            self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 60))

        # Controller hint (first 5s)
        if not hasattr(self, "_hint_shown"):
            self._hint_shown = time.time()
        if time.time() - self._hint_shown < 5:
            if self.joystick:
                hint = "L-Stick: Move  R-Stick: Aim+Fire  LB: Dash  Start: Pause"
            else:
                hint = "WASD: Move  Mouse: Aim  LMB/Space: Fire  Shift: Dash  Esc: Pause"
            h_surf = self.font_sm.render(hint, True, (80, 100, 140))
            self.screen.blit(h_surf, (WIDTH//2 - h_surf.get_width()//2, 10))

    def _draw_pause(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 140))
        self.screen.blit(s, (0, 0))
        t1 = self.font_big.render("PAUSED", True, WHITE)
        t2 = self.font_sm.render("Press Start / Escape to resume", True, (160,160,180))
        self.screen.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 50))
        self.screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 20))

    def _draw_game_over(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 170))
        self.screen.blit(s, (0, 0))
        t1 = self.font_big.render("GAME  OVER", True, RED)
        t2 = self.font_med.render(f"Score: {self.score}    High: {self.high_score}", True, YELLOW)
        t3 = self.font_sm.render("Press Enter / Start to restart", True, (180,180,200))
        self.screen.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 80))
        self.screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2))
        self.screen.blit(t3, (WIDTH//2 - t3.get_width()//2, HEIGHT//2 + 60))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        pause_held = False

        while True:
            dt = self.clock.tick(FPS) / 1000.0

            # ── Events ───────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_over:
                            self.reset()
                        else:
                            self.paused = not self.paused
                    if event.key == pygame.K_RETURN and self.game_over:
                        self.reset()

                if event.type == pygame.JOYBUTTONDOWN:
                    btn = event.button
                    # Start / Options to pause
                    if btn in (7, 9):
                        if not pause_held:
                            if self.game_over:
                                self.reset()
                            else:
                                self.paused = not self.paused
                            pause_held = True
                    # A / Cross to restart on game over
                    if btn == 0 and self.game_over:
                        self.reset()

                if event.type == pygame.JOYBUTTONUP:
                    if event.button in (7, 9):
                        pause_held = False

                if event.type == pygame.JOYDEVICEADDED:
                    self._init_controller()
                if event.type == pygame.JOYDEVICEREMOVED:
                    self.joystick = None
                    print("Controller disconnected.")

            if self.paused:
                self._draw_pause()
                pygame.display.flip()
                continue

            if self.game_over:
                self._draw_game_over()
                pygame.display.flip()
                continue

            # ── Get input ────────────────────────────────────────────────────
            move, aim, shoot, dash, pause = self._get_input()
            if pause and not pause_held:
                self.paused = True
                pause_held  = True
            elif not pause:
                pause_held = False

            # ── Update player ────────────────────────────────────────────────
            new_bullet = self.player.update(dt, move, aim, shoot, dash)
            if new_bullet:
                self.bullets.append(new_bullet)

            # ── Wave / spawn logic ────────────────────────────────────────────
            self.wave_timer = max(0, self.wave_timer - dt)

            if self.wave_timer <= 0:
                self.spawn_cd -= dt
                if self.spawn_cd <= 0 and self.spawn_queue:
                    kind = self.spawn_queue.pop(0)
                    self._spawn_enemy(kind)
                    self.spawn_cd = 0.5

                if not self.spawn_queue and not self.enemies:
                    self._next_wave()

            # ── Update bullets ───────────────────────────────────────────────
            for b in self.bullets:
                b.update(dt)
            self.bullets = [b for b in self.bullets if b.alive]

            # ── Update enemies ───────────────────────────────────────────────
            for e in self.enemies:
                e.update(self.player.x, self.player.y, dt)

                # Bullet collision
                for b in self.bullets:
                    if not b.alive: continue
                    dist = math.hypot(b.x - e.x, b.y - e.y)
                    if dist < e.radius + Bullet.RADIUS:
                        b.alive = False
                        killed  = e.take_hit()
                        self._burst(b.x, b.y, e.color, n=8, speed=100)
                        if killed:
                            self.score += e.score
                            self._burst(e.x, e.y, e.color, n=20, speed=160)

                # Player collision
                dist = math.hypot(self.player.x - e.x, self.player.y - e.y)
                if dist < self.player.RADIUS + e.radius:
                    if self.player.take_hit():
                        self._burst(self.player.x, self.player.y, PLAYER_COL, n=14)

            self.enemies = [e for e in self.enemies if e.alive]

            # Dash particles
            if self.player.dash_timer > 0:
                self._burst(self.player.x, self.player.y, DASH_COL, n=2, speed=60)

            # ── Update particles ─────────────────────────────────────────────
            self.particles = [p for p in self.particles if p.update(dt)]

            # ── Check game over ──────────────────────────────────────────────
            if not self.player.alive:
                self.game_over = True
                self.high_score = max(self.high_score, self.score)

            # ── Draw ─────────────────────────────────────────────────────────
            self.screen.fill(BG)
            self._draw_grid()

            for p in self.particles: p.draw(self.screen)
            for b in self.bullets:   b.draw(self.screen)
            for e in self.enemies:   e.draw(self.screen)
            self.player.draw(self.screen)
            self._draw_hud()

            pygame.display.flip()

# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game().run()