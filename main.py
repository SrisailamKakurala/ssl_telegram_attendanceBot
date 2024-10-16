import os
import requests
import pandas as pd
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Dictionary to store user roll numbers
user_roll_numbers = {}

# File to store analytics
analytics_file_path = './analytics.json'

# URL for login action
login_url = "http://tkrcet.in/login_action.php"

# Token extracted from the environment variable
token = "MTcyNjEwODg0OTR6TVZGRnJnbHF4R2RIRWFiZ0hxOTU3NWN5Nk1zcXRU"

# Path to the HTML file
file_path = './fresh.html'

# Load analytics data from the file
def load_analytics():
    if os.path.exists(analytics_file_path):
        if os.path.getsize(analytics_file_path) > 0:
            try:
                with open(analytics_file_path, 'r') as f:
                    analytics = json.load(f)
                    analytics["unique_users"] = set(analytics["unique_users"])  # Convert list back to set
                    return analytics
            except json.JSONDecodeError:
                print("Corrupted JSON, initializing with default values.")
        else:
            print("Empty file, initializing with default values.")
    
    return {"unique_users": set(), "total_users": 0, "total_visits": 0, "route_usage": {}}

# Save analytics data to the file
def save_analytics(analytics):
    analytics["unique_users"] = list(analytics["unique_users"])  # Convert to list for JSON
    with open(analytics_file_path, 'w') as f:
        json.dump(analytics, f, indent=4)
    analytics["unique_users"] = set(analytics["unique_users"])  # Convert back to set after saving

# Log in and save HTML content
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

# Check attendance
def check_attendance(roll):
    login(roll)
    tables = pd.read_html(file_path)
    df = tables[2]
    
    try:
        value = df.xs(key='%', axis=1, level=1).iloc[-1].values[0].item()
        return value
    except KeyError as e:
        raise Exception(f"KeyError: {e}")

# Attendance history after login
def attendance_history():
    tables = pd.read_html(file_path)
    df = tables[3].fillna("-")
    df.columns = df.columns.droplevel(0)
    df_small = df[['Date', 'Total', 'Attend']].head(3)
    history_str = df_small.to_markdown(index=False)
    return history_str

# Start command handler
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    # Update analytics
    analytics = load_analytics()
    if user_id not in analytics["unique_users"]:
        analytics["unique_users"].add(user_id)
        analytics["total_users"] += 1
    analytics["total_visits"] += 1
    analytics["route_usage"]["/start"] = analytics["route_usage"].get("/start", 0) + 1
    save_analytics(analytics)

    await update.message.reply_text("(Bot Updated) \n\nWelcome! Please enter your roll number.")
    return

# Store user's roll number
async def store_rollno(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    roll_no = update.message.text.upper()

    # Save the roll number for the user
    user_roll_numbers[user_id] = roll_no
    
    print(user_roll_numbers)

    # Update analytics
    analytics = load_analytics()
    analytics["route_usage"]["rollno"] = analytics["route_usage"].get("rollno", 0) + 1
    save_analytics(analytics)

    await update.message.reply_text(f"Roll number saved as {roll_no}. Now use \n 1. /at for total attendance. \n 2. /history for last 3 days attendance. \n 3. /at <rollNo> for others' attendance.")
    return

# Attendance command handler
async def attendance(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    roll = context.args[0].upper() if context.args else user_roll_numbers.get(user_id)

    if not roll:
        await update.message.reply_text("Please provide your roll number first using the /start command.")
        return

    try:
        attendance_data = check_attendance(roll)

        # Update analytics
        analytics = load_analytics()
        analytics["route_usage"]["/at"] = analytics["route_usage"].get("/at", 0) + 1
        save_analytics(analytics)

        await update.message.reply_text(f"Attendance for {roll}: {attendance_data}")
    except Exception as e:
        await update.message.reply_text(f"Could not retrieve attendance for {roll}. Error: {e}")

# Attendance history command handler with login
async def history(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    roll = user_roll_numbers.get(user_id)  # Fetch stored roll number

    if not roll:
        await update.message.reply_text("Please provide your roll number first using the /start command.")
        return

    try:
        # Call login to ensure we have the latest data
        login(roll)
        
        history_data = attendance_history()

        # Update analytics
        analytics = load_analytics()
        analytics["route_usage"]["/history"] = analytics["route_usage"].get("/history", 0) + 1
        save_analytics(analytics)

        # Send the fetched history as the bot
        await update.message.reply_text(f"Attendance History for {roll}:\n```\n{history_data}\n```", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Could not retrieve attendance history. Error: {e}")

# Broadcast command handler
async def broadcast(update: Update, context: CallbackContext) -> None:
    if context.args:
        message = ' '.join(context.args)  # Join message parts

        # Send the message to all users in the user_roll_numbers dictionary
        for user_id in user_roll_numbers.keys():
            try:
                await context.bot.send_message(chat_id=user_id, text=f"ADMIN: {message}")
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

        await update.message.reply_text("Broadcast sent successfully.")
    else:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")

# View all roll numbers
async def view_roll_numbers(update: Update, context: CallbackContext) -> None:
    if not user_roll_numbers:
        await update.message.reply_text("No roll numbers registered yet.")
    else:
        roll_numbers = "\n".join(f"Roll No: {roll}" for user_id, roll in user_roll_numbers.items())
        await update.message.reply_text(f"Registered roll numbers:\n{roll_numbers}")

# View analytics command
async def analytics(update: Update, context: CallbackContext) -> None:
    analytics = load_analytics()

    analytics["unique_users"] = len(analytics["unique_users"])  # Show the number of unique users
    await update.message.reply_text(f"Analytics:\n{json.dumps(analytics, indent=4)}")

# Main function to run the bot
def main() -> None:
    application = Application.builder().token('7019335062:AAFS42J4nJOQ-5I7MUSQ_AQ0WdaFnu01HTQ').build()

    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, store_rollno))
    application.add_handler(CommandHandler('at', attendance))
    application.add_handler(CommandHandler('history', history))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('view_roll_numbers', view_roll_numbers))
    application.add_handler(CommandHandler('analytics', analytics))

    application.run_polling()

if __name__ == '__main__':
    main()
