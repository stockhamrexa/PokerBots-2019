from deuces import Card
from deuces import Evaluator
import json
from pokerbots import Bot, parse_args, run_bot
from pokerbots.actions import FoldAction, CallAction, CheckAction, BetAction, RaiseAction, ExchangeAction
import random

try: #Tries to import the C library first
    from pbots_calc import calc
except ImportError: #If it cannot, imports the local python library
    from equity_calc import calc

suits = ['c', 'd', 'h', 's']
counts = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

action_buckets=['0', '1', '2', '3', '4', '5', '6'] #The seven possible game actions to be taken
preflop_buckets=['0', '1', '2', '3', '4', '5'] #The six possible buckets preflop hands can fall into
postflop_buckets=['0', '1', '2', '3', '4'] #The five possible buckets postflop hands can fall into

"""
This bot utilizes counterfactual regret minimization. Preflop hands are bucketed according to type (pocket pairs, suited connectors, 
unsuited connectors, suited, unsuited close, and unsuited far). Postflop hands are bucketed into five categories by hand strength. 
Actions are bucketed from 0 to 6 (Fold, Check/Exchange, Call, Raise half pot, Raise full pot, "Bet half pot, Bet full pot). Betting is 
truncated to one bet by each player per round of betting and no exchanges may occur in the preflop. If a game state cannot be found in
the map of strategy distributions, the bot will play heuristically for the rest of the hand. If we reach a certain threshold above the 
opponent, we will check-fold the rest of the game.
"""

class Player(Bot):
    def handle_new_game(self, new_game):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        new_game: the pokerbots.Game object.

        Returns:
        Nothing.
        '''
        filename = "game_strategies_json"  # The file that holds the strategy distributions
        file = open(filename, "r")
        self.i_map = json.load(file)
        file.close()

        self.player_name=new_game.name #Your players name
        self.opponent_name=new_game.opponent_name #Opponents name
        self.check_fold=False #Should we check/fold the rest of the game

    def handle_new_round(self, game, new_round):
        '''
        Called when a new round starts. Called Game.num_rounds times.

        Arguments:
        game: the pokerbots.Game object for the new round.
        new_round: the new pokerbots.Round object.

        Returns:
        Nothing.
        '''
        self.num_cards=None #The number of board cards dealt. None at the start of each game and zero once hole cards have been dealt
        self.agression=random.random() #Sets a random agression level for the round
        self.just_exchanged=False #Was our last move an exchange
        self.discarded_cards=[] #All cards discarded during the round
        self.hand_strength=0 #Starting hand strength
        self.card_buckets="" #The combination of buckets that your cards fall into
        self.history=[] #The running game history

    def handle_round_over(self, game, round, pot, cards, opponent_cards, board_cards, result, new_bankroll, new_opponent_bankroll, move_history):
        '''
        Called when a round ends. Called Game.num_rounds times.

        Arguments:
        game: the pokerbots.Game object.
        round: the pokerbots.Round object.
        pot: the pokerbots.Pot object.
        cards: the cards you held when the round ended.
        opponent_cards: the cards your opponent held when the round ended, or None if they never showed.
        board_cards: the cards on the board when the round ended.
        result: 'win', 'loss' or 'tie'
        new_bankroll: your total bankroll at the end of this round.
        new_opponent_bankroll: your opponent's total bankroll at the end of this round.
        move_history: a list of moves that occurred during this round, earliest moves first.

        Returns:
        Nothing.
        '''
        print("")

    def get_action(self, game, round, pot, cards, board_cards, legal_moves, cost_func, move_history, time_left, min_amount=None, max_amount=None):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the server needs an action from your bot.

        Arguments:
        game: the pokerbots.Game object.
        round: the pokerbots.Round object.
        pot: the pokerbots.Pot object.
        cards: an array of your cards, in common format.
        board_cards: an array of cards on the board. This list has length 0, 3, 4, or 5.
        legal_moves: a set of the move classes that are legal to make.
        cost_func: a function that takes a move, and returns additional cost of that move. Your returned move will raise your pot.contribution by this amount.
        move_history: a list of moves that have occurred during this round so far, earliest moves first.
        time_left: a float of the number of seconds your bot has remaining in this match (not round).
        min_amount: if BetAction or RaiseAction is valid, the smallest amount you can bet or raise to (i.e. the smallest you can increase your pip).
        max_amount: if BetAction or RaiseAction is valid, the largest amount you can bet or raise to (i.e. the largest you can increase your pip).
        '''
        if self.check_fold==False: #Check to see if the value of self.checkfold has changed
            self.check_fold=self.will_win(game, round)

        if self.check_fold==True: #See if we should play a checkfold strategy the rest of the game
            return self.play_checkfold(legal_moves)

        if self.just_exchanged==True: #If we just exchanged, update our hand strength and self.card_buckets
            if not self.is_preflop(board_cards):
                self.hand_strength=self.get_deuces_hand_strength(cards, board_cards)

        if self.num_cards==None: #The start of a new hand
            self.num_cards=0
            self.hand_strength=self.get_calc_hand_strength(cards, board_cards, self.discarded_cards)
            self.card_buckets+=self.bucket_cards(cards, board_cards, self.hand_strength)

        if len(board_cards)!=self.num_cards: #Every time new cards are dealt after the preflop
            self.num_cards=len(board_cards)
            self.hand_strength = self.get_deuces_hand_strength(cards, board_cards)
            self.card_buckets += self.bucket_cards(cards, board_cards, self.hand_strength)

        self.update_history(cards, board_cards, round, move_history)

        strategy=self.get_strategy_distribution(self.history)

        if strategy!=None:
            action_vector=self.get_action_vector(legal_moves) #Get an action vector for all possible legal moves
            action=self.choose_action(strategy, action_vector) #Select a move to play
            if action==None: #If none of the actions were selected from the strategy profile, play the average strategy
                hand_strength = self.get_calc_hand_strength(cards, board_cards, self.discarded_cards)  # Get a hand strength that takes discarded cards into account
                return self.play_heuristic(cards, board_cards, pot, legal_moves, cost_func, min_amount, max_amount, hand_strength)
            else:
                return self.play_strategy(action, cards, board_cards, legal_moves, pot, cost_func, min_amount, max_amount, self.hand_strength)
        else: #If there is no strategy for this game history or if it is a randomized strategy distribution, play heuristically
            hand_strength=self.get_calc_hand_strength(cards, board_cards, self.discarded_cards) #Get a hand strength that takes discarded cards into account
            print("No strategy")
            print(self.get_strategy_distribution(self.history))
            print(self.history, self.card_buckets)
            return self.play_heuristic(cards, board_cards, pot, legal_moves, cost_func, min_amount, max_amount, hand_strength)

    def is_preflop(self, board_cards):
        """
        Checks whether we are pre-flop or post-flop
        """
        return len(board_cards)==0

    def is_flop(self, board_cards):
        """
        Checks whether we are in the flop
        """
        return len(board_cards)==3

    def is_turn(self, board_cards):
        """
        Checks whether we are in the turn
        """
        return len(board_cards)==4

    def is_river(self, board_cards):
        """
        Checks whether we are in the river
        """
        return len(board_cards)==5

    def get_calc_hand_strength(self, cards, board_cards, discarded_cards):
        """
        Gets the effective hand strength of your cards at any stage of the game using the pbots_calc library.
        """
        if calc is not None:
            result = calc(''.join(cards) + ':xx', ''.join(board_cards), ''.join(discarded_cards), 1000)
            if result is not None:
                strength = result.ev[0]
            else:
                strength = random.random()
        else:
            strength = random.random()
        return strength

    def get_deuces_hand_strength(self, cards, board_cards):
        """
        Gets the effective hand strength of your cards at any stage of the game using the deuces library.
        """
        evaluator=Evaluator()
        hole=[Card.new(cards[0]), Card.new(cards[1])] #Turns cards and board cards into deuces.Card objects
        board=[]
        for card in board_cards:
            board.append(Card.new(card))
        return (7643-evaluator.evaluate(hole, board))/float(7642) #Turns the hand strength into a decimal in the range of 0-1

    def bucket_cards(self, cards, board_cards, hand_strength):
        """
        Takes in a players cards, the board cards, and the hand strength and puts their hand into a bucket.
        """
        if len(board_cards)==0: #If it is preflop, use preflop buckets
            suit1 = cards[0][1]
            suit2 = cards[1][1]
            value1 = cards[0][0]
            value2 = cards[1][0]
            if value1 == value2:  #Pocket pairs
                return "0"
            elif suit1 == suit2:
                if abs(counts.index(value1) - counts.index(value2)) == 1:  #Suited connectors
                    return "1"
                else: #Suited
                    return "3"
            else:
                if abs(counts.index(value1) - counts.index(value2)) == 1:  #Unsuited connectors
                    return "2"
                else:
                    if abs(counts.index(value1) - counts.index(value2)) <= 4:  #Unsuited close
                        return "4"
                    else:  #Unsuited far
                        return "5"
        else: #Use postflop buckets
            if hand_strength <= .2:
                return "0"
            elif hand_strength > .2 and hand_strength <= .4:
                return "1"
            elif hand_strength > .4 and hand_strength <= .6:
                return "2"
            elif hand_strength > .6 and hand_strength <= .8:
                return "3"
            else:
                return "4"

    def add_chance_nodes(self, history):
        """
        Called any time cards are dealt. Adds two chance nodes to the game history, one for each player.
        """
        history+=["r", "r"]
        return history

    def get_strategy_distribution(self, history):
        """
        Looks up the game history in i_map. Returns none if it cannot be found or if it returns a randomized strategy distribution.
        """
        key="("+self.card_buckets+")"+"".join(history)
        try:
            strategy=self.i_map[key] #Gets the strategy distribution
            non_zero=[i for i in strategy if i>0]
            if len(non_zero)==1: #If only one action is available return the strategy distribution
                return strategy
            for i in range(1, len(non_zero)): #If all of the non-zero numbers are not the same
                if non_zero[i]!=non_zero[i-1]:
                    return strategy
            return None
        except KeyError:
            return None

    def get_action_vector(self, legal_moves):
        """
        Returns an action vector mapping moves in the action_buckets list to whether or not they are in legal_moves
        """
        action_vector=[False, False, False, False, False, False, False]
        for move in legal_moves:
            if move==FoldAction:
                action_vector[0]=True
            if move==CheckAction or move==ExchangeAction:
                action_vector[1]=True
            if move==CallAction:
                action_vector[2]=True
            if move==RaiseAction:
                action_vector[3]=True
                action_vector[4]=True
            if move==BetAction:
                action_vector[5]=True
                action_vector[6]=True
        return action_vector

    def choose_action(self, strategy, action_vector):
        """
        Given our possible legal moves and the strategy profile for this game history, chooses an action to take
        non-deterministically.
        """
        sum=0
        for i in range(len(strategy)):
            sum+=strategy[i]
            if strategy[i]!=0 and action_vector[i]==True:  #If it is a legal move
                if self.agression<=sum:
                    return i
        return None

    def will_win(self, game, round):
        """
        Checks to see whether or not we can win the rest of the game by only checking or folding.
        """
        rounds_left=game.num_hands-round.hand_num
        losses=(.5*rounds_left*4)+(.5*rounds_left*2) #By playing a checkfold strategy the margin between your score and the opponents score will change by 4 or 2 depending on whether or not you are the big blind
        return round.bankroll>(losses+round.opponent_bankroll) #Will they catch up to us by the end of the game if we checkfold

    def play_checkfold(self, legal_moves):
        """
        Once we pass a given points threshold, we will check or fold the rest of the game, ensuring a win.
        """
        if CheckAction in legal_moves:
            return CheckAction()
        else:
            return FoldAction()

    def play_strategy(self, action, cards, board_cards, legal_moves, pot, cost_func, min_amount, max_amount, hand_strength):
        """
        Given an action selected from our strategy distribution, play that strategy.
        """
        self.just_exchanged=False

        if action==0: #Fold
            return FoldAction()

        if action==1: #Check/ Exchange
            if ExchangeAction in legal_moves and not self.is_preflop(board_cards): #Do not exchange pre-flop
                exchange_cost=cost_func(ExchangeAction())
                exchange_ev=0.5*pot.opponent_total-0.5*(pot.total + exchange_cost)
                check_ev=hand_strength*pot.opponent_total-(1-hand_strength)*pot.total
                if exchange_ev>check_ev:  #Exchanging is worth it
                    self.discarded_cards+=cards  #Keep track of the cards we discarded
                    self.just_exchanged=True
                    return ExchangeAction()
                return CheckAction()
            return CheckAction()

        if action==2: #Call
            return CallAction()

        if action==3: #Raise half pot
            if max_amount>.5*pot.total: #If we have enough money to raise half of the pot
                amount=max(.5*pot.total, min_amount)
                return RaiseAction(amount)
            else: #If we cannot raise half of the pot, raise by as much a we can
                return RaiseAction(max_amount)

        if action==4: #Raise full pot
            if max_amount>pot.total: #If we have enough money to raise the full pot
                amount=max(pot.total, min_amount)
                return RaiseAction(amount)
            else: #If we cannot raise the full pot, raise by as much a we can
                return RaiseAction(max_amount)

        if action==5: #Bet half pot
            if max_amount>.5*pot.total: #If we have enough money to bet half of the pot
                amount=max(.5*pot.total, min_amount)
                return BetAction(amount)
            else: #If we cannot raise half of the pot, bet as much a we can
                return BetAction(max_amount)

        if action==6: #Bet full pot
            if max_amount>pot.total: #If we have enough money to bet the full pot
                amount=max(pot.total, min_amount)
                return BetAction(amount)
            else: #If we cannot raise the full pot, bet as much a we can
                return BetAction(max_amount)

    def play_heuristic(self, cards, board_cards, pot, legal_moves, cost_func, min_amount, max_amount, hand_strength):
        """
        Plays average (staff bot). Called whenever we try to look up a game stage that is not in i_map or if i_map
        returns a randomized strategy distribution
        """
        self.just_exchanged = False

        if ExchangeAction in legal_moves and not self.is_preflop(board_cards):  #Exchange logic
            exchange_cost = cost_func(ExchangeAction())
            exchange_ev = 0.5 * pot.opponent_total - 0.5 * (pot.total + exchange_cost)
            check_ev = hand_strength * pot.opponent_total - (1 - hand_strength) * pot.total
            if exchange_ev > check_ev:  #Exchanging is worth it
                self.discarded_cards += cards  #Keep track of the cards we discarded
                self.just_exchanged=True
                return ExchangeAction()
            return CheckAction()

        else:  #Decision to commit resources to the pot
            continue_cost = cost_func(CallAction()) if CallAction in legal_moves else cost_func(CheckAction())
            commit_amount = int(pot.pip + continue_cost + 0.75 * (pot.grand_total + continue_cost))
            if min_amount is not None:
                commit_amount = max(commit_amount, min_amount)
                commit_amount = min(commit_amount, max_amount)

            if RaiseAction in legal_moves:
                commit_action = RaiseAction(commit_amount)
            elif BetAction in legal_moves:
                commit_action = BetAction(commit_amount)
            elif CallAction in legal_moves:  # We are contemplating an all-in call
                commit_action = CallAction()
            else:  # Only legal action
                return CheckAction()

            if continue_cost > 0:  # Our opponent has raised the stakes
                if continue_cost > 1 and hand_strength < 1:  # Tight-aggressive playstyle
                    hand_strength -= 0.25  # Intimidation factor
                pot_odds = float(continue_cost) / (pot.grand_total + continue_cost)
                if hand_strength >= pot_odds:  # Staying in the game has positive EV
                    if hand_strength > 0.5 and random.random() < hand_strength:  # Commit more sometimes
                        return commit_action
                    return CallAction()
                else:  # Staying in the game has negative EV
                    return FoldAction()

            elif continue_cost == 0:
                if random.random() < hand_strength:  # Balance bluffs with value bets
                    return commit_action
                return CheckAction()

    def update_history(self, cards, board_cards, round, move_history):
        """
        Parses move_history and updates self.history with moves made in both players last round of betting.
        """
        history=["r", "r"]
        truncate=False
        pot_size=3
        contrib_sb=1
        contrib_bb=2

        if round.big_blind: #If you are the big blind this round
            sb_name=self.opponent_name
            bb_name=self.player_name
        else:
            sb_name=self.player_name
            bb_name=self.opponent_name

        for i in range(2, len(move_history)):
            if history[-2:]==["-1", "1"] or history[-2:]==["1", "-1"]:
                truncate=True
            move = move_history[i]
            player = move.split(":")[-1]  # Who is making the given move
            if "FOLD" in move:
                if not truncate:
                    if player == sb_name:
                        history.append("0")
                    if player == bb_name:
                        history.append("-0")

            elif "CHECK" in move or "EXCHANGE" in move:
                if not truncate:
                    if player == sb_name:
                        history.append("1")
                        if history[-1] == "-1":
                            truncate = True
                    if player == bb_name:
                        history.append("-1")
                        if history[-1] == "1":
                            truncate = True

            elif "CALL" in move:
                if not truncate:
                    if player == sb_name:
                        cost = contrib_bb - contrib_sb  # Cost for the small blind to call
                        pot_size += cost
                        contrib_sb += cost
                        history.append("2")
                    if player == bb_name:
                        cost = contrib_bb - contrib_sb  # Cost for the big blind to call
                        pot_size += cost
                        contrib_bb += cost
                        history.append("-2")

            elif "RAISE" in move:
                if not truncate:
                    amount = int(move.split(":")[1])  # The amount that the player raised
                    if player == sb_name:
                        cost = (amount - contrib_sb) + (contrib_bb - contrib_sb)
                        pot_size += cost
                        contrib_sb += cost
                        if cost <= .5 * pot_size:
                            history.append("3")
                        else:
                            history.append("4")
                    if player == bb_name:
                        cost = (amount - contrib_bb) + (contrib_sb - contrib_bb)
                        pot_size += cost
                        contrib_bb += cost
                        if cost <= .5 * pot_size:
                            history.append("-3")
                        else:
                            history.append("-4")

            elif "BET" in move:
                if not truncate:
                    amount = int(move.split(":")[1])  # The amount that the player raised
                    print(amount, pot_size)
                    if player == sb_name:
                        cost = amount
                        pot_size += cost
                        contrib_sb += cost
                        if cost <= .5 * pot_size:
                            history.append("5")
                        else:
                            history.append("6")
                    if player == bb_name:
                        cost = amount
                        pot_size += cost
                        contrib_bb += cost
                        if cost <= .5 * pot_size:
                            history.append("-5")
                        else:
                            history.append("-6")

            elif "DEAL" in move:
                truncate = False  # Stop truncating for the last round of betting
                contrib_sb = 0
                contrib_bb = 0
                history=self.add_chance_nodes(history)

            else:
                pass

        print(history, pot_size, contrib_sb, contrib_bb)
        self.history=history

if __name__ == '__main__':
    args = parse_args()
    run_bot(Player(), args)