"""Twenty-nine new emails for the same inbox, written as realistic traffic.

Each one is labelled before any run, from the agent's own written triage rules
(`default_triage_instructions` in the agent's prompts.py); `rule` quotes the rule that decides
it. Emails that need a reply also carry the tools LangChain's response preferences call for and
written criteria in the style of LangChain's own dataset. They are harder than the shipped
sixteen in the ways real mail is harder: longer threads, a question buried in an FYI, look-alike
phishing, notifications that mention a person by name. None is ambiguous under the rules.
"""

LANCE = "Lance Martin <lance@company.com>"
WRITE = ["write_email", "done"]
MEET_TIMES = ["check_calendar_availability", "schedule_meeting", "write_email", "done"]
MEET_OPEN = ["check_calendar_availability", "write_email", "done"]


def e(author, subject, body, label, rule, calls=None, criteria="", to=LANCE):
    """One traffic email with its label and, for replies, the expected tools and criteria."""
    return {
        "email_input": {"author": author, "to": to, "subject": subject, "email_thread": body},
        "classification": label,
        "rule": rule,
        "expected_calls": calls or [],
        "criteria": criteria,
    }


EMAILS = [
    # --- respond -------------------------------------------------------------------------------
    e("Priya Raman <priya.raman@company.com>", "Re: Q3 planning notes",
      """Hi all,

Attaching the notes from Monday's planning session. Highlights:
- Retrieval eval harness moves to the platform team in Q3
- Docs refresh owned by Sam
- Hiring: two backend roles open

Lance, one thing for you specifically: does the streaming endpoint still support the `include_metadata` flag after last week's refactor? The docs team needs to know before Friday's release notes go out.

Thanks,
Priya""",
      "respond", "Technical questions about documentation, code, or APIs", WRITE,
      "• Send email with write_email tool call answering or committing to check the include_metadata question\n• Acknowledge the Friday release-notes deadline"),
    e("Marcus Lee <marcus.lee@company.com>", "Can we sync on the eval dashboard?",
      """Hey Lance,

I'd like 30 minutes to walk through the eval dashboard mockups before we hand them to design. Would Wednesday at 10am or Thursday at 2pm work for you?

Marcus""",
      "respond", "Meeting requests requiring confirmation", MEET_TIMES,
      "• Check calendar availability for Wednesday 10am and Thursday 2pm with check_calendar_availability tool call\n• Schedule a 30-minute meeting at one of the proposed times with schedule_meeting tool call\n• Send email with write_email tool call confirming the time and the 30-minute duration"),
    e("Dana Whitfield <dana@acmecorp.com>", "Production outage after upgrading the SDK",
      """Hi Lance,

After upgrading to the latest SDK this morning, every agent run in our production environment fails with `KeyError: 'run_id'` inside the tracing callback. We've rolled back for now, but this blocks our launch on Thursday.

Can your team look at this urgently? Happy to share logs.

Dana Whitfield
Head of Engineering, Acme Corp""",
      "respond", "Critical bug reports related to team's projects", WRITE,
      "• Send email with write_email tool call acknowledging the outage and committing to investigate\n• Acknowledge the Thursday launch deadline\n• Ask for or accept the offered logs"),
    e("Harrison Chase <harrison@company.com>", "Board deck numbers",
      """Lance,

I'm finalizing the board deck tonight. Please confirm you've seen the updated adoption numbers in the shared doc and that the eval section is accurate. Just need a quick yes.

H""",
      "respond", "Requests from management requiring acknowledgment", WRITE,
      "• Send email with write_email tool call acknowledging the request about the adoption numbers and eval section"),
    e("Wife <wife@personal.com>", "Don't forget Saturday",
      """Hey love,

Reminder that we have dinner with my parents on Saturday at 7. Can you pick up the cake from Bella's Bakery on the way? Let me know.

xo""",
      "respond", "Personal reminders related to family (wife / daughter)", WRITE,
      "• Send email with write_email tool call confirming Saturday dinner and the cake pickup"),
    e("Lincoln Elementary <office@lincolnelementary.org>", "Your daughter's science fair - volunteer sign-up",
      """Dear Parent,

Your daughter Emma's class is presenting at the science fair on March 14. We're looking for parent volunteers for setup from 8 to 9am. Please reply by March 7 to let us know if you can help.

Thank you,
Lincoln Elementary Office""",
      "respond", "Personal reminders related to family (wife / daughter)", WRITE,
      "• Send email with write_email tool call replying about volunteering\n• Acknowledge the March 7 reply deadline"),
    e("Smile Dental <appointments@smiledental.com>", "Time for your cleaning",
      """Hi Lance,

Our records show you're due for your six-month cleaning. Reply to this email with a day that works and we'll book you in.

Smile Dental""",
      "respond", "Personal reminder related to self-care (doctor appointments, etc)", WRITE,
      "• Send email with write_email tool call to book or request a cleaning appointment"),
    e("Kenji Watanabe <kenji@globex.io>", "Does LangGraph support per-node timeouts?",
      """Hi Lance,

We're evaluating your platform for our support automation. Before our architecture review next Tuesday, could you tell us whether per-node timeouts are supported, and if not, whether they're on the roadmap?

Best,
Kenji Watanabe, Globex""",
      "respond", "Client inquiries about project status or features", WRITE,
      "• Send email with write_email tool call responding to the per-node timeout question or committing to find out\n• Acknowledge the architecture review next Tuesday"),
    e("Sofia Alvarez <sofia.alvarez@company.com>", "Quick question on the retry decorator",
      """Lance,

The retry decorator in utils/backoff.py swallows the original exception when max_retries is hit. Was that intentional? I'm about to change it to re-raise and want to make sure I'm not breaking something you depend on.

Sofia""",
      "respond", "Direct questions from team members requiring expertise", WRITE,
      "• Send email with write_email tool call answering whether the behaviour was intentional or saying they will check"),
    e("Rachel Kim <rachel.kim@company.com>", "Coffee chat?",
      """Hi Lance,

I just joined the applied AI team and would love to pick your brain about the evaluation tooling. Could we find 30 minutes sometime next week? I'm pretty flexible.

Rachel""",
      "respond", "Meeting requests requiring confirmation", MEET_OPEN,
      "• Check calendar availability with check_calendar_availability tool call\n• Send email with write_email tool call proposing multiple time options for a 30-minute chat"),
    e("Tom Becker <tom.becker@company.com>", "FW: Customer escalation - missing traces",
      """Lance - forwarding below. Can you take a look and tell the customer what's going on? They're a top-10 account.

---------- Forwarded message ----------
From: Lena Fischer <lena@initech.com>
Subject: Missing traces

Since yesterday about a third of our traces never show up in the dashboard. Nothing changed on our side. Is something wrong with ingestion?""",
      "respond", "Requests from management requiring acknowledgment", WRITE,
      "• Send email with write_email tool call acknowledging the escalation and committing to investigate the missing traces"),
    e("Ana Costa <ana.costa@company.com>", "Review my design doc before Thursday?",
      """Hi Lance,

I've put the draft design doc for the memory store in our shared folder. Could you review it before Thursday's architecture meeting? Your comments on the eviction section would be most useful.

Thanks!
Ana""",
      "respond", "Direct questions from team members requiring expertise", WRITE,
      "• Send email with write_email tool call agreeing to review the design doc\n• Acknowledge the Thursday deadline\n• Mention the eviction section"),
    e("Omar Haddad <omar@company.com>", "Interview loop - can you join Friday?",
      """Lance,

We need one more interviewer for a staff engineer candidate on Friday. The slot is 1pm to 2pm. Can you take the systems design round?

Omar""",
      "respond", "Meeting requests requiring confirmation", MEET_TIMES,
      "• Check calendar availability for Friday with check_calendar_availability tool call\n• Schedule the Friday 1pm interview with schedule_meeting tool call, or decline it\n• Send email with write_email tool call confirming or declining the 1pm slot"),

    # --- notify --------------------------------------------------------------------------------
    e("Jordan Price <jordan.price@company.com>", "Out sick today",
      """Hi team,

I'm out sick today. I'll be offline but checking Slack occasionally for anything urgent. My PR for the cache layer can wait until tomorrow.

Jordan""",
      "notify", "Team member out sick or on vacation", to="Engineering Team <eng@company.com>"),
    e("CI Bot <ci@company.com>", "FAILED: main build #4821",
      """Build #4821 on main FAILED.

Stage: integration-tests
Failed test: test_streaming_metadata_roundtrip
Triggered by: merge of PR #1290 (lance-martin)

View logs: https://ci.company.com/builds/4821""",
      "notify", "Build system notifications or deployments"),
    e("Deploy Bot <deploy@company.com>", "Deployed api-server v2.14.0 to production",
      """api-server v2.14.0 was deployed to production at 14:02 UTC.

Changes: 23 commits, including streaming metadata fix (#1288).
Rollback: run `deploy rollback api-server`""",
      "notify", "Build system notifications or deployments"),
    e("Mei Chen <mei.chen@company.com>", "Weekly status: retrieval evals",
      """Hi all,

Weekly update on retrieval evals:
- Benchmark v2 is 80% complete
- Recall@10 improved from 0.71 to 0.76 on the dev split
- No blockers this week

Next update next Friday.
Mei""",
      "notify", "Project status updates without action items", to="Applied AI <applied-ai@company.com>"),
    e("CEO Office <ceo@company.com>", "Company announcement: new office opening",
      """Team,

I'm excited to share that we're opening a new office in Austin in September. Existing teams are not moving; the office will host our new customer success group. More details at the all-hands next week.

Thanks,
The CEO Office""",
      "notify", "Important company announcements", to="All Staff <all@company.com>"),
    e("HR Department <hr@company.com>", "Reminder: benefits enrollment closes Friday",
      """Hi Lance,

Open enrollment for 2026 benefits closes this Friday at 5pm. If you don't make a selection, your current plan will roll over.

HR Department""",
      "notify", "HR Department deadline reminders"),
    e("GitHub <notifications@github.com>", "[langchain-ai/langgraph] Review requested on #3312",
      """@sofia-alvarez requested your review on pull request #3312: "Re-raise original exception in retry decorator".

Files changed: utils/backoff.py, tests/test_backoff.py

View pull request: https://github.com/langchain-ai/langgraph/pull/3312""",
      "notify", "GitHub notifications"),
    e("Figma <billing@figma.com>", "Your Figma Professional plan renews in 7 days",
      """Hi Lance,

Your Figma Professional subscription renews on June 3 for $15/month. No action is needed if you want to keep your plan.

Manage subscription: https://figma.com/billing""",
      "notify", "Subscription status / renewal reminders"),
    e("Nina Patel <nina.patel@company.com>", "FYI: vector store migration moved to next sprint",
      """Hi Lance,

Heads up since your retrieval work depends on it: the vector store migration slipped to next sprint because of the security review. The old index stays live until then, so nothing breaks in the meantime.

Nina""",
      "notify", "FYI emails that contain relevant information for current projects"),

    # --- ignore --------------------------------------------------------------------------------
    e("DevTools Weekly <newsletter@devtoolsweekly.com>", "This week: 10 VS Code extensions you need",
      """Hi Lance,

This week's issue: 10 VS Code extensions for AI engineers, a deep dive on vector databases, and 20% off our Pro membership with code SPRING20.

Read online | Unsubscribe""",
      "ignore", "Marketing newsletters and promotional emails"),
    e("IT Support <it-support@cornpany-helpdesk.com>", "Action required: your password expires today",
      """Dear user,

Your company password expires in 2 hours. To avoid losing access to email and Slack, verify your account now:

http://cornpany-helpdesk.com/verify?user=lance

IT Support Team""",
      "ignore", "Spam or suspicious emails"),
    e("Vanessa Cole <vanessa@cloudscale-partners.com>", "Lance, quick question about your infra",
      """Hi Lance,

I noticed LangChain is growing fast. Are you open to a quick call to see how CloudScale can cut your GPU spend by 40%? Most teams see ROI in the first month.

Book a slot here: https://cal.cloudscale-partners.com/vanessa

Vanessa
Account Executive, CloudScale""",
      "ignore", "Marketing newsletters and promotional emails"),
    e("Priya Raman <priya.raman@company.com>", "Re: offsite venue options",
      """Hi Sam,

Thanks for pulling these together. I like the second venue best; can you check whether they have AV for 40 people and get a quote by Wednesday?

Priya

(cc: Lance for visibility)""",
      "ignore", "CC'd on FYI threads with no direct questions",
      to="Sam Ortiz <sam.ortiz@company.com>"),
    e("Prize Center <winner@global-rewards-center.net>", "Congratulations Lance! You've been selected",
      """Congratulations!

You have been selected to receive a $500 Amazon gift card as a valued developer. Claim within 24 hours by confirming your shipping details:

http://global-rewards-center.net/claim/lance""",
      "ignore", "Spam or suspicious emails"),
    e("SaaS Summit <promo@saassummit.events>", "Last chance: 50% off SaaS Summit tickets",
      """Hi Lance,

Prices go up at midnight! Grab your SaaS Summit pass at 50% off and hear from 200+ speakers.

Get tickets | Unsubscribe""",
      "ignore", "Marketing newsletters and promotional emails"),
    e("Tom Becker <tom.becker@company.com>", "Re: team lunch Thursday",
      """Hi Mei,

Thursday works. Let's do the Thai place at 12:30. I'll book for six.

Tom

(Lance cc'd since he was on the original thread)""",
      "ignore", "CC'd on FYI threads with no direct questions",
      to="Mei Chen <mei.chen@company.com>"),
]
