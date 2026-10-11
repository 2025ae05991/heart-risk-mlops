"""Generate a submission status file; --strict fails while required evidence is pending."""

from heartml.submission import main

if __name__ == "__main__":
    raise SystemExit(main())
