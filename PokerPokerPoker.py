import random
from itertools import combinations
from phevaluator import evaluate_cards, Card

# Constants
NUM_PLAYERS = 3  # Including the user
user_player_number = int(
    input(f"Enter your player number (1-{NUM_PLAYERS}): "))
dealer_position = int(
    input(f"Enter the initial dealer position (1-{NUM_PLAYERS}): ")) - 1

small_blind_position = (dealer_position + 1) % NUM_PLAYERS
big_blind_position = (dealer_position + 2) % NUM_PLAYERS


NUM_SIMULATIONS = 10000
INITIAL_CHIP_COUNT = 1000  # Adjust as needed
SMALL_BLIND = 10
BIG_BLIND = 20
MINIMUM_BET = 20  # This could be the same as the big blind or a different value

players = [{'id': i + 1, 'status': 'active', 'last_action': None,
            'last_bet': 0, 'chips': INITIAL_CHIP_COUNT} for i in range(NUM_PLAYERS)]

DECK = [r + s for r in '23456789TJQKA' for s in 'SHDC']

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

    # Deduct blinds from the appropriate players
    players[small_blind_position]['chips'] -= SMALL_BLIND
    players[big_blind_position]['chips'] -= BIG_BLIND

    print(f"Player {small_blind_position + 1} is the Small Blind.")
    print(f"Player {big_blind_position + 1} is the Big Blind.")

    # Return the total blinds to add to the pot
    return SMALL_BLIND + BIG_BLIND


def shuffle_deck(exclude_cards):
    """Return a shuffled deck of cards, excluding certain known cards."""
    deck = [card for card in DECK if card not in exclude_cards]
    random.shuffle(deck)
    return deck


def deal_cards(deck, num_cards):
    """Deal num_cards from the deck and return them."""
    return [deck.pop() for _ in range(num_cards)]


def simulate_game(deck, community_cards, my_hand):
    """Simulate a single game of Texas Hold'em from the current state."""
    remaining_cards = 5 - len(community_cards)
    community_cards += deal_cards(deck, remaining_cards)
    my_strength = evaluate_hand_strength(my_hand + community_cards)
    opponent_strengths = []
    for _ in range(NUM_PLAYERS - 1):
        opponent_hand = deal_cards(deck, 2)
        opponent_strength = evaluate_hand_strength(
            opponent_hand + community_cards)
        opponent_strengths.append(opponent_strength)
    return 'win' if all(my_strength > opponent_strength for opponent_strength in opponent_strengths) else 'lose'


def calculate_preflop_equity(hole_cards, num_opponents=1, iterations=1000):
    suits = ['C', 'D', 'H', 'S']
    total_wins = 0
    total_iterations = 0

    # Determine if the hand is suited or unsuited to adjust the suit combinations
    if hole_cards[0][1] == hole_cards[1][1]:  # Suited hand
        suit_combinations = [(hole_cards[0][1], hole_cards[1][1])]
    else:  # Unsuited hand
        suit_combinations = [(s1, s2)
                             for s1 in suits for s2 in suits if s1 != s2]

    for suit1, suit2 in suit_combinations:
        suited_hole_cards = [hole_cards[0][0] +
                             suit1, hole_cards[1][0] + suit2]
        wins = 0

        for _ in range(iterations):
            # Shuffle deck excluding hole cards
            deck = shuffle_deck(suited_hole_cards)
            community_cards = deal_cards(deck, 5)  # Deal the community cards
            my_strength = evaluate_hand_strength(
                suited_hole_cards + community_cards)

            if my_strength is None:  # Skip if hand strength couldn't be evaluated
                continue

            opponent_strengths = []
            for _ in range(num_opponents):
                opponent_hand = deal_cards(deck, 2)
                opponent_strength = evaluate_hand_strength(
                    opponent_hand + community_cards)
                if opponent_strength is None:  # Skip if hand strength couldn't be evaluated
                    continue
                opponent_strengths.append(opponent_strength)

            if all(my_strength > opponent_strength for opponent_strength in opponent_strengths):
                wins += 1

        total_wins += wins
        total_iterations += iterations

    return total_wins / total_iterations


def evaluate_hand_strength(hand):
    """Evaluate the strength of a hand using phevaluator."""
    if len(hand) < 5:
        return None  # Not enough cards to evaluate

    # Ensure the card format is correct for phevaluator
    hand = [Card(card) for card in hand]

    # Generate all possible combinations of 5 cards from the available cards
    all_combinations = combinations(hand, 5)

    # Evaluate all combinations and keep track of the best (lowest) rank
    best_rank = 7462  # Highest possible rank in phevaluator, represents the weakest hand
    for combo in all_combinations:
        rank = evaluate_cards(*combo)
        if rank < best_rank:
            best_rank = rank

    # Calculate hand strength based on the best (lowest) rank found
    hand_strength = 1 - (best_rank / 7462)

    # Uncomment the next line to see details about the hand evaluation
    # print(f"Best Hand Rank: {best_rank}, Strength: {hand_strength}")
    return hand_strength


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
    print(f"Hand strength: {hand_strength}, Pot size: {pot_size}")

    bet_multiplier, bluff_threshold, value_bet_threshold = gtoHelper(
        hand_strength)

    # Determine action based on hand strength
    if hand_strength > value_bet_threshold:
        action = 'bet'
        bet_size = max(pot_size * bet_multiplier, MINIMUM_BET)
    elif hand_strength > bluff_threshold:
        action = 'bluff'
        bet_size = max(pot_size * bet_multiplier, MINIMUM_BET)
    else:
        action = 'check/fold'
        bet_size = 0  # No bet for check/fold action

    print(f"Bet multiplier: {bet_multiplier}, Bet size: {bet_size}")
    return action, bet_size


def gtoHelper(hand_strength):
    # Adjust bet multipliers based on hand strength
    if hand_strength > 0.5:  # Adjust this threshold as needed
        bet_multiplier = 2.00  # Very strong hand
    elif hand_strength > 0.3:  # Adjust this threshold as needed
        bet_multiplier = 1.50  # Moderately strong hand
    else:
        bet_multiplier = 1.00  # Weaker hand
    strategy = GTO_STRATEGY_TABLE[bet_multiplier]
    value_bet_threshold = strategy['value_bet']
    bluff_threshold = strategy['bluff'] + value_bet_threshold
    print(
        f"Value bet threshold: {value_bet_threshold}, Bluff threshold: {bluff_threshold}")
    return bet_multiplier, bluff_threshold, value_bet_threshold


def calculate_pot_odds(call_amount, pot_size):
    if call_amount == 0:  # Avoid division by zero
        return -1
    return pot_size / call_amount


def adjust_bet_for_pot_odds(bet_size, hand_strength, pot_size, call_amount):
    # Calculate the pot odds
    pot_odds = calculate_pot_odds(call_amount, pot_size)

    # Debug print to understand the values being processed
    print(
        f"Adjusting for pot odds: Bet Size: {bet_size}, Hand Strength: {hand_strength}, Pot Odds: {pot_odds}, Call Amount: {call_amount}")

    if call_amount == 0:  # If there's nothing to call, return the original bet size
        return bet_size

    if hand_strength < pot_odds:
        # If the hand isn't strong enough for the pot odds, adjust the bet size down, but not below the minimum bet
        adjusted_bet = min(bet_size, call_amount)
        return max(adjusted_bet, MINIMUM_BET)

    elif hand_strength > pot_odds * 2:  # If the hand is much stronger than needed, consider being more aggressive
        # Increase the bet but cap it at the pot size and ensure it's not below the minimum bet
        increased_bet = min(bet_size * 1.5, pot_size)
        return max(increased_bet, MINIMUM_BET)

    # If neither condition is met, return the original bet size
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
        # Exclude known cards from the deck
        deck = shuffle_deck(known_cards + my_hand + community_cards)
        outcome = simulate_game(deck, community_cards.copy(), my_hand)
        if outcome == 'win':
            win_count += 1
    win_probability = win_count / NUM_SIMULATIONS
    print(
        f"Based on the simulation, your estimated probability of winning is: {win_probability:.2f}")
    # Adjust action recommendation based on probability
    if win_probability > 0.45:
        return 'raise'
    elif win_probability > 0.25:
        return 'call'
    else:
        return 'fold'


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
        # Calculate the amount the player needs to call
        call_amount = current_bet - player['last_bet']

        # Determine valid actions
        valid_actions = ['fold']
        valid_actions_helper(call_amount, player, valid_actions)

        print(
            f"{role} {player['id']} chips: {player['chips']}, pot size: {pot_size}")
        print(f"Valid actions: {valid_actions}")

        # Determine the recommended action
        if player['id'] == user_player_number:
            player_gto_guidance(community_cards, current_bet,
                                known_cards, my_hand, player, pot_size)

        else:
            print(
                f"Player {player['id']} chips: {player['chips']}, pot size: {pot_size}")

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
            action_valid, pot_size = call_Helper(
                action_valid, current_bet, player, pot_size, role, stage)

        elif action == 'fold':
            player['status'] = 'folded'
            action_valid = True

        if action == 'all-in':
            action_valid, current_bet, pot_size = all_in_helper(
                action_valid, current_bet, player, pot_size)

        elif action == 'check':
            if current_bet == player['last_bet'] or (stage == "Pre-flop" and role == "Big Blind" and current_bet == BIG_BLIND) or (stage == "Pre-flop" and role == "Small Blind" and current_bet == SMALL_BLIND) or (stage != "Pre-flop" and role == "Big Blind" and current_bet == 0):
                player['last_action'] = 'check'
                action_valid = True
            else:
                print("You can't check now. Please choose another action.")
                continue

    return True, current_bet, pot_size  # Action resolved, return updated state


def valid_actions_helper(call_amount, player, valid_actions):
    if player['chips'] >= call_amount:
        valid_actions.append('call')
        if call_amount == 0:
            # Can check if no need to add chips
            valid_actions.append('check')
    else:
        # Can go all-in if not enough chips for a full call
        valid_actions.append('all-in')
    if player['chips'] > call_amount:
        # Can raise if have more chips than call amount
        valid_actions.append('raise')
    if current_bet == player['last_bet']:
        valid_actions.append('check')

    elif player['id'] == big_blind_position + 1 and stage == "Pre-flop" and current_bet == BIG_BLIND:
        valid_actions.append('check')


def player_gto_guidance(community_cards, current_bet, known_cards, my_hand, player, pot_size):
    print(f"Your chips: {player['chips']}, pot size: {pot_size}")
    monte_carlo_action = monte_carlo_simulation(
        my_hand, community_cards, known_cards)
    print(f"Monte Carlo recommended action: {monte_carlo_action}")
    if len(community_cards) >= 3:  # GTO decisions are more relevant post-flop
        combined_cards = my_hand + community_cards
        hand_strength = evaluate_hand_strength(combined_cards)
        gto_action, suggested_bet_size = gto_decision(
            hand_strength, pot_size)
        suggested_bet_size = adjust_bet_for_pot_odds(
            suggested_bet_size, hand_strength, pot_size, current_bet)
        print(
            f"GTO recommended action: {gto_action} with an amount of {suggested_bet_size}")
    else:
        print("Not enough information to make a GTO-based decision.")


def all_in_helper(action_valid, current_bet, player, pot_size):
    all_in_amount = player['chips']
    player['chips'] = 0
    pot_size += all_in_amount
    player['last_action'] = 'all-in'
    player['last_bet'] += all_in_amount
    if player['last_bet'] > current_bet:
        # Update the highest bet if this all-in is a raise
        current_bet = player['last_bet']
    action_valid = True
    return action_valid, current_bet, pot_size


def call_Helper(action_valid, current_bet, player, pot_size, role, stage):
    bet_amount = current_bet - player['last_bet']
    if role == "Small Blind" and stage == "Pre-flop":
        # Small blind only needs to match up to the big blind
        bet_amount = min(bet_amount, BIG_BLIND - SMALL_BLIND)
    if bet_amount > player['chips']:
        bet_amount = player['chips']  # All-in if not enough chips
    player['chips'] -= bet_amount
    pot_size += bet_amount  # Update the pot size
    player['last_action'] = 'call'
    # Ensure this is additive, not a replacement
    player['last_bet'] += bet_amount
    action_valid = True
    return action_valid, pot_size


# Main Interaction Loop
pot_size = assign_blinds(players)

known_cards = []

my_hand_input = user_input("Enter your two cards (e.g., 'AS KH'): ").split()
my_hand = [standardize_card_input(card) for card in my_hand_input]
known_cards.extend(my_hand)
print(f"Your hand: {my_hand}")

community_cards = []

preflop_equity = calculate_preflop_equity(my_hand, NUM_PLAYERS - 1)
print(f"Your estimated preflop equity: {preflop_equity:.2%}")

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
    pot_size += betting_round(stage, players, current_bet,
                              community_cards, my_hand, known_cards, pot_size)

# Final results
print("\nFinal round (River) complete.")
final_rank = evaluate_hand_strength(my_hand + community_cards)
print(
    f"Your final hand rank is {final_rank}, which is a {rank_to_human_readable(final_rank)}")
