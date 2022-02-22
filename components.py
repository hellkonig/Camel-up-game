import random

class Board:

    '''
    board object

    input:
      land_len: int
        number of the blocks
    '''
    def __init__(self, land_len):

        self.blocks = [[] for _ in range(land_len)]
        self.spectator_tiles = {}
        self.dices = ['red', 'blue', 'green', 'yellow', 'purple', 'grey']

    def toss_dice(self):

        current_number_of_dices = len(self.dices)
        select_camel_id = random.randint(0, current_number_of_dices - 1)
        step = random.randint(1, 3)

        color = self.dices.pop(select_camel_id)

        return color, step

    def place_camel(self, block_id, camels, forward=True):

        # camels must be list of camle object(s)
        if forward:
            self.blocks[block_id] += camels
        else:
            self.blocks[block_id] = camels + self.blocks[block_id]

        self.update_camels(block_id)

    def update_camels(self, block_id):

        stack_id_ini = 0
        for camel in self.blocks[block_id]:
            camel.block_id = block_id
            camel.stack_id = stack_id_ini
            stack_id_ini += 1

    def select_camel(self, camel):

        block_id = camel.block_id
        stack_id = camel.stack_id

        camel_to_move = self.blocks[block_id][stack_id:]
        self.blocks[block_id] = self.blocks[block_id][:stack_id]
        return camel_to_move

    def place_spectator_tile(self, block_id, side):

        if len(self.block[block_id] != 0):
            print('Place your spectator tile into an empty space.')
        elif ((block_id - 1) in self.spectator_tiles or 
              (block_id + 1) in self.spectator_tiles):
            print('You are not allowed to place the spectator tile'
                  'onto a space that is adjacent to a space containing'
                  'a spectator tile.')
        else:
            self.spectator_tiles[block_id] = side

    def one_leg_reset(self):

        self.spectator_tiles = {}
        self.dices = ['red', 'blue', 'green', 'yellow', 'purple', 'grey']


class Camel:

    '''
    Camel object

    '''
    
    def __init__(self, color, block_id=None, stack_id=None):

        self.color = color
        self.block_id = block_id
        self.stack_id = stack_id