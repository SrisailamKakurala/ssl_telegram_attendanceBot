import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Dictionary to store user roll numbers
user_roll_numbers = {}

# URL for login action
login_url = "http://tkrcet.in/login_action.php"

# Token extracted from the environment variable
token = "MTcyNjEwODg0OTR6TVZGRnJnbHF4R2RIRWFiZ0hxOTU3NWN5Nk1zcXRU"

# Path to the HTML file
file_path = './fresh.html'

# Conversation handler states
ASK_ROLLNO = 1

# Function to log in and save HTML content
def login(username):
    login_data = {
        'token': token,
        'username': username,
        'password': username,
        'submit': 'Login',
    }
    
    try:
        response = requests.post(login_url, data=login_data, allow_redirects=True)
        
        if response.status_code == 200:
            with open(file_path, "w", encoding='utf-8') as file:
                file.write(response.text)
        
        else:
            raise Exception(f"Failed to log in. Status code: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"An error occurred: {e}")

# Function to check attendance
def check_attendance(roll):
    login(roll)  # Log in and save the HTML content
    tables = pd.read_html(file_path)
    df = tables[2]
    
    try:
        value = df.xs(key='%', axis=1, level=1).iloc[-1].values[0].item()
        return value
    except KeyError as e:
        raise Exception(f"KeyError: {e}")

# # Functions for new command handlers
# def attendance_table():
#     # Read the HTML tables from the specified file
#     tables = pd.read_html(file_path)
#     df = tables[2]  # Assuming the attendance data is in table 2
    
#     # Reset the column headers by dropping the first level
#     df.columns = df.columns.droplevel(0)

#     # Remove the first two rows (header rows)
#     df = df[2:].reset_index(drop=True)

#     # Optionally, drop the 'Conduct' and 'Attend' columns if they exist
#     if 'Conduct' in df.columns and 'Attend' in df.columns:
#         df = df.drop(columns=['Conduct', 'Attend'])

#     # Selecting relevant columns only
#     df_small = df[['Subject', 'Classes', '%']]

#     # Format the table as a markdown text
#     table_str = df_small.to_markdown(index=False)

#     # Return the formatted table string
#     return table_str

def attendance_history():
    tables = pd.read_html(file_path)
    df = tables[3].fillna("-")
    
    # Drop the extra header row by resetting the column headers
    df.columns = df.columns.droplevel(0)

    df_small = df[['Date', 'Total', 'Attend']].head(3)  # Limit to the last 3 rows
    # Format the history in markdown
    history_str = df_small.to_markdown(index=False)
    return history_str

# Start command handler
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome! Please enter your roll number.")
    return ASK_ROLLNO  # Move to the state where we ask for roll number

# Function to store user's roll number
async def store_rollno(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    roll_no = update.message.text.upper()  # Convert roll number to uppercase

    # Save the roll number for the user
    user_roll_numbers[user_id] = roll_no
    await update.message.reply_text(f"Roll number saved as {roll_no}. Now use \n 1. /at for total attendance. \n 2. /history for last 3 days atendance. \n 3. /at <rollNo> for others attendance")
    return ConversationHandler.END  # End conversation

# Attendance command handler
async def attendance(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    roll = context.args[0].upper() if context.args else user_roll_numbers.get(user_id)

    if not roll:
        await update.message.reply_text("Please provide your roll number first using the /start command.")
        return

    try:
        attendance_data = check_attendance(roll)
        await update.message.reply_text(f"Attendance for {roll}: {attendance_data}")
    except Exception as e:
        await update.message.reply_text(f"Could not retrieve attendance for {roll}. Error: {e}")

# Attendance table command handler
# async def table(update: Update, context: CallbackContext) -> None:
#     try:
#         table_data = attendance_table()
#         await update.message.reply_text(f"Attendance Table:\n```\n{table_data}\n```", parse_mode='Markdown')
#     except Exception as e:
#         await update.message.reply_text(f"Could not retrieve attendance table. Error: {e}")

# Attendance history command handler
async def history(update: Update, context: CallbackContext) -> None:
    try:
        history_data = attendance_history()
        await update.message.reply_text(f"Attendance History:\n```\n{history_data}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Could not retrieve attendance history. Error: {e}")

def main():
    # Fetch bot token from environment variable
    bot_token = '7019335062:AAFS42J4nJOQ-5I7MUSQ_AQ0WdaFnu01HTQ'

    application = Application.builder().token(bot_token).build()

    # Create conversation handler to ask for roll number
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLLNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_rollno)]
        },
        fallbacks=[],
    )

    # Add command handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("at", attendance))
    # application.add_handler(CommandHandler("table", table))
    application.add_handler(CommandHandler("history", history))

    application.run_polling()

if __name__ == '__main__':
    main()
