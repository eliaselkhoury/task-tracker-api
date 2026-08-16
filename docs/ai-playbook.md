# My AI Playbook

I wrote this after finishing the Task Tracker project. These rules came from what actually happened while building and reviewing it.

I used **Claude Code (Opus 5)** for most of the work and **GitHub Copilot** for repetitive markup and CSS. Claude’s involvement is also recorded in the Git co-author trailers.

## When I Use AI

- To challenge a decision before coding.
- To enumerate boundary cases that I can review and turn into tests.
- To help with safe, behaviour-preserving refactors.
- To complete repetitive work after I have established the pattern.
- To get a second opinion on a diff I already understand.
- To draft infrastructure files whose syntax I use infrequently, followed by real execution and verification.

## When I Do Not Use AI First

- When I cannot clearly define the contract or scope.
- When a fact must be verified against a real file, version, commit, or advisory.
- When I need to debug my own understanding of the system.
- When the decision is mine to own, such as scope, priorities, or what “done” means.
- When I am trying to learn something I do not yet understand.

## My Rules

1. Never share secrets, credentials, personal or customer data, production logs, or confidential information.
2. Do not submit code I cannot explain.
3. Do not trust a green test suite on its own.
4. Do not allow AI to change the project scope.
5. Record what AI contributed, changed, or got wrong.
6. Distinguish facts proved by the repository from process claims that only I can attest to.

## How I Review AI-Generated Work

- Read the diff, not the summary.
- Ask what the tests are missing.
- Add an automated regression test when a proportional test harness exists.
- If an automated test would require disproportionate new infrastructure, record a reproducible manual check and state the limitation explicitly.
- Run the command instead of trusting the claim.
- Grade findings as useful, wrong, or noise.
- Treat disagreements between documentation, code, and Git history as findings.
- Check the exact Git state being discussed: a commit, a branch, and an uncommitted working tree are different artifacts.

## What I Am Still Figuring Out

I am still learning how these practices should work across a team, especially how to establish shared rules for AI use without turning every small change into excessive process.

I am also still deciding where the line belongs between a proportionate manual check and an automated regression test when a project has no existing test harness for that layer.

## Decision Card

| Situation | What I Do |
| --- | --- |
| **New feature** | Define the contract, scope, response shape, and required tests before asking for code. |
| **Code review** | Let AI widen the search, then verify and grade every finding myself. |
| **Debugging** | Reproduce the problem and provide the real error, input, and failing test. |
| **Infrastructure** | Let AI draft it, then read every line and run it for real. |
| **Documentation** | Check claims against the exact commit or working tree they describe. |
| **Testing** | Prefer an automated regression test; document a reproducible manual exception when no proportional harness exists. |
| **Never paste** | Credentials, tokens, environment values, personal or customer data, production logs, or confidential information. |
| **Main rule** | **If I cannot explain or verify it, it does not ship.** |
