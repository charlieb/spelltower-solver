import datrie
import string
import random
from copy import deepcopy
from curses import wrapper, A_REVERSE, curs_set

LOG = open('log', 'w')

def filter_dict_into_trie(words, trie):
    lowercase_letters = set(string.ascii_lowercase)
    for line in words:
        line = line[:-1]
        # exclude proper nouns and punctuation
        # and words of 2 letters and less
        if len(line) <= 2 and not set(line).issubset(lowercase_letters):
            continue
        trie[line] = 1
    return trie

def build_trie(dict_file = '/usr/share/dict/words'):
    trie = datrie.BaseTrie(string.ascii_lowercase)
    with open(dict_file, 'r') as words:
        filter_dict_into_trie(words, trie)
    return trie

def random_letter():
    return random.choice(string.ascii_lowercase + '*')

class Word:
    def __init__(self, dictionary, grid):
        self.grid = grid
        self.coords = []
        self.trie = dictionary
        self.tried_coords = []
    def __len__(self): return len(self.coords)
    def clear_tries(self):
        self.tried_coords = []
    def push(self, x,y):
        if len(self.coords) == 0 or \
                ((abs(x - self.coords[-1][0]) <= 1 and abs(y - self.coords[-1][1]) <= 1) and not \
                 (x == self.coords[-1][0] and y == self.coords[-1][1])):
            self.coords.append((x,y))
            self.tried_coords.append((x,y))
    def pop(self):
        self.coords = self.coords[:-1]
    def letters(self):
        return ''.join([self.grid[coord] for coord in self.coords])
    def tried(self, coord):
        for c in self.tried_coords:
            if c == coord:
                return True
        return False
    def member(self, coord):
        for c in self.coords:
            if c == coord:
                return True
        return False
    def is_valid_or_prefix(self):
        return self.trie.has_keys_with_prefix(self.letters())
    def is_valid(self):
        return len(self.coords) >= 3 and self.letters() in self.trie

class Grid:
    def __init__(self, dictionary, x=8,y=12):
        self.grid = []
        self._random_grid(x,y)
        self.x, self.y = x,y
        self.dictionary = dictionary
    def _valid_neighbours(self, coords):
        (i,j) = coords
        return [(x,y) for (x,y) in
                [(i-1,j-1), (i-1,j), (i,j-1),
                 # (i,j),
                 (i,j+1), (i+1,j), (i+1, j+1)] 
                if 0 <= x < self.x and 0 <= y < self.y]

    def _random_grid(self, x,y):
        # 8x12
        self.grid = []
        for _ in range(y):
            row = []
            for _ in range(x):
                row.append(random_letter())
            self.grid.append(row)
    def __getitem__(self, coords):
        return self.grid[coords[1]][coords[0]]
    def __setitem__(self, coords, letter):
        self.grid[coords[1]][coords[0]] = letter
    def __repr__(self):
        return '\n'.join(['  '.join(row) for row in self.grid]) 
    def _words_r(self, word, words):
        for (x,y) in self._valid_neighbours(word.coords[-1]):
            # don't use an already visited letter
            if not word.member((x,y)):
                # add a new letter
                word.push(x,y)
                # check that the letter makes a potentially valid word
                if word.is_valid_or_prefix():
                    # if it's a word, add it
                    if word.is_valid():
                        words.append(deepcopy(word))
                    # try adding more letters
                    self._words_r(word, words)
                # remove the added letter and keep looking
                word.pop()
            
    def find_words(self):
        words = []
        for i in range(self.x):
            for j in range(self.y):
                word = Word(self.dictionary, self)
                word.push(i,j)
                self._words_r(word, words)
        return words
    def clear(self):
        for i in range(self.x):
            for j in range(self.y):
                self[(i,j)] = ' '
    def apply_gravity(self):
        for j in range(self.y-1, -1, -1):
            for i in range(self.x):
                if self[(i,j)] == ' ':
                    print('%s, %s'%(i,j), file=LOG)
                    for up in range(j, -1, -1):
                        if self[(i, up)] != ' ':
                            print('move %s,%s -> %s, %s'%(i,j,i,up), file=LOG)
                            self[(i,j)] = self[(i,up)]
                            self[(i,up)] = ' '
                            break
    def eliminate_word(self, word):
        for coord in word.coords:
            self[coord] = ' '
            # eliminate cardinal neighbours
            for (x,y) in self._valid_neighbours(coord):
                if len(word.coords) > 4 or self[(x,y)] == '*':
                    self[(x,y)] = ' '
        self.apply_gravity()
        

class GridUI:
    def __init__(self, grid, stdscr):
        self.grid = grid
        self.stdscr = stdscr
        self.word = False
        self.words = []
        self._regen_wordlist()
        curs_set(False)
    def _regen_wordlist(self):
        self.word = 0
        self.words = sorted(self.grid.find_words(), key=len, reverse=True)[0:10]
    def mainloop(self):
        self.update()
        while True:
            key = self.stdscr.getkey()

            self.stdscr.addstr(18, 0, key)
            if key == "e" or key == "E":
                if len(self.words) > 0:
                    self.grid.eliminate_word(self.words[self.word])
                self._regen_wordlist()
            elif key == 'r' or key == 'R':
                self._regen_wordlist()
            elif key == 'q' or key == 'Q':
                return
            elif key == 'n' or key == 'N':
                self.editloop()
            elif key == 'KEY_UP':
                self.word = self.word - 1 if self.word > 0 else len(self.words)-1
            elif key == 'KEY_DOWN':
                self.word = self.word + 1 if self.word < len(self.words)-1 else 0

            self.update(key=key)
    def editloop(self):
        self.grid.clear()
        self.words = []
        self.word = -1 # turn off word hilighing
        self.update()
        i, j = 0,0
        while True:
            i = 0
            while i < self.grid.x:
                self.update()
                self.stdscr.addstr(16, 0, "Enter letters, use arrow keys, then hit (End)                                              ")
                self.stdscr.addstr(j,i*2, self.grid[(i,j)], A_REVERSE)

                key = self.stdscr.getkey()
                if key in set(string.ascii_lowercase + '*' + ' '):
                    self.grid[(i,j)] = key
                    i +=1
                elif key == 'KEY_LEFT':
                    i = i-1 if i > 0 else i
                elif key == 'KEY_RIGHT':
                    i = i+1 if i+1 < self.grid.x else i
                elif key == 'KEY_UP':
                    j = j-1 if j > 0 else j
                elif key == 'KEY_DOWN':
                    j = j+1 if j+1 < self.grid.y else j
                elif key == 'KEY_END':
                    self.grid.apply_gravity()
                    return

            j = j+1 if j+1 < self.grid.y else j



    def update(self, key=''):
        self.stdscr.clear()
        for i in range(self.grid.x):
            for j in range(self.grid.y):
                self.stdscr.addstr(j, i*2, '%s '%(self.grid[(i,j)]))
        self.show_wordlist()
        self.show_promptline()
        self.stdscr.addstr(18, 0, key)
        self.stdscr.refresh()

    def show_promptline(self):
        self.stdscr.addstr(16, 0, "(R)egenerate Wordlist, (E)liminate Word, (Up/Down) Select Word, (N)ew Tower, (Q)uit")
    def show_wordlist(self):
        if len(self.words) <= 0: return
        for i in range(len(self.words)):
            self.stdscr.addstr(i, 16, '| ' + self.words[i].letters())

        if self.word >= 0:
            self.stdscr.addstr(self.word, 18, self.words[self.word].letters(), A_REVERSE)
            for coord in self.words[self.word].coords:
                self.stdscr.addstr(coord[1], coord[0]*2, '%s '%(self.grid[coord]), A_REVERSE)


        
        

def main(stdscr):
    trie = build_trie(dict_file = '/usr/share/dict/cracklib-small')
    grid = Grid(trie)
    ui = GridUI(grid, stdscr)
    ui.mainloop()

if __name__ == "__main__":
    wrapper(main)
