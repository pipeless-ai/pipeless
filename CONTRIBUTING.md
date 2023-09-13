# Contributing Guidelines

Contributions are welcome via GitHub Pull Requests. This document outlines the process to help get your contribution accepted.

Any type of contribution is welcome: new features, bug fixes, documentation improvements, etc.

## How to Contribute

1. Fork this repository, develop, and test your changes.
2. Submit a pull request.

### Requirements

When submitting a PR make sure that:

- It must pass CI jobs for linting and test the changes (if any).
- The title of the PR is clear enough
- The commits follow [Conventional Commits Guidelines](https://www.conventionalcommits.org/en/v1.0.0/)
- If necessary, add information to the repository's `README.md`.

#### Sign Your Work

All commits must be GPG signed. Check [this guide](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits) to learn how to sign your commits with GPG.

We recommend adding also a sign-off. The sign-off is a simple line at the end of the explanation for a commit. All commits needs to be signed. Your signature certifies that you wrote the patch or otherwise have the right to contribute the material. The rules are pretty simple, you only need to certify the guidelines from [developercertificate.org](https://developercertificate.org/).

Then you just add a line to every git commit message:

```text
Signed-off-by: Joe Smith <joe.smith@example.com>
```

Use your real name (sorry, no pseudonyms or anonymous contributions.)

If you set your `user.name` and `user.email` git configs, you can sign your commit automatically with `git commit -s`.

Note: If your git config information is set properly then viewing the `git log` information for your commit will look something like this:

```text
Author: Joe Smith <joe.smith@example.com>
Date:   Thu Feb 2 11:41:15 2018 -0800

    Update README

    Signed-off-by: Joe Smith <joe.smith@example.com>
```

Notice the `Author` and `Signed-off-by` lines match. If they don't your PR will be rejected by the automated DCO check.

### PR Approval and Release Process

1. Changes are manually reviewed by Pipeless team members usually within a business day.
2. Once the changes are accepted, the PR is tested (if needed) into the Pipeless CI pipeline.
3. The PR is merged by the reviewer(s) in the GitHub `main` branch.
4. The new changes will be available in the next Pipeless release. The release cycle will push new versions to PyPi for all the affected components as well as build and publish the container images.
