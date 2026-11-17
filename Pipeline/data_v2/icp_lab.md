---
name: ICP Lab — AI Prospecting and Outreach Analytics
description: ICP Lab, Vaughn's AI-powered prospecting tool — paste a job description, get the people most likely to respond ranked by predicted engagement from his own outreach history, one-click personalized messages with tracking links, outreach funnel analytics, and a Work mode he uses for prospecting at Feathery.
company: personal
repo_url: https://github.com/VDEugenio/icp-lab
topics: [personal_projects, prospecting, sales_tooling, outreach_analytics, ai_ml, ideal_customer_profile, cold_outreach]
skills: [prospecting, data_analysis, claude_api, apollo, fastapi, postgresql, javascript, product_thinking, statistics]
story_types: [project, sales_tooling, product_pitch, problem_solving]
related_files: [outreach_extension.md, sales_journey_and_mentorship.md, projects_index.md]
---

# ICP Lab — AI Prospecting Built From His Own Outreach Data

**GitHub repository:** https://github.com/VDEugenio/icp-lab

## What it is

ICP Lab is a prospecting and analytics dashboard Vaughn built to answer one question: **who actually responds to my outreach?** It then uses the answer to find and rank new people to contact. It grew out of his **Outreach Extension** (see outreach_extension.md), which was effectively version 1. The extension made outreach fast and trackable. ICP Lab added the analytics and the prospecting intelligence on top.

He built it during his career switch into sales, his "SDR phase" of high-volume cold outreach. He has also used it for **prospecting at Feathery**.

## How it works

1. **Paste a job description.** Claude (Anthropic's Claude Haiku 4.5) extracts the company, role, department, and seniority. It then generates realistic LinkedIn titles for four groups of people worth contacting: **peers in the role, hiring managers, adjacent leaders** (for example, sales directors for an SE role), and **recruiters**.
2. **Find the people.** Apollo.io searches each group in parallel.
3. **Rank them.** Each person gets an **estimated likelihood of engaging**, as a percentage, based on how similar people have historically responded to Vaughn's outreach. The tool lays out exactly whom to contact first.
4. **One click to reach out.** Clicking a profile opens a preview of the person's LinkedIn page and **copies a personalized message to the clipboard** at the same time. The message uses the template that won Vaughn's **formal A/B testing of openers**, and fills in the prospect's name, the role he's targeting, and the company.
5. **Track everything.** Every message includes a link to Vaughn's website with a **unique slug** for that person, so he can see exactly who visited his site and who went on to ask his AI resume chatbot questions. LinkedIn fetches a link preview when the recipient opens the chat. That fetch is classified as automated traffic rather than a human click, but Vaughn's **Telegram integration** still notifies him that the conversation was opened. So he knows who **opened** his message, even if they never reply, and separately who **clicked**.

## The analytics

- **Funnel:** contacted → clicked → responded, with conversion at each stage and response rate over time.
- **Breakdowns:** click and response rates by seniority, company size, industry, country, and more, always shown with sample sizes.
- **ICP finder:** ranks every combination of attributes by click or response rate, filtering out small samples so noise can't pass for signal. This is how Vaughn found his **ideal customer profile** for outreach.
- **Reply scanner:** reads LinkedIn's "sent you a message" notification emails in Gmail (read-only) and automatically marks matching contacts as responded. Ambiguous matches go to a one-click review queue.

## The scoring model

The score is an estimated engagement rate built only from Vaughn's own outreach data. It starts from his overall click-through rate and adjusts for how people with the same **seniority** and **country** have responded. Small segments are pulled toward the average (empirical-Bayes shrinkage), so a lucky 2-for-2 group can't produce a 100% score. No single factor can move a score more than 2× in either direction. Each score is labeled strong, average, or weak, and the tooltip shows exactly which segments drove it. It is never a black box.

**The scoring is directionally supported by the data collected:** in backtesting, people scored "strong" engaged noticeably more than people scored "weak."

## What the data taught him

From his tracked outreach:

- About **1 in 4** people clicked through to his portfolio, and **12–18% replied**. The outreach produced **30 calls**.
- **People who clicked his link were 3.8× more likely to reply** (about 37% vs. 10%). Sending people to his interactive AI resume chatbot really did start conversations.
- **Entry-level people engaged far more than VPs** (about 34% vs. 12% click-through), the clearest pattern in the data. It suggests peers are often the best way into a company.
- **Large companies (5,000+ employees) and directors** had some of the highest response rates.

## Work mode: prospecting for Feathery

Vaughn added a **Work** mode for his job at Feathery. He describes a buyer persona (for example, commercial insurance brokers and commercial-lines producers), Claude expands it into the matching LinkedIn titles, and Apollo finds the people. It **excludes Feathery's current clients before any search credits are spent**, and work messages deliberately leave out his personal tracking links: outreach sent on his employer's behalf stays professional.

## Engineering highlights

- **Bot filtering:** about **87% of raw link visits turned out to be bots** (mostly link-preview crawlers). Vaughn's hosting edge stripped the visitor's real IP, so he forwarded the real IP and user agent through custom headers, classified every visit, and recounted all metrics on human clicks only. Every raw visit is kept, so visits can be reclassified later.
- **Name matching for the reply scanner:** normalizes accents, credential suffixes (PhD, MBA), pronouns, and emoji in LinkedIn display names. Only an unambiguous exact match is applied automatically.
- **Safety by design:** ICP Lab reads a shared database through a least-privilege Postgres role that can only update specific columns, and can't insert or delete. API credits are only spent on an explicit click.
- **Speed:** Vaughn built the core of ICP Lab (dashboard, ICP finder, enrichment, and the job-description prospecting flow) in about a day. The extension and its backend were built and deployed in a single morning.
- **Stack:** FastAPI (Python), PostgreSQL (Neon), vanilla HTML/CSS/JavaScript, Claude API, Apollo.io API, Gmail API, Telegram, deployed on Railway. About 6,000 lines of code across three repos (extension, backend, dashboard).

## Why it matters

ICP Lab shows how Vaughn approaches sales. He treats outreach as a funnel to be measured and improved, finds his ideal customer profile from real data instead of guesswork, and builds his own tools to sell smarter. He's an engineer who prospects, and a seller who can build.
