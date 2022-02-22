import random

from components import Board
from components import Camel

def visualization():

    # board visualization
    for block_id, block in enumerate(board.blocks):
        if len(block) == 0:
            print("%i: []"%block_id)
        else:
            print("%i :["%block_id, end='')
            for camel in block:
                print("%s, "%camel.color, end='')
            print("]")

    # camel status
    for color in camels:
        print("%s: %i, %i"%(color, 
                            camels[color].block_id, 
                            camels[color].stack_id))

def camel_initialization(board, camels, color, step):
    camels[color] = Camel(color, block_id=step - 1)
    board.place_camel(step - 1, [camels[color]])
    return board, camels

def if_crazy_camel_alone(crazy_camel):
    block_id = crazy_camel.block_id
    stack_id = crazy_camel.stack_id
    camels_on_back = board.blocks[block_id][stack_id:]
    for camel in camels_on_back:
        if camel.color != 'white' or camel.color != 'black':
            return False
    return True

def crazy_camel_move(step):
    if_white_alone = if_crazy_camel_alone(camels['white'])
    if_black_alone = if_crazy_camel_alone(camels['black'])
    if if_black_alone == if_white_alone:
        color = crazy_camel_set[random.randint(0,1)]
    elif if_black_alone:
        color = 'white'
    elif if_white_alone:
        color = 'black'
    step = -step
    return color, step

if __name__ == "__main__":

    ### game setting ###

    LAND_LEN = 17


    ### initialize the game ###

    # board
    board = Board(land_len=LAND_LEN)

    # camels
    numbers_of_camels = len(board.dices)
    camels = {}
    for _ in range(numbers_of_camels):
        color, step = board.toss_dice()
        if color != 'grey':
            board, camels = camel_initialization(board, camels, color, step)
        else:
            # 0 for white and 1 for black
            crazy_camel_set = {0: 'white', 1: 'black'}

            first_crazy_camel_id = random.randint(0,1)
            color = crazy_camel_set[first_crazy_camel_id]
            step = LAND_LEN - step
            board, camels = camel_initialization(board, camels, color, step)

            second_crazy_camel_id = abs(1 - first_crazy_camel_id)
            color = crazy_camel_set[second_crazy_camel_id]
            step = LAND_LEN - random.randint(1, 3)
            board, camels = camel_initialization(board, camels, color, step)

    # reset dices
    board.one_leg_reset()

    # visualize the board
    visualization()

    ### Game running ###

    while True:
        color, step = board.toss_dice()

        if color == 'grey':
            color, step = crazy_camel_move(step)

        print("%s camel move %i step(s)..."%(color, step))

        camel_to_move = board.select_camel(camels[color])
        target_block_id = min(camels[color].block_id + step,
                              LAND_LEN - 1)
        board.place_camel(target_block_id, camel_to_move)

        if target_block_id == LAND_LEN - 1:
            break

        visualization()
        input("Press the <ENTER> key to continue...")

        if len(board.dices) == 1:
            board.one_leg_reset()
            print('One leg finished...')
            print('-------------------------------')

    visualization()