import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Dictionary to store user roll numbers
user_roll_numbers = {}

# URL for login action
login_url = "http://tkrcet.in/login_action.php"

# Token extracted from the form (assuming it's static)
token = "MTcyNjEwODg0OTR6TVZGRnJnbHF4R2RIRWFiZ0hxOTU3NWN5Nk1zcXRU"

# Conversation handler states
ASK_ROLLNO = 1

# Function to check attendance
def check_attendance(roll):
    login_data = {
        'token': token,  # Hidden token field
        'username': roll,  # Roll number or username
        'password': roll,  # Password (assuming roll number is also the password)
        'submit': 'Login',  # Submit button value
    }

    session = requests.Session()
    response = session.post(login_url, data=login_data)
    
    if response.status_code != 200:
        raise Exception(f"Failed to log in. Status code: {response.status_code}")
    
    # with open('test.html', 'w', encoding='utf-8') as file:
    #     file.write(response.text)  # Write the HTML content, not the response object

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find attendance value
    attendance_element = soup.find('th', class_='text-blue')
    if attendance_element:
        attendance_value = attendance_element.text.strip()
        return attendance_value
    else:
        raise Exception("Attendance element not found. The page structure may have changed.")

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
    await update.message.reply_text(f"Roll number saved as {roll_no}. Now use /at to check your attendance.")
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

def main():
    application = Application.builder().token("7019335062:AAFS42J4nJOQ-5I7MUSQ_AQ0WdaFnu01HTQ").build()

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

    application.run_polling()

if __name__ == '__main__':
    main()
