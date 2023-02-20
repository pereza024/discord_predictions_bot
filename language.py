def startText(title: str, believe: str, doubt: str, duration: str):
    text = f"> Prediction Started: **{title}** Time Left: **{duration}**\n" \
           f"```bash\n" \
           f"Type /believe (amount) to bet on \"{believe}\"\n" \
           f"Type /doubt (amount) to bet on \"{doubt}\"\n" \
           f"Type /points to check how many points you have```"
    return text