from flask import Flask, render_template, request, redirect, url_for, session, make_response
import random
import time
import numbers
import math
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback-secret-key")

final_scores = []

# Give a little feedback based on score
def get_comment(score):
    if score >= 200:
        return "You really got to the root of this game!"
    elif score >= 100:
        return "Maybe try multiplying your efforts next time!"
    else:
        return "You may need to add on to your math skills!"

# Start or reset the game session
def init_game(difficulty="Easy"):
    session['score'] = 0
    session['rounds'] = random.randint(4, 10)
    session['round_num'] = 1
    session['target_number'] = random.randint(1, 1000)
    session['current_number'] = random.randint(1, 100)
    session['points'] = 0
    session['turns'] = 0
    session['game_over'] = False
    session['history'] = []
    session['difficulty'] = difficulty

# Save stuff to cookies so it sticks around
def save_session_to_cookies(resp):
    resp.set_cookie('final_scores', json.dumps(final_scores), max_age=60*60*24*365)
    resp.set_cookie('difficulty', session.get('difficulty', 'Easy'), max_age=60*60*24*365)

# Grab stuff from cookies if it's there
def load_session_from_cookies():
    global final_scores
    if 'final_scores' in request.cookies:
        try:
            final_scores.clear()
            final_scores.extend(json.loads(request.cookies.get('final_scores')))
        except Exception:
            final_scores.clear()
    if 'difficulty' in request.cookies:
        session['difficulty'] = request.cookies.get('difficulty')

@app.route("/", methods=["GET", "POST"])
def game():
    load_session_from_cookies()
    message = ""
    message2 = ""
    success = False

    # If you pick a difficulty, start a new game with it
    if request.method == "POST" and request.form.get("difficulty"):
        session['difficulty'] = request.form.get("difficulty")
        init_game(session['difficulty'])

    # If it's a new game or you ended the game, reset everything
    if 'score' not in session or (request.method == "POST" and request.form.get("end") == "game"):
        if 'score' in session and not session.get('game_over'):
            final_scores.append({
                "score": round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        init_game(session.get('difficulty', "Easy"))
        if request.method == "POST" and request.form.get("end") == "game":
            session['game_over'] = True
            sorted_scores = sorted(final_scores, key=lambda s: s["score"] if isinstance(s["score"], (int, float)) else float('-inf'), reverse=True)
            resp = make_response(render_template(
                "game.html",
                game_over=True,
                score=round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                comment=get_comment(session['score']) if isinstance(session['score'], numbers.Real) else "Invalid result.",
                final_scores=sorted_scores,
                message="Game ended.",
                success=True,
                history=session.get('history', []),
                difficulty=session['difficulty'],
                allowed_ops=get_allowed_ops(session['difficulty'], session.get('score', 0))
            ))
            save_session_to_cookies(resp)
            return resp

    # Main game logic
    if request.method == "POST" and not session.get('game_over'):
        op = request.form.get("operation")
        operand = request.form.get("operand")
        end = request.form.get("end")
        valid_operation = False

        # If you hit "End Round", either end the game or start a new round
        if end == "round":
            if session['round_num'] >= session['rounds']:
                final_scores.append({
                    "score": round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                session['game_over'] = True
                sorted_scores = sorted(final_scores, key=lambda s: s["score"] if isinstance(s["score"], (int, float)) else float('-inf'), reverse=True)
                resp = make_response(render_template(
                    "game.html",
                    game_over=True,
                    score=round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                    comment=get_comment(session['score']) if isinstance(session['score'], numbers.Real) else "Invalid result.",
                    final_scores=sorted_scores,
                    message="Game ended.",
                    success=True,
                    history=session.get('history', []),
                    difficulty=session['difficulty'],
                    allowed_ops=get_allowed_ops(session['difficulty'], session.get('score', 0))
                ))
                save_session_to_cookies(resp)
                return resp
            else:
                message = "Round ended. Starting new round."
                session['round_num'] += 1
                session['score'] = 0
                session['points'] = 0
                session['turns'] = 0
                session['target_number'] = random.randint(1, 1000)
                session['current_number'] = random.randint(1, 100)
                session['history'] = []
                sorted_scores = sorted(final_scores, key=lambda s: s["score"] if isinstance(s["score"], (int, float)) else float('-inf'), reverse=True)
                resp = make_response(render_template(
                    "game.html",
                    round_num=session['round_num'],
                    total_rounds=session['rounds'],
                    current_number=round(session['current_number'], 2) if isinstance(session['current_number'], numbers.Real) else "Invalid (complex)",
                    target_number=round(session['target_number'], 2) if isinstance(session['target_number'], numbers.Real) else "Invalid (complex)",
                    points=session['points'],
                    turns=session['turns'],
                    score=round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                    op_disabled=False,
                    game_over=False,
                    final_scores=sorted_scores,
                    message=message,
                    message2=message2,
                    success=True,
                    history=session.get('history', []),
                    difficulty=session['difficulty'],
                    allowed_ops=get_allowed_ops(session['difficulty'], session.get('score', 0))
                ))
                save_session_to_cookies(resp)
                return resp

        # Handle math operations
        if op:
            allowed_ops = get_allowed_ops(session['difficulty'], session.get('score', 0))
            if op not in allowed_ops:
                message = "This operation is not allowed at the current difficulty or score."
            else:
                session['turns'] += 1
                try:
                    if op == "sqrt()":
                        if session['current_number'] < 0:
                            message = "Cannot take square root of a negative number."
                            session['turns'] -= 1
                        else:
                            result = math.sqrt(session['current_number'])
                            if isinstance(result, complex):
                                message = "Result is a complex number. Operation not allowed."
                                session['turns'] -= 1
                            elif session['current_number'] < 1.1:
                                message = "This seems a bit low..."
                                session['turns'] -= 1
                            else:
                                session['points'] += 3
                                session['history'].append({
                                    "operation": "√",
                                    "operand": "",
                                    "result": round(result, 4)
                                })
                                session['current_number'] = result
                                valid_operation = True
                    elif op == "**":
                        if operand is None or operand.strip() == "":
                            message = "Please enter a number for this operation."
                            session['turns'] -= 1
                        else:
                            operand_val = float(operand)
                            if session['current_number'] < 0 and not operand_val.is_integer():
                                message = "Result would be complex. Operation not allowed."
                                session['turns'] -= 1
                                raise ValueError
                            result = session['current_number'] ** operand_val
                            if isinstance(result, complex):
                                message = "Result is a complex number. Operation not allowed."
                                session['turns'] -= 1
                                raise ValueError
                            session['points'] += 3
                            session['history'].append({
                                "operation": op,
                                "operand": operand,
                                "result": round(result, 4)
                            })
                            session['current_number'] = result
                            valid_operation = True
                    else:
                        if operand is None or operand.strip() == "":
                            message = "Please enter a number for this operation."
                            session['turns'] -= 1
                        else:
                            operand_val = float(operand)
                            if op == "+":
                                result = session['current_number'] + operand_val
                                session['points'] += 1
                            elif op == "-":
                                result = session['current_number'] - operand_val
                                session['points'] += 1
                            elif op == "*":
                                result = session['current_number'] * operand_val
                                session['points'] += 2
                            elif op == "/":
                                if operand_val == 0:
                                    message = "Cannot divide by zero."
                                    session['turns'] -= 1
                                    raise ValueError
                                result = session['current_number'] / operand_val
                                session['points'] += 2
                            else:
                                message = "Invalid operation."
                                session['turns'] -= 1
                                raise ValueError
                            session['history'].append({
                                "operation": op,
                                "operand": operand,
                                "result": round(result, 4)
                            })
                            session['current_number'] = result
                            valid_operation = True

                    # If you did something valid, update the score
                    if valid_operation:
                        session['score'] += session['points']
                        session['points'] = 0
                    if session['score'] < 0:
                        session['score'] = 0
                        message = "How did you end up with a negative score?"
                        message2 = "Don't worry, you're back to zero!"
                    # If you hit the target, either end the game or go to the next round
                    if abs(session['current_number'] - session['target_number']) < 1e-6:
                        message = "Congratulations! You've reached the target number!"
                        if session['round_num'] >= session['rounds']:
                            final_scores.append({
                                "score": round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            session['game_over'] = True
                            sorted_scores = sorted(final_scores, key=lambda s: s["score"] if isinstance(s["score"], (int, float)) else float('-inf'), reverse=True)
                            resp = make_response(render_template(
                                "game.html",
                                game_over=True,
                                score=round(session['score'], 2) if isinstance(session['score'], numbers.Real) else "Invalid (complex)",
                                comment=get_comment(session['score']) if isinstance(session['score'], numbers.Real) else "Invalid result.",
                                final_scores=sorted_scores,
                                message=message,
                                message2=message2,
                                success=True,
                                history=session.get('history', []),
                                difficulty=session['difficulty'],
                                allowed_ops=get_allowed_ops(session['difficulty'], session.get('score', 0))
                            ))
                            save_session_to_cookies(resp)
                            return resp
                        else:
                            session['round_num'] += 1
                            session['points'] = 0
                            session['turns'] = 0
                            session['target_number'] = random.randint(1, 1000)
                            session['current_number'] = random.randint(1, 100)
                            session['history'] = []
                            success = True
                    elif abs(session['current_number'] - session['target_number']) < 10:
                        message = "You're close to the target number!"
                        success = True
                except ValueError:
                    pass

    # Always sort scores before rendering and save cookies
    sorted_scores = sorted(final_scores, key=lambda s: s["score"] if isinstance(s["score"], (int, float)) else float('-inf'), reverse=True)
    resp = make_response(render_template(
        "game.html",
        round_num=session.get('round_num', 1),
        total_rounds=session.get('rounds', 1),
        current_number=round(session.get('current_number', 0), 2) if isinstance(session.get('current_number', 0), numbers.Real) else "Invalid (complex)",
        target_number=round(session.get('target_number', 0), 2) if isinstance(session.get('target_number', 0), numbers.Real) else "Invalid (complex)",
        points=session.get('points', 0),
        turns=session.get('turns', 0),
        score=round(session.get('score', 0), 2) if isinstance(session.get('score', 0), numbers.Real) else "Invalid (complex)",
        op_disabled=False,
        game_over=session.get('game_over', False),
        final_scores=sorted_scores,
        message=message,
        message2=message2,
        success=success,
        history=session.get('history', []),
        difficulty=session['difficulty'],
        allowed_ops=get_allowed_ops(session['difficulty'], session.get('score', 0))
    ))
    save_session_to_cookies(resp)
    return resp

# Figure out which operations are allowed based on difficulty and score
def get_allowed_ops(difficulty, score):
    if difficulty == "Easy":
        ops = ["+", "-"]
        if score >= 50:
            ops.append("*")
        if score >= 75:
            ops.append("/")
        if score >= 100:
            ops.append("**")
        if score >= 150:
            ops.append("sqrt()")
        return ops
    elif difficulty == "Hard":
        ops = ["*", "/"]
        if score >= 100:
            ops.append("**")
        if score >= 150:
            ops.append("sqrt()")
        return ops
    elif difficulty == "Extreme":
        return ["**", "sqrt()"]
    else:
        return ["+", "-"]

@app.route("/restart", methods=["POST"])
def restart():
    init_game(session.get('difficulty', "Easy"))
    return redirect(url_for('game'))