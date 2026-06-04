# Dataset
In any MLXP cluster pod, 
```
/mnt/ddn/extra-ddn-continuous-gui/
    labeled/
        README.md
        <game-name>/
            <recording>.mkv
            <recording>.mcap
        .source-metadata/        # provenance and verification artifacts, not training input
    unlabeled/
        README.md
        <game-name>/
            <video>.mkv
        .source-metadata/        # provenance and verification artifacts, not training input
```