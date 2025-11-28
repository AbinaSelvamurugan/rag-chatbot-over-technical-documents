# Junos CLI field notes (original educational summary)

This short independently written study note summarizes common Junos CLI ideas. It is not an official Juniper publication. For authoritative syntax and release-specific behavior, consult the source guide: https://www.juniper.net/documentation/us/en/software/junos/cli/topics/topic-map/cli-overview.html

## Operational and configuration modes

Junos OS CLI provides an operational mode for viewing device state and troubleshooting, and a configuration mode for changing device configuration. The `>` prompt typically denotes operational mode and the `#` prompt typically denotes configuration mode. Enter configuration mode from operational mode with `configure`.

## Examine the current configuration

Use `show configuration` in operational mode to display the current committed configuration. In configuration mode, `show` displays the candidate configuration at the current hierarchy. Before committing candidate changes, review changes with `show | compare` from configuration mode.

## Commit safety

The command `commit check` validates candidate configuration syntax and consistency without activating it. `commit confirmed 5` commits changes temporarily and automatically rolls them back if the commit is not confirmed before the five-minute timer expires. Check command support and operational policy for the software version on the device.

## Interface inspection

Use `show interfaces terse` in operational mode for a compact summary of interface administrative and link states. Detailed interface diagnosis may require `show interfaces extensive` and correlation with alarms and physical link status. Exact output varies by platform and software release.
