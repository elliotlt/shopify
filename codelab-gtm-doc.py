# --- INSTALL REQUIRED PACKAGES ---
!pip install --upgrade openai gspread oauth2client --quiet

# --- IMPORTS ---
import json
import openai
import gspread
from google.colab import files
from google.auth import default
from google.colab import auth
from gspread_dataframe import set_with_dataframe
import pandas as pd
import os
import time

# --- AUTHENTICATE GOOGLE SERVICES ---
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)

# --- SETUP OPENAI ---
os.environ["OPENAI_API_KEY"] = input("🔑 Enter your OpenAI API key: ")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- CONFIG ---
USE_AI = True  # Set to False to skip GPT calls
MAX_RETRIES = 3

# --- UPLOAD GTM JSON FILE ---
upload = files.upload()
filename = list(upload.keys())[0]

try:
    with open(filename, 'r') as file:
        gtm_data = json.load(file)
except json.JSONDecodeError:
    raise ValueError("❌ Error: Uploaded file is not valid JSON.")

# --- LOOKUP TABLES ---
tag_types = {
    'gaawe': 'GA4 Event', 'sp': 'Google Ads Remarketing', 'gclidw': 'Conversion Linker',
    'ua': 'Universal Analytics', 'html': 'Custom HTML', 'img': 'Custom Image',
    'googtag': 'Google Tag', 'hjtc': 'Hotjar', 'pntr': 'Pinterest', 'bzi': 'LinkedIn Insight',
    'qpx': 'Quora Pixel', 'flc': 'Floodlight Counter', 'fls': 'Floodlight Sales'
}

variable_types = {
    'aev': 'Auto-Event Variable', 'c': 'Constant', 'j': 'JavaScript Variable',
    'u': 'URL', 'v': 'DataLayer Variable', 'smm': 'Lookup Table', 'remm': 'Regex Table'
}

built_in_triggers = {
    '2147479553': 'All Pages', '2147479572': 'Consent Initialization'
}

# --- EXTRACT GTM ELEMENTS ---
tags = gtm_data['containerVersion'].get('tag', [])
triggers = gtm_data['containerVersion'].get('trigger', [])
variables = gtm_data['containerVersion'].get('variable', [])

# --- MAPPINGS ---
trigger_id_to_name = {t['triggerId']: t['name'] for t in triggers}
trigger_id_to_name.update(built_in_triggers)

# --- AI COMMENT GENERATOR WITH RETRIES ---
def safe_openai_call(prompt):
    if not USE_AI:
        return "(AI comments disabled)"
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    return "Comment generation failed"

def get_ai_comment_tag(tag_name, variable_list, trigger_list):
    prompt = (
        f"What does the GTM tag '{tag_name}' do? "
        f"It uses these variables: {', '.join(variable_list)} and is triggered by: {', '.join(trigger_list)}. "
        "Please explain what it does, why it's useful, and where the data is sent in max 150 words, keep it simple"
    )
    return safe_openai_call(prompt)

def get_ai_comment_variable(variable_name):
    prompt = (
        f"What data does the GTM variable '{variable_name}' collect? "
        "Explain what it collects, why it's needed, and how it's used in the GTM container in simple language, max 150 words."
    )
    return safe_openai_call(prompt)

def get_ai_comment_trigger(trigger_name):
    prompt = (
        f"What does the GTM trigger '{trigger_name}' listen for? "
        "Explain what kind of events it fires, why it's useful, and what actions it triggers in simple language, max 150 words."
    )
    return safe_openai_call(prompt)

# --- CREATE TAGS OVERVIEW DATAFRAME ---
tag_rows = []
for tag in tags:
    name = tag.get('name', 'Unnamed Tag')
    type_ = tag_types.get(tag.get('type', ''), tag.get('type', 'Unknown'))

    trigger_names = [trigger_id_to_name.get(tid, tid) for tid in tag.get('firingTriggerId', [])]
    trigger_bullets = "\n• " + "\n• ".join(trigger_names) if trigger_names else ""

    tag_params = tag.get('parameter', [])
    variable_names = [val.strip("{{}}") for param in tag_params 
                      if isinstance((val := param.get('value')), str) and val.startswith("{{")]
    variable_bullets = "\n• " + "\n• ".join(variable_names) if variable_names else ""

    comment = get_ai_comment_tag(name, variable_names, trigger_names)
    tag_rows.append([name, variable_bullets, trigger_bullets, comment])

tags_df = pd.DataFrame(tag_rows, columns=["Tag Name", "Variables", "Triggers", "Comment"])

# --- CREATE VARIABLES DATAFRAME ---
var_rows = []
for var in variables:
    var_name = var.get('name', 'Unnamed Variable')
    comment = get_ai_comment_variable(var_name)
    var_rows.append([
        var_name,
        variable_types.get(var.get('type', ''), var.get('type', 'Unknown')),
        comment
    ])
variables_df = pd.DataFrame(var_rows, columns=["Variable Name", "Type", "Comment"])

# --- CREATE TRIGGERS DATAFRAME ---
trigger_rows = []
for trig in triggers:
    name = trig.get('name', 'Unnamed Trigger')
    type_ = trig.get('type', 'Unknown')
    comment = get_ai_comment_trigger(name)
    trigger_rows.append([name, type_, comment])

triggers_df = pd.DataFrame(trigger_rows, columns=["Trigger Name", "Type", "Comment"])

# --- CREATE GOOGLE SHEET ---
spreadsheet = gc.create("GTM Container Documentation")
sheet_tags = spreadsheet.add_worksheet(title="Tags Overview", rows="100", cols="20")
sheet_vars = spreadsheet.add_worksheet(title="Variables", rows="100", cols="10")
sheet_trigs = spreadsheet.add_worksheet(title="Triggers", rows="100", cols="10")

spreadsheet.del_worksheet(spreadsheet.sheet1)

# --- WRITE TO SHEETS ---
set_with_dataframe(sheet_tags, tags_df)
set_with_dataframe(sheet_vars, variables_df)
set_with_dataframe(sheet_trigs, triggers_df)

# --- DONE ---
print(f"\u2705 Google Sheet created: https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit")
