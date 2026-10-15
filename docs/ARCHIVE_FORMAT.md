# Observed chunk index layout

Scope: eight chunk pairs from Steam build 616161. Not a complete specification for master.index or streamed resources.

At index byte 0x24: big-endian u32 record count, then u32 unknown (observed zero). Each record contains three little-endian u32 byte-length-prefixed UTF-8 strings (type, logical name, resource path), followed by big-endian u32 archive offset, decoded size, stored size and dependency count. Skip dependency_count * 24 + 5 opaque bytes; skip another four opaque bytes between records. All observed indexes end exactly after their last record.

Offsets and stored sizes are checked against the matching resources file. Equal stored/decoded size denotes uncompressed data for the extracted language resources. Other selected payloads decode as raw DEFLATE with a terminal sync-flush marker. See DISCOVERY_REPORT.md for the failed complete-stream assumption and validation method.

Unknown headers, dependencies, inter-record fields and archive metadata must be preserved until understood. No repacker or game-valid append strategy has been established.
