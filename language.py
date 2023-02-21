import math
from enum import Enum
from competition import Competition

def startText(title: str, believe: str, doubt: str, duration: str):
    text = f"> Prediction Started: **{title}** - Betting Submittion Time Left: **{duration}**\n" \
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

def winning_text(competition: Competition, winning_group: int):
       text = ""
       if winning_group == 0:
              text = f"Prediction Closed: **{competition.title}**\n" \
                     f"Results: **{competition.believe.title} - #{competition.believe.amount} ({math.trunc(competition.believe.amount / competition.believe.amount + competition.doubt.amount * 100)}%)** " \
                     f"vs. ({competition.doubt.amount / (competition.believe.amount + competition.doubt.amount) * 100}%) #{competition.doubt.amount} - {competition.doubt.title} \n" \
                     f"```bash\n" \
                     f"Congrats to all the winner!```"
       if winning_group == 1:
              text = f"Prediction Closed: **{competition.title}**\n" \
                     f"Results: {competition.believe.title} - #{competition.believe.amount} ({math.trunc(competition.believe.amount / competition.believe.amount + competition.doubt.amount * 100)}%) " \
                     f"vs. **({competition.doubt.amount / (competition.believe.amount + competition.doubt.amount) * 100}%) #{competition.doubt.amount} - {competition.doubt.title}** \n" \
                     f"```bash\n" \
                     f"Congrats to all the winner!```"

       return text