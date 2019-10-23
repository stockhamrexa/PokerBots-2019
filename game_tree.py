from deuces import Card
from deuces import Evaluator

"""
This file is used to test recursive game tree creation and chance node propagation used in CFR. It does not do anything
for the actual game.
"""

action_buckets=['0', '1', '2', '3', '4', '5', '6'] #The seven possible game actions to be taken

def main():
    history=[]
    hole_cards_1=["Ah", "As"] #Random hole cards
    hole_cards_2=["9s", "2c"] #Random hole cards
    board_cards=["Ad", "Kc", "Kh"] #Random hole cards
    generate_game_tree(history, hole_cards_1, hole_cards_2, board_cards)

def generate_game_tree(history, hole_cards_1, hole_cards_2, board_cards, pot_size=3, contrib_1=1, contrib_2=2, pr_1=1.0, pr_2=2.0, pr_c=3.0):
    """
    This function generates the game tree when called. History is the list containing all moves made up to this point, hole cards 1 and 2 are the
    hole cards being held by each player, pot_size is how much money is in the pot, contrib 1 and 2 are how much each player has contributed to the
    pot, pr_1 and pr_2 are the probabilities that each player reaches this point in the game history, and pr_c is the probability that the chance
    nodes lead us to this point in the game history.
    """
    if is_chance_node(history): #If it is the start of a hand or the end of a round of betting, time to deal cards
        return get_chance_util(history, hole_cards_1, hole_cards_2, board_cards, pot_size, contrib_1, contrib_2, pr_1, pr_2, pr_c)

    if is_terminal_node(history): #If the hand ended
        return get_terminal_util(history, hole_cards_1, hole_cards_2, board_cards, pot_size, contrib_1)

    is_sb=get_is_sb(history) #Is it the small blinds turn to bet

    for action in action_buckets: #Loop through all actions
        if is_legal_move(history, action, pot_size, contrib_1, contrib_2, is_sb): #If the action is legal
            if is_sb: #If the small blind is going
                next_history = history[:]
                next_history.append(action)
                new_pot = get_new_pot(action, pot_size, contrib_1, contrib_2, is_sb)
                generate_game_tree(next_history, hole_cards_1, hole_cards_2, board_cards, new_pot[0], new_pot[1], new_pot[2], pr_1, pr_2, pr_c)
            else: #If the big blind is going
                next_history = history[:]
                next_history.append("-"+action)
                new_pot = get_new_pot(action, pot_size, contrib_1, contrib_2, is_sb)
                generate_game_tree(next_history, hole_cards_1, hole_cards_2, board_cards, new_pot[0], new_pot[1], new_pot[2], pr_1, pr_2, pr_c)

def is_chance_node(history):
    """
    Takes in a game history and determines whether or not the next node is a chance node.
    """
    if len(history)==0: #If the hole cards have not been dealt yet
        return True
    if not is_river(history) and is_betting_over(history): #If a round of betting is over and it is not the river
        return True
    else:
        return False

def is_terminal_node(history):
    """
    Takes in a game history and determines whether or not it is a terminal node.
    """
    if history[-1]=="0" or history[-1]=="-0": #Last move was a fold (negative indicates move by big blind)
        return True
    elif is_river(history): #If the game didnt end on a fold it is only a terminal node at the river
        if is_betting_over(history):
            return True
        else:
            return False
    else:
        return False

def get_chance_util(history, hole_cards_1, hole_cards_2, board_cards, pot_size, contrib_1, contrib_2, pr_1, pr_2, pr_c):
    """
    Returns the chance utility at chance nodes. Enumerates through all possible outcomes of the given chance node.
    """
    new_history=history+["r", "r"]
    return generate_game_tree(new_history, hole_cards_1, hole_cards_2, board_cards, pot_size, contrib_1, contrib_2, pr_1, pr_2, pr_c)

def get_terminal_util(history, hole_cards_1, hole_cards_2, board_cards, pot_size, contrib_1):
    """
    Returns the utility whenever a hand is over.
    """
    if history[-1]=="-0": #If the big blind folded
        return pot_size-contrib_1
    elif history[-1]=="0": #If the small blind folded
        return -(contrib_1)
    else: #If it went to a showdown
        strength_difference=get_strength_difference(hole_cards_1, hole_cards_2, board_cards)
        if strength_difference>0: #If the small blind won
            return pot_size-contrib_1
        elif strength_difference<0: #If the small blind lost
            return -(contrib_1)
        else: #The small blind and big blind tied
            return 0

def get_is_sb(history):
    """
    Returns whether or not it is the small blinds turn to bet or the big blinds. Accounts for the change in the order of
    betting after the preflop betting round as well as possible double actions such as check-check and check-call.
    """
    if is_preflop(history):
        if history[-2:] == ["r", "r"]:  # Small blind always bets first preflop
            return True
        if history==["r", "r", "2", "-1"]: #If it is the preflop and the small blind calls then the big blind checks, the big blind gets to go again for a check-check
            return False
        if history==["r", "r", "3", "-2"] or history==["r", "r", "4", "-2"]: #After an initial preflop raise by the small blind and a call by the big blind, the big blind can call-check
            return False
        else:
            return "-" in history[-1] #If it is none of the above scenarios, the small blind gets to go if the big blind just went
    else:
        if history[-2:] == ["r", "r"]:  # Big blind always bets first postflop
            return False
        if not is_river(history): #Not the preflop and not the river
            if history[-5:]==["r", "r", "-1", "5", "-2"] or history[-5:]==["r", "r", "-1", "6", "-2"]: #If the big blind checks then the small blind bets then the big blind calls you can call-check
                return False
            if history[-7:]==["r", "r", "-1", "5", "-3", "3", "-2"]: #All of the following if statements are variations of the check, bet, raise, raise, call combo
                return False
            if history[-7:]==["r", "r", "-1", "5", "-3", "4", "-2"]:
                return False
            if history[-7:]==["r", "r", "-1", "5", "-4", "3", "-2"]:
                return False
            if history[-7:]==["r", "r", "-1", "5", "-4", "4", "-2"]:
                return False
            if history[-7:]==["r", "r", "-1", "6", "-3", "3", "-2"]:
                return False
            if history[-7:]==["r", "r", "-1", "6", "-3", "4", "-2"]:
                return False
            if history[-7:]==["r", "r", "-1", "6", "-4", "3", "-2"]:
                return False
            if history[-7:]==["r", "r", "-1", "6", "-4", "4", "-2"]:
                return False
        return "-" in history[-1] #If it is none of the above scenarios, the small blind gets to go if the big blind just went

def is_betting_over(history):
    """
    Takes in a game history and determines whether or not the round of betting is over.
    """
    if history[-2:]==["1", "-1"] or history[-2:]==["-1", "1"]: #If the last two moves of the game were checks
        return True
    elif is_river(history):
        if history[-1]=="2" or history[-1]=="-2": #Betting is over in the river if someone calls
            return True
    else:
        return False

def is_preflop(history):
    """
    Takes in a game history and returns whether or not it is the preflop based on the number of chance nodes. Chance nodes
    are represented as "r".
    """
    return history.count("r")==2 #Two chance nodes at the start of the game and two each time new board cards are played

def is_flop(history):
    """
    Takes in a game history and returns whether or not it is the flop based on the number of chance nodes. Chance nodes
    are represented as "r".
    """
    return history.count("r")==4 #Two chance nodes at the start of the game and two each time new board cards are played

def is_turn(history):
    """
    Takes in a game history and returns whether or not it is the turn based on the number of chance nodes. Chance nodes
    are represented as "r".
    """
    return history.count("r")==6 #Two chance nodes at the start of the game and two each time new board cards are played

def is_river(history):
    """
    Takes in a game history and returns whether or not it is the river based on the number of chance nodes. Chance nodes
    are represented as "r".
    """
    return history.count("r")==8 #Two chance nodes at the start of the game and two each time new board cards are played

def is_legal_move(history, action, pot_size, contrib_1, contrib_2, is_sb):
    """
    Returns whether or not a given action is legal at this point in the game. Takes in a game history and the same
    other parameters as get_new_pot.
    """
    if action=="0": #Fold
        if is_preflop(history): #Checks first actions in preflop
            if is_sb:
                if history == ['r', 'r']:  #Folding is always allowed as the first move of preflop
                    return True
            else:
                if history[:2] == ['r', 'r'] and len(history)==3:  #Folding is always allowed as the first move of preflop regardless of small blinds action
                    return True
        if is_sb:
            if history[-1]=="-3" or history[-1]=="-4" or history[-1]=="-5" or history[-1]=="-6": #If the last move was a raise or a bet
                return True
            else:
                return False
        else:
            if history[-1]=="3" or history[-1]=="4" or history[-1]=="5" or history[-1]=="6": #If the last move was a raise or a bet
                return True
            else:
                return False

    elif action=="1": #Check or exchange
        if history[-1]=="1" or history[-1]=="-1": #If another player or you just checked, allows for check-check scenarios
            return True
        if history[-1] == "2" or history[-1] == "-2":  # Always able to check after a call and allows for a call-check
            return True
        if not is_preflop(history):
            if is_sb:
                if history[-3:]==["r", "r", "-1"]: #If it is the small blinds first move in a postflop round of betting and the big blind just checked
                    return True
            else:
                if history[-2:]==["r", "r"]: #If it is the big blinds first move in a postflop round of betting
                    return True
        if is_preflop(history):
            if not is_sb:
                if history==["r", "r", "2"]: #If the small blind opened with a call preflop the big blind can check (Sets up check-check scenario)
                    return True

    elif action=="2": #Call
        if is_sb:
            if history == ["r", "r"]:  # The small blind is allowed to call on their first action preflop since they only bet 1
                return True
            if history[-1]=="-3" or history[-1]=="-4" or history[-1]=="-5" or history[-1]=="-6": #If the last move was a raise or a bet
                return True
            else:
                return False
        else:
            if history[-1]=="3" or history[-1]=="4" or history[-1]=="5" or history[-1]=="6": #If the last move was a raise or a bet
                return True
            else:
                return False

    elif action=="3": #Raise half pot
        if is_preflop(history):
            if is_sb:
                if history == ['r', 'r']:  # Raising is always allowed as the first move of preflop
                    return True
            else:
                if history[:2] == ['r', 'r'] and len(history)==3:  #Raising is always allowed as the first move of preflop for the big blind regardless of the small blinds first action
                    return True
        if is_sb:
            cost=int(.5*pot_size)+(pot_size-contrib_1) #Cost to call plus half of the pot
            if cost<=400: #Cannot bet more than 400 in a round
                if num_bets(history, is_sb)<2: #No more than two bets or raises in a given round
                    if history[-1]=="-3" or history[-1]=="-4" or history[-1]=="-5" or history[-1]=="-6": #If the last action by the opponent was a bet or raise
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False
        else:
            cost=int(.5*pot_size)+(pot_size-contrib_2) #Cost to call plus half of the pot
            if cost<=400: #Cannot bet more than 400 in a round
                if num_bets(history, is_sb)<2: #No more than two bets or raises in a given round
                    if history[-1]=="3" or history[-1]=="4" or history[-1]=="5" or history[-1]=="6": #If the last action by the opponent was a bet or raise
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

    elif action=="4": #Raise full pot
        if is_preflop(history):
            if is_sb:
                if history == ['r', 'r']:  # Raising is always allowed as the first move of preflop
                    return True
            else:
                if history[:2] == ['r', 'r'] and len(history)==3:  #Raising is always allowed as the first move of preflop for the big blind regardless of the small blinds first action
                    return True
        if is_sb:
            cost=pot_size+(pot_size-contrib_1) #Cost to call plus half of the pot
            if cost<=400: #Cannot bet more than 400 in a round
                if num_bets(history, is_sb)<2: #No more than two bets or raises in a given round
                    if history[-1]=="-3" or history[-1]=="-4" or history[-1]=="-5" or history[-1]=="-6": #If the last action by the opponent was a bet or raise
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False
        else:
            cost=pot_size+(pot_size-contrib_2) #Cost to call plus half of the pot
            if cost<=400: #Cannot bet more than 400 in a round
                if num_bets(history, is_sb)<2: #No more than two bets or raises in a given round
                    if history[-1]=="3" or history[-1]=="4" or history[-1]=="5" or history[-1]=="6": #If the last action by the opponent was a bet or raise
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False

    elif action=="5": #Bet half pot
        if not is_preflop(history): #You cannot bet in the preflop
            if is_sb:
                cost=int(.5*pot_size)+contrib_1
                if cost<=400: #You cannot bet more then 400 in a round
                    if history[-1]=="-1" and history[-2]=="r": #Betting is only allowed at the start of a round and small blind bets second so big blind must have checked
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                cost=int(.5*pot_size)+contrib_2
                if cost<=400: #You cannot bet more then 400 in a round
                    if history[-2:]==["r", "r"]: #If it is the first chance for the big blind to bet in a round
                        return True
                    else:
                        return False
                else:
                    return False
        else:
            return False

    else: #Bet full pot
        if not is_preflop(history): #You cannot bet in the preflop
            if is_sb:
                cost=pot_size+contrib_1
                if cost<=400: #You cannot bet more then 400 in a round
                    if history[-1]=="-1" and history[-2]=="r": #Betting is only allowed at the start of a round and small blind bets second so big blind must have checked
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                cost=pot_size+contrib_2
                if cost<=400: #You cannot bet more then 400 in a round
                    if history[-2:]==["r", "r"]: #If it is the first chance for the big blind to bet in a round
                        return True
                    else:
                        return False
                else:
                    return False
        else:
            return False

def get_new_pot(action, pot_size, contrib_1, contrib_2, is_sb):
    """
    Takes in information about the pot and returns all new pot information given the action being taken. Action is the
    action being taken, pot_size is how large the pot is, contrib 1 and 2 are how much each player has added to the pot
    and is_sb is whether or not it is the small blinds turn.
    """
    if action=="0" or action=="1": #Fold, check
        return (pot_size, contrib_1, contrib_2) #These actions cost nothing

    if action=="2": #Calling
        if is_sb:
            cost = contrib_2 - contrib_1  # Cost to call
            return (pot_size+cost, contrib_1+cost, contrib_2)
        else:
            cost = contrib_1 - contrib_2  # Cost to call
            return (pot_size+cost, contrib_1, contrib_2+cost)

    if action=="3": #Raise half the pot
        if is_sb:
            cost=int(.5*pot_size)+(contrib_2-contrib_1) #The amount to call the pot plus half of the pot size
            return (pot_size+cost, contrib_1+cost, contrib_2)
        else:
            cost = int(.5 * pot_size) + (contrib_1 - contrib_2)  #The amount to call the pot plus half of the pot size
            return (pot_size+cost, contrib_1, contrib_2+cost)

    if action=="4": #Raise the full pot
        if is_sb:
            cost=pot_size+(contrib_2-contrib_1) #The amount to call the pot plus the pot size
            return (pot_size+cost, contrib_1+cost, contrib_2)
        else:
            cost=pot_size+(contrib_2-contrib_1) #The amount to call the pot plus the pot size
            return (pot_size+cost, contrib_1, contrib_2+cost)

    if action=="5": #Bet half the pot
        if is_sb:
            cost = int(.5 * pot_size)  # Half of the pot size
            return (pot_size + cost, contrib_1 + cost, contrib_2)
        else:
            cost = int(.5 * pot_size)  # Half of the pot size
            return (pot_size + cost, contrib_1, contrib_2+cost)

    if action=="6": #Bet the full pot
        if is_sb:
            cost = pot_size  # The full pot size
            return (pot_size + cost, contrib_1 + cost, contrib_2)
        else:
            cost = pot_size  # The full pot size
            return (pot_size + cost, contrib_1, contrib_2+cost)

def get_hand_strength(hole_cards, board_cards):
    """
    Takes in hole cards and board cards and returns the hand strength.
    """
    evaluator=Evaluator()
    hole=[Card.new(hole_cards[0]), Card.new(hole_cards[1])]
    board=[]
    for card in board_cards:
        board.append(Card.new(card))
    strength=(7643-evaluator.evaluate(hole, board))/float(7642)
    return strength

def get_strength_difference(hole_cards_1, hole_cards_2, board_cards):
    """
    Takes in the hole cards and the board cards and returns the difference in hand strength between player one and
    player two.
    """
    evaluator=Evaluator()
    hole_1=[Card.new(hole_cards_1[0]), Card.new(hole_cards_1[1])]
    hole_2=[Card.new(hole_cards_2[0]), Card.new(hole_cards_2[1])]
    board=[]
    for card in board_cards:
        board.append(Card.new(card))
    strength_1=(7643-evaluator.evaluate(hole_1, board))/float(7642)
    strength_2=(7643-evaluator.evaluate(hole_2, board))/float(7642)
    return strength_1-strength_2

def num_bets(history, is_sb):
    """
    Returns the number of times you have bet/ raised in the current stage of the game.
    """
    reverse_history=history[::-1] #Reverses the history
    i=reverse_history.index("r")
    betting_round=history[len(history)-i:]
    if is_sb:
        total=betting_round.count("3")+betting_round.count("4")+betting_round.count("5")+betting_round.count("6")
    else:
        total=betting_round.count("-3")+betting_round.count("-4")+betting_round.count("-5")+betting_round.count("-6")
    return total

if __name__=="__main__":
    main()
