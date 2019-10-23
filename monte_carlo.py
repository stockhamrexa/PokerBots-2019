import deuces
import itertools
import pickle
import random

"""
Preflop hands are bucketed into six ctegories based on suit, count, and distance from each other while postflop hands
are bucketed by hand strength, increasing by .2 each time.
"""

suits = ['c', 'd', 'h', 's']
counts = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
deck = []
for i in counts:
    for j in suits:
        deck.append(i + j)

preflop_hands=[] #All possible hole cards that can be drawn
for hand in itertools.combinations(deck, 2):
    preflop_hands.append(hand)

def generate_preflop_type(preflop_hands):
    """
    Puts all preflop hands into their bucket.
    """
    pocket_pairs = []  # A list of all hands that are pocket pairs
    suited_connectors = []  # A list of all hands that are suited connectors
    unsuited_connectors = []  # A list of all hands that are unsuited connectors
    suited = []  # A list of all hands that are only suited
    unsuited_close = []  # A list of all hands that are only unsuited and within 5 (straight) of each other
    unsuited_far = []  # A list of preflop hands that are only suited and greater than 5 from each other
    for hand in preflop_hands:
        suit1 = hand[0][1]
        suit2 = hand[1][1]
        value1 = hand[0][0]
        value2 = hand[1][0]
        if value1 == value2:  # Pocket pairs
            pocket_pairs.append(hand)
        elif suit1 == suit2:  # Suited
            if abs(counts.index(value1) - counts.index(value2)) == 1:  # Suited connectors
                suited_connectors.append(hand)
            else:
                suited.append(hand)
        else:  # Unsuited
            if abs(counts.index(value1) - counts.index(value2)) == 1:  # Unsuited connectors
                unsuited_connectors.append(hand)
            else:
                if abs(counts.index(value1) - counts.index(value2)) <= 4:  # Unsuited close
                    unsuited_close.append(hand)
                else:  # Unsuited far
                    unsuited_far.append(hand)
    preflop_type = [pocket_pairs, suited_connectors, unsuited_connectors, suited, unsuited_close, unsuited_far]
    return preflop_type

def generate_preflop_odds(preflop_type):
    """
    Returns the odds of a preflop hand being in one of the given buckets
    """
    preflop_odds=[]
    for i in preflop_type:
      preflop_odds.append(len(i)/float(len(preflop_hands)))
    return preflop_odds

def generate_random_preflop(preflop_type, n):
    """
    Takes in a list of all preflop card combinations, segmented into their six unique buckets. Returns a list of cards
    with n selected from each category.
    """
    preflop_hands = []  # A list of 6*n random hole card pairs, n from each of the six preflop buckets
    preflop_cards=[] #The actual cards that were dealt
    for type in preflop_type:
        new_cards_added = 0
        while new_cards_added < n:
            rand = random.randint(0, len(type) - 1)
            hand = type[rand]
            if hand[0] not in preflop_cards and hand[1] not in preflop_cards:
                preflop_hands.append(hand)
                preflop_cards.append(hand[0])
                preflop_cards.append(hand[1])
                new_cards_added += 1
    return preflop_hands

def generate_postflop_odds(preflop_type, deck):
    """
    For each of the six preflop buckets, calculates the odds of the postflop cards putting the hand into one of the five
    hand strength buckets.
    """
    evaluator=deuces.Evaluator()
    postflop_odds=[]
    for type in preflop_type: #Loops through each of the preflop buckets
        odds=[0, 0, 0, 0, 0]
        for hand in type: #Loops through each hand in the bucket
            new_deck=deck[:]
            new_deck.remove(hand[0]) #Removes the cards in the current hand from the deck
            new_deck.remove(hand[1])
            postflop_hands=list(itertools.combinations(new_deck, 5))
            for i in range(10000): #Doesn't loop through all possible five board cards for each hole card, only picks 50 random ones and estimates odds of going from one bucket to another
                board=postflop_hands.pop(random.randint(0, len(postflop_hands)-1))
                hand_strength=get_hand_strength(hand, board, evaluator)
                if hand_strength<=.2:
                    odds[0]+=1
                elif hand_strength>.2 and hand_strength<=.4:
                    odds[1]+=1
                elif hand_strength>.4 and hand_strength<=.6:
                    odds[2]+=1
                elif hand_strength>.6 and hand_strength<=.8:
                    odds[3]+=1
                else:
                    odds[4]+=1
        total=sum(odds)
        for i in range(len(odds)):
            odds[i]=odds[i]/float(total)
        print(odds)
        postflop_odds.append(odds)
    return postflop_odds

def get_hand_strength(hole_cards, board_cards, evaluator):
    """
    Returns the hand strength of the cards.
    """
    hole = [deuces.Card.new(hole_cards[0]), deuces.Card.new(hole_cards[1])]
    board = [deuces.Card.new(board_cards[0]), deuces.Card.new(board_cards[1]), deuces.Card.new(board_cards[2]), deuces.Card.new(board_cards[3]), deuces.Card.new(board_cards[4])]
    strength=(7643-evaluator.evaluate(hole, board))/float(7642)
    return strength

preflop_type=generate_preflop_type(preflop_hands)
preflop_odds=generate_preflop_odds(preflop_type)
postflop_odds=generate_postflop_odds(preflop_type, deck)


print(preflop_odds)
print(postflop_odds)

filename="bucket_odds"
file=open(filename, "wb")
pickle.dump([preflop_type, preflop_odds, postflop_odds], file)
file.close()


