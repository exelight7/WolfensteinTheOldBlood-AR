# Observed English localization table

Steam build 616161: chunk0 record 22456, `strings/english.lang`, UTF-8 BOM and CRLF, 3572 quoted key/value pairs inside braces with // header comments. Native IDs are unique #str_ keys. Observed escapes are backslash-n and backslash-quote; unsupported syntax fails parsing. Literal escapes and exact file bytes are retained locally alongside decoded English.

Stable ID: resource path + colon + native key. English checksum: SHA-256 of decoded value encoded as UTF-8, without Unicode or whitespace normalization. This policy is versioned here; do not silently alter it after translation starts.

Repeated values are not merged: speaker/context may differ. A complete game-wide source inventory and actual placeholder/control grammar remain pending. Loose warning JSON must be investigated separately.
