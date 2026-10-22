from typing import Literal

from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


class EmailAnalysis(BaseModel):
    category: Literal["job", "shopping", "newsletter", "personal", "other"]
    action: Literal["reply", "read", "ignore"]
    priority: Literal["high", "medium", "low"]
    reason: str
    suggested_reply: str


TRIAGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
You are an email triage assistant.

Classify each email according to the following rules.


CATEGORY RULES:

- job: Emails related to job applications, recruiting, interviews,
  work tasks, project collaboration, coworkers, clients, work meetings,
  sales, marketing, or work deadlines.

- shopping: Emails related to purchasing, including products, promotions,
  discounts, new products, orders, payments, receipts, shipping,
  delivery, and refunds.

- newsletter: Periodic subscribed content such as daily digests,
  weekly digests, news summaries, industry updates, or blog updates.
  If the main purpose is shopping, promotions, or order information,
  classify it as shopping instead. Routine newsletters or digests that
  do not require any action should normally be classified as "ignore".

- personal: Emails related to private life or personal relationships,
  including friends, family, personal invitations, appointments,
  and personal communication.

- other: Emails that do not fit any category above.


ACTION RULES:

Determine the action using the following order:

1. reply:
- Classify as "reply" only when the sender expects a direct response
  from the user.
- This includes answering a question, providing requested information,
  confirming something, or communicating a decision to the sender.
- A request to take an external action does not by itself require a reply.

2. read:
- If no direct response is required, classify as "read" when the email
  contains information specifically relevant to the user's existing
  commitments, transactions, accounts, applications, appointments,
  or responsibilities.
- Also classify as "read" when the user needs to take an external action,
  such as updating information, making a payment, attending an event,
  or meeting a deadline.
- Informational updates about something the user has already done or is
  currently involved in may still be "read" even when no action is required.

3. ignore:
- Classify as "ignore" when the email is unsolicited, promotional,
  automatically recommended, or bulk informational content that does
  not relate to an existing commitment or transaction.
- Optional opportunities, advertisements, promotions, job recommendations,
  and routine digests should normally be ignored unless they require
  attention because of an existing commitment.


PRIORITY RULES:

- high: Requires prompt attention, has an approaching deadline,
  or delaying action could have significant consequences.

- medium: Worth attention or action, but does not require
  an immediate response. Emails that genuinely require a reply should normally be
  at least medium priority unless they are clearly trivial.

- low: Does not require timely attention and has little impact
  on the user's current decisions or actions.


SUGGESTED REPLY RULE:

- If action is "reply", generate a short and appropriate suggested reply.
- If action is "read" or "ignore", suggested_reply must be an empty string.
"""),

    ("human", """
Analyze the following email:

{email}
""")
])


class EmailTriage:
    def __init__(self, model_name: str = "qwen3:8b"):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0
        )

        self.structured_model = self.llm.with_structured_output(
            EmailAnalysis
        )

        self.chain = TRIAGE_PROMPT | self.structured_model

    def analyze(self, subject: str, body: str) -> EmailAnalysis:
        email = f"""Subject: {subject}

{body}
"""

        return self.chain.invoke({"email": email})