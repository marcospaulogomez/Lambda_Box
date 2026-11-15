# Project conventions

- Use English names for source files, directories, identifiers and commit messages. Keep user-facing text in Portuguese unless requested otherwise.
- At the end of each validated delivery, commit the changes and push them to the repository. The user authorized this workflow. Check the diff and tests first, preserve unrelated work, and do not force-push.
- Explain the commit type briefly in Portuguese: `feat` adds behavior, `fix` corrects a defect, `refactor` reorganizes code without changing its behavior, and `docs` changes documentation.
- Prioritize backend functionality. Keep the approved dark-blue interface; branding, animations and layout redesign are deferred. The requested future layout puts progress near the top and uploaded files alongside the workspace to reduce scrolling.
- Keep routes, services, processing adapters and templates separate so tools can evolve independently.
