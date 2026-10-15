# Distribution strategy

Distribute original tooling, Arabic data and licensed project font derivatives only. Full game archives, extracted original fonts/textures and complete English tables remain local.

Approach implemented locally: rebuild the user's own chunk0 archive in its original resource order, preserving untouched stored payloads and updating affected offsets/sizes in the index. The initial append-to-end approach caused FileTable is out of order and is superseded. The ordered version passed startup loading and the user's main-menu screenshot; broader runtime testing remains pending. No generated game archives or English runtime table are published.
