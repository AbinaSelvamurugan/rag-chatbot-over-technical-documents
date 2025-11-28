# Network troubleshooting field guide (original educational content)

## Check physical connectivity first

When a switch interface shows a down link, first inspect physical cabling, transceivers, power and the connected peer. A down physical link does not by itself prove a routing-protocol fault. Confirm interface administrative state and link state separately.

## Use a layer-by-layer method

Work from physical connectivity through addressing, routing and application reachability. Capture evidence and the time of the symptom. Avoid making unreviewed changes while collecting a baseline.

## IP addressing basics

IPv4 notation `192.0.2.1/24` describes a documentation-only IPv4 address with a 24-bit prefix. The `192.0.2.0/24` block is reserved for examples. It is not a production destination to probe.

## Configuration review and rollback

Before changing network settings, record current state, identify a rollback path and verify maintenance-window requirements. Review diffs before applying a change. A recovery plan must be tailored to the device and organizational process.
