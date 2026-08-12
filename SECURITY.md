# Security Policy

## Responsible Use

Aegis NetValid Core includes tooling that generates real network load and
simulates attack conditions:

- The **Traffic Stresser** engine launches `iperf3` traffic against a
  configurable `target_ip`.
- The **IoT Simulator**'s `infect <IP>` command flags one of its own
  *simulated* devices as a `DDoS_Attacker` for scenario testing. It does not
  send any command to, or otherwise affect, real devices at that address.

**Only point the Stresser at hosts and networks you own or have explicit,
written authorization to test.** Running bandwidth or stress tests against
infrastructure you do not control may violate the law (e.g. the U.S. Computer
Fraud and Abuse Act, or equivalent legislation elsewhere) and the acceptable
use policies of most networks and cloud providers. The maintainers are not
responsible for misuse of this software.

## Supported Versions

This project is pre-1.0 and does not yet maintain parallel release branches.
Security fixes are applied to the latest commit on `main`.

## Reporting a Vulnerability

If you discover a security vulnerability in this project (e.g. command
injection, unsafe deserialization, credential handling issues, or privilege
escalation), please report it privately rather than opening a public issue:

- Email: **daweilin7689@gmail.com**
- Include: affected file(s)/version, a description of the issue, and, if
  possible, steps to reproduce.

Please allow a reasonable amount of time for a fix before any public
disclosure. We aim to acknowledge reports within 5 business days.
