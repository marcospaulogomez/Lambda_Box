# Project conventions

- Use English names for source files, directories, identifiers and commit messages. Keep user-facing text in Portuguese unless requested otherwise.
- At the end of each validated delivery, provide explicit git add commands and an English commit message. The user prefers to commit and push manually; do not stage, commit or push without a new explicit request. Check the diff and tests first and preserve unrelated work.
- Explain the commit type briefly in Portuguese: `feat` adds behavior, `fix` corrects a defect, `refactor` reorganizes code without changing its behavior, and `docs` changes documentation.
- Keep the approved dark-blue interface. The user has now authorized Lambda Box branding, narrower tool cards, contact pages and voluntary donations. Animations and internal workspace redesign remain deferred. The requested future layout puts progress near the top and uploaded files alongside the workspace to reduce scrolling.
- Keep real contacts and donation settings in the ignored .env file. Track only a blank .env.example. Values intentionally displayed on the website are public to visitors even though they are excluded from Git.
- Keep routes, services, processing adapters and templates separate so tools can evolve independently.
