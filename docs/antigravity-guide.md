# GRAVITAS with Google Antigravity

Use [the installation guide](install.md) for current commands. This page records
the product boundary that matters in day-to-day use.

- **Antigravity IDE** and **Antigravity CLI (`agy`)** are distinct surfaces.
- **Core** is installed project-locally at `.agents/skills/gravitas/` by the
  skills CLI command documented in this repository.
- **Native** is a separate `gravitas-native` plugin built from
  `dist/gravitas-antigravity` and installed with `agy plugin install`.
- Open a new CLI session and use `/hooks` to inspect active hook registration.

Antigravity’s current IDE and CLI documentation use different global skill and
plugin locations across releases. GRAVITAS deliberately documents the tested
project-local Core path and local `agy` plugin path instead of asking users to
copy files into a global directory.

Native hooks receive Antigravity hook JSON on stdin and return JSON on stdout.
They provide workflow checks around configured tool events; they are not an OS
sandbox. Keep host permissions and sandboxing enabled.

See Google’s [Plugins documentation](https://antigravity.google/docs/plugins),
[CLI plugins and skills documentation](https://antigravity.google/docs/cli/plugins/),
and [Hooks documentation](https://antigravity.google/docs/hooks).
