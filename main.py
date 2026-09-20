from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd

load_dotenv()

class EmailAnalysis(BaseModel):
    category: Literal["job", "shopping", "newsletter", "personal", "other"]
    action: Literal["reply", "read", "ignore"]
    priority: Literal["high", "medium", "low"]
    reason: str
    suggested_reply: str

prompt = ChatPromptTemplate.from_messages([
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
- If no direct response to the sender is required, classify as "read"
  when the user should know the information or needs to take an external action.
- External actions include completing a task, updating information,
  making a payment, visiting a website, attending an event, or meeting a deadline.
- The user may need to act urgently while the email is still classified as "read".

3. ignore:
- If no direct response is required and no meaningful external action is required,
  classify as "ignore" when the information does not require the user's attention.
- Routine newsletters, advertisements, promotions, discounts, and other
  non-essential bulk emails should normally be classified as "ignore".


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


email_llm = ChatOllama(model="qwen3:8b")
structured_model = email_llm.with_structured_output(EmailAnalysis)
chain = prompt | structured_model

def analyze_email(email:str) -> EmailAnalysis:
    result = chain.invoke({"email": email})
    return result

test_cases = [
    {
      "email": """
          Subject: Interview Availability

          Hi Alex,

          We enjoyed reviewing your application and would like to invite you
          to a technical interview this Thursday.

          Could you please send us your availability by tomorrow at noon?

          Best,
          Sarah
          """,
      "expected_category": "job",
      "expected_action": "reply",
      "expected_priority": "high"
    },

    {
      "email": """
          Subject: Your Order Has Shipped

          Hi Alex,

          Your order #58291 has shipped and is expected to arrive this Friday.
          You can track your package using the tracking link in your account.

          Thanks,
          Customer Service
          """,
      "expected_category": "shopping",
      "expected_action": "read",
      "expected_priority": "medium"
    },

    {
      "email": """
          Subject: 50% Off Today Only!

          Don't miss our biggest sale of the season.
          Get 50% off selected items when you shop before midnight tonight.

          Shop now and save!
          """,
      "expected_category": "shopping",
      "expected_action": "ignore",
      "expected_priority": "low"
    },

    {
      "email": """
        Subject: Dinner on Friday?

        Hey Alex,

        Are you free for dinner this Friday?
        I was thinking we could try the new Italian restaurant downtown.
        Let me know if you're interested!

        John
        """,
      "expected_category": "personal",
      "expected_action": "reply",
      "expected_priority": "medium"
    },

    {
      "email": """
        Subject: AI Weekly Digest

        Here is your weekly AI newsletter.

        This week's topics:
        - New open-source language models
        - Advances in multimodal AI
        - Three interesting research papers

        See you next week!
        """,
      "expected_category": "newsletter",
      "expected_action": "ignore",
      "expected_priority": "low"
    },

    {
      "email": """
        Subject: Project Meeting Moved to 3 PM

        Hi team,

        Tomorrow's project meeting has been moved from 2 PM to 3 PM.
        The meeting room remains the same.

        No response is required.

        Best,
        Michael
        """,
      "expected_category": "job",
      "expected_action": "read",
      "expected_priority": "medium"
    },

    {
      "email": """
        Subject: Payment Failed for Order #83920

        We were unable to process your payment for order #83920.

        Please update your payment information within 24 hours,
        otherwise your order will be cancelled.

        Customer Service
        """,
      "expected_category": "shopping",
      "expected_action": "read",
      "expected_priority": "high"
    },

    {
      "email": """
        Subject: Building Water Maintenance Notice

        Water service in your building will be temporarily unavailable
        tomorrow from 9 AM to 12 PM due to scheduled maintenance.

        No action is required.

        Building Management
        """,
      "expected_category": "other",
      "expected_action": "read",
      "expected_priority": "medium"
    }
]

category_correct_count = 0
action_correct_count = 0
priority_correct_count = 0
evaluation_results = []

for case in test_cases:
    email = case["email"]
    result = analyze_email(email)

    category_correct_count+=1 if result.category == case["expected_category"] else 0
    action_correct_count+=1 if result.action == case["expected_action"] else 0
    priority_correct_count+=1 if result.priority == case["expected_priority"] else 0

    evaluation_results.append({
        "email": email,
        "expected_category": case["expected_category"],
        "predicted_category": result.category,
        "expected_action": case["expected_action"],
        "predicted_action": result.action,
        "expected_priority": case["expected_priority"],
        "predicted_priority": result.priority
    })

category_accuracy = category_correct_count / len(test_cases)
action_accuracy = action_correct_count / len(test_cases)
priority_accuracy = priority_correct_count / len(test_cases)

print(f"Category Accuracy: {category_accuracy:.2%}")
print(f"Action Accuracy: {action_accuracy:.2%}")
print(f"Priority Accuracy: {priority_accuracy:.2%}")

df = pd.DataFrame(evaluation_results)

def confusion_matrix(df, expected_col, predicted_col):
    return pd.crosstab(
        df[expected_col],
        df[predicted_col]
    )

action_confusion_matrix = confusion_matrix(df, "expected_action", "predicted_action")
category_confusion_matrix = confusion_matrix(df, "expected_category", "predicted_category")
priority_confusion_matrix = confusion_matrix(df, "expected_priority", "predicted_priority")

critical_errors = df[
    (df["expected_action"] == "reply") &
    (df["predicted_action"] == "ignore")
]

action_errors = df[
  (df["expected_action"] != df["predicted_action"])
]
action_accuracy = 1 - len(action_errors) / len(df)

error_patterns = action_errors[
    ["expected_action", "predicted_action"]
].value_counts()

ignore_to_read = action_errors[
    (action_errors["expected_action"] == "ignore") &
    (action_errors["predicted_action"] == "read")
]

print(error_patterns)
print(
    action_errors[
        ["email", "expected_action", "predicted_action"]
    ]
)