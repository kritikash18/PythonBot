from flask import Flask, redirect, url_for, render_template, request, render_template_string
import threading
 
from functions import (
    initialize_conversation,
    initialize_conv_reco,
    get_chat_completions,
    moderation_check,
    intent_confirmation_layer,
    compare_laptops_with_user,
    recommendation_validation,
    extract_user_requirements
)

import openai
import os
import ast
import re
import pandas as pd
import json
import time
from tenacity import retry, wait_random_exponential, stop_after_attempt

openai.api_key=open("API_Key.txt",'r').read().strip()
os.environ['OPENAI_API_KEY'] = openai.api_key

app = Flask(__name__)

shopassist_bot = []
conversation = initialize_conversation()
introduction = get_chat_completions(conversation)
shopassist_bot.append({'bot':introduction})
top_3_laptops = None


@app.route("/")
def default_func():
    global shopassist_bot, conversation, top_3_laptops
    return render_template("index.html", name_bot = shopassist_bot)

@app.route("/exit", methods = ['POST','GET'])
def end_conv():
    global shopassist_bot, conversation, top_3_laptops
    shopassist_bot = []
    conversation = initialize_conversation()
    introduction = get_chat_completions(conversation)
    shopassist_bot.append({'bot':introduction})
    top_3_laptops = None
    return redirect(url_for('default_func'))

def delayed_redirect():
    shopassist_bot.append({'bot': "Sorry, this message has been flagged. Restarting your conversation...."})
    time.sleep(10)  # Simulate server-side work before redirection
    return redirect(url_for('end_conv'))

@app.route("/chat", methods = ['POST'])
def invite():
    global shopassist_bot, conversation, top_3_laptops, conversation_reco
    user_input = request.form["user_input_message"]
    shopassist_bot.append({'user':user_input})
    prompt = 'Remember that you are an intelligent laptop assistant. So, you only answer questions around laptop. Remind the same to user in case anything else is asked.'
    moderation = moderation_check(user_input)
    if moderation == 'Flagged':
        threading.Timer(0, delayed_redirect).start()

    if top_3_laptops is None:
        conversation.append({"role": "user", "content": user_input + prompt})
        response_assistant = get_chat_completions(conversation)

        moderation = moderation_check(response_assistant)
        if moderation == 'Flagged':
            threading.Timer(0, delayed_redirect).start()

        confirmation = intent_confirmation_layer(response_assistant)

        moderation = moderation_check(confirmation)
        if moderation == 'Flagged':
            threading.Timer(0, delayed_redirect).start()

        if "No" in confirmation:
            conversation.append({"role": "assistant", "content": response_assistant})
            shopassist_bot.append({'bot':response_assistant})
        else:
            result = extract_user_requirements(response_assistant, True)
            shopassist_bot.append({'bot':"Thank you for providing all the information. Kindly wait, while I fetch the products: \n"})
            
            top_3_laptops = compare_laptops_with_user(result)

            validated_reco = recommendation_validation(top_3_laptops)

            if len(validated_reco) == 0:
                shopassist_bot.append({'bot':"Sorry, we do not have laptops that match your requirements. Connecting you to a human expert. Please end this conversation."})

            conversation_reco = initialize_conv_reco(validated_reco)
            recommendation = get_chat_completions(conversation_reco)

            moderation = moderation_check(recommendation)
            if moderation == 'Flagged':
                threading.Timer(0, delayed_redirect).start()

            conversation_reco.append({"role": "user", "content": "This is my user profile" + response_assistant})
            conversation_reco.append({"role": "assistant", "content": recommendation})
            shopassist_bot.append({'bot':recommendation})

    else:
        conversation_reco.append({"role": "user", "content": user_input})
        shopassist_bot.append({'user':user_input})

        response_asst_reco = get_chat_completions(conversation_reco)

        moderation = moderation_check(response_asst_reco)
        if moderation == 'Flagged':
            threading.Timer(0, delayed_redirect).start()

        conversation.append({"role": "assistant", "content": response_asst_reco})
        shopassist_bot.append({'bot':response_asst_reco})
    return redirect(url_for('default_func'))

if __name__ == "__main__":
    app.run(port=5000, debug=True)
