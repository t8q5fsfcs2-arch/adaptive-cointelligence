# Adaptive Cointelligence

Adaptive Cointelligence creates adaptive intent through multiple people's
consequential work. A sponsor states what the business is trying to achieve.
Research, Design and other teams do their own professional work and publish what
they learn. Their contributions can confirm, refine or challenge the intent, and
authorized people decide what changes. The purpose endures while the plan adapts,
and the reasoning behind every change stays traceable.

AI helps people think, draft and check their work. It never approves anything.
Every consequential change is an explicit, versioned human decision.

## Run it

Requires **Python 3.12 or newer**.

```sh
git clone https://github.com/t8q5fsfcs2-arch/intelligence-workbench.git
cd intelligence-workbench
python3 run_demo.py
```

On Windows use `py -3.12 run_demo.py`. If your default `python3` is older, use
`python3.12`. The launcher creates its own environment and a synthetic
demonstration project in `.demo/` ([what's in it](docs/demo.md)), then prints the
browser link
(normally http://127.0.0.1:8770/). Run the same command again to resume. Use
`--port` to choose another port.

Verify the complete workflow in disposable data:

```sh
python3 run_demo.py --check
```

The demonstration runs offline with clearly labelled scripted examples. To use
live AI, open **Settings → Model connections** as Administrator, add your own
provider and key, test it and assign it to the project. Credentials stay in the
Git-ignored local demo folder.

## Tests

```sh
python -m unittest discover -s tests
node --test tests/*.cjs
```

## Documentation

- [IKE application authority and Builder entry](applications/adaptive-cointelligence/index.md) (future native application; start here for corpus preparation)
- [Architecture overview](docs/architecture.md)
- [Decisions](docs/decisions/README.md)
- [CLAUDE.md](CLAUDE.md): project instructions for development with Claude

This is a local experimental application using synthetic data. It is not a
production or enterprise-ready system.
