## Installing

1. Clone the repository and navigate to the project directory:
```shell
git clone https://github.com/ZxcTimurka/ArchiverBot.git
cd ArchiverBot
```
2. Create a virtual environment:
```shell
python -m venv .venv
```
3. Activate the virtual environment:
```shell
.venv\Scripts\activate
```
3. Install the dependencies:
```shell
pip install pyTelegramBotAPI
```
4. Use the following command to start the bot:
```
python archive_bot_v1.py
```

## Setup
1. Using an Environment Variable (recommended):
  - Using the Command Prompt
    ```shell
    set TELEGRAM_BOT_TOKEN="YOUR_TOKEN"
    ```
  - Using a .env file: Create a file named .env in your project's root directory and add the line:
    ```
    TELEGRAM_BOT_TOKEN="YOUR_TOKEN"
    ```
2. Default Value
- replace TELEGRAM_BOT_TOKEN_HERE with your token
  
