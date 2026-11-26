"""ASCIIテトリス（標準ライブラリ）。

遊び方: A/D または ←/→ 移動、W または ↑ 回転、S または ↓ 加速、
Space 一気に落下、P 一時停止、R 最初から、Q 終了。

【改造の入口 ★★～★★★★】
1. SHAPESでブロックの形を変える、COLS/ROWSで盤面変更。
2. `clear_lines()`の得点、`fall_interval`の落下速度を調整。
3. 次のブロック表示・ホールド機能・特殊ブロックを追加。

既存エンジンには回転、接触、固定、横一列の消去、ゲームオーバーを実装済み。
"""
from __future__ import annotations
import random
import time
from terminal_io import Terminal, paint

COLS, ROWS = 10, 18
LEVEL_STEP_SCORE = 500
# 4x4以内の相対座標。T/J/L/S/Z/I/Oの7種類。
SHAPES = {
    'I': [(0, 1), (1, 1), (2, 1), (3, 1)],
    'O': [(1, 0), (2, 0), (1, 1), (2, 1)],
    'T': [(1, 0), (0, 1), (1, 1), (2, 1)],
    'S': [(1, 0), (2, 0), (0, 1), (1, 1)],
    'Z': [(0, 0), (1, 0), (1, 1), (2, 1)],
    'J': [(0, 0), (0, 1), (1, 1), (2, 1)],
    'L': [(2, 0), (0, 1), (1, 1), (2, 1)],
}


class Tetris:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.board = [[' ' for _ in range(COLS)] for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.next_level_score = LEVEL_STEP_SCORE
        self.status_msg = ''
        self.game_over = False
        self.paused = False
        self.hold_kind = None     
        self.can_hold = True
        self.next_kind = self.rng.choice(list(SHAPES))
        self.spawn()

    def spawn(self):
        self.kind = self.next_kind
        self.next_kind = self.rng.choice(list(SHAPES))
        self.cells = list(SHAPES[self.kind])
        self.x, self.y = COLS // 2 - 2, 0
        self.can_hold = True
        if not self.can_place(self.cells, self.x, self.y):
            self.game_over = True

    def can_place(self, cells, x, y):
        for dx, dy in cells:
            px, py = x + dx, y + dy
            if px < 0 or px >= COLS or py >= ROWS:
                return False
            if py >= 0 and self.board[py][px] != ' ':
                return False
        return True

    def move(self, dx, dy):
        if self.game_over or self.paused:
            return False
        if self.can_place(self.cells, self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            return True
        if dy > 0:
            self.lock()
        return False

    def rotate(self):
        if self.game_over or self.paused or self.kind == 'O':
            return False
        # 座標を90度回転。壁際では1～2マス横へ補正する簡易ウォールキック
        rotated = [(3 - dy, dx) for dx, dy in self.cells]
        for shift in (0, -1, 1, -2, 2):
            if self.can_place(rotated, self.x + shift, self.y):
                self.cells = rotated
                self.x += shift
                return True
        return False

    def hard_drop(self):
        if self.game_over or self.paused:
            return
        while self.can_place(self.cells, self.x, self.y + 1):
            self.y += 1
            self.score += 1
        self.check_level_up()
        self.lock()

    def check_level_up(self):
        while self.score >= self.next_level_score:
            self.level += 1
            self.next_level_score += LEVEL_STEP_SCORE
            self.status_msg = f'★ LEVEL {self.level} UP! (Speed Up!) ★'

    def hold_piece(self):
        if self.game_over or self.paused or not self.can_hold:
            return False
        if self.hold_kind is None:
            self.hold_kind = self.kind
            self.spawn()
        else:
            self.kind, self.hold_kind = self.hold_kind, self.kind
            self.cells = list(SHAPES[self.kind])
            self.x, self.y = COLS // 2 - 2, 0
        self.can_hold = False
        return True
    
    def get_ghost_y(self): 
        ghost_y = self.y
        while self.can_place(self.cells, self.x, ghost_y + 1):
            ghost_y += 1
        return ghost_y

    def format_mini_piece(self, kind): 
        grid = [['  ' for _ in range(4)] for _ in range(2)]
        if kind:
            for dx, dy in SHAPES[kind]:
                if 0 <= dy < 2 and 0 <= dx < 4:
                    grid[dy][dx] = '[]'
        return [''.join(row) for row in grid]
    
    def lock(self):
        for dx, dy in self.cells:
            px, py = self.x + dx, self.y + dy
            if py < 0:
                self.game_over = True
                return
            self.board[py][px] = self.kind
        self.clear_lines()
        self.check_level_up()
        self.spawn()

    def clear_lines(self):
        remaining = [row for row in self.board if ' ' in row]
        removed = ROWS - len(remaining)
        if removed:
            self.board = [[' '] * COLS for _ in range(removed)] + remaining
            self.lines += removed
            gained = (0, 100, 300, 500, 800)[removed] * self.level
            self.score += gained
            self.check_level_up()
        return removed

    @property
    def fall_interval(self):
        return max(0.10, 0.65 - (self.level - 1) * 0.15)

    def render(self):
        screen = [row[:] for row in self.board]
        if not self.game_over:
            ghost_y = self.get_ghost_y()  
            for dx, dy in self.cells:     
                px, py = self.x + dx, ghost_y + dy
                if 0 <= py < ROWS and 0 <= px < COLS:
                    screen[py][px] = 'G'
            for dx, dy in self.cells:
                px, py = self.x + dx, self.y + dy
                if 0 <= py < ROWS and 0 <= px < COLS:
                    screen[py][px] = self.kind

        hold_str = self.hold_kind if self.hold_kind else '-'
        next_view = self.format_mini_piece(self.next_kind)
        remain_score = max(0, self.next_level_score - self.score)

        out = [
            '=== ASCII TETRIS ===',
            f'LV {self.level}    SCORE {self.score}    LINES {self.lines}    HOLD {hold_str}',
            '+' + '--' * COLS + '+',
        ]
        out += ['|' + ''.join('::' if c == 'G' else ('[]' if c != ' ' else '  ') for c in row) + '|' for row in screen]
        out += [
            '+' + '--' * COLS + '+',
            'A/D:移動 W:回転 S:加速 Space:落下 C:ホールド P:停止 R:再開 Q:終了',
            'Next Block:',
            f'  {next_view[0]}',
            f'  {next_view[1]}',
            '------------------------------------',
            f'Next Level (LV {self.level + 1}): あと {remain_score} pts',
        ]
        if self.status_msg:
            out.append(self.status_msg)
        if self.paused:
            out.append('--- PAUSED ---')
        if self.game_over:
            out.append('--- GAME OVER ---  Rで再挑戦 / Qで終了')
        return out


def main():
    game = Tetris()
    with Terminal() as terminal:
        last_fall = time.monotonic()
        while True:
            paint(game.render())
            key = terminal.read_key()
            if key == 'q':
                break
            if key == 'r':
                game.reset()
                last_fall = time.monotonic()
            elif key == 'p':
                game.paused = not game.paused
                last_fall = time.monotonic()
            elif not game.paused and not game.game_over:
                if key in ('a', 'left'):
                    game.move(-1, 0)
                elif key in ('d', 'right'):
                    game.move(1, 0)
                elif key in ('w', 'up'):
                    game.rotate()
                elif key in ('s', 'down'):
                    game.move(0, 1)
                elif key == ' ':
                    game.hard_drop()
                elif key == 'c':       
                    game.hold_piece()
            now = time.monotonic()
            if not game.paused and not game.game_over and now - last_fall >= game.fall_interval:
                game.move(0, 1)
                last_fall = now
            time.sleep(0.035)
    print('テトリスを終了しました。')


if __name__ == '__main__':
    main()
