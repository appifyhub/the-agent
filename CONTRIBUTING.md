# Contributing guide

[//]: # (Inspired by github.com/milosmns/code-stats/blob/master/CONTRIBUTING)

#### Thank you! 💚

First off, thank you for considering contributing to this project. It's people like you that make The Agent such a great tool.

Now let's get down to business.

### Why these guidelines?

Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open source project.

In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

Without this guide, we're all just making assumptions – the authors of this tool don't like that.

### What <u>does</u> this tool need?

The Agent is an open source project for a reason, and we love to receive contributions from our community — you!

There are many ways to contribute, from writing tutorials or blog posts, improving the documentation, submitting bug reports / bug fixes / feature requests, or even writing new code which can be incorporated back into the project.

The more work you do, the more karma you get.

### What <u>doesn't</u> this tool need?

Please, **do not** open issues, bug reports, feature requests and other work requests if the same already exists. Always check whether the issues page on GitHub already has your request, and see if the existing issue list can help you. Stack Overflow is also worth considering if you're customizing the tool for your needs.

Please, **do not** open new pull requests at random without creating an issue first. It is important that we don't start making changes to the tool without prior consent from the maintainers. This goes even for documentation fixes and other cosmetic improvements.

# Ground Rules

### Setting expectations

#### Maintainer and contributor responsibilities:

- Try to ensure cross-platform and backwards compatibility for every change
  - This is best done through the continuous integration (CI) pipelines
- Ensure that code that goes into the project meets all requirements set by the project configuration
  - CI pipelines and pull request templates are there to verify it, just in case
- Create issues for any changes and enhancements that you wish to make
  - Discuss things transparently and get feedback on your ideas
- Follow the best practices for the given platform, unless the project is configured to do differently
  - When not sure, follow the project's codebase to understand the maintainer decisions
- Keep feature versions as small as possible, preferably one new feature per version
  - The project uses [semantic versioning](https://semver.org)
- Maintainers are generally busy, and they do open-source work on a voluntary basis
  - Please treat maintainers as volunteers and not your employees
- Be welcoming to newcomers and encourage diverse new contributors from all backgrounds
  - See the [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct) for reference

### Your First Contribution

Not sure where to begin contributing to The Agent?

You can start by looking through the [list of open issues](https://github.com/appifyhub/the-agent/issues).
We will try to categorize the issues using labels/tags, so you'll be able to use labels/tags to filter.
While not perfect, the number of comments on an issue is a reasonable proxy for impact a given change will have.

#### For people (and bots) who have never contributed to open source projects before:

Working on your first issue? Here are some resources to get you started with Pull Requests (PRs):

- [EggHead's **How-To**](https://app.egghead.io/playlists/how-to-contribute-to-an-open-source-project-on-github)
- [MakeAPullRequest's **How-To**](https://makeapullrequest.com)
- [FirstTimersOnly's **How-To**](http://www.firsttimersonly.com)

You're not feeling ready to make your changes? Then feel ready to ask for help. 🤓 Everyone is a beginner at first!

For example, if a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed outside your work,
and that you need to update your git branch so it's easier to merge. Pro tips!

### <font color="#C03080">WhY dIs BaD cOdE? HoW tO wOrK?</font> 🙄

Well… look, we get it. Software evolves and 💩 happens over time.
Tech stacks change, popular libraries lose their appeal, and best practices change.
Despite the best efforts of maintainers, legacy code and technical debt often accumulate – not by choice, but by necessity.

In the case of The Agent, the project has traversed several phases:

1. Firebase Functions + JavaScript, closed-source
1. Firebase Functions + TypeScript, closed-source
1. Detached Python scripts in Digital Ocean: no framework, closed-source
1. Single service in a Docker-powered VPS: Python + Flask, closed-source
1. Single service in a Kubernetes environment: Python + FastAPI, closed-source
1. **The current, open-source version (Sep 2024)**: Python + FastAPI

Different features and modules were created using various languages and approaches to problem-solving, as well as using different programming paradigms. Consequently, some of the current Python code resembles JavaScript, other Bash code looks like Python, and some tooling & and scripts are similar to how things are written in Groovy.

A unified tech stack for all project layers is optimal, but constant and extensive refactoring was making this consolidation difficult. But hey, here's the good news – the project now relies on **only one** technology: [Python](https://www.python.org).

In addition, it's important to note that [Chat GPT](https://chatgpt.com) and [Claude](https://claude.ai) contributed (and continue to contribute) to parts of this code. [GitHub's Copilot](https://github.com/features/copilot) also played a significant role with its code generation feature. Due to the usage of these tools, coding styles and complexity vary across features.

Ending on a positive note – the project is now open-source and welcomes contributions for refactoring and cleanup!

-----

# Getting started

### How to submit contributions

The general how-to:

1. Read this Contributing guide
1. Take note of the project's [license](./LICENSE)
1. Check the [issues](https://github.com/appifyhub/the-agent/issues) to see if your change was already requested
1. Create your own fork of the repository
1. Make the changes inside your fork
1. When you finally like the changes and think the project could use them:
    1. Ensure that you've followed the code style of this project
    1. Open a new Pull Request, indicating that you are ready for a review
    1. Follow the PR template to ensure smooth communication

## How to report a bug

### Security issues

If you believe that you have found a security vulnerability, please **DO NOT** open an issue disclosing it. Try to reach out to the maintainers directly through their GitHub account pages.

In order to determine whether you are dealing with a security issue, ask yourself these two questions:

- Can I access something that's not mine, or something I shouldn't have access to?
- Can I enable or disable something for other people?

If the answer to either of those two questions is "yes", then you're probably dealing with a security issue. Note that even if you answer "no" to both questions, you may still be dealing with a security issue – so if you're unsure, just reach out to one of the maintainers in private to discuss it.

All security issues can be publicly disclosed after they've been fixed.

### General bugs

When filing a new bug ticket, make sure to follow the bug ticket template from the Issues page.

In general, we try to answer these five questions:

1. What product version are you using?
1. What operating system and processor architecture are you using? Or, what client are you using?
1. What did you do before you saw the issue?
1. What did you expect to see?
1. What did you see instead?

## How to suggest a feature/enhancement

### General requests

We should aim to provide simple, yet robust tooling for our users.

If you find yourself wishing for a feature that doesn't exist yet, you are probably not alone. There are others out there with similar needs. Many of the features that we have today were added because the users saw the need for them, whether internally or externally (post open-sourcing).

To make a new feature request, simply open a new issue on our Issues page on GitHub. There is a template you can use to make communication smoother. Make sure to include exactly what you'd like to see, why you need it, and how it should work (with details).

## Code review process

### General contributions

The maintainers look at Pull Requests (PRs) on a regular basis. We can't say exactly how often, but normally it's multiple times per month.
As each PR must include a link to the issue it is addressing, it should be clear to the maintainers what they're looking at.

After PR feedback has been given, we expect responses within two weeks. After two weeks, we may decide to close the PR if it isn't showing any activity.

### Code, commit messages, labeling, and other conventions

The rules are straightforward and more or less "industry standard":

- Lint tooling checks for code style and code conventions (runs in CI too)
- We use **imperative** language for commit messages
    - e.g. "**Add** feature X" instead of "_Adding_ feature X", answering the question "What will this commit do, if applied?"
- We try to make PRs small, so that they're easy to review
- All issues and PRs will be labeled by the maintainers

Language and framework defaults apply to everything else.

Happy coding! 🍀
