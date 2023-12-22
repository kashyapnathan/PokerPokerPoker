import random
from phevaluator import evaluate_cards, Card

# Constants
NUM_PLAYERS = 3  # Including the user
NUM_SIMULATIONS = 10000
INITIAL_CHIP_COUNT = 1000  # Adjust as needed
SMALL_BLIND = 10
BIG_BLIND = 20
MINIMUM_BET = 20  # This could be the same as the big blind or a different value
dealer_position = 0  # Start with the first player as the dealer
small_blind_position = 1  # Typically starts with the player to the left of the dealer
big_blind_position = 2  # Typically the player two seats to the left of the dealer
players = [{'id': i+1, 'status': 'active', 'last_action': None,
            'last_bet': 0, 'chips': INITIAL_CHIP_COUNT} for i in range(NUM_PLAYERS)]

DECK = [r+s for r in '23456789TJQKA' for s in 'SHDC']

GTO_STRATEGY_TABLE = {
    0.25: {'value_bet': 0.83, 'bluff': 0.17},
    0.50: {'value_bet': 0.75, 'bluff': 0.25},
    0.66: {'value_bet': 0.72, 'bluff': 0.28},
    1.00: {'value_bet': 0.67, 'bluff': 0.33},
    1.50: {'value_bet': 0.62, 'bluff': 0.38},
    2.00: {'value_bet': 0.60, 'bluff': 0.40}
}
# Functions


def assign_blinds(players):
    global small_blind_position, big_blind_position

    players[small_blind_position]['chips'] -= SMALL_BLIND
    players[big_blind_position]['chips'] -= BIG_BLIND

    # Rotate the blinds for the next hand
    small_blind_position = (small_blind_position + 1) % NUM_PLAYERS
    big_blind_position = (big_blind_position + 1) % NUM_PLAYERS

    return SMALL_BLIND + BIG_BLIND  # Return the total blinds to add to the pot


def shuffle_deck(exclude_cards):
    """Return a shuffled deck of cards, excluding certain known cards."""
    deck = [card for card in DECK if card not in exclude_cards]
    random.shuffle(deck)
    return deck


def deal_cards(deck, num_cards):
    """Deal num_cards from the deck and return them."""
    return [deck.pop() for _ in range(num_cards)]


def simulate_game(state, deck, community_cards, my_hand):
    """Simulate a single game of Texas Hold'em from the current state."""
    remaining_cards = 5 - len(community_cards)
    community_cards += deal_cards(deck, remaining_cards)
    opponent_hands = [deal_cards(deck, 2) for _ in range(NUM_PLAYERS - 1)]
    my_strength = evaluate_hand_strength(my_hand + community_cards)
    opponent_strengths = [evaluate_hand_strength(
        hand + community_cards) for hand in opponent_hands]
    return 'win' if all(my_strength < opponent_strength for opponent_strength in opponent_strengths) else 'lose'


def evaluate_hand_strength(hand):
    """Evaluate the strength of a hand using phevaluator."""
    if len(hand) < 5:
        return None  # Not enough cards to evaluate
    # Ensure the card format is correct for phevaluator
    hand = [Card(card) for card in hand]
    rank = evaluate_cards(*hand)
    return rank


def rank_to_human_readable(rank):
    """Translate the numerical rank into a human-readable format."""
    # This is a simplified translation.
    if rank == 1:
        return "Royal Flush"
    elif rank <= 10:
        return "Straight Flush"
    elif rank <= 166:
        return "Four of a Kind"
    elif rank <= 322:
        return "Full House"
    elif rank <= 1599:
        return "Flush"
    elif rank <= 1609:
        return "Straight"
    elif rank <= 2467:
        return "Three of a Kind"
    elif rank <= 3325:
        return "Two Pair"
    elif rank <= 6185:
        return "One Pair"
    else:
        return "High Card"


def gto_decision(hand_strength, pot_size):
    # Determine the optimal bet size based on hand strength
    if hand_strength > 0.9:
        bet_multiplier = 2.00  # Strong hand, bet more
    elif hand_strength > 0.75:
        bet_multiplier = 1.00  # Decent hand, bet a moderate amount
    else:
        bet_multiplier = 0.25  # Weak hand, bet less or check

    strategy = GTO_STRATEGY_TABLE[bet_multiplier]
    value_bet_threshold = strategy['value_bet']
    bluff_threshold = strategy['bluff'] + value_bet_threshold

    random_decision = random.random()

    if random_decision < value_bet_threshold:
        action = 'bet'
    elif random_decision < bluff_threshold:
        action = 'bluff'
    else:
        action = 'check/fold'

    bet_size = pot_size * bet_multiplier
    return action, bet_size


def calculate_pot_odds(call_amount, pot_size):
    if call_amount == 0:  # Avoid division by zero
        return float('inf')
    return pot_size / call_amount


def adjust_bet_for_pot_odds(bet_size, hand_strength, pot_size, call_amount):
    pot_odds = calculate_pot_odds(call_amount, pot_size)
    if hand_strength < pot_odds:  # If the hand isn't strong enough for the pot odds
        # Adjust the bet size to match the call amount or less
        return min(bet_size, call_amount)
    return bet_size


def user_input(prompt):
    """Get user input and return it."""
    return input(prompt).strip().upper()


def standardize_card_input(card):
    """Converts card input like '10H' to 'TH'."""
    if card[:-1] == '10':  # If the card is a ten
        # Replace '10' with 'T' and ensure the suit is uppercase
        return 'T' + card[-1].upper()
    # Ensure the entire card is uppercase
    return card[0].upper() + card[1].upper()


def monte_carlo_simulation(my_hand, community_cards, known_cards):
    """Run a Monte Carlo simulation to recommend an action."""
    win_count = 0
    for _ in range(NUM_SIMULATIONS):
        deck = shuffle_deck(known_cards + my_hand)
        outcome = simulate_game(None, deck, community_cards.copy(), my_hand)
        if outcome == 'win':
            win_count += 1
    win_probability = win_count / NUM_SIMULATIONS
    print(
        f"Based on the simulation, your estimated probability of winning is: {win_probability:.2f}")
    return 'raise' if win_probability > 0.4 else 'fold' if win_probability < 0.2 else 'call'


def betting_round(stage, players, current_bet, community_cards, my_hand, known_cards, pot_size):
    print(f"\n--- {stage} Betting Round ---")
    actions_resolved = False

    while not actions_resolved:
        actions_resolved = True
        for player in players:
            if player['status'] != 'folded':
                # Call handle_player_action with all required arguments
                action_resolved, current_bet, pot_size = handle_player_action(
                    player, current_bet, pot_size, my_hand, community_cards, known_cards, stage, small_blind_position, big_blind_position)

                if not action_resolved:
                    actions_resolved = False  # If any action is not resolved, continue the loop

    print(f"Pot size after {stage}: {pot_size}")
    return pot_size  # Return the updated pot size


def handle_player_action(player, current_bet, pot_size, my_hand, community_cards, known_cards, stage, small_blind_position, big_blind_position):
    # Determine the player's role for the prompt
    role = "Player"
    if player['id'] == small_blind_position + 1:
        role = "Small Blind"
    elif player['id'] == big_blind_position + 1:
        role = "Big Blind"

    action_valid = False
    while not action_valid:
        print(
            f"{role} {player['id']} chips: {player['chips']}, pot size: {pot_size}")
        valid_actions = ['fold', 'call', 'raise']
        if current_bet == player['last_bet']:
            # Add 'check' as a valid action if the player can check
            valid_actions.append('check')

        action = user_input(
            f"{role} {player['id']}, enter your action ({'/'.join(valid_actions)}): ").lower()

        if action not in valid_actions:
            print("Invalid action. Please try again.")
            continue  # Stay in the loop until a valid action is provided

        if action == 'raise':
            try:
                raise_amount = int(user_input("Enter raise amount: "))
                if raise_amount < MINIMUM_BET:
                    print(
                        f"The minimum bet is {MINIMUM_BET}. Please raise at least the minimum.")
                    continue  # Invalid raise amount, prompt again

                if raise_amount > player['chips']:
                    print(
                        "Not enough chips. You can raise up to your total chip count.")
                    continue  # Not enough chips, prompt again

                current_bet += raise_amount
                player['chips'] -= raise_amount
                pot_size += raise_amount  # Update the pot size
                player['last_action'] = 'raise'
                player['last_bet'] = current_bet
                action_valid = True

            except ValueError:
                print("Please enter a valid number for the raise amount.")
                continue  # Invalid number entered, prompt again

        elif action == 'call':
            bet_amount = current_bet - player['last_bet']
            if bet_amount > player['chips']:
                bet_amount = player['chips']  # All-in if not enough chips
            player['chips'] -= bet_amount
            pot_size += bet_amount  # Update the pot size
            player['last_action'] = 'call'
            player['last_bet'] = current_bet
            action_valid = True

        elif action == 'fold':
            player['status'] = 'folded'
            action_valid = True

        elif action == 'check' and current_bet == player['last_bet']:
            player['last_action'] = 'check'
            action_valid = True

    return True, current_bet, pot_size  # Action resolved, return updated state


# Main Interaction Loop
pot_size = assign_blinds(players)

known_cards = []

my_hand_input = user_input("Enter your two cards (e.g., 'AS KH'): ").split()
my_hand = [standardize_card_input(card) for card in my_hand_input]
known_cards.extend(my_hand)
print(f"Your hand: {my_hand}")

community_cards = []

# Pre-flop betting round
current_bet = BIG_BLIND  # The initial bet pre-flop is the big blind
pot_size = betting_round("Pre-flop", players, current_bet,
                         community_cards, my_hand, known_cards, pot_size)

for stage, num_cards in [("Flop", 3), ("Turn", 1), ("River", 1)]:
    round_cards_input = user_input(
        f"Enter the {stage} cards (e.g., 'AD KH 3D'): ").split()
    round_cards = [standardize_card_input(card) for card in round_cards_input]
    community_cards.extend(round_cards)
    known_cards.extend(round_cards)
    print(f"\n{stage} cards: {round_cards}")
    print(f"Community Cards: {community_cards}")
    current_bet = 0
    pot_size = betting_round(stage, players, current_bet,
                             community_cards, my_hand, known_cards, pot_size)

# Final results
print("\nFinal round (River) complete.")
final_rank = evaluate_hand_strength(my_hand + community_cards)
print(
    f"Your final hand rank is {final_rank}, which is a {rank_to_human_readable(final_rank)}")
