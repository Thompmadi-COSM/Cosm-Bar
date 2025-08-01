from flask import Flask, render_template, abort, url_for, request, jsonify, redirect, session
from Flask.sheets import get_all_drinks, get_sheet_names  # <-- new import
import random
import os
print("Current working directory:", os.getcwd())

app = Flask(__name__)
app.secret_key = 'something_secret'  # Needed for session support

GLASS_TYPES = [
    "Martini", "Highball", "Rocks", "Collins", "Margarita",
    "Coupe", "Shot Glass", "Wine Glass"
]

AMOUNT_INCREMENTS = [f"{0.25 * i:.2f}" for i in range(1, 11)]

MIXERS = [
    "Lime Juice",
    "Orange Juice",
    "Cranberry Juice",
    "Pineapple Juice",
    "Lemonade",
    "Cola",
    "Tonic Water",
    "Soda Water",
    "Ginger Beer"
]

SPIRITS = [
    "Tequila",
    "Triple Sec",
    "Vodka",
    "Gin",
    "Rum",
    "Whiskey",
    "Brandy",
    "Cognac"
]

# NEW: Venue selector route
@app.route('/')
def select_venue():
    venues = get_sheet_names()
    return render_template('select_venue.html', venues=venues)

# NEW: Store venue choice in session
@app.route('/set_venue', methods=['POST'])
def set_venue():
    session['venue'] = request.form['venue']
    return redirect('/home')

def get_drink_data(drink_name):
    drinks = get_all_drinks(session.get('venue'))
    return drinks.get(drink_name)

def build_amount_options(correct_amount):
    decoys = [amt for amt in AMOUNT_INCREMENTS if amt != correct_amount]
    decoy_sample = random.sample(decoys, min(4, len(decoys)))
    options = decoy_sample + [correct_amount]
    random.shuffle(options)
    return [str(amt) for amt in options]

def build_glass_options(correct_glass):
    others = [g for g in GLASS_TYPES if g != correct_glass]
    decoys = random.sample(others, min(7, len(others)))
    options = decoys + [correct_glass]
    random.shuffle(options)
    return options

@app.route('/home')
def home():
    if 'venue' not in session:
        return redirect('/')
    return render_template('home.html')

@app.route('/select_drink')
def select_drink():
    drinks = list(get_all_drinks(session.get('venue')).keys())
    return render_template('select_drink.html', drinks=drinks, back_url=url_for('home'))

@app.route('/train/<drink_name>')
def train(drink_name):
    drink_data = get_drink_data(drink_name)
    if not drink_data:
        abort(404)

    correct_mixers = drink_data.get("mixers", [])
    correct_spirits = drink_data.get("spirits", [])
    correct_garnish = drink_data["correct"].get("garnish", "")
    correct_glass_type = drink_data["correct"].get("glass_type", "Martini")

    all_drinks = get_all_drinks(session.get('venue'))

    all_mixers_raw = []
    for d in all_drinks.values():
        all_mixers_raw.extend(d.get("mixers", []))
    unique_mixers = list(set(all_mixers_raw))
    random.shuffle(unique_mixers)

    all_spirits_raw = []
    for d in all_drinks.values():
        all_spirits_raw.extend(d.get("spirits", []))
    unique_spirits = list(set(all_spirits_raw))
    random.shuffle(unique_spirits)

    all_garnishes_raw = []
    for d in all_drinks.values():
        garnish = d.get("correct", {}).get("garnish")
        if garnish:
            all_garnishes_raw.append(garnish)
    unique_garnishes = list(set(all_garnishes_raw))
    random.shuffle(unique_garnishes)

    all_glasses_raw = []
    for d in all_drinks.values():
        glass = d.get("correct", {}).get("glass_type")
        if glass:
            all_glasses_raw.append(glass)
    unique_glasses = list(set(all_glasses_raw))
    random.shuffle(unique_glasses)

    flat_amount_options = [str(amt) for amt in AMOUNT_INCREMENTS]

    return render_template(
        'train_drink.html',
        drink_name=drink_name,
        mixers=unique_mixers,
        spirits=unique_spirits,
        amounts=flat_amount_options,
        garnishes=unique_garnishes,
        glass_types=unique_glasses,
        correct={
            "mixers": correct_mixers,
            "spirits": correct_spirits,
            "amounts": [str(amt) for amt in drink_data["amounts"]],
            "glass_type": correct_glass_type,
            "garnish": correct_garnish,
        },
        back_url=url_for('select_drink')
    )

@app.route('/refresher')
def refresher():
    drinks = get_all_drinks(session.get('venue'))
    drink_names = list(drinks.keys())

    mixers = {name: drinks[name].get("mixers", []) for name in drink_names}
    spirits = {name: drinks[name].get("spirits", []) for name in drink_names}
    amounts = {name: [str(amt) for amt in drinks[name]["amounts"]] for name in drink_names}
    garnishes = {name: drinks[name]["correct"]["garnish"] for name in drink_names}
    glass_types = {name: drinks[name]["correct"]["glass_type"] for name in drink_names}

    zipped_mixers = {name: list(zip(mixers[name], amounts[name])) for name in drink_names}
    zipped_spirits = {name: list(zip(spirits[name], amounts[name][len(mixers[name]):])) for name in drink_names}

    return render_template(
        'refresher.html',
        drinks=drink_names,
        mixers=mixers,
        spirits=spirits,
        amounts=amounts,
        garnishes=garnishes,
        glass_types=glass_types,
        zipped_mixers=zipped_mixers,
        zipped_spirits=zipped_spirits,
        back_url=url_for('home'),
        zip=zip
    )

def normalize_amount(amount_str):
    try:
        num_part = amount_str.lower().replace('oz', '').strip()
        return round(float(num_part), 2)
    except Exception:
        return None

def parse_steps_flexible(steps_list):
    parsed = {
        'ingredients': {},
        'specials': set(),
    }

    for step in steps_list:
        step = step.strip()
        if " - " in step and "oz" in step:
            try:
                name, amt_str = step.split(" - ")
                amt = normalize_amount(amt_str)
                parsed['ingredients'][name.lower()] = amt
            except Exception:
                parsed['ingredients'][step.lower()] = step.lower()
        else:
            parsed['specials'].add(step.lower())

    return parsed

def check_user_answer_flexible(user_steps, correct_steps, drink_data):
    def parse_steps_grouped(steps, mixer_list, spirit_list):
        result = {
            'mixers': {},
            'spirits': {},
            'glass': None,
            'garnish': None,
        }

        for step in steps:
            step = step.strip()
            if " - " in step and "oz" in step:
                try:
                    name, amt_str = step.split(" - ")
                    amt = normalize_amount(amt_str)

                    lower_name = name.lower()
                    if lower_name in [m.lower() for m in mixer_list]:
                        result['mixers'][lower_name] = amt
                    elif lower_name in [s.lower() for s in spirit_list]:
                        result['spirits'][lower_name] = amt
                except Exception:
                    continue
            else:
                lowered = step.lower()
                if lowered in [g.lower() for g in GLASS_TYPES]:
                    result['glass'] = step
                else:
                    result['garnish'] = step

        return result

    def category_sequence(user_steps, mixer_list, spirit_list):
        order_map = {
            'mixer': 0,
            'spirit': 1,
            'glass': 2,
            'garnish': 3
        }

        sequence = []
        for step in user_steps:
            step = step.strip()
            if " - " in step and "oz" in step:
                try:
                    name, _ = step.split(" - ")
                    name_lower = name.lower()
                    if name_lower in [m.lower() for m in mixer_list]:
                        sequence.append(order_map['mixer'])
                    elif name_lower in [s.lower() for s in spirit_list]:
                        sequence.append(order_map['spirit'])
                except:
                    continue
            else:
                lowered = step.lower()
                if lowered in [g.lower() for g in GLASS_TYPES]:
                    sequence.append(order_map['glass'])
                else:
                    sequence.append(order_map['garnish'])

        return sequence == sorted(sequence)

    # 💡 Pull mixer/spirit names directly from drink_data
    mixers = drink_data.get("mixers", [])
    spirits = drink_data.get("spirits", [])

    correct_parsed = parse_steps_grouped(correct_steps, mixers, spirits)
    user_parsed = parse_steps_grouped(user_steps, mixers, spirits)

    # Check that all mixers match regardless of order
    if set(user_parsed['mixers'].keys()) != set(m.lower() for m in mixers):
        return False
    for k, v in user_parsed['mixers'].items():
        correct_amt = correct_parsed['mixers'].get(k)
        if correct_amt is None or abs(correct_amt - v) > 0.01:
            return False

    # Same for spirits
    if set(user_parsed['spirits'].keys()) != set(s.lower() for s in spirits):
        return False
    for k, v in user_parsed['spirits'].items():
        correct_amt = correct_parsed['spirits'].get(k)
        if correct_amt is None or abs(correct_amt - v) > 0.01:
            return False

    # Check glass and garnish match
    if correct_parsed['glass'] and (user_parsed['glass'] or "").lower() != correct_parsed['glass'].lower():
        return False
    if correct_parsed['garnish'] and (user_parsed['garnish'] or "").lower() != correct_parsed['garnish'].lower():
        return False

    # Check that the order of categories was followed
    if not category_sequence(user_steps, mixers, spirits):
        return False

    return True




@app.route('/check_answer/<drink_name>', methods=['POST'])
def check_answer(drink_name):
    drink_data = get_drink_data(drink_name)
    if not drink_data:
        return jsonify({'error': 'Drink not found'}), 404

    user_steps = request.json.get('user_steps', [])

    correct_steps = []

    mixers = drink_data.get('mixers', [])
    spirits = drink_data.get('spirits', [])
    amounts = drink_data.get('amounts', [])

    for i, ing in enumerate(mixers + spirits):
        amount = float(amounts[i])
        formatted = f"{ing} - {amount:.2f} oz"
        correct_steps.append(formatted)

    glass_type = drink_data['correct'].get('glass_type', '')
    garnish = drink_data['correct'].get('garnish', '')
    if glass_type:
        correct_steps.append(glass_type)
    if garnish:
        correct_steps.append(garnish)

    is_correct = check_user_answer_flexible(user_steps, correct_steps, drink_data)


    return jsonify({'correct': is_correct})

if __name__ == '__main__':
    app.run(debug=True, port=5050)







































