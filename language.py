from enum import Enum

def startText(title: str, believe: str, doubt: str, duration: str):
    text = f"> Prediction Started: **{title}** Time Left: **{duration}**\n" \
           f"```bash\n" \
           f"Type /believe (amount) to bet on \"{believe}\"\n" \
           f"Type /doubt (amount) to bet on \"{doubt}\"\n" \
           f"Type /points to check how many points you have```"
    return text

class end_text_reasons(Enum):
       REFUND = 0
       BELIEVERS = 1
       DOUBTERS = 2

def endText(title: str, reason: end_text_reasons):
       if reason == end_text_reasons.REFUND:
              text = f"> Prediction Closed: **{title}**\n" \
                     f"```bash\n" \
                     f"Users have been refunded their points ```"
       elif reason == end_text_reasons.BELIEVERS:
              pass
       elif reason == end_text_reasons.DOUBTERS:
              pass
       else:
              text = "Invalid enum returned"
       
       return text