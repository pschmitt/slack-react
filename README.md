# 💬 slack-react 🚀

Automate your Slack reactions! This Python project allows you to automatically
add emoji reactions to Slack messages. The emojis are generated based on a 
user-provided message, with each character in the message converted to a 
corresponding emoji.

## 📚 Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [License](#license)

## ⚙️ Installation

```bash
pipx install slack-react
```

## 🛠 Usage

Before using this project, you need to get your Slack OAUTH token. 

Refer to [this guide](https://api.slack.com/authentication/token-types) to 
create and install a Slack app to get your token.

Once you have your token, set it as an environment variable.

```bash
export SLACK_OAUTH_USER_TOKEN=your-slack-token
```

Now you're ready to use the project! You can run the script using the following
command:

```bash
python slack_react.py "your message" -c "your-channel"
```

Replace `"your message"` with the message you want to spell out with reactions.
Replace `"your-channel"` with the name of the channel where you want to add the
reactions. 
The script will convert each character in the message to a corresponding emoji 
and add these emojis as reactions to the most recent message in the 
specified channel.

## 📖 Examples

```bash
python slack_react.py -c "general" "hello" 
```

This command will spell out "hello" in emoji reactions in the "general" channel.

## 📜 License

This project is licensed under the [GPL-3.0 License](./LICENSE).
