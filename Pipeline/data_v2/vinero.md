---
name: Vinero — Personal Finance App with One-Tap Card Recommender
description: Vinero, Vaughn's custom personal finance app — a one-tap iPhone button that detects what kind of store he's at and recommends which credit card maximizes rewards, plus budgeting, reimbursement tracking, and an AI (MCP) connection to Claude.
company: personal
topics: [personal_projects, personal_finance, fintech, product_thinking, ai_ml, mobile]
skills: [product_thinking, fastapi, react, typescript, postgresql, plaid, google_places, mcp, claude_code]
story_types: [project, product_pitch, problem_solving]
related_files: [projects_index.md]
---

# Vinero — A Personal Finance App Built Around One Tap

## Why he built it

Vaughn wanted to make sure he was using **every one of his credit cards as effectively as possible**. He also wasn't satisfied with the personal finance apps on the market. Everyone's finances, how they're structured, and what they're aiming for vary widely from person to person, and off-the-shelf apps force one model on everyone. So he built **Vinero**, a finance app customized to his own needs and goals.

One example: Vinero puts a big emphasis on **work travel reimbursements**. It tracks which expenses he needs to submit for reimbursement, then automatically matches each employer payout to the exact set of expenses it covers.

## The feature he's proudest of: "Which card here?"

A single button on his iPhone home screen:

1. It checks his **current location** and identifies the store he's at and what **type of vendor** it is.
2. It runs **his own cards' reward rates** through a rules engine. The engine converts every card's rewards ("3× points," "5% back," spending caps, excluded merchants) into one comparable number: cents earned per dollar.
3. It tells him **which card to use and why**, along with any current **Chase Offers** or **Rakuten** cash-back deals at that merchant. In case the nearest store is the wrong one, it also shows the next two nearby places.

Vaughn uses it **3–5 times a week**. By his estimate, picking the card this way earns **about 1.9× the rewards of a flat 2% cash-back card**, very close to the theoretical best on every purchase.

It's built as an **iOS Shortcut** that calls his backend, so there's **no native app to install**. It works from the home screen, the lock screen, the Action button, or Siri.

## The rest of the app (briefly)

Vinero also syncs his bank accounts through **Plaid**. It auto-categorizes spending, and a **Telegram bot** asks him about ambiguous purchases and learns from his answers. It covers budgets with pacing alerts, net worth, investments, and credit-score tracking. It also includes an **MCP server**, so he can ask **Claude** questions about his own finances in plain English.

## How it was built

Vaughn built Vinero in about a month, working **AI-assisted with Claude Code**: roughly 90 commits over 13 active building days. Stack: FastAPI, PostgreSQL, React/TypeScript, a Chrome extension, Google Places, and Plaid, with a large automated test suite.

## Why it matters

Vinero reflects how Vaughn thinks about selling: **find a real, everyday problem, make the solution dead simple (one tap), and make the value obvious.**
