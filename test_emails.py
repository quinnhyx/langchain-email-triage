test_emails = [
    {
        "id": 1,
        "subject": "Interview Invitation – Machine Learning Intern",
        "body": """Hi Yixuan,

Thank you for applying for our Machine Learning Intern position.
We'd like to invite you to a 45-minute technical interview next week.

Please reply with your availability for Monday through Wednesday.

Best,
Sarah
University Recruiting""",
        "expected_category": "job",
        "expected_action": "reply",
        "expected_priority": "high",
    },

    {
        "id": 2,
        "subject": "Update on your Software Engineering Intern application",
        "body": """Hi Yixuan,

Thank you for your interest in our Software Engineering Intern position.
After careful consideration, we have decided to move forward with other candidates.

We appreciate the time you spent applying and wish you the best in your job search.""",
        "expected_category": "job",
        "expected_action": "read",
        "expected_priority": "medium",
    },

    {
        "id": 3,
        "subject": "New machine learning internships for you",
        "body": """Based on your job preferences, we found 12 new Machine Learning Intern positions.

Companies hiring this week include several startups and technology companies.

View your recommended jobs and apply today.
You are receiving this automated job alert based on your saved search.""",
        "expected_category": "job",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 4,
        "subject": "Reminder: Technical Interview Tomorrow",
        "body": """Hi Yixuan,

This is a reminder that your technical interview is scheduled for tomorrow at 2:00 PM ET.

The meeting link is included in your original invitation.
No response is required.

Best,
Recruiting Team""",
        "expected_category": "job",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 5,
        "subject": "Next steps for your internship application",
        "body": """Hi Yixuan,

We enjoyed speaking with you at the career fair.
Could you please send us an updated copy of your resume and your availability for a short call this week?

Thanks,
Daniel""",
        "expected_category": "job",
        "expected_action": "reply",
        "expected_priority": "high",
    },

    {
        "id": 6,
        "subject": "50% Off Ends Tonight",
        "body": """Our biggest sale of the month ends tonight!

Get 50% off selected clothing and accessories when you order before midnight.

Shop now while supplies last.
Unsubscribe from promotional emails here.""",
        "expected_category": "shopping",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 7,
        "subject": "Your order has shipped",
        "body": """Good news! Your order #48291 has shipped.

Expected delivery: in three business days.
You can track your package using the tracking link below.

No action is required.""",
        "expected_category": "shopping",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 8,
        "subject": "Payment failed for your recent order",
        "body": """We were unable to process your payment for order #91822.

Your order will be cancelled within 24 hours unless you update your payment information.

Please visit your account to resolve the issue.""",
        "expected_category": "shopping",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 9,
        "subject": "Your September receipt",
        "body": """Thank you for your purchase.

Total: $24.87
Payment method: Visa ending in 4218

This email is your receipt. No further action is required.""",
        "expected_category": "shopping",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 10,
        "subject": "AI Weekly: Agents are becoming production-ready",
        "body": """This week in AI:

- New developments in AI agents
- Open-source LLM releases
- RAG evaluation techniques
- Five papers worth reading

Thanks for subscribing to AI Weekly.
You can unsubscribe at any time.""",
        "expected_category": "newsletter",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 11,
        "subject": "Your weekly Waterloo career digest",
        "body": """Here are this week's recommended career opportunities, workshops, and employer events.

This digest is automatically sent every Sunday based on your preferences.

View all opportunities on the career portal.""",
        "expected_category": "newsletter",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 12,
        "subject": "Dinner this Friday?",
        "body": """Hey!

Are you free Friday evening? A few of us are thinking about getting dinner in Toronto around 7.

Let me know if you want to come!""",
        "expected_category": "personal",
        "expected_action": "reply",
        "expected_priority": "medium",
    },

    {
        "id": 13,
        "subject": "Photos from our Toronto trip",
        "body": """Hey Yixuan,

Here are the photos I took yesterday. The Google Drive link is below.

No rush, just thought you'd want them :)""",
        "expected_category": "personal",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 14,
        "subject": "Quick question",
        "body": """Hey,

Do you still have the notes from last week's machine learning lecture?
If you do, could you send them to me when you get a chance?

Thanks!""",
        "expected_category": "personal",
        "expected_action": "reply",
        "expected_priority": "medium",
    },

    {
        "id": 15,
        "subject": "Building Water Maintenance in Three Days",
        "body": """Dear Residents,

Water service in the building will be temporarily unavailable in three days from 9:00 AM to 12:00 PM due to scheduled maintenance.

Please plan accordingly. No response is required.

Residence Services""",
        "expected_category": "other",
        "expected_action": "read",
        "expected_priority": "medium",
    },

    {
        "id": 16,
        "subject": "Action Required: Verify your account",
        "body": """Your university account requires verification.

Please complete verification within 24 hours to avoid temporary loss of access to university services.

Sign in to your account portal to complete the process.""",
        "expected_category": "other",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 17,
        "subject": "Scheduled system maintenance tonight",
        "body": """The student portal will be unavailable tonight between 1:00 AM and 3:00 AM for scheduled maintenance.

This interruption does not affect your current coursework, planned access, or existing responsibilities.
No action is required. Services will automatically resume after maintenance is complete.""",
        "expected_category": "other",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 18,
        "subject": "Invitation: AI Networking Event",
        "body": """You're invited to an AI networking event this Thursday evening.

The event will include presentations from local AI companies followed by an open networking session.

This is an optional community event, not a recruiting session or work meeting.
You have not registered or committed to attending, and no response is expected.
Registration is optional and space is limited.""",
        "expected_category": "other",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 19,
        "subject": "Your password will expire in 3 days",
        "body": """Your university account password will expire in 3 days.

Please change your password before the expiration date to avoid losing access to university systems.

You can update your password through the account management portal.""",
        "expected_category": "other",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 20,
        "subject": "Thanks for chatting today",
        "body": """Hi Yixuan,

It was great meeting you at the recruiting event today.
Thanks for taking the time to learn more about our engineering team.

Feel free to stay in touch, and good luck with the rest of your semester!

Best,
Alex""",
        "expected_category": "job",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 21,
        "subject": "A time for the next conversation",
        "body": "Hi Yixuan, The team would like to meet you for the data engineering internship you applied for. We can offer Tuesday at 10 or Wednesday at 3 next week. Please send your choice by noon tomorrow so I can reserve the panel. —Maya, Recruiting",
        "expected_category": "job",
        "expected_action": "reply",
        "expected_priority": "high",
    },

    {
        "id": 22,
        "subject": "Where things stand",
        "body": "Hi Yixuan, Your application has passed the initial review. The hiring manager is away this week; we expect to send the next update in about two weeks. We have everything we need from you for now. —Evan, Recruiting",
        "expected_category": "job",
        "expected_action": "read",
        "expected_priority": "medium",
    },

    {
        "id": 23,
        "subject": "Your saved draft",
        "body": "You started an application for the research engineering placement but have not submitted it. The portal closes tomorrow at 5 PM ET; unfinished applications will not be considered. Submit through the portal if you want this application reviewed.",
        "expected_category": "job",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 24,
        "subject": "For our Thursday session",
        "body": "Hi Yixuan, The client review for the project you are working on starts tomorrow at 11 AM ET. We moved it from room 204 to room 310. Your demo is still on the agenda and the existing calendar invitation has been updated. —Priya",
        "expected_category": "job",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 25,
        "subject": "Summer reading group",
        "body": "Hi Yixuan, A few coworkers are planning an optional reading group next month. Could you email me which of the two papers attached you would prefer? We are collecting preferences over the next two weeks. —Luis",
        "expected_category": "job",
        "expected_action": "reply",
        "expected_priority": "medium",
    },

    {
        "id": 26,
        "subject": "All set for your desk",
        "body": "Your desk lamp purchase is confirmed: $38.40 paid, delivery expected in five business days. We will send tracking when it leaves the warehouse. Keep this confirmation if you need to contact us about the purchase.",
        "expected_category": "shopping",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 27,
        "subject": "Back on your card",
        "body": "The $62.00 refund for the shoes you returned has been issued to your original payment method. It should appear within five to seven business days. Your return is now complete.",
        "expected_category": "shopping",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 28,
        "subject": "This week's edit",
        "body": "Our weekly store email features linen bedding and new kitchen accessories. Take 15% off anything featured through Sunday. Browse the collection using the links below. You subscribed to offers at checkout.",
        "expected_category": "shopping",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 29,
        "subject": "A few hours left",
        "body": "Final reminder: your subscriber discount expires at midnight tonight. Save 40% on headphones while stock lasts. This offer is available to everyone on our mailing list.",
        "expected_category": "shopping",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 30,
        "subject": "One detail before we dispatch",
        "body": "Hi Yixuan, The apartment number is missing from the address for your paid chair purchase. Please reply with that number within two business days so we can release the shipment. Otherwise it will remain on hold. —Nora, Customer Support",
        "expected_category": "shopping",
        "expected_action": "reply",
        "expected_priority": "medium",
    },

    {
        "id": 31,
        "subject": "Research notes, issue 18",
        "body": "In this month's subscribed research digest: a comparison of speech benchmarks, three new datasets, and a discussion of reproducibility. Links to the articles are below. Manage your subscription at the bottom of this email.",
        "expected_category": "newsletter",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 32,
        "subject": "The week in energy",
        "body": "Your weekly energy news subscription covers storage costs, grid investment, and recent policy debates. Read the full stories on our site. This edition contains general industry news.",
        "expected_category": "newsletter",
        "expected_action": "ignore",
        "expected_priority": "low",
    },

    {
        "id": 33,
        "subject": "Neighborhood bulletin, June edition",
        "body": "This monthly bulletin includes garden photos and local history. For residents already registered for Saturday's community garden session, including you: the meeting point has changed to the west gate. Your place remains reserved; arrive at 10 AM this Saturday, three days from now.",
        "expected_category": "newsletter",
        "expected_action": "read",
        "expected_priority": "medium",
    },

    {
        "id": 34,
        "subject": "Accessibility dispatch, issue 9",
        "body": "This subscribed monthly dispatch links to new accessibility research and tools. It also includes the recording and slides from the accessibility workshop you attended last month, for your reference whenever useful.",
        "expected_category": "newsletter",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 35,
        "subject": "Tomorrow's participant briefing",
        "body": "This weekly digest covers talks and community news. For confirmed participants in tomorrow's conference, including you: registration now opens at 8 AM at the south entrance, and the first session starts at 8:30 instead of 9. Use the updated check-in instructions linked here.",
        "expected_category": "newsletter",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 36,
        "subject": "Saturday on the trail?",
        "body": "Hey Yixuan, Would you like to join me for a walk next Saturday? We can decide on a trail later; let me know sometime this week if you're interested. —Sam",
        "expected_category": "personal",
        "expected_action": "reply",
        "expected_priority": "medium",
    },

    {
        "id": 37,
        "subject": "The route we took",
        "body": "Hi Yixuan, Here is the map from the hike you asked about when we last spoke. The little cafe near the end was our favorite stop. Thought you might enjoy looking at it whenever you have time. —Leah",
        "expected_category": "personal",
        "expected_action": "read",
        "expected_priority": "low",
    },

    {
        "id": 38,
        "subject": "I'll meet you at the other entrance",
        "body": "Hey Yixuan, For our lunch in three days, the restaurant asked us to use the courtyard entrance because the front door is being repaired. Our reservation is still at 12:30. I've already confirmed it with them. —Jordan",
        "expected_category": "personal",
        "expected_action": "read",
        "expected_priority": "medium",
    },

    {
        "id": 39,
        "subject": "Can you pick her up?",
        "body": "Hi Yixuan, My train has been cancelled and I won't make it to Grandma's clinic appointment. Could you reply within the next hour to say whether you can collect her at 4 PM today? If you can't, I'll arrange a taxi. —Mom",
        "expected_category": "personal",
        "expected_action": "reply",
        "expected_priority": "high",
    },

    {
        "id": 40,
        "subject": "A small favor for next month",
        "body": "Hey Yixuan, Could you send me the name of the cafe you mentioned? I'm planning a birthday outing next month and would like to look it up sometime this week. —Rina",
        "expected_category": "personal",
        "expected_action": "reply",
        "expected_priority": "medium",
    },

    {
        "id": 41,
        "subject": "A change to your access",
        "body": "A new recovery email was added to your university account ten minutes ago. If you did not make this change, open the university account portal immediately to review recent activity and secure your account. This mailbox does not accept replies.",
        "expected_category": "other",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 42,
        "subject": "For tomorrow's discussion",
        "body": "Hi Yixuan, I am your instructor for the independent study course. Please reply by 5 PM today with the topic you plan to present in tomorrow's assessed discussion so I can finalize the order. —Professor Chen",
        "expected_category": "other",
        "expected_action": "reply",
        "expected_priority": "high",
    },

    {
        "id": 43,
        "subject": "Materials for next week",
        "body": "To students enrolled in History 210: next week's readings are now in the course portal. We will discuss them in class in seven days. The syllabus and assignment schedule are unchanged. —Course Office",
        "expected_category": "other",
        "expected_action": "read",
        "expected_priority": "medium",
    },

    {
        "id": 44,
        "subject": "Before the submission window closes",
        "body": "For students enrolled in Statistics 230: the problem set is due in the course portal tomorrow at 6 PM. Late submissions lose credit under the published course policy. Upload your work through the portal; do not email it to the teaching team.",
        "expected_category": "other",
        "expected_action": "read",
        "expected_priority": "high",
    },

    {
        "id": 45,
        "subject": "Monthly service bulletin",
        "body": "This general bulletin goes to everyone on the university IT announcements list. The alumni directory will undergo routine maintenance overnight next month. Student sign-in, course systems, and email are unaffected; no user action is needed.",
        "expected_category": "other",
        "expected_action": "ignore",
        "expected_priority": "low",
    },
]
