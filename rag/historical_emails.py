"""Synthetic history and manually labeled retrieval fixtures, separate from triage."""

historical_emails = [
    {
        "id": "h001",
        "thread_id": "aster-intern-2026",
        "sender": "maya@aster.example",
        "recipient": "yixuan@example.test",
        "subject": "Aster summer placement",
        "body": "Thanks for applying to Aster Robotics' perception internship. We would like to arrange a technical conversation about your robotics coursework. Please send a few times you are available next week.",
        "date": "2026-09-15"
    },
    {
        "id": "h002",
        "thread_id": "aster-intern-2026",
        "sender": "yixuan@example.test",
        "recipient": "maya@aster.example",
        "subject": "Re: Aster summer placement",
        "body": "Hi Maya, for the Aster Robotics perception internship interview I can meet on September 22 at 10 AM ET. My robotics project used camera calibration and point cloud registration.",
        "date": "2026-09-16"
    },
    {
        "id": "h003",
        "thread_id": "aster-intern-2026",
        "sender": "maya@aster.example",
        "recipient": "yixuan@example.test",
        "subject": "Re: Aster summer placement",
        "body": "Your Aster Robotics perception internship interview is confirmed for September 22 at 10 AM ET with engineer Devin. Please prepare to discuss camera calibration. We will follow up with a decision afterward.",
        "date": "2026-09-18"
    },
    {
        "id": "h004",
        "thread_id": "aster-intern-2025",
        "sender": "maya@aster.example",
        "recipient": "yixuan@example.test",
        "subject": "Aster summer placement",
        "body": "For your 2025 Aster Robotics perception internship application, we booked the technical interview for February 11, 2025. The panel will ask about robot navigation.",
        "date": "2025-02-05"
    },
    {
        "id": "h005",
        "thread_id": "aster-intern-2025",
        "sender": "maya@aster.example",
        "recipient": "yixuan@example.test",
        "subject": "Re: Aster summer placement",
        "body": "The 2025 Aster Robotics perception internship recruitment cycle is complete. We selected another candidate. This closes your February application.",
        "date": "2025-02-20"
    },
    {
        "id": "h006",
        "thread_id": "beacon-data-2026",
        "sender": "noah@beacon.example",
        "recipient": "yixuan@example.test",
        "subject": "Next conversation",
        "body": "Beacon Analytics would like to interview you for our data platform internship. The exercise will involve SQL query plans and batch ingestion. Can you meet on September 24?",
        "date": "2026-09-17"
    },
    {
        "id": "h007",
        "thread_id": "beacon-data-2026",
        "sender": "yixuan@example.test",
        "recipient": "noah@beacon.example",
        "subject": "Re: Next conversation",
        "body": "Hi Noah, September 24 at 2 PM ET works for the Beacon Analytics data platform internship interview. I have attached my resume with the database migration project.",
        "date": "2026-09-18"
    },
    {
        "id": "h008",
        "thread_id": "beacon-data-2026",
        "sender": "noah@beacon.example",
        "recipient": "yixuan@example.test",
        "subject": "Re: Next conversation",
        "body": "Your Beacon Analytics interview on September 24 at 2 PM ET is confirmed. After the SQL exercise, the data platform team will discuss next steps with you.",
        "date": "2026-09-19"
    },
    {
        "id": "h009",
        "thread_id": "capstone-ethics",
        "sender": "chen@university.example",
        "recipient": "yixuan@example.test",
        "subject": "Before we collect recordings",
        "body": "For your capstone study of speech recognition, the ethics board requires a consent form before recording volunteers. Please revise the retention section and send the form to me for review.",
        "date": "2026-09-12"
    },
    {
        "id": "h010",
        "thread_id": "capstone-ethics",
        "sender": "yixuan@example.test",
        "recipient": "chen@university.example",
        "subject": "Re: Before we collect recordings",
        "body": "Professor Chen, I revised the speech capstone consent form to delete recordings after 30 days. The updated participant information and retention section are attached.",
        "date": "2026-09-14"
    },
    {
        "id": "h011",
        "thread_id": "capstone-ethics",
        "sender": "chen@university.example",
        "recipient": "yixuan@example.test",
        "subject": "Re: Before we collect recordings",
        "body": "The revised consent form for your speech capstone is approved. Use this version for volunteers; do not begin recording until each person signs. Keep the signed forms in the university research folder.",
        "date": "2026-09-16"
    },
    {
        "id": "h012",
        "thread_id": "family-lake-trip",
        "sender": "eli@family.example",
        "recipient": "yixuan@example.test",
        "subject": "Saturday plans",
        "body": "For our family trip to Cedar Lake on October 10, I reserved two kayaks at the west marina. Please bring a waterproof jacket. We will meet at the marina at 9 AM.",
        "date": "2026-10-01"
    },
    {
        "id": "h013",
        "thread_id": "family-lake-trip",
        "sender": "yixuan@example.test",
        "recipient": "eli@family.example",
        "subject": "Re: Saturday plans",
        "body": "Hi Eli, I will bring a jacket for our October 10 Cedar Lake trip. Is the kayak reservation under your name or mine?",
        "date": "2026-10-02"
    },
    {
        "id": "h014",
        "thread_id": "family-lake-trip",
        "sender": "eli@family.example",
        "recipient": "yixuan@example.test",
        "subject": "Re: Saturday plans",
        "body": "The Cedar Lake kayak booking for October 10 is under Eli Morgan. The west marina sent reservation code CL-418. We still meet at 9 AM.",
        "date": "2026-10-03"
    },
    {
        "id": "h015",
        "thread_id": "birch-chair-return",
        "sender": "support@birch.example",
        "recipient": "yixuan@example.test",
        "subject": "Your return request",
        "body": "We accepted the return of the damaged Birch Home desk chair, purchase BH-731. Print the attached prepaid label and send it back by October 15. Refunds are issued after inspection.",
        "date": "2026-09-28"
    },
    {
        "id": "h016",
        "thread_id": "birch-chair-return",
        "sender": "support@birch.example",
        "recipient": "yixuan@example.test",
        "subject": "Inspection complete",
        "body": "The returned desk chair from purchase BH-731 passed inspection. Birch Home has issued a $148 refund to your card; allow five business days for it to appear.",
        "date": "2026-10-04"
    },
    {
        "id": "h017",
        "thread_id": "birch-chair-promo",
        "sender": "offers@birch.example",
        "recipient": "yixuan@example.test",
        "subject": "A better desk setup",
        "body": "Birch Home desk chairs are 20% off this weekend. Members can get free shipping on new furniture purchases. Explore our autumn workspace collection.",
        "date": "2026-10-04"
    },
    {
        "id": "h018",
        "thread_id": "university-recovery",
        "sender": "security@university.example",
        "recipient": "yixuan@example.test",
        "subject": "Recovery settings updated",
        "body": "A recovery phone number ending in 9082 was added to your university account on October 2. If you did not authorize the change, review account activity through the university security portal.",
        "date": "2026-10-02"
    },
    {
        "id": "h019",
        "thread_id": "university-recovery",
        "sender": "helpdesk@university.example",
        "recipient": "yixuan@example.test",
        "subject": "Re: Recovery settings updated",
        "body": "We received your report of an unauthorized recovery phone change. University IT removed the number ending in 9082 and revoked active sessions. Reset your password through the official portal.",
        "date": "2026-10-03"
    },
    {
        "id": "h020",
        "thread_id": "retail-recovery",
        "sender": "security@birch.example",
        "recipient": "yixuan@example.test",
        "subject": "Recovery settings updated",
        "body": "Your Birch Home shopping account recovery phone number ending in 1144 was changed. This notice concerns only your retail account and does not affect your university login.",
        "date": "2026-10-02"
    },
    {
        "id": "h021",
        "thread_id": "accessibility-session-oct",
        "sender": "events@accessibility.example",
        "recipient": "yixuan@example.test",
        "subject": "Room changed for our session",
        "body": "You are registered for the October 12 accessibility design workshop. The venue has moved to the library's east seminar room. Bring a laptop for the screen reader exercise.",
        "date": "2026-10-05"
    },
    {
        "id": "h022",
        "thread_id": "accessibility-session-may",
        "sender": "events@accessibility.example",
        "recipient": "yixuan@example.test",
        "subject": "Room changed for our session",
        "body": "For the May 8 accessibility design workshop, we moved the meeting to the arts building. This message concerns the spring event; its recording is now archived.",
        "date": "2026-05-02"
    },
    {
        "id": "h023",
        "thread_id": "career-mailing",
        "sender": "digest@career.example",
        "recipient": "yixuan@example.test",
        "subject": "Preparing for technical conversations",
        "body": "This week's career newsletter links to interview practice exercises for robotics and data platform internships. These are general resources, not an invitation or an update on your applications.",
        "date": "2026-09-20"
    },
    {
        "id": "h024",
        "thread_id": "lakeside-club",
        "sender": "outdoors@university.example",
        "recipient": "yixuan@example.test",
        "subject": "Saturday plans",
        "body": "The university outdoors club is offering an optional kayak day at Pine Lake on October 10. Members can book individually through the club website. This is not the Cedar Lake family reservation.",
        "date": "2026-10-01"
    },
    {
        "id": "h025",
        "thread_id": "ethics-news",
        "sender": "digest@research.example",
        "recipient": "yixuan@example.test",
        "subject": "Consent and recordings",
        "body": "This monthly research newsletter discusses consent forms and recording retention policies in speech studies. It summarizes public guidance and does not approve any individual capstone project.",
        "date": "2026-09-16"
    },
    {
        "id": "h026",
        "thread_id": "beacon-fulltime-2024",
        "sender": "noah@beacon.example",
        "recipient": "yixuan@example.test",
        "subject": "Next conversation",
        "body": "For the 2024 Beacon Analytics full-time data engineer opening, your SQL interview is scheduled for November 5. This hiring process is separate from the internship program.",
        "date": "2024-10-29"
    }
]

retrieval_queries = [
    {
        "id": "q1",
        "query": "Following up on our September 2026 Aster Robotics perception internship interview: what time and preparation did we agree on?",
        "relevant_ids": [
            "h001",
            "h002",
            "h003"
        ],
        "hard_negative_ids": [
            "h004",
            "h005",
            "h006",
            "h023"
        ],
        "note": "Current Aster process, not last year's process or another employer."
    },
    {
        "id": "q2",
        "query": "What are the arrangements for my September 2026 Beacon Analytics data platform internship SQL interview?",
        "relevant_ids": [
            "h006",
            "h007",
            "h008"
        ],
        "hard_negative_ids": [
            "h003",
            "h023",
            "h026"
        ],
        "note": "Beacon internship, not old full-time recruiting."
    },
    {
        "id": "q3",
        "query": "Professor Chen, what did we decide about consent and retention of volunteer recordings for my speech capstone?",
        "relevant_ids": [
            "h009",
            "h010",
            "h011"
        ],
        "hard_negative_ids": [
            "h025"
        ],
        "note": "Actual supervisor conversation rather than general ethics guidance."
    },
    {
        "id": "q4",
        "query": "For our October 10 family kayaking trip to Cedar Lake, where do we meet and whose name is the booking under?",
        "relevant_ids": [
            "h012",
            "h013",
            "h014"
        ],
        "hard_negative_ids": [
            "h024"
        ],
        "note": "Family reservation rather than the club's same-date trip."
    },
    {
        "id": "q5",
        "query": "Has the refund for my damaged Birch Home desk chair BH-731 been processed, and what was the return procedure?",
        "relevant_ids": [
            "h015",
            "h016"
        ],
        "hard_negative_ids": [
            "h017"
        ],
        "note": "Existing return transaction rather than another chair promotion."
    },
    {
        "id": "q6",
        "query": "I reported the unauthorized recovery phone ending 9082 on my university login. What changed and how did IT resolve it?",
        "relevant_ids": [
            "h018",
            "h019"
        ],
        "hard_negative_ids": [
            "h020"
        ],
        "note": "University security thread rather than retail recovery settings."
    },
    {
        "id": "q7",
        "query": "Where is the October 12 accessibility design workshop I registered for, and what should I bring?",
        "relevant_ids": [
            "h021"
        ],
        "hard_negative_ids": [
            "h022"
        ],
        "note": "Current workshop instead of similarly titled spring event."
    },
    {
        "id": "q8",
        "query": "What was the outcome of my February 2025 Aster Robotics perception internship recruitment process?",
        "relevant_ids": [
            "h004",
            "h005"
        ],
        "hard_negative_ids": [
            "h001",
            "h002",
            "h003"
        ],
        "note": "Old process intentionally relevant; recency alone must not decide relevance."
    }
]

