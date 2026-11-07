"""Space Shooter Game (Python, tkinter).

A small 2D arcade shooter: move the player ship left/right, shoot
bullets upward, destroy incoming enemies, avoid collisions. Tracks
score, lives, and level. Pure standard library (tkinter).
"""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass, field
from typing import List

WIDTH = 800
HEIGHT = 600
PLAYER_SPEED = 8
BULLET_SPEED = 12
ENEMY_SPEED = 3
SPAWN_INTERVAL_MS = 900


@dataclass
class Player:
    x: float = WIDTH / 2
    y: float = HEIGHT - 40
    w: int = 40
    h: int = 20
    speed: int = PLAYER_SPEED
    lives: int = 3

    @property
    def left(self) -> float:
        return self.x - self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y - self.h / 2

    @property
    def bottom(self) -> float:
        return self.y + self.h / 2


@dataclass
class Bullet:
    x: float
    y: float
    w: int = 4
    h: int = 12
    speed: int = BULLET_SPEED

    @property
    def left(self) -> float:
        return self.x - self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y - self.h / 2

    @property
    def bottom(self) -> float:
        return self.y + self.h / 2


@dataclass
class Enemy:
    x: float
    y: float
    w: int = 36
    h: int = 24
    speed: float = ENEMY_SPEED
    dx: float = 0.0

    @property
    def left(self) -> float:
        return self.x - self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y - self.h / 2

    @property
    def bottom(self) -> float:
        return self.y + self.h / 2


def rects_overlap(a, b) -> bool:
    return not (a.right < b.left or a.left > b.right or
                a.bottom < b.top or a.top > b.bottom)


class Game:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Space Shooter")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
        self.canvas.pack()

        self.player = Player()
        self.bullets: List[Bullet] = []
        self.enemies: List[Enemy] = []
        self.score = 0
        self.level = 1
        self.game_over = False
        self.paused = False

        self.keys = {"Left": False, "Right": False, "space": False}
        self.shoot_cooldown = 0

        self.root.bind("<KeyPress-Left>", lambda e: self._set_key("Left", True))
        self.root.bind("<KeyRelease-Left>", lambda e: self._set_key("Left", False))
        self.root.bind("<KeyPress-Right>", lambda e: self._set_key("Right", True))
        self.root.bind("<KeyRelease-Right>", lambda e: self._set_key("Right", False))
        self.root.bind("<KeyPress-space>", lambda e: self._set_key("space", True))
        self.root.bind("<KeyRelease-space>", lambda e: self._set_key("space", False))
        self.root.bind("<KeyPress-r>", lambda e: self._restart())
        self.root.bind("<KeyPress-R>", lambda e: self._restart())
        self.root.bind("<KeyPress-p>", lambda e: self._toggle_pause())
        self.root.bind("<KeyPress-P>", lambda e: self._toggle_pause())

        self.spawn_job = None
        self.loop_job = None
        self._schedule_spawn()
        self._loop()

    # ------------------------------------------------------------------ #
    # Input handling
    # ------------------------------------------------------------------ #
    def _set_key(self, name: str, value: bool) -> None:
        self.keys[name] = value

    def _restart(self) -> None:
        if not self.game_over:
            return
        self.player = Player()
        self.bullets.clear()
        self.enemies.clear()
        self.score = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.shoot_cooldown = 0
        if self.spawn_job is not None:
            self.root.after_cancel(self.spawn_job)
        self._schedule_spawn()

    def _toggle_pause(self) -> None:
        if self.game_over:
            return
        self.paused = not self.paused

    # ------------------------------------------------------------------ #
    # Spawning
    # ------------------------------------------------------------------ #
    def _schedule_spawn(self) -> None:
        if self.game_over:
            return
        self.spawn_job = self.root.after(SPAWN_INTERVAL_MS, self._spawn_enemy)

    def _spawn_enemy(self) -> None:
        if self.game_over or self.paused:
            self._schedule_spawn()
            return
        x = random.randint(40, WIDTH - 40)
        speed = ENEMY_SPEED + (self.level - 1) * 0.4
        dx = random.choice((-1.2, -0.6, 0.0, 0.6, 1.2))
        self.enemies.append(Enemy(x=x, y=-20, speed=speed, dx=dx))
        self._schedule_spawn()

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def _loop(self) -> None:
        if not self.game_over and not self.paused:
            self._update()
        self._draw()
        self.loop_job = self.root.after(16, self._loop)

    def _update(self) -> None:
        # player movement
        if self.keys["Left"]:
            self.player.x = max(self.player.w / 2, self.player.x - self.player.speed)
        if self.keys["Right"]:
            self.player.x = min(WIDTH - self.player.w / 2, self.player.x + self.player.speed)

        # shooting
        if self.keys["space"] and self.shoot_cooldown <= 0:
            self.bullets.append(Bullet(x=self.player.x, y=self.player.top - 6))
            self.shoot_cooldown = 12
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        # bullets
        for b in self.bullets:
            b.y -= b.speed
        self.bullets = [b for b in self.bullets if b.bottom > 0]

        # enemies
        for e in self.enemies:
            e.y += e.speed
            e.x += e.dx
            if e.left < 0 or e.right > WIDTH:
                e.dx = -e.dx
        # remove off-screen enemies
        for e in list(self.enemies):
            if e.top > HEIGHT:
                self.enemies.remove(e)
                self.player.lives -= 1
                if self.player.lives <= 0:
                    self.game_over = True

        # collisions: bullets vs enemies
        for b in list(self.bullets):
            for e in list(self.enemies):
                if rects_overlap(b, e):
                    self.bullets.remove(b)
                    self.enemies.remove(e)
                    self.score += 10
                    break

        # collisions: player vs enemies
        for e in list(self.enemies):
            if rects_overlap(self.player, e):
                self.enemies.remove(e)
                self.player.lives -= 1
                if self.player.lives <= 0:
                    self.game_over = True

        # level progression
        self.level = 1 + self.score // 100

    def _draw(self) -> None:
        self.canvas.delete("all")

        # stars (simple static-ish background)
        self.canvas.create_text(10, 10, anchor="nw", fill="white",
                               text=f"Score: {self.score}   Lives: {self.player.lives}   Level: {self.level}",
                               font=("Consolas", 12))

        if self.paused and not self.game_over:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2, fill="yellow",
                                   text="PAUSED (P to resume)", font=("Consolas", 24))
            return

        # player
        p = self.player
        self.canvas.create_polygon(
            p.x, p.top, p.right, p.bottom, p.left, p.bottom,
            fill="cyan", outline="white")

        # bullets
        for b in self.bullets:
            self.canvas.create_rectangle(b.left, b.top, b.right, b.bottom,
                                        fill="yellow", outline="")

        # enemies
        for e in self.enemies:
            self.canvas.create_rectangle(e.left, e.top, e.right, e.bottom,
                                        fill="red", outline="white")

        if self.game_over:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 20, fill="red",
                                   text="GAME OVER", font=("Consolas", 36, "bold"))
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 20, fill="white",
                                   text=f"Final score: {self.score}", font=("Consolas", 16))
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 50, fill="white",
                                   text="Press R to restart", font=("Consolas", 14))


def main() -> None:
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
