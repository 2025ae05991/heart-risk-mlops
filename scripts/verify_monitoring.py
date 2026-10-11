"""Run live monitoring checks after deploying and forwarding both monitoring services."""

from heartml.monitoring import main

if __name__ == "__main__":
    raise SystemExit(main())
