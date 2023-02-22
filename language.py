import math, json
from enum import Enum
from competition import Competition

import discord

class end_text_reasons(Enum):
       REFUND = 0
       BELIEVERS = 1
       DOUBTERS = 2

class Language():
              
       def __init__(self):
              self.data = json.load(open('string_dictionary.json'))

       def output_string(self, key: str , language: str = "en") -> str:
              for record in self.data['data']:
                     if key == record["key"]:
                            for text in record["content"]:
                                   if language == text["lang"]:
                                          return text["text"]

       def get_prediction_end(self, competition: Competition, reason: end_text_reasons, language: str = "en"):
              if reason == end_text_reasons.REFUND:
                     return self.output_string("refund_issued").format(
                            title = competition.title
                     )
              elif reason == end_text_reasons.BELIEVERS:
                     return self.output_string("winning_believers").format(
                            title = competition.title,
                            believe_title = competition.believe.title,
                            believe_amount = competition.believe.amount,
                            believe_percent = round(competition.believe.amount / (competition.believe.amount + competition.doubt.amount) * 100),
                            doubt_title = competition.doubt.title,
                            doubt_amount = competition.doubt.amount,
                            doubt_percent = round(competition.doubt.amount / (competition.believe.amount + competition.doubt.amount) * 100)
                     )
              elif reason == end_text_reasons.DOUBTERS:
                     return self.output_string("winning_doubters").format(
                            title = competition.title,
                            believe_title = competition.believe.title,
                            believe_amount = competition.believe.amount,
                            believe_percent = round(competition.believe.amount / (competition.believe.amount + competition.doubt.amount) * 100),
                            doubt_title = competition.doubt.title,
                            doubt_amount = competition.doubt.amount,
                            doubt_percent = round(competition.doubt.amount / (competition.believe.amount + competition.doubt.amount) * 100)
                     )