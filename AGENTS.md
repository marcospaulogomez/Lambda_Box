# Project conventions

- Use English names for source files, directories, identifiers and commit messages. Keep user-facing text in Portuguese unless requested otherwise.
- At the end of each validated delivery, provide explicit git add commands and an English commit message. The user prefers to commit and push manually; do not stage, commit or push without a new explicit request. Check the diff and tests first and preserve unrelated work.
- Explain the commit type briefly in Portuguese: `feat` adds behavior, `fix` corrects a defect, `refactor` reorganizes code without changing its behavior, and `docs` changes documentation.
- Keep the approved dark-blue interface and Lambda Box branding. Upload tools show progress at the top, upload controls on the left and selected files on the right on wide screens, with a stacked layout on smaller screens. Support pointer reordering and preserve keyboard controls. Tool icons use a brief hover/focus animation that respects reduced-motion preferences; the project support link has a green background.
- Keep real contacts and donation settings in the ignored .env file. Track only a blank .env.example. Values intentionally displayed on the website are public to visitors even though they are excluded from Git.
- Keep routes, services, processing adapters and templates separate so tools can evolve independently.
